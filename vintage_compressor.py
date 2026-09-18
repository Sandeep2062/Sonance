"""
vintage_compressor.py - Vintage Optical & Variable-Mu Master Compressor Studio
Part of Sonance (Unified Audiophile Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Phase 34 Milestone:
- Dual Iconic Vintage Analog Dynamic Topologies:
  1. Teletronix LA-2A (T4 Electro-Optical Attenuator):
     * Physical modeling of electroluminescent panel and dual CdS photoresistors.
     * Dual-stage memory-dependent release ballistics:
       Initial 50% release occurs fast (~60 ms), while remaining 50% exhibits
       a long gradual memory decay (0.5s to 4.5s) dependent on past compression history.
     * Fixed soft-knee curve with high-frequency pre-emphasis trimming (R37 emphasis).
  2. Fairchild 670 (Variable-Mu Dual-Triode 6386 Tube Compressor):
     * Continuous remote-cutoff variable-mu gain reduction: mu(Vg) = mu0 / (1 + k * |Vg|).
     * No fixed threshold; smooth progressive ratio scaling with signal density.
     * 6 classic stepped time-constant positions (from lightning 0.2ms/0.3s to 10s dual auto-release).
- Studio Mastering Features:
  * Sidechain High-Pass Filter (Flat, 60, 90, 120, 185 Hz) preventing bass pumping.
  * Sidechain HF Emphasis (R37 trim) boosting sibilance/treble sensitivity.
  * Analog 6386 / 12AX7 tube saturation and transformer warmth.
  * Stereo Link vs Dual-Mono sidechain detection.
  * Parallel New York style Dry/Wet compression blend (0-100%).
  * True-Peak brickwall safety limiter (-0.2 dBFS) & 24-bit linear PCM WAV export.
"""

import os
import sys
import math
import wave
import struct
import argparse
from typing import Dict, List, Optional, Tuple, Any

import numpy as np


# ---------------------------------------------------------------------------
# Audio File I/O
# ---------------------------------------------------------------------------

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
            padded = np.pad(raw_u, ((0, 0), (1, 0)), mode="constant", constant_values=0)
            data = padded.view("<i4").flatten().astype(np.float32) / 2147483648.0
        elif sampwidth == 4:
            data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            data = np.frombuffer(raw, dtype=np.float32)

        if n_ch >= 2:
            data = data.reshape(-1, n_ch).T[:2]
        else:
            data = np.vstack([data, data])
        return data, sr

    raise ValueError(f"Could not load audio file: {file_path}")


def write_audio_stereo_24bit(file_path: str, audio: np.ndarray, sr: int) -> None:
    """Writes 2-channel stereo audio to 24-bit linear PCM WAV."""
    samples = audio.shape[1]
    interleaved = np.empty((samples * 2,), dtype=np.float32)
    interleaved[0::2] = np.clip(audio[0], -1.0, 1.0)
    interleaved[1::2] = np.clip(audio[1], -1.0, 1.0)

    int24 = (interleaved * 8388607.0).astype(np.int32)
    bytes_arr = int24.tobytes()

    packed = bytearray(samples * 2 * 3)
    for i in range(samples * 2):
        b_idx = i * 4
        out_idx = i * 3
        packed[out_idx] = bytes_arr[b_idx]
        packed[out_idx + 1] = bytes_arr[b_idx + 1]
        packed[out_idx + 2] = bytes_arr[b_idx + 2]

    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)
        wf.setframerate(sr)
        wf.writeframes(packed)


# ---------------------------------------------------------------------------
# Biquad Filter Helpers for Sidechain Filtering
# ---------------------------------------------------------------------------

