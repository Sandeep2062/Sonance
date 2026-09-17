"""
parametric_eq.py - Audiophile Parametric 5-Band Peaking & Shelving Master EQ Studio
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Implements standard Robert Bristow-Johnson (RBJ) Audio EQ Cookbook biquad filters:
- Low-Shelf, High-Shelf, and parametric Peaking/Bell biquads
- Continuous frequency (20 Hz - 20 kHz), gain (-18 to +18 dB), and Q factor (0.1 - 10.0)
- Cascaded complex frequency response calculation for UI graphing
- High-precision audio filtering to WAV, FLAC, and MP3
"""

import os
import sys
import math
import wave
import struct
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple, Any

try:
    import numpy as np
except ImportError:
    np = None

try:
    from scipy.signal import lfilter
except ImportError:
    lfilter = None


DEFAULT_BANDS = [
    {"type": "lowshelf",  "freq": 80.0,    "gain": 0.0, "q": 0.707, "enabled": True},
    {"type": "peaking",   "freq": 250.0,   "gain": 0.0, "q": 1.0,   "enabled": True},
    {"type": "peaking",   "freq": 1000.0,  "gain": 0.0, "q": 1.0,   "enabled": True},
    {"type": "peaking",   "freq": 4000.0,  "gain": 0.0, "q": 1.0,   "enabled": True},
    {"type": "highshelf", "freq": 12000.0, "gain": 0.0, "q": 0.707, "enabled": True},
]


def calculate_rbj_biquad(
    filter_type: str,
    freq: float,
    gain_db: float,
    q: float,
    sample_rate: int = 44100,
) -> Tuple[float, float, float, float, float]:
    """
    Computes Robert Bristow-Johnson (RBJ) normalized biquad filter coefficients:
    Returns (b0, b1, b2, a1, a2) where a0 is normalized to 1.0.
    """
    omega = 2.0 * math.pi * min(freq, sample_rate * 0.499) / sample_rate
    sin_w = math.sin(omega)
    cos_w = math.cos(omega)
    A = 10.0 ** (gain_db / 40.0)
    alpha = sin_w / (2.0 * max(0.01, q))

    filter_type = filter_type.lower()

    if filter_type == "peaking":
        b0 = 1.0 + alpha * A
        b1 = -2.0 * cos_w
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha / A
    elif filter_type == "lowshelf":
        sqrt_A = math.sqrt(A)
        b0 = A * ((A + 1.0) - (A - 1.0) * cos_w + 2.0 * sqrt_A * alpha)
        b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w)
        b2 = A * ((A + 1.0) - (A - 1.0) * cos_w - 2.0 * sqrt_A * alpha)
        a0 = (A + 1.0) + (A - 1.0) * cos_w + 2.0 * sqrt_A * alpha
        a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w)
        a2 = (A + 1.0) + (A - 1.0) * cos_w - 2.0 * sqrt_A * alpha
    elif filter_type == "highshelf":
        sqrt_A = math.sqrt(A)
        b0 = A * ((A + 1.0) + (A - 1.0) * cos_w + 2.0 * sqrt_A * alpha)
        b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w)
        b2 = A * ((A + 1.0) + (A - 1.0) * cos_w - 2.0 * sqrt_A * alpha)
        a0 = (A + 1.0) - (A - 1.0) * cos_w + 2.0 * sqrt_A * alpha
        a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w)
        a2 = (A + 1.0) - (A - 1.0) * cos_w - 2.0 * sqrt_A * alpha
    elif filter_type == "highpass":
        b0 = (1.0 + cos_w) / 2.0
        b1 = -(1.0 + cos_w)
        b2 = (1.0 + cos_w) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha
    elif filter_type == "lowpass":
        b0 = (1.0 - cos_w) / 2.0
        b1 = 1.0 - cos_w
        b2 = (1.0 - cos_w) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha
    else:
        # Default bypass / flat
        return 1.0, 0.0, 0.0, 0.0, 0.0

    # Normalize by a0
    inv_a0 = 1.0 / a0
    return (b0 * inv_a0, b1 * inv_a0, b2 * inv_a0, a1 * inv_a0, a2 * inv_a0)


