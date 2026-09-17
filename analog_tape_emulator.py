"""
analog_tape_emulator.py - Audiophile Dynamic Tape Saturation & Analog Tube Warmth Studio
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Audiophile magnetic tape saturation and analog tube character processor:
- Soft-knee hyperbolic tangent tape transfer curve: y = tanh(x * drive) / tanh(drive)
- Asymmetrical 2nd-order harmonic tube warmth (triode bias) & 3rd-order tape compression
- Multi-speed tape head modeling: 30 ips (mastering clarity), 15 ips (classic warm punch), 7.5 ips (vintage coloration)
- Low-frequency tape head-bump resonance filter (50-100 Hz low shelf boost)
- Subtle high-frequency tape flux compression & high-cut damping
- Optional ultra-low analog tape noise floor (-75 dBFS to -95 dBFS)
- 24-bit PCM WAV master export with zero clipping
"""

import os
import sys
import math
import wave
import struct
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

    interleaved = np.empty(num_samples * 2, dtype=np.int32)
    interleaved[0::2] = l_int
    interleaved[1::2] = r_int

    raw_24 = bytearray(num_samples * 6)
    u_vals = interleaved.view(np.uint32)
    b0 = (u_vals & 0xFF).astype(np.uint8)
    b1 = ((u_vals >> 8) & 0xFF).astype(np.uint8)
    b2 = ((u_vals >> 16) & 0xFF).astype(np.uint8)
    raw_24[0::3] = b0.tobytes()
    raw_24[1::3] = b1.tobytes()
    raw_24[2::3] = b2.tobytes()

    fmt_chunk = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 2, sample_rate, sample_rate * 6, 6, 24)
    data_chunk = b"data" + struct.pack("<I", len(raw_24)) + bytes(raw_24)
    riff_header = b"RIFF" + struct.pack("<I", 4 + len(fmt_chunk) + len(data_chunk)) + b"WAVE"

    with open(output_path, "wb") as f:
        f.write(riff_header)
        f.write(fmt_chunk)
        f.write(data_chunk)


def apply_biquad_lowshelf(signal: np.ndarray, sample_rate: int, freq_hz: float, gain_db: float) -> np.ndarray:
    """Applies a 2nd-order low-shelf filter for tape head-bump bass resonance."""
    if abs(gain_db) < 0.05:
        return signal

    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq_hz / sample_rate
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / 2.0 * math.sqrt(2.0)
    two_sqrt_A_alpha = 2.0 * math.sqrt(A) * alpha

    b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + two_sqrt_A_alpha)
    b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - two_sqrt_A_alpha)
    a0 = (A + 1.0) + (A - 1.0) * cos_w0 + two_sqrt_A_alpha
    a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
    a2 = (A + 1.0) + (A - 1.0) * cos_w0 - two_sqrt_A_alpha

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)

    out = np.zeros_like(signal, dtype=np.float64)
    x = signal.astype(np.float64)
    x1 = x2 = y1 = y2 = 0.0

    for i in range(len(signal)):
        xi = x[i]
        yi = b[0] * xi + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        out[i] = yi
        x2 = x1
        x1 = xi
        y2 = y1
        y1 = yi

    return out.astype(np.float32)


def apply_biquad_highshelf(signal: np.ndarray, sample_rate: int, freq_hz: float, gain_db: float) -> np.ndarray:
    """Applies a 2nd-order high-shelf filter for tape high-frequency flux rolloff."""
    if abs(gain_db) < 0.05:
        return signal

    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * min(freq_hz, sample_rate * 0.45) / sample_rate
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

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)

    out = np.zeros_like(signal, dtype=np.float64)
    x = signal.astype(np.float64)
    x1 = x2 = y1 = y2 = 0.0

    for i in range(len(signal)):
        xi = x[i]
        yi = b[0] * xi + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        out[i] = yi
        x2 = x1
        x1 = xi
        y2 = y1
        y1 = yi

    return out.astype(np.float32)


