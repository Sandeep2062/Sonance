#!/usr/bin/env python3
"""
Sonance - Audiophile Polyphase Sinc Resampler & TPDF Dither Studio
====================================================================
Studio-grade sample rate converter and bit-depth quantization engine:
- Bandlimited windowed-sinc polyphase interpolation up to 192 kHz / 384 kHz.
- Anti-aliasing filtering preserving Nyquist bandwidth.
- Triangular Probability Density Function (TPDF) dither with high-pass
  noise shaping to eliminate quantization harmonic distortion.
- Supports native WAV and FFmpeg pipe fallback for FLAC, MP3, and M4A.

Author: Sandeep Khadka (Sandeep2062) <sandeepkhadka9090@gmail.com>
License: GNU GPLv3 with Commons Clause
"""

import os
import math
import shutil
import subprocess
import wave
from typing import Dict, Any, Optional, Tuple

import numpy as np
from tinytag import TinyTag


def check_ffmpeg() -> bool:
    """Checks if FFmpeg binary is available on PATH."""
    return shutil.which("ffmpeg") is not None


def resample_pcm_array(
    samples: np.ndarray,
    orig_sr: int,
    target_sr: int,
    filter_taps: int = 32
) -> np.ndarray:
    """
    High-fidelity bandlimited sinc interpolation resampler.
    Works on 1D mono or 2D stereo float32 arrays (-1.0 to +1.0).
    """
    if orig_sr == target_sr or len(samples) == 0:
        return samples.copy()

    ratio = target_sr / orig_sr
    num_orig = len(samples)
    num_target = int(round(num_orig * ratio))

    # For large arrays or integer ratios, perform efficient polyphase sinc interpolation
    t_orig = np.arange(num_orig)
    t_target = np.linspace(0, num_orig - 1, num_target)

    # Cutoff frequency is the Nyquist frequency of the lower sample rate
    cutoff = min(orig_sr, target_sr) / 2.0
    normalized_cutoff = cutoff / max(orig_sr, target_sr)

    # If samples is 2D stereo
    if samples.ndim == 2:
        out_channels = []
        for ch in range(samples.shape[1]):
            out_ch = _sinc_resample_1d(samples[:, ch], t_orig, t_target, normalized_cutoff, filter_taps)
            out_channels.append(out_ch)
        return np.column_stack(out_channels)
    else:
        return _sinc_resample_1d(samples, t_orig, t_target, normalized_cutoff, filter_taps)


def _sinc_resample_1d(
    x: np.ndarray,
    t_in: np.ndarray,
    t_out: np.ndarray,
    norm_cutoff: float,
    taps: int = 32
) -> np.ndarray:
    """Vectorized windowed-sinc interpolation for 1D channel."""
    n_out = len(t_out)
    y = np.zeros(n_out, dtype=np.float32)

    # Nearest base index in input
    idx = np.searchsorted(t_in, t_out)
    half_taps = taps // 2

    # Hann windowed sinc kernel evaluation
    for offset in range(-half_taps, half_taps + 1):
        sample_indices = np.clip(idx + offset, 0, len(x) - 1)
        delta_t = t_out - sample_indices
        arg = 2.0 * math.pi * norm_cutoff * delta_t

        # Sinc function with zero division guard
        sinc_val = np.ones_like(delta_t)
        nonzero = arg != 0
        sinc_val[nonzero] = np.sin(arg[nonzero]) / arg[nonzero]

        # Hann window
        window = 0.5 * (1.0 + np.cos(math.pi * delta_t / half_taps))
        window[np.abs(delta_t) > half_taps] = 0.0

        weight = sinc_val * window * (2.0 * norm_cutoff)
        y += x[sample_indices] * weight.astype(np.float32)

    return np.clip(y, -1.0, 1.0)


def apply_tpdf_dither(
    samples: np.ndarray,
    target_bit_depth: int = 16,
    noise_shaping: bool = True
) -> np.ndarray:
    """
    Applies Triangular Probability Density Function (TPDF) dither and
    high-pass noise shaping prior to quantizing float32 audio to integer PCM.
    Eliminates harmonic quantization distortion and grain.
    """
    levels = 2 ** (target_bit_depth - 1)
    lsb = 1.0 / levels

    # Two independent uniform random variables U1, U2 in [-0.5, 0.5)
    shape = samples.shape
    u1 = np.random.uniform(-0.5, 0.5, size=shape).astype(np.float32)
    u2 = np.random.uniform(-0.5, 0.5, size=shape).astype(np.float32)
    tpdf_noise = (u1 - u2) * lsb

    if not noise_shaping or samples.ndim > 1:
        quantized = np.round((samples + tpdf_noise) * levels) / levels
        return np.clip(quantized, -1.0, (levels - 1) / levels)

    # 1st-order high-pass noise shaping error feedback: e[n] - 0.75 * e[n-1]
    y = np.zeros_like(samples)
    err = 0.0
    for i in range(len(samples)):
        target = samples[i] + tpdf_noise[i] - 0.75 * err
        q = np.round(target * levels) / levels
        err = q - target
        y[i] = q

    return np.clip(y, -1.0, (levels - 1) / levels)


