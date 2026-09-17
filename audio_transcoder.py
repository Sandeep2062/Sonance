"""
audio_transcoder.py - Sonance High-Performance Lossless & Hi-Res Batch Audio Transcoder

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Converts audio files between formats (FLAC, WAV, MP3, M4A, OGG) with full
ID3v2.4/Vorbis tag preservation, embedded album art transfer, and .lrc companion sync.
"""

import os
import shutil
import subprocess
from typing import Dict, Any, List, Optional
import mutagen
import tag_editor


SUPPORTED_OUTPUT_FORMATS = ["mp3", "flac", "wav", "m4a", "ogg"]
DEFAULT_BITRATES = {
    "mp3": ["320k", "256k", "192k", "128k"],
    "m4a": ["320k", "256k", "192k", "128k"],
    "ogg": ["320k", "256k", "192k", "128k"],
    "flac": ["lossless"],
    "wav": ["lossless"],
}


def find_ffmpeg_executable() -> Optional[str]:
    """Finds system ffmpeg or local ffmpeg binaries."""
    # Check PATH
    p = shutil.which("ffmpeg")
    if p:
        return p

    # Check common installation locations on Windows
    common_paths = [
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for cp in common_paths:
        if os.path.isfile(cp):
            return cp
        if os.path.isdir(cp):
            for root, _, files in os.walk(cp):
                if "ffmpeg.exe" in files:
                    return os.path.join(root, "ffmpeg.exe")
    return None


def transcode_audio_file(
    source_path: str,
    target_format: str = "mp3",
    target_bitrate: str = "320k",
    dest_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transcodes a single audio file to target format, preserving tags,
    embedded album artwork, and accompanying .lrc lyrics.
    """
    if not os.path.exists(source_path):
        return {"success": False, "error": "Source audio file not found"}

    target_format = target_format.lower().replace(".", "")
    if target_format not in SUPPORTED_OUTPUT_FORMATS:
        return {"success": False, "error": f"Unsupported target format: {target_format}"}

    ffmpeg_bin = find_ffmpeg_executable()
    if not ffmpeg_bin:
        return {
            "success": False,
            "error": "ffmpeg executable not found on system. Please install ffmpeg or add to PATH."
        }

    # Determine destination filename and directory
    src_dir, src_filename = os.path.split(source_path)
    base_name = os.path.splitext(src_filename)[0]
    out_dir = dest_dir if dest_dir else src_dir
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"{base_name}.{target_format}")

    # Don't overwrite identical file
    if os.path.abspath(source_path).lower() == os.path.abspath(out_path).lower():
        out_path = os.path.join(out_dir, f"{base_name}_converted.{target_format}")

    # Build ffmpeg command line
    cmd = [ffmpeg_bin, "-y", "-i", source_path]

    if target_format == "mp3":
        cmd.extend(["-c:a", "libmp3lame", "-b:a", target_bitrate or "320k"])
    elif target_format == "flac":
        cmd.extend(["-c:a", "flac", "-compression_level", "8"])
    elif target_format == "wav":
        cmd.extend(["-c:a", "pcm_s16le"])
    elif target_format == "m4a":
        cmd.extend(["-c:a", "aac", "-b:a", target_bitrate or "256k"])
    elif target_format == "ogg":
        cmd.extend(["-c:a", "libvorbis", "-b:a", target_bitrate or "256k"])

    cmd.append(out_path)

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if proc.returncode != 0:
            err_msg = proc.stderr.decode("utf-8", errors="ignore")
            return {"success": False, "error": f"Transcode failed: {err_msg[:200]}"}

        # 1. Migrate metadata tags and embedded cover art
        src_tags = tag_editor.read_tags(source_path)
        if src_tags.get("success"):
            payload = {
                "title": src_tags.get("title", ""),
                "artist": src_tags.get("artist", ""),
                "album": src_tags.get("album", ""),
                "album_artist": src_tags.get("album_artist", ""),
                "year": src_tags.get("year", ""),
                "genre": src_tags.get("genre", ""),
                "track_number": src_tags.get("track_number", ""),
                "total_tracks": src_tags.get("total_tracks", ""),
                "disc_number": src_tags.get("disc_number", "1"),
                "comment": src_tags.get("comment", ""),
                "cover_data_uri": src_tags.get("cover_data_uri", ""),
                "remove_cover": False,
            }
            tag_editor.save_tags(out_path, payload)

        # 2. Migrate companion .lrc synchronized lyrics file if present
        src_lrc = os.path.splitext(source_path)[0] + ".lrc"
        out_lrc = os.path.splitext(out_path)[0] + ".lrc"
        if os.path.exists(src_lrc) and not os.path.exists(out_lrc):
            try:
                shutil.copy2(src_lrc, out_lrc)
            except Exception:
                pass

        size_mb = round(os.path.getsize(out_path) / (1024 * 1024), 2)
        return {
            "success": True,
            "source_path": source_path,
            "output_path": out_path,
            "format": target_format.upper(),
            "bitrate": target_bitrate,
            "size_mb": size_mb,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def batch_transcode(
    file_paths: List[str],
    target_format: str = "mp3",
    target_bitrate: str = "320k",
    dest_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Batch converts a list of audio files."""
    results = []
    success_count = 0
    fail_count = 0

    for path in file_paths:
        res = transcode_audio_file(path, target_format, target_bitrate, dest_dir)
        results.append(res)
        if res.get("success"):
            success_count += 1
        else:
            fail_count += 1

    return {
        "success": True,
        "total": len(file_paths),
        "success_count": success_count,
        "fail_count": fail_count,
        "results": results,
    }
