"""
modern_lyrics_downloader.py - Sonance Modern Desktop Application (v2.1)

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (c) 2024-2026 Sandeep Khadka — MIT License

Features:
- Native Windows Desktop Window (powered by pywebview & Windows WebView2)
- Built-in HTTP Audio Streaming Server with Byte-Range Scrubbing
- Real-time Karaoke Sync & In-App Music Player
- Spek-style Audio Quality & Spectrogram Inspector
- Full-Height Artist & Album Browser with Instant Search
- Direct LRCLIB & Genius Integration
- In-App GitHub Update Checker
"""

import os
import sys
import json
import re
import mimetypes
import socket
import threading
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, List
import requests
import webview

import lyrics_engine
import downloader_engine

APP_VERSION = "2.1.0"
GITHUB_REPO = "Sandeep2062/Sonance"
APP_DIR = Path(__file__).parent.resolve()
UI_PATH = APP_DIR / "ui" / "index.html"
CONFIG_FILE = APP_DIR / "lyrics_gui_config.json"


# ------------------ Local Audio Streaming Server ------------------

def find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port

STREAM_PORT = find_free_port()


class AudioStreamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress console clutter

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/stream":
            self.handle_audio_stream(qs)
        elif parsed.path == "/cover":
            self.handle_cover_art(qs)
        else:
            self.send_response(404)
            self.end_headers()

    def handle_cover_art(self, qs):
        path_list = qs.get("path", [])
        if not path_list:
            self.send_response(400)
            self.end_headers()
            return

        file_path = path_list[0]
        if not os.path.exists(file_path):
            self.send_response(404)
            self.end_headers()
            return

        image_data = None
        if lyrics_engine.HAS_TINYTAG:
            try:
                from tinytag import TinyTag
                tag = TinyTag.get(file_path, image=True)
                image_data = tag.get_image()
            except Exception:
                pass

        if image_data:
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(image_data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(image_data)
        else:
            self.send_response(404)
            self.end_headers()

    def handle_audio_stream(self, qs):
        path_list = qs.get("path", [])
        if not path_list:
            self.send_response(400)
            self.end_headers()
            return

        file_path = path_list[0]
        if not os.path.exists(file_path):
            self.send_response(404)
            self.end_headers()
            return

        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "audio/mpeg"

        range_header = self.headers.get("Range")
        if range_header:
            # Handle HTTP 206 Partial Content for instant seeking
            match = re.search(r"bytes=(\d+)-(\d*)", range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                with open(file_path, "rb") as f:
                    f.seek(start)
                    bytes_left = length
                    while bytes_left > 0:
                        chunk_size = min(bytes_left, 64 * 1024)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        bytes_left -= len(chunk)
                return

        # Full content
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)


def start_audio_server():
    server = HTTPServer(("127.0.0.1", STREAM_PORT), AudioStreamHandler)
    server.serve_forever()

threading.Thread(target=start_audio_server, daemon=True).start()


# ------------------ Desktop API Bridge ------------------

class LyricsAPI:
    def __init__(self):
        self._window: Optional[webview.Window] = None
        self._current_folder: str = ""
        self._tracks: List[Dict[str, Any]] = []

    def set_window(self, window: webview.Window):
        self._window = window

    def select_folder(self) -> str:
        """Opens native OS folder picker without deprecation warnings."""
        if not self._window:
            return ""

        # pywebview 5+ uses FileDialog.FOLDER, fallback to FOLDER_DIALOG
        dialog_type = getattr(webview.FileDialog, "FOLDER", getattr(webview, "FOLDER_DIALOG", None))
        result = self._window.create_file_dialog(dialog_type)
        if result and len(result) > 0:
            folder = result[0]
            self._current_folder = folder
            self._save_last_folder(folder)
            return folder
        return ""

    def get_last_folder(self) -> str:
        """Loads last opened folder from config."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("music_dir", "")
            except Exception:
                pass
        return ""

    def scan_library(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scans directory for audio tracks, detects LRC status and technical audio quality."""
        target_dir = folder or self._current_folder
        if not target_dir or not os.path.exists(target_dir):
            return []

        self._current_folder = target_dir
        tracks = []
        idx = 0
        audio_exts = (".mp3", ".flac", ".m4a", ".ogg", ".wav")

        for root, _, files in os.walk(target_dir):
            for f in sorted(files):
                if f.lower().endswith(audio_exts):
                    full_path = os.path.join(root, f)
                    lrc_path = os.path.splitext(full_path)[0] + ".lrc"

                    state = "none"
                    if os.path.exists(lrc_path):
                        try:
                            with open(lrc_path, "r", encoding="utf-8", errors="ignore") as lf:
                                content = lf.read()
                            state = lyrics_engine.analyze_lrc_content(content)
                        except Exception:
                            state = "none"

                    # Get metadata (ID3 / Tag / Technical Specs)
                    meta = lyrics_engine.get_audio_metadata(full_path)
                    fn_artist, fn_title = lyrics_engine.clean_filename_to_artist_title(f)

                    # Inferred artist & album from standard folder structure
                    inferred_artist = ""
                    inferred_album = ""
                    try:
                        rel = os.path.relpath(full_path, target_dir)
                        parts = rel.split(os.sep)
                        if len(parts) >= 2:
                            inferred_artist = parts[0]
                        if len(parts) >= 3:
                            inferred_album = parts[1]
                    except Exception:
                        pass

                    artist = meta["artist"] or fn_artist or inferred_artist or "Unknown"
                    title = meta["title"] or fn_title or f
                    album = meta["album"] or inferred_album or "Unknown Album"

                    # Stream URL for player
                    stream_url = f"http://127.0.0.1:{STREAM_PORT}/stream?path={urllib.parse.quote(full_path)}"
                    cover_url = f"http://127.0.0.1:{STREAM_PORT}/cover?path={urllib.parse.quote(full_path)}"

                    tracks.append({
                        "index": idx,
                        "filename": f,
                        "path": full_path,
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "duration": meta["duration"],
                        "quality": meta["quality"],
                        "bitrate": meta["bitrate"],
                        "samplerate": meta["samplerate"],
                        "bitdepth": meta["bitdepth"],
                        "format": meta["format"],
                        "state": state,
                        "stream_url": stream_url,
                        "cover_url": cover_url,
                        "checked": False,
                    })
                    idx += 1

        self._tracks = tracks
        return tracks

    def rescan_library(self) -> List[Dict[str, Any]]:
        """Rescans current folder."""
        return self.scan_library(self._current_folder)

    def download_track(self, file_path: str, custom_query: Optional[str] = None) -> Dict[str, Any]:
        """Downloads lyrics for single track using the anti-mismatch engine and LRCLIB/Genius."""
        return lyrics_engine.download_track_lyrics(
            file_path=file_path,
            custom_query=custom_query,
            allow_plain=True,
            strip_cjk=True,
        )

    def get_lyrics(self, file_path: str) -> Dict[str, Any]:
        """Loads and parses the existing .lrc file for live karaoke preview."""
        lrc_path = os.path.splitext(file_path)[0] + ".lrc"
        if not os.path.exists(lrc_path):
            return {"success": False, "lines": [], "state": "none"}

        try:
            with open(lrc_path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()

            state = lyrics_engine.analyze_lrc_content(raw)
            parsed_lines = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                match = lyrics_engine.TIMESTAMP_RE.search(line)
                if match:
                    ts = match.group(0)
                    text = line.replace(ts, "").strip()
                    # Calculate seconds for karaoke sync
                    mins = int(match.group(1))
                    secs = int(match.group(2))
                    ms = float(f"0.{match.group(3)}") if match.group(3) else 0.0
                    total_sec = mins * 60 + secs + ms
                    parsed_lines.append({"timestamp": ts, "seconds": total_sec, "text": text})
                else:
                    parsed_lines.append({"timestamp": "", "seconds": None, "text": line})

            return {"success": True, "lines": parsed_lines, "state": state}
        except Exception as e:
            return {"success": False, "error": str(e), "lines": [], "state": "none"}

    def custom_search(self, file_path: str, query: str) -> Dict[str, Any]:
        """Performs search on LRCLIB and Genius with the custom query."""
        # 1. Direct LRCLIB Search
        try:
            lrclib_lyrics, state = lyrics_engine.fetch_lrclib_lyrics("", query, want_synced=True)
            if lrclib_lyrics:
                return {
                    "success": True,
                    "preview": f"[LRCLIB {state.upper()} Match]\n\n" + lrclib_lyrics[:450] + ("..." if len(lrclib_lyrics) > 450 else ""),
                }
        except Exception:
            pass

        # 2. Direct Genius Search
        try:
            genius_res = lyrics_engine.fetch_genius_plain_lyrics(query)
            if genius_res:
                return {
                    "success": True,
                    "preview": f"[Genius Plain Lyrics Match]\n\n" + genius_res[:450] + ("..." if len(genius_res) > 450 else ""),
                }
        except Exception:
            pass

        return {"success": False, "preview": "No matching lyrics found on LRCLIB or Genius for this query."}

    def check_for_updates(self) -> Dict[str, Any]:
        """Checks GitHub releases for new versions."""
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Sonance"}
            r = requests.get(url, headers=headers, timeout=5)
            if r.ok:
                data = r.json()
                latest_tag = data.get("tag_name", "").lstrip("v")
                if latest_tag and latest_tag != APP_VERSION:
                    # Look for windows exe asset
                    download_url = data.get("html_url")
                    for asset in data.get("assets", []):
                        if asset.get("name", "").endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            break
                    return {
                        "update_available": True,
                        "current_version": APP_VERSION,
                        "latest_version": latest_tag,
                        "changelog": data.get("body", "Bug fixes and improvements."),
                        "download_url": download_url,
                    }
        except Exception:
            pass

        return {"update_available": False, "current_version": APP_VERSION}

    def search_music(self, query: str, source: str = "all") -> List[Dict[str, Any]]:
        """Multi-source search across Deezer, Spotify metadata, and YouTube."""
        return downloader_engine.search_music_catalog(query, source=source)

    def add_to_queue(self, track_data: Dict[str, Any], output_format: str = "mp3") -> str:
        """Adds a track to the download queue with simultaneous synced lyrics."""
        return downloader_engine.queue_manager.add_task(track_data, output_format=output_format)

    def get_queue_tasks(self) -> List[Dict[str, Any]]:
        """Returns live status of all download tasks in the queue."""
        return downloader_engine.queue_manager.get_all_tasks()

    def get_auth(self) -> Dict[str, Any]:
        """Loads Deezer ARL, Qobuz, and Spotify credentials."""
        return downloader_engine.load_auth_config()

    def save_auth(self, auth_data: Dict[str, Any]) -> bool:
        """Saves Deezer ARL, Qobuz, and Spotify credentials."""
        downloader_engine.save_auth_config(auth_data)
        return True

    def get_download_dir(self) -> str:
        """Gets the configured download directory."""
        cfg = downloader_engine.load_auth_config()
        return cfg.get("download_dir", downloader_engine.DEFAULT_DOWNLOAD_DIR)

    def select_download_folder(self) -> str:
        """Opens native OS folder picker for download directory."""
        if not self._window:
            return ""
        dialog_type = getattr(webview.FileDialog, "FOLDER", getattr(webview, "FOLDER_DIALOG", None))
        result = self._window.create_file_dialog(dialog_type)
        if result and len(result) > 0:
            folder = result[0]
            cfg = downloader_engine.load_auth_config()
            cfg["download_dir"] = folder
            downloader_engine.save_auth_config(cfg)
            return folder
        return ""

    def _save_last_folder(self, folder: str):
        try:
            cfg = {}
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["music_dir"] = folder
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass


def main():
    api = LyricsAPI()

    window = webview.create_window(
        title=f"Sonance v{APP_VERSION}",
        url=str(UI_PATH),
        js_api=api,
        width=1160,
        height=780,
        min_size=(960, 640),
        background_color="#0f1117",
    )
    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
