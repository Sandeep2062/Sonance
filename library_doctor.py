"""
library_doctor.py - Sonance Music Library Health, Duplicate Finder & Integrity Doctor

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Scans local audio libraries to detect duplicate tracks, rank audio quality (Lossless vs 320k vs 128k),
identify missing cover art and lyrics, and calculate a Library Health Score.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import lyrics_engine


def clean_title_for_comparison(text: str) -> str:
    """Normalizes titles by stripping common suffixes, brackets, and feat credits."""
    if not text:
        return ""
    t = text.lower().strip()
    # Strip feat / ft / featuring
    t = re.sub(r'[\(\[\{]?(?:feat\.?|ft\.?|featuring)[^\)\]\}]*[\)\]\}]?', '', t)
    # Strip official audio / video / lyrics / remastered
    t = re.sub(r'[\(\[\{]?(?:official|remaster(?:ed)?|live|audio|video|lyric[s]?)[^\)\]\}]*[\)\]\}]?', '', t)
    # Strip non-alphanumeric except spaces
    t = re.sub(r'[^\w\s]', '', t)
    return ' '.join(t.split())


def get_format_rank(fmt: str, bitrate: int) -> int:
    """Returns higher score for higher quality audio."""
    fmt = (fmt or "").upper()
    if fmt in ("FLAC", "WAV", "ALAC"):
        return 1000 + bitrate
    if fmt in ("M4A", "AAC"):
        return 500 + bitrate
    if fmt == "OGG":
        return 400 + bitrate
    return bitrate  # MP3


def scan_library_health(target_folder: str) -> Dict[str, Any]:
    """
    Analyzes all audio tracks in the folder, detecting duplicates, missing covers,
    and missing lyrics. Computes an overall Library Health Score (0-100).
    """
    if not target_folder or not os.path.exists(target_folder):
        return {"success": False, "error": "Folder not found"}

    audio_exts = (".mp3", ".flac", ".m4a", ".ogg", ".wav")
    all_tracks: List[Dict[str, Any]] = []

    for root, _, files in os.walk(target_folder):
        for f in files:
            if f.lower().endswith(audio_exts):
                full_path = os.path.join(root, f)
                lrc_path = os.path.splitext(full_path)[0] + ".lrc"

                meta = lyrics_engine.get_audio_metadata(full_path)
                fn_artist, fn_title = lyrics_engine.clean_filename_to_artist_title(f)
                artist = meta["artist"] or fn_artist or "Unknown"
                title = meta["title"] or fn_title or f
                album = meta["album"] or "Unknown"

                all_tracks.append({
                    "path": full_path,
                    "filename": f,
                    "artist": artist,
                    "title": title,
                    "album": album,
                    "clean_artist": clean_title_for_comparison(artist),
                    "clean_title": clean_title_for_comparison(title),
                    "duration": meta["duration"] or 0,
                    "bitrate": meta["bitrate"] or 0,
                    "format": meta["format"] or "MP3",
                    "quality": meta["quality"] or "Unknown",
                    "has_lrc": os.path.exists(lrc_path),
                    "size_bytes": os.path.getsize(full_path),
                })

    total_tracks = len(all_tracks)
    if total_tracks == 0:
        return {
            "success": True,
            "total_tracks": 0,
            "health_score": 100,
            "total_duplicate_groups": 0,
            "total_duplicate_files": 0,
            "duplicate_groups": [],
            "missing_lyrics_count": 0,
            "missing_tags_count": 0,
        }

    # Group tracks for duplicate detection
    groups: Dict[str, List[Dict[str, Any]]] = {}
    missing_lyrics = 0
    missing_tags = 0

    for t in all_tracks:
        if not t["has_lrc"]:
            missing_lyrics += 1
        if t["artist"] == "Unknown" or t["album"] == "Unknown":
            missing_tags += 1

        # Key based on normalized artist + title
        key = f"{t['clean_artist']}___{t['clean_title']}"
        if key not in groups:
            groups[key] = []
        groups[key].append(t)

    # Detect duplicate candidates
    duplicate_groups = []
    total_duplicate_files = 0

    for key, tracks in groups.items():
        if len(tracks) > 1:
            # Check duration tolerance (within 4 seconds of each other)
            durations = [t["duration"] for t in tracks if t["duration"] > 0]
            if durations and (max(durations) - min(durations) <= 4.0):
                # Sort descending by quality rank (best first)
                sorted_tracks = sorted(
                    tracks,
                    key=lambda x: get_format_rank(x["format"], x["bitrate"]),
                    reverse=True,
                )

                best_track = sorted_tracks[0]
                duplicates_to_review = []

                for idx, tr in enumerate(sorted_tracks):
                    duplicates_to_review.append({
                        "path": tr["path"],
                        "filename": tr["filename"],
                        "artist": tr["artist"],
                        "title": tr["title"],
                        "album": tr["album"],
                        "duration": tr["duration"],
                        "quality": tr["quality"],
                        "format": tr["format"],
                        "size_mb": round(tr["size_bytes"] / (1024 * 1024), 2),
                        "is_recommended_keep": idx == 0,
                    })

                duplicate_groups.append({
                    "artist": best_track["artist"],
                    "title": best_track["title"],
                    "count": len(sorted_tracks),
                    "tracks": duplicates_to_review,
                })
                total_duplicate_files += (len(sorted_tracks) - 1)

    # Calculate Health Score (100 base, deductions for duplicates & missing metadata)
    dup_penalty = min(30, (total_duplicate_files / max(1, total_tracks)) * 50)
    lrc_penalty = min(35, (missing_lyrics / max(1, total_tracks)) * 40)
    tag_penalty = min(35, (missing_tags / max(1, total_tracks)) * 30)

    health_score = max(0, min(100, round(100 - (dup_penalty + lrc_penalty + tag_penalty))))

    return {
        "success": True,
        "total_tracks": total_tracks,
        "health_score": health_score,
        "total_duplicate_groups": len(duplicate_groups),
        "total_duplicate_files": total_duplicate_files,
        "duplicate_groups": duplicate_groups,
        "missing_lyrics_count": missing_lyrics,
        "missing_tags_count": missing_tags,
    }


def delete_audio_file(file_path: str) -> Dict[str, Any]:
    """Safely removes duplicate audio file and any matching .lrc file."""
    if not os.path.exists(file_path):
        return {"success": False, "error": "File not found"}

    try:
        os.remove(file_path)
        lrc_path = os.path.splitext(file_path)[0] + ".lrc"
        if os.path.exists(lrc_path):
            try:
                os.remove(lrc_path)
            except Exception:
                pass
        return {"success": True, "deleted": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
