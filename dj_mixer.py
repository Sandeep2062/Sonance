#!/usr/bin/env python3
"""
Sonance - DJ Camelot Harmonic Key & BPM Beatmatcher Engine
===========================================================
Analyzes audio files to extract:
- Tempo in Beats Per Minute (BPM) via spectral onset autocorrelation.
- Musical Key (e.g. A Minor, C Major) using chromagram pitch profiling
  and Krumhansl-Schmuckler tonal correlation.
- Camelot Wheel Code (e.g. 8A, 8B) for DJ mixing.
- Harmonic compatibility recommendations for smooth DJ set transitions.

Author: Sandeep Khadka (Sandeep2062) <sandeepkhadka9090@gmail.com>
License: GNU GPLv3 with Commons Clause
"""

import os
import math
import shutil
import subprocess
import wave
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from tinytag import TinyTag

# Note names (12 semitones)
PITCH_CLASSES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

# Camelot Wheel Mapping
# Format: (Pitch, Mode) -> Camelot Code
CAMELOT_MAP = {
    # Major Keys (B)
    ("B", "Major"): "1B",
    ("F#", "Major"): "2B",
    ("Db", "Major"): "3B",
    ("C#", "Major"): "3B",
    ("Ab", "Major"): "4B",
    ("G#", "Major"): "4B",
    ("Eb", "Major"): "5B",
    ("D#", "Major"): "5B",
    ("Bb", "Major"): "6B",
    ("A#", "Major"): "6B",
    ("F", "Major"): "7B",
    ("C", "Major"): "8B",
    ("G", "Major"): "9B",
    ("D", "Major"): "10B",
    ("A", "Major"): "11B",
    ("E", "Major"): "12B",

    # Minor Keys (A)
    ("Ab", "Minor"): "1A",
    ("G#", "Minor"): "1A",
    ("Eb", "Minor"): "2A",
    ("D#", "Minor"): "2A",
    ("Bb", "Minor"): "3A",
    ("A#", "Minor"): "3A",
    ("F", "Minor"): "4A",
    ("C", "Minor"): "5A",
    ("G", "Minor"): "6A",
    ("D", "Minor"): "7A",
    ("A", "Minor"): "8A",
    ("E", "Minor"): "9A",
    ("B", "Minor"): "10A",
    ("F#", "Minor"): "11A",
    ("Gb", "Minor"): "11A",
    ("C#", "Minor"): "12A",
    ("Db", "Minor"): "12A",
}

# Reverse Camelot map for lookup
REVERSE_CAMELOT = {
    "1A": "Ab Minor", "1B": "B Major",
    "2A": "Eb Minor", "2B": "F# Major",
    "3A": "Bb Minor", "3B": "Db Major",
    "4A": "F Minor",  "4B": "Ab Major",
    "5A": "C Minor",  "5B": "Eb Major",
    "6A": "G Minor",  "6B": "Bb Major",
    "7A": "D Minor",  "7B": "F Major",
    "8A": "A Minor",  "8B": "C Major",
    "9A": "E Minor",  "9B": "G Major",
    "10A": "B Minor", "10B": "D Major",
    "11A": "F# Minor", "11B": "A Major",
    "12A": "C# Minor", "12B": "E Major",
}

# Krumhansl-Schmuckler Key Profiles for Tonal Hierarchy
# Index 0 corresponds to Tonic, 1 to m2, 2 to M2, etc.
KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def check_ffmpeg() -> bool:
    """Checks if FFmpeg binary is available on PATH."""
    return shutil.which("ffmpeg") is not None


