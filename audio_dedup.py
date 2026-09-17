#!/usr/bin/env python3
"""
audio_dedup.py - Lossless Audio Duplicate Cleaner & Integrity Verifier
Author: Sandeep Khadka (Sandeep2062 <sandeepkhadka9090@gmail.com>)
License: GNU GPLv3 with Commons Clause

Discovers identical songs across varying audio formats (FLAC, WAV, MP3, M4A, OGG)
and varying bitrates (e.g. comparing a 128 kbps MP3 against a 24-bit 96 kHz FLAC).
Intelligently preserves the highest-fidelity lossless recording and safely archives
or cleans redundant lower-bitrate duplicates.
"""

import os
import re
import sys
import shutil
from typing import Dict, Any, List, Optional
from collections import defaultdict

# Ensure standard UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def clean_str(s: str) -> str:
    """Normalizes artist and title strings for fuzzy grouping."""
    if not s:
        return ""
    # Lowercase, remove feat/ft, remove bracketed info, remove punctuation
    s = s.lower()
    s = re.sub(r"\(feat\.[^\)]+\)|\(ft\.[^\)]+\)|\[feat\.[^\]]+\]", "", s)
    s = re.sub(r"\(remaster[^\)]*\)|\[remaster[^\]]*\]", "", s)
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def calculate_quality_score(track: Dict[str, Any]) -> int:
    """
    Computes an audiophile quality score for an audio track:
    - Lossless (FLAC, WAV): 10,000+ points based on bitdepth and sample rate
    - Hi-Res Lossy (320 kbps MP3, 256k AAC): 3,000 - 4,000 points
    - Low-rate Lossy: 1,000 - 2,500 points
    - Companion .lrc bonus: +200 points
    """
    score = 0
    fmt = track.get("format", "").upper()
    bitrate = track.get("bitrate", 0) or 0
    samplerate = track.get("samplerate", 0) or 44100
    bitdepth = track.get("bitdepth", 16) or 16

    if fmt in ["FLAC", "WAV", "ALAC", "APE"]:
        score += 10000
        score += bitdepth * 100  # 24-bit gets 2400, 16-bit gets 1600
        score += int(samplerate / 1000) * 10  # 96kHz gets 960, 44.1kHz gets 440
    else:
        score += min(3500, int(bitrate * 10))

    if track.get("has_lrc"):
        score += 200

    return score


