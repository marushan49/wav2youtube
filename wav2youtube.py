#!/usr/bin/env python3
"""
WAV2YouTube — GUI app. Drop a WAV, set title, click upload.
"""

import sys
import os
import subprocess
import tempfile
import pickle
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Fix for --windowed exe: subprocess needs explicit pipe handles
SUBPROCESS_KWARGS = {}
if sys.platform == "win32":
    SUBPROCESS_KWARGS["creationflags"] = subprocess.CREATE_NO_WINDOW
    SUBPROCESS_KWARGS["stdin"] = subprocess.DEVNULL


def config_dir():
    d = Path.home() / ".wav2youtube"
    d.mkdir(exist_ok=True)
    return d


def get_ffmpeg():
    """Find ffmpeg - PATH first, then same folder as exe."""
    # Check PATH
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True,
                       **SUBPROCESS_KWARGS)
        return "ffmpeg"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Check next to exe
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent

    for name in ["ffmpeg.exe", "ffmpeg"]:
        local = exe_dir / name
        if local.exists():
            return str(local)

    # Check subfolder ffmpeg/bin/
    for sub in ["ffmpeg/bin", "ffmpeg"]:
        local = exe_dir / sub / "ffmpeg.exe"
        if local.exists():
            return str(local)

    return None


def check_ffmpeg():
    path = get_ffmpeg()
    if path:
        return path
    return None


def normalize_audio(input_wav, output_wav, progress_cb=None, ffmpeg="ffmpeg"):
    import json

    if progress_cb:
        progress_cb("Normalizing audio...")

    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", input_wav,
         "-af", "loudnorm=I=-14:LRA=7:TP=-1:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True, **SUBPROCESS_KWARGS
    )

    json_start = result.stderr.rfind("{")
    json_end = result.stderr.rfind("}") + 1

    if json_start == -1:
        subprocess.run(
            [ffmpeg, "-y", "-hide_banner", "-i", input_wav,
             "-af", "loudnorm=I=-14:LRA=7:TP=-1",
             "-ar", "48000", output_wav],
            check=True, capture_output=True, **SUBPROCESS_KWARGS
        )
        return

    stats = json.loads(result.stderr[json_start:json_end])

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
        [ffmpeg, "-y", "-hide_banner", "-i", input_wav,
         "-af", af, "-ar", "48000", output_wav],
        check=True, capture_output=True, **SUBPROCESS_KWARGS
    )


def create_mp4(audio_path, output_mp4, progress_cb=None, ffmpeg="ffmpeg"):
    if progress_cb:
        progress_cb("Creating video...")

    subprocess.run(
        [ffmpeg, "-y", "-hide_banner",
         "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=1",
         "-i", audio_path,
         "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
         "-shortest", output_mp4],
        check=True, capture_output=True, **SUBPROCESS_KWARGS
    )


def get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    token_file = config_dir() / "token.pickle"
    client_secret = config_dir() / "client_secret.json"

    if not client_secret.exists():
        raise FileNotFoundError(
            f"client_secret.json not found!\n\n"
            f"Place it in:\n{config_dir()}\n\n"
            f"Get it from:\n"
            f"1. console.cloud.google.com\n"
            f"2. Enable YouTube Data API v3\n"
            f"3. Create OAuth Client (Desktop)\n"
            f"4. Download JSON → rename to client_secret.json"
        )

    creds = None
    if token_file.exists():
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=8090, prompt="consent")
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)

    return creds


