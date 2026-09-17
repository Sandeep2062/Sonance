"""
playlist_doctor.py - M3U / M3U8 Playlist Doctor, Dead Link Healer & Lossless Upgrader
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Parses and validates M3U, M3U8, and PLS playlists, detects broken links, missing files,
and duplicates, recursively heals paths across library reorganizations, and automatically
upgrades lossy entries to lossless FLAC/WAV files.
"""

import os
import sys
import re
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any

LOSSLESS_EXTS = {".flac", ".wav", ".alac", ".aif", ".aiff"}
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".alac", ".aiff"}


def parse_playlist_file(playlist_path: str) -> List[Dict[str, Any]]:
    """
    Parses an M3U, M3U8, or PLS playlist into structured track entries.
    """
    if not os.path.exists(playlist_path):
        raise FileNotFoundError(f"Playlist file not found: {playlist_path}")

    base_dir = os.path.dirname(os.path.abspath(playlist_path))
    ext = os.path.splitext(playlist_path)[1].lower()
    entries = []

    try:
        with open(playlist_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        return []

    if ext == ".pls":
        # PLS parsing
        current_entry = {}
        for line in lines:
            if line.lower().startswith("file"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    current_entry["path"] = parts[1].strip()
            elif line.lower().startswith("title"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    current_entry["title"] = parts[1].strip()
            elif line.lower().startswith("length"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    try:
                        current_entry["duration"] = float(parts[1].strip())
                    except ValueError:
                        current_entry["duration"] = 0.0

            if "path" in current_entry:
                path = current_entry["path"]
                if not os.path.isabs(path) and not path.startswith("http"):
                    path = os.path.normpath(os.path.join(base_dir, path))
                entries.append({
                    "path": path,
                    "title": current_entry.get("title", os.path.basename(path)),
                    "duration": current_entry.get("duration", 0.0),
                })
                current_entry = {}
        return entries

    # Standard M3U / M3U8 parsing
    current_meta = {"duration": 0.0, "title": ""}
    for line in lines:
        if line.startswith("#EXTINF:"):
            # Format: #EXTINF:180,Artist - Title
            content = line[8:]
            parts = content.split(",", 1)
            try:
                current_meta["duration"] = float(parts[0].strip())
            except ValueError:
                current_meta["duration"] = 0.0
            if len(parts) > 1:
                current_meta["title"] = parts[1].strip()
        elif not line.startswith("#"):
            # Audio path
            path = line.strip()
            if path.startswith("file://"):
                path = urllib.parse.unquote(urllib.parse.urlparse(path).path)
                if sys.platform == "win32" and path.startswith("/"):
                    path = path[1:]

            if not os.path.isabs(path) and not path.startswith("http"):
                path = os.path.normpath(os.path.join(base_dir, path))

            entries.append({
                "path": path,
                "title": current_meta.get("title") or os.path.basename(path),
                "duration": current_meta.get("duration", 0.0),
            })
            current_meta = {"duration": 0.0, "title": ""}

    return entries


def diagnose_playlist(playlist_path: str) -> Dict[str, Any]:
    """
    Performs full health diagnostics on a playlist:
    - Dead link detection
    - Duplicate detection
    - Lossless ratio calculation
    - Health score (0-100%)
    """
    if not os.path.exists(playlist_path):
        return {"error": f"Playlist not found: {playlist_path}", "success": False}

    entries = parse_playlist_file(playlist_path)
    total_tracks = len(entries)
    if total_tracks == 0:
        return {
            "success": True,
            "playlist": os.path.basename(playlist_path),
            "total_tracks": 0,
            "valid_tracks": 0,
            "broken_tracks": 0,
            "duplicates": 0,
            "lossless_tracks": 0,
            "lossless_percent": 0.0,
            "total_duration_sec": 0.0,
            "health_score": 100.0,
            "items": [],
        }

    valid_count = 0
    broken_count = 0
    lossless_count = 0
    total_duration = 0.0
    seen_paths = set()
    duplicate_count = 0
    diagnosed_items = []

    for idx, e in enumerate(entries, start=1):
        path = e["path"]
        exists = os.path.exists(path)
        ext = os.path.splitext(path)[1].lower()
        is_lossless = ext in LOSSLESS_EXTS

        is_dup = path.lower() in seen_paths
        seen_paths.add(path.lower())
        if is_dup:
            duplicate_count += 1

        if exists:
            valid_count += 1
            if is_lossless:
                lossless_count += 1
        else:
            broken_count += 1

        total_duration += e.get("duration", 0.0)

        diagnosed_items.append({
            "index": idx,
            "title": e["title"],
            "path": path,
            "exists": exists,
            "is_lossless": is_lossless,
            "is_duplicate": is_dup,
            "duration": e.get("duration", 0.0),
        })

    health_score = round((valid_count / total_tracks) * 100.0, 1) if total_tracks > 0 else 100.0
    lossless_pct = round((lossless_count / valid_count) * 100.0, 1) if valid_count > 0 else 0.0

    return {
        "success": True,
        "playlist": os.path.basename(playlist_path),
        "path": playlist_path,
        "total_tracks": total_tracks,
        "valid_tracks": valid_count,
        "broken_tracks": broken_count,
        "duplicates": duplicate_count,
        "lossless_tracks": lossless_count,
        "lossless_percent": lossless_pct,
        "total_duration_sec": round(total_duration, 1),
        "health_score": health_score,
        "items": diagnosed_items,
    }


def build_library_index(library_dir: str) -> Dict[str, List[str]]:
    """
    Recursively indexes all audio files in a music directory.
    Maps normalized base filename variations -> list of full paths.
    """
    index: Dict[str, List[str]] = {}
    if not os.path.exists(library_dir):
        return index

    for root, _, files in os.walk(library_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTS:
                full_path = os.path.join(root, f)
                base = os.path.splitext(f)[0].lower().strip()
                # Clean track numbers like "01 - " or "01. "
                clean_base = re.sub(r"^\d+[\s\.\-_]+", "", base).strip()
                keys = {base, clean_base}

                # If "Artist - Title", extract title part
                if " - " in clean_base:
                    parts = clean_base.split(" - ")
                    keys.add(parts[-1].strip())
                elif "-" in clean_base:
                    parts = clean_base.split("-")
                    keys.add(parts[-1].strip())

                for k in keys:
                    if k:
                        if k not in index:
                            index[k] = []
                        if full_path not in index[k]:
                            index[k].append(full_path)
    return index


def heal_playlist(
    playlist_path: str,
    library_dir: Optional[str] = None,
    output_path: Optional[str] = None,
    upgrade_lossless: bool = False,
    relative_paths: bool = False,
    remove_duplicates: bool = False,
) -> Dict[str, Any]:
    """
    Heals broken playlist paths by searching library_dir, upgrades lossy to lossless,
    and writes a sanitized UTF-8 #EXTM3U file.
    """
    if not os.path.exists(playlist_path):
        return {"error": f"Playlist not found: {playlist_path}", "success": False}

    diag = diagnose_playlist(playlist_path)
    if not diag.get("success"):
        return diag

    if library_dir is None:
        library_dir = os.path.dirname(os.path.abspath(playlist_path))

    lib_index = build_library_index(library_dir)

    healed_entries = []
    healed_count = 0
    upgraded_count = 0
    seen = set()

    for item in diag["items"]:
        path = item["path"]
        orig_ext = os.path.splitext(path)[1].lower()
        title = item["title"]
        dur = item["duration"]
        base_name = os.path.splitext(os.path.basename(path))[0].lower().strip()
        clean_name = re.sub(r"^\d+[\s\.\-_]+", "", base_name).strip()

        target_path = path

        # Step 1: Check Lossless Upgrade if requested and available
        upgraded = False
        if upgrade_lossless and orig_ext not in LOSSLESS_EXTS:
            for k in (base_name, clean_name):
                if k in lib_index:
                    for candidate in lib_index[k]:
                        cand_ext = os.path.splitext(candidate)[1].lower()
                        if cand_ext in LOSSLESS_EXTS and os.path.exists(candidate):
                            target_path = candidate
                            upgraded = True
                            upgraded_count += 1
                            break
                if upgraded:
                    break

        # Step 2: Heal Broken Path if file does not exist
        if not os.path.exists(target_path):
            found_path = None
            for k in (base_name, clean_name):
                if k in lib_index:
                    for candidate in lib_index[k]:
                        if os.path.exists(candidate):
                            found_path = candidate
                            break
                if found_path:
                    break

            if found_path:
                target_path = found_path
                healed_count += 1

        # Step 3: Handle Duplicates
        if remove_duplicates and target_path.lower() in seen:
            continue
        seen.add(target_path.lower())

        # Step 4: Handle Relative vs Absolute
        out_entry_path = target_path
        if relative_paths and output_path:
            out_base = os.path.dirname(os.path.abspath(output_path))
            try:
                out_entry_path = os.path.relpath(target_path, out_base)
            except ValueError:
                out_entry_path = target_path

        healed_entries.append({
            "path": out_entry_path,
            "title": title,
            "duration": dur,
            "exists": os.path.exists(target_path),
            "upgraded": upgraded,
        })

    # Determine output file path
    if not output_path:
        base, ext = os.path.splitext(playlist_path)
        output_path = f"{base}_healed.m3u8"

    # Write sanitized #EXTM3U8 file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for e in healed_entries:
                dur_int = int(e.get("duration", 0))
                f.write(f"#EXTINF:{dur_int},{e['title']}\n")
                f.write(f"{e['path']}\n")
    except Exception as e:
        return {"error": f"Failed to write healed playlist: {str(e)}", "success": False}

    post_diag = diagnose_playlist(output_path)

    return {
        "success": True,
        "original_playlist": playlist_path,
        "output_playlist": output_path,
        "total_tracks": len(healed_entries),
        "healed_tracks": healed_count,
        "upgraded_to_lossless": upgraded_count,
        "pre_health_score": diag["health_score"],
        "post_health_score": post_diag["health_score"],
        "pre_broken": diag["broken_tracks"],
        "post_broken": post_diag["broken_tracks"],
    }


def format_doctor_card(diag: Dict[str, Any]) -> str:
    """
    Renders an ASCII diagnostic card safe for Windows console codepages.
    """
    if not diag.get("success"):
        return f"[!] Error: {diag.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append(f"| M3U / M3U8 PLAYLIST DOCTOR & HEALTH DIAGNOSTIC REPORT            |")
    lines.append(sep)
    lines.append(f"| Playlist: {diag['playlist'][:54]:<54} |")
    dur_m = int(diag['total_duration_sec'] // 60)
    dur_s = int(diag['total_duration_sec'] % 60)
    lines.append(f"| Total Duration : {dur_m}m {dur_s}s  |  Total Tracks: {diag['total_tracks']:<18} |")
    lines.append(f"| Health Score   : {diag['health_score']}% {'(PERFECT)' if diag['health_score']==100 else '(NEEDS HEALING)'} |")
    lines.append(sep)
    lines.append(f"| Metric                           | Count       | Percentage       |")
    lines.append(f"|----------------------------------+-------------+------------------|")
    lines.append(f"| Playable / Verified Tracks       | {diag['valid_tracks']:<11} | {diag['health_score']:>6.1f}%          |")
    broken_pct = 100.0 - diag['health_score'] if diag['total_tracks'] > 0 else 0.0
    lines.append(f"| Dead / Broken File Links         | {diag['broken_tracks']:<11} | {broken_pct:>6.1f}%          |")
    lines.append(f"| Lossless Tracks (FLAC/WAV)       | {diag['lossless_tracks']:<11} | {diag['lossless_percent']:>6.1f}%          |")
    lines.append(f"| Duplicate Entries                | {diag['duplicates']:<11} | {'--':>6}           |")
    lines.append(sep)

    if diag.get("broken_tracks", 0) > 0:
        lines.append(f"| TOP BROKEN LINKS DETECTED                                        |")
        lines.append(f"| Index | Track / Missing Path                                     |")
        lines.append(f"|-------+----------------------------------------------------------|")
        count = 0
        for item in diag["items"]:
            if not item["exists"]:
                count += 1
                p_display = item['path'] if len(item['path']) <= 54 else "..." + item['path'][-51:]
                lines.append(f"| #{item['index']:3d}  | {p_display:<56} |")
                if count >= 8:
                    rem = diag['broken_tracks'] - count
                    if rem > 0:
                        lines.append(f"|       | ... and {rem} more broken links                            |")
                    break
        lines.append(sep)

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playlist_doctor.py <playlist.m3u|m3u8|pls> [--heal] [--library-dir <dir>] [--lossless]")
        sys.exit(1)

    target_pl = sys.argv[1]
    if "--heal" in sys.argv:
        lib_dir = None
        if "--library-dir" in sys.argv:
            idx = sys.argv.index("--library-dir")
            if idx + 1 < len(sys.argv):
                lib_dir = sys.argv[idx + 1]
        up_lossless = "--lossless" in sys.argv
        res = heal_playlist(target_pl, library_dir=lib_dir, upgrade_lossless=up_lossless)
        print(f"[+] Healed playlist written to: {res.get('output_playlist')}")
        print(f"[+] Restored: {res.get('healed_tracks')} broken tracks, Upgraded: {res.get('upgraded_to_lossless')} to Lossless.")
        print(f"[+] Health: {res.get('pre_health_score')}% -> {res.get('post_health_score')}%")
    else:
        diag = diagnose_playlist(target_pl)
        print(format_doctor_card(diag))
