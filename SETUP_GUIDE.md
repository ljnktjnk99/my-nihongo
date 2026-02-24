# 🎌 NihonGo Meeting - Hướng dẫn Setup

## Tổng quan

```
📁 ~/nihongo-meeting/
├── processor/              ← Chạy trên máy công ty (macOS)
│   ├── process_transcript.py   ← Script gọi Claude Code xử lý
│   ├── prompt_template.md      ← Prompt cho Claude Code
│   └── watcher.py              ← File watcher tự động
├── pwa/                    ← PWA (deploy lên GitHub Pages)
│   ├── index.html
│   ├── js/app.js
│   ├── js/db.js
│   ├── js/srs.js
│   ├── manifest.json
│   └── sw.js
├── data/                   ← Data generated (git tracked)
│   ├── meetings/
│   │   └── 2025-02-20.json
│   └── index.json
├── scripts/
│   └── setup.sh            ← Script setup 1 lần
├── Meeting/                ← BỎ FILE TRANSCRIPT VÀO ĐÂY
└── .github/workflows/
    └── pages.yml
```

---

## Bước 1: Tạo GitHub Repo

### 1.1 Tạo repo trên GitHub
1. Mở https://github.com/new
2. Repository name: `nihongo-meeting`
3. Chọn **Private**
4. Bấm **Create repository**

### 1.2 Clone về máy công ty
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/nihongo-meeting.git
cd nihongo-meeting
```

### 1.3 Copy tất cả file từ project này vào
(Sau khi download các file tôi tạo)
```bash
# Copy toàn bộ cấu trúc vào repo
cp -r /path/to/downloaded/files/* ~/nihongo-meeting/

# Tạo folder cho transcript
mkdir -p ~/nihongo-meeting/Meeting

# Commit lần đầu
git add .
git commit -m "Initial setup"
git push origin main
```

### 1.4 Enable GitHub Pages
1. Vào repo trên GitHub → **Settings** → **Pages**
2. Source: chọn **GitHub Actions**
3. Sau khi push, PWA sẽ tự deploy tại:
   `https://YOUR_USERNAME.github.io/nihongo-meeting/`

---

## Bước 2: Cài đặt trên máy công ty (macOS)

### 2.1 Cài Python dependencies
```bash
cd ~/nihongo-meeting
python3 -m venv venv
source venv/bin/activate
pip install watchdog
```

### 2.2 Kiểm tra Claude Code CLI
```bash
# Kiểm tra Claude Code đã cài chưa
claude --version

# Nếu chưa, cài theo hướng dẫn công ty
```

### 2.3 Test thử xử lý 1 file
```bash
cd ~/nihongo-meeting

# Bỏ 1 file transcript test vào folder Meeting/
# Ví dụ: Meeting/2025-02-24_sprint_review.txt

# Chạy processor
source venv/bin/activate
python processor/process_transcript.py Meeting/2025-02-24_sprint_review.txt
```

Nếu thành công, sẽ thấy file `data/meetings/2025-02-24.json` được tạo.

---

## Bước 3: Chạy File Watcher (tự động)

### 3.1 Chạy thủ công
```bash
cd ~/nihongo-meeting
source venv/bin/activate
python processor/watcher.py
```
→ Giờ chỉ cần bỏ file vào `Meeting/` là tự xử lý + push.

### 3.2 Chạy tự động khi mở máy (khuyến khích)
```bash
# Tạo LaunchAgent để tự chạy khi login
cp scripts/com.nihongo.watcher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.nihongo.watcher.plist
```

---

## Bước 4: Mở PWA trên điện thoại

1. Mở Safari/Chrome trên điện thoại
2. Truy cập: `https://YOUR_USERNAME.github.io/nihongo-meeting/`
3. **iPhone**: Bấm Share → "Add to Home Screen"
4. **Android**: Bấm menu ⋮ → "Add to Home Screen"
5. Done! App xuất hiện trên màn hình chính 🎉

---

## Workflow hàng ngày

```
🖥️  Sau cuộc họp:
    1. Download transcript từ Teams
    2. Kéo file vào ~/nihongo-meeting/Meeting/
    3. (Tự động) Watcher detect → Claude Code xử lý → Git push

📱  Lúc rảnh (tàu điện, nghỉ trưa, ...):
    1. Mở app NihonGo Meeting
    2. Pull data mới (nút refresh)
    3. Học flashcard + luyện tập
```

---

## Troubleshooting

### Q: Watcher không detect file?
```bash
# Check watcher đang chạy không
ps aux | grep watcher.py

# Restart
python processor/watcher.py
```

### Q: Git push bị lỗi?
```bash
# Setup credential 1 lần
git config --global credential.helper osxkeychain
# Hoặc dùng SSH key
```

### Q: PWA không update data mới?
- Pull-to-refresh trên app
- Hoặc: Settings → Clear Cache trong app

### Q: Claude Code bị lỗi xử lý?
- Check file transcript có đúng format không
- Xem log: `tail -f processor/logs/latest.log`