def apply_biquad_hpf(sig: np.ndarray, cutoff_hz: float, sr: int) -> np.ndarray:
    """2nd-order Butterworth High-Pass Filter for sidechain detection."""
    if cutoff_hz <= 10.0:
        return sig
    w0 = 2.0 * math.pi * cutoff_hz / sr
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / (2.0 * math.sqrt(2.0))

    b0 = (1.0 + cos_w0) / 2.0
    b1 = -(1.0 + cos_w0)
    b2 = (1.0 + cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)

    # IIR filter implementation
    out = np.zeros_like(sig)
    x1, x2, y1, y2 = 0.0, 0.0, 0.0, 0.0
    for i in range(len(sig)):
        x0 = float(sig[i])
        y0 = b[0] * x0 + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        out[i] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return out


def apply_hf_emphasis(sig: np.ndarray, sr: int, gain_db: float = 4.0) -> np.ndarray:
    """High-frequency emphasis shelf filter (~1 kHz+) simulating LA-2A R37 trim."""
    if gain_db <= 0.1:
        return sig
    w0 = 2.0 * math.pi * 1200.0 / sr
    A = 10.0 ** (gain_db / 40.0)
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / 2.0 * math.sqrt(2.0)

    b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + 2.0 * math.sqrt(A) * alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - 2.0 * math.sqrt(A) * alpha)
    a0 = (A + 1.0) - (A - 1.0) * cos_w0 + 2.0 * math.sqrt(A) * alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
    a2 = (A + 1.0) - (A - 1.0) * cos_w0 - 2.0 * math.sqrt(A) * alpha

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)

    out = np.zeros_like(sig)
    x1, x2, y1, y2 = 0.0, 0.0, 0.0, 0.0
    for i in range(len(sig)):
        x0 = float(sig[i])
        y0 = b[0] * x0 + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        out[i] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return out


# ---------------------------------------------------------------------------
# Analog Tube Saturation Physical Model
# ---------------------------------------------------------------------------

def apply_vintage_tube_drive(sig: np.ndarray, drive: float = 1.2, bias: float = 0.08) -> np.ndarray:
    """
    Emulates vintage 12AX7/6386 dual-triode tube harmonic saturation with
    asymmetric transfer function yielding warm 2nd and 3rd harmonics.
    """
    if drive <= 1.001 and abs(bias) < 0.01:
        return sig
    x = sig * drive
    denom = math.tanh(drive) if drive > 0.01 else 1.0
    sat = (np.tanh(x + bias) - math.tanh(bias)) / denom
    # Add subtle transformer core saturation
    subtle_iron = 0.03 * (drive - 1.0) * (sig ** 3)
    return (sat + subtle_iron).astype(np.float32)


# ---------------------------------------------------------------------------
# Dynamic Engine: Teletronix LA-2A (T4 Optical Attenuator)
# ---------------------------------------------------------------------------

