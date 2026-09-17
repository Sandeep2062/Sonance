"""
word_aligner.py - Enhanced Word-by-Word ELRC Syllable Aligner & Transient Snapper
Part of Sonance - The Ultimate Open-Source Music Workstation
Generates Apple Music / Spotify Sing style Enhanced LRC (<mm:ss.xx> word timestamps)
using acoustic transient onset detection and phonetic syllable length weighting.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import re
import wave
import subprocess
import shutil
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Regex for standard LRC lines: [mm:ss.xx] Lyrics text
LRC_LINE_REGEX = re.compile(r"^\[(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]\s*(.*)$")
# Regex for already enhanced LRC lines with <mm:ss.xx> tags
ELRC_TAG_REGEX = re.compile(r"<(\d{1,2}):(\d{2}(?:\.\d{1,3})?)>")


def format_lrc_timestamp(seconds: float) -> str:
    """Formats seconds into [mm:ss.xx] timestamp string."""
    seconds = max(0.0, seconds)
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


def parse_timestamp_to_seconds(time_str: str) -> float:
    """Parses mm:ss.xx or mm:ss into float seconds."""
    parts = time_str.split(":")
    if len(parts) == 2:
        return float(parts[0]) * 60.0 + float(parts[1])
    return 0.0


def estimate_word_syllables(word: str) -> int:
    """Estimates the syllable count of an English or Latin-script word."""
    clean = re.sub(r"[^a-zA-Z]", "", word).lower()
    if not clean:
        return 1
    # Count vowel groups
    vowel_runs = re.findall(r"[aeiouy]+", clean)
    count = len(vowel_runs)
    # Silent 'e' at end
    if clean.endswith("e") and not clean.endswith("le") and len(clean) > 2 and count > 1:
        count -= 1
    return max(1, count)


def _detect_audio_onsets(
    audio_path: str,
    start_sec: float,
    end_sec: float,
    target_count: int
) -> List[float]:
    """
    Computes acoustic energy transients within [start_sec, end_sec]
    to locate syllable attacks.
    """
    try:
        # Load audio slice
        dur = max(0.2, end_sec - start_sec)
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        cmd = [
            ffmpeg_bin, "-v", "error",
            "-ss", str(start_sec),
            "-t", str(dur),
            "-i", audio_path,
            "-f", "f32le",
            "-acodec", "pcm_f32le",
            "-ar", "22050",
            "-ac", "1",
            "-"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        raw_pcm, _ = proc.communicate()
        if not raw_pcm:
            return []

        samples = np.frombuffer(raw_pcm, dtype=np.float32)
        sr = 22050
        frame_len = int(0.02 * sr)  # 20ms frame
        hop_len = int(0.01 * sr)    # 10ms hop
        if len(samples) < frame_len:
            return []

        # Short-time RMS energy
        n_frames = (len(samples) - frame_len) // hop_len
        energy = np.zeros(n_frames, dtype=np.float32)
        for i in range(n_frames):
            frame = samples[i * hop_len : i * hop_len + frame_len]
            energy[i] = np.sqrt(np.mean(frame ** 2) + 1e-12)

        # Spectral flux / onset novelty (positive difference)
        flux = np.maximum(0.0, np.diff(energy))
        if len(flux) == 0:
            return []

        # Find top target_count peaks
        peak_indices = []
        for i in range(1, len(flux) - 1):
            if flux[i] > flux[i - 1] and flux[i] > flux[i + 1] and flux[i] > 0.01:
                peak_indices.append(i)

        # Sort by flux magnitude descending
        peak_indices.sort(key=lambda idx: flux[idx], reverse=True)
        selected = sorted(peak_indices[:target_count])

        # Convert back to absolute seconds
        timestamps = [start_sec + (idx * hop_len) / sr for idx in selected]
        return timestamps
    except Exception:
        return []


def align_line_words(
    words: List[str],
    start_sec: float,
    end_sec: float,
    audio_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Distributes and aligns words within a single line time window.
    Returns list of dicts: {"word": str, "start": float, "end": float, "timestamp": str}
    """
    if not words:
        return []

    line_duration = max(0.5, end_sec - start_sec)
    n_words = len(words)

    # Calculate syllable weights for each word
    syllable_counts = [estimate_word_syllables(w) for w in words]
    char_lengths = [max(1, len(w)) for w in words]
    # Combined heuristic: 65% syllable count, 35% character length
    weights = [0.65 * s + 0.35 * (c / 3.0) for s, c in zip(syllable_counts, char_lengths)]
    total_weight = sum(weights) or float(n_words)

    # 1. Proportional time allocation
    ideal_starts = []
    current_t = start_sec
    for w in weights:
        ideal_starts.append(current_t)
        current_t += (w / total_weight) * line_duration

    # 2. Refine with acoustic transients if audio is available
    if audio_path and os.path.isfile(audio_path) and n_words > 1:
        onsets = _detect_audio_onsets(audio_path, start_sec, end_sec, target_count=n_words)
        if len(onsets) >= 2:
            # Snap ideal starts toward detected onsets if within reasonable tolerance (250ms)
            for i in range(1, n_words):
                closest_onset = min(onsets, key=lambda o: abs(o - ideal_starts[i]))
                if abs(closest_onset - ideal_starts[i]) <= 0.25:
                    if closest_onset > ideal_starts[i - 1] + 0.08:
                        ideal_starts[i] = closest_onset

    # Build word result entries
    word_entries = []
    for i in range(n_words):
        w_start = ideal_starts[i]
        w_end = ideal_starts[i + 1] if i + 1 < n_words else end_sec
        word_entries.append({
            "word": words[i],
            "start": round(w_start, 2),
            "end": round(w_end, 2),
            "timestamp": format_lrc_timestamp(w_start),
        })

    return word_entries


