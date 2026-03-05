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
TRANSLATIONS_DIR = BASE_DIR / "translations"
PROMPT_TEMPLATE = Path(__file__).parent / "prompt_template.md"
TRANSLATE_TEMPLATE = Path(__file__).parent / "translate_template.md"
LOG_DIR = Path(__file__).parent / "logs"


def setup_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)
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


def extract_slug_from_filename(filepath: str) -> str:
    """Extract slug from filename (basename without extension)."""
    return Path(filepath).stem


def read_transcript(filepath: str) -> str:
    """Read transcript file. Supports .txt, .rtf, .rtfd, .doc, .docx"""
    path = Path(filepath)
    ext = path.suffix.lower()

    # .rtfd is a directory (Apple Notes with attachments)
    if ext == ".rtfd":
        rtf_file = path / "TXT.rtf"
        if rtf_file.exists():
            return _extract_text_with_textutil(str(rtf_file))
        else:
            raise FileNotFoundError(f"TXT.rtf not found inside {filepath}")

    # .rtf, .doc, .docx - all supported by macOS textutil
    if ext in (".rtf", ".doc", ".docx"):
        return _extract_text_with_textutil(filepath)

    # .txt or other text files
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _extract_text_with_textutil(filepath: str) -> str:
    """Extract plain text from RTF/DOC/DOCX using macOS textutil."""
    try:
        result = subprocess.run(
            ["textutil", "-convert", "txt", "-stdout", filepath],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback for RTF: strip tags manually
    if filepath.lower().endswith((".rtf", ".rtfd")):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        text = re.sub(r'\\[a-z]+\d*\s?', '', content)
        text = re.sub(r'[{}]', '', text)
        return text.strip()

    raise RuntimeError(f"Could not extract text from {filepath}. textutil failed.")


def build_system_prompt(slug: str) -> str:
    """Build system prompt from template (instructions only, no transcript)."""
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    # Remove the TRANSCRIPT section from system prompt
    parts = template.split("## TRANSCRIPT")
    return parts[0].replace("{FILE_NAME}", slug)


def build_user_prompt(transcript: str) -> str:
    """Build user prompt containing only the transcript."""
    return f"以下のtranscriptを分析し、指示通りのJSON教材を生成してください。pure JSONのみ出力。\n\n---\n{transcript}\n---"


def build_translate_prompt(transcript: str) -> str:
    """Build translation prompt from template + transcript."""
    template = TRANSLATE_TEMPLATE.read_text(encoding="utf-8")
    return template.replace("{TRANSCRIPT_CONTENT}", transcript)


def call_claude_code(user_prompt: str, system_prompt: str = None) -> str:
    """Call Claude Code CLI with system prompt + user prompt via temp files."""
    import tempfile

    print("🤖 Đang gọi Claude Code CLI xử lý transcript...")
    print(f"   User prompt: {len(user_prompt):,} chars")
    if system_prompt:
        print(f"   System prompt: {len(system_prompt):,} chars")
    print("   (Có thể mất 5-10 phút tùy độ dài transcript)")

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    # Write user prompt to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(user_prompt)
        user_tmp = f.name

    # Build command
    cmd = f'cat "{user_tmp}" | claude -p --output-format text'
    if system_prompt:
        # Write system prompt to temp file and use --append-system-prompt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(system_prompt)
            sys_tmp = f.name
        cmd = f'cat "{user_tmp}" | claude -p --append-system-prompt "$(cat "{sys_tmp}")" --output-format text'

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=900,  # 15 min timeout
            env=env,
        )
    finally:
        os.unlink(user_tmp)
        if system_prompt:
            os.unlink(sys_tmp)

    if result.returncode != 0:
        print(f"❌ Claude Code error: {result.stderr}")
        raise Exception(f"Claude Code failed: {result.stderr}")

    return result.stdout


def extract_json(response: str) -> dict:
    """Extract JSON from Claude's response, handling various formats."""
    # Strategy 1: Try to parse directly
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip response to find JSON start/end
    stripped = response.strip()
    # Find the first { that could be JSON start
    first_brace = stripped.find('{')
    last_brace = stripped.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        json_str = stripped[first_brace:last_brace + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find JSON inside code blocks
    json_patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```json\s*(.*?)\s*```",
        r"```\s*\n(.*?)\n\s*```",
    ]
    for pattern in json_patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # Strategy 4: Try fixing excess closing braces
    if first_brace != -1 and last_brace > first_brace:
        json_str = stripped[first_brace:last_brace + 1]
        for excess_count in range(1, 5):
            try:
                return json.loads(json_str[:-excess_count])
            except json.JSONDecodeError:
                continue

    # If all patterns fail, print debug info
    print(f"⚠️  JSON extraction failed. Response length: {len(response)}")
    print(f"   First 500 chars: {response[:500]}")
    raise ValueError("Could not extract valid JSON from Claude's response")


