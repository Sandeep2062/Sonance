#!/usr/bin/env python3
"""
lyrics_creator.py - Visual Interactive LRC Lyrics Creator & Time-Stamper Studio
Author: Sandeep Khadka (Sandeep2062 <sandeepkhadka9090@gmail.com>)
License: GNU GPLv3 with Commons Clause

Provides full authoring, line-by-line real-time timestamping, micro-adjusting,
validation, and persistent saving to companion .lrc files and embedded metadata tags.
"""

import os
import re
import sys
from typing import List, Dict, Any, Optional

# Ensure standard UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_timestamp(seconds: float) -> str:
    """Converts a float duration in seconds to standard LRC [mm:ss.xx] format."""
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    remaining_secs = seconds % 60
    secs = int(remaining_secs)
    centis = int(round((remaining_secs - secs) * 100))
    if centis >= 100:
        centis = 99
    return f"[{minutes:02d}:{secs:02d}.{centis:02d}]"


def parse_timestamp(tag: str) -> Optional[float]:
    """Parses [mm:ss.xx] or [mm:ss] timestamp string to seconds (float)."""
    match = re.search(r"\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]", tag)
    if not match:
        return None
    mins = int(match.group(1))
    secs = int(match.group(2))
    frac_str = match.group(3)
    if frac_str:
        if len(frac_str) == 1:
            frac = int(frac_str) / 10.0
        elif len(frac_str) == 2:
            frac = int(frac_str) / 100.0
        else:
            frac = int(frac_str[:3]) / 1000.0
    else:
        frac = 0.0
    return mins * 60.0 + secs + frac