def generate_enhanced_lrc(
    lrc_content: str,
    audio_path: Optional[str] = None,
    default_line_dur: float = 3.5
) -> Dict[str, Any]:
    """
    Converts standard line-by-line LRC text into word-by-word Enhanced LRC (ELRC).
    """
    lines = lrc_content.strip().splitlines()
    parsed_lines = []

    # 1. Parse lines and timestamps
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = LRC_LINE_REGEX.match(line)
        if m:
            time_str, sec_str, text = m.groups()
            sec = parse_timestamp_to_seconds(f"{time_str}:{sec_str}")
            parsed_lines.append({"start": sec, "text": text.strip()})
        else:
            # Metadata tag like [ar: Artist] or untimed line
            parsed_lines.append({"start": None, "text": line})

    # 2. Determine line end times
    timed_indices = [i for i, p in enumerate(parsed_lines) if p["start"] is not None]
    for idx_pos, i in enumerate(timed_indices):
        current_start = parsed_lines[i]["start"]
        if idx_pos + 1 < len(timed_indices):
            next_start = parsed_lines[timed_indices[idx_pos + 1]]["start"]
            parsed_lines[i]["end"] = min(next_start, current_start + 8.0)
        else:
            parsed_lines[i]["end"] = current_start + default_line_dur

    # 3. Align each timed line into words
    elrc_lines = []
    total_aligned_words = 0

    for p in parsed_lines:
        if p["start"] is None:
            elrc_lines.append(p["text"])
            continue

        text = p["text"]
        if not text:
            elrc_lines.append(f"[{format_lrc_timestamp(p['start'])}]")
            continue

        words = text.split()
        if not words:
            elrc_lines.append(f"[{format_lrc_timestamp(p['start'])}] {text}")
            continue

        aligned = align_line_words(words, p["start"], p["end"], audio_path=audio_path)
        total_aligned_words += len(aligned)

        # Build Enhanced LRC line:
        # [00:12.34] <00:12.34> Never <00:12.80> gonna <00:13.10> give
        line_prefix = f"[{format_lrc_timestamp(p['start'])}]"
        tokens = [f"<{w['timestamp']}> {w['word']}" for w in aligned]
        enhanced_line = f"{line_prefix} {' '.join(tokens)}"
        elrc_lines.append(enhanced_line)

    enhanced_lrc_text = "\n".join(elrc_lines)

    return {
        "success": True,
        "enhanced_lrc": enhanced_lrc_text,
        "total_lines": len(parsed_lines),
        "total_words_aligned": total_aligned_words,
    }


def save_enhanced_lrc(
    enhanced_lrc: str,
    output_path: str
) -> bool:
    """Saves enhanced LRC content to disk."""
    try:
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(enhanced_lrc)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python word_aligner.py <lrc_file> [audio_file] [output_elrc]")
        sys.exit(1)

    lrc_file = sys.argv[1]
    audio_file = sys.argv[2] if len(sys.argv) > 2 and os.path.isfile(sys.argv[2]) else None
    out_file = sys.argv[3] if len(sys.argv) > 3 else (os.path.splitext(lrc_file)[0] + ".elrc")

    if not os.path.isfile(lrc_file):
        print(f"Error: LRC file not found: {lrc_file}")
        sys.exit(1)

    with open(lrc_file, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"Aligning lyrics from: {lrc_file}...")
    res = generate_enhanced_lrc(content, audio_path=audio_file)
    if res.get("success"):
        save_enhanced_lrc(res["enhanced_lrc"], out_file)
        print(f"Success! Aligned {res['total_words_aligned']} words across {res['total_lines']} lines.")
        print(f"Saved Enhanced LRC to: {out_file}")
        print("\nSample Output:")
        sample_lines = res["enhanced_lrc"].splitlines()[:5]
        for l in sample_lines:
            print(" ", l)
    else:
        print("Error during alignment.")
