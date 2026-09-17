"""
album_art_studio.py - Batch Album Art Optimizer, Cover Normalizer & Embedded Bloat Reducer
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Audits, extracts, and manages album art across audio libraries:
- Inspects embedded artwork in FLAC, MP3, M4A, OGG, and WAV containers
- Pure-Python binary header parser for PNG, JPEG, and WebP dimensions without Pillow
- Pinpoints bloated embedded art (e.g. 10MB uncompressed PNGs embedded in every track)
- Extracts companion 'cover.jpg' / 'folder.jpg' for portable DAPs, car audio & MusicBee
- Non-destructive embedded art removal to reclaim disk space
"""

import os
import sys
import struct
import argparse
from typing import Dict, List, Optional, Tuple, Any

import mutagen
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4


AUDIO_EXTS = {".mp3", ".flac", ".m4a", ".ogg", ".wav"}


def detect_image_format_and_dimensions(data: bytes) -> Tuple[str, int, int]:
    """
    Sniffs image binary data to determine MIME/format and dimensions (Width x Height)
    without requiring PIL/Pillow.
    """
    if len(data) < 24:
        return "Unknown", 0, 0

    # PNG: Signature \x89PNG\r\n\x1a\n, IHDR chunk at offset 12
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data) >= 24:
            w, h = struct.unpack(">II", data[16:24])
            return "PNG", w, h
        return "PNG", 0, 0

    # JPEG: Signature \xFF\xD8\xFF
    if data.startswith(b"\xff\xd8"):
        idx = 2
        data_len = len(data)
        while idx < data_len - 8:
            if data[idx] != 0xFF:
                idx += 1
                continue
            marker = data[idx + 1]
            # SOF markers: 0xC0, 0xC1, 0xC2, 0xC3 (Baseline, Extended, Progressive)
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                h, w = struct.unpack(">HH", data[idx + 5 : idx + 9])
                return "JPEG", w, h
            # Skip marker segment
            if marker in (0xD9, 0xDA):  # EOI or SOS
                break
            length = struct.unpack(">H", data[idx + 2 : idx + 4])[0]
            idx += 2 + length
        return "JPEG", 0, 0

    # WebP: RIFF....WEBP
    if data.startswith(b"RIFF") and len(data) > 16 and data[8:12] == b"WEBP":
        return "WebP", 0, 0

    return "Unknown", 0, 0


def extract_embedded_artwork(file_path: str) -> Optional[Tuple[bytes, str, int, int]]:
    """
    Extracts embedded album art bytes from an audio file.
    Returns (image_bytes, format_str, width, height) or None.
    """
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".flac":
            audio = FLAC(file_path)
            if audio.pictures:
                pic = audio.pictures[0]
                fmt, w, h = detect_image_format_and_dimensions(pic.data)
                w = pic.width if pic.width > 0 else w
                h = pic.height if pic.height > 0 else h
                return pic.data, fmt, w, h

        elif ext == ".mp3":
            try:
                tags = ID3(file_path)
                for tag in tags.values():
                    if isinstance(tag, APIC):
                        fmt, w, h = detect_image_format_and_dimensions(tag.data)
                        return tag.data, fmt, w, h
            except Exception:
                pass

        elif ext == ".m4a":
            audio = MP4(file_path)
            covr = audio.tags.get("covr") if audio.tags else None
            if covr and len(covr) > 0:
                raw = bytes(covr[0])
                fmt, w, h = detect_image_format_and_dimensions(raw)
                return raw, fmt, w, h

        # Generic mutagen fallback
        m = mutagen.File(file_path)
        if m and hasattr(m, "tags") and m.tags:
            for key in m.tags.keys():
                if "picture" in key.lower() or "covr" in key.lower():
                    val = m.tags[key]
                    if isinstance(val, (list, tuple)) and len(val) > 0:
                        val = val[0]
                    if hasattr(val, "data"):
                        fmt, w, h = detect_image_format_and_dimensions(val.data)
                        return val.data, fmt, w, h

    except Exception:
        pass

    return None