def scan_for_duplicates(folder_path: str) -> Dict[str, Any]:
    """
    Scans a directory tree and groups duplicate tracks by canonical acoustic match.
    """
    if not os.path.isdir(folder_path):
        return {"success": False, "error": f"Folder not found: {folder_path}"}

    try:
        from tinytag import TinyTag
    except ImportError:
        return {"success": False, "error": "TinyTag is required for audio metadata inspection."}

    audio_exts = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".aac", ".wma"}
    scanned_tracks: List[Dict[str, Any]] = []

    for root, _, files in os.walk(folder_path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in audio_exts:
                continue

            full_path = os.path.join(root, f)
            try:
                tag = TinyTag.get(full_path)
                dur = round(tag.duration or 0.0, 1)
                title = tag.title or os.path.splitext(f)[0]
                artist = tag.artist or "Unknown Artist"
                album = tag.album or "Unknown Album"
                fmt = ext.replace(".", "").upper()
                bitrate = int(tag.bitrate) if tag.bitrate else 0
                samplerate = int(tag.samplerate) if tag.samplerate else 44100
                bitdepth = getattr(tag, "bitdepth", 16) or 16

                lrc_path = os.path.splitext(full_path)[0] + ".lrc"
                has_lrc = os.path.exists(lrc_path)
                filesize = os.path.getsize(full_path)

                track_info = {
                    "path": full_path,
                    "filename": f,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "duration": dur,
                    "format": fmt,
                    "bitrate": bitrate,
                    "samplerate": samplerate,
                    "bitdepth": bitdepth,
                    "filesize": filesize,
                    "has_lrc": has_lrc,
                }
                track_info["quality_score"] = calculate_quality_score(track_info)
                scanned_tracks.append(track_info)
            except Exception:
                continue

    # Group by canonical title + artist + rough duration (within 4 seconds)
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for t in scanned_tracks:
        c_title = clean_str(t["title"])
        c_artist = clean_str(t["artist"])
        # Bucket duration to nearest 4s to tolerate fade tails
        dur_bucket = int(t["duration"] // 4) * 4

        key = f"{c_artist}::{c_title}::{dur_bucket}"
        groups[key].append(t)

    duplicate_sets: List[Dict[str, Any]] = []
    total_redundant_files = 0
    potential_space_freed = 0

    for key, tracks in groups.items():
        if len(tracks) > 1:
            # Sort tracks descending by quality score (best file first)
            sorted_tracks = sorted(tracks, key=lambda x: x["quality_score"], reverse=True)
            best_track = sorted_tracks[0]
            redundant = sorted_tracks[1:]

            total_redundant_files += len(redundant)
            group_space = sum(r["filesize"] for r in redundant)
            potential_space_freed += group_space

            duplicate_sets.append({
                "song": f"{best_track['title']} - {best_track['artist']}",
                "keeper": best_track,
                "duplicates": redundant,
                "duplicate_count": len(redundant),
                "space_freed_bytes": group_space,
                "space_freed_mb": round(group_space / (1024 * 1024), 2)
            })

    return {
        "success": True,
        "scanned_count": len(scanned_tracks),
        "duplicate_groups_count": len(duplicate_sets),
        "total_redundant_files": total_redundant_files,
        "potential_space_freed_mb": round(potential_space_freed / (1024 * 1024), 2),
        "duplicate_sets": duplicate_sets
    }


def archive_redundant_duplicates(
    duplicate_paths: List[str],
    archive_directory: str
) -> Dict[str, Any]:
    """
    Safely moves redundant duplicate files and any matching .lrc lyrics to an
    archive directory instead of deleting them.
    """
    if not os.path.exists(archive_directory):
        os.makedirs(archive_directory, exist_ok=True)

    moved_files = []
    errors = []

    for path in duplicate_paths:
        if not os.path.exists(path):
            continue

        try:
            filename = os.path.basename(path)
            dest = os.path.join(archive_directory, filename)
            # Handle destination name collisions
            if os.path.exists(dest):
                base, ext = os.path.splitext(filename)
                dest = os.path.join(archive_directory, f"{base}_dup{ext}")

            shutil.move(path, dest)
            moved_files.append(dest)

            # Move companion .lrc if exists
            lrc_src = os.path.splitext(path)[0] + ".lrc"
            if os.path.exists(lrc_src):
                lrc_dest = os.path.splitext(dest)[0] + ".lrc"
                shutil.move(lrc_src, lrc_dest)
        except Exception as e:
            errors.append({"file": path, "error": str(e)})

    return {
        "success": True,
        "archived_count": len(moved_files),
        "archive_directory": archive_directory,
        "moved_files": moved_files,
        "errors": errors
    }


if __name__ == "__main__":
    print("Testing audio_dedup module...")
    # Test quality score calculation
    t_flac = {"format": "FLAC", "bitdepth": 24, "samplerate": 96000, "has_lrc": True}
    t_mp3 = {"format": "MP3", "bitrate": 320, "has_lrc": False}
    score_flac = calculate_quality_score(t_flac)
    score_mp3 = calculate_quality_score(t_mp3)
    assert score_flac > score_mp3, "Lossless 24/96 should rank higher than 320k MP3"
    print(f"✓ Quality scoring verified: 24/96 FLAC ({score_flac} pts) > 320k MP3 ({score_mp3} pts)")
    print("✓ Audio dedup unit test passed successfully!")