def calculate_complex_response(
    bands: List[Dict[str, Any]],
    num_points: int = 200,
    sample_rate: int = 44100,
) -> Dict[str, Any]:
    """
    Computes the composite logarithmic frequency response curve H(f) across 20 Hz to 20 kHz.
    Returns: {"frequencies": [...], "magnitude_db": [...], "bands": [...]}
    """
    freqs = [20.0 * (1000.0 ** (i / (num_points - 1))) for i in range(num_points)]
    total_db = [0.0] * num_points

    for band in bands:
        if not band.get("enabled", True) or abs(band.get("gain", 0.0)) < 0.01:
            continue

        b0, b1, b2, a1, a2 = calculate_rbj_biquad(
            band.get("type", "peaking"),
            band.get("freq", 1000.0),
            band.get("gain", 0.0),
            band.get("q", 1.0),
            sample_rate=sample_rate,
        )

        for i, f in enumerate(freqs):
            w = 2.0 * math.pi * f / sample_rate
            # z^-1 = cos(w) - j sin(w)
            cos_w = math.cos(w)
            sin_w = math.sin(w)
            cos_2w = math.cos(2.0 * w)
            sin_2w = math.sin(2.0 * w)

            # Numerator = b0 + b1 z^-1 + b2 z^-2
            num_re = b0 + b1 * cos_w + b2 * cos_2w
            num_im = -b1 * sin_w - b2 * sin_2w

            # Denominator = 1 + a1 z^-1 + a2 z^-2
            den_re = 1.0 + a1 * cos_w + a2 * cos_2w
            den_im = -a1 * sin_w - a2 * sin_2w

            num_mag_sq = num_re * num_re + num_im * num_im
            den_mag_sq = den_re * den_re + den_im * den_im
            mag_sq = max(1e-12, num_mag_sq / max(1e-12, den_mag_sq))
            db = 10.0 * math.log10(mag_sq)
            total_db[i] += db

    return {
        "frequencies": [round(f, 1) for f in freqs],
        "magnitude_db": [round(m, 2) for m in total_db],
        "bands": bands,
    }


def apply_biquad_filtering(
    signal: Any,
    bands: List[Dict[str, Any]],
    sample_rate: int = 44100,
) -> Any:
    """
    Applies the cascaded parametric 5-band filter chain to audio samples.
    """
    if np is None:
        raise ImportError("NumPy is required.")

    out = np.copy(signal)

    for band in bands:
        if not band.get("enabled", True) or abs(band.get("gain", 0.0)) < 0.01:
            continue

        b0, b1, b2, a1, a2 = calculate_rbj_biquad(
            band.get("type", "peaking"),
            band.get("freq", 1000.0),
            band.get("gain", 0.0),
            band.get("q", 1.0),
            sample_rate=sample_rate,
        )

        b = [b0, b1, b2]
        a = [1.0, a1, a2]

        if lfilter is not None:
            # High-speed SciPy implementation
            for ch in range(out.shape[1]):
                out[:, ch] = lfilter(b, a, out[:, ch])
        else:
            # Pure NumPy direct form II transposed difference equation
            for ch in range(out.shape[1]):
                x = out[:, ch]
                y = np.zeros_like(x)
                d1 = 0.0
                d2 = 0.0
                for n in range(len(x)):
                    xn = x[n]
                    yn = b0 * xn + d1
                    d1 = b1 * xn - a1 * yn + d2
                    d2 = b2 * xn - a2 * yn
                    y[n] = yn
                out[:, ch] = y

    # Peak normalization protection to prevent clipping
    peak = np.max(np.abs(out))
    if peak > 0.98:
        out = out * (0.95 / peak)

    return out


