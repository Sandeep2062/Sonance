"""
midside_processor.py - M/S (Mid-Side) Spatial Width & Elliptical Bass Monomaker Studio
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Audiophile Mid/Side matrix processor for mastering and mixing:
- Mid/Side matrix decomposition: M = (L+R)/sqrt(2), S = (L-R)/sqrt(2)
- Continuously variable stereo width scaling (0% mono to 200% hyper-wide panorama)
- Elliptical Low-End Monomaker: High-passes Side channel (60-300 Hz) to eliminate sub-bass phase cancellation
- High-Frequency Side Air Exciter (>10 kHz) to widen acoustic ambience without shifting lead vocals
- Phase correlation & stereo balance monitoring
"""

import os
import sys
import math
import wave
import argparse
from typing import Dict, List, Optional, Tuple, Any

import numpy as np


def read_audio_stereo(file_path: str) -> Tuple[np.ndarray, int]:
    """Reads audio file into float32 array with shape (2, samples)."""
    try:
        import soundfile as sf
        data, sr = sf.read(file_path, dtype="float32")
        if data.ndim > 1:
            return data.T[:2], sr
        return np.vstack([data, data]), sr
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

        if n_ch >= 2:
            data = data.reshape(-1, n_ch).T[:2]
        else:
            data = np.vstack([data, data])
        return data, sr

    raise ValueError(f"Unsupported audio format: {file_path}")


def write_stereo_wav(output_path: str, left: np.ndarray, right: np.ndarray, sample_rate: int):
    """Writes stereo float32 channels into 24-bit PCM WAV."""
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    num_samples = min(len(left), len(right))
    l_int = np.clip(left[:num_samples] * 8388607.0, -8388608.0, 8388607.0).astype(np.int32)
    r_int = np.clip(right[:num_samples] * 8388607.0, -8388608.0, 8388607.0).astype(np.int32)

    interleaved = np.empty((num_samples * 2,), dtype=np.int32)
    interleaved[0::2] = l_int
    interleaved[1::2] = r_int

    raw_bytes = bytearray(num_samples * 2 * 3)
    idx = 0
    for val in interleaved:
        uval = val if val >= 0 else (val + 16777216)
        raw_bytes[idx] = uval & 0xFF
        raw_bytes[idx + 1] = (uval >> 8) & 0xFF
        raw_bytes[idx + 2] = (uval >> 16) & 0xFF
        idx += 3

    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(raw_bytes))


