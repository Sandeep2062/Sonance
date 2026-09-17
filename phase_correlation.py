"""
phase_correlation.py - Audio Phase Correlation & Stereo Goniometer Studio
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Calculates stereo phase correlation coefficient (-1.0 to +1.0), stereo width,
balance tilt (dB), mono-compatibility collapse attenuation, downsampled
Lissajous vector scope coordinates, and provides 1-click phase correction.
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


def analyze_phase_correlation(file_path: str, max_points: int = 500) -> Dict[str, Any]:
    """
    Computes phase correlation coefficient, L/R balance, stereo width,
    mono collapse loss, and downsampled Lissajous vector scope points.
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "success": False}

    signal, sr = decode_audio(file_path)
    l = signal[:, 0]
    r = signal[:, 1]

    # Calculate Pearson phase correlation: sum(L*R) / sqrt(sum(L^2) * sum(R^2))
    sum_lr = float(np.sum(l * r))
    sum_l2 = float(np.sum(l ** 2))
    sum_r2 = float(np.sum(r ** 2))
    denom = math.sqrt(max(1e-12, sum_l2 * sum_r2))

    correlation = round(max(-1.0, min(1.0, sum_lr / denom)), 3)

    # RMS Levels & Balance Tilt (dB)
    rms_l = math.sqrt(max(1e-12, sum_l2 / len(l)))
    rms_r = math.sqrt(max(1e-12, sum_r2 / len(r)))
    balance_db = round(20.0 * math.log10(max(1e-6, rms_l / max(1e-6, rms_r))), 2)

    # Mid / Side energy ratio
    mid = 0.5 * (l + r)
    side = 0.5 * (l - r)
    rms_mid = math.sqrt(max(1e-12, float(np.mean(mid ** 2))))
    rms_side = math.sqrt(max(1e-12, float(np.mean(side ** 2))))
    width_pct = round((rms_side / max(1e-6, rms_mid)) * 100.0, 1)

    # Mono collapse loss (dB): energy of (L+R) vs (L^2 + R^2)
    sum_mono2 = float(np.sum((l + r) ** 2))
    sum_total2 = 2.0 * (sum_l2 + sum_r2)
    mono_loss_db = round(10.0 * math.log10(max(1e-9, sum_mono2 / max(1e-9, sum_total2))), 2)

    # Diagnosis classification
    if correlation > 0.85:
        diag = "Narrow Stereo / Strong Mono Alignment"
        status = "EXCELLENT"
    elif correlation > 0.40:
        diag = "Balanced Wide Stereo (Natural Mix)"
        status = "OPTIMAL"
    elif correlation >= 0.0:
        diag = "Very Wide Stereo (Moderate Mono Loss)"
        status = "ACCEPTABLE"
    elif correlation > -0.40:
        diag = "Phase Cancellation Detected (Vocal/Bass Loss on Mono)"
        status = "WARNING"
    else:
        diag = "Severe Anti-Phase / Channel Inversion Detected"
        status = "CRITICAL"

    # Downsample points for Lissajous Goniometer: (S, M) rotated 45 deg
    step = max(1, len(l) // max_points)
    sampled_l = l[::step][:max_points]
    sampled_r = r[::step][:max_points]

    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    goniometer_x = (sampled_r - sampled_l) * inv_sqrt2
    goniometer_y = (sampled_r + sampled_l) * inv_sqrt2

    goniometer_points = [
        {"x": round(float(gx), 3), "y": round(float(gy), 3)}
        for gx, gy in zip(goniometer_x, goniometer_y)
    ]

    duration = len(l) / sr

    return {
        "success": True,
        "file": os.path.basename(file_path),
        "path": file_path,
        "duration_sec": round(duration, 2),
        "correlation": correlation,
        "balance_db": balance_db,
        "stereo_width_pct": width_pct,
        "mono_loss_db": mono_loss_db,
        "diagnosis": diag,
        "status": status,
        "goniometer_points": goniometer_points,
    }


def correct_stereo_phase(
    input_path: str,
    output_path: Optional[str] = None,
    invert_right_channel: bool = True,
    mono_bass: bool = True,
    mono_cutoff_hz: float = 120.0,
) -> Dict[str, Any]:
    """
    Applies phase correction:
    1. Channel phase inversion (fixes 180 deg polarity inversion)
    2. Elliptical EQ (mono-sums bass below cutoff to preserve low-end punch)
    """
    if not os.path.exists(input_path):
        return {"error": f"File not found: {input_path}", "success": False}

    signal, sr = decode_audio(input_path)
    l = np.copy(signal[:, 0])
    r = np.copy(signal[:, 1])

    if invert_right_channel:
        r = -r

    if mono_bass:
        # Elliptical EQ: Low-pass filter side channel, and subtract it
        # Side channel = 0.5 * (L - R)
        side = 0.5 * (l - r)
        # Apply 1st order high-pass to Side channel (rolling off low frequencies in side)
        fc = mono_cutoff_hz
        rc = 1.0 / (2.0 * math.pi * fc)
        dt = 1.0 / sr
        alpha = rc / (rc + dt)

        side_hp = np.zeros_like(side)
        for i in range(1, len(side)):
            side_hp[i] = alpha * (side_hp[i-1] + side[i] - side[i-1])

        mid = 0.5 * (l + r)
        l = mid + side_hp
        r = mid - side_hp

    # Normalize to prevent digital overs
    out_signal = np.column_stack([l, r])
    peak = np.max(np.abs(out_signal))
    if peak > 0.98:
        out_signal = out_signal * (0.95 / peak)

    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_phase_corrected{ext}"

    ext = os.path.splitext(output_path)[1].lower()
    target_wav = output_path if ext == ".wav" else output_path + ".tmp.wav"

    int16_data = (np.clip(out_signal, -1.0, 1.0) * 32767.0).astype(np.int16)
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

    post_diag = analyze_phase_correlation(output_path, max_points=10)

    return {
        "success": True,
        "input_file": os.path.basename(input_path),
        "output_file": os.path.basename(output_path),
        "path": output_path,
        "inverted_right": invert_right_channel,
        "mono_bass_applied": mono_bass,
        "new_correlation": post_diag["correlation"],
        "new_status": post_diag["status"],
    }


def format_phase_card(res: Dict[str, Any]) -> str:
    """Renders ASCII card for Phase Correlation Analysis."""
    if not res.get("success"):
        return f"[!] Error: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append(f"| AUDIO PHASE CORRELATION & STEREO GONIOMETER METER              |")
    lines.append(sep)
    lines.append(f"| File           : {res['file'][:48]:<48} |")
    lines.append(f"| Duration       : {res['duration_sec']}s  |  Status: {res['status']:<25} |")
    lines.append(sep)

    # Correlation bar: -1.0 to +1.0 mapped to 30 characters
    val = res['correlation']
    pos = int(((val + 1.0) / 2.0) * 30)
    pos = max(0, min(29, pos))
    bar = ["-"] * 30
    bar[pos] = "|"
    bar_str = "".join(bar)

    lines.append(f"| Phase Correlation : {val:>+5.3f}   [-1.0 {bar_str} +1.0] |")
    lines.append(f"| Stereo Width      : {res['stereo_width_pct']:>5.1f}%  (Side/Mid Energy Ratio)                 |")
    lines.append(f"| L/R Balance Tilt  : {res['balance_db']:>+5.2f} dB {'(Left heavy)' if res['balance_db']>0.5 else '(Right heavy)' if res['balance_db']<-0.5 else '(Centered)'}                 |")
    lines.append(f"| Mono Collapse Loss: {res['mono_loss_db']:>+5.2f} dB (Power difference if summed to mono)     |")
    lines.append(sep)
    lines.append(f"| Diagnostic Evaluation:                                           |")
    lines.append(f"| {res['diagnosis'][:64]:<64} |")
    lines.append(sep)
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python phase_correlation.py <audio_file> [--correct]")
        sys.exit(1)

    target_audio = sys.argv[1]
    if "--correct" in sys.argv:
        res = correct_stereo_phase(target_audio)
        print(f"[+] Phase corrected file saved: {res.get('output_file')}")
        print(f"[+] New Phase Correlation: {res.get('new_correlation')} ({res.get('new_status')})")
    else:
        diag = analyze_phase_correlation(target_audio)
        print(format_phase_card(diag))
