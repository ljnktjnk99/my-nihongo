#!/usr/bin/env python3
"""
Polling file watcher - monitors Meeting/ folder for new transcript files.
No external dependencies. Polls every 10 seconds.

Usage: python processor/watcher.py
       (normally started via launchd)
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
MEETING_DIR = BASE_DIR / "Meeting"
PROCESSOR = Path(__file__).parent / "process_transcript.py"
VENV_PYTHON = BASE_DIR / "venv" / "bin" / "python"
LOG_DIR = Path(__file__).parent / "logs"
PROCESSED_LOG = LOG_DIR / "processed.txt"

POLL_INTERVAL = 10  # seconds
SUPPORTED_EXTENSIONS = {".txt", ".rtf", ".rtfd", ".doc", ".docx"}


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def load_processed():
    if PROCESSED_LOG.exists():
        lines = PROCESSED_LOG.read_text(encoding="utf-8").strip()
        return set(lines.split("\n")) if lines else set()
    return set()


def mark_processed(filepath_str):
    with open(PROCESSED_LOG, "a", encoding="utf-8") as f:
        f.write(filepath_str + "\n")


def scan_meeting_dir():
    """Return list of supported transcript files in Meeting/ folder."""
    found = []
    try:
        for entry in os.scandir(MEETING_DIR):
            name = entry.name
            if name.startswith(".") or name.startswith("~"):
                continue
            suffix = Path(name).suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                continue
            if suffix == ".rtfd":
                # .rtfd is a macOS directory bundle
                if entry.is_dir() and (Path(entry.path) / "TXT.rtf").exists():
                    found.append(Path(entry.path))
            elif entry.is_file():
                found.append(Path(entry.path))
    except FileNotFoundError:
        log(f"Warning: Meeting directory not found: {MEETING_DIR}")
    return found


def run_processor(filepath):
    """Run process_transcript.py on the given file. Returns True on success."""
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    log(f"Processing: {filepath.name}")
    try:
        result = subprocess.run(
            [python, str(PROCESSOR), str(filepath)],
            cwd=str(BASE_DIR),
            env=env,
            timeout=600,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"Timeout processing: {filepath.name}")
        return False
    except Exception as e:
        log(f"Error: {e}")
        return False


def main():
    MEETING_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    processed = load_processed()
    log(f"Watcher started. Polling every {POLL_INTERVAL}s.")
    log(f"Watching: {MEETING_DIR}")
    log(f"Already processed: {len(processed)} file(s)")

    while True:
        candidates = scan_meeting_dir()
        for path in candidates:
            key = str(path)
            if key not in processed:
                success = run_processor(path)
                if success:
                    processed.add(key)
                    mark_processed(key)
                    log(f"Completed: {path.name}")
                else:
                    log(f"Failed (will retry next cycle): {path.name}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