def upload_to_youtube(mp4_path, title, description, privacy, progress_cb=None):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    if progress_cb:
        progress_cb("Authenticating...")

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

    if progress_cb:
        progress_cb("Uploading to YouTube...")

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status and progress_cb:
            progress_cb(f"Uploading... {int(status.progress() * 100)}%")

    return response["id"]


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WAV2YouTube")
        self.root.geometry("500x420")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        self.setup_ui()

    def setup_ui(self):
        bg = "#1a1a2e"
        fg = "#eaeaea"
        accent = "#e94560"
        entry_bg = "#16213e"
        btn_bg = "#0f3460"

        # Title
        tk.Label(self.root, text="🎵 WAV2YouTube", font=("Segoe UI", 20, "bold"),
                 bg=bg, fg=accent).pack(pady=(20, 5))
        tk.Label(self.root, text="Normalize & Upload to YouTube", font=("Segoe UI", 10),
                 bg=bg, fg="#888").pack(pady=(0, 20))

        # File selection
        file_frame = tk.Frame(self.root, bg=bg)
        file_frame.pack(fill="x", padx=30)

        tk.Label(file_frame, text="WAV File:", font=("Segoe UI", 10),
                 bg=bg, fg=fg).pack(anchor="w")

        file_row = tk.Frame(file_frame, bg=bg)
        file_row.pack(fill="x", pady=(2, 10))

        self.file_var = tk.StringVar()
        self.file_entry = tk.Entry(file_row, textvariable=self.file_var, font=("Segoe UI", 10),
                                   bg=entry_bg, fg=fg, insertbackground=fg, relief="flat", bd=5)
        self.file_entry.pack(side="left", fill="x", expand=True)

        tk.Button(file_row, text="Browse", command=self.browse_file,
                  bg=btn_bg, fg=fg, relief="flat", font=("Segoe UI", 9),
                  cursor="hand2", padx=10).pack(side="right", padx=(5, 0))

        # Title
        fields_frame = tk.Frame(self.root, bg=bg)
        fields_frame.pack(fill="x", padx=30)

        tk.Label(fields_frame, text="Title:", font=("Segoe UI", 10),
                 bg=bg, fg=fg).pack(anchor="w")
        self.title_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.title_var, font=("Segoe UI", 10),
                 bg=entry_bg, fg=fg, insertbackground=fg, relief="flat", bd=5).pack(fill="x", pady=(2, 10))

        # Description
        tk.Label(fields_frame, text="Description (optional):", font=("Segoe UI", 10),
                 bg=bg, fg=fg).pack(anchor="w")
        self.desc_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.desc_var, font=("Segoe UI", 10),
                 bg=entry_bg, fg=fg, insertbackground=fg, relief="flat", bd=5).pack(fill="x", pady=(2, 10))

        # Privacy
        privacy_frame = tk.Frame(fields_frame, bg=bg)
        privacy_frame.pack(fill="x", pady=(0, 15))
        tk.Label(privacy_frame, text="Privacy:", font=("Segoe UI", 10),
                 bg=bg, fg=fg).pack(side="left")

        self.privacy_var = tk.StringVar(value="unlisted")
        for val in ["unlisted", "public", "private"]:
            tk.Radiobutton(privacy_frame, text=val.capitalize(), variable=self.privacy_var,
                           value=val, bg=bg, fg=fg, selectcolor=entry_bg,
                           activebackground=bg, activeforeground=fg,
                           font=("Segoe UI", 9)).pack(side="left", padx=(10, 0))

        # Upload button
        self.upload_btn = tk.Button(self.root, text="🚀 Upload to YouTube",
                                    command=self.start_upload,
                                    bg=accent, fg="white", relief="flat",
                                    font=("Segoe UI", 12, "bold"),
                                    cursor="hand2", padx=20, pady=8)
        self.upload_btn.pack(pady=(5, 10))

        # Status
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(self.root, textvariable=self.status_var,
                                     font=("Segoe UI", 9), bg=bg, fg="#888")
        self.status_label.pack(pady=(0, 5))

        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode="indeterminate", length=300)
        self.progress.pack(pady=(0, 10))

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select WAV file",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if path:
            self.file_var.set(path)
            if not self.title_var.get():
                self.title_var.set(Path(path).stem)

    def set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def start_upload(self):
        wav = self.file_var.get().strip()
        title = self.title_var.get().strip()

        if not wav:
            messagebox.showerror("Error", "Please select a WAV file.")
            return
        if not os.path.isfile(wav):
            messagebox.showerror("Error", f"File not found:\n{wav}")
            return
        if not title:
            messagebox.showerror("Error", "Please enter a title.")
            return

        self.ffmpeg_path = check_ffmpeg()
        if not self.ffmpeg_path:
            messagebox.showerror("Error",
                                 "ffmpeg not found!\n\n"
                                 "Either:\n"
                                 "• Install ffmpeg and add to PATH\n"
                                 "• Or put ffmpeg.exe in the same folder as wav2youtube.exe\n\n"
                                 "Download: https://ffmpeg.org/download.html")
            return

        self.upload_btn.configure(state="disabled")
        self.progress.start(10)

        thread = threading.Thread(target=self.do_upload, daemon=True)
        thread.start()

    def do_upload(self):
        try:
            wav = self.file_var.get().strip()
            title = self.title_var.get().strip()
            desc = self.desc_var.get().strip()
            privacy = self.privacy_var.get()

            with tempfile.TemporaryDirectory() as tmpdir:
                basename = Path(wav).stem
                norm_wav = os.path.join(tmpdir, f"{basename}_norm.wav")
                mp4 = os.path.join(tmpdir, f"{basename}.mp4")

                normalize_audio(wav, norm_wav, self.set_status, self.ffmpeg_path)
                self.set_status("✅ Normalized!")

                create_mp4(norm_wav, mp4, self.set_status, self.ffmpeg_path)
                self.set_status("✅ Video created!")

                video_id = upload_to_youtube(mp4, title, desc, privacy, self.set_status)

            url = f"https://youtube.com/watch?v={video_id}"
            self.root.after(0, lambda: self.upload_done(url))

        except Exception as e:
            self.root.after(0, lambda: self.upload_failed(str(e)))

    def upload_done(self, url):
        self.progress.stop()
        self.upload_btn.configure(state="normal")
        self.set_status(f"✅ Done! {url}")
        messagebox.showinfo("Success! 🎉",
                            f"Video uploaded!\n\n{url}\n\n"
                            f"(Link copied to clipboard)")
        self.root.clipboard_clear()
        self.root.clipboard_append(url)

    def upload_failed(self, error):
        self.progress.stop()
        self.upload_btn.configure(state="normal")
        self.set_status("❌ Failed")
        messagebox.showerror("Upload Failed", error)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
