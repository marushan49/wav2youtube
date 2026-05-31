# 🎵 WAV2YouTube

**Drop a WAV → click Upload → it's on YouTube.** Simple GUI, no terminal needed.

![wav2youtube](https://img.shields.io/badge/Windows-exe-blue?style=for-the-badge&logo=windows)

## ⬇️ Download

**[Download wav2youtube.exe](../../releases/latest)** — No Python needed, just run it.

---

## 🖥️ How it looks

1. Click **Browse** → pick your WAV
2. Enter a **title**
3. Click **🚀 Upload to YouTube**
4. Done! Link gets copied to clipboard.

> Default privacy: **Unlisted** (only people with the link can see it)

---

## What it does

1. **Normalizes** audio to -14 LUFS (YouTube loudness standard)
2. **Creates** 1080p MP4 (black screen + high-quality AAC audio)
3. **Uploads** directly to YouTube

---

## ⚙️ First-Time Setup (2 minutes)

### 1. Install ffmpeg

- **Windows:** [Download ffmpeg](https://www.gyan.dev/ffmpeg/builds/) → extract → add `bin/` folder to PATH
- Quick test: open CMD, type `ffmpeg -version`

### 2. YouTube API access

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable **YouTube Data API v3**
3. Credentials → **OAuth 2.0 Client ID** → Desktop App
4. Download JSON → rename to `client_secret.json`
5. Put in: `C:\Users\YourName\.wav2youtube\client_secret.json`

First upload opens your browser once to authorize. After that it's automatic forever.

---

## 🛠️ Build from source

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name wav2youtube wav2youtube.py
```

`--windowed` = no console window behind the GUI.

---

## License

MIT