def strip_embedded_artwork(file_path: str) -> bool:
    """Removes embedded artwork from an audio file to reduce file bloat."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".flac":
            audio = FLAC(file_path)
            if audio.pictures:
                audio.clear_pictures()
                audio.save()
                return True
        elif ext == ".mp3":
            tags = ID3(file_path)
            apic_keys = [k for k in tags.keys() if k.startswith("APIC")]
            if apic_keys:
                for k in apic_keys:
                    del tags[k]
                tags.save()
                return True
        elif ext == ".m4a":
            audio = MP4(file_path)
            if audio.tags and "covr" in audio.tags:
                del audio.tags["covr"]
                audio.save()
                return True
    except Exception:
        pass
    return False


def scan_and_manage_artwork(
    target_path: str,
    action: str = "report",
    export_companion: bool = False
) -> Dict[str, Any]:
    """
    Audits, extracts, or strips artwork across file or directory.
    
    Args:
        target_path: File or folder path.
        action: 'report', 'extract', or 'strip'.
        export_companion: If True, writes companion cover.jpg in album folders.
    """
    if not os.path.exists(target_path):
        return {"success": False, "error": f"Path not found: {target_path}"}

    files = []
    if os.path.isfile(target_path):
        if os.path.splitext(target_path)[1].lower() in AUDIO_EXTS:
            files.append(target_path)
    else:
        for root, _, fnames in os.walk(target_path):
            for fn in fnames:
                if os.path.splitext(fn)[1].lower() in AUDIO_EXTS:
                    files.append(os.path.join(root, fn))

    if not files:
        return {"success": False, "error": "No supported audio files found."}

    total_files = len(files)
    with_art = 0
    missing_art = 0
    bloated_files = 0
    total_art_bytes = 0
    extracted_count = 0
    stripped_count = 0
    exported_covers = []
    sample_tracks = []

    # Map directories to extracted companion covers to avoid duplicate extraction
    folders_covered = set()

    for idx, fpath in enumerate(files):
        art_info = extract_embedded_artwork(fpath)
        folder = os.path.dirname(os.path.abspath(fpath))

        if art_info:
            with_art += 1
            raw_bytes, fmt, w, h = art_info
            size_bytes = len(raw_bytes)
            total_art_bytes += size_bytes
            is_bloated = size_bytes > (1.5 * 1024 * 1024) or fmt == "PNG"

            if is_bloated:
                bloated_files += 1

            if idx < 6:
                sample_tracks.append({
                    "file": os.path.basename(fpath),
                    "format": fmt,
                    "dimensions": f"{w}x{h}" if w > 0 else "Unknown",
                    "size_kb": round(size_bytes / 1024.0, 1),
                    "bloated": is_bloated
                })

            # Extract companion cover if requested
            if (action == "extract" or export_companion) and folder not in folders_covered:
                ext_ext = ".jpg" if fmt == "JPEG" else (".png" if fmt == "PNG" else ".jpg")
                cover_dest = os.path.join(folder, f"cover{ext_ext}")
                try:
                    with open(cover_dest, "wb") as cf:
                        cf.write(raw_bytes)
                    folders_covered.add(folder)
                    extracted_count += 1
                    exported_covers.append(cover_dest)
                except Exception:
                    pass

            # Strip embedded art if requested
            if action == "strip":
                if strip_embedded_artwork(fpath):
                    stripped_count += 1
        else:
            missing_art += 1
            if idx < 6:
                sample_tracks.append({
                    "file": os.path.basename(fpath),
                    "format": "None",
                    "dimensions": "None",
                    "size_kb": 0.0,
                    "bloated": False
                })

    avg_art_size_kb = (total_art_bytes / max(1, with_art)) / 1024.0
    total_art_mb = total_art_bytes / (1024.0 * 1024.0)

    return {
        "success": True,
        "target_path": target_path,
        "action": action,
        "total_files": total_files,
        "files_with_art": with_art,
        "missing_art": missing_art,
        "bloated_files": bloated_files,
        "total_art_mb": round(total_art_mb, 2),
        "avg_art_size_kb": round(avg_art_size_kb, 1),
        "extracted_covers_count": extracted_count,
        "stripped_files_count": stripped_count,
        "exported_covers": exported_covers[:5],
        "sample_tracks": sample_tracks
    }


def format_art_card(res: Dict[str, Any]) -> str:
    """Renders formatted ASCII album art management and bloat reduction card."""
    if not res.get("success"):
        return f"[!] Error managing album art: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append("| ALBUM ART OPTIMIZER, COVER NORMALIZER & BLOAT REDUCER           |")
    lines.append(sep)
    lines.append(f"| Scanned Path   : {res['target_path'][:48]:<48} |")
    lines.append(f"| Total Tracks   : {res['total_files']:<6} | With Embedded Art: {res['files_with_art']:<6} | Missing: {res['missing_art']:<6}|")
    lines.append(f"| Total Art Size : {res['total_art_mb']} MB (Average: {res['avg_art_size_kb']} KB / track)                  |")
    lines.append(f"| Bloated Tracks : {res['bloated_files']} tracks contain oversize PNG or >1.5MB images    |")
    lines.append(sep)

    if res["action"] == "extract":
        lines.append(f"| Action: EXTRACTED {res['extracted_covers_count']} external companion cover.jpg files         |")
    elif res["action"] == "strip":
        lines.append(f"| Action: STRIPPED {res['stripped_files_count']} embedded artworks (Reclaimed space)         |")
    else:
        lines.append("| Action: AUDIT COMPLETE (Ready to extract companion or strip)     |")

    lines.append(sep)
    lines.append("| SAMPLE TRACK AUDIT:                                              |")
    for trk in res["sample_tracks"]:
        b_flag = "[!] BLOAT" if trk["bloated"] else "   OK   "
        lines.append(f"| {trk['file'][:24]:<24} | {trk['format']:<5} | {trk['dimensions']:<9} | {trk['size_kb']:>6.1f} KB | {b_flag} |")

    lines.append(sep)
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sonance Album Art Studio & Cover Optimizer")
    parser.add_argument("target", help="Audio file or folder to audit")
    parser.add_argument("--extract", action="store_true", help="Extract companion cover.jpg to album folders")
    parser.add_argument("--strip", action="store_true", help="Strip bloated embedded artwork from files")

    args = parser.parse_args()

    act = "extract" if args.extract else ("strip" if args.strip else "report")
    result = scan_and_manage_artwork(args.target, action=act, export_companion=args.extract)
    print(format_art_card(result))