def process_tape_channel(
    channel: np.ndarray,
    sample_rate: int,
    drive: float,
    warmth: float,
    bias: float,
    head_bump_freq: float,
    head_bump_db: float,
    hf_cutoff_hz: float,
    hf_damping_db: float,
    add_hiss: bool,
    hiss_db: float
) -> np.ndarray:
    """Processes a single mono channel through the tape & tube saturation engine."""
    # Step 1: Pre-saturation Head Bump (Low-End Resonance)
    sig = apply_biquad_lowshelf(channel, sample_rate, head_bump_freq, head_bump_db)

    # Step 2: Asymmetrical Tube Bias (2nd harmonic generation)
    # y_bias = x + bias * 0.15 * (x^2 - E[x^2])
    if abs(bias) > 0.01:
        x_sq = sig * np.abs(sig)
        sig = sig + (bias * 0.12 * x_sq)

    # Step 3: Nonlinear Tape Soft-Knee Saturation (3rd harmonic & compression)
    # y = tanh(drive * x) / tanh(drive)
    effective_drive = max(1.0, drive)
    norm_factor = math.tanh(effective_drive)
    sig = np.tanh(sig * effective_drive) / norm_factor

    # Step 4: Post-saturation High-Frequency Flux Rolloff
    sig = apply_biquad_highshelf(sig, sample_rate, hf_cutoff_hz, hf_damping_db)

    # Step 5: Optional Analog Tape Hiss (Pink-filtered noise)
    if add_hiss:
        hiss_amp = 10.0 ** (hiss_db / 20.0)
        noise = np.random.normal(0.0, 1.0, len(sig)).astype(np.float32)
        # Gentle 1st order lowpass on hiss to shape like magnetic tape pink noise
        noise_filtered = np.zeros_like(noise)
        alpha_n = 0.35
        for i in range(1, len(noise)):
            noise_filtered[i] = alpha_n * noise[i] + (1.0 - alpha_n) * noise_filtered[i - 1]
        sig = sig + (noise_filtered * hiss_amp)

    return sig


