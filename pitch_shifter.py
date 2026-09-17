#!/usr/bin/env python3
"""
Sonance - Karaoke Vocal Pitch Transposer & Key Shifter Studio
=============================================================
Shifts the musical key / pitch of an audio track by +/- 6 semitones
without altering the tempo or duration (time-pitch invariance).

Enables vocalists and karaoke performers to adjust tracks to match their
natural singing range. Features:
- FFmpeg high-fidelity atempo/asetrate filter chain.
- Pure Python/NumPy Phase Vocoder DSP fallback.
- Export to WAV, FLAC, or MP3 with companion lyrics preserved.

Author: Sandeep Khadka (Sandeep2062) <sandeepkhadka9090@gmail.com>
License: GNU GPLv3 with Commons Clause
"""

import os
import math
import shutil
import subprocess
import wave
from typing import Dict, Any, Optional

import numpy as np


def check_ffmpeg() -> bool:
    """Checks if FFmpeg binary is available on PATH."""
    return shutil.which("ffmpeg") is not None


def phase_vocoder_pitch_shift(
    samples: np.ndarray,
    sr: int,
    semitones: float,
    n_fft: int = 2048,
    hop_size: int = 512
) -> np.ndarray:
    """
    Pure NumPy Phase Vocoder time-pitch invariant pitch shifter.
    Shifts pitch by semitones while preserving exact length.
    """
    if abs(semitones) < 0.01:
        return samples.copy()

    pitch_ratio = 2.0 ** (semitones / 12.0)
    time_stretch_ratio = 1.0 / pitch_ratio

    # Handle stereo channels individually
    if samples.ndim == 2:
        shifted_channels = []
        for ch in range(samples.shape[1]):
            s = _phase_vocoder_1d(samples[:, ch], sr, time_stretch_ratio, n_fft, hop_size)
            shifted_channels.append(s)
        # Resample back to original length
        shifted_stereo = np.column_stack(shifted_channels)
        return _resample_to_len(shifted_stereo, len(samples))
    else:
        stretched = _phase_vocoder_1d(samples, sr, time_stretch_ratio, n_fft, hop_size)
        return _resample_to_len(stretched, len(samples))