def biquad_highpass(cutoff_hz: float, sample_rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """2nd-order Butterworth high-pass filter biquad coefficients."""
    w0 = 2.0 * math.pi * cutoff_hz / float(sample_rate)
    alpha = math.sin(w0) / (2.0 * math.sqrt(2.0))

    b0 = (1.0 + math.cos(w0)) / 2.0
    b1 = -(1.0 + math.cos(w0))
    b2 = (1.0 + math.cos(w0)) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * math.cos(w0)
    a2 = 1.0 - alpha

    b = np.array([b0, b1, b2], dtype=np.float64) / a0
    a = np.array([a0, a1, a2], dtype=np.float64) / a0
    return b, a


def biquad_highshelf(cutoff_hz: float, gain_db: float, sample_rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """2nd-order High-Shelf filter biquad coefficients."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * cutoff_hz / float(sample_rate)
    alpha = math.sin(w0) / (2.0 * math.sqrt(2.0))

    b0 = A * ((A + 1.0) + (A - 1.0) * math.cos(w0) + 2.0 * math.sqrt(A) * alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * math.cos(w0))
    b2 = A * ((A + 1.0) + (A - 1.0) * math.cos(w0) - 2.0 * math.sqrt(A) * alpha)
    a0 = (A + 1.0) - (A - 1.0) * math.cos(w0) + 2.0 * math.sqrt(A) * alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * math.cos(w0))
    a2 = (A + 1.0) - (A - 1.0) * math.cos(w0) - 2.0 * math.sqrt(A) * alpha

    b = np.array([b0, b1, b2], dtype=np.float64) / a0
    a = np.array([a0, a1, a2], dtype=np.float64) / a0
    return b, a


def apply_filter_1d(signal: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Applies biquad IIR filter to 1D signal."""
    out = np.zeros_like(signal, dtype=np.float32)
    d1, d2 = 0.0, 0.0
    b0, b1, b2 = b[0], b[1], b[2]
    a1, a2 = a[1], a[2]

    for i in range(len(signal)):
        x = float(signal[i])
        y = b0 * x + d1
        d1 = b1 * x - a1 * y + d2
        d2 = b2 * x - a2 * y
        out[i] = y
    return out


def process_midside_audio(
    input_path: str,
    output_path: Optional[str] = None,
    width_percent: float = 125.0,
    monomaker_hz: float = 120.0,
    mid_gain_db: float = 0.0,
    side_gain_db: float = 0.0,
    side_air_db: float = 1.5
) -> Dict[str, Any]:
    """
    Processes stereo audio track in the Mid/Side domain with bass monomaker and air excitation.
    
    Args:
        input_path: Source audio file.
        output_path: Target output WAV path.
        width_percent: Stereo width scaling (0% = mono, 100% = normal, 200% = wide).
        monomaker_hz: Crossover frequency below which Side is high-passed (e.g. 120 Hz).
        mid_gain_db: Additional gain for Mid channel in dB.
        side_gain_db: Additional gain for Side channel in dB.
        side_air_db: High-shelf air boost on Side channel (>10 kHz) in dB.
    """
    if not os.path.isfile(input_path):
        return {"success": False, "error": f"Audio file not found: {input_path}"}

    try:
        channels, sr = read_audio_stereo(input_path)
    except Exception as e:
        return {"success": False, "error": f"Failed to read audio: {e}"}

    left = channels[0]
    right = channels[1]

    # Pre-processing correlation
    norm_l = float(np.linalg.norm(left))
    norm_r = float(np.linalg.norm(right))
    corr_in = float(np.dot(left, right)) / (norm_l * norm_r) if (norm_l * norm_r) > 0 else 1.0

    # 1. Mid/Side Matrix Decomposition (orthogonal sqrt(2) scaling)
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    mid = (left + right) * inv_sqrt2
    side = (left - right) * inv_sqrt2

    # 2. Elliptical Low-End Monomaker on Side Channel
    if monomaker_hz > 10.0:
        safe_cutoff = min(float(monomaker_hz), sr * 0.40)
        b_hp, a_hp = biquad_highpass(safe_cutoff, sample_rate=sr)
        side = apply_filter_1d(side, b_hp, a_hp)

    # 3. High-Frequency Side Air Exciter
    if abs(side_air_db) > 0.05:
        b_hs, a_hs = biquad_highshelf(10000.0, side_air_db, sample_rate=sr)
        side = apply_filter_1d(side, b_hs, a_hs)

    # 4. Width Scaling & Individual Gains
    mid_factor = 10.0 ** (mid_gain_db / 20.0)
    side_factor = (width_percent / 100.0) * (10.0 ** (side_gain_db / 20.0))

    mid = mid * mid_factor
    side = side * side_factor

    # 5. Reconstitute Stereo (L', R')
    out_left = (mid + side) * inv_sqrt2
    out_right = (mid - side) * inv_sqrt2

    # Post-processing correlation & peak
    norm_ol = float(np.linalg.norm(out_left))
    norm_or = float(np.linalg.norm(out_right))
    corr_out = float(np.dot(out_left, out_right)) / (norm_ol * norm_or) if (norm_ol * norm_or) > 0 else 1.0

    # Prevent digital clipping with smooth normalization if needed
    peak = max(float(np.max(np.abs(out_left))), float(np.max(np.abs(out_right))))
    if peak > 0.99:
        gain_shift = 0.98 / peak
        out_left *= gain_shift
        out_right *= gain_shift
        peak = 0.98

    peak_dbfs = round(20.0 * math.log10(max(1e-6, peak)), 2)

    # Energy ratio (Side vs Mid in dB)
    energy_m = float(np.sum(mid ** 2))
    energy_s = float(np.sum(side ** 2))
    side_to_mid_db = round(10.0 * math.log10(max(1e-9, energy_s) / max(1e-9, energy_m)), 2)

    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_MidSide_W{int(width_percent)}%.wav"

    write_stereo_wav(output_path, out_left, out_right, sample_rate=sr)

    return {
        "success": True,
        "input_file": os.path.basename(input_path),
        "output_path": output_path,
        "sample_rate": sr,
        "width_percent": width_percent,
        "monomaker_hz": monomaker_hz,
        "mid_gain_db": mid_gain_db,
        "side_gain_db": side_gain_db,
        "side_air_db": side_air_db,
        "side_to_mid_db": side_to_mid_db,
        "corr_in": round(corr_in, 4),
        "corr_out": round(corr_out, 4),
        "peak_dbfs": peak_dbfs
    }


# Convenience alias
process_midside = process_midside_audio


def format_midside_card(res: Dict[str, Any]) -> str:
    """Renders formatted ASCII Mid/Side processor report card."""
    if not res.get("success"):
        return f"[!] Error processing Mid/Side: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append("| M/S (MID-SIDE) SPATIAL WIDTH & BASS MONOMAKER STUDIO            |")
    lines.append(sep)
    lines.append(f"| Input Track    : {res['input_file'][:48]:<48} |")
    lines.append(f"| Stereo Width   : {res['width_percent']:>5.1f}% (Natural: 100%, Mono: 0%, Immersive: >130%) |")
    lines.append(f"| Bass Monomaker : High-passed Side at {res['monomaker_hz']:>5.1f} Hz (Solid Subwoofer Focus)   |")
    lines.append(f"| Side Air Boost : {res['side_air_db']:>+5.1f} dB High-Shelf at >10 kHz (Panoramic Sparkle)     |")
    lines.append(sep)
    lines.append(f"| Phase Coherence: r = {res['corr_in']:>+6.4f} -> r = {res['corr_out']:>+6.4f} (Side/Mid: {res['side_to_mid_db']:>+5.1f} dB)    |")
    lines.append(f"| Output Ceiling : Peak: {res['peak_dbfs']:>+5.1f} dBFS | 24-bit Stereo Master Export         |")
    lines.append(sep)

    # ASCII Width visualization
    w_factor = min(200.0, max(0.0, res['width_percent']))
    bar_pos = int((w_factor / 200.0) * 30.0)
    bar = ["-"] * 31
    bar[min(30, bar_pos)] = "|"
    bar_str = "".join(bar)
    lines.append(f"| Width Meter    : Mono [0%]{bar_str}[200%] Wide |")
    lines.append(sep)
    lines.append(f"| Mastered Audio : {res['output_path'][:48]:<48} |")
    lines.append(sep)

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sonance Mid-Side Spatial Width & Monomaker Studio")
    parser.add_argument("input", help="Path to stereo audio file")
    parser.add_argument("output", nargs="?", default=None, help="Target output WAV path")
    parser.add_argument("--width", type=float, default=125.0, help="Stereo width percentage (default 125.0)")
    parser.add_argument("--monomaker-hz", type=float, default=120.0, help="Bass monomaker cutoff in Hz (default 120.0)")
    parser.add_argument("--mid-gain", type=float, default=0.0, help="Mid gain in dB (default 0.0)")
    parser.add_argument("--side-gain", type=float, default=0.0, help="Side gain in dB (default 0.0)")
    parser.add_argument("--side-air", type=float, default=1.5, help="Side high shelf air in dB (default 1.5)")

    args = parser.parse_args()

    result = process_midside_audio(
        input_path=args.input,
        output_path=args.output,
        width_percent=args.width,
        monomaker_hz=args.monomaker_hz,
        mid_gain_db=args.mid_gain,
        side_gain_db=args.side_gain,
        side_air_db=args.side_air
    )
    print(format_midside_card(result))
