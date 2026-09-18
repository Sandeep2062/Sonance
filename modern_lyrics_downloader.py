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
import remote_server
import smart_playlists
import lyrics_translation
import audio_transcoder
import listening_stats
import lyrics_creator
import audio_fingerprint
import discography_scraper
import cue_splitter
import audio_cutter
import loudness_scanner
import word_karaoke
import audio_dedup
import cd_ripper
import cloud_streamer
import room_eq
import playlist_converter
import vocal_separator
import audio_auditor
import dj_mixer
import chord_studio
import audio_resampler
import pitch_shifter
import library_organizer
import album_packer
import dr_meter
import device_sync
import ab_looper
import word_aligner
import headphone_autoeq
import flac_verifier
import dj_automix
import lyrics_aggregator
import audio_inspector
import audio_restorer
import library_migrator
import lyrics_translator
import accuraterip_verifier
import playlist_doctor
import audio_8d_spatializer
import replaygain_normalizer
import parametric_eq
import phase_correlation
import dac_tester
import lyrics_retimer
import spectrum_analyzer
import audio_declipper
import track_splitter
import lyrics_video_maker
import audio_upsampler
import cue_fixer
import room_ir_synthesizer
import lrc_to_ass_converter
import dsd_converter
import subsample_delay
import mastering_limiter
import album_art_studio
import audio_deesser
import midside_processor
import audio_watermark
import cue_markers
import analog_tape_emulator
import formant_shifter
import loudness_war_studio
import stems_remixer
import transient_shaper
import binaural_virtualizer
import audio_noisegate
import tape_echo_delay
import release_packager
import docs_generator
import plugin_host
import spatial_multichannel
import console_channel_strip
import ambisonic_hoa
import subharmonic_bass
import resonance_suppressor
import vintage_compressor
import zenith_orchestrator
import exclusive_audio_engine
import sonance_paths

