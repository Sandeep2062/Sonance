"""
audio_restorer.py - Analog Audio Restoration & Vinyl De-Clicker / De-Hisser Studio
Part of Sonance - The Ultimate Open-Source Music Workstation
Performs studio-grade restoration on digitized vinyl record rips and analog cassette tapes.
Features impulsive click/pop repair via cubic spline reconstruction, 50/60 Hz AC ground hum
notch filtering, 18 Hz subsonic turntable rumble removal, and tape hiss spectral reduction.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import math
import wave
import shutil
import subprocess
from typing import Dict, Any, Optional, Tuple, List
import numpy as np


def _decode_audio_to_float(input_path: str) -> Tuple[np.ndarray, int]:
    """Decodes audio file into float32 array [-1.0, 1.0] of shape (channels, samples)."""
    ext = os.path.splitext(input_path)[1].lower()

    if ext in {".wav", ".wave"}:
        try:
            with wave.open(input_path, "rb") as wf:
                n_ch = wf.getnchannels()
                sw = wf.getsampwidth()
                sr = wf.getframerate()
                n_f = wf.getnframes()
                raw = wf.readframes(n_f)
                if sw == 2:
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                elif sw == 3:
                    raw_arr = np.frombuffer(raw, dtype=np.uint8)
                    n_s = len(raw_arr) // 3
                    reshaped = raw_arr[: n_s * 3].reshape(-1, 3)
                    int24 = (
                        reshaped[:, 0].astype(np.int32)
                        | (reshaped[:, 1].astype(np.int32) << 8)
                        | (reshaped[:, 2].astype(np.int32) << 16)
                    )
                    int24[int24 >= 0x800000] -= 0x1000000
                    data = int24.astype(np.float32) / 8388608.0
                elif sw == 4:
                    data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
                else:
                    data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0

                if n_ch > 1:
                    data = data.reshape(-1, n_ch).T
                else:
                    data = data.reshape(1, -1)
                return data, sr
        except Exception:
            pass

    # Try FFmpeg fallback for MP3, FLAC, M4A, etc.
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    try:
        cmd = [
            ffmpeg_bin,
            "-v", "error",
            "-i", input_path,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "2",
            "-ar", "44100",
            "-",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        raw_pcm = proc.stdout
        arr = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
        data = arr.reshape(-1, 2).T
        return data, 44100
    except Exception as e:
        raise RuntimeError(f"Could not decode audio file: {e}")


def _design_biquad_notch(fc: float, q: float, sr: int) -> Tuple[float, float, float, float, float]:
    """Designs digital second-order IIR biquad notch filter coefficients (b0, b1, b2, a1, a2)."""
    w0 = 2.0 * math.pi * fc / sr
    alpha = math.sin(w0) / (2.0 * q)
    cos_w0 = math.cos(w0)

    b0 = 1.0
    b1 = -2.0 * cos_w0
    b2 = 1.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha

    # Normalize by a0
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def _apply_biquad_filter(audio: np.ndarray, b0: float, b1: float, b2: float, a1: float, a2: float) -> np.ndarray:
    """Applies Direct Form II biquad IIR filter across channels."""
    out = np.zeros_like(audio)
    for ch in range(audio.shape[0]):
        x = audio[ch]
        y = np.zeros_like(x)
        x1 = x2 = y1 = y2 = 0.0
        for i in range(len(x)):
            xi = x[i]
            yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            y[i] = yi
            x2 = x1
            x1 = xi
            y2 = y1
            y1 = yi
        out[ch] = y
    return out


def apply_declick(audio: np.ndarray, sr: int, sensitivity: float = 5.0) -> Tuple[np.ndarray, int]:
    """
    Impulsive click & pop detection and cubic interpolation restoration.
    Identifies sharp transient acceleration spikes characteristic of vinyl dust & scratches.
    """
    restored = audio.copy()
    total_clicks = 0
    # Search window of 1.5ms
    win_len = max(4, int(sr * 0.0015))

    for ch in range(restored.shape[0]):
        channel_data = restored[ch]
        if len(channel_data) < win_len * 4:
            continue

        # Compute 2nd difference (discrete acceleration)
        d2 = np.abs(channel_data[2:] - 2.0 * channel_data[1:-1] + channel_data[:-2])
        med = np.median(d2)
        mad = np.median(np.abs(d2 - med)) + 1e-9
        thresh = med + sensitivity * mad * 1.4826

        # Identify candidate click indices
        spike_indices = np.where(d2 > thresh)[0] + 1
        if len(spike_indices) == 0:
            continue

        # Group consecutive click points into clusters
        clusters: List[Tuple[int, int]] = []
        c_start = spike_indices[0]
        c_end = spike_indices[0]

        for idx in spike_indices[1:]:
            if idx <= c_end + win_len:
                c_end = idx
            else:
                clusters.append((max(0, c_start - 2), min(len(channel_data) - 1, c_end + 2)))
                c_start = idx
                c_end = idx
        clusters.append((max(0, c_start - 2), min(len(channel_data) - 1, c_end + 2)))

        total_clicks += len(clusters)

        # Repair each click cluster with cubic Hermite spline interpolation
        for start, end in clusters:
            span = end - start
            if span >= win_len * 4 or start < 2 or end >= len(channel_data) - 2:
                continue

            # Boundary points
            y0 = channel_data[start]
            y1 = channel_data[end]
            m0 = (channel_data[start] - channel_data[start - 2]) / 2.0
            m1 = (channel_data[end + 2] - channel_data[end]) / 2.0

            t = np.linspace(0.0, 1.0, span + 1)
            # Cubic Hermite basis functions
            h00 = (1 + 2 * t) * ((1 - t) ** 2)
            h10 = t * ((1 - t) ** 2)
            h01 = (t ** 2) * (3 - 2 * t)
            h11 = (t ** 2) * (t - 1)

            interp = h00 * y0 + h10 * m0 * span + h01 * y1 + h11 * m1 * span
            channel_data[start : end + 1] = interp

    return restored, total_clicks


def apply_dehum(audio: np.ndarray, sr: int, hum_freq: float = 60.0, harmonics: int = 3) -> np.ndarray:
    """Removes AC mains hum (50Hz or 60Hz) and overtones using high-Q biquad notch filters."""
    out = audio.copy()
    for h in range(1, harmonics + 1):
        fc = hum_freq * h
        if fc < sr / 2.0 - 50:
            q = 30.0 + h * 5.0
            b0, b1, b2, a1, a2 = _design_biquad_notch(fc, q, sr)
            out = _apply_biquad_filter(out, b0, b1, b2, a1, a2)
    return out


def apply_subsonic_rumble_filter(audio: np.ndarray, sr: int, cutoff_hz: float = 18.0) -> np.ndarray:
    """Applies high-pass filter to eliminate turntable motor rumble below 18 Hz."""
    # 2-stage cascaded second-order high-pass Butterworth filter
    w0 = 2.0 * math.pi * cutoff_hz / sr
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / (2.0 * (1.0 / math.sqrt(2.0)))

    b0 = (1.0 + cos_w0) / 2.0
    b1 = -(1.0 + cos_w0)
    b2 = (1.0 + cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha

    norm_b0 = b0 / a0
    norm_b1 = b1 / a0
    norm_b2 = b2 / a0
    norm_a1 = a1 / a0
    norm_a2 = a2 / a0

    out = _apply_biquad_filter(audio, norm_b0, norm_b1, norm_b2, norm_a1, norm_a2)
    # Second pass for 24 dB/oct roll-off
    out = _apply_biquad_filter(out, norm_b0, norm_b1, norm_b2, norm_a1, norm_a2)
    return out


def apply_dehiss(audio: np.ndarray, sr: int, hiss_reduction_db: float = 8.0) -> np.ndarray:
    """Applies high-frequency spectral downward expansion to diminish tape hiss above 7 kHz."""
    if hiss_reduction_db <= 0:
        return audio

    cutoff_hz = 7000.0
    if cutoff_hz >= sr / 2.0 - 500:
        return audio

    # High-shelf filter to gently attenuate tape hiss region
    w0 = 2.0 * math.pi * cutoff_hz / sr
    gain_linear = 10.0 ** (-abs(hiss_reduction_db) / 40.0)
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    a = gain_linear
    alpha = sin_w0 / 2.0 * math.sqrt((a + 1.0 / a) * (1.0 / 0.707 - 1.0) + 2.0)

    b0 = a * ((a + 1.0) + (a - 1.0) * cos_w0 + 2.0 * math.sqrt(a) * alpha)
    b1 = -2.0 * a * ((a - 1.0) + (a + 1.0) * cos_w0)
    b2 = a * ((a + 1.0) + (a - 1.0) * cos_w0 - 2.0 * math.sqrt(a) * alpha)
    a0 = (a + 1.0) - (a - 1.0) * cos_w0 + 2.0 * math.sqrt(a) * alpha
    a1 = 2.0 * ((a - 1.0) - (a + 1.0) * cos_w0)
    a2 = (a + 1.0) - (a - 1.0) * cos_w0 - 2.0 * math.sqrt(a) * alpha

    return _apply_biquad_filter(audio, b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def restore_analog_audio(
    input_path: str,
    output_path: Optional[str] = None,
    declick: bool = True,
    dehum_freq: Optional[float] = 60.0,
    rumble_filter: bool = True,
    dehiss: bool = True,
    click_sensitivity: float = 5.0,
) -> Dict[str, Any]:
    """
    Main entry point for analog audio restoration.
    Performs de-clicking, ground hum notch filtering, rumble removal, and de-hissing.
    """
    if not os.path.isfile(input_path):
        return {"success": False, "error": f"File not found: {input_path}"}

    try:
        audio, sr = _decode_audio_to_float(input_path)
    except Exception as e:
        return {"success": False, "error": str(e)}

    stats = {
        "clicks_repaired": 0,
        "dehum_applied": False,
        "rumble_filtered": False,
        "dehiss_applied": False,
    }

    # 1. Subsonic Turntable Rumble Filter (removes DC / motor resonance first)
    if rumble_filter:
        audio = apply_subsonic_rumble_filter(audio, sr, cutoff_hz=18.0)
        stats["rumble_filtered"] = True

    # 2. AC Ground Hum Filter (50 Hz or 60 Hz)
    if dehum_freq and dehum_freq in {50.0, 60.0}:
        audio = apply_dehum(audio, sr, hum_freq=dehum_freq, harmonics=3)
        stats["dehum_applied"] = True
        stats["hum_frequency"] = f"{int(dehum_freq)} Hz"

    # 3. Impulsive De-Clicker / De-Popper
    if declick:
        audio, clicks = apply_declick(audio, sr, sensitivity=click_sensitivity)
        stats["clicks_repaired"] = clicks

    # 4. Tape Hiss Reducer
    if dehiss:
        audio = apply_dehiss(audio, sr, hiss_reduction_db=7.0)
        stats["dehiss_applied"] = True

    # Normalize audio slightly if any clipping occurred
    peak = np.max(np.abs(audio))
    if peak > 0.999:
        audio = (audio / peak) * 0.98

    # Determine output path
    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_Restored.wav"

    out_ext = os.path.splitext(output_path)[1].lower()
    temp_wav = output_path if out_ext in {".wav", ".wave"} else f"{output_path}.tmp.wav"

    # Save to 16-bit PCM WAV
    int16_pcm = np.clip(audio * 32767.0, -32768.0, 32767.0).astype(np.int16)
    interleaved = int16_pcm.T.flatten() if audio.shape[0] > 1 else int16_pcm.flatten()

    with wave.open(temp_wav, "wb") as wf:
        wf.setnchannels(audio.shape[0])
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(interleaved.tobytes())

    # If FLAC or MP3 requested, convert using FFmpeg
    if out_ext not in {".wav", ".wave"}:
        try:
            ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
            subprocess.run([ffmpeg_bin, "-y", "-v", "error", "-i", temp_wav, output_path], check=True)
            if os.path.exists(temp_wav) and temp_wav != output_path:
                os.remove(temp_wav)
        except Exception:
            output_path = temp_wav

    dur_sec = round(audio.shape[1] / sr, 2)
    stats.update({
        "success": True,
        "input_file": input_path,
        "output_file": output_path,
        "duration_sec": dur_sec,
        "sample_rate": sr,
        "channels": audio.shape[0],
    })
    return stats


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audio_restorer.py <audio_file> [output_file] [--declick] [--dehum 50|60] [--rumble] [--dehiss]")
        sys.exit(1)

    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    hum = 60.0 if "--dehum" in sys.argv else None
    if "--dehum" in sys.argv:
        h_idx = sys.argv.index("--dehum")
        if h_idx + 1 < len(sys.argv) and sys.argv[h_idx + 1] in {"50", "60"}:
            hum = float(sys.argv[h_idx + 1])

    res = restore_analog_audio(
        inp,
        output_path=out,
        declick="--no-declick" not in sys.argv,
        dehum_freq=hum,
        rumble_filter="--no-rumble" not in sys.argv,
        dehiss="--no-dehiss" not in sys.argv,
    )
    if res.get("success"):
        print("[+] Audio Restoration Succeeded!")
        print(f"    • Output:         {res['output_file']}")
        print(f"    • Clicks Repaired:{res['clicks_repaired']}")
        print(f"    • Rumble Filtered:{res['rumble_filtered']}")
        print(f"    • Dehum Applied:  {res['dehum_applied']}")
        print(f"    • Dehiss Applied: {res['dehiss_applied']}")
    else:
        print(f"[-] Restoration Failed: {res.get('error')}")
