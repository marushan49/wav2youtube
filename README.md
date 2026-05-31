# WAV2YouTube

Normalize a WAV file and upload it to YouTube — as a standalone `.exe` (Windows) or CLI tool.

## Features
- 🔊 **EBU R128 normalization** to -14 LUFS (YouTube standard)
- 🎬 **Auto-generates MP4** (1080p black + AAC 320kbps)
- 🚀 **Direct YouTube upload** via OAuth2
- 📦 **Single .exe** — no Python install needed

## Download

Grab the latest `wav2youtube.exe` from [**Releases**](../../releases/latest).

## Prerequisites

- **ffmpeg** must be installed and in your PATH
  - Windows: Download from https://ffmpeg.org/download.html, add to PATH
  - Linux/Mac: `sudo apt install ffmpeg` / `brew install ffmpeg`

## First-Time Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a project → Enable **YouTube Data API v3**
3. Create **OAuth 2.0 Client ID** (type: Desktop App)
4. Download the JSON → rename to `client_secret.json`
5. Place it in `~/.wav2youtube/client_secret.json`
   - Windows: `C:\Users\YourName\.wav2youtube\client_secret.json`

On first run, a browser opens for YouTube authorization. Token is cached for future use.

## Usage

```bash
wav2youtube track.wav "My Song Title"
wav2youtube track.wav "My Song" -d "Song description" -p unlisted
wav2youtube track.wav "My Song" --keep-mp4
```

### Options
| Flag | Description |
|------|-------------|
| `-d`, `--description` | Video description |
| `-p`, `--privacy` | `public` (default), `unlisted`, or `private` |
| `--keep-mp4` | Keep the generated MP4 file |

## Build from Source

```bash
pip install -r requirements.txt
pyinstaller --onefile wav2youtube.py
# Output: dist/wav2youtube.exe
```

## License

MIT