APP_VERSION = "3.6.6"
GITHUB_REPO = "Sandeep2062/Sonance"
APP_DIR = Path(__file__).parent.resolve()
UI_PATH = APP_DIR / "ui" / "index.html"
CONFIG_FILE = sonance_paths.get_config_path()


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
        # Connect mobile remote action handler to desktop UI
        def _handle_remote(action: str, value: Any):
            if self._window:
                try:
                    js = f"window.handleRemoteAction && window.handleRemoteAction({json.dumps(action)}, {json.dumps(value)});"
                    self._window.evaluate_js(js)
                except Exception:
                    pass
        remote_server.global_remote_state.action_handler = _handle_remote

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

    @staticmethod
    def _is_newer_version(latest: str, current: str) -> bool:
        try:
            l_parts = [int(x) for x in re.findall(r'\d+', latest)]
            c_parts = [int(x) for x in re.findall(r'\d+', current)]
            for l, c in zip(l_parts, c_parts):
                if l > c:
                    return True
                if l < c:
                    return False
            return len(l_parts) > len(c_parts)
        except Exception:
            return latest != current

    def check_for_updates(self) -> Dict[str, Any]:
        """Checks GitHub releases for new versions with cross-platform installer matching."""
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Sonance"}
            r = requests.get(url, headers=headers, timeout=6)
            if r.ok:
                data = r.json()
                latest_tag = data.get("tag_name", "").lstrip("v")
                if latest_tag and self._is_newer_version(latest_tag, APP_VERSION):
                    assets = data.get("assets", [])
                    installer_url = None
                    portable_url = None
                    sha256_url = None

                    for asset in assets:
                        name = asset.get("name", "").lower()
                        dl_url = asset.get("browser_download_url")
                        if "sha256" in name:
                            sha256_url = dl_url

                        if sys.platform == "win32":
                            if "installer" in name and name.endswith(".exe"):
                                installer_url = dl_url
                            elif (not installer_url) and name.endswith(".exe"):
                                installer_url = dl_url
                            elif "portable" in name and (name.endswith(".zip") or name.endswith(".exe")):
                                portable_url = dl_url
                        elif sys.platform == "darwin":
                            if name.endswith(".dmg"):
                                installer_url = dl_url
                            elif name.endswith(".zip"):
                                portable_url = dl_url
                        else:  # Linux
                            if name.endswith(".deb"):
                                installer_url = dl_url
                            elif name.endswith(".appimage") or name.endswith(".tar.xz"):
                                portable_url = dl_url

                    return {
                        "update_available": True,
                        "current_version": APP_VERSION,
                        "latest_version": latest_tag,
                        "changelog": data.get("body", "Bug fixes and performance improvements."),
                        "download_url": installer_url or portable_url or data.get("html_url"),
                        "installer_url": installer_url,
                        "portable_url": portable_url,
                        "sha256_url": sha256_url,
                    }
        except Exception as e:
            print(f"[!] Update check error: {e}")

        return {"update_available": False, "current_version": APP_VERSION}

    def download_and_install_update(self, download_url: str) -> Dict[str, Any]:
        """Downloads the installer binary in background and launches it."""
        if not download_url:
            return {"success": False, "error": "No download URL provided."}

        def _worker():
            try:
                import tempfile
                import subprocess

                temp_dir = Path(tempfile.gettempdir())
                filename = download_url.split("/")[-1]
                target_file = temp_dir / filename

                def _notify(pct: float, message: str):
                    if self._window:
                        try:
                            msg_clean = message.replace("'", "\\'")
                            self._window.evaluate_js(
                                f"window.onUpdateDownloadProgress && window.onUpdateDownloadProgress({pct}, '{msg_clean}');"
                            )
                        except Exception:
                            pass

                _notify(5, "Connecting to GitHub Releases CDN...")
                resp = requests.get(download_url, stream=True, timeout=15)
                resp.raise_for_status()

                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(target_file, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = min(95.0, (downloaded / total_size) * 85.0 + 10.0)
                                mb_done = downloaded / (1024 * 1024)
                                mb_total = total_size / (1024 * 1024)
                                _notify(round(pct, 1), f"Downloading: {mb_done:.1f} MB / {mb_total:.1f} MB")

                _notify(98, "Launching installer...")
                time.sleep(0.5)

                # Launch installer based on platform
                if sys.platform == "win32":
                    subprocess.Popen([str(target_file)], shell=True)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(target_file)])
                else:
                    subprocess.Popen(["xdg-open", str(target_file)])

                _notify(100, "Installer launched! Closing current version...")
                time.sleep(1.2)
                if self._window:
                    self._window.destroy()
                os._exit(0)

            except Exception as e:
                if self._window:
                    try:
                        err_msg = str(e).replace("'", "\\'")
                        self._window.evaluate_js(
                            f"window.onUpdateDownloadProgress && window.onUpdateDownloadProgress(-1, 'Error: {err_msg}');"
                        )
                    except Exception:
                        pass

        threading.Thread(target=_worker, daemon=True).start()
        return {"success": True, "message": "Download started in background."}

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

    # ------------------ Tag Editor & Cover Art (Studio Tag Editor) ------------------
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

    # ------------------ Phase 8: Mobile Web Remote ------------------
    def get_remote_server_info(self) -> Dict[str, Any]:
        """Returns Wi-Fi mobile remote status, LAN URL, and connection port."""
        return remote_server.remote_server.get_info()

    def toggle_remote_server(self, enable: bool) -> Dict[str, Any]:
        """Starts or stops the embedded Wi-Fi mobile remote server."""
        if enable:
            return remote_server.remote_server.start()
        else:
            return remote_server.remote_server.stop()

    def update_remote_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Updates playback state broadcasted to connected mobile devices."""
        remote_server.global_remote_state.update(state)
        return {"success": True}

    # ------------------ Phase 8: Smart Dynamic Playlists ------------------
    def get_smart_playlists(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of smart dynamic playlists with live item counts."""
        target = folder or self._current_folder
        return smart_playlists.get_smart_playlists(target)

    def get_smart_playlist_tracks(self, playlist_id: str, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns tracks matching the smart dynamic playlist."""
        target = folder or self._current_folder
        return smart_playlists.get_smart_playlist_tracks(playlist_id, target)

    def export_smart_playlist(self, playlist_id: str, output_path: str, folder: Optional[str] = None) -> Dict[str, Any]:
        """Exports smart playlist tracks to a standard .m3u8 file."""
        target = folder or self._current_folder
        return smart_playlists.export_smart_playlist_m3u8(playlist_id, target, output_path)

    # ------------------ Phase 9: Multilingual Lyrics Studio ------------------
    def enrich_lyrics_multilingual(self, lines: List[Dict[str, Any]], target_lang: str = "en") -> List[Dict[str, Any]]:
        """Adds phonetic romanization (Romaji/Pinyin/Hangul) and translation to lyrics."""
        return lyrics_translation.enrich_lyrics_with_phonetics(lines, target_lang)

    # ------------------ Phase 9: Audio Batch Transcoder ------------------
    def get_transcoder_formats(self) -> Dict[str, Any]:
        """Returns supported audio export formats and bitrate presets."""
        return {
            "formats": audio_transcoder.SUPPORTED_OUTPUT_FORMATS,
            "bitrates": audio_transcoder.DEFAULT_BITRATES,
            "has_ffmpeg": bool(audio_transcoder.find_ffmpeg_executable()),
        }

    def transcode_audio_files(
        self,
        file_paths: List[str],
        target_format: str = "mp3",
        target_bitrate: str = "320k",
        dest_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcodes a batch of audio tracks while preserving tags and .lrc lyrics."""
        return audio_transcoder.batch_transcode(file_paths, target_format, target_bitrate, dest_dir)

    # ------------------ Phase 9: Listening Stats & Wrapped ------------------
    def record_play_event(
        self,
        title: str,
        artist: str,
        album: str = "",
        duration: float = 0.0,
        format_name: str = "MP3",
        quality: str = "320 kbps",
        is_stream: bool = False
    ) -> Dict[str, Any]:
        """Records a completed track playback into local stats history."""
        return listening_stats.record_playback_event(title, artist, album, duration, format_name, quality, is_stream)

    def get_listening_stats(self) -> Dict[str, Any]:
        """Computes local Wrapped listening statistics."""
        return listening_stats.get_listening_stats()

    def clear_listening_history(self) -> Dict[str, Any]:
        """Resets local listening history."""
        return listening_stats.clear_listening_history()

    # ------------------ Phase 10: Interactive LRC Creator Studio ------------------
    def parse_lyrics_for_creator(self, raw_text: str) -> List[Dict[str, Any]]:
        """Parses plain lyrics into structured items for real-time stamping."""
        return lyrics_creator.parse_plain_lyrics(raw_text)

    def save_created_lrc(
        self,
        audio_path: str,
        lines: List[Dict[str, Any]],
        title: str = "",
        artist: str = "",
        album: str = ""
    ) -> Dict[str, Any]:
        """Builds and saves stamped RFC-compliant .lrc lyrics to disk and metadata."""
        lrc_text = lyrics_creator.build_lrc_string(lines, title, artist, album)
        return lyrics_creator.save_lrc_file(audio_path, lrc_text)

    def shift_created_lrc_lines(self, lines: List[Dict[str, Any]], offset_seconds: float) -> List[Dict[str, Any]]:
        """Shifts timestamped lines forward or backward."""
        return lyrics_creator.shift_all_timestamps(lines, offset_seconds)

    # ------------------ Phase 10: Acoustic Audio Fingerprinting ------------------
    def identify_audio_track(self, file_path: str) -> Dict[str, Any]:
        """Identifies an unknown audio file via acoustic properties and catalog query."""
        return audio_fingerprint.identify_track(file_path)

    # ------------------ Phase 10: Artist Discography & Album Downloader -----------
    def get_artist_discography(self, artist_name: str, max_albums: int = 15) -> Dict[str, Any]:
        """Fetches complete discography with studio albums, EPs, and tracklists."""
        return discography_scraper.get_full_discography(artist_name, include_tracks=True, max_albums=max_albums)

    def get_album_tracks(self, album_id: str) -> List[Dict[str, Any]]:
        """Fetches tracklist for an album ID."""
        return discography_scraper.get_album_tracklist(album_id)

    # ------------------ Phase 10: Podcast & Audiobook Bookmarking -----------------
    def save_playback_bookmark(self, file_path: str, position_sec: float) -> Dict[str, Any]:
        """Saves current playback position for long files (>15 min) or podcasts."""
        try:
            bm_file = APP_DIR / "cache" / "playback_bookmarks.json"
            bm_file.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if bm_file.exists():
                with open(bm_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data[file_path] = {
                "position": round(position_sec, 1),
                "timestamp": round(position_sec, 1)
            }
            with open(bm_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_playback_bookmark(self, file_path: str) -> Dict[str, Any]:
        """Retrieves saved bookmark for an audio file."""
        try:
            bm_file = APP_DIR / "cache" / "playback_bookmarks.json"
            if bm_file.exists():
                with open(bm_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    rec = data.get(file_path)
                    if rec and rec.get("position", 0) > 15:
                        pos = rec["position"]
                        mins = int(pos // 60)
                        secs = int(pos % 60)
                        return {
                            "has_bookmark": True,
                            "position": pos,
                            "position_str": f"{mins}:{secs:02d}"
                        }
        except Exception:
            pass
        return {"has_bookmark": False, "position": 0}

    # ------------------ Phase 11: CUE Sheet Splitter & Parser ------------------
    def parse_cue_sheet(self, cue_path: str) -> Dict[str, Any]:
        """Parses a .cue index sheet and resolves virtual tracks."""
        return cue_splitter.parse_cue_file(cue_path)

    def split_cue_sheet(
        self,
        cue_path: str,
        output_dir: Optional[str] = None,
        output_format: str = "flac",
        bitrate: str = "320k"
    ) -> Dict[str, Any]:
        """Splits an album audio file into individual tagged track files."""
        return cue_splitter.split_cue_sheet(cue_path, output_dir, output_format, bitrate)

    # ------------------ Phase 11: Studio Audio Ringtone & Clip Cutter ----------
    def trim_audio_clip(
        self,
        file_path: str,
        start_sec: float,
        end_sec: float,
        fade_in: float = 0.5,
        fade_out: float = 0.5,
        format_name: str = "mp3",
        bitrate: str = "320k",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trims a high-quality audio clip or ringtone with fade envelopes."""
        return audio_cutter.trim_audio_clip(
            file_path, start_sec, end_sec, fade_in, fade_out, format_name, bitrate, output_path
        )

    def select_cue_file(self) -> str:
        """Opens native OS file picker for .cue sheet files."""
        if not self._window:
            return ""
        open_dialog = getattr(webview.FileDialog, "OPEN", getattr(webview, "OPEN_DIALOG", None))
        result = self._window.create_file_dialog(
            open_dialog,
            file_types=('CUE Sheet Files (*.cue)', 'All files (*.*)')
        )
        if result and len(result) > 0:
            return result[0]
        return ""

    def select_audio_file(self) -> str:
        """Opens native OS file picker for audio files."""
        if not self._window:
            return ""
        open_dialog = getattr(webview.FileDialog, "OPEN", getattr(webview, "OPEN_DIALOG", None))
        result = self._window.create_file_dialog(
            open_dialog,
            file_types=('Audio Files (*.mp3;*.flac;*.wav;*.m4a;*.ogg;*.opus;*.aac)', 'All files (*.*)')
        )
        if result and len(result) > 0:
            return result[0]
        return ""

    # ------------------ Phase 12: ReplayGain & Loudness Scanner -----------------
    def scan_track_loudness(self, file_path: str, target_lufs: float = -14.0, apply_tags: bool = False) -> Dict[str, Any]:
        """Scans single track loudness and calculates ReplayGain."""
        return loudness_scanner.scan_file_loudness(file_path, target_lufs, apply_tags)

    def scan_batch_loudness(self, file_paths: List[str], target_lufs: float = -14.0, apply_tags: bool = False) -> Dict[str, Any]:
        """Scans batch of tracks and computes track/album ReplayGain."""
        return loudness_scanner.scan_batch_loudness(file_paths, target_lufs, apply_tags)

    # ------------------ Phase 12: Word-by-Word Syllable Karaoke -----------------
    def parse_enhanced_lyrics(self, lrc_text: str) -> Dict[str, Any]:
        """Parses Enhanced LRC or standard LRC into word-by-word syllable timing data."""
        return word_karaoke.parse_enhanced_lrc(lrc_text)

    # ------------------ Phase 12: Audio Duplicate Cleaner -----------------------
    def scan_for_duplicates(self, folder_path: str) -> Dict[str, Any]:
        """Scans folder for duplicate tracks matching across formats and bitrates."""
        return audio_dedup.scan_for_duplicates(folder_path)

    def archive_duplicates(self, duplicate_paths: List[str], archive_directory: str) -> Dict[str, Any]:
        """Safely archives redundant duplicate tracks."""
        return audio_dedup.archive_redundant_duplicates(duplicate_paths, archive_directory)

    # ------------------ Phase 12: Audio CD Ripper -------------------------------
    def detect_cd_drives(self) -> List[Dict[str, Any]]:
        """Detects physical and virtual optical CD drives."""
        return cd_ripper.detect_cd_drives()

    def rip_audio_cd(self, drive_letter: str, output_dir: Optional[str] = None, output_format: str = "flac") -> Dict[str, Any]:
        """Rips audio CD tracks into tagged audio files."""
        return cd_ripper.rip_audio_cd(drive_letter, output_dir, output_format)

    # ------------------ Phase 13: Subsonic Personal Cloud Streaming -------------
    def test_subsonic_connection(self, server_url: str, username: str, password: str) -> Dict[str, Any]:
        """Tests connection to a Subsonic / Navidrome / Jellyfin server."""
        return cloud_streamer.test_connection(server_url, username, password)

    def get_subsonic_artists(self, server_url: str, username: str, password: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves artist directory from cloud server."""
        return cloud_streamer.get_artists(server_url, username, password, folder_id)

    def get_subsonic_artist_albums(self, server_url: str, username: str, password: str, artist_id: str) -> Dict[str, Any]:
        """Retrieves artist albums from cloud server."""
        return cloud_streamer.get_artist_albums(server_url, username, password, artist_id)

    def get_subsonic_album_tracks(self, server_url: str, username: str, password: str, album_id: str) -> Dict[str, Any]:
        """Retrieves album tracklist from cloud server."""
        return cloud_streamer.get_album_tracks(server_url, username, password, album_id)

    def search_subsonic_music(self, server_url: str, username: str, password: str, query: str) -> Dict[str, Any]:
        """Searches personal cloud music collection."""
        return cloud_streamer.search_cloud(server_url, username, password, query)

    # ------------------ Phase 13: Room EQ Convolution DSP -----------------------
    def get_room_ir_preset(self, preset: str = "abbey_studio") -> Dict[str, Any]:
        """Returns base64-encoded impulse response WAV data URI for Web Audio ConvolverNode."""
        return room_eq.get_ir_preset_data_uri(preset)

    def load_custom_ir_wav(self, file_path: str) -> Dict[str, Any]:
        """Loads and normalizes a custom impulse response WAV file."""
        return room_eq.load_custom_ir_file(file_path)

    # ------------------ Phase 13: Universal Playlist Converter ------------------
    def parse_playlist_file(self, file_path_or_url: str) -> Dict[str, Any]:
        """Parses M3U, PLS, WPL, XSPF, or Spotify playlist."""
        return playlist_converter.parse_any_playlist(file_path_or_url)

    def convert_playlist_file(self, input_path: str, output_format: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Converts playlist file to another format."""
        return playlist_converter.convert_playlist(input_path, output_format, output_path)

    # ------------------ Phase 14: Stem Separator Studio -------------------------
    def separate_audio_stems(self, file_path: str, output_dir: Optional[str] = None, mode: str = "2stems", output_format: str = "flac") -> Dict[str, Any]:
        """Separates audio file into isolated stems (Vocals, Instrumental, Bass, Drums)."""
        return vocal_separator.separate_stems(file_path, output_dir, mode, output_format)

    # ------------------ Phase 14: Lossless Authenticity Auditor -----------------
    def audit_audio_authenticity(self, file_path: str) -> Dict[str, Any]:
        """Audits an audio file for fake/upscaled lossless compression via brickwall frequency cutoff."""
        return audio_auditor.audit_file(file_path)

    def audit_batch_authenticity(self, folder_path: str) -> Dict[str, Any]:
        """Audits all lossless files in a directory to detect fake upscales."""
        return audio_auditor.audit_directory(folder_path)

    # ------------------ Phase 14: DJ Camelot Harmonic Key & BPM -----------------
    def analyze_track_key_bpm(self, file_path: str) -> Dict[str, Any]:
        """Analyzes BPM tempo, musical key, and Camelot DJ wheel mixing code."""
        return dj_mixer.analyze_track_bpm_and_key(file_path)

    # ------------------ Phase 14: Synchronized Guitar Chord Studio --------------
    def get_synced_chords(self, artist: str, title: str, key_name: Optional[str] = "A Minor") -> Dict[str, Any]:
        """Fetches harmonic progression and chord diagrams for track."""
        return chord_studio.get_song_chord_studio_data(artist, title, key_name)

    def get_chord_diagram(self, chord_name: str) -> Dict[str, Any]:
        """Returns guitar fretboard diagram and voicing for chord."""
        return chord_studio.get_chord_details(chord_name)

    # ------------------ Phase 15: Audiophile Sinc Resampler & Dither ------------
    def resample_audio_track(self, file_path: str, target_rate: int = 96000, target_bit_depth: int = 24, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Resamples audio track with polyphase sinc interpolation and TPDF noise-shaped dither."""
        return audio_resampler.resample_audio_file(file_path, target_rate, target_bit_depth, output_file)

    # ------------------ Phase 15: Vocal Pitch Transposer & Key Shifter ----------
    def transpose_audio_pitch(self, file_path: str, semitones: float, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Transposes musical pitch (-6 to +6 semitones) without tempo changes."""
        return pitch_shifter.shift_pitch_file(file_path, semitones, output_file)

    # ------------------ Phase 15: Library Auto-Organizer & File Renamer ---------
    def preview_library_organization(self, folder_path: str, pattern: str = library_organizer.DEFAULT_ORGANIZER_PATTERN) -> Dict[str, Any]:
        """Generates a dry-run preview of library folder organization."""
        return library_organizer.preview_library_organization(folder_path, pattern)

    def execute_library_organization(self, folder_path: str, pattern: str = library_organizer.DEFAULT_ORGANIZER_PATTERN, copy_mode: bool = False) -> Dict[str, Any]:
        """Executes tag-based library file renaming and directory restructuring."""
        return library_organizer.execute_library_organization(folder_path, pattern, copy_mode=copy_mode)

    # ------------------ Phase 15: Lossless Monolithic Album Packer --------------
    def pack_album_to_monolithic(self, folder_path: str, output_flac: Optional[str] = None) -> Dict[str, Any]:
        """Packs loose album tracks into a single monolithic FLAC with Red Book CUE sheet."""
        return album_packer.pack_album(folder_path, output_flac)

    def unpack_monolithic_album(self, album_file: str, cue_file: Optional[str] = None, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Unpacks a monolithic album image into separate tagged tracks."""
        return album_packer.unpack_album(album_file, cue_file, output_dir)

    # ------------------ Phase 16: Dynamic Range (DR) Meter ----------------------
    def measure_dynamic_range(self, path: str) -> Dict[str, Any]:
        """Measures Pleasurize Music Foundation TT Dynamic Range and Crest Factor."""
        if os.path.isdir(path):
            return dr_meter.analyze_album_dynamic_range(path)
        return dr_meter.analyze_track_dynamic_range(path)

    # ------------------ Phase 16: Portable DAP & USB Synchronizer ---------------
    def get_portable_devices(self) -> List[Dict[str, Any]]:
        """Returns detected removable USB drives, DAPs, and SD cards."""
        return device_sync.detect_portable_drives()

    def sync_to_portable_device(self, target_dir: str, track_paths: List[str], playlist_name: str = "Sonance Sync", transcode_mode: str = "copy", bitrate: str = "320k") -> Dict[str, Any]:
        """Synchronizes tracks to portable device storage with optional transcoding and M3U8 creation."""
        return device_sync.sync_tracks_to_device(track_paths, target_dir, playlist_name=playlist_name, transcode_mode=transcode_mode, bitrate=bitrate)

    # ------------------ Phase 16: Musician A-B Phrase Looper --------------------
    def render_ab_loop(self, audio_path: str, start_sec: float, end_sec: float, repeats: int = 4, add_count_in: bool = False, bpm: float = 120.0, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Extracts and renders seamless de-clicked A-B phrase loop with count-in metronome."""
        return ab_looper.create_ab_loop(audio_path, start_sec, end_sec, repeats=repeats, add_count_in=add_count_in, bpm=bpm, output_path=output_path)

    # ------------------ Phase 16: Word-by-Word ELRC Syllable Aligner ------------
    def align_word_lyrics(self, lrc_text: str, audio_path: Optional[str] = None, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Aligns line-level lyrics to word/syllable level Enhanced LRC with acoustic transients."""
        res = word_aligner.generate_enhanced_lrc(lrc_text, audio_path=audio_path)
        if res.get("success") and output_path:
            word_aligner.save_enhanced_lrc(res["enhanced_lrc"], output_path)
            res["output_file"] = output_path
        return res

    # ------------------ Phase 17: Headphone AutoEq Studio -----------------------
    def get_autoeq_profiles(self) -> List[Dict[str, Any]]:
        """Returns built-in headphone AutoEq Harman calibration profiles."""
        return headphone_autoeq.get_available_profiles()

    def get_autoeq_gains(self, profile_key: str) -> Dict[str, Any]:
        """Retrieves 10-band EQ gains and preamp for a specific headphone profile."""
        prof = headphone_autoeq.get_profile_by_key(profile_key)
        if prof:
            data = dict(prof)
            data["success"] = True
            data["bands"] = list(prof.get("gains", []))
            data["frequencies"] = headphone_autoeq.EQ_10_BANDS
            return data
        return {"success": False, "error": f"Profile '{profile_key}' not found"}

    def parse_custom_autoeq(self, content: str) -> Dict[str, Any]:
        """Parses custom EqualizerAPO / Peace configuration file."""
        res = headphone_autoeq.parse_equalizer_apo_text(content)
        if res.get("success"):
            res["bands"] = list(res.get("gains", []))
            res["frequencies"] = headphone_autoeq.EQ_10_BANDS
        return res

    # ------------------ Phase 17: FLAC MD5 Stream Integrity Auditor -------------
    def audit_flac_integrity(self, file_or_dir: str) -> Dict[str, Any]:
        """Verifies FLAC STREAMINFO MD5 checksum to detect bit rot or corruption."""
        if os.path.isdir(file_or_dir):
            return flac_verifier.verify_flac_directory(file_or_dir)
        return flac_verifier.verify_single_flac(file_or_dir)

    # ------------------ Phase 17: DJ Harmonic Auto-Mix Studio -------------------
    def render_dj_automix(self, track_paths: List[str], transition_sec: Any = 12.0, output_file: Optional[str] = None, *args, **kwargs) -> Dict[str, Any]:
        """Renders continuous DJ automix with phrase alignment and filter sweeps."""
        if (transition_sec is None or not isinstance(transition_sec, (int, float))) and args:
            for a in args:
                if isinstance(a, (int, float)):
                    transition_sec = a
                    break
        try:
            sec = float(transition_sec) if transition_sec is not None else 12.0
        except (ValueError, TypeError):
            sec = 12.0
        return dj_automix.create_dj_automix(track_paths, transition_sec=sec, output_path=output_file)

    # ------------------ Phase 17: Multi-Source Lyrics Aggregator ----------------
    def aggregate_lyrics_search(self, artist: str, title: str, album: Optional[str] = None, duration: Optional[float] = None, romanize: bool = False) -> Dict[str, Any]:
        """Searches multi-provider synced lyrics with quality ranking and romanization."""
        return lyrics_aggregator.aggregate_lyrics(artist, title, album=album, duration=duration, romanize=romanize)

    def batch_download_missing_lyrics(self, folder_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Batch downloads missing .lrc files for all tracks in a folder."""
        return lyrics_aggregator.batch_download_folder_lyrics(folder_path, overwrite=overwrite)

    # ------------------ Phase 18: Hi-Res Audio Stream Inspector -----------------
    def inspect_audio_stream(self, file_path: str) -> Dict[str, Any]:
        """Performs deep bitstream and container forensics on an audio file."""
        return audio_inspector.inspect_audio_stream(file_path)

    # ------------------ Phase 18: Analog Vinyl & Tape Audio Restorer ------------
    def restore_analog_audio(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        declick: bool = True,
        dehum_freq: Optional[float] = 60.0,
        rumble_filter: bool = True,
        dehiss: bool = True,
    ) -> Dict[str, Any]:
        """Restores analog audio with de-clicking, ground hum notch, rumble filter, and de-hiss."""
        return audio_restorer.restore_analog_audio(
            input_path,
            output_path=output_path,
            declick=declick,
            dehum_freq=dehum_freq,
            rumble_filter=rumble_filter,
            dehiss=dehiss,
        )

    # ------------------ Phase 18: Cross-Platform Library Migrator ---------------
    def migrate_music_library(
        self,
        xml_path: str,
        target_music_dir: Optional[str] = None,
        output_playlist_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Migrates iTunes / Apple Music library XML with fuzzy path reconciliation."""
        return library_migrator.migrate_library(
            xml_path,
            target_music_dir=target_music_dir,
            output_playlist_dir=output_playlist_dir,
        )

    # ------------------ Phase 18: Dual-Language Lyrics Translator ---------------
    def translate_synced_lyrics(
        self,
        lyrics_content: str,
        target_language: str = "es",
        dual_format: bool = True,
        output_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Translates synced lyrics preserving timestamps into bilingual subtitles."""
        return lyrics_translator.translate_lyrics(
            lyrics_content,
            target_lang=target_language,
            dual_format=dual_format,
            output_path=output_file,
        )

    def get_supported_translation_languages(self) -> Dict[str, str]:
        """Returns supported target language codes and names."""
        return lyrics_translator.get_supported_languages()

    # ------------------ Phase 19: AccurateRip CD Verifier ------------------------
    def verify_accuraterip(self, file_or_folder: str) -> Dict[str, Any]:
        """Audits CD rip audio against AccurateRip CRCv1, CRCv2 and scans drive offsets."""
        if os.path.isdir(file_or_folder):
            return accuraterip_verifier.verify_album_directory(file_or_folder)
        return accuraterip_verifier.verify_audio_file(file_or_folder)

    # ------------------ Phase 19: Playlist Doctor & Healer -----------------------
    def diagnose_playlist(self, playlist_path: str) -> Dict[str, Any]:
        """Checks playlist health, broken links, duplicates, and lossless ratio."""
        return playlist_doctor.diagnose_playlist(playlist_path)

    def heal_playlist(
        self,
        playlist_path: str,
        library_dir: Optional[str] = None,
        output_path: Optional[str] = None,
        upgrade_lossless: bool = False,
        relative_paths: bool = False,
        remove_duplicates: bool = False,
    ) -> Dict[str, Any]:
        """Heals broken playlist paths, upgrades to lossless, and writes sanitized M3U8."""
        return playlist_doctor.heal_playlist(
            playlist_path,
            library_dir=library_dir,
            output_path=output_path,
            upgrade_lossless=upgrade_lossless,
            relative_paths=relative_paths,
            remove_duplicates=remove_duplicates,
        )

    # ------------------ Phase 19: 8D Spatial Audio Orbit DSP ---------------------
    def render_8d_audio(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        orbit_seconds: float = 12.0,
        spatial_depth: float = 0.85,
        reverb_mix: float = 0.20,
    ) -> Dict[str, Any]:
        """Renders binaural 360-degree rotating 8D spatial audio master."""
        return audio_8d_spatializer.render_8d_audio_file(
            input_path,
            output_path=output_path,
            orbit_period_sec=orbit_seconds,
            spatial_depth=spatial_depth,
            reverb_mix=reverb_mix,
        )

    # ------------------ Phase 19: ReplayGain 2.0 & Loudness Normalizer -----------
    def analyze_replaygain(self, file_path: str, target_lufs: float = -18.0) -> Dict[str, Any]:
        """Analyzes ITU-R BS.1770-4 LUFS and calculates ReplayGain."""
        return replaygain_normalizer.analyze_audio_gain(file_path, target_lufs=target_lufs)

    def process_replaygain_folder(
        self,
        folder_path: str,
        mode: str = "tag",
        target_lufs: float = -18.0,
    ) -> Dict[str, Any]:
        """Audits folder and applies Album/Track ReplayGain tags or hard-normalizes."""
        return replaygain_normalizer.process_folder_replaygain(
            folder_path, mode=mode, target_lufs=target_lufs
        )

    def hard_normalize_audio(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        target_lufs: float = -14.0,
        peak_ceiling_db: float = -0.5,
    ) -> Dict[str, Any]:
        """Renders hard-normalized audio with True-Peak brickwall limiter."""
        return replaygain_normalizer.hard_normalize_audio(
            input_path,
            output_path=output_path,
            target_lufs=target_lufs,
            peak_ceiling_db=peak_ceiling_db,
        )

    # ------------------ Phase 20: Parametric Master EQ ---------------------------
    def get_parametric_eq_curve(self, bands: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Calculates complex frequency response curve across 20Hz-20kHz."""
        return parametric_eq.calculate_complex_response(bands or parametric_eq.DEFAULT_BANDS)

    def render_parametric_eq(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        bands: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Filters audio through the 5-band parametric master EQ."""
        return parametric_eq.render_parametric_eq(input_path, output_path=output_path, bands=bands)

    # ------------------ Phase 20: Phase Correlation & Goniometer -----------------
    def analyze_stereo_phase(self, file_path: str) -> Dict[str, Any]:
        """Analyzes stereo phase correlation, width, balance, and vector scope points."""
        return phase_correlation.analyze_phase_correlation(file_path)

    def correct_stereo_phase(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        invert_right: bool = True,
        mono_bass: bool = True,
    ) -> Dict[str, Any]:
        """Fixes inverted channel phase and applies elliptical EQ for bass punch."""
        return phase_correlation.correct_stereo_phase(
            input_path, output_path=output_path, invert_right_channel=invert_right, mono_bass=mono_bass
        )

    # ------------------ Phase 20: DAC Bit-Perfect Test Generator -----------------
    def generate_dac_test_signal(
        self,
        test_type: str = "sweep",
        sample_rate: int = 96000,
        bit_depth: int = 24,
        duration_sec: float = 10.0,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates precision DAC linearity, jitter, and room calibration test audio."""
        return dac_tester.generate_test_signal_file(
            test_type=test_type,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            duration_sec=duration_sec,
            output_path=output_path,
        )

    # ------------------ Phase 20: Lyrics Drift Corrector -------------------------
    def retime_lyrics_drift(
        self,
        lyrics_content: str,
        t1_old: float,
        t1_new: float,
        t2_old: float,
        t2_new: float,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recalibrates lyrics timestamps using two-point linear slope calibration."""
        if os.path.isfile(lyrics_content):
            if not output_path:
                stem, ext = os.path.splitext(lyrics_content)
                output_path = f"{stem}.calibrated{ext}"
            try:
                with open(lyrics_content, "r", encoding="utf-8", errors="ignore") as f:
                    lyrics_content = f.read()
            except Exception as e:
                return {"success": False, "error": f"Failed to read lyrics file: {e}"}
        return lyrics_retimer.retime_lyrics(
            lyrics_content, t1_old=t1_old, t1_new=t1_new, t2_old=t2_old, t2_new=t2_new, output_path=output_path
        )

    # ------------------ Phase 21: High-Res Spectrum & Forensics ------------------
    def analyze_audio_spectrum(self, file_path: str, max_sec: float = 60.0) -> Dict[str, Any]:
        """Analyzes audio frequency spectrum, bandwidth rolloff, and genuine Hi-Res status."""
        return spectrum_analyzer.analyze_spectrum(file_path, max_duration_sec=max_sec)

    # ------------------ Phase 21: Dynamic De-Clipper & Expander ------------------
    def declip_audio_track(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        expansion_db: float = 2.0,
        headroom_db: float = 4.0,
    ) -> Dict[str, Any]:
        """Reconstructs clipped digital waveform peaks and applies multiband dynamic expansion."""
        return audio_declipper.declip_audio(
            input_path, output_path=output_path, expansion_db=expansion_db, headroom_db=headroom_db
        )

    # ------------------ Phase 21: Smart Silence Track Splitter -------------------
    def auto_split_track_silence(
        self,
        input_path: str,
        output_dir: Optional[str] = None,
        silence_threshold_db: float = -42.0,
        min_silence_sec: float = 1.5,
        min_track_sec: float = 15.0,
    ) -> Dict[str, Any]:
        """Detects silence gaps, generates Red Book CUE sheet, and splits into individual tracks."""
        return track_splitter.auto_split_audio(
            input_path,
            output_dir=output_dir,
            silence_threshold_db=silence_threshold_db,
            min_silence_sec=min_silence_sec,
            min_track_sec=min_track_sec,
        )

    # ------------------ Phase 21: Synchronized Lyrics Video Maker ----------------
    def render_lyrics_karaoke_video(
        self,
        audio_path: str,
        lrc_path: Optional[str] = None,
        output_path: Optional[str] = None,
        resolution: str = "1080p",
    ) -> Dict[str, Any]:
        """Generates synchronized lyrics karaoke video / interactive HTML5 presentation."""
        return lyrics_video_maker.generate_lyrics_video(
            audio_path, lrc_path=lrc_path, output_path=output_path, resolution=resolution
        )

    # ------------------ Phase 22: Sinc Upsampler & Apodizing Studio ------------------
    def upsample_audio_track(
        self,
        input_path: str,
        target_sr: int = 192000,
        output_path: Optional[str] = None,
        filter_type: str = "linear",
    ) -> Dict[str, Any]:
        """Upsamples audio using bandlimited Whittaker-Shannon polyphase sinc interpolation."""
        return audio_upsampler.upsample_audio(
            input_path, target_sr=target_sr, output_path=output_path, filter_type=filter_type
        )

    # ------------------ Phase 22: Smart CUE Sheet Doctor & Validator ------------------
    def audit_and_fix_cue_sheet(
        self,
        cue_path: str,
        target_audio: Optional[str] = None,
        output_cue_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Audits, heals missing FILE references, fixes sector frames, and re-encodes CUE to UTF-8."""
        return cue_fixer.audit_and_fix_cue(
            cue_path, target_audio_file=target_audio, output_cue_path=output_cue_path
        )

    # ------------------ Phase 22: Room Acoustic IR Synthesizer ------------------------
    def generate_room_impulse_response(
        self,
        room_preset: str = "room",
        rt60_sec: Optional[float] = None,
        sample_rate: int = 48000,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesizes calibrated stereo acoustic impulse response (WAV) using image-source model."""
        return room_ir_synthesizer.synthesize_impulse_response(
            room_preset=room_preset, rt60_sec=rt60_sec, sample_rate=sample_rate, output_path=output_path
        )

    # ------------------ Phase 22: Word-by-Word LRC to ASS Subtitle Converter ----------
    def convert_lrc_to_ass_subtitles(
        self,
        lrc_path: str,
        output_path: Optional[str] = None,
        style_preset: str = "karaoke",
        primary_color: str = "#FFD700",
        export_srt: bool = False,
    ) -> Dict[str, Any]:
        """Converts LRC/ELRC into broadcast ASS karaoke subtitles with syllable wipe animation."""
        return lrc_to_ass_converter.convert_lrc_to_subtitles(
            lrc_path=lrc_path,
            output_path=output_path,
            style_preset=style_preset,
            primary_color_hex=primary_color,
            export_srt=export_srt,
        )

    # ------------------ Phase 23: DSD to PCM & DoP Decimator Studio -------------------
    def convert_dsd_stream(
        self,
        input_path: str,
        target_sr: int = 88200,
        output_path: Optional[str] = None,
        dop_mode: bool = False,
    ) -> Dict[str, Any]:
        """Converts 1-bit DSD stream to Hi-Res PCM or DoP v1.1 USB DAC stream."""
        return dsd_converter.process_dsd_stream(
            input_path=input_path, target_pcm_rate=target_sr, output_path=output_path, dop_mode=dop_mode
        )

    # ------------------ Phase 23: Sub-Sample Phase & Delay Aligner --------------------
    def align_subsample_phase(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        max_delay_ms: float = 10.0,
        target_channel: str = "auto",
    ) -> Dict[str, Any]:
        """Measures and aligns sub-sample inter-channel time delay to eliminate comb filtering."""
        return subsample_delay.align_audio_phase(
            input_path=input_path,
            output_path=output_path,
            max_delay_ms=max_delay_ms,
            target_channel=target_channel,
        )

    # ------------------ Phase 23: Mastering Brickwall Limiter & True-Peak -------------
    def apply_mastering_limiter(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        ceiling_db: float = -1.0,
        threshold_db: float = -3.0,
        release_ms: float = 120.0,
    ) -> Dict[str, Any]:
        """Applies lookahead true-peak brickwall limiting with 4x oversampled ISP detection."""
        return mastering_limiter.process_mastering_limiter(
            input_path=input_path,
            output_path=output_path,
            ceiling_db=ceiling_db,
            threshold_db=threshold_db,
            release_ms=release_ms,
        )

    # ------------------ Phase 23: Album Art Studio & Cover Optimizer ------------------
    def manage_album_artwork(
        self,
        target_path: str,
        action: str = "report",
        export_companion: bool = False,
    ) -> Dict[str, Any]:
        """Audits, extracts companion cover.jpg, or strips bloated embedded album art."""
        return album_art_studio.scan_and_manage_artwork(
            target_path=target_path, action=action, export_companion=export_companion
        )

    # ------------------ Phase 24: Multiband Dynamic De-Esser Studio ------------------
    def deess_audio_track(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        sibilance_freq_hz: float = 6500.0,
        threshold_dbfs: float = -18.0,
        max_reduction_db: float = -9.0,
        listen_sibilance: bool = False,
    ) -> Dict[str, Any]:
        """Dynamically attenuates harsh vocal sibilance and harsh frequencies."""
        return audio_deesser.process_deesser(
            input_path=input_path,
            output_path=output_path,
            sibilance_freq_hz=sibilance_freq_hz,
            threshold_dbfs=threshold_dbfs,
            max_reduction_db=max_reduction_db,
            listen_sibilance=listen_sibilance,
        )

    # ------------------ Phase 24: M/S Spatial Width & Monomaker Studio ------------------
    def process_midside_spatial(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        width_percent: float = 125.0,
        monomaker_hz: float = 120.0,
        mid_gain_db: float = 0.0,
        side_gain_db: float = 0.0,
        side_air_db: float = 0.0,
    ) -> Dict[str, Any]:
        """Applies Mid/Side stereo widening, elliptical low-end mono filter, and high-frequency air."""
        return midside_processor.process_midside(
            input_path=input_path,
            output_path=output_path,
            width_percent=width_percent,
            monomaker_hz=monomaker_hz,
            mid_gain_db=mid_gain_db,
            side_gain_db=side_gain_db,
            side_air_db=side_air_db,
        )

    # ------------------ Phase 24: Lossless Audio Watermark Studio ------------------
    def manage_audio_watermark(
        self,
        input_path: str,
        payload_text: str = "",
        action: str = "detect",
        output_path: Optional[str] = None,
        strength_db: float = -65.0,
    ) -> Dict[str, Any]:
        """Embeds or forensically detects inaudible ultrasonic FSK and RIFF chunk watermarks."""
        if action == "embed":
            return audio_watermark.embed_watermark(
                input_path=input_path,
                payload_text=payload_text,
                output_path=output_path,
                strength_db=strength_db,
            )
        else:
            return audio_watermark.detect_watermark(input_path=input_path)

    # ------------------ Phase 24: Broadcast Cue Marker & Chapter Studio ------------------
    def manage_cue_markers(
        self,
        input_path: str,
        timestamps_text: Optional[str] = None,
        export_cue_path: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Imports timestamps, embeds sample-accurate cue markers into WAV/FLAC, or exports CUE sheets."""
        if timestamps_text and timestamps_text.strip():
            markers = cue_markers.parse_timestamp_text(timestamps_text.strip())
            if export_cue_path:
                cue_str = cue_markers.export_cue_sheet(markers, input_path)
                with open(export_cue_path, "w", encoding="utf-8") as f:
                    f.write(cue_str)
            out_file = output_path or input_path
            return cue_markers.write_cue_markers(input_path, markers, output_path=out_file)
        elif export_cue_path:
            res = cue_markers.read_cue_markers(input_path)
            markers = res.get("markers", [])
            cue_str = cue_markers.export_cue_sheet(markers, input_path)
            with open(export_cue_path, "w", encoding="utf-8") as f:
                f.write(cue_str)
            return {
                "success": True,
                "exported_cue": export_cue_path,
                "marker_count": len(markers),
                "markers": markers,
            }
        else:
            return cue_markers.read_cue_markers(input_path)

    # ------------------ Phase 25: Analog Tape Saturation & Tube Warmth ------------------
    def emulate_analog_tape(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        drive: float = 2.5,
        tape_speed_ips: float = 15.0,
        warmth: float = 2.0,
        tube_bias: float = 0.5,
        add_hiss: bool = False,
        hiss_db: float = -80.0,
    ) -> Dict[str, Any]:
        """Simulates magnetic tape saturation, tube 2nd harmonics, and head-bump bass response."""
        return analog_tape_emulator.process_analog_tape(
            input_path=input_path,
            output_path=output_path,
            drive=drive,
            tape_speed_ips=tape_speed_ips,
            warmth=warmth,
            tube_bias=tube_bias,
            add_hiss=add_hiss,
            hiss_db=hiss_db,
        )

    # ------------------ Phase 25: Multi-Rate Pitch & Formant Vocal Resizer ------------------
    def shift_vocal_formants(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        pitch_semitones: float = 0.0,
        formant_ratio: float = 1.0,
        preserve_formants: bool = True,
    ) -> Dict[str, Any]:
        """Transposes pitch independently of vocal tract formants to eliminate chipmunk effect."""
        return formant_shifter.process_formant_shifter(
            input_path=input_path,
            output_path=output_path,
            pitch_semitones=pitch_semitones,
            formant_ratio=formant_ratio,
            preserve_formants=preserve_formants,
        )

    # ------------------ Phase 25: Mastering Loudness War & Dynamic Spread ------------------
    def analyze_loudness_spread(
        self,
        input_path: str,
        target_lufs: float = -14.0,
    ) -> Dict[str, Any]:
        """Measures EBU R128 BS.1770-4 gated LUFS, LRA dynamic spread, crest factor, and streaming penalties."""
        return loudness_war_studio.analyze_loudness_war(
            file_path=input_path,
            target_lufs=target_lufs,
        )

    # ------------------ Phase 25: Multi-Track Stems & Audio Remixer ------------------
    def remix_audio_stems(
        self,
        stems_dict: Dict[str, str],
        output_path: Optional[str] = None,
        gains_db: Optional[Dict[str, float]] = None,
        pans: Optional[Dict[str, float]] = None,
        mutes: Optional[Dict[str, bool]] = None,
        preset: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mixes and balances 4-track separated stems (Vocals, Drums, Bass, Other) into 24-bit WAV master."""
        return stems_remixer.remix_stems(
            stems_dict=stems_dict,
            output_path=output_path,
            gains_db=gains_db,
            pans=pans,
            mutes=mutes,
            preset=preset,
        )

    # ------------------ Phase 26: Audiophile Transient Shaper & Drum Punch ------------------
    def shape_audio_transients(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        attack_db: float = 0.0,
        sustain_db: float = 0.0,
        attack_speed_ms: float = 4.0,
        sustain_speed_ms: float = 80.0,
        soft_clip: bool = True,
    ) -> Dict[str, Any]:
        """Shapes percussive attack transients and acoustic sustain tail levels."""
        return transient_shaper.run_transient_shaping(
            input_path=input_path,
            output_path=output_path,
            attack_db=attack_db,
            sustain_db=sustain_db,
            attack_speed_ms=attack_speed_ms,
            sustain_speed_ms=sustain_speed_ms,
            soft_clip=soft_clip,
        )

    # ------------------ Phase 26: Binaural 3D Room & Headphone Virtualizer ------------------
    def virtualize_binaural_room(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        speaker_angle_deg: float = 30.0,
        distance_m: float = 1.8,
        crossfeed_amount: float = 1.0,
        room_ambience: float = 0.35,
        preset: str = "control_room",
    ) -> Dict[str, Any]:
        """Simulates physical studio monitors in an acoustically treated control room over headphones."""
        return binaural_virtualizer.run_binaural_virtualization(
            input_path=input_path,
            output_path=output_path,
            speaker_angle_deg=speaker_angle_deg,
            distance_m=distance_m,
            crossfeed_amount=crossfeed_amount,
            room_ambience=room_ambience,
            preset=preset,
        )

    # ------------------ Phase 26: Broadcast Noise Gate & Downward Expander ------------------
    def process_broadcast_noisegate(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        threshold_db: float = -40.0,
        reduction_db: float = -60.0,
        ratio: float = 10.0,
        attack_ms: float = 1.5,
        hold_ms: float = 40.0,
        release_ms: float = 120.0,
        lookahead_ms: float = 2.0,
        hysteresis_db: float = 3.0,
    ) -> Dict[str, Any]:
        """Applies lookahead noise gating and downward expansion to eliminate hum, hiss, and spill."""
        return audio_noisegate.run_noise_gate(
            input_path=input_path,
            output_path=output_path,
            threshold_db=threshold_db,
            reduction_db=reduction_db,
            ratio=ratio,
            attack_ms=attack_ms,
            hold_ms=hold_ms,
            release_ms=release_ms,
            lookahead_ms=lookahead_ms,
            hysteresis_db=hysteresis_db,
        )

    # ------------------ Phase 26: Stereo Ping-Pong & Multi-Tap Tape Echo ------------------
    def apply_tape_echo_delay(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        delay_ms: float = 375.0,
        feedback_pct: float = 45.0,
        damping_hz: float = 3800.0,
        flutter_pct: float = 0.12,
        drive: float = 1.3,
        dry_wet_pct: float = 35.0,
        ping_pong: bool = True,
    ) -> Dict[str, Any]:
        """Emulates vintage Roland Space Echo tape delay and analog BBD ping-pong echoes."""
        return tape_echo_delay.run_tape_echo(
            input_path=input_path,
            output_path=output_path,
            delay_ms=delay_ms,
            feedback_pct=feedback_pct,
            damping_hz=damping_hz,
            flutter_pct=flutter_pct,
            drive=drive,
            dry_wet_pct=dry_wet_pct,
            ping_pong=ping_pong,
        )

    # ------------------ Phase 27: Universal Release Packager & Offline Manual ------------------
    def package_workstation_release(
        self,
        create_zip: bool = False,
        verify_only: bool = False,
    ) -> Dict[str, Any]:
        """Audits codebase across all 27 phases, computes cryptographic manifests, and optionally creates distribution zip."""
        return release_packager.audit_and_package(
            create_zip=create_zip,
            verify_only=verify_only,
        )

    def generate_workstation_manual(
        self,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates the interactive single-file offline workstation manual and DSP handbook."""
        return docs_generator.generate_offline_manual(output_path=output_path)

    def open_offline_manual(self) -> Dict[str, Any]:
        """Opens the offline manual in the default web browser."""
        manual_path = docs_generator.DEFAULT_MANUAL_PATH
        if not manual_path.exists():
            docs_generator.generate_offline_manual()
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(manual_path)}")
        return {"success": True, "path": str(manual_path)}

    # ------------------ Phase 28: VST3 & CLAP Audio Plugin Host & Rack ------------------
    def scan_system_plugins(self, custom_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Scans host system and virtual registry for VST3 and CLAP audio plugins."""
        return plugin_host.scan_installed_plugins(custom_dirs=custom_dirs)

    def process_vst_rack(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        rack_slots: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Processes audio file through a serial multi-slot VST3/CLAP effect rack chain."""
        return plugin_host.process_plugin_rack(
            input_path=input_path,
            output_path=output_path,
            rack_slots=rack_slots,
        )

    def get_vst_factory_presets(self) -> Dict[str, Any]:
        """Returns factory rack chain presets."""
        return plugin_host.FACTORY_PRESETS

    # ------------------ Phase 29: Dolby Atmos 7.1.4 Spatializer & Multichannel Renderer ------------------
    def render_spatial_714(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        mode: str = "binaural",
        format_type: str = "7.1.4",
        lfe_cutoff_hz: float = 80.0,
        height_level: float = 0.35,
        spread: float = 1.15,
    ) -> Dict[str, Any]:
        """Renders stereo audio into an immersive 7.1.4 Dolby Atmos spatial bed (binaural or discrete multichannel)."""
        return spatial_multichannel.render_spatial_714(
            input_path=input_path,
            output_path=output_path,
            mode=mode,
            format_type=format_type,
            lfe_cutoff_hz=lfe_cutoff_hz,
            height_level=height_level,
            spread=spread,
        )

    # ------------------ Phase 30: British Class-A Console Channel Strip & SSL G-Comp ------------------
    def render_console_strip(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        preset: str = "master_bus_glue",
        custom_ssl: Optional[Dict[str, Any]] = None,
        custom_neve: Optional[Dict[str, Any]] = None,
        crosstalk_db: float = -65.0,
        analog_noise: bool = False,
        output_gain_db: float = 0.0,
    ) -> Dict[str, Any]:
        """Renders audio through the British Class-A Console Channel Strip & SSL 4000 G-Master Bus Compressor."""
        return console_channel_strip.render_console_strip(
            input_path=input_path,
            output_path=output_path,
            preset=preset,
            custom_ssl=custom_ssl,
            custom_neve=custom_neve,
            crosstalk_db=crosstalk_db,
            analog_noise=analog_noise,
            output_gain_db=output_gain_db,
        )

    def get_console_presets(self) -> Dict[str, Any]:
        """Returns factory presets for British Class-A Console & SSL G-Master Bus Studio."""
        return console_channel_strip.FACTORY_PRESETS

    # ------------------ Phase 31: Higher-Order Ambisonics (HOA) & 360 VR Spatializer ------------------
    def render_ambisonic_hoa(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        order: int = 3,
        mode: str = "binaural",
        trajectory_type: str = "orbit_helix",
        base_azimuth_deg: float = 0.0,
        base_elevation_deg: float = 0.0,
        orbit_period_sec: float = 12.0,
    ) -> Dict[str, Any]:
        """Encodes stereo audio into Higher-Order Ambisonics (1st/2nd/3rd order) and renders binaural 3D or AmbiX B-format."""
        return ambisonic_hoa.render_ambisonic_hoa(
            input_path=input_path,
            output_path=output_path,
            order=order,
            mode=mode,
            trajectory_type=trajectory_type,
            base_azimuth_deg=base_azimuth_deg,
            base_elevation_deg=base_elevation_deg,
            orbit_period_sec=orbit_period_sec,
        )

    # ------------------ Phase 32: Psychoacoustic Subharmonic Bass Synthesizer ------------------
    def get_subharmonic_presets(self) -> Dict[str, Any]:
        """Returns the dictionary of factory presets for Subharmonic Bass Studio."""
        return subharmonic_bass.FACTORY_PRESETS

    def render_subharmonic_bass(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        preset: str = "club_sub_boom",
        sub_24_36_gain: Optional[float] = None,
        sub_36_56_gain: Optional[float] = None,
        maxxbass_intensity: Optional[float] = None,
        maxxbass_cutoff_hz: Optional[float] = None,
        tube_drive: Optional[float] = None,
        subsonic_hpf_hz: Optional[float] = None,
        monomaker_hz: Optional[float] = None,
        dry_wet: Optional[float] = None,
        output_gain_db: float = 0.0,
    ) -> Dict[str, Any]:
        """Synthesizes subharmonics and psychoacoustic missing fundamental overtones for deep low-end."""
        return subharmonic_bass.render_subharmonic_bass(
            input_path=input_path,
            output_path=output_path,
            preset=preset,
            sub_24_36_gain=sub_24_36_gain,
            sub_36_56_gain=sub_36_56_gain,
            maxxbass_intensity=maxxbass_intensity,
            maxxbass_cutoff_hz=maxxbass_cutoff_hz,
            tube_drive=tube_drive,
            subsonic_hpf_hz=subsonic_hpf_hz,
            monomaker_hz=monomaker_hz,
            dry_wet=dry_wet,
            output_gain_db=output_gain_db,
        )

    # ------------------ Phase 33: Dynamic Spectral Resonance Suppressor ------------------
    def get_resonance_presets(self) -> Dict[str, Any]:
        """Returns factory presets for Dynamic Spectral Resonance Suppressor Studio."""
        return resonance_suppressor.FACTORY_PRESETS

    def render_resonance_suppressor(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        preset: str = "tame_harshness",
        depth: Optional[float] = None,
        threshold_db: Optional[float] = None,
        sharpness: Optional[float] = None,
        low_cut_hz: Optional[float] = None,
        high_cut_hz: Optional[float] = None,
        listen_mode: bool = False,
        dry_wet: Optional[float] = None,
        output_gain_db: float = 0.0,
    ) -> Dict[str, Any]:
        """Dynamically tracks and surgically de-resonates harsh acoustic peaks and sibilance."""
        return resonance_suppressor.render_resonance_suppressor(
            input_path=input_path,
            output_path=output_path,
            preset=preset,
            depth=depth,
            threshold_db=threshold_db,
            sharpness=sharpness,
            low_cut_hz=low_cut_hz,
            high_cut_hz=high_cut_hz,
            listen_mode=listen_mode,
            dry_wet=dry_wet,
            output_gain_db=output_gain_db,
        )

    # ------------------ Phase 34: Vintage Optical & Variable-Mu Compressor ------------------
    def get_vintage_compressor_presets(self) -> Dict[str, Any]:
        """Returns factory presets for Vintage Optical & Variable-Mu Master Compressor Studio."""
        return vintage_compressor.FACTORY_PRESETS

    def render_vintage_compressor(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        preset: str = "la2a_smooth_vocal",
        mode: Optional[str] = None,
        peak_reduction: Optional[float] = None,
        sidechain_hpf_hz: Optional[float] = None,
        hf_emphasis: Optional[bool] = None,
        time_constant: Optional[int] = None,
        tube_drive: Optional[float] = None,
        makeup_gain_db: Optional[float] = None,
        dry_wet: Optional[float] = None,
        stereo_link: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Renders audio through Teletronix LA-2A or Fairchild 670 vintage dynamics physical model."""
        return vintage_compressor.render_vintage_compressor(
            input_path=input_path,
            output_path=output_path,
            preset=preset,
            mode=mode,
            peak_reduction=peak_reduction,
            sidechain_hpf_hz=sidechain_hpf_hz,
            hf_emphasis=hf_emphasis,
            time_constant=time_constant,
            tube_drive=tube_drive,
            makeup_gain_db=makeup_gain_db,
            dry_wet=dry_wet,
            stereo_link=stereo_link,
        )

    # ------------------ Phase 35: The Grand Workstation Zenith Suite ------------------
    def get_zenith_profiles(self) -> Dict[str, Any]:
        """Returns macro master profiles for The Grand Workstation Zenith Suite."""
        return zenith_orchestrator.ZENITH_PROFILES

    def render_zenith_master(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        profile: str = "audiophile_pure_master",
        stage_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executes the complete 7-stage Zenith Master Orchestration pipeline."""
        return zenith_orchestrator.render_zenith_master(
            input_path=input_path,
            output_path=output_path,
            profile=profile,
            stage_overrides=stage_overrides,
        )

    # ------------------ Exclusive Audio Mode & Hardware DAC Output ------------------
    def get_audio_output_devices(self) -> Dict[str, Any]:
        """Returns all system audio output devices, host APIs, and registered ASIO drivers."""
        return exclusive_audio_engine.get_engine().query_devices()

    def get_exclusive_audio_config(self) -> Dict[str, Any]:
        """Returns current exclusive audio engine settings."""
        return exclusive_audio_engine.get_engine().get_config()

    def set_exclusive_audio_config(
        self,
        mode: Optional[str] = None,
        device_id: Optional[int] = None,
        buffer_size: Optional[int] = None,
        bit_perfect_lock: Optional[bool] = None,
        volume: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Updates exclusive audio output configuration."""
        return exclusive_audio_engine.get_engine().set_config(
            mode=mode,
            device_id=device_id,
            buffer_size=buffer_size,
            bit_perfect_lock=bit_perfect_lock,
            volume=volume,
        )

    def test_exclusive_device(
        self,
        device_id: Optional[int] = None,
        sample_rate: int = 48000,
    ) -> Dict[str, Any]:
        """Plays a brief 440 Hz test chime in Exclusive mode to verify DAC hardware lock."""
        return exclusive_audio_engine.get_engine().play_test_tone(
            device_id=device_id,
            sample_rate=sample_rate,
        )

    def exclusive_play(self, file_path: str, start_time: float = 0.0) -> Dict[str, Any]:
        """Initiates bit-perfect hardware playback bypassing the OS mixer."""
        return exclusive_audio_engine.get_engine().play(file_path, start_time=start_time)

    def exclusive_pause(self) -> Dict[str, Any]:
        """Pauses exclusive hardware playback."""
        exclusive_audio_engine.get_engine().pause()
        return {"status": "paused"}

    def exclusive_resume(self) -> Dict[str, Any]:
        """Resumes exclusive hardware playback."""
        exclusive_audio_engine.get_engine().resume()
        return {"status": "resumed"}

    def exclusive_seek(self, position_sec: float) -> Dict[str, Any]:
        """Seeks within exclusive hardware playback stream."""
        exclusive_audio_engine.get_engine().seek(position_sec)
        return {"status": "seeked", "position": position_sec}

    def exclusive_stop(self) -> Dict[str, Any]:
        """Stops exclusive hardware playback and releases device lock."""
        exclusive_audio_engine.get_engine().stop()
        return {"status": "stopped"}

    def get_exclusive_status(self) -> Dict[str, Any]:
        """Returns real-time telemetry of the active bit-perfect audio stream."""
        return exclusive_audio_engine.get_engine().get_status()

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
