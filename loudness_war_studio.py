"""
loudness_war_studio.py - Mastering Loudness War & True Dynamic Spread Analyzer Studio
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

ITU-R BS.1770-4 & EBU R128 loudness metrics and dynamic spread analyzer:
- Integrated Loudness (LUFS) with absolute (-70 LKFS) & relative (-10 LU) gating
- Loudness Range (LRA in LU) measuring musical dynamic spread (EBU R128 standard)
- Short-term (3.0s) and Momentary (400ms) loudness tracking
- Crest factor (dB) and true dynamic range preservation analysis
- Loudness War Compression Rating (0% heavily brickwalled to 100% open audiophile master)
- Multi-Platform Streaming Normalization Penalties (Spotify, Apple Music, YouTube, Tidal)
- ASCII visual dynamic spread bar and mastering recommendations
"""

import os
import sys
import math
import wave
import struct
import argparse
from typing import Dict, List, Optional, Tuple, Any

import numpy as np


def read_audio_pcm(file_path: str) -> Tuple[np.ndarray, int]:
    """Reads audio file into float32 array with shape (channels, samples)."""
    try:
        import soundfile as sf
        data, sr = sf.read(file_path, dtype="float32")
        if data.ndim > 1:
            return data.T, sr
        return np.expand_dims(data, axis=0), sr
    except Exception:
        pass

    if file_path.lower().endswith(".wav"):
        with wave.open(file_path, "rb") as wf:
            sr = wf.getframerate()
            n_ch = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        if sampwidth == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 3:
            raw_u = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
            int24 = (raw_u[:, 0].astype(np.int32) |
                     (raw_u[:, 1].astype(np.int32) << 8) |
                     (raw_u[:, 2].astype(np.int32) << 16))
            int24 = (int24 ^ (1 << 23)) - (1 << 23)
            data = int24.astype(np.float32) / 8388608.0
        elif sampwidth == 4:
            data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0

        if n_ch > 1:
            data = data.reshape(-1, n_ch).T
        else:
            data = np.expand_dims(data, axis=0)
        return data, sr

    raise ValueError(f"Unsupported audio format: {file_path}")


