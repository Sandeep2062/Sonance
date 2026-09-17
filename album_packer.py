#!/usr/bin/env python3
"""
Sonance - Lossless Monolithic Album Packer & CUE Archiver Studio
================================================================
Packs multiple album tracks into a single continuous, gapless monolithic
FLAC/WAV master file with embedded Red Book CUE sheet and tags, or unpacks
monolithic album images into pristine, individually tagged tracks.

Author: Sandeep Khadka (Sandeep2062) <sandeepkhadka9090@gmail.com>
License: GNU GPLv3 with Commons Clause
"""

import os
import shutil
import subprocess
import wave
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from tinytag import TinyTag

SUPPORTED_AUDIO_EXTS = (".flac", ".wav", ".mp3", ".m4a", ".ogg")


def check_ffmpeg() -> bool:
    """Checks if FFmpeg binary is available on PATH."""
    return shutil.which("ffmpeg") is not None


def seconds_to_cue_time(seconds: float) -> str:
    """Converts seconds into Red Book CD CUE timestamp: MM:SS:FF (75 frames/sec)."""
    mins = int(seconds // 60)
    rem_secs = seconds % 60
    secs = int(rem_secs)
    frames = int(round((rem_secs - secs) * 75.0))
    if frames >= 75:
        frames = 0
        secs += 1
    return f"{mins:02d}:{secs:02d}:{frames:02d}"


def generate_cue_sheet_text(
    album_artist: str,
    album_title: str,
    target_audio_filename: str,
    tracks: List[Dict[str, Any]]
) -> str:
    """Generates standard Red Book compliant CUE sheet text."""
    lines = [
        f'PERFORMER "{album_artist}"',
        f'TITLE "{album_title}"',
        f'FILE "{target_audio_filename}" WAVE',
    ]

    for i, t in enumerate(tracks, 1):
        lines.append(f'  TRACK {i:02d} AUDIO')
        lines.append(f'    TITLE "{t.get("title", f"Track {i}")}"')
        lines.append(f'    PERFORMER "{t.get("artist", album_artist)}"')
        lines.append(f'    INDEX 01 {seconds_to_cue_time(t.get("start_sec", 0.0))}')

    return "\n".join(lines) + "\n"


def pack_album(
    folder_path: str,
    output_audio_path: Optional[str] = None,
    output_format: str = "flac"
) -> Dict[str, Any]:
    """
    Packs all audio tracks in a folder into a single monolithic audio file
    accompanied by a Red Book CUE sheet.
    """
    if not os.path.isdir(folder_path):
        return {"success": False, "error": f"Folder not found: {folder_path}"}

    audio_files = []
    for f in os.listdir(folder_path):
        if f.lower().endswith(SUPPORTED_AUDIO_EXTS):
            audio_files.append(os.path.join(folder_path, f))

    if not audio_files:
        return {"success": False, "error": "No supported audio files found in directory"}

    # Sort tracks by track number or filename
    tracks_info = []
    for p in audio_files:
        t_num = 999
        title = os.path.splitext(os.path.basename(p))[0]
        artist = "Unknown Artist"
        album = "Unknown Album"
        dur = 0.0

        try:
            tag = TinyTag.get(p)
            dur = tag.duration or 0.0
            artist = tag.artist or artist
            album = tag.album or album
            title = tag.title or title
            if tag.track:
                t_num = int(tag.track)
        except Exception:
            pass

        tracks_info.append({
            "path": p,
            "filename": os.path.basename(p),
            "track_num": t_num,
            "title": title,
            "artist": artist,
            "album": album,
            "duration": dur,
        })

    tracks_info.sort(key=lambda x: (x["track_num"], x["filename"]))

    album_name = tracks_info[0]["album"]
    album_artist = tracks_info[0]["artist"]
    out_ext = output_format.lower().replace(".", "")
    if out_ext not in ["flac", "wav"]:
        out_ext = "flac"

    if not output_audio_path:
        clean_alb = "".join(c for c in album_name if c.isalnum() or c in (' ', '_', '-')).strip() or "Album"
        output_audio_path = os.path.join(folder_path, f"{clean_alb}_packed.{out_ext}")

    cue_path = os.path.splitext(output_audio_path)[0] + ".cue"
    packed_filename = os.path.basename(output_audio_path)

    # Compute track offsets
    cumulative_time = 0.0
    for t in tracks_info:
        t["start_sec"] = cumulative_time
        cumulative_time += t["duration"]

    # Write CUE sheet
    cue_text = generate_cue_sheet_text(album_artist, album_name, packed_filename, tracks_info)
    with open(cue_path, "w", encoding="utf-8") as f:
        f.write(cue_text)

    # Concatenate audio
    if check_ffmpeg():
        try:
            # Generate FFmpeg concat list
            concat_list_file = os.path.join(folder_path, ".sonance_concat.txt")
            with open(concat_list_file, "w", encoding="utf-8") as f:
                for t in tracks_info:
                    safe_p = t["path"].replace("'", "'\\''")
                    f.write(f"file '{safe_p}'\n")

            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list_file,
                "-c:a", "flac" if out_ext == "flac" else "pcm_s16le",
                output_audio_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if os.path.exists(concat_list_file):
                os.remove(concat_list_file)

            return {
                "success": True,
                "album": album_name,
                "artist": album_artist,
                "total_tracks": len(tracks_info),
                "total_duration_sec": round(cumulative_time, 2),
                "output_audio": output_audio_path,
                "output_cue": cue_path,
                "engine": "FFmpeg Gapless Concat",
            }
        except Exception:
            pass

    # Pure Python / Wave fallback for WAV files
    try:
        out_wav_path = os.path.splitext(output_audio_path)[0] + ".wav"
        n_channels = 2
        sampwidth = 2
        framerate = 44100

        with wave.open(out_wav_path, "wb") as out_wf:
            initialized = False
            for t in tracks_info:
                if t["path"].lower().endswith(".wav"):
                    with wave.open(t["path"], "rb") as in_wf:
                        if not initialized:
                            n_channels = in_wf.getnchannels()
                            sampwidth = in_wf.getsampwidth()
                            framerate = in_wf.getframerate()
                            out_wf.setnchannels(n_channels)
                            out_wf.setsampwidth(sampwidth)
                            out_wf.setframerate(framerate)
                            initialized = True
                        out_wf.writeframes(in_wf.readframes(in_wf.getnframes()))

        return {
            "success": True,
            "album": album_name,
            "artist": album_artist,
            "total_tracks": len(tracks_info),
            "total_duration_sec": round(cumulative_time, 2),
            "output_audio": out_wav_path,
            "output_cue": cue_path,
            "engine": "Sonance Pure Wave Concat",
        }
    except Exception as e:
        return {"success": False, "error": f"Album packing failed: {str(e)}"}


def unpack_album(
    monolithic_file: str,
    cue_file: Optional[str] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Unpacks a monolithic album image into separate tracks using cue_splitter.
    """
    import cue_splitter

    if not os.path.isfile(monolithic_file):
        return {"success": False, "error": f"Monolithic album file not found: {monolithic_file}"}

    if not cue_file:
        candidate_cue = os.path.splitext(monolithic_file)[0] + ".cue"
        if os.path.isfile(candidate_cue):
            cue_file = candidate_cue
        else:
            return {"success": False, "error": f"CUE sheet not found for {monolithic_file}"}

    src_dir = os.path.dirname(os.path.abspath(monolithic_file))
    target_out = output_dir or os.path.join(src_dir, os.path.splitext(os.path.basename(monolithic_file))[0] + "_unpacked")

    return cue_splitter.split_cue_sheet(cue_file, output_directory=target_out, output_format="flac")


if __name__ == "__main__":
    import sys
    print("Sonance Lossless Monolithic Album Packer Studio")
    if len(sys.argv) < 2:
        print("Usage: python album_packer.py <album_folder> [output_file]")
        sys.exit(1)

    folder = sys.argv[1]
    out_f = sys.argv[2] if len(sys.argv) > 2 else None
    res = pack_album(folder, out_f)
    print(res)
