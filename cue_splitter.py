#!/usr/bin/env python3
"""
cue_splitter.py - CUE Sheet Lossless Album Splitter & Virtual Track Engine
Author: Sandeep Khadka (Sandeep2062 <sandeepkhadka9090@gmail.com>)
License: GNU GPLv3 with Commons Clause

Parses Red Book CD .cue index sheets associated with single-file FLAC/WAV/APE album images,
provides instant virtual track seeking without duplicating files, and delivers
high-performance sample-accurate physical audio splitting with metadata preservation.
"""

import os
import re
import sys
import subprocess
from typing import Dict, Any, List, Optional

# Ensure standard UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def parse_cue_time(time_str: str) -> float:
    """
    Parses Red Book CD CUE timestamp (mm:ss:ff) where ff represents frames (75 frames/second).
    Example: '04:15:32' -> 4*60 + 15 + 32/75 = 255.426 seconds.
    """
    parts = time_str.strip().split(":")
    if len(parts) == 3:
        mins = int(parts[0])
        secs = int(parts[1])
        frames = int(parts[2])
        return mins * 60.0 + secs + (frames / 75.0)
    elif len(parts) == 2:
        mins = int(parts[0])
        secs = float(parts[1])
        return mins * 60.0 + secs
    return 0.0


def format_duration_str(seconds: float) -> str:
    """Formats float seconds to 'm:ss'."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


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


def parse_cue_file(cue_path: str) -> Dict[str, Any]:
    """
    Parses a .cue sheet text file, extracting album metadata, audio source file,
    and individual track indexes.
    """
    if not os.path.exists(cue_path):
        return {"success": False, "error": f"CUE file not found: {cue_path}"}

    # Attempt decoding with multiple common encodings
    content = ""
    for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
        try:
            with open(cue_path, "r", encoding=enc) as f:
                content = f.read()
                break
        except Exception:
            continue

    if not content:
        return {"success": False, "error": "Unable to read or decode CUE file."}

    cue_dir = os.path.dirname(os.path.abspath(cue_path))

    album_title = "Unknown Album"
    album_artist = "Unknown Artist"
    audio_file_rel = ""
    genre = ""
    year = ""

    tracks_data: List[Dict[str, Any]] = []
    current_track: Optional[Dict[str, Any]] = None

    lines = content.splitlines()
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        # Top-level tags
        if not current_track:
            perf_m = re.match(r'^PERFORMER\s+"?([^"]+)"?', line_clean, re.IGNORECASE)
            if perf_m:
                album_artist = perf_m.group(1).strip()
                continue

            tit_m = re.match(r'^TITLE\s+"?([^"]+)"?', line_clean, re.IGNORECASE)
            if tit_m:
                album_title = tit_m.group(1).strip()
                continue

            genre_m = re.match(r'^REM\s+GENRE\s+"?([^"]+)"?', line_clean, re.IGNORECASE)
            if genre_m:
                genre = genre_m.group(1).strip()
                continue

            date_m = re.match(r'^REM\s+DATE\s+"?(\d{4})"?', line_clean, re.IGNORECASE)
            if date_m:
                year = date_m.group(1).strip()
                continue

        # Master audio file declaration
        file_m = re.match(r'^FILE\s+"?([^"]+)"?\s+.*', line_clean, re.IGNORECASE)
        if file_m:
            audio_file_rel = file_m.group(1).strip()
            continue

        # Track declaration: TRACK 01 AUDIO
        track_m = re.match(r'^TRACK\s+(\d+)\s+AUDIO', line_clean, re.IGNORECASE)
        if track_m:
            if current_track:
                tracks_data.append(current_track)
            track_num = int(track_m.group(1))
            current_track = {
                "track_number": track_num,
                "title": f"Track {track_num:02d}",
                "artist": album_artist,
                "start_sec": 0.0,
                "end_sec": 0.0,
                "duration_sec": 0.0,
                "duration_str": "0:00"
            }
            continue

        # Track sub-properties
        if current_track:
            t_tit_m = re.match(r'^TITLE\s+"?([^"]+)"?', line_clean, re.IGNORECASE)
            if t_tit_m:
                current_track["title"] = t_tit_m.group(1).strip()
                continue

            t_perf_m = re.match(r'^PERFORMER\s+"?([^"]+)"?', line_clean, re.IGNORECASE)
            if t_perf_m:
                current_track["artist"] = t_perf_m.group(1).strip()
                continue

            idx_m = re.match(r'^INDEX\s+01\s+(\d{1,3}:\d{2}:\d{2})', line_clean, re.IGNORECASE)
            if idx_m:
                current_track["start_sec"] = parse_cue_time(idx_m.group(1))
                continue

    if current_track:
        tracks_data.append(current_track)

    # Resolve master audio file path
    resolved_audio = ""
    if audio_file_rel:
        test_path = os.path.join(cue_dir, audio_file_rel)
        if os.path.exists(test_path):
            resolved_audio = test_path

    # If not found directly, check for audio files with the same basename in directory
    if not resolved_audio:
        cue_base, _ = os.path.splitext(cue_path)
        for ext in [".flac", ".wav", ".ape", ".m4a", ".mp3"]:
            cand = cue_base + ext
            if os.path.exists(cand):
                resolved_audio = cand
                break

    # Get total file duration if audio file exists
    total_audio_sec = 0.0
    if resolved_audio and os.path.exists(resolved_audio):
        try:
            from tinytag import TinyTag
            tag = TinyTag.get(resolved_audio)
            if tag and tag.duration:
                total_audio_sec = float(tag.duration)
        except Exception:
            pass

    # Compute duration and end_sec for each track
    for i in range(len(tracks_data)):
        cur = tracks_data[i]
        if i + 1 < len(tracks_data):
            nxt = tracks_data[i + 1]
            cur["end_sec"] = nxt["start_sec"]
            cur["duration_sec"] = max(0.0, cur["end_sec"] - cur["start_sec"])
        else:
            if total_audio_sec > cur["start_sec"]:
                cur["end_sec"] = total_audio_sec
                cur["duration_sec"] = total_audio_sec - cur["start_sec"]
            else:
                cur["end_sec"] = cur["start_sec"] + 180.0  # fallback 3 mins
                cur["duration_sec"] = 180.0
        cur["duration_str"] = format_duration_str(cur["duration_sec"])

    return {
        "success": True,
        "album_title": album_title,
        "album_artist": album_artist,
        "genre": genre,
        "year": year,
        "audio_file": resolved_audio,
        "audio_exists": bool(resolved_audio and os.path.exists(resolved_audio)),
        "total_tracks": len(tracks_data),
        "tracks": tracks_data
    }


def split_cue_sheet(
    cue_path: str,
    output_dir: Optional[str] = None,
    output_format: str = "flac",
    bitrate: str = "320k"
) -> Dict[str, Any]:
    """
    Physically splits the album audio file defined in the CUE sheet into individual
    tagged audio track files using ffmpeg.
    """
    cue_info = parse_cue_file(cue_path)
    if not cue_info.get("success"):
        return cue_info

    master_audio = cue_info.get("audio_file")
    if not master_audio or not os.path.exists(master_audio):
        return {"success": False, "error": "Associated master audio file not found on disk."}

    ffmpeg_bin = find_ffmpeg_executable()
    if not ffmpeg_bin:
        return {"success": False, "error": "FFmpeg is required for physical CUE splitting but was not found on PATH."}

    if not output_dir:
        output_dir = os.path.join(os.path.dirname(cue_path), f"{cue_info['album_artist']} - {cue_info['album_title']}")

    os.makedirs(output_dir, exist_ok=True)

    tracks = cue_info.get("tracks", [])
    split_results = []

    for t in tracks:
        tr_num = t["track_number"]
        tr_title = t["title"]
        tr_artist = t["artist"]
        start = t["start_sec"]
        duration = t["duration_sec"]

        safe_title = re.sub(r'[\\/*?:"<>|]', "", tr_title).strip()
        out_filename = f"{tr_num:02d} - {safe_title}.{output_format}"
        out_path = os.path.join(output_dir, out_filename)

        cmd = [
            ffmpeg_bin, "-y",
            "-ss", f"{start:.3f}",
            "-t", f"{duration:.3f}",
            "-i", master_audio,
        ]

        if output_format == "mp3":
            cmd += ["-c:a", "libmp3lame", "-b:a", bitrate]
        elif output_format == "flac":
            cmd += ["-c:a", "flac"]
        elif output_format == "wav":
            cmd += ["-c:a", "pcm_s16le"]
        elif output_format == "m4a":
            cmd += ["-c:a", "aac", "-b:a", bitrate]

        # Metadata tags
        cmd += [
            "-metadata", f"title={tr_title}",
            "-metadata", f"artist={tr_artist}",
            "-metadata", f"album={cue_info['album_title']}",
            "-metadata", f"track={tr_num}/{len(tracks)}",
            out_path
        ]

        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if r.returncode == 0 and os.path.exists(out_path):
                split_results.append({
                    "track_number": tr_num,
                    "title": tr_title,
                    "file": out_path,
                    "success": True
                })
            else:
                split_results.append({
                    "track_number": tr_num,
                    "title": tr_title,
                    "success": False,
                    "error": r.stderr.decode("utf-8", errors="ignore")[:200]
                })
        except Exception as e:
            split_results.append({
                "track_number": tr_num,
                "title": tr_title,
                "success": False,
                "error": str(e)
            })

    succeeded = sum(1 for r in split_results if r["success"])
    return {
        "success": succeeded > 0,
        "output_dir": output_dir,
        "total_tracks": len(tracks),
        "split_count": succeeded,
        "results": split_results
    }


if __name__ == "__main__":
    print("Testing cue_splitter module...")

    sample_cue = """
    REM GENRE "Progressive Rock"
    REM DATE 1973
    PERFORMER "Pink Floyd"
    TITLE "The Dark Side of the Moon"
    FILE "Pink Floyd - The Dark Side of the Moon.flac" WAVE
      TRACK 01 AUDIO
        TITLE "Speak to Me"
        INDEX 01 00:00:00
      TRACK 02 AUDIO
        TITLE "Breathe"
        INDEX 01 01:07:30
      TRACK 03 AUDIO
        TITLE "On the Run"
        INDEX 01 03:51:15
      TRACK 04 AUDIO
        TITLE "Time"
        INDEX 01 07:23:45
    """
    tmp_cue_path = os.path.join(os.path.dirname(__file__), "test_sample.cue")
    with open(tmp_cue_path, "w", encoding="utf-8") as f:
        f.write(sample_cue)

    parsed = parse_cue_file(tmp_cue_path)
    if os.path.exists(tmp_cue_path):
        os.remove(tmp_cue_path)

    assert parsed["success"] is True
    assert parsed["album_title"] == "The Dark Side of the Moon"
    assert parsed["album_artist"] == "Pink Floyd"
    assert parsed["total_tracks"] == 4
    assert parsed["tracks"][0]["title"] == "Speak to Me"
    assert parsed["tracks"][1]["title"] == "Breathe"
    assert round(parsed["tracks"][1]["start_sec"], 2) == 67.40  # 1*60 + 7 + 30/75 = 67.40

    print(f"✓ Parsed Album: {parsed['album_title']} by {parsed['album_artist']}")
    print(f"✓ Track 2 ({parsed['tracks'][1]['title']}) start: {parsed['tracks'][1]['start_sec']}s")
    print("✓ All cue_splitter unit tests passed successfully!")