def process_la2a_optical(
    audio: np.ndarray,
    sr: int,
    peak_reduction: float = 50.0,
    sidechain_hpf_hz: float = 90.0,
    hf_emphasis: bool = False,
    stereo_link: bool = True,
    block_size: int = 32
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Teletronix LA-2A T4 Electro-Optical Attenuator physical model.
    Dual-stage release: 50% initial fast release (~60ms) + gradual memory tail (0.5-4.5s).
    """
    channels, samples = audio.shape
    num_blocks = samples // block_size

    # Prepare sidechain signals
    sc_audio = np.copy(audio)
    for ch in range(channels):
        sc_audio[ch] = apply_biquad_hpf(sc_audio[ch], sidechain_hpf_hz, sr)
        if hf_emphasis:
            sc_audio[ch] = apply_hf_emphasis(sc_audio[ch], sr, gain_db=4.5)

    # Convert peak_reduction (0-100) to internal threshold & drive
    # 0 = no reduction, 100 = heavy limiting
    target_drive = 10.0 ** ((peak_reduction * 0.40 - 24.0) / 20.0)

    # Ballistics constants
    dt = block_size / float(sr)
    alpha_att = math.exp(-dt / 0.010)       # ~10 ms attack
    alpha_rel_fast = math.exp(-dt / 0.060)  # ~60 ms fast 50% release

    # Optical memory accumulation state
    gr_history = 0.0
    prev_gr_db = np.zeros(channels, dtype=np.float32)

    gain_reduction_curve = np.zeros((channels, samples), dtype=np.float32)
    max_gr_db = 0.0
    sum_gr_db = 0.0
    gr_sample_count = 0

    for b in range(num_blocks):
        start = b * block_size
        end = start + block_size

        # Compute block RMS for sidechain
        block_rms = np.sqrt(np.mean(sc_audio[:, start:end] ** 2, axis=1) + 1e-12)

        if stereo_link:
            link_rms = np.max(block_rms)
            rms_vals = [link_rms] * channels
        else:
            rms_vals = block_rms

        for ch in range(channels):
            det_val = rms_vals[ch] * target_drive
            # Non-linear electroluminescent panel luminescence response
            luminescence = (det_val ** 1.8) if det_val > 0.05 else 0.0

            # Target gain reduction in dB (soft knee)
            target_gr = -20.0 * math.log10(1.0 + luminescence * 4.0)
            target_gr = max(-36.0, min(0.0, target_gr))

            # Dynamic slow release time based on history (0.5s to 4.5s)
            gr_history = 0.995 * gr_history + 0.005 * abs(prev_gr_db[ch])
            t_slow = 0.5 + min(4.0, gr_history * 0.25)
            alpha_rel_slow = math.exp(-dt / t_slow)

            # Combined dual-stage optical decay
            if target_gr < prev_gr_db[ch]:
                # Attack phase
                curr_gr = target_gr + alpha_att * (prev_gr_db[ch] - target_gr)
            else:
                # Release phase: fast initial decay + slow memory tail
                delta_rel = prev_gr_db[ch] - target_gr
                half_fast = alpha_rel_fast * (delta_rel * 0.5)
                half_slow = alpha_rel_slow * (delta_rel * 0.5)
                curr_gr = target_gr + (half_fast + half_slow)

            prev_gr_db[ch] = curr_gr
            gain_reduction_curve[ch, start:end] = curr_gr

            if curr_gr < max_gr_db:
                max_gr_db = curr_gr
            sum_gr_db += abs(curr_gr)
            gr_sample_count += 1

    # Handle remaining tail samples
    if num_blocks * block_size < samples:
        rem_start = num_blocks * block_size
        for ch in range(channels):
            gain_reduction_curve[ch, rem_start:] = prev_gr_db[ch]

    # Apply gain reduction to audio
    gr_linear = 10.0 ** (gain_reduction_curve / 20.0)
    out_audio = audio * gr_linear

    telemetry = {
        "model": "Teletronix LA-2A (T4 Optical Attenuator)",
        "max_gain_reduction_db": round(float(max_gr_db), 2),
        "avg_gain_reduction_db": round(float(sum_gr_db / max(1, gr_sample_count)), 2),
        "optical_memory_seconds": round(float(0.5 + min(4.0, gr_history * 0.25)), 2),
    }

    return out_audio, gain_reduction_curve, telemetry


# ---------------------------------------------------------------------------
# Dynamic Engine: Fairchild 670 (Variable-Mu Dual-Triode 6386 Tube)
# ---------------------------------------------------------------------------

FAIRCHILD_TIME_CONSTANTS = {
    1: {"attack_sec": 0.0002, "release_sec": 0.30, "desc": "0.2ms / 0.3s (Aggressive Transient Grab)"},
    2: {"attack_sec": 0.0002, "release_sec": 0.80, "desc": "0.2ms / 0.8s (Punchy Drum & Rhythm Bus)"},
    3: {"attack_sec": 0.0004, "release_sec": 2.00, "desc": "0.4ms / 2.0s (Universal Vocal & Bass)"},
    4: {"attack_sec": 0.0004, "release_sec": 5.00, "desc": "0.4ms / 5.0s (Lush Acoustic & Master Mix)"},
    5: {"attack_sec": 0.0004, "release_sec": 2.00, "desc": "0.4ms / Auto (2s peak, 10s program memory)"},
    6: {"attack_sec": 0.0002, "release_sec": 0.30, "desc": "0.2ms / Auto (0.3s peak, 10s program memory)"},
}

def process_fairchild_varmu(
    audio: np.ndarray,
    sr: int,
    input_gain_db: float = 0.0,
    threshold_bias: float = 5.0,
    time_constant: int = 5,
    sidechain_hpf_hz: float = 90.0,
    stereo_link: bool = True,
    block_size: int = 32
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Fairchild 670 Variable-Mu Dual-Triode 6386 physical model.
    Grid-bias modulated amplification factor mu without a fixed threshold or knee.
    """
    channels, samples = audio.shape
    num_blocks = samples // block_size

    tc = FAIRCHILD_TIME_CONSTANTS.get(time_constant, FAIRCHILD_TIME_CONSTANTS[5])
    t_att = tc["attack_sec"]
    t_rel = tc["release_sec"]
    is_auto = time_constant in (5, 6)

    # Input level staging
    in_gain_lin = 10.0 ** (input_gain_db / 20.0)
    staged_audio = audio * in_gain_lin

    # Prepare sidechain
    sc_audio = np.copy(staged_audio)
    for ch in range(channels):
        sc_audio[ch] = apply_biquad_hpf(sc_audio[ch], sidechain_hpf_hz, sr)

    dt = block_size / float(sr)
    alpha_att = math.exp(-dt / max(1e-5, t_att))
    alpha_rel_base = math.exp(-dt / max(1e-5, t_rel))
    alpha_rel_auto = math.exp(-dt / 10.0)  # 10s memory recovery

    density_history = 0.0
    prev_gr_db = np.zeros(channels, dtype=np.float32)

    gain_reduction_curve = np.zeros((channels, samples), dtype=np.float32)
    max_gr_db = 0.0
    sum_gr_db = 0.0
    gr_sample_count = 0

    # Variable-Mu grid bias scale parameter
    bias_scale = 10.0 ** ((10.0 - threshold_bias) / 10.0)

    for b in range(num_blocks):
        start = b * block_size
        end = start + block_size

        block_peak = np.max(np.abs(sc_audio[:, start:end]), axis=1)

        if stereo_link:
            link_peak = np.max(block_peak)
            peak_vals = [link_peak] * channels
        else:
            peak_vals = block_peak

        for ch in range(channels):
            # Control voltage (Vg) generation via full-wave rectified DC bias
            vg = float(peak_vals[ch] * bias_scale)

            # 6386 Remote-cutoff variable-mu gain formula:
            # Mu(Vg) = Mu0 / (1 + k * Vg^1.2)
            if vg > 0.05:
                # Continuous variable-mu compression
                reduction_ratio = 1.0 / (1.0 + 1.6 * (vg ** 1.15))
                target_gr = 20.0 * math.log10(max(1e-4, reduction_ratio))
            else:
                target_gr = 0.0
            target_gr = max(-30.0, min(0.0, target_gr))

            # Ballistics
            if is_auto:
                density_history = 0.998 * density_history + 0.002 * abs(prev_gr_db[ch])
                long_blend = min(0.65, density_history * 0.08)
                effective_alpha_rel = (1.0 - long_blend) * alpha_rel_base + long_blend * alpha_rel_auto
            else:
                effective_alpha_rel = alpha_rel_base

            if target_gr < prev_gr_db[ch]:
                curr_gr = target_gr + alpha_att * (prev_gr_db[ch] - target_gr)
            else:
                curr_gr = target_gr + effective_alpha_rel * (prev_gr_db[ch] - target_gr)

            prev_gr_db[ch] = curr_gr
            gain_reduction_curve[ch, start:end] = curr_gr

            if curr_gr < max_gr_db:
                max_gr_db = curr_gr
            sum_gr_db += abs(curr_gr)
            gr_sample_count += 1

    if num_blocks * block_size < samples:
        rem_start = num_blocks * block_size
        for ch in range(channels):
            gain_reduction_curve[ch, rem_start:] = prev_gr_db[ch]

    gr_linear = 10.0 ** (gain_reduction_curve / 20.0)
    out_audio = staged_audio * gr_linear

    telemetry = {
        "model": "Fairchild 670 (Variable-Mu Dual-Triode 6386)",
        "time_constant_pos": time_constant,
        "time_constant_desc": tc["desc"],
        "max_gain_reduction_db": round(float(max_gr_db), 2),
        "avg_gain_reduction_db": round(float(sum_gr_db / max(1, gr_sample_count)), 2),
    }

    return out_audio, gain_reduction_curve, telemetry


# ---------------------------------------------------------------------------
# Factory Presets
# ---------------------------------------------------------------------------

FACTORY_PRESETS = {
    "la2a_smooth_vocal": {
        "name": "LA-2A Silky Vocal Leveler",
        "description": "Smooth, musical leveling for lead vocals with 60ms fast initial release and warm optical memory tail.",
        "mode": "la2a",
        "peak_reduction": 55.0,
        "sidechain_hpf_hz": 90.0,
        "hf_emphasis": True,
        "time_constant": 5,
        "tube_drive": 1.25,
        "makeup_gain_db": 3.5,
        "dry_wet": 1.0,
        "stereo_link": True
    },
    "la2a_acoustic_warmth": {
        "name": "LA-2A Acoustic Guitar & Piano",
        "description": "Gentle 2-4 dB transparent optical leveling enhancing warmth and sustain without transient smearing.",
        "mode": "la2a",
        "peak_reduction": 40.0,
        "sidechain_hpf_hz": 120.0,
        "hf_emphasis": False,
        "time_constant": 5,
        "tube_drive": 1.15,
        "makeup_gain_db": 2.0,
        "dry_wet": 0.90,
        "stereo_link": True
    },
    "fairchild_master_bus": {
        "name": "Fairchild 670 Mix Bus Glue",
        "description": "Classic Position 5 Auto-Release variable-mu mastering glue delivering cohesive analog mix density.",
        "mode": "fairchild",
        "peak_reduction": 45.0,
        "sidechain_hpf_hz": 90.0,
        "hf_emphasis": False,
        "time_constant": 5,
        "tube_drive": 1.20,
        "makeup_gain_db": 1.5,
        "dry_wet": 1.0,
        "stereo_link": True
    },
    "fairchild_drum_crush": {
        "name": "Fairchild 670 Drum Bus Punch",
        "description": "Fast Position 2 attack/release with rich 6386 tube saturation for explosive punch and room excitement.",
        "mode": "fairchild",
        "peak_reduction": 70.0,
        "sidechain_hpf_hz": 60.0,
        "hf_emphasis": False,
        "time_constant": 2,
        "tube_drive": 1.50,
        "makeup_gain_db": 4.0,
        "dry_wet": 0.75,
        "stereo_link": True
    },
    "vintage_warm_glue": {
        "name": "Vintage Hybrid Master Warmth",
        "description": "Balanced optical warmth with subtle tube saturation and wide dynamic retention for full tracks.",
        "mode": "la2a",
        "peak_reduction": 35.0,
        "sidechain_hpf_hz": 120.0,
        "hf_emphasis": False,
        "time_constant": 4,
        "tube_drive": 1.30,
        "makeup_gain_db": 1.0,
        "dry_wet": 0.85,
        "stereo_link": True
    }
}


# ---------------------------------------------------------------------------
# Master Rendering Controller
# ---------------------------------------------------------------------------

def render_vintage_compressor(
    input_path: str,
    output_path: Optional[str] = None,
    preset: str = "la2a_smooth_vocal",
    mode: Optional[str] = None,
    peak_reduction: Optional[float] = None,
    sidechain_hpf_hz: Optional[float] = None,
    hf_emphasis: Optional[bool] = None,
    time_constant: Optional[int] = None,
    tube_drive: Optional[float] = None,
    makeup_gain_db: Optional[float] = None,
    dry_wet: Optional[float] = None,
    stereo_link: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Renders audio through the Vintage Optical & Variable-Mu Master Compressor Studio.
    """
    audio, sr = read_audio_stereo(input_path)

    # Resolve settings from preset or overrides
    p = FACTORY_PRESETS.get(preset, FACTORY_PRESETS["la2a_smooth_vocal"])
    m = mode if mode is not None else p["mode"]
    pr = float(peak_reduction) if peak_reduction is not None else float(p["peak_reduction"])
    hpf = float(sidechain_hpf_hz) if sidechain_hpf_hz is not None else float(p["sidechain_hpf_hz"])
    hf = bool(hf_emphasis) if hf_emphasis is not None else bool(p["hf_emphasis"])
    tc = int(time_constant) if time_constant is not None else int(p["time_constant"])
    drv = float(tube_drive) if tube_drive is not None else float(p["tube_drive"])
    mk = float(makeup_gain_db) if makeup_gain_db is not None else float(p["makeup_gain_db"])
    mix = float(dry_wet) if dry_wet is not None else float(p["dry_wet"])
    link = bool(stereo_link) if stereo_link is not None else bool(p["stereo_link"])

    in_peak_db = 20.0 * math.log10(max(1e-6, np.max(np.abs(audio))))
    in_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(audio ** 2))))

    # Run dynamics core
    if m.lower() == "fairchild":
        compressed_audio, gr_curve, telemetry = process_fairchild_varmu(
            audio=audio,
            sr=sr,
            input_gain_db=0.0,
            threshold_bias=max(1.0, min(10.0, pr / 10.0)),
            time_constant=tc,
            sidechain_hpf_hz=hpf,
            stereo_link=link
        )
    else:
        # Default to LA-2A
        compressed_audio, gr_curve, telemetry = process_la2a_optical(
            audio=audio,
            sr=sr,
            peak_reduction=pr,
            sidechain_hpf_hz=hpf,
            hf_emphasis=hf,
            stereo_link=link
        )

    # Apply vintage tube saturation and transformer warmth
    if drv > 1.01:
        for ch in range(compressed_audio.shape[0]):
            compressed_audio[ch] = apply_vintage_tube_drive(compressed_audio[ch], drive=drv, bias=0.06)

    # Apply makeup gain
    if abs(mk) > 0.01:
        compressed_audio *= (10.0 ** (mk / 20.0))

    # Parallel dry/wet blend
    mix = max(0.0, min(1.0, mix))
    out_audio = (1.0 - mix) * audio + mix * compressed_audio

    # Master true-peak safety limiter (-0.2 dBFS ceiling)
    peak = np.max(np.abs(out_audio))
    ceiling = 10.0 ** (-0.2 / 20.0)
    if peak > ceiling:
        out_audio = (out_audio / peak) * ceiling

    out_peak_db = 20.0 * math.log10(max(1e-6, np.max(np.abs(out_audio))))
    out_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(out_audio ** 2))))
    duration_sec = out_audio.shape[1] / float(sr)

    crest_factor_in = in_peak_db - in_rms_db
    crest_factor_out = out_peak_db - out_rms_db

    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_{m.lower()}_vintage_master.wav"

    write_audio_stereo_24bit(output_path, out_audio, sr)

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "preset": preset,
        "preset_name": p.get("name", preset),
        "mode": m,
        "sample_rate": sr,
        "duration_sec": round(duration_sec, 2),
        "in_peak_dbfs": round(in_peak_db, 2),
        "in_rms_dbfs": round(in_rms_db, 2),
        "out_peak_dbfs": round(out_peak_db, 2),
        "out_rms_dbfs": round(out_rms_db, 2),
        "crest_factor_in_db": round(crest_factor_in, 2),
        "crest_factor_out_db": round(crest_factor_out, 2),
        "max_gain_reduction_db": telemetry.get("max_gain_reduction_db", 0.0),
        "avg_gain_reduction_db": telemetry.get("avg_gain_reduction_db", 0.0),
        "telemetry": telemetry,
        "settings": {
            "mode": m,
            "peak_reduction": pr,
            "sidechain_hpf_hz": hpf,
            "hf_emphasis": hf,
            "time_constant": tc,
            "tube_drive": drv,
            "makeup_gain_db": mk,
            "dry_wet": mix,
            "stereo_link": link
        }
    }


# ---------------------------------------------------------------------------
# Standalone CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sonance Phase 34: Vintage Optical & Variable-Mu Master Compressor Studio"
    )
    parser.add_argument("input", type=str, help="Path to input audio file")
    parser.add_argument("output", type=str, nargs="?", default=None, help="Output WAV path (optional)")
    parser.add_argument("--preset", type=str, default="la2a_smooth_vocal",
                        choices=list(FACTORY_PRESETS.keys()),
                        help="Factory preset name")
    parser.add_argument("--mode", type=str, choices=["la2a", "fairchild"], default=None,
                        help="Compressor topology: la2a (optical) or fairchild (variable-mu)")
    parser.add_argument("--reduction", "--pr", type=float, default=None,
                        help="Peak reduction / compression intensity (0-100)")
    parser.add_argument("--hpf", type=float, default=None,
                        help="Sidechain high-pass filter cutoff in Hz (0, 60, 90, 120, 185)")
    parser.add_argument("--hf-emphasis", action="store_true", default=None,
                        help="Enable high-frequency sidechain emphasis (LA-2A R37 trim)")
    parser.add_argument("--tc", type=int, choices=[1, 2, 3, 4, 5, 6], default=None,
                        help="Fairchild time-constant position (1 to 6)")
    parser.add_argument("--tube-drive", "--drive", type=float, default=None,
                        help="Vintage tube harmonic saturation drive (1.0 to 2.5x)")
    parser.add_argument("--makeup", "--gain", type=float, default=None,
                        help="Makeup gain in dB (-12 to +18 dB)")
    parser.add_argument("--mix", type=float, default=None,
                        help="Dry/wet parallel blend (0.0 to 1.0)")
    parser.add_argument("--dual-mono", action="store_true", default=False,
                        help="Independent Left/Right channel compression (disables stereo link)")

    args = parser.parse_args()

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.4.0")
    print("  Phase 34: Vintage Optical & Variable-Mu Master Compressor Studio")
    print("=" * 70)
    print(f"[*] Input Source     : {args.input}")
    print(f"[*] Preset Selected  : {args.preset.upper()}")

    stereo_link = not args.dual_mono

    res = render_vintage_compressor(
        input_path=args.input,
        output_path=args.output,
        preset=args.preset,
        mode=args.mode,
        peak_reduction=args.reduction,
        sidechain_hpf_hz=args.hpf,
        hf_emphasis=args.hf_emphasis,
        time_constant=args.tc,
        tube_drive=args.tube_drive,
        makeup_gain_db=args.makeup,
        dry_wet=args.mix,
        stereo_link=stereo_link
    )

    s = res["settings"]
    print(f"[+] Output Master    : {res['output_path']}")
    print(f"[+] Audio Format     : 24-bit Linear PCM WAV @ {res['sample_rate']} Hz ({res['duration_sec']}s)")
    print(f"[+] Model Emulation  : {res['telemetry']['model']}")
    print(f"[+] Peak Gain Reduct : {res['max_gain_reduction_db']:.2f} dB (Avg: {res['avg_gain_reduction_db']:.2f} dB)")
    print(f"[+] Dynamics Crest   : {res['crest_factor_in_db']:.2f} dB -> {res['crest_factor_out_db']:.2f} dB")
    print(f"[+] Tube Drive Stage : {s['tube_drive']:.2f}x | Makeup: {s['makeup_gain_db']:+.1f} dB | Mix: {int(s['dry_wet']*100)}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
