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
