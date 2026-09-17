#!/usr/bin/env python3
"""
Sonance - Subsonic / Navidrome / Jellyfin Personal Cloud Streaming Client
========================================================================
Connects Sonance to self-hosted personal cloud music servers using the
standard Subsonic REST API (v1.16.1). Supports Navidrome, Subsonic, Airsonic,
Jellyfin, and Ampache with MD5 token authentication.

Author: Sandeep Khadka (Sandeep2062) <sandeepkhadka9090@gmail.com>
License: GNU GPLv3 with Commons Clause
"""

import os
import hashlib
import secrets
import urllib.parse
from typing import Dict, Any, List, Optional
import requests

CLIENT_NAME = "Sonance"
API_VERSION = "1.16.1"
DEFAULT_TIMEOUT = 10


def _normalize_server_url(server_url: str) -> str:
    """Normalizes server URL, removing trailing slashes and ensuring http/https."""
    url = (server_url or "").strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    if url.endswith("/rest"):
        url = url[:-5]
    return url


def generate_auth_params(username: str, password: str) -> Dict[str, str]:
    """
    Generates standard Subsonic token-based authentication parameters.
    Token = md5(password + salt)
    """
    salt = secrets.token_hex(6)
    token = hashlib.md5((password + salt).encode("utf-8")).hexdigest()
    return {
        "u": username,
        "s": salt,
        "t": token,
        "v": API_VERSION,
        "c": CLIENT_NAME,
        "f": "json",
    }


def test_connection(server_url: str, username: str, password: str) -> Dict[str, Any]:
    """
    Pings the Subsonic server to verify connectivity and authentication.
    """
    base_url = _normalize_server_url(server_url)
    auth = generate_auth_params(username, password)
    ping_url = f"{base_url}/rest/ping.view"

    try:
        resp = requests.get(ping_url, params=auth, timeout=DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {resp.status_code}: {resp.reason}",
            }

        data = resp.json().get("subsonic-response", {})
        status = data.get("status")

        if status == "ok":
            return {
                "success": True,
                "server_url": base_url,
                "api_version": data.get("version", API_VERSION),
                "server_version": data.get("serverVersion", "Unknown"),
                "type": data.get("type", "Subsonic / Navidrome"),
            }
        else:
            err = data.get("error", {})
            return {
                "success": False,
                "error": err.get("message", "Authentication or server error"),
                "code": err.get("code", 0),
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Connection failed: {str(e)}",
        }