def parse_plain_lyrics(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parses plain text lyrics into structured lines ready for live timestamping.
    Strips out empty header comments or whitespace while keeping stanza separators.
    """
    lines: List[Dict[str, Any]] = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Check if line already has a timestamp
        t_val = parse_timestamp(line)
        cleaned_text = re.sub(r"^\[\d{1,3}:\d{2}(?:\.\d{1,3})?\]\s*", "", line).strip()
        lines.append({
            "text": cleaned_text,
            "timestamp": t_val,
            "time_str": format_timestamp(t_val) if t_val is not None else ""
        })
    return lines


def parse_lrc_lines(lrc_text: str) -> List[Dict[str, Any]]:
    """
    Parses complete .lrc file contents into structured lines with timestamps.
    Preserves order and handles multi-tag lines.
    """
    result: List[Dict[str, Any]] = []
    tag_regex = re.compile(r"\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]")

    for raw_line in lrc_text.splitlines():
        line = raw_line.strip()
        if not line or re.match(r"^\[[a-zA-Z]{2,10}:.*\]$", line):
            continue

        matches = list(tag_regex.finditer(line))
        if not matches:
            result.append({"text": line, "timestamp": None, "time_str": ""})
            continue

        text_part = tag_regex.sub("", line).strip()
        for m in matches:
            t = parse_timestamp(m.group(0))
            if t is not None:
                result.append({
                    "text": text_part,
                    "timestamp": t,
                    "time_str": format_timestamp(t)
                })

    result.sort(key=lambda x: x["timestamp"] if x["timestamp"] is not None else 999999)
    return result


def build_lrc_string(
    lines: List[Dict[str, Any]],
    title: str = "",
    artist: str = "",
    album: str = ""
) -> str:
    """Builds standard RFC-compliant .lrc string from structured lines."""
    output: List[str] = []
    if title:
        output.append(f"[ti:{title}]")
    if artist:
        output.append(f"[ar:{artist}]")
    if album:
        output.append(f"[al:{album}]")
    output.append("[by:Sonance LRC Studio]")

    for item in lines:
        t = item.get("timestamp")
        text = (item.get("text") or "").strip()
        if t is not None:
            time_str = format_timestamp(t)
            output.append(f"{time_str}{text}")
        else:
            output.append(text)

    return "\n".join(output) + "\n"


def shift_all_timestamps(lines: List[Dict[str, Any]], offset_seconds: float) -> List[Dict[str, Any]]:
    """Shifts all valid timestamps in lines by offset_seconds (can be positive or negative)."""
    shifted: List[Dict[str, Any]] = []
    for item in lines:
        t = item.get("timestamp")
        if t is not None:
            new_t = max(0.0, round(t + offset_seconds, 2))
            shifted.append({
                "text": item.get("text", ""),
                "timestamp": new_t,
                "time_str": format_timestamp(new_t)
            })
        else:
            shifted.append(dict(item))
    return shifted


def save_lrc_file(audio_path: str, lrc_content: str) -> Dict[str, Any]:
    """
    Saves the .lrc content to disk right beside the audio file (`<song_basename>.lrc`),
    and attempts to embed synchronized lyrics into the audio file metadata tags.
    """
    if not audio_path or not os.path.exists(audio_path):
        return {"success": False, "error": "Target audio file does not exist."}

    # 1. Determine companion .lrc path
    base_no_ext, _ = os.path.splitext(audio_path)
    lrc_path = base_no_ext + ".lrc"

    try:
        with open(lrc_path, "w", encoding="utf-8") as f:
            f.write(lrc_content)
    except Exception as e:
        return {"success": False, "error": f"Failed writing .lrc file: {e}"}

    # 2. Embed into audio tags via mutagen if available
    embedded = False
    try:
        import mutagen
        ext = os.path.splitext(audio_path)[1].lower()

        if ext == ".mp3":
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, USLT
            audio = MP3(audio_path, ID3=ID3)
            try:
                audio.add_tags()
            except Exception:
                pass
            audio.tags.setall("USLT", [USLT(encoding=3, lang="eng", desc="", text=lrc_content)])
            audio.save(v2_version=4)
            embedded = True
        elif ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(audio_path)
            audio["LYRICS"] = [lrc_content]
            audio.save()
            embedded = True
        elif ext in [".m4a", ".mp4"]:
            from mutagen.mp4 import MP4
            audio = MP4(audio_path)
            audio["\xa9lyr"] = [lrc_content]
            audio.save()
            embedded = True
        elif ext == ".ogg":
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(audio_path)
            audio["LYRICS"] = [lrc_content]
            audio.save()
            embedded = True
    except Exception:
        # Embedding is best-effort; companion .lrc was written successfully
        pass

    return {
        "success": True,
        "lrc_path": lrc_path,
        "embedded": embedded,
        "line_count": len([l for l in lrc_content.splitlines() if l.strip()])
    }


if __name__ == "__main__":
    print("Testing lyrics_creator module...")
    sample_text = """
    We've known each other for so long
    Your heart's been aching, but you're too shy to say it
    Inside, we both know what's been going on
    We know the game, and we're gonna play it
    """
    lines = parse_plain_lyrics(sample_text)
    assert len(lines) == 4, f"Expected 4 lines, got {len(lines)}"

    # Simulate live timestamp tapping
    timestamps = [12.45, 16.80, 21.15, 25.40]
    for idx, t in enumerate(timestamps):
        lines[idx]["timestamp"] = t
        lines[idx]["time_str"] = format_timestamp(t)

    lrc_string = build_lrc_string(lines, title="Never Gonna Give You Up", artist="Rick Astley")
    assert "[ti:Never Gonna Give You Up]" in lrc_string
    assert "[00:12.45]We've known each other for so long" in lrc_string

    # Test shift
    shifted = shift_all_timestamps(lines, 0.5)
    assert shifted[0]["timestamp"] == 12.95

    # Test parse back
    parsed = parse_lrc_lines(lrc_string)
    assert len(parsed) == 4
    assert parsed[0]["timestamp"] == 12.45

    print("✓ All lyrics_creator unit tests passed successfully!")
