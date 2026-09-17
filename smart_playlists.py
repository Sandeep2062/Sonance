"""
smart_playlists.py - Sonance Smart Dynamic Auto-Playlists Engine

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Dynamically evaluates and builds virtual playlists from local library metadata:
- Top Favorites
- Pure Lossless (FLAC, WAV, ALAC)
- Karaoke Ready (files with matching .lrc synchronized lyrics)
- Doctor's Queue (missing lyrics or incomplete tags)
- Recently Added (added/modified in the last 30 days)
- Decades (80s, 90s, 2000s, 2010s, 2020s)
"""

import os
import time
from typing import Dict, Any, List, Optional
import lyrics_engine


AUDIO_EXTS = (".mp3", ".flac", ".m4a", ".ogg", ".wav")


SMART_PLAYLIST_DEFINITIONS = [
    {
        "id": "smart_lossless",
        "name": "Pure Lossless",
        "description": "Bit-perfect FLAC, WAV, and ALAC audiophile studio tracks",
        "icon": "💎"
    },
    {
        "id": "smart_karaoke",
        "name": "Karaoke Ready",
        "description": "Tracks with verified .lrc synchronized lyrics",
        "icon": "🎤"
    },
    {
        "id": "smart_recent",
        "name": "Recently Added",
        "description": "Music added or downloaded within the last 30 days",
        "icon": "📅"
    },
    {
        "id": "smart_doctor",
        "name": "Doctor's Queue",
        "description": "Tracks missing lyrics or metadata tags needing attention",
        "icon": "🩺"
    },
    {
        "id": "smart_2020s",
        "name": "2020s Modern",
        "description": "Hits and releases from 2020 to present",
        "icon": "⚡"
    },
    {
        "id": "smart_2010s",
        "name": "2010s Era",
        "description": "Tracks released between 2010 and 2019",
        "icon": "📻"
    },
    {
        "id": "smart_2000s",
        "name": "2000s Classics",
        "description": "Tracks released between 2000 and 2009",
        "icon": "💿"
    },
    {
        "id": "smart_90s",
        "name": "90s Vintage",
        "description": "Golden era 90s music (1990 - 1999)",
        "icon": "📼"
    },
]


def scan_folder_tracks(target_folder: str) -> List[Dict[str, Any]]:
    """Recursively scans folder for all supported audio tracks with metadata."""
    if not target_folder or not os.path.exists(target_folder):
        return []

    tracks = []
    now = time.time()
    thirty_days_sec = 30 * 86400

    for root, _, files in os.walk(target_folder):
        for f in files:
            if f.lower().endswith(AUDIO_EXTS):
                full_path = os.path.join(root, f)
                lrc_path = os.path.splitext(full_path)[0] + ".lrc"
                
                try:
                    mtime = os.path.getmtime(full_path)
                    size = os.path.getsize(full_path)
                except Exception:
                    mtime = now
                    size = 0

                meta = lyrics_engine.get_audio_metadata(full_path)
                fn_artist, fn_title = lyrics_engine.clean_filename_to_artist_title(f)
                artist = meta.get("artist") or fn_artist or "Unknown"
                title = meta.get("title") or fn_title or f
                album = meta.get("album") or "Unknown"
                fmt = (meta.get("format") or os.path.splitext(f)[1].replace(".", "")).upper()
                year_str = str(meta.get("year") or "")
                year = int(year_str[:4]) if year_str[:4].isdigit() else 0

                tracks.append({
                    "path": full_path,
                    "filename": f,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "duration": meta.get("duration") or 0,
                    "format": fmt,
                    "quality": meta.get("quality") or fmt,
                    "year": year,
                    "has_lrc": os.path.exists(lrc_path),
                    "is_recent": (now - mtime) <= thirty_days_sec,
                    "mtime": mtime,
                    "size_bytes": size,
                })
    return tracks


def filter_tracks_for_smart_playlist(playlist_id: str, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Applies smart filtering criteria to track collection."""
    if playlist_id == "smart_lossless":
        return [t for t in tracks if t["format"] in ("FLAC", "WAV", "ALAC")]
    elif playlist_id == "smart_karaoke":
        return [t for t in tracks if t["has_lrc"]]
    elif playlist_id == "smart_recent":
        # Sort newest first
        recents = [t for t in tracks if t["is_recent"]]
        recents.sort(key=lambda x: x["mtime"], reverse=True)
        return recents
    elif playlist_id == "smart_doctor":
        return [t for t in tracks if not t["has_lrc"] or t["artist"] == "Unknown" or t["album"] == "Unknown"]
    elif playlist_id == "smart_2020s":
        return [t for t in tracks if t["year"] >= 2020]
    elif playlist_id == "smart_2010s":
        return [t for t in tracks if 2010 <= t["year"] <= 2019]
    elif playlist_id == "smart_2000s":
        return [t for t in tracks if 2000 <= t["year"] <= 2009]
    elif playlist_id == "smart_90s":
        return [t for t in tracks if 1990 <= t["year"] <= 1999]
    return tracks


def get_smart_playlists(target_folder: str) -> List[Dict[str, Any]]:
    """Returns all smart playlist definitions with live track count badge."""
    all_tracks = scan_folder_tracks(target_folder)
    results = []

    for defn in SMART_PLAYLIST_DEFINITIONS:
        matched = filter_tracks_for_smart_playlist(defn["id"], all_tracks)
        results.append({
            "id": defn["id"],
            "name": defn["name"],
            "description": defn["description"],
            "icon": defn["icon"],
            "count": len(matched)
        })
    return results


def get_smart_playlist_tracks(playlist_id: str, target_folder: str) -> List[Dict[str, Any]]:
    """Returns detailed tracks for a specific smart playlist."""
    all_tracks = scan_folder_tracks(target_folder)
    return filter_tracks_for_smart_playlist(playlist_id, all_tracks)


def export_smart_playlist_m3u8(playlist_id: str, target_folder: str, output_path: str) -> Dict[str, Any]:
    """Exports smart playlist to a standard .m3u8 playlist file."""
    tracks = get_smart_playlist_tracks(playlist_id, target_folder)
    if not tracks:
        return {"success": False, "error": "No tracks found in smart playlist"}

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:Sonance Smart Playlist - {playlist_id}\n")
            for t in tracks:
                dur = int(t.get("duration", 0))
                artist = t.get("artist", "Unknown")
                title = t.get("title", "Unknown")
                path = t.get("path", "")
                f.write(f"#EXTINF:{dur},{artist} - {title}\n")
                f.write(f"{path}\n")
        return {"success": True, "path": output_path, "total_tracks": len(tracks)}
    except Exception as e:
        return {"success": False, "error": str(e)}