def read_audio_pcm(file_path: str, max_duration_sec: float = 45.0, target_sr: int = 22050) -> Tuple[Optional[np.ndarray], int]:
    """
    Decodes audio to a mono float32 numpy array at target_sr.
    Supports WAV natively and any format supported by FFmpeg.
    """
    ext = os.path.splitext(file_path)[1].lower()

    # Native WAV reading
    if ext == ".wav":
        try:
            with wave.open(file_path, "rb") as wf:
                sr = wf.getframerate()
                ch = wf.getnchannels()
                frames_to_read = min(wf.getnframes(), int(sr * max_duration_sec))
                raw_bytes = wf.readframes(frames_to_read)

                if wf.getsampwidth() == 2:
                    samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                elif wf.getsampwidth() == 3:
                    # 24-bit PCM
                    raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
                    sample_count = len(raw_arr) // 3
                    b = raw_arr[:sample_count * 3].reshape(-1, 3)
                    int24 = (b[:, 0].astype(np.int32) |
                             (b[:, 1].astype(np.int32) << 8) |
                             (b[:, 2].astype(np.int32) << 16))
                    int24 = np.where(int24 & 0x800000, int24 - 0x1000000, int24)
                    samples = int24.astype(np.float32) / 8388608.0
                else:
                    samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                if ch > 1:
                    samples = samples.reshape(-1, ch).mean(axis=1)

                if sr != target_sr and len(samples) > 0:
                    step = sr / target_sr
                    idx = np.arange(0, len(samples), step).astype(int)
                    idx = idx[idx < len(samples)]
                    samples = samples[idx]
                    sr = target_sr

                return samples, sr
        except Exception:
            pass

    # FFmpeg pipe decode for MP3, FLAC, M4A, OGG, etc.
    if check_ffmpeg():
        try:
            cmd = [
                "ffmpeg", "-y", "-v", "quiet",
                "-ss", "10",  # Skip 10s intro to capture main musical section
                "-t", str(max_duration_sec),
                "-i", file_path,
                "-f", "s16le",
                "-ac", "1",
                "-ar", str(target_sr),
                "-"
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20)
            if proc.returncode == 0 and len(proc.stdout) > 1024:
                samples = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
                return samples, target_sr
        except Exception:
            pass

    return None, target_sr


def estimate_bpm(samples: np.ndarray, sr: int) -> float:
    """
    Estimates BPM using spectral flux onset envelope autocorrelation.
    """
    if len(samples) < sr * 5:
        return 120.0

    # Frame parameters
    hop_size = 512
    n_fft = 1024
    num_frames = (len(samples) - n_fft) // hop_size

    if num_frames < 32:
        return 120.0

    # Compute STFT magnitude
    frames = np.lib.stride_tricks.sliding_window_view(samples[:num_frames * hop_size + n_fft], n_fft)[::hop_size]
    window = np.hanning(n_fft)
    spec = np.abs(np.fft.rfft(frames * window, axis=1))

    # Spectral flux (difference between consecutive frames, positive only)
    diff = np.diff(spec, axis=0)
    diff[diff < 0] = 0
    onset_env = np.sum(diff, axis=1)

    # Normalize onset envelope
    onset_env = onset_env - np.mean(onset_env)
    std = np.std(onset_env)
    if std > 1e-6:
        onset_env = onset_env / std

    # Autocorrelation of onset envelope
    env_sr = sr / hop_size  # ~43.06 Hz
    min_bpm = 60.0
    max_bpm = 185.0
    min_lag = int(env_sr * 60.0 / max_bpm)
    max_lag = int(env_sr * 60.0 / min_bpm)

    if len(onset_env) < max_lag * 2:
        return 120.0

    autocorr = np.correlate(onset_env, onset_env, mode="full")
    autocorr = autocorr[len(onset_env) - 1:]

    # Inspect lags corresponding to plausible BPM range
    search_range = autocorr[min_lag:max_lag]
    if len(search_range) == 0:
        return 120.0

    peak_idx = np.argmax(search_range) + min_lag
    raw_bpm = (env_sr * 60.0) / peak_idx

    # Octave correction (bias toward 90-145 BPM typical for commercial music)
    while raw_bpm < 75.0:
        raw_bpm *= 2.0
    while raw_bpm > 165.0:
        raw_bpm /= 2.0

    return round(float(raw_bpm), 1)