def _phase_vocoder_1d(
    x: np.ndarray,
    sr: int,
    stretch_ratio: float,
    n_fft: int = 2048,
    hop_a: int = 512
) -> np.ndarray:
    """Phase vocoder time-stretch for 1D channel."""
    hop_s = int(round(hop_a * stretch_ratio))
    window = np.hanning(n_fft).astype(np.float32)

    # Frame extraction
    num_frames = (len(x) - n_fft) // hop_a
    if num_frames <= 0:
        return x.copy()

    # Output buffer allocation
    out_len = num_frames * hop_s + n_fft
    out = np.zeros(out_len, dtype=np.float32)
    win_sum = np.zeros(out_len, dtype=np.float32)

    # Frequency bin centers
    omega = 2.0 * math.pi * np.arange(n_fft // 2 + 1) * hop_a / n_fft
    prev_phase = np.zeros(n_fft // 2 + 1, dtype=np.float32)
    out_phase = np.zeros(n_fft // 2 + 1, dtype=np.float32)

    for i in range(num_frames):
        idx = i * hop_a
        frame = x[idx:idx + n_fft] * window
        spec = np.fft.rfft(frame)
        mag = np.abs(spec)
        phase = np.angle(spec)

        # Phase advance and unwrapping
        delta_phase = phase - prev_phase - omega
        delta_phase = (delta_phase + math.pi) % (2.0 * math.pi) - math.pi
        true_freq = omega + delta_phase

        # Synthesis phase
        out_phase += true_freq * (hop_s / hop_a)
        prev_phase = phase

        # Synthesis frame
        syn_spec = mag * np.exp(1j * out_phase)
        syn_frame = np.fft.irfft(syn_spec, n=n_fft).real * window

        out_idx = i * hop_s
        out[out_idx:out_idx + n_fft] += syn_frame
        win_sum[out_idx:out_idx + n_fft] += window ** 2

    # Normalization by window overlap sum
    nonzero = win_sum > 1e-4
    out[nonzero] /= win_sum[nonzero]
    return out


def _resample_to_len(arr: np.ndarray, target_len: int) -> np.ndarray:
    """Linear interpolation to restore array to target sample length."""
    orig_len = len(arr)
    if orig_len == target_len:
        return arr

    x_orig = np.linspace(0, 1, orig_len)
    x_target = np.linspace(0, 1, target_len)

    if arr.ndim == 2:
        out = np.zeros((target_len, arr.shape[1]), dtype=np.float32)
        for ch in range(arr.shape[1]):
            out[:, ch] = np.interp(x_target, x_orig, arr[:, ch])
        return out
    else:
        return np.interp(x_target, x_orig, arr).astype(np.float32)


def shift_pitch_file(
    input_file: str,
    semitones: float,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Shifts the key of an audio file by semitones (-6 to +6).
    Preserves duration and tempo completely.
    """
    if not os.path.isfile(input_file):
        return {"success": False, "error": f"Audio file not found: {input_file}"}

    if abs(semitones) > 12:
        semitones = max(-12.0, min(12.0, float(semitones)))

    ext = os.path.splitext(input_file)[1].lower()
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    src_dir = os.path.dirname(os.path.abspath(input_file))

    sign = f"+{semitones:g}" if semitones > 0 else f"{semitones:g}"
    if not output_file:
        out_ext = ext if ext in [".wav", ".flac", ".mp3"] else ".wav"
        output_file = os.path.join(src_dir, f"{base_name}_key_{sign}{out_ext}")

    # FFmpeg asetrate + atempo filter chain
    if check_ffmpeg():
        try:
            pitch_ratio = 2.0 ** (semitones / 12.0)
            tempo_ratio = 1.0 / pitch_ratio

            # atempo filter accepts 0.5 to 2.0; chain multiple if outside
            tempo_filters = []
            rem_tempo = tempo_ratio
            while rem_tempo > 2.0:
                tempo_filters.append("atempo=2.0")
                rem_tempo /= 2.0
            while rem_tempo < 0.5:
                tempo_filters.append("atempo=0.5")
                rem_tempo /= 0.5
            tempo_filters.append(f"atempo={rem_tempo:.6f}")
            tempo_str = ",".join(tempo_filters)

            # Get source sample rate
            sr = 44100
            try:
                probe_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "stream=sample_rate", "-of", "default=noprint_wrappers=1:nokey=1", input_file]
                sr_out = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip()
                if sr_out:
                    sr = int(sr_out)
            except Exception:
                pass

            shifted_sr = int(round(sr * pitch_ratio))
            af_filter = f"asetrate={shifted_sr},{tempo_str},aresample={sr}"

            cmd = ["ffmpeg", "-y", "-i", input_file, "-af", af_filter, "-vn"]
            if output_file.lower().endswith(".flac"):
                cmd.extend(["-c:a", "flac"])
            elif output_file.lower().endswith(".mp3"):
                cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k"])
            elif output_file.lower().endswith(".wav"):
                cmd.extend(["-c:a", "pcm_s16le"])
            cmd.append(output_file)

            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            return {
                "success": True,
                "input_file": input_file,
                "output_file": output_file,
                "semitones": semitones,
                "key_shift_ratio": round(pitch_ratio, 4),
                "engine": "FFmpeg High-Fidelity Pitch Engine",
            }
        except Exception:
            pass

    # Native Python / NumPy Phase Vocoder for WAV files
    try:
        with wave.open(input_file, "rb") as wf:
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            sr = wf.getframerate()
            raw = wf.readframes(wf.getnframes())

        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            data = data.reshape(-1, ch)

        shifted_data = phase_vocoder_pitch_shift(data, sr, semitones)
        pcm_out = (np.clip(shifted_data, -1.0, 1.0) * 32767.0).astype(np.int16)

        out_wav = output_file if output_file.lower().endswith(".wav") else output_file + ".wav"
        with wave.open(out_wav, "wb") as wf:
            wf.setnchannels(ch)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm_out.tobytes())

        return {
            "success": True,
            "input_file": input_file,
            "output_file": out_wav,
            "semitones": semitones,
            "key_shift_ratio": round(2.0 ** (semitones / 12.0), 4),
            "engine": "Sonance Phase Vocoder NumPy Engine",
        }
    except Exception as e:
        return {"success": False, "error": f"Pitch shift failed: {str(e)}"}


if __name__ == "__main__":
    import sys
    print("Sonance Karaoke Vocal Pitch Transposer & Key Shifter")
    if len(sys.argv) < 3:
        print("Usage: python pitch_shifter.py <input_file> <semitones> [output_file]")
        sys.exit(1)

    in_file = sys.argv[1]
    semi = float(sys.argv[2])
    out_f = sys.argv[3] if len(sys.argv) > 3 else None
    res = shift_pitch_file(in_file, semi, out_f)
    print(res)
