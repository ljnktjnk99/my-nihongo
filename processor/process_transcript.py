#!/usr/bin/env python3
"""
Process meeting transcript using Claude Code CLI.
Usage: python process_transcript.py <path_to_transcript.txt>
"""

import sys
import os
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "meetings"
PROMPT_TEMPLATE = Path(__file__).parent / "prompt_template.md"
LOG_DIR = Path(__file__).parent / "logs"


def setup_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def extract_date_from_filename(filepath: str) -> str:
    """Try to extract date from filename, fallback to today."""
    basename = Path(filepath).stem
    # Try patterns: 2025-02-24, 20250224, 2025_02_24
    patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{4})(\d{2})(\d{2})",
        r"(\d{4})_(\d{2})_(\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, basename)
        if m:
            groups = m.groups()
            if len(groups) == 1:
                return groups[0]
            return f"{groups[0]}-{groups[1]}-{groups[2]}"
    return datetime.now().strftime("%Y-%m-%d")


def read_transcript(filepath: str) -> str:
    """Read transcript file. Supports .txt, .rtf, .rtfd"""
    path = Path(filepath)

    # .rtfd is a directory (Apple Notes with attachments)
    if path.suffix.lower() == ".rtfd":
        rtf_file = path / "TXT.rtf"
        if rtf_file.exists():
            return _extract_text_from_rtf(str(rtf_file))
        else:
            raise FileNotFoundError(f"TXT.rtf not found inside {filepath}")

    # .rtf file
    if path.suffix.lower() == ".rtf":
        return _extract_text_from_rtf(filepath)

    # .txt or other text files
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _extract_text_from_rtf(filepath: str) -> str:
    """Extract plain text from RTF file using macOS textutil."""
    try:
        result = subprocess.run(
            ["textutil", "-convert", "txt", "-stdout", filepath],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: strip RTF tags manually
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    # Basic RTF tag removal
    text = re.sub(r'\\[a-z]+\d*\s?', '', content)
    text = re.sub(r'[{}]', '', text)
    return text.strip()


def build_prompt(transcript: str) -> str:
    """Build prompt from template + transcript."""
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    return template.replace("{TRANSCRIPT_CONTENT}", transcript)


def call_claude_code(prompt: str) -> str:
    """Call Claude Code CLI with the prompt."""
    print("🤖 Đang gọi Claude Code CLI xử lý transcript...")
    print("   (Có thể mất 1-3 phút tùy độ dài transcript)")

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=300,  # 5 min timeout
    )

    if result.returncode != 0:
        print(f"❌ Claude Code error: {result.stderr}")
        raise Exception(f"Claude Code failed: {result.stderr}")

    return result.stdout


def extract_json(response: str) -> dict:
    """Extract JSON from Claude's response."""
    # Try to parse directly
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in response
    json_patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```json\s*(.*?)\s*```",
        r"```\s*\n(.*?)\n\s*```",
        r"(\{[\s\S]*\})",
    ]
    for pattern in json_patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            json_str = match.group(1).strip()

            # Try to parse as-is
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # If parsing fails, try removing excess closing braces
                # This handles cases where Claude adds extra braces
                json_str_stripped = json_str.rstrip()
                for excess_count in range(1, 5):
                    try_str = json_str_stripped[:-excess_count] if excess_count > 0 else json_str_stripped
                    try:
                        return json.loads(try_str)
                    except json.JSONDecodeError:
                        continue

    # If all patterns fail, print debug info
    print(f"⚠️  JSON extraction failed. Response length: {len(response)}")
    print(f"   First 500 chars: {response[:500]}")
    raise ValueError("Could not extract valid JSON from Claude's response")


def validate_data(data: dict) -> bool:
    """Basic validation of the generated data."""
    required_keys = ["meeting_id", "date", "vocabulary", "phrases", "grammar", "exercises"]
    for key in required_keys:
        if key not in data:
            print(f"⚠️  Missing key: {key}")
            return False

    total_items = len(data.get("vocabulary", [])) + len(data.get("phrases", [])) + len(data.get("grammar", []))
    print(f"📊 Trích xuất: {len(data.get('vocabulary', []))} từ vựng, "
          f"{len(data.get('phrases', []))} cụm từ, "
          f"{len(data.get('grammar', []))} ngữ pháp")
    print(f"📝 Bài tập: {len(data.get('exercises', {}).get('translate_vj', []))} dịch V→J, "
          f"{len(data.get('exercises', {}).get('translate_jv', []))} dịch J→V, "
          f"{len(data.get('exercises', {}).get('fill_blank', []))} điền từ, "
          f"{len(data.get('exercises', {}).get('reorder', []))} sắp xếp")

    if total_items < 20:
        print(f"⚠️  Chỉ có {total_items} items, ít hơn mong đợi (50-100)")
    return True