def get_music_folders(server_url: str, username: str, password: str) -> Dict[str, Any]:
    """Retrieves top-level configured music folders from the server."""
    base_url = _normalize_server_url(server_url)
    auth = generate_auth_params(username, password)
    url = f"{base_url}/rest/getMusicFolders.view"

    try:
        resp = requests.get(url, params=auth, timeout=DEFAULT_TIMEOUT)
        data = resp.json().get("subsonic-response", {})
        if data.get("status") == "ok":
            folders = data.get("musicFolders", {}).get("musicFolder", [])
            if isinstance(folders, dict):
                folders = [folders]
            return {"success": True, "folders": folders}
        return {"success": False, "error": data.get("error", {}).get("message", "Failed to get folders")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_artists(server_url: str, username: str, password: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves artist directory indexes from the server."""
    base_url = _normalize_server_url(server_url)
    auth = generate_auth_params(username, password)
    if folder_id:
        auth["musicFolderId"] = folder_id

    url = f"{base_url}/rest/getArtists.view"
    try:
        resp = requests.get(url, params=auth, timeout=DEFAULT_TIMEOUT)
        data = resp.json().get("subsonic-response", {})
        if data.get("status") == "ok":
            index_list = data.get("artists", {}).get("index", [])
            artists_flattened = []
            for idx in index_list:
                art_items = idx.get("artist", [])
                if isinstance(art_items, dict):
                    art_items = [art_items]
                for a in art_items:
                    artists_flattened.append({
                        "id": a.get("id"),
                        "name": a.get("name"),
                        "album_count": a.get("albumCount", 0),
                        "cover_art": get_cover_art_url(base_url, username, password, a.get("coverArt", "")),
                    })
            return {"success": True, "artists": artists_flattened, "count": len(artists_flattened)}
        return {"success": False, "error": data.get("error", {}).get("message", "Failed to list artists")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_artist_albums(server_url: str, username: str, password: str, artist_id: str) -> Dict[str, Any]:
    """Retrieves albums for a specific artist."""
    base_url = _normalize_server_url(server_url)
    auth = generate_auth_params(username, password)
    auth["id"] = artist_id

    url = f"{base_url}/rest/getArtist.view"
    try:
        resp = requests.get(url, params=auth, timeout=DEFAULT_TIMEOUT)
        data = resp.json().get("subsonic-response", {})
        if data.get("status") == "ok":
            art_data = data.get("artist", {})
            album_list = art_data.get("album", [])
            if isinstance(album_list, dict):
                album_list = [album_list]

            albums = []
            for alb in album_list:
                albums.append({
                    "id": alb.get("id"),
                    "title": alb.get("name") or alb.get("title"),
                    "artist": alb.get("artist") or art_data.get("name"),
                    "year": alb.get("year"),
                    "song_count": alb.get("songCount", 0),
                    "duration": alb.get("duration", 0),
                    "cover_art": get_cover_art_url(base_url, username, password, alb.get("coverArt", "")),
                })
            return {"success": True, "artist": art_data.get("name"), "albums": albums}
        return {"success": False, "error": data.get("error", {}).get("message", "Failed to get artist")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_album_tracks(server_url: str, username: str, password: str, album_id: str) -> Dict[str, Any]:
    """Retrieves tracklist for a specific album."""
    base_url = _normalize_server_url(server_url)
    auth = generate_auth_params(username, password)
    auth["id"] = album_id

    url = f"{base_url}/rest/getAlbum.view"
    try:
        resp = requests.get(url, params=auth, timeout=DEFAULT_TIMEOUT)
        data = resp.json().get("subsonic-response", {})
        if data.get("status") == "ok":
            alb_data = data.get("album", {})
            song_list = alb_data.get("song", [])
            if isinstance(song_list, dict):
                song_list = [song_list]

            tracks = []
            for s in song_list:
                dur = s.get("duration", 0)
                mins = dur // 60
                secs = dur % 60
                tracks.append({
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "artist": s.get("artist"),
                    "album": s.get("album"),
                    "track_number": s.get("track", 1),
                    "duration": dur,
                    "duration_str": f"{mins}:{secs:02d}",
                    "suffix": s.get("suffix", "mp3").upper(),
                    "bitrate": s.get("bitRate", 320),
                    "stream_url": get_stream_url(base_url, username, password, s.get("id")),
                    "cover_art": get_cover_art_url(base_url, username, password, s.get("coverArt", "")),
                })
            return {
                "success": True,
                "album": alb_data.get("name") or alb_data.get("title"),
                "artist": alb_data.get("artist"),
                "cover_art": get_cover_art_url(base_url, username, password, alb_data.get("coverArt", "")),
                "tracks": tracks,
            }
        return {"success": False, "error": data.get("error", {}).get("message", "Failed to get album tracks")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_cloud(server_url: str, username: str, password: str, query: str) -> Dict[str, Any]:
    """Searches the cloud music library for artists, albums, and songs."""
    base_url = _normalize_server_url(server_url)
    auth = generate_auth_params(username, password)
    auth["query"] = query
    auth["songCount"] = "30"
    auth["albumCount"] = "10"
    auth["artistCount"] = "5"

    url = f"{base_url}/rest/search3.view"
    try:
        resp = requests.get(url, params=auth, timeout=DEFAULT_TIMEOUT)
        data = resp.json().get("subsonic-response", {})
        if data.get("status") == "ok":
            res = data.get("searchResult3", {})
            songs_raw = res.get("song", [])
            if isinstance(songs_raw, dict):
                songs_raw = [songs_raw]

            songs = []
            for s in songs_raw:
                dur = s.get("duration", 0)
                mins = dur // 60
                secs = dur % 60
                songs.append({
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "artist": s.get("artist"),
                    "album": s.get("album"),
                    "track_number": s.get("track", 1),
                    "duration": dur,
                    "duration_str": f"{mins}:{secs:02d}",
                    "suffix": s.get("suffix", "mp3").upper(),
                    "bitrate": s.get("bitRate", 320),
                    "stream_url": get_stream_url(base_url, username, password, s.get("id")),
                    "cover_art": get_cover_art_url(base_url, username, password, s.get("coverArt", "")),
                })
            return {"success": True, "songs": songs, "total": len(songs)}
        return {"success": False, "error": data.get("error", {}).get("message", "Search failed")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_stream_url(
    server_url: str,
    username: str,
    password: str,
    track_id: str,
    max_bitrate: Optional[int] = None,
    audio_format: Optional[str] = None
) -> str:
    """
    Constructs an authenticated, direct streaming URL for a track.
    Can be loaded directly into HTML5 <audio> element.
    """
    base_url = _normalize_server_url(server_url)
    auth = generate_auth_params(username, password)
    auth["id"] = track_id
    if max_bitrate:
        auth["maxBitRate"] = str(max_bitrate)
    if audio_format:
        auth["format"] = audio_format

    query_str = urllib.parse.urlencode(auth)
    return f"{base_url}/rest/stream.view?{query_str}"


def get_cover_art_url(server_url: str, username: str, password: str, cover_id: str, size: int = 300) -> str:
    """Constructs an authenticated cover art image URL."""
    if not cover_id:
        return ""
    base_url = _normalize_server_url(server_url)
    auth = generate_auth_params(username, password)
    auth["id"] = cover_id
    auth["size"] = str(size)
    query_str = urllib.parse.urlencode(auth)
    return f"{base_url}/rest/getCoverArt.view?{query_str}"


if __name__ == "__main__":
    print("Testing Subsonic Cloud Streamer Module...")
    test_auth = generate_auth_params("demo_user", "demo_pass")
    assert "u" in test_auth and "t" in test_auth and "s" in test_auth
    print(f"Token generation verified: u={test_auth['u']}, s={test_auth['s']}")

    stream_url = get_stream_url("http://localhost:4533", "demo_user", "demo_pass", "12345")
    assert "stream.view" in stream_url and "id=12345" in stream_url
    print(f"Stream URL generation verified: {stream_url[:60]}...")
    print("Cloud Streamer unit test passed successfully!")