def decode_audio(file_path: str) -> Tuple[Any, int]:
    """Decodes audio to float32 NumPy array [-1.0, 1.0]."""
    if np is None:
        raise ImportError("NumPy is required.")

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".wav":
        try:
            with wave.open(file_path, "rb") as wf:
                sr = wf.getframerate()
                ch = wf.getnchannels()
                sw = wf.getsampwidth()
                raw = wf.readframes(wf.getnframes())
                if sw == 2:
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                elif sw == 4:
                    data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
                else:
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if ch == 1:
                    data = np.column_stack([data, data])
                else:
                    data = data.reshape(-1, ch)[:, :2]
                return data, sr
        except Exception:
            pass

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        cmd = [
            ffmpeg, "-v", "error", "-i", file_path,
            "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "2", "-ar", "44100", "-"
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = proc.communicate(timeout=60)
            if proc.returncode == 0 and len(out) > 0:
                raw_data = np.frombuffer(out, dtype=np.int16).astype(np.float32) / 32768.0
                return raw_data.reshape(-1, 2), 44100
        except Exception:
            pass

    raise RuntimeError(f"Could not decode audio: {file_path}")


def render_parametric_eq(
    input_path: str,
    output_path: Optional[str] = None,
    bands: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Renders an audio file processed through the 5-band parametric equalizer.
    """
    if not os.path.exists(input_path):
        return {"error": f"File not found: {input_path}", "success": False}

    if bands is None:
        bands = DEFAULT_BANDS

    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_eq{ext}"

    signal, sr = decode_audio(input_path)
    duration = signal.shape[0] / sr

    filtered = apply_biquad_filtering(signal, bands, sample_rate=sr)

    ext = os.path.splitext(output_path)[1].lower()
    target_wav = output_path if ext == ".wav" else output_path + ".tmp.wav"

    int16_data = (np.clip(filtered, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(target_wav, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16_data.tobytes())

    if ext != ".wav":
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            cmd = [ffmpeg, "-y", "-v", "error", "-i", target_wav, output_path]
            subprocess.run(cmd, check=True)
            if os.path.exists(target_wav):
                os.remove(target_wav)
        else:
            output_path = target_wav

    return {
        "success": True,
        "input_file": os.path.basename(input_path),
        "output_file": os.path.basename(output_path),
        "path": output_path,
        "duration_sec": round(duration, 2),
        "sample_rate": sr,
        "bands_applied": len(bands),
    }


def format_parametric_card(res: Dict[str, Any], bands: List[Dict[str, Any]]) -> str:
    """Renders ASCII card for Parametric EQ."""
    if not res.get("success"):
        return f"[!] Error: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append(f"| AUDIOPHILE PARAMETRIC 5-BAND MASTER EQUALIZER STUDIO           |")
    lines.append(sep)
    lines.append(f"| Input File     : {res['input_file'][:47]:<47} |")
    lines.append(f"| Output File    : {res['output_file'][:47]:<47} |")
    lines.append(f"| Duration       : {res['duration_sec']}s  |  Sample Rate: {res['sample_rate']} Hz          |")
    lines.append(sep)
    lines.append(f"| Band | Filter Type | Frequency  | Gain (dB)  | Q Factor | Active |")
    lines.append(f"|------+-------------+------------+------------+----------+--------|")
    for i, b in enumerate(bands, start=1):
        t_str = b.get('type', 'peaking')[:11].capitalize()
        f_str = f"{b.get('freq', 1000):.1f} Hz"
        g_str = f"{b.get('gain', 0):+.1f} dB"
        q_str = f"{b.get('q', 1.0):.2f}"
        act = "YES" if b.get('enabled', True) else "NO"
        lines.append(f"|  #{i}  | {t_str:<11} | {f_str:>10} | {g_str:>10} | {q_str:>8} | {act:^6} |")
    lines.append(sep)
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parametric_eq.py <input_audio> [output_audio]")
        sys.exit(1)

    in_f = sys.argv[1]
    out_f = sys.argv[2] if len(sys.argv) > 2 else None
    res = render_parametric_eq(in_f, output_path=out_f, bands=DEFAULT_BANDS)
    print(format_parametric_card(res, DEFAULT_BANDS))