def validate_data(data: dict) -> bool:
    """Basic validation of the generated data."""
    # Support both new (sentences) and old (vocabulary/phrases/grammar) schema
    if "sentences" in data:
        total = len(data["sentences"])
        print(f"📊 Trích xuất: {total} câu từ transcript")
    elif "vocabulary" in data:
        total = len(data.get("vocabulary", [])) + len(data.get("phrases", [])) + len(data.get("grammar", []))
        print(f"📊 Trích xuất: {len(data.get('vocabulary', []))} từ vựng, "
              f"{len(data.get('phrases', []))} cụm từ, "
              f"{len(data.get('grammar', []))} ngữ pháp")
    else:
        print("⚠️  Missing both 'sentences' and 'vocabulary' keys")
        return False

    if "exercises" not in data:
        print("⚠️  Missing 'exercises' key")
        return False

    ex = data.get("exercises", {})
    print(f"📝 Bài tập: {len(ex.get('translate_jv', []))} dịch J→V, "
          f"{len(ex.get('translate_vj', []))} dịch V→J, "
          f"{len(ex.get('fill_blank', []))} điền từ, "
          f"{len(ex.get('reorder', []))} sắp xếp")

    if total < 10:
        print(f"⚠️  Chỉ có {total} items, ít hơn mong đợi")
    return True


def update_index(meeting_data: dict, slug: str, date: str):
    """Update the index.json file with new meeting."""
    index_path = BASE_DIR / "data" / "index.json"

    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"meetings": [], "last_updated": ""}

    # Check if meeting already exists (by slug)
    existing = [m for m in index["meetings"] if m["id"] == slug]

    # Support both new and old schema
    if "sentences" in meeting_data:
        total_items = len(meeting_data["sentences"])
    else:
        total_items = (len(meeting_data.get("vocabulary", []))
                       + len(meeting_data.get("phrases", []))
                       + len(meeting_data.get("grammar", [])))

    meeting_entry = {
        "id": slug,
        "date": date,
        "topic": slug,
        "file": f"meetings/{slug}.json",
        "total_items": total_items,
        "sentence_count": len(meeting_data.get("sentences", [])),
    }

    if existing:
        index["meetings"] = [m if m["id"] != slug else meeting_entry for m in index["meetings"]]
    else:
        index["meetings"].append(meeting_entry)

    # Sort by date desc
    index["meetings"].sort(key=lambda m: m["date"], reverse=True)
    index["last_updated"] = datetime.now().isoformat()

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"📋 Updated index.json ({len(index['meetings'])} meetings)")


def git_push(slug: str):
    """Auto commit and push to GitHub."""
    try:
        os.chdir(BASE_DIR)
        subprocess.run(["git", "add", "data/"], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add meeting data: {slug}"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)
        print("✅ Git push thành công!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git push failed: {e}")
        print("   Bạn có thể push thủ công: git push")


def generate_translation(transcript: str, slug: str):
    """Generate Vietnamese translation markdown."""
    print("🌐 Đang tạo bản dịch tiếng Việt...")
    prompt = build_translate_prompt(transcript)
    response = call_claude_code(prompt)

    # Save translation
    output_file = TRANSLATIONS_DIR / f"{slug}.md"
    output_file.write_text(response, encoding="utf-8")
    print(f"📝 Bản dịch: {output_file}")
    return output_file


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

    # 2. Extract slug and date
    slug = extract_slug_from_filename(filepath)
    date = extract_date_from_filename(filepath)
    print(f"📅 Ngày: {date} | Slug: {slug}")

    # 3. Build prompt & call Claude (learning materials)
    system_prompt = build_system_prompt(slug)
    user_prompt = build_user_prompt(transcript)
    response = call_claude_code(user_prompt, system_prompt)

    # 4. Save raw response log
    log_file = LOG_DIR / f"{slug}_raw.txt"
    log_file.write_text(response, encoding="utf-8")

    # 5. Extract & validate JSON
    print("🔍 Đang parse JSON...")
    data = extract_json(response)
    data["date"] = date
    data["meeting_id"] = slug

    if not validate_data(data):
        print("❌ Validation failed. Kiểm tra log:", log_file)
        return False

    # 6. Save JSON (named by slug = original filename)
    output_file = DATA_DIR / f"{slug}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved: {output_file}")

    # 7. Update index
    update_index(data, slug, date)

    # 8. Generate translation (saved locally, gitignored)
    # TODO: tạm tắt, bật lại khi cần
    # generate_translation(transcript, slug)

    # 9. Git push (only data/, not translations/)
    if auto_push:
        git_push(slug)

    print(f"\n{'='*50}")
    print(f"✅ Hoàn tất! Data sẵn sàng trên app.")
    print(f"📝 Bản dịch: translations/{slug}.md")
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

    # Validate supported extensions
    ext = Path(filepath).suffix.lower()
    supported = (".txt", ".rtf", ".rtfd", ".doc", ".docx")
    if ext not in supported:
        print(f"❌ Unsupported file type: {ext}")
        print(f"   Supported: {', '.join(supported)}")
        sys.exit(1)

    # .rtfd is a directory - check for TXT.rtf inside
    if ext == ".rtfd":
        rtf_inside = os.path.join(filepath, "TXT.rtf")
        if not os.path.exists(rtf_inside):
            print(f"❌ TXT.rtf not found inside {filepath}")
            sys.exit(1)

    auto_push = "--no-push" not in sys.argv
    success = process(filepath, auto_push=auto_push)
    sys.exit(0 if success else 1)
