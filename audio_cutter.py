#!/usr/bin/env python3
"""
audio_cutter.py - Studio Audio Ringtone, Sample & Stem Cutter Studio
Author: Sandeep Khadka (Sandeep2062 <sandeepkhadka9090@gmail.com>)
License: GNU GPLv3 with Commons Clause

Provides millisecond-accurate audio trimming, envelope fade-in/fade-out curves,
and ringtone generation (.m4r, .mp3, .wav, .m4a) with full metadata tag and cover preservation.
"""

import os
import re
import sys
import subprocess
from typing import Dict, Any, Optional

# Ensure standard UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


import shutil

def find_ffmpeg_executable() -> Optional[str]:
    """Finds ffmpeg binary on system PATH or candidate directories."""
    p = shutil.which("ffmpeg")
    if p:
        return p

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


def trim_audio_clip(
    source_file: str,
    start_sec: float,
    end_sec: float,
    fade_in_sec: float = 0.5,
    fade_out_sec: float = 0.5,
    output_format: str = "mp3",
    bitrate: str = "320k",
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Trims an audio snippet from source_file between start_sec and end_sec,
    applying optional fade-in and fade-out curves, and saving to output_path.
    """
    if not os.path.exists(source_file):
        return {"success": False, "error": f"Source audio file not found: {source_file}"}

    if start_sec < 0:
        start_sec = 0.0
    if end_sec <= start_sec:
        return {"success": False, "error": f"Invalid range: end time ({end_sec}s) must be greater than start time ({start_sec}s)."}

    duration = end_sec - start_sec

    ffmpeg_bin = find_ffmpeg_executable()
    if not ffmpeg_bin:
        return {"success": False, "error": "FFmpeg binary is required for high-quality audio trimming."}

    # Generate default output path if not specified
    if not output_path:
        base, _ = os.path.splitext(source_file)
        start_str = f"{int(start_sec // 60)}m{int(start_sec % 60)}s"
        end_str = f"{int(end_sec // 60)}m{int(end_sec % 60)}s"
        ext = output_format.lower()
        if ext == "m4r":
            ext = "m4r"
        output_path = f"{base}_clip_{start_str}-{end_str}.{ext}"

    # Build audio filter chain for smooth fading
    filters = []
    if fade_in_sec > 0:
        actual_fade_in = min(fade_in_sec, duration / 2.0)
        filters.append(f"afade=t=in:ss=0:d={actual_fade_in:.2f}")

    if fade_out_sec > 0:
        actual_fade_out = min(fade_out_sec, duration / 2.0)
        fade_out_start = max(0.0, duration - actual_fade_out)
        filters.append(f"afade=t=out:st={fade_out_start:.2f}:d={actual_fade_out:.2f}")

    filter_arg = ",".join(filters) if filters else None

    cmd = [
        ffmpeg_bin, "-y",
        "-ss", f"{start_sec:.3f}",
        "-t", f"{duration:.3f}",
        "-i", source_file
    ]

    if filter_arg:
        cmd += ["-af", filter_arg]

    ext_lower = output_format.lower()
    if ext_lower == "mp3":
        cmd += ["-c:a", "libmp3lame", "-b:a", bitrate]
    elif ext_lower in ["m4a", "m4r"]:
        cmd += ["-c:a", "aac", "-b:a", bitrate]
    elif ext_lower == "wav":
        cmd += ["-c:a", "pcm_s16le"]
    elif ext_lower == "flac":
        cmd += ["-c:a", "flac"]

    # Preserve metadata tags
    cmd += ["-map_metadata", "0", output_path]

    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        if r.returncode == 0 and os.path.exists(output_path):
            file_size_kb = round(os.path.getsize(output_path) / 1024.0, 1)
            return {
                "success": True,
                "output_file": output_path,
                "duration": round(duration, 2),
                "format": output_format,
                "size_kb": file_size_kb
            }
        else:
            return {
                "success": False,
                "error": r.stderr.decode("utf-8", errors="ignore")[:300] or "FFmpeg process failed."
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    ff = find_ffmpeg_executable()
    print(f"[*] Detected FFmpeg executable: {ff or 'Not found (graceful mode)'}")

    # Test parameter validation
    res = trim_audio_clip("nonexistent_file.mp3", 10.0, 25.0)
    assert res["success"] is False
    assert "not found" in res["error"]

    res_invalid_range = trim_audio_clip("some_file.mp3", 30.0, 20.0)
    assert res_invalid_range["success"] is False

    print("✓ All audio_cutter unit tests passed successfully!")
