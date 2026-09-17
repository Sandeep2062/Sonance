#!/usr/bin/env python3
"""
word_karaoke.py - Enhanced LRC (ELRC) & Word-by-Word Syllable Karaoke Timing Engine
Author: Sandeep Khadka (Sandeep2062 <sandeepkhadka9090@gmail.com>)
License: GNU GPLv3 with Commons Clause

Parses and generates Enhanced LRC format lyrics containing millisecond-accurate
word-by-word and syllable-by-syllable timing tags (<mm:ss.xx> word <mm:ss.xx>).
Enables Apple Music / Spotify Sing-style glowing real-time text sweep synchronization.
"""

import re
import sys
from typing import Dict, Any, List, Optional

# Ensure standard UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def parse_timestamp(time_str: str) -> float:
    """Converts mm:ss.xx or mm:ss:xx timestamp into float seconds."""
    parts = time_str.strip().replace(":", ".").split(".")
    if len(parts) >= 3:
        try:
            mins = int(parts[0])
            secs = int(parts[1])
            ms_str = parts[2]
            if len(ms_str) == 2:
                ms = int(ms_str) * 10
            elif len(ms_str) == 3:
                ms = int(ms_str)
            else:
                ms = int(ms_str[:3].ljust(3, "0"))
            return mins * 60.0 + secs + (ms / 1000.0)
        except Exception:
            return 0.0
    elif len(parts) == 2:
        try:
            mins = int(parts[0])
            secs = float(parts[1])
            return mins * 60.0 + secs
        except Exception:
            return 0.0
    return 0.0


