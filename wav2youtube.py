#!/usr/bin/env python3
"""
WAV2YouTube — Normalize a WAV file and upload to YouTube as MP4.
Compiles to standalone .exe via PyInstaller.
"""

import sys
import os
import subprocess
import tempfile
import pickle
import argparse
from pathlib import Path

def get_config_dir():
    """Config dir for tokens."""
    d = Path.home() / ".wav2youtube"
    d.mkdir(exist_ok=True)
    return d

def check_ffmpeg():
    """Ensure ffmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ ffmpeg not found! Install from https://ffmpeg.org/download.html")
        print("   Make sure ffmpeg.exe is in your PATH.")
        sys.exit(1)

def normalize_audio(input_wav, output_wav):
    """Normalize WAV to -14 LUFS (YouTube standard) using ffmpeg loudnorm."""
    print("🔊 Analyzing loudness...")
    
    # First pass: measure
    cmd_measure = [
        "ffmpeg", "-hide_banner", "-i", input_wav,
        "-af", "loudnorm=I=-14:LRA=7:TP=-1:print_format=json",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd_measure, capture_output=True, text=True)
    stderr = result.stderr
    
    # Parse loudnorm stats from stderr
    import json
    json_start = stderr.rfind("{")
    json_end = stderr.rfind("}") + 1
    if json_start == -1:
        print("⚠️  Could not parse loudness stats, using single-pass normalization")
        cmd_single = [
            "ffmpeg", "-y", "-hide_banner", "-i", input_wav,
            "-af", "loudnorm=I=-14:LRA=7:TP=-1",
            "-ar", "48000", output_wav
        ]
        subprocess.run(cmd_single, check=True, capture_output=True)
        return

    stats = json.loads(stderr[json_start:json_end])
    
    # Second pass: apply
    print("🔊 Normalizing to -14 LUFS...")
    af = (
        f"loudnorm=I=-14:LRA=7:TP=-1:"
        f"measured_I={stats['input_i']}:"
        f"measured_LRA={stats['input_lra']}:"
        f"measured_TP={stats['input_tp']}:"
        f"measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}:"
        f"linear=true"
    )
    cmd_apply = [
        "ffmpeg", "-y", "-hide_banner", "-i", input_wav,
        "-af", af, "-ar", "48000", output_wav
    ]
    subprocess.run(cmd_apply, check=True, capture_output=True)
    print("✅ Normalized!")

def create_mp4(audio_path, output_mp4):
    """Create MP4 with black screen + audio."""
    print("🎬 Creating MP4...")
    cmd = [
        "ffmpeg", "-y", "-hide_banner",
        "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=1",
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-shortest",
        output_mp4
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print("✅ MP4 created!")

def get_youtube_credentials():
    """Get or refresh YouTube OAuth2 credentials."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    config_dir = get_config_dir()
    token_file = config_dir / "token.pickle"
    client_secret = config_dir / "client_secret.json"

    if not client_secret.exists():
        print(f"❌ OAuth client secret not found!")
        print(f"   Place your client_secret.json in: {client_secret}")
        print()
        print("   To get one:")
        print("   1. Go to https://console.cloud.google.com/apis/credentials")
        print("   2. Create OAuth 2.0 Client ID (Desktop App)")
        print("   3. Download JSON → rename to client_secret.json")
        print("   4. Enable 'YouTube Data API v3' in your project")
        sys.exit(1)

    creds = None
    if token_file.exists():
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing token...")
            creds.refresh(Request())
        else:
            print("🔑 First-time login — YouTube authorization required...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            try:
                creds = flow.run_local_server(port=8090, prompt="consent", open_browser=False)
            except Exception:
                creds = flow.run_console()
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)
        print("✅ Authenticated!")

    return creds

def upload_to_youtube(mp4_path, title, description, privacy="public"):
    """Upload MP4 to YouTube."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = get_youtube_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "10",  # Music
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(mp4_path, mimetype="video/mp4", resumable=True, chunksize=10*1024*1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("🚀 Uploading to YouTube...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   {int(status.progress() * 100)}% uploaded")

    video_id = response["id"]
    url = f"https://youtube.com/watch?v={video_id}"
    print(f"✅ Upload complete! {url}")
    return url

def main():
    parser = argparse.ArgumentParser(
        description="WAV2YouTube — Normalize WAV & upload to YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wav2youtube track.wav "My Song" 
  wav2youtube track.wav "My Song" -d "Description" -p unlisted
  wav2youtube track.wav "My Song" --keep-mp4

First run: place client_secret.json in ~/.wav2youtube/
Get it from: https://console.cloud.google.com/apis/credentials
        """
    )
    parser.add_argument("wav_file", help="Input WAV file path")
    parser.add_argument("title", help="YouTube video title")
    parser.add_argument("-d", "--description", default="", help="Video description")
    parser.add_argument("-p", "--privacy", choices=["public", "unlisted", "private"], default="public")
    parser.add_argument("--keep-mp4", action="store_true", help="Keep the MP4 file after upload")
    
    args = parser.parse_args()

    # Validate input
    if not os.path.isfile(args.wav_file):
        print(f"❌ File not found: {args.wav_file}")
        sys.exit(1)

    check_ffmpeg()

    # Work in temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        basename = Path(args.wav_file).stem
        normalized_wav = os.path.join(tmpdir, f"{basename}_norm.wav")
        mp4_file = os.path.join(tmpdir, f"{basename}.mp4")

        # Process
        normalize_audio(args.wav_file, normalized_wav)
        create_mp4(normalized_wav, mp4_file)
        
        if args.keep_mp4:
            output_path = str(Path(args.wav_file).parent / f"{basename}.mp4")
            import shutil
            shutil.copy2(mp4_file, output_path)
            print(f"📁 MP4 saved: {output_path}")
            upload_to_youtube(output_path, args.title, args.description, args.privacy)
        else:
            upload_to_youtube(mp4_file, args.title, args.description, args.privacy)

    print("🎉 Done!")

if __name__ == "__main__":
    main()