def process_analog_tape(
    input_path: str,
    output_path: Optional[str] = None,
    drive: float = 2.5,
    tape_speed_ips: float = 15.0,
    warmth: float = 2.0,
    tube_bias: float = 0.5,
    add_hiss: bool = False,
    hiss_db: float = -80.0
) -> Dict[str, Any]:
    """
    Simulates analog tape saturation, tube warmth, and head-bump frequency response.
    
    Args:
        input_path: Input audio file (WAV, FLAC, etc.)
        output_path: Target 24-bit PCM WAV master.
        drive: Saturation drive multiplier (1.0 = transparent, 2.5 = classic tape, 6.0+ = heavy fuzz).
        tape_speed_ips: Tape speed (30.0 = mastering studio, 15.0 = warm punch, 7.5 = vintage color).
        warmth: Analog low-mid presence scale (0.0 to 5.0).
        tube_bias: Asymmetrical 2nd harmonic tube warmth ratio (0.0 to 2.0).
        add_hiss: Whether to include subtle magnetic tape noise floor.
        hiss_db: Noise floor level in dBFS (default -80 dBFS).
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input audio file not found: {input_path}")

    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_tape.wav"

    channels, sr = read_audio_stereo(input_path)
    left, right = channels[0], channels[1]

    # Speed profiling parameters
    if tape_speed_ips >= 25.0:
        # 30 ips: Ultra-wide linear response, head bump at 45 Hz (+0.8 dB), smooth HF
        bump_freq = 45.0
        bump_db = 0.8 * (warmth / 2.0)
        hf_cut = 18500.0
        hf_damp = -0.5
        speed_desc = "30 ips (Mastering Clarity & High Headroom)"
    elif tape_speed_ips >= 12.0:
        # 15 ips: Classic punchy low end at 65 Hz (+2.0 dB), sweet analog rolloff at 16 kHz (-1.8 dB)
        bump_freq = 65.0
        bump_db = 2.0 * (warmth / 2.0)
        hf_cut = 16000.0
        hf_damp = -1.8
        speed_desc = "15 ips (Classic Studio Warmth & Solid Punch)"
    else:
        # 7.5 ips: Heavy vintage color, head bump at 95 Hz (+3.5 dB), rolloff at 12 kHz (-4.0 dB)
        bump_freq = 95.0
        bump_db = 3.5 * (warmth / 2.0)
        hf_cut = 12500.0
        hf_damp = -4.0
        speed_desc = "7.5 ips (Vintage Lo-Fi Coloration & Thick Midrange)"

    out_l = process_tape_channel(
        left, sr, drive, warmth, tube_bias, bump_freq, bump_db, hf_cut, hf_damp, add_hiss, hiss_db
    )
    out_r = process_tape_channel(
        right, sr, drive, warmth, tube_bias, bump_freq, bump_db, hf_cut, hf_damp, add_hiss, hiss_db
    )

    # Normalize ceiling to avoid digital overs
    peak = max(np.max(np.abs(out_l)), np.max(np.abs(out_r)))
    if peak > 0.99:
        scale = 0.98 / peak
        out_l *= scale
        out_r *= scale
        peak_dbfs = -0.18
    else:
        peak_dbfs = 20.0 * math.log10(max(1e-7, float(peak)))

    write_stereo_wav(output_path, out_l, out_r, sample_rate=sr)

    # Calculate estimated Total Harmonic Distortion (THD)
    thd_pct = min(12.5, round((drive - 1.0) * 1.8 + tube_bias * 0.75 + 0.15, 2))

    return {
        "success": True,
        "input_file": os.path.basename(input_path),
        "output_path": output_path,
        "sample_rate": sr,
        "tape_speed": f"{tape_speed_ips} ips",
        "speed_profile": speed_desc,
        "drive": round(drive, 2),
        "warmth": round(warmth, 2),
        "tube_bias": round(tube_bias, 2),
        "head_bump": f"{bump_freq:.1f} Hz ({bump_db:+.1f} dB)",
        "hf_damping": f"{hf_cut:.0f} Hz ({hf_damp:+.1f} dB)",
        "tape_hiss": f"{hiss_db} dBFS" if add_hiss else "Disabled",
        "estimated_thd": f"{thd_pct}%",
        "peak_dbfs": round(peak_dbfs, 2),
    }


def format_tape_card(res: Dict[str, Any]) -> str:
    """Formats an ASCII-safe report card for tape saturation."""
    lines = []
    lines.append("=" * 65)
    lines.append("  ANALOG TAPE SATURATION & TUBE WARMTH STUDIO")
    lines.append("=" * 65)
    lines.append(f"  Input Track    : {res.get('input_file', '')}")
    lines.append(f"  Tape Speed     : {res.get('tape_speed')} - {res.get('speed_profile')}")
    lines.append(f"  Drive Level    : {res.get('drive')}x (Soft-Knee Tanh Saturation)")
    lines.append(f"  Tube Bias      : {res.get('tube_bias')} (2nd-Order Even Harmonics)")
    lines.append(f"  Head Bump      : {res.get('head_bump')}")
    lines.append(f"  High Damping   : {res.get('hf_damping')}")
    lines.append(f"  Estimated THD  : {res.get('estimated_thd')} total harmonic coloration")
    lines.append(f"  Tape Hiss      : {res.get('tape_hiss')}")
    lines.append(f"  Master Peak    : {res.get('peak_dbfs')} dBFS (24-bit Stereo Master)")
    lines.append(f"  Output File    : {os.path.basename(res.get('output_path', ''))}")
    lines.append("=" * 65)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sonance Analog Tape Saturation Studio")
    parser.add_argument("input_file", help="Path to audio file (WAV/FLAC)")
    parser.add_argument("output_file", nargs="?", help="Output 24-bit WAV file")
    parser.add_argument("--drive", type=float, default=2.5, help="Saturation drive multiplier (default: 2.5)")
    parser.add_argument("--speed", type=float, default=15.0, choices=[7.5, 15.0, 30.0], help="Tape speed in ips (default: 15.0)")
    parser.add_argument("--warmth", type=float, default=2.0, help="Low-mid presence scale 0-5 (default: 2.0)")
    parser.add_argument("--bias", type=float, default=0.5, help="Tube 2nd harmonic bias 0-2 (default: 0.5)")
    parser.add_argument("--hiss", action="store_true", help="Add subtle analog tape noise floor")
    parser.add_argument("--hiss-db", type=float, default=-80.0, help="Hiss amplitude in dBFS (default: -80)")

    args = parser.parse_args()

    res = process_analog_tape(
        args.input_file,
        output_path=args.output_file,
        drive=args.drive,
        tape_speed_ips=args.speed,
        warmth=args.warmth,
        tube_bias=args.bias,
        add_hiss=args.hiss,
        hiss_db=args.hiss_db,
    )
    print(format_tape_card(res))


if __name__ == "__main__":
    main()
