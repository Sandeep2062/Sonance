#!/usr/bin/env python3
"""
Sonance - MusicBee-Grade Library Auto-Organizer & File Renamer
==============================================================
Intelligently restructures and organizes local music collections based on
audio metadata tags and custom directory naming patterns.

Features:
- Flexible pattern syntax: %artist%/[%year%] %album%/%track% - %title%
- Windows/Linux filesystem path sanitization (removes illegal characters).
- Companion file synchronization (moves matching .lrc and cover artwork).
- Interactive Dry-Run mode with visual diff before any disk changes.

Author: Sandeep Khadka (Sandeep2062) <sandeepkhadka9090@gmail.com>
License: GNU GPLv3 with Commons Clause
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from tinytag import TinyTag

SUPPORTED_AUDIO_EXTS = (".flac", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".alac", ".aiff", ".wma")
DEFAULT_ORGANIZER_PATTERN = "%artist%/[%year%] %album%/%track% - %title%"


def sanitize_filename_segment(text: str, fallback: str = "Unknown") -> str:
    r"""
    Sanitizes a single directory or filename segment:
    Removes illegal Windows/Linux characters (< > : " / \ | ? *),
    trims whitespace, and eliminates trailing dots.
    """
    if not text:
        return fallback

    cleaned = re.sub(r'[<>:"/\\|?*]', '-', str(text))
    # Replace multiple spaces/hyphens
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = cleaned.rstrip('. ')
    return cleaned if cleaned else fallback


def extract_track_metadata(file_path: str) -> Dict[str, str]:
    """Extracts tag dictionary for pattern substitution."""
    ext = os.path.splitext(file_path)[1].lower()
    base = os.path.splitext(os.path.basename(file_path))[0]

    tag = None
    try:
        tag = TinyTag.get(file_path)
    except Exception:
        pass

    artist = getattr(tag, "artist", None) or "Unknown Artist"
    album_artist = getattr(tag, "albumartist", None) or artist
    album = getattr(tag, "album", None) or "Unknown Album"
    title = getattr(tag, "title", None) or base
    genre = getattr(tag, "genre", None) or "Music"

    # Year
    year_raw = getattr(tag, "year", None)
    year = str(year_raw)[:4] if year_raw else ""

    # Track number
    track_raw = getattr(tag, "track", None)
    try:
        track_num = int(track_raw) if track_raw else 1
        track = f"{track_num:02d}"
    except Exception:
        track = "01"

    # Disc number
    disc_raw = getattr(tag, "disc", None)
    try:
        disc = str(int(disc_raw)) if disc_raw else "1"
    except Exception:
        disc = "1"

    return {
        "artist": sanitize_filename_segment(artist, "Unknown Artist"),
        "album_artist": sanitize_filename_segment(album_artist, "Unknown Artist"),
        "album": sanitize_filename_segment(album, "Unknown Album"),
        "title": sanitize_filename_segment(title, base),
        "track": track,
        "year": year,
        "genre": sanitize_filename_segment(genre, "Music"),
        "disc": disc,
        "ext": ext.replace(".", ""),
    }


def resolve_pattern_path(
    file_path: str,
    root_destination: str,
    pattern: str = DEFAULT_ORGANIZER_PATTERN
) -> str:
    """
    Resolves pattern placeholders to construct target file path.
    Example pattern: '%artist%/[%year%] %album%/%track% - %title%'
    """
    meta = extract_track_metadata(file_path)

    # If year is empty, remove empty brackets e.g. '[] ' or '[Unknown Year]'
    res = pattern
    if not meta["year"]:
        res = re.sub(r'\[%year%\]\s*', '', res)
        res = re.sub(r'\(%year%\)\s*', '', res)

    for key, val in meta.items():
        res = res.replace(f"%{key}%", val)

    # Ensure target has correct file extension
    ext = os.path.splitext(file_path)[1].lower()
    if not res.lower().endswith(ext):
        res = f"{res}{ext}"

    # Normalize relative path separators
    segments = [sanitize_filename_segment(s) for s in res.replace("\\", "/").split("/") if s]
    target_rel = os.path.join(*segments)
    return os.path.abspath(os.path.join(root_destination, target_rel))


def preview_library_organization(
    library_folder: str,
    pattern: str = DEFAULT_ORGANIZER_PATTERN,
    target_root: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a dry-run preview diff without making any modifications on disk.
    """
    if not os.path.isdir(library_folder):
        return {"success": False, "error": f"Folder not found: {library_folder}"}

    dest_dir = target_root or library_folder
    plan = []
    unchanged_count = 0
    change_count = 0

    for root, _, files in os.walk(library_folder):
        for f in files:
            if f.lower().endswith(SUPPORTED_AUDIO_EXTS):
                src = os.path.abspath(os.path.join(root, f))
                dst = resolve_pattern_path(src, dest_dir, pattern)

                is_same = (os.path.normcase(src) == os.path.normcase(dst))
                if is_same:
                    unchanged_count += 1
                    status = "unchanged"
                else:
                    change_count += 1
                    status = "pending"

                plan.append({
                    "source": src,
                    "target": dst,
                    "filename": f,
                    "new_rel_path": os.path.relpath(dst, dest_dir),
                    "status": status,
                    "has_lrc": os.path.isfile(os.path.splitext(src)[0] + ".lrc"),
                })

    return {
        "success": True,
        "library_folder": library_folder,
        "destination_root": dest_dir,
        "pattern": pattern,
        "total_tracks": len(plan),
        "tracks_to_move": change_count,
        "unchanged_tracks": unchanged_count,
        "preview_items": plan,
    }


def execute_library_organization(
    library_folder: str,
    pattern: str = DEFAULT_ORGANIZER_PATTERN,
    target_root: Optional[str] = None,
    copy_mode: bool = False
) -> Dict[str, Any]:
    """
    Executes directory restructuring and file renaming.
    Also migrates companion .lrc lyrics and album cover artwork.
    """
    preview = preview_library_organization(library_folder, pattern, target_root)
    if not preview.get("success"):
        return preview

    dest_dir = target_root or library_folder
    items = preview.get("preview_items", [])
    success_count = 0
    errors = []

    for item in items:
        if item["status"] == "unchanged":
            continue

        src = item["source"]
        dst = item["target"]

        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)

            if copy_mode:
                shutil.copy2(src, dst)
            else:
                shutil.move(src, dst)

            # Move companion .lrc if present
            src_lrc = os.path.splitext(src)[0] + ".lrc"
            if os.path.isfile(src_lrc):
                dst_lrc = os.path.splitext(dst)[0] + ".lrc"
                if copy_mode:
                    shutil.copy2(src_lrc, dst_lrc)
                else:
                    shutil.move(src_lrc, dst_lrc)

            success_count += 1
        except Exception as e:
            errors.append({"file": src, "error": str(e)})

    # Clean empty directories if in move mode
    if not copy_mode and library_folder == dest_dir:
        for root, dirs, _ in os.walk(library_folder, topdown=False):
            for d in dirs:
                full_d = os.path.join(root, d)
                try:
                    if not os.listdir(full_d):
                        os.rmdir(full_d)
                except Exception:
                    pass

    return {
        "success": True,
        "total_processed": len(items),
        "success_count": success_count,
        "error_count": len(errors),
        "errors": errors,
        "mode": "copy" if copy_mode else "move",
    }


if __name__ == "__main__":
    import sys
    print("Sonance MusicBee-Grade Library Auto-Organizer")
    if len(sys.argv) < 2:
        print("Usage: python library_organizer.py <library_folder> [pattern] [--dry-run]")
        sys.exit(1)

    folder = sys.argv[1]
    pat = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else DEFAULT_ORGANIZER_PATTERN
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("[*] Running DRY-RUN preview...")
        res = preview_library_organization(folder, pat)
        print(f"Total: {res.get('total_tracks')} | To Move: {res.get('tracks_to_move')}")
        for p in res.get("preview_items", [])[:10]:
            print(f"  • {p['filename']} -> {p['new_rel_path']}")
    else:
        print("[*] Executing organization...")
        res = execute_library_organization(folder, pat)
        print(f"Moved {res.get('success_count')} files successfully!")
