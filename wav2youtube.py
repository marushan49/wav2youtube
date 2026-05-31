#!/usr/bin/env python3
"""
WAV2YouTube — Drop a WAV, get it on YouTube. That's it.
"""

import sys
import os
import subprocess
import tempfile
import pickle
import argparse
from pathlib import Path


def config_dir():
    d = Path.home() / ".wav2youtube"
    d.mkdir(exist_ok=True)
    return d


def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ ffmpeg not found!")
        print("   Download: https://ffmpeg.org/download.html")
        print("   Make sure it's in your PATH.")
        sys.exit(1)


def normalize_audio(input_wav, output_wav):
    """Two-pass EBU R128 normalization to -14 LUFS."""
    import json

    print("\n  🔊 Normalizing audio...")

    # Pass 1: Measure
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", input_wav,
         "-af", "loudnorm=I=-14:LRA=7:TP=-1:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True
    )

    json_start = result.stderr.rfind("{")
    json_end = result.stderr.rfind("}") + 1

    if json_start == -1:
        # Fallback: single-pass
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-i", input_wav,
             "-af", "loudnorm=I=-14:LRA=7:TP=-1",
             "-ar", "48000", output_wav],
            check=True, capture_output=True
        )
        return

    stats = json.loads(result.stderr[json_start:json_end])

    # Pass 2: Apply
    af = (
        f"loudnorm=I=-14:LRA=7:TP=-1:"
        f"measured_I={stats['input_i']}:"
        f"measured_LRA={stats['input_lra']}:"
        f"measured_TP={stats['input_tp']}:"
        f"measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}:"
        f"linear=true"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-i", input_wav,
         "-af", af, "-ar", "48000", output_wav],
        check=True, capture_output=True
    )
    print("  ✅ Done")


def create_mp4(audio_path, output_mp4):
    """Black 1080p video + AAC 320k audio."""
    print("  🎬 Creating video...")
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner",
         "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=1",
         "-i", audio_path,
         "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
         "-shortest", output_mp4],
        check=True, capture_output=True
    )
    print("  ✅ Done")


def get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    token_file = config_dir() / "token.pickle"
    client_secret = config_dir() / "client_secret.json"

    if not client_secret.exists():
        print("\n  ⚙️  One-time setup needed!")
        print(f"  Place client_secret.json in: {config_dir()}")
        print()
        print("  How to get it (takes 2 min):")
        print("  1. https://console.cloud.google.com → Create project")
        print("  2. Enable 'YouTube Data API v3'")
        print("  3. Credentials → OAuth 2.0 → Desktop App")
        print("  4. Download JSON → rename to client_secret.json")
        sys.exit(1)

    creds = None
    if token_file.exists():
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("\n  🔑 Opening browser for YouTube login...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=8090, prompt="consent")
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)

    return creds


def upload(mp4_path, title, description, privacy):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "10",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(mp4_path, mimetype="video/mp4", resumable=True, chunksize=10 * 1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("  🚀 Uploading...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"     {pct}%", end="\r")

    video_id = response["id"]
    url = f"https://youtube.com/watch?v={video_id}"
    print(f"  ✅ Live at: {url}")
    return url


def main():
    parser = argparse.ArgumentParser(
        prog="wav2youtube",
        description="Drop a WAV → get it on YouTube.",
    )
    parser.add_argument("wav", help="WAV file to upload")
    parser.add_argument("title", nargs="?", help="Video title (asks interactively if omitted)")
    parser.add_argument("-d", "--desc", default="", help="Description (optional)")
    parser.add_argument("-p", "--privacy", choices=["public", "unlisted", "private"],
                        default="unlisted", help="Privacy (default: unlisted)")
    parser.add_argument("--keep", action="store_true", help="Keep the MP4 file")

    # If no args (double-click on exe), go interactive
    if len(sys.argv) == 1:
        print("╭─────────────────────────────────────╮")
        print("│  🎵 WAV2YouTube                     │")
        print("╰─────────────────────────────────────╯")
        print()
        wav_path = input("  WAV file (drag & drop or type path): ").strip().strip('"').strip("'")
        if not wav_path:
            print("  ❌ No file provided.")
            return
        title = input("  Video title: ").strip()
        if not title:
            title = Path(wav_path).stem
        privacy = input("  Privacy [unlisted/public/private] (Enter=unlisted): ").strip().lower()
        if privacy not in ("public", "unlisted", "private"):
            privacy = "unlisted"
        desc = input("  Description (Enter=skip): ").strip()

        args_ns = argparse.Namespace(wav=wav_path, title=title, privacy=privacy, desc=desc, keep=False)
    else:
        args_ns = parser.parse_args()

    args = args_ns

    if not os.path.isfile(args.wav):
        print(f"❌ File not found: {args.wav}")
        sys.exit(1)

    check_ffmpeg()

    title = args.title if args.title else Path(args.wav).stem

    print(f"\n╭─────────────────────────────────────╮")
    print(f"│  WAV2YouTube                        │")
    print(f"├─────────────────────────────────────┤")
    print(f"│  File:    {Path(args.wav).name[:25]:<25} │")
    print(f"│  Title:   {title[:25]:<25} │")
    print(f"│  Privacy: {args.privacy:<25} │")
    print(f"╰─────────────────────────────────────╯")

    with tempfile.TemporaryDirectory() as tmpdir:
        basename = Path(args.wav).stem
        norm_wav = os.path.join(tmpdir, f"{basename}_norm.wav")
        mp4 = os.path.join(tmpdir, f"{basename}.mp4")

        normalize_audio(args.wav, norm_wav)
        create_mp4(norm_wav, mp4)

        if args.keep:
            out = str(Path(args.wav).parent / f"{basename}.mp4")
            import shutil
            shutil.copy2(mp4, out)
            print(f"  📁 Saved: {out}")
            upload(out, title, args.desc, args.privacy)
        else:
            upload(mp4, title, args.desc, args.privacy)

    print("\n  🎉 All done!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Abgebrochen.")
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        print(f"     Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    finally:
        print()
        input("  Press Enter to close...")
