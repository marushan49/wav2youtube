# 🎵 WAV2YouTube

**Drop a WAV file → get it on YouTube.** One command. That's it.

```
wav2youtube song.wav "My Track"
```

## ⬇️ Download

**[Download wav2youtube.exe](../../releases/latest)** (Windows, no Python needed)

> Also works as Python script on Mac/Linux: `python wav2youtube.py song.wav`

---

## 🚀 How it works

1. **Normalizes** your audio to YouTube standard (-14 LUFS)
2. **Creates** a 1080p MP4 (black screen + high-quality audio)
3. **Uploads** directly to your YouTube channel

---

## 📖 Usage

```bash
# Simple — asks for title interactively
wav2youtube song.wav

# With title (default: unlisted)
wav2youtube song.wav "My Song Title"

# Public upload with description
wav2youtube song.wav "My Song" -p public -d "Check out my new track!"

# Keep the MP4 file locally
wav2youtube song.wav "My Song" --keep
```

### Options

- `-p` / `--privacy` → `unlisted` (default), `public`, or `private`
- `-d` / `--desc` → Video description
- `--keep` → Save the MP4 file after uploading

---

## ⚙️ First-Time Setup (2 minutes)

**You need two things:** ffmpeg + a YouTube API key.

### 1. Install ffmpeg

- **Windows:** [Download](https://www.gyan.dev/ffmpeg/builds/) → add to PATH
- **Mac:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

### 2. Get YouTube API access

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → search and enable **YouTube Data API v3**
3. Go to **Credentials** → Create **OAuth 2.0 Client ID** → type: Desktop
4. Download the JSON file
5. Rename it to `client_secret.json`
6. Put it in:
   - Windows: `C:\Users\YourName\.wav2youtube\client_secret.json`
   - Mac/Linux: `~/.wav2youtube/client_secret.json`

**First run** opens your browser to authorize. After that, it's automatic.

---

## 🛠 Build from source

```bash
pip install -r requirements.txt
pyinstaller --onefile wav2youtube.py
```

---

## License

MIT