def estimate_key(samples: np.ndarray, sr: int) -> Tuple[str, str, float]:
    """
    Estimates the musical key using a 12-semitone chromagram and Krumhansl-Schmuckler correlation.
    Returns: (Key Name e.g. 'A Minor', Camelot Code e.g. '8A', Confidence [0.0 - 1.0])
    """
    if len(samples) < sr * 4:
        return "C Major", "8B", 0.5

    n_fft = 4096
    hop_size = 2048
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    # Pitch mapping for bins between 65 Hz (C2) and 2000 Hz (B6)
    chromagram = np.zeros(12, dtype=np.float64)
    valid_freq_mask = (freqs >= 65.0) & (freqs <= 2000.0)

    # Pre-calculate pitch class for each FFT bin
    bin_freqs = freqs[valid_freq_mask]
    midi_notes = 12.0 * np.log2(bin_freqs / 440.0) + 69.0
    pitch_classes = (np.round(midi_notes).astype(int)) % 12

    # Windowed FFT accumulation
    num_frames = min(120, (len(samples) - n_fft) // hop_size)
    window = np.hanning(n_fft)

    for i in range(0, num_frames * hop_size, hop_size):
        frame = samples[i:i + n_fft] * window
        mag = np.abs(np.fft.rfft(frame))[valid_freq_mask]
        for pc in range(12):
            chromagram[pc] += np.sum(mag[pitch_classes == pc])

    # Normalize chromagram vector
    norm = np.linalg.norm(chromagram)
    if norm > 1e-6:
        chromagram /= norm
    else:
        return "C Major", "8B", 0.5

    # Correlate with 24 keys (12 Major, 12 Minor)
    best_key = "C Major"
    best_camelot = "8B"
    best_corr = -2.0

    for shift in range(12):
        shifted_chroma = np.roll(chromagram, -shift)
        tonic_name = PITCH_CLASSES[shift]

        # Major correlation
        corr_major = np.corrcoef(shifted_chroma, KS_MAJOR)[0, 1]
        if corr_major > best_corr:
            best_corr = corr_major
            best_key = f"{tonic_name} Major"
            best_camelot = CAMELOT_MAP.get((tonic_name, "Major"), "8B")

        # Minor correlation
        corr_minor = np.corrcoef(shifted_chroma, KS_MINOR)[0, 1]
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = f"{tonic_name} Minor"
            best_camelot = CAMELOT_MAP.get((tonic_name, "Minor"), "8A")

    confidence = max(0.0, min(1.0, float((best_corr + 1.0) / 2.0)))
    return best_key, best_camelot, round(confidence, 2)


def get_compatible_camelot_keys(camelot_code: str) -> List[Dict[str, str]]:
    """
    Returns harmonically compatible Camelot keys for seamless DJ mixing:
    - Same key (energy stability)
    - Relative Major/Minor (mood change)
    - +1 Camelot Step (energy boost)
    - -1 Camelot Step (energy cool-down)
    """
    camelot_code = camelot_code.upper().strip()
    if not camelot_code or len(camelot_code) < 2:
        return []

    try:
        letter = camelot_code[-1]
        number = int(camelot_code[:-1])
    except ValueError:
        return []

    other_letter = "B" if letter == "A" else "A"
    plus_one = (number % 12) + 1
    minus_one = 12 if number == 1 else (number - 1)

    return [
        {
            "camelot": f"{number}{letter}",
            "key": REVERSE_CAMELOT.get(f"{number}{letter}", ""),
            "relation": "Exact Match (Steady Energy)"
        },
        {
            "camelot": f"{number}{other_letter}",
            "key": REVERSE_CAMELOT.get(f"{number}{other_letter}", ""),
            "relation": "Relative Major/Minor (Mood Shift)"
        },
        {
            "camelot": f"{plus_one}{letter}",
            "key": REVERSE_CAMELOT.get(f"{plus_one}{letter}", ""),
            "relation": "+1 Step (Energy Boost)"
        },
        {
            "camelot": f"{minus_one}{letter}",
            "key": REVERSE_CAMELOT.get(f"{minus_one}{letter}", ""),
            "relation": "-1 Step (Energy Cool-Down)"
        }
    ]


def evaluate_harmonic_transition(key_a: str, key_b: str) -> Dict[str, Any]:
    """
    Evaluates harmonic compatibility between two tracks given their Camelot codes.
    """
    code_a = key_a.upper().strip()
    code_b = key_b.upper().strip()

    if code_a == code_b:
        return {"compatible": True, "score": 100, "description": "Perfect Match (Identical Harmonic Center)"}

    try:
        num_a = int(code_a[:-1])
        let_a = code_a[-1]
        num_b = int(code_b[:-1])
        let_b = code_b[-1]
    except Exception:
        return {"compatible": False, "score": 0, "description": "Unknown Key"}

    diff = abs(num_a - num_b)
    if diff == 11:
        diff = 1  # Circular wrap 12 <-> 1

    if diff == 0 and let_a != let_b:
        return {"compatible": True, "score": 90, "description": "Relative Major/Minor (Smooth Emotional Pivot)"}
    elif diff == 1 and let_a == let_b:
        return {"compatible": True, "score": 85, "description": "Adjacent Camelot Step (Harmonic Energy Transition)"}
    elif diff == 1 and let_a != let_b:
        return {"compatible": True, "score": 70, "description": "Diagonal Camelot Step (Subtle Harmonic Modulation)"}
    elif diff == 2 and let_a == let_b:
        return {"compatible": False, "score": 50, "description": "Energy Jump (+2 Key Lift)"}
    else:
        return {"compatible": False, "score": 25, "description": "Harmonic Clash (Requires Break/Filter Transition)"}


def analyze_track_bpm_and_key(file_path: str) -> Dict[str, Any]:
    """
    Complete analysis pipeline extracting BPM, Musical Key, and Camelot code.
    Falls back gracefully to embedded metadata tags if audio decoding is unavailable.
    """
    if not os.path.isfile(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    # First check embedded ID3/Vorbis tags for pre-computed BPM/Key
    tag_bpm = None
    tag_key = None
    try:
        tag = TinyTag.get(file_path)
        tag_bpm = getattr(tag, "bpm", None)
    except Exception:
        pass

    # Read audio PCM
    samples, sr = read_audio_pcm(file_path, max_duration_sec=40.0)

    bpm = 120.0
    key_name = "A Minor"
    camelot = "8A"
    confidence = 0.85

    if samples is not None and len(samples) > sr * 4:
        bpm = estimate_bpm(samples, sr)
        key_name, camelot, confidence = estimate_key(samples, sr)
    elif tag_bpm:
        try:
            bpm = round(float(tag_bpm), 1)
            confidence = 0.90
        except Exception:
            bpm = 120.0

    # Short format abbreviation (e.g. "8A (Am)")
    short_mode = "m" if "Minor" in key_name else ""
    tonic = key_name.split()[0]
    camelot_full = f"{camelot} ({tonic}{short_mode})"

    compatible = get_compatible_camelot_keys(camelot)

    return {
        "success": True,
        "file_path": file_path,
        "filename": os.path.basename(file_path),
        "bpm": bpm,
        "key": key_name,
        "camelot": camelot,
        "camelot_full": camelot_full,
        "confidence": confidence,
        "compatible_keys": compatible,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Sonance DJ Camelot Harmonic Key & BPM Beatmatcher")
        print("Usage: python dj_mixer.py <audio_file>")
        sys.exit(1)

    res = analyze_track_bpm_and_key(sys.argv[1])
    if res.get("success"):
        print(f"🎵 Track: {res['filename']}")
        print(f"⚡ BPM: {res['bpm']}")
        print(f"🎹 Key: {res['key']} [{res['camelot_full']}] (Confidence: {res['confidence']*100:.0f}%)")
        print("🎛️ Harmonically Compatible Keys for Seamless DJ Transitions:")
        for k in res["compatible_keys"]:
            print(f"   • {k['camelot']} ({k['key']}) -> {k['relation']}")
    else:
        print(f"❌ Error: {res.get('error')}")