def apply_k_weighting(channel: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Applies ITU-R BS.1770-4 K-weighting filter curve:
    Stage 1: High-shelf pre-filter (+4 dB at 1.5 kHz)
    Stage 2: RLB high-pass filter (100 Hz cutoff)
    """
    # Stage 1: High shelf filter coefficients (approx at 48kHz / 44.1kHz)
    # Pre-filter: K-weighting stage 1
    db_gain = 3.99984
    A = 10.0 ** (db_gain / 40.0)
    w0 = 2.0 * math.pi * 1681.97 / sample_rate
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / 2.0 * math.sqrt(2.0)
    two_sqrt_A_alpha = 2.0 * math.sqrt(A) * alpha

    b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + two_sqrt_A_alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - two_sqrt_A_alpha)
    a0 = (A + 1.0) - (A - 1.0) * cos_w0 + two_sqrt_A_alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
    a2 = (A + 1.0) - (A - 1.0) * cos_w0 - two_sqrt_A_alpha

    # Apply stage 1
    b_s1 = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    a_s1 = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)

    # Stage 2: RLB High-pass filter coefficients
    w0_hp = 2.0 * math.pi * 38.135 / sample_rate
    cos_w0_hp = math.cos(w0_hp)
    sin_w0_hp = math.sin(w0_hp)
    alpha_hp = sin_w0_hp / 2.0 * math.sqrt(2.0)

    b0_hp = (1.0 + cos_w0_hp) / 2.0
    b1_hp = -(1.0 + cos_w0_hp)
    b2_hp = (1.0 + cos_w0_hp) / 2.0
    a0_hp = 1.0 + alpha_hp
    a1_hp = -2.0 * cos_w0_hp
    a2_hp = 1.0 - alpha_hp

    b_s2 = np.array([b0_hp / a0_hp, b1_hp / a0_hp, b2_hp / a0_hp], dtype=np.float64)
    a_s2 = np.array([1.0, a1_hp / a0_hp, a2_hp / a0_hp], dtype=np.float64)

    # Fast 2-stage IIR filtering
    s1 = np.zeros_like(channel, dtype=np.float64)
    x = channel.astype(np.float64)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(channel)):
        xi = x[i]
        yi = b_s1[0] * xi + b_s1[1] * x1 + b_s1[2] * x2 - a_s1[1] * y1 - a_s1[2] * y2
        s1[i] = yi
        x2 = x1
        x1 = xi
        y2 = y1
        y1 = yi

    s2 = np.zeros_like(channel, dtype=np.float64)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(channel)):
        xi = s1[i]
        yi = b_s2[0] * xi + b_s2[1] * x1 + b_s2[2] * x2 - a_s2[1] * y1 - a_s2[2] * y2
        s2[i] = yi
        x2 = x1
        x1 = xi
        y2 = y1
        y1 = yi

    return s2.astype(np.float32)


def calculate_gated_loudness(k_channels: np.ndarray, sample_rate: int) -> Tuple[float, float, float, float]:
    """
    Computes Integrated LUFS, Max Momentary LUFS, Max Short-Term LUFS, and Loudness Range (LRA).
    Uses standard BS.1770-4 block gating.
    """
    n_ch, total_samples = k_channels.shape
    block_len = int(sample_rate * 0.400)  # 400ms momentary block
    hop_len = int(sample_rate * 0.100)    # 100ms (75% overlap)
    short_block_len = int(sample_rate * 3.0)  # 3s short-term block

    if total_samples < block_len:
        rms = np.mean(k_channels ** 2)
        lufs = -0.691 + 10.0 * math.log10(max(1e-12, rms))
        return lufs, lufs, lufs, 0.0

    num_blocks = (total_samples - block_len) // hop_len + 1
    block_powers = []

    # Channel weights (Left: 1.0, Right: 1.0, Center: 1.0, LFE: 0.0, Surrounds: 1.41)
    ch_weights = np.ones(n_ch, dtype=np.float64)

    for i in range(num_blocks):
        start = i * hop_len
        chunk = k_channels[:, start:start + block_len]
        ms = np.mean(chunk ** 2, axis=1)
        z = np.sum(ms * ch_weights)
        block_powers.append(z)

    block_powers = np.array(block_powers, dtype=np.float64)
    block_lufs = -0.691 + 10.0 * np.log10(np.maximum(1e-12, block_powers))
    max_momentary = float(np.max(block_lufs))

    # Absolute Gating (-70 LKFS)
    abs_mask = block_lufs > -70.0
    if not np.any(abs_mask):
        return -70.0, -70.0, -70.0, 0.0

    gated_powers = block_powers[abs_mask]
    gamma_a = -0.691 + 10.0 * math.log10(np.mean(gated_powers))

    # Relative Gating (Gamma_A - 10.0 LU)
    gamma_r = gamma_a - 10.0
    rel_mask = block_lufs > gamma_r
    if np.any(rel_mask):
        integrated_power = np.mean(block_powers[rel_mask])
        integrated_lufs = -0.691 + 10.0 * math.log10(max(1e-12, integrated_power))
    else:
        integrated_lufs = gamma_a

    # Short-term Loudness & Loudness Range (LRA)
    short_hop = int(sample_rate * 0.500)
    num_short = max(1, (total_samples - short_block_len) // short_hop + 1)
    short_lufs_list = []

    for i in range(num_short):
        start = i * short_hop
        chunk = k_channels[:, start:start + short_block_len]
        ms = np.mean(chunk ** 2, axis=1)
        z = np.sum(ms * ch_weights)
        st_lufs = -0.691 + 10.0 * math.log10(max(1e-12, z))
        short_lufs_list.append(st_lufs)

    short_lufs_arr = np.array(short_lufs_list)
    max_short = float(np.max(short_lufs_arr))

    # LRA Gating (Absolute -70 LUFS & Relative Gamma_A - 20 LU)
    lra_mask = (short_lufs_arr > -70.0) & (short_lufs_arr > (integrated_lufs - 20.0))
    if np.sum(lra_mask) >= 2:
        valid_st = short_lufs_arr[lra_mask]
        p10 = float(np.percentile(valid_st, 10))
        p95 = float(np.percentile(valid_st, 95))
        lra = max(0.0, p95 - p10)
    else:
        lra = 0.0

    return integrated_lufs, max_momentary, max_short, lra


def analyze_loudness_war(file_path: str, target_lufs: float = -14.0) -> Dict[str, Any]:
    """
    Forensically measures loudness, dynamic spread, and loudness war compression.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    channels, sample_rate = read_audio_pcm(file_path)
    n_ch, num_samples = channels.shape

    # Calculate Peak & RMS
    peak_sample = float(np.max(np.abs(channels)))
    peak_dbfs = 20.0 * math.log10(max(1e-7, peak_sample))
    rms_linear = float(np.sqrt(np.mean(channels ** 2)))
    rms_dbfs = 20.0 * math.log10(max(1e-7, rms_linear))
    crest_factor_db = peak_dbfs - rms_dbfs

    # Apply K-weighting filter
    k_channels = np.zeros_like(channels)
    for c in range(n_ch):
        k_channels[c] = apply_k_weighting(channels[c], sample_rate)

    integrated_lufs, max_mom, max_short, lra = calculate_gated_loudness(k_channels, sample_rate)

    # Streaming Penalties / Gain adjustments
    spotify_penalty = max(0.0, integrated_lufs - (-14.0))
    apple_penalty = max(0.0, integrated_lufs - (-16.0))
    youtube_penalty = max(0.0, integrated_lufs - (-14.0))
    tidal_penalty = max(0.0, integrated_lufs - (-14.0))

    # Loudness War Compression Score
    # Score 0% = heavily brickwalled (LUFS > -7, LRA < 3, Crest < 7)
    # Score 100% = audiophile classical/jazz (LUFS -16 to -22, LRA > 12, Crest > 15)
    score_lufs = np.clip((-(integrated_lufs + 6.0) / 12.0) * 40.0, 0.0, 40.0)
    score_lra = np.clip((lra / 14.0) * 35.0, 0.0, 35.0)
    score_crest = np.clip(((crest_factor_db - 6.0) / 10.0) * 25.0, 0.0, 25.0)
    dyn_health_pct = min(100.0, max(0.0, score_lufs + score_lra + score_crest))

    if dyn_health_pct >= 80.0:
        health_status = "Audiophile Reference (Wide Dynamic Range & Punch)"
    elif dyn_health_pct >= 55.0:
        health_status = "Modern Commercial Standard (Balanced Dynamics)"
    elif dyn_health_pct >= 30.0:
        health_status = "Loud & Aggressive (Limited Micro-dynamics)"
    else:
        health_status = "Loudness War Casualty (Severely Brickwalled / Flattened)"

    duration_sec = num_samples / float(sample_rate)

    return {
        "file_path": file_path,
        "input_file": os.path.basename(file_path),
        "duration_sec": round(duration_sec, 2),
        "sample_rate": sample_rate,
        "channels": n_ch,
        "integrated_lufs": round(integrated_lufs, 2),
        "max_momentary_lufs": round(max_mom, 2),
        "max_short_term_lufs": round(max_short, 2),
        "loudness_range_lra": round(lra, 2),
        "peak_dbfs": round(peak_dbfs, 2),
        "rms_dbfs": round(rms_dbfs, 2),
        "crest_factor_db": round(crest_factor_db, 2),
        "dynamic_health_pct": round(dyn_health_pct, 1),
        "dynamic_health_desc": health_status,
        "spotify_penalty_db": round(spotify_penalty, 2),
        "apple_penalty_db": round(apple_penalty, 2),
        "youtube_penalty_db": round(youtube_penalty, 2),
        "tidal_penalty_db": round(tidal_penalty, 2),
        "target_lufs": target_lufs,
        "gain_to_target_db": round(target_lufs - integrated_lufs, 2),
    }


def format_loudness_war_card(res: Dict[str, Any]) -> str:
    """Formats ASCII-safe report card for loudness war analysis."""
    lines = []
    lines.append("=" * 65)
    lines.append("  MASTERING LOUDNESS WAR & DYNAMIC SPREAD REPORT")
    lines.append("=" * 65)
    lines.append(f"  Input Track    : {res.get('input_file', '')}")
    lines.append(f"  Duration       : {res.get('duration_sec')}s ({res.get('sample_rate')} Hz, {res.get('channels')} ch)")
    lines.append("-" * 65)
    lines.append(f"  Integrated LUFS: {res.get('integrated_lufs'):>+6.2f} LUFS (EBU R128 BS.1770-4 Gated)")
    lines.append(f"  Short-Term Max : {res.get('max_short_term_lufs'):>+6.2f} LUFS (3s Sliding Window)")
    lines.append(f"  Momentary Max  : {res.get('max_momentary_lufs'):>+6.2f} LUFS (400ms Transient Peak)")
    lines.append(f"  Loudness Range : {res.get('loudness_range_lra'):>6.2f} LU (LRA Dynamic Spread)")
    lines.append(f"  Sample Peak    : {res.get('peak_dbfs'):>+6.2f} dBFS | RMS: {res.get('rms_dbfs'):>+6.2f} dBFS")
    lines.append(f"  Crest Factor   : {res.get('crest_factor_db'):>6.2f} dB (Transient Punch to Body Ratio)")
    lines.append("-" * 65)
    lines.append(f"  Dynamic Health : {res.get('dynamic_health_pct')}% - {res.get('dynamic_health_desc')}")

    # Meter bar
    bar_len = 30
    filled = int(round((res.get('dynamic_health_pct', 0) / 100.0) * bar_len))
    meter = "[" + "#" * filled + "-" * (bar_len - filled) + "]"
    lines.append(f"  Spread Meter   : Crushed {meter} Open")
    lines.append("-" * 65)
    lines.append("  STREAMING NORMALIZATION GAIN PENALTIES:")
    lines.append(f"  * Spotify (-14 LUFS)     : -{res.get('spotify_penalty_db', 0):.2f} dB reduction applied")
    lines.append(f"  * Apple Music (-16 LUFS) : -{res.get('apple_penalty_db', 0):.2f} dB reduction applied")
    lines.append(f"  * YouTube Music (-14 LUFS): -{res.get('youtube_penalty_db', 0):.2f} dB reduction applied")
    lines.append(f"  * Target Adjustment      : {res.get('gain_to_target_db'):>+5.2f} dB to reach {res.get('target_lufs')} LUFS")
    lines.append("=" * 65)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sonance Loudness War & Dynamic Spread Analyzer")
    parser.add_argument("audio_file", help="Path to audio file (WAV/FLAC/MP3)")
    parser.add_argument("--target", type=float, default=-14.0, help="Target LUFS level (default: -14.0)")

    args = parser.parse_args()

    res = analyze_loudness_war(args.audio_file, target_lufs=args.target)
    print(format_loudness_war_card(res))


if __name__ == "__main__":
    main()
