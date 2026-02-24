#!/usr/bin/env python3
"""
File watcher - monitors Meeting/ folder for new transcript files.
Auto-processes them with Claude Code CLI and pushes to GitHub.

Usage: python watcher.py
"""

import time
import sys
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

BASE_DIR = Path(__file__).parent.parent
MEETING_DIR = BASE_DIR / "Meeting"
PROCESSOR = Path(__file__).parent / "process_transcript.py"
PROCESSED_LOG = Path(__file__).parent / "logs" / "processed.txt"


def get_processed_files():
    if PROCESSED_LOG.exists():
        return set(PROCESSED_LOG.read_text().strip().split("\n"))
    return set()


def mark_processed(filepath):
    PROCESSED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_LOG, "a") as f:
        f.write(filepath + "\n")


class TranscriptHandler(FileSystemEventHandler):
    def __init__(self):
        self.processed = get_processed_files()

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_file(event.src_path)

    def _handle_file(self, filepath):
        path = Path(filepath)
        if path.suffix.lower() not in [".txt", ".docx"]:
            return
        if path.name.startswith(".") or path.name.startswith("~"):
            return
        if str(path) in self.processed:
            return

        time.sleep(2)  # Wait for file to finish writing

        print(f"\n🆕 Phát hiện file mới: {path.name}")
        print(f"⏳ Bắt đầu xử lý...")

        try:
            result = subprocess.run(
                [sys.executable, str(PROCESSOR), str(path)],
                cwd=str(BASE_DIR),
                timeout=600,
            )
            if result.returncode == 0:
                self.processed.add(str(path))
                mark_processed(str(path))
                print(f"✅ Xử lý xong: {path.name}")
            else:
                print(f"❌ Lỗi xử lý: {path.name}")
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout khi xử lý: {path.name}")
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    MEETING_DIR.mkdir(parents=True, exist_ok=True)
    print(f"""
╔══════════════════════════════════════════════╗
║  🎌 NihonGo Meeting - File Watcher          ║
║  Đang theo dõi: ~/nihongo-meeting/Meeting/   ║
║  Bỏ file .txt vào folder trên để xử lý      ║
║  Ctrl+C để dừng                              ║
╚══════════════════════════════════════════════╝
    """)

    handler = TranscriptHandler()

    # Process existing unprocessed files
    for f in MEETING_DIR.glob("*.txt"):
        if str(f) not in handler.processed:
            print(f"📄 Tìm thấy file chưa xử lý: {f.name}")
            handler._handle_file(str(f))

    observer = Observer()
    observer.schedule(handler, str(MEETING_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Đã dừng watcher.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