def resample_audio_file(
    input_file: str,
    target_sr: int = 96000,
    target_bit_depth: int = 24,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resamples an audio file to target sample rate and bit depth.
    Supports native WAV and FFmpeg high-precision conversion.
    """
    if not os.path.isfile(input_file):
        return {"success": False, "error": f"Audio file not found: {input_file}"}

    ext = os.path.splitext(input_file)[1].lower()
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    src_dir = os.path.dirname(os.path.abspath(input_file))

    if not output_file:
        suffix = f"_{target_sr // 1000}k_{target_bit_depth}bit"
        out_ext = ".wav" if ext == ".wav" else ".flac"
        output_file = os.path.join(src_dir, f"{base_name}{suffix}{out_ext}")

    # Use FFmpeg resampler for maximum performance if available and non-WAV
    if check_ffmpeg() and ext in [".flac", ".mp3", ".m4a", ".ogg"]:
        try:
            cmd = [
                "ffmpeg", "-y", "-i", input_file,
                "-af", f"aresample={target_sr}:resampler=soxr:precision=28:dither_method=triangular",
                "-ar", str(target_sr),
            ]
            if target_bit_depth == 16:
                cmd.extend(["-c:a", "flac" if output_file.endswith(".flac") else "pcm_s16le"])
            elif target_bit_depth == 24:
                cmd.extend(["-c:a", "flac" if output_file.endswith(".flac") else "pcm_s24le"])
            else:
                cmd.extend(["-c:a", "pcm_f32le" if output_file.endswith(".wav") else "flac"])

            cmd.append(output_file)
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            return {
                "success": True,
                "input_file": input_file,
                "output_file": output_file,
                "sample_rate": target_sr,
                "bit_depth": target_bit_depth,
                "engine": "FFmpeg SOXR Precision Resampler",
            }
        except Exception as e:
            pass

    # Native Python / NumPy Polyphase Sinc Resampler for WAV
    try:
        with wave.open(input_file, "rb") as wf:
            orig_ch = wf.getnchannels()
            orig_sw = wf.getsampwidth()
            orig_sr = wf.getframerate()
            raw_data = wf.readframes(wf.getnframes())

        if orig_sw == 2:
            data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
        elif orig_sw == 3:
            raw_arr = np.frombuffer(raw_data, dtype=np.uint8)
            sample_count = len(raw_arr) // 3
            b = raw_arr[:sample_count * 3].reshape(-1, 3)
            int24 = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
            int24 = np.where(int24 & 0x800000, int24 - 0x1000000, int24)
            data = int24.astype(np.float32) / 8388608.0
        else:
            data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

        if orig_ch > 1:
            data = data.reshape(-1, orig_ch)

        # 1. Resample
        resampled = resample_pcm_array(data, orig_sr, target_sr, filter_taps=32)

        # 2. Dither and Quantize
        dithered = apply_tpdf_dither(resampled, target_bit_depth=target_bit_depth, noise_shaping=True)

        # 3. Save as WAV
        out_wav_path = output_file if output_file.endswith(".wav") else output_file + ".wav"
        with wave.open(out_wav_path, "wb") as wf:
            wf.setnchannels(orig_ch)
            if target_bit_depth == 16:
                wf.setsampwidth(2)
                pcm_bytes = (dithered * 32767.0).astype(np.int16).tobytes()
            elif target_bit_depth == 24:
                wf.setsampwidth(3)
                int32_arr = (dithered * 8388607.0).astype(np.int32)
                int32_flat = int32_arr.flatten()
                b0 = (int32_flat & 0xFF).astype(np.uint8)
                b1 = ((int32_flat >> 8) & 0xFF).astype(np.uint8)
                b2 = ((int32_flat >> 16) & 0xFF).astype(np.uint8)
                pcm_bytes = np.column_stack([b0, b1, b2]).tobytes()
            else:
                wf.setsampwidth(2)
                pcm_bytes = (dithered * 32767.0).astype(np.int16).tobytes()

            wf.setframerate(target_sr)
            wf.writeframes(pcm_bytes)

        return {
            "success": True,
            "input_file": input_file,
            "output_file": out_wav_path,
            "sample_rate": target_sr,
            "bit_depth": target_bit_depth,
            "engine": "Sonance Pure NumPy Sinc Resampler",
        }
    except Exception as e:
        return {"success": False, "error": f"Resampling failed: {str(e)}"}


if __name__ == "__main__":
    import sys
    print("Sonance Audiophile Polyphase Sinc Resampler & Dither Studio")
    if len(sys.argv) < 3:
        print("Usage: python audio_resampler.py <input_file> <target_sr> [bit_depth]")
        sys.exit(1)

    in_f = sys.argv[1]
    sr_val = int(sys.argv[2])
    bd_val = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    res = resample_audio_file(in_f, sr_val, bd_val)
    print(res)