def update_index(meeting_data: dict, date: str):
    """Update the index.json file with new meeting."""
    index_path = BASE_DIR / "data" / "index.json"

    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"meetings": [], "last_updated": ""}

    # Check if meeting already exists
    existing = [m for m in index["meetings"] if m["date"] == date]
    total_items = (len(meeting_data.get("vocabulary", []))
                   + len(meeting_data.get("phrases", []))
                   + len(meeting_data.get("grammar", [])))

    meeting_entry = {
        "id": meeting_data.get("meeting_id", date),
        "date": date,
        "topic": meeting_data.get("topic_hint", "Meeting"),
        "file": f"meetings/{date}.json",
        "total_items": total_items,
        "vocab_count": len(meeting_data.get("vocabulary", [])),
        "phrase_count": len(meeting_data.get("phrases", [])),
        "grammar_count": len(meeting_data.get("grammar", [])),
    }

    if existing:
        # Update existing
        index["meetings"] = [m if m["date"] != date else meeting_entry for m in index["meetings"]]
    else:
        index["meetings"].append(meeting_entry)

    # Sort by date desc
    index["meetings"].sort(key=lambda m: m["date"], reverse=True)
    index["last_updated"] = datetime.now().isoformat()

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"📋 Updated index.json ({len(index['meetings'])} meetings)")


def git_push(date: str):
    """Auto commit and push to GitHub."""
    try:
        os.chdir(BASE_DIR)
        subprocess.run(["git", "add", "data/"], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add meeting data: {date}"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)
        print("✅ Git push thành công!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git push failed: {e}")
        print("   Bạn có thể push thủ công: cd ~/nihongo-meeting && git push")


def process(filepath: str, auto_push: bool = True):
    """Main processing pipeline."""
    setup_dirs()

    print(f"\n{'='*50}")
    print(f"🎌 NihonGo Meeting - Xử lý Transcript")
    print(f"{'='*50}")
    print(f"📄 File: {filepath}")

    # 1. Read transcript
    transcript = read_transcript(filepath)
    print(f"📖 Đọc transcript: {len(transcript)} ký tự")

    # 2. Extract date
    date = extract_date_from_filename(filepath)
    print(f"📅 Ngày: {date}")

    # 3. Build prompt & call Claude
    prompt = build_prompt(transcript)
    response = call_claude_code(prompt)

    # 4. Save raw response log
    log_file = LOG_DIR / f"{date}_raw.txt"
    log_file.write_text(response, encoding="utf-8")

    # 5. Extract & validate JSON
    print("🔍 Đang parse JSON...")
    data = extract_json(response)
    data["date"] = date  # Ensure date is set

    if not validate_data(data):
        print("❌ Validation failed. Kiểm tra log:", log_file)
        return False

    # 6. Save JSON
    output_file = DATA_DIR / f"{date}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved: {output_file}")

    # 7. Update index
    update_index(data, date)

    # 8. Git push
    if auto_push:
        git_push(date)

    print(f"\n{'='*50}")
    print(f"✅ Hoàn tất! Data sẵn sàng trên app.")
    print(f"{'='*50}\n")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_transcript.py <path_to_transcript.txt>")
        print("Example: python process_transcript.py Meeting/2025-02-24_sprint.txt")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    # .rtfd is a directory - check for TXT.rtf inside
    if filepath.endswith(".rtfd"):
        rtf_inside = os.path.join(filepath, "TXT.rtf")
        if not os.path.exists(rtf_inside):
            print(f"❌ TXT.rtf not found inside {filepath}")
            sys.exit(1)

    auto_push = "--no-push" not in sys.argv
    success = process(filepath, auto_push=auto_push)
    sys.exit(0 if success else 1)