def format_timestamp(seconds: float, bracket: bool = False, tag_type: str = "line") -> str:
    """Formats float seconds into [mm:ss.xx] or <mm:ss.xx> timestamp."""
    if seconds < 0:
        seconds = 0.0
    mins = int(seconds // 60)
    rem = seconds - (mins * 60)
    secs = int(rem)
    hundredths = int(round((rem - secs) * 100))
    if hundredths >= 100:
        secs += 1
        hundredths = 0
    t_str = f"{mins:02d}:{secs:02d}.{hundredths:02d}"
    if bracket:
        return f"[{t_str}]" if tag_type == "line" else f"<{t_str}>"
    return t_str


def count_syllables(word: str) -> int:
    """Estimates the number of syllables in an English or phonetic word."""
    w = word.strip().lower()
    if not w:
        return 1
    # Remove non-alpha
    w = re.sub(r"[^a-z]", "", w)
    if not w or len(w) <= 2:
        return 1

    # Basic syllable counting heuristic
    count = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith("le") and len(w) > 3 and not w.endswith("ee"):
        count -= 1
    return max(1, count)


def parse_enhanced_lrc(lrc_text: str) -> Dict[str, Any]:
    """
    Parses an LRC string. Accurately identifies whether it contains word-level
    enhanced tags (<mm:ss.xx> word) or line-level tags, and produces structured
    word tokens with start, end, and duration.
    """
    if not lrc_text or not lrc_text.strip():
        return {"success": False, "is_enhanced": False, "lines": []}

    lines = lrc_text.splitlines()
    parsed_lines: List[Dict[str, Any]] = []
    has_word_timing = False
    metadata: Dict[str, str] = {}

    line_regex = re.compile(r"^\[(\d{1,2}:\d{2}[\.:]\d{1,3})\](.*)$")
    word_tag_regex = re.compile(r"<(\d{1,2}:\d{2}[\.:]\d{1,3})>([^<]*)")

    for raw_line in lines:
        line_clean = raw_line.strip()
        if not line_clean:
            continue

        # Check metadata headers: [ar: ...], [ti: ...], [al: ...]
        meta_m = re.match(r"^\[([a-zA-Z]+):([^\]]*)\]$", line_clean)
        if meta_m:
            metadata[meta_m.group(1).lower()] = meta_m.group(2).strip()
            continue

        m = line_regex.match(line_clean)
        if not m:
            continue

        line_time = parse_timestamp(m.group(1))
        content = m.group(2)

        # Look for word-level tags: <00:12.34>word
        word_matches = list(word_tag_regex.finditer(content))
        words_data: List[Dict[str, Any]] = []

        if word_matches:
            has_word_timing = True
            for i, wm in enumerate(word_matches):
                w_time = parse_timestamp(wm.group(1))
                w_text = wm.group(2)
                words_data.append({
                    "word": w_text,
                    "start_sec": w_time,
                    "end_sec": w_time + 0.5, # temporary, calculated below
                    "duration": 0.5,
                    "syllables": count_syllables(w_text)
                })

            # Calculate word end times from next word's start time
            for idx in range(len(words_data)):
                cur = words_data[idx]
                if idx + 1 < len(words_data):
                    nxt = words_data[idx + 1]
                    cur["end_sec"] = nxt["start_sec"]
                    cur["duration"] = max(0.05, round(cur["end_sec"] - cur["start_sec"], 3))
                else:
                    cur["end_sec"] = cur["start_sec"] + 0.8
                    cur["duration"] = 0.8

            clean_text = "".join(w["word"] for w in words_data).strip()
        else:
            clean_text = content.strip()

        parsed_lines.append({
            "start_sec": line_time,
            "end_sec": line_time + 4.0, # default 4s until next line
            "text": clean_text,
            "has_word_timing": bool(word_matches),
            "words": words_data
        })

    # Sort lines chronologically
    parsed_lines.sort(key=lambda x: x["start_sec"])

    # Interpolate line end times and evenly distribute words for standard lines
    for i in range(len(parsed_lines)):
        cur = parsed_lines[i]
        if i + 1 < len(parsed_lines):
            cur["end_sec"] = parsed_lines[i + 1]["start_sec"]
        else:
            cur["end_sec"] = cur["start_sec"] + 4.0
        cur["duration"] = max(0.2, round(cur["end_sec"] - cur["start_sec"], 3))

        # If line had no explicit word tags, synthesize distributed words
        if not cur["words"] and cur["text"]:
            words = cur["text"].split()
            if words:
                w_count = len(words)
                total_syllables = sum(count_syllables(w) for w in words)
                elapsed = cur["start_sec"]
                syn_words = []
                for w in words:
                    syl = count_syllables(w)
                    w_dur = (cur["duration"] * (syl / total_syllables)) if total_syllables > 0 else (cur["duration"] / w_count)
                    syn_words.append({
                        "word": w + " ",
                        "start_sec": round(elapsed, 3),
                        "end_sec": round(elapsed + w_dur, 3),
                        "duration": round(w_dur, 3),
                        "syllables": syl
                    })
                    elapsed += w_dur
                cur["words"] = syn_words

    return {
        "success": True,
        "is_enhanced": has_word_timing,
        "metadata": metadata,
        "total_lines": len(parsed_lines),
        "lines": parsed_lines
    }


def export_enhanced_lrc(parsed_data: Dict[str, Any]) -> str:
    """Converts parsed lines data back to a standardized Enhanced LRC format."""
    lines_out = []
    meta = parsed_data.get("metadata", {})
    for k, v in meta.items():
        lines_out.append(f"[{k}:{v}]")

    for line in parsed_data.get("lines", []):
        t_tag = format_timestamp(line["start_sec"], bracket=True, tag_type="line")
        words = line.get("words", [])
        if words:
            word_str = "".join(f"{format_timestamp(w['start_sec'], bracket=True, tag_type='word')}{w['word']}" for w in words)
            lines_out.append(f"{t_tag}{word_str}")
        else:
            lines_out.append(f"{t_tag}{line.get('text', '')}")

    return "\n".join(lines_out)


if __name__ == "__main__":
    print("Testing word_karaoke module...")
    sample_elrc = (
        "[ar:Daft Punk]\n"
        "[ti:One More Time]\n"
        "[00:15.20]<00:15.20>One <00:15.60>more <00:16.00>time\n"
        "[00:17.50]<00:17.50>We're <00:17.90>gonna <00:18.30>celebrate\n"
    )
    res = parse_enhanced_lrc(sample_elrc)
    assert res["success"] is True
    assert res["is_enhanced"] is True
    assert len(res["lines"]) == 2
    assert len(res["lines"][0]["words"]) == 3
    print(f"✓ Parsed Enhanced LRC with {len(res['lines'])} lines, word-level timing confirmed!")
    exported = export_enhanced_lrc(res)
    assert "[ar:Daft Punk]" in exported
    print("✓ Word karaoke unit test passed successfully!")
