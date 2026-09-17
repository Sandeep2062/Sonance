"""
modern_lyrics_downloader.py - Sonance Modern Desktop Application (v2.1)

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (c) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Features:
- Native Windows Desktop Window (powered by pywebview & Windows WebView2)
- Built-in HTTP Audio Streaming Server with Byte-Range Scrubbing
- Real-time Karaoke Sync & In-App Music Player
- Spek-style Audio Quality & Spectrogram Inspector
- Full-Height Artist & Album Browser with Instant Search
- Direct LRCLIB & Genius Integration
- In-App GitHub Update Checker
- 10-Band Studio Hardware Equalizer (DSP)
- Discord Rich Presence Live Integration
- User Playlists & Favorites Management
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
import cookie_manager
import playlist_manager
import discord_rpc
import scrobbler
import tag_editor
import cache_manager
import auto_dj
import library_doctor

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

        if not image_data and tag_editor:
            try:
                t = tag_editor.read_tags(file_path)
                uri = t.get("cover_data_uri", "")
                if uri and uri.startswith("data:"):
                    header, b64_str = uri.split(",", 1)
                    image_data = base64.b64decode(b64_str)
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
        fav_items = playlist_manager.get_favorites()
        fav_ids = {t.get("id") or t.get("path") for t in fav_items}
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

                    track_id = full_path
                    tracks.append({
                        "id": track_id,
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
                        "is_favorite": track_id in fav_ids,
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

    def open_login_window(self, platform: str) -> Dict[str, Any]:
        """Opens embedded WebView login for YouTube, Deezer, Spotify, or SoundCloud."""
        return cookie_manager.open_browser_login(platform)

    def extract_browser_cookies(self, browser_name: str) -> Dict[str, Any]:
        """Extracts cookies directly from installed browser (Chrome, Edge, Firefox, Brave)."""
        return cookie_manager.extract_cookies_from_browser(browser_name)

    def get_cookie_status(self) -> Dict[str, Any]:
        """Checks active cookies status for YouTube, Deezer, Spotify, Qobuz."""
        return cookie_manager.get_cookie_status()

    # ------------------ Favorites & Playlists ------------------
    def toggle_favorite(self, track_data: Dict[str, Any]) -> bool:
        """Toggles a track in user favorites."""
        if not track_data.get("id"):
            track_data["id"] = track_data.get("path") or track_data.get("stream_url") or f"{track_data.get('artist')}_{track_data.get('title')}"
        return playlist_manager.toggle_favorite(track_data)

    def get_favorites(self) -> List[Dict[str, Any]]:
        """Returns list of favorite tracks."""
        return playlist_manager.get_favorites()

    def create_playlist(self, name: str) -> bool:
        """Creates a new user playlist."""
        return playlist_manager.create_playlist(name)

    def add_to_playlist(self, name: str, track_data: Dict[str, Any]) -> bool:
        """Adds a track to a playlist."""
        if not track_data.get("id"):
            track_data["id"] = track_data.get("path") or track_data.get("stream_url") or f"{track_data.get('artist')}_{track_data.get('title')}"
        return playlist_manager.add_track_to_playlist(name, track_data)

    def get_all_playlists(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns all custom playlists."""
        return playlist_manager.get_all_playlists()

    def export_playlist_m3u(self, name: str, out_path: str = "") -> bool:
        """Exports a playlist to M3U file."""
        if not out_path:
            out_path = str(Path(self.get_download_dir()) / f"{name}.m3u")
        return playlist_manager.export_playlist_m3u(name, out_path)

    # ------------------ Discord Rich Presence ------------------
    def update_discord_rpc(
        self,
        title: str,
        artist: str,
        album: str = "",
        duration_sec: int = 0,
        cover_url: Optional[str] = None,
        is_playing: bool = True,
    ):
        """Updates Discord Rich Presence profile status."""
        try:
            discord_rpc.rpc_manager.update_activity(
                title=title,
                artist=artist,
                album=album,
                duration_sec=duration_sec,
                cover_url=cover_url,
                is_playing=is_playing,
            )
        except Exception:
            pass

    def clear_discord_rpc(self):
        """Clears Discord Rich Presence."""
        try:
            discord_rpc.rpc_manager.clear_activity()
        except Exception:
            pass

    # ------------------ Last.fm & ListenBrainz Scrobbler ------------------
    def get_scrobbler_config(self) -> Dict[str, Any]:
        """Returns active Last.fm and ListenBrainz configuration."""
        return scrobbler.load_config()

    def save_scrobbler_config(self, cfg: Dict[str, Any]) -> bool:
        """Saves Last.fm and ListenBrainz configuration."""
        scrobbler.save_config(cfg)
        return True

    def validate_listenbrainz_token(self, token: str) -> Dict[str, Any]:
        """Validates ListenBrainz token against official API."""
        return scrobbler.listenbrainz_client.validate_token(token)

    def get_lastfm_session(self, token: str) -> Dict[str, Any]:
        """Exchanges Last.fm web auth token for session key."""
        return scrobbler.lastfm_client.get_session_from_token(token)

    def scrobble_now_playing(self, artist: str, track: str, album: str = "", duration: int = 0):
        """Broadcasts Now Playing state to Last.fm and ListenBrainz."""
        scrobbler.scrobble_now_playing(artist=artist, track=track, album=album or None, duration=duration or None)

    def scrobble_track(self, artist: str, track: str, album: str = "", duration: int = 0, timestamp: int = 0):
        """Submits scrobble to Last.fm and ListenBrainz."""
        scrobbler.scrobble_track(artist=artist, track=track, album=album or None, duration=duration or None, timestamp=timestamp or None)

    def get_artist_info(self, artist: str) -> Dict[str, Any]:
        """Retrieves artist bio, genre tags, and listener statistics."""
        return scrobbler.lastfm_client.get_artist_info(artist)

    def get_similar_tracks(self, artist: str, track: str) -> List[Dict[str, Any]]:
        """Retrieves similar recommended tracks."""
        return scrobbler.lastfm_client.get_similar_tracks(artist, track)

    # ------------------ Tag Editor & Cover Art (Mp3tag Grade) ------------------
    def read_track_tags(self, file_path: str) -> Dict[str, Any]:
        """Reads ID3/Vorbis/MP4 tags and cover art data URI."""
        return tag_editor.read_tags(file_path)

    def save_track_tags(self, file_path: str, tags: Dict[str, Any]) -> Dict[str, Any]:
        """Saves metadata tags and embeds cover art."""
        return tag_editor.write_tags(file_path, tags)

    def auto_fetch_track_tags(self, title: str, artist: str) -> Dict[str, Any]:
        """Queries MusicBrainz and web databases to auto-fill tags and cover art."""
        return tag_editor.auto_fetch_metadata(title, artist)

    # ------------------ Live Lyrics Timing Offset ------------------
    def shift_lrc_offset(self, file_path: str, offset_ms: int) -> Dict[str, Any]:
        """Permanently shifts all timestamps in the .lrc file by offset_ms."""
        return lyrics_engine.shift_lrc_file_offset(file_path, offset_ms)

    # ------------------ Stream Cache & Offline Mode ------------------
    def get_cache_stats(self) -> Dict[str, Any]:
        """Returns total cached stream files and size in MB."""
        return cache_manager.get_cache_stats()

    def clear_stream_cache(self) -> bool:
        """Clears local stream cache."""
        return cache_manager.clear_cache()

    # ------------------ Phase 7: Desktop Mini-Player & Overlay ------------------
    def toggle_mini_player(self, enable: bool) -> Dict[str, Any]:
        """Toggles compact 380x240 always-on-top floating desktop widget."""
        try:
            if self._window:
                if enable:
                    self._window.resize(380, 240)
                    self._window.on_top = True
                else:
                    self._window.resize(1160, 780)
                    self._window.on_top = False
                return {"success": True, "is_mini": enable}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Window not initialized"}

    # ------------------ Phase 7: Auto-DJ & Infinite Radio ------------------
    def get_auto_dj_tracks(self, artist: str, title: str, count: int = 5) -> List[Dict[str, Any]]:
        """Queries Auto-DJ engine for similar matching tracks to keep music playing."""
        return auto_dj.auto_dj_engine.get_recommendations(artist, title, count)

    # ------------------ Phase 7: Library Doctor & Duplicates ------------------
    def scan_library_health(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes music folder for duplicates, missing lyrics, and library health."""
        target = folder or self._current_folder
        return library_doctor.scan_library_health(target)

    def delete_duplicate_file(self, file_path: str) -> Dict[str, Any]:
        """Removes a duplicate audio file and deletes any corresponding .lrc file."""
        return library_doctor.delete_audio_file(file_path)

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
