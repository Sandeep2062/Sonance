"""
console_channel_strip.py - British Class-A Console Channel Strip & SSL G-Master Bus Compressor Studio
Part of Sonance (Unified Audiophile Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Phase 30 Landmark Milestone:
- Solid State Logic (SSL 4000 G-Master Bus Compressor):
  * Quad-VCA peak/RMS detector with log-domain envelope
  * Selectable ratios: 1.5:1, 2:1, 4:1, 10:1
  * Attack times: 0.1ms, 0.3ms, 1.0ms, 3.0ms, 10.0ms, 30.0ms
  * Release times: 0.1s, 0.3s, 0.6s, 1.2s, and program-dependent Auto-Release
  * Sidechain High-Pass Filter (HPF): Bypass, 60Hz, 90Hz, 120Hz, 185Hz
  * Parallel New York-style compression (0-100% Dry/Wet) & makeup gain (-6 to +18 dB)
- Neve 1073 Class-A Preamp & 3-Band Inductor EQ:
  * Marinair transformer harmonic saturation: y = tanh(drive * x + bias) + alpha * x^3
  * High-Pass Filter: 18 dB/oct 3rd-order Butterworth (45, 70, 160, 360 Hz)
  * Low Shelf: 35, 60, 110, 220 Hz (+/- 16 dB) with classic Neve overshoot
  * Mid Peaking: Proportional-Q inductor bands (360, 700, 1600, 3200, 4800, 7200 Hz, +/- 18 dB)
  * High Shelf: 12 kHz Baxandall air sheen (+/- 16 dB)
- Analog Console Summing & Crosstalk:
  * Inter-channel stereo crosstalk (-65 dB frequency-shaped leakage)
  * Switchable analog thermal noise floor (-90 dBFS)
  * Master true-peak safety ceiling limiter (-0.2 dBFS)
- 24-bit PCM WAV master export with real-time gain reduction telemetry
"""

import os
import sys
import math
import wave
import struct
import argparse
from dataclasses import dataclass, field
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
            data = data.reshape(-1, n_ch)[:, :2].T
        else:
            data = np.vstack([data, data])
        return data, sr

    raise RuntimeError(f"Unsupported audio format or unreadable file: {file_path}")


def write_wav_24bit(file_path: str, audio: np.ndarray, sample_rate: int):
    """Writes float32 array with shape (2, samples) to 24-bit linear PCM WAV."""
    audio = np.clip(audio, -1.0, 1.0)
    samples = audio.shape[1]
    int24_data = (audio * 8388607.0).astype(np.int32)
    interleaved = np.empty((samples * 2,), dtype=np.int32)
    interleaved[0::2] = int24_data[0]
    interleaved[1::2] = int24_data[1]

    raw_bytes = bytearray(samples * 2 * 3)
    idx = 0
    for val in interleaved:
        val_u = val & 0xFFFFFF
        raw_bytes[idx] = val_u & 0xFF
        raw_bytes[idx + 1] = (val_u >> 8) & 0xFF
        raw_bytes[idx + 2] = (val_u >> 16) & 0xFF
        idx += 3

    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(raw_bytes))


# ---------------------------------------------------------------------------
# Biquad Filter Mathematics (Transposed Direct-Form II)
# ---------------------------------------------------------------------------

def apply_biquad_filter(audio: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Applies a biquad IIR filter across 2 channels using transposed direct-form II."""
    b0, b1, b2 = b[0], b[1], b[2]
    a1, a2 = a[1], a[2]
    out = np.zeros_like(audio)

    for ch in range(audio.shape[0]):
        x = audio[ch]
        y = np.zeros_like(x)
        d1, d2 = 0.0, 0.0
        for i in range(len(x)):
            xi = x[i]
            yi = b0 * xi + d1
            d1 = b1 * xi - a1 * yi + d2
            d2 = b2 * xi - a2 * yi
            y[i] = yi
        out[ch] = y
    return out


def make_peaking_coeffs(fc: float, gain_db: float, q: float, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    """Bristow-Johnson parametric peaking biquad filter."""
    if abs(gain_db) < 0.01:
        return np.array([1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])
    w0 = 2.0 * math.pi * min(fc, sr * 0.49) / sr
    alpha = math.sin(w0) / (2.0 * max(q, 0.05))
    A = 10.0 ** (gain_db / 40.0)
    cos_w0 = math.cos(w0)

    b0 = 1.0 + alpha * A
    b1 = -2.0 * cos_w0
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha / A

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return b, a


def make_lowshelf_coeffs(fc: float, gain_db: float, q: float, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    """Low-shelf biquad filter with Neve-style overshoot resonance."""
    if abs(gain_db) < 0.01:
        return np.array([1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])
    w0 = 2.0 * math.pi * min(fc, sr * 0.49) / sr
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    A = 10.0 ** (gain_db / 40.0)
    alpha = sin_w0 / (2.0 * max(q, 0.05))
    sqrt_A = math.sqrt(max(A, 1e-6))

    b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha)
    b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha)
    a0 = (A + 1.0) + (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha
    a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
    a2 = (A + 1.0) + (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return b, a


def make_highshelf_coeffs(fc: float, gain_db: float, q: float, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    """High-shelf biquad filter for Baxandall 12 kHz air sheen."""
    if abs(gain_db) < 0.01:
        return np.array([1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])
    w0 = 2.0 * math.pi * min(fc, sr * 0.49) / sr
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    A = 10.0 ** (gain_db / 40.0)
    alpha = sin_w0 / (2.0 * max(q, 0.05))
    sqrt_A = math.sqrt(max(A, 1e-6))

    b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha)
    a0 = (A + 1.0) - (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
    a2 = (A + 1.0) - (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return b, a


def make_highpass_coeffs(fc: float, q: float, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    """2nd-order Butterworth / peaking high-pass biquad filter."""
    if fc <= 5.0:
        return np.array([1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])
    w0 = 2.0 * math.pi * min(fc, sr * 0.49) / sr
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / (2.0 * max(q, 0.05))

    b0 = (1.0 + cos_w0) / 2.0
    b1 = -(1.0 + cos_w0)
    b2 = (1.0 + cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return b, a


# ---------------------------------------------------------------------------
# Neve 1073 Class-A Preamp & Inductor EQ Model
# ---------------------------------------------------------------------------

@dataclass
class Neve1073Config:
    preamp_drive: float = 1.25          # 1.0 (clean) to 4.0 (hot transformer saturation)
    transformer_warmth: float = 0.25    # 0.0 to 1.0 (asymmetrical tube/transformer harmonics)
    hpf_hz: float = 45.0                # 0 (bypass), 45, 70, 160, 360 Hz
    low_shelf_hz: float = 60.0          # 35, 60, 110, 220 Hz
    low_shelf_gain_db: float = 1.5      # -16.0 to +16.0 dB
    mid_freq_hz: float = 3200.0         # 360, 700, 1600, 3200, 4800, 7200 Hz
    mid_gain_db: float = 1.0            # -18.0 to +18.0 dB
    high_shelf_gain_db: float = 1.5     # -16.0 to +16.0 dB @ 12 kHz Baxandall
    bypass: bool = False


def process_neve_1073(audio: np.ndarray, config: Neve1073Config, sr: int) -> np.ndarray:
    """Processes stereo audio through physical Neve 1073 preamp and 3-band inductor EQ."""
    if config.bypass:
        return audio.copy()

    processed = audio.copy()

    # 1. High-Pass Filter (18 dB/oct 3rd-order: 2nd-order Butterworth + 1st-order RC)
    if config.hpf_hz > 10.0:
        b_hpf, a_hpf = make_highpass_coeffs(config.hpf_hz, 0.707, sr)
        processed = apply_biquad_filter(processed, b_hpf, a_hpf)
        # Extra 1st order slope
        w0 = 2.0 * math.pi * config.hpf_hz / sr
        alpha_rc = math.exp(-w0)
        for ch in range(2):
            x = processed[ch]
            y = np.zeros_like(x)
            prev_y = 0.0
            prev_x = 0.0
            for i in range(len(x)):
                curr_y = alpha_rc * (prev_y + x[i] - prev_x)
                y[i] = curr_y
                prev_y = curr_y
                prev_x = x[i]
            processed[ch] = y

    # 2. Low-Shelf Filter (Overshoot curve at selected frequency)
    if abs(config.low_shelf_gain_db) > 0.01:
        # Neve low shelf has slight overshoot/undershoot resonance (Q ~ 0.82)
        b_ls, a_ls = make_lowshelf_coeffs(config.low_shelf_hz, config.low_shelf_gain_db, 0.82, sr)
        processed = apply_biquad_filter(processed, b_ls, a_ls)

    # 3. Mid Peaking Band (Proportional-Q inductor band)
    if abs(config.mid_gain_db) > 0.01:
        # Proportional-Q: sharper Q at higher gains, wider Q at gentle touches
        gain_abs = abs(config.mid_gain_db)
        proportional_q = 0.6 + (gain_abs / 18.0) * 0.9  # 0.6 to 1.5
        b_mid, a_mid = make_peaking_coeffs(config.mid_freq_hz, config.mid_gain_db, proportional_q, sr)
        processed = apply_biquad_filter(processed, b_mid, a_mid)

    # 4. High-Shelf 12 kHz Baxandall Air Sheen
    if abs(config.high_shelf_gain_db) > 0.01:
        b_hs, a_hs = make_highshelf_coeffs(12000.0, config.high_shelf_gain_db, 0.707, sr)
        processed = apply_biquad_filter(processed, b_hs, a_hs)

    # 5. Marinair Output Transformer & Class-A Preamp Saturation
    drive = max(1.0, config.preamp_drive)
    warmth = max(0.0, min(1.0, config.transformer_warmth))
    if drive > 1.01 or warmth > 0.01:
        bias = 0.04 * warmth
        tanh_norm = math.tanh(drive)
        # Soft-knee tanh with 2nd-order bias and subtle 3rd-order transformer core flux
        saturated = (np.tanh(drive * processed + bias) - np.tanh(bias)) / tanh_norm
        if warmth > 0.05:
            # 3rd-order transformer core hysteresis saturation
            cubic = 0.04 * warmth * (processed ** 3)
            saturated = saturated + cubic
        processed = saturated

    return processed


# ---------------------------------------------------------------------------
# Solid State Logic (SSL 4000 G-Master Bus Compressor Model)
# ---------------------------------------------------------------------------

@dataclass
class SSLBusCompressorConfig:
    threshold_db: float = -14.0         # -30.0 to +10.0 dB
    ratio: float = 2.0                  # 1.5, 2.0, 4.0, 10.0
    attack_ms: float = 30.0             # 0.1, 0.3, 1.0, 3.0, 10.0, 30.0 ms
    release_sec: float = -1.0           # 0.1, 0.3, 0.6, 1.2, or -1.0 for Auto
    sidechain_hpf_hz: float = 90.0      # 0 (bypass), 60, 90, 120, 185 Hz
    makeup_gain_db: float = 2.0         # -6.0 to +18.0 dB
    dry_wet: float = 1.0                # 0.0 to 1.0 (Parallel Compression)
    bypass: bool = False


def process_ssl_bus_compressor(
    audio: np.ndarray, config: SSLBusCompressorConfig, sr: int
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Processes stereo audio through the iconic SSL 4000 G-Master Bus VCA Compressor.
    Returns: (compressed_audio, telemetry_dict)
    """
    if config.bypass:
        return audio.copy(), {
            "max_gain_reduction_db": 0.0,
            "avg_gain_reduction_db": 0.0,
            "rms_in_db": 0.0,
            "rms_out_db": 0.0
        }

    samples = audio.shape[1]
    in_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(audio ** 2))))

    # 1. Sidechain High-Pass Filter (prevents kick/bass pumping)
    sc_audio = audio.copy()
    if config.sidechain_hpf_hz > 10.0:
        b_sc, a_sc = make_highpass_coeffs(config.sidechain_hpf_hz, 0.707, sr)
        sc_audio = apply_biquad_filter(sc_audio, b_sc, a_sc)

    # Sidechain detector signal (maximum of absolute L and R)
    sc_detector = np.maximum(np.abs(sc_audio[0]), np.abs(sc_audio[1]))
    sc_detector = np.maximum(sc_detector, 1e-6)
    sc_db = 20.0 * np.log10(sc_detector)

    # 2. Static VCA Characteristic Curve with Smooth Soft Knee
    threshold = config.threshold_db
    ratio = max(1.0, config.ratio)
    knee_width = 4.0  # 4 dB soft-knee characteristic of the 4000 G VCA
    slope = 1.0 - 1.0 / ratio

    # Desired gain reduction in dB
    gr_target = np.zeros(samples, dtype=np.float32)

    over_knee = sc_db - threshold
    lower_idx = over_knee < -knee_width / 2.0
    upper_idx = over_knee > knee_width / 2.0
    knee_idx = ~(lower_idx | upper_idx)

    # Linear below knee: 0 dB reduction
    gr_target[lower_idx] = 0.0
    # Linear above knee
    gr_target[upper_idx] = -slope * (over_knee[upper_idx])
    # Quadratic soft-knee transition
    gr_target[knee_idx] = -slope * ((over_knee[knee_idx] + knee_width / 2.0) ** 2) / (2.0 * knee_width)

    # 3. Dynamic Ballistics (Log-Domain Smoothing)
    attack_sec = max(0.0001, config.attack_ms / 1000.0)
    alpha_att = math.exp(-1.0 / (sr * attack_sec))

    is_auto_release = (config.release_sec <= 0.0)
    if is_auto_release:
        # SSL G-Comp Auto Release: dual-stage release (0.1s fast recovery + 1.2s program memory)
        alpha_rel_fast = math.exp(-1.0 / (sr * 0.10))
        alpha_rel_slow = math.exp(-1.0 / (sr * 1.20))
    else:
        release_sec = max(0.01, config.release_sec)
        alpha_rel = math.exp(-1.0 / (sr * release_sec))

    # Envelope ballistics loop
    gr_env = np.zeros(samples, dtype=np.float32)
    curr_env = 0.0
    curr_slow = 0.0

    for i in range(samples):
        target = gr_target[i]
        if target < curr_env:
            # Attack phase (gain reduction deepening)
            curr_env = alpha_att * curr_env + (1.0 - alpha_att) * target
            if is_auto_release:
                curr_slow = curr_env
        else:
            # Release phase (gain recovery)
            if is_auto_release:
                curr_env = alpha_rel_fast * curr_env + (1.0 - alpha_rel_fast) * target
                curr_slow = alpha_rel_slow * curr_slow + (1.0 - alpha_rel_slow) * target
                # Program-dependent blend: 65% fast recovery, 35% slow memory
                curr_env = 0.65 * curr_env + 0.35 * curr_slow
            else:
                curr_env = alpha_rel * curr_env + (1.0 - alpha_rel) * target
        gr_env[i] = curr_env

    # 4. Gain VCA Modulation & Makeup Gain
    makeup_linear = 10.0 ** (config.makeup_gain_db / 20.0)
    vca_gain = (10.0 ** (gr_env / 20.0)) * makeup_linear

    # Apply to stereo channels
    compressed = np.empty_like(audio)
    compressed[0] = audio[0] * vca_gain
    compressed[1] = audio[1] * vca_gain

    # 5. Parallel Wet/Dry Mix
    dry_wet = max(0.0, min(1.0, config.dry_wet))
    if dry_wet < 0.999:
        out = (1.0 - dry_wet) * audio + dry_wet * compressed
    else:
        out = compressed

    max_gr = float(np.min(gr_env))   # Negative value (e.g. -4.5 dB)
    avg_gr = float(np.mean(gr_env))
    out_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(out ** 2))))

    telemetry = {
        "max_gain_reduction_db": abs(max_gr),
        "avg_gain_reduction_db": abs(avg_gr),
        "rms_in_db": round(in_rms_db, 2),
        "rms_out_db": round(out_rms_db, 2),
        "ratio": config.ratio,
        "attack_ms": config.attack_ms,
        "release": "Auto" if is_auto_release else f"{config.release_sec}s",
        "makeup_db": config.makeup_gain_db,
        "dry_wet_pct": int(dry_wet * 100)
    }

    return out, telemetry


# ---------------------------------------------------------------------------
# Console Summing, Crosstalk & Analog Master Strip
# ---------------------------------------------------------------------------

@dataclass
class ConsoleStripConfig:
    neve: Neve1073Config = field(default_factory=Neve1073Config)
    ssl: SSLBusCompressorConfig = field(default_factory=SSLBusCompressorConfig)
    crosstalk_db: float = -65.0         # -90 to -50 dB (inter-channel analog console bleed)
    analog_noise: bool = False          # Subtle analog console thermal noise floor
    output_gain_db: float = 0.0         # -12 to +12 dB
    safety_limiter: bool = True         # Ceiling limiter at -0.2 dBFS


FACTORY_PRESETS: Dict[str, Dict[str, Any]] = {
    "master_bus_glue": {
        "name": "SSL Master Bus Glue & Neve Sheen",
        "description": "Classic Solid State Logic 4000 master bus glue with gentle 2:1 ratio, 30ms attack, Auto release, 90Hz HPF, and Neve 12kHz high air sheen.",
        "ssl": {
            "threshold_db": -13.5,
            "ratio": 2.0,
            "attack_ms": 30.0,
            "release_sec": -1.0,
            "sidechain_hpf_hz": 90.0,
            "makeup_gain_db": 2.2,
            "dry_wet": 1.0,
            "bypass": False
        },
        "neve": {
            "preamp_drive": 1.2,
            "transformer_warmth": 0.25,
            "hpf_hz": 45.0,
            "low_shelf_hz": 60.0,
            "low_shelf_gain_db": 1.0,
            "mid_freq_hz": 3200.0,
            "mid_gain_db": 0.5,
            "high_shelf_gain_db": 1.8,
            "bypass": False
        },
        "crosstalk_db": -65.0,
        "output_gain_db": 0.0
    },
    "analog_warmth": {
        "name": "British Class-A Transformer Saturation",
        "description": "Rich Neve 1073 Marinair transformer saturation and 60Hz low shelf warmth paired with subtle optical-style bus smoothing.",
        "ssl": {
            "threshold_db": -10.0,
            "ratio": 1.5,
            "attack_ms": 30.0,
            "release_sec": 0.6,
            "sidechain_hpf_hz": 120.0,
            "makeup_gain_db": 1.0,
            "dry_wet": 1.0,
            "bypass": False
        },
        "neve": {
            "preamp_drive": 2.8,
            "transformer_warmth": 0.75,
            "hpf_hz": 45.0,
            "low_shelf_hz": 60.0,
            "low_shelf_gain_db": 2.5,
            "mid_freq_hz": 1600.0,
            "mid_gain_db": 1.0,
            "high_shelf_gain_db": 1.2,
            "bypass": False
        },
        "crosstalk_db": -60.0,
        "output_gain_db": -0.5
    },
    "drum_bus_punch": {
        "name": "Aggressive Drum Bus Punch & Snap",
        "description": "Fast 10ms SSL attack with 4:1 punchy ratio, 120Hz kick protector HPF, and parallel compression blend for explosive drum room energy.",
        "ssl": {
            "threshold_db": -16.0,
            "ratio": 4.0,
            "attack_ms": 10.0,
            "release_sec": 0.1,
            "sidechain_hpf_hz": 120.0,
            "makeup_gain_db": 4.0,
            "dry_wet": 0.75,
            "bypass": False
        },
        "neve": {
            "preamp_drive": 1.5,
            "transformer_warmth": 0.35,
            "hpf_hz": 45.0,
            "low_shelf_hz": 110.0,
            "low_shelf_gain_db": 1.8,
            "mid_freq_hz": 4800.0,
            "mid_gain_db": 2.0,
            "high_shelf_gain_db": 1.5,
            "bypass": False
        },
        "crosstalk_db": -70.0,
        "output_gain_db": 0.0
    },
    "vocal_channel": {
        "name": "Lead Vocal Console Channel Strip",
        "description": "Pristine vocal channel strip with 70Hz high-pass filter, 1.6kHz body definition, silky 12kHz top air, and smooth leveling compression.",
        "ssl": {
            "threshold_db": -15.0,
            "ratio": 2.0,
            "attack_ms": 3.0,
            "release_sec": 0.3,
            "sidechain_hpf_hz": 185.0,
            "makeup_gain_db": 2.5,
            "dry_wet": 1.0,
            "bypass": False
        },
        "neve": {
            "preamp_drive": 1.3,
            "transformer_warmth": 0.30,
            "hpf_hz": 70.0,
            "low_shelf_hz": 110.0,
            "low_shelf_gain_db": -1.0,
            "mid_freq_hz": 1600.0,
            "mid_gain_db": 1.8,
            "high_shelf_gain_db": 2.5,
            "bypass": False
        },
        "crosstalk_db": -75.0,
        "output_gain_db": 0.0
    },
    "radio_broadcast": {
        "name": "Radio Broadcast Limiting & Density",
        "description": "High-density 10:1 ratio broadcast compression with fast 1ms attack and mid-range forward presence for maximum commercial loudness.",
        "ssl": {
            "threshold_db": -18.0,
            "ratio": 10.0,
            "attack_ms": 1.0,
            "release_sec": 0.3,
            "sidechain_hpf_hz": 90.0,
            "makeup_gain_db": 5.0,
            "dry_wet": 0.90,
            "bypass": False
        },
        "neve": {
            "preamp_drive": 1.4,
            "transformer_warmth": 0.20,
            "hpf_hz": 45.0,
            "low_shelf_hz": 60.0,
            "low_shelf_gain_db": 1.0,
            "mid_freq_hz": 3200.0,
            "mid_gain_db": 2.2,
            "high_shelf_gain_db": 2.0,
            "bypass": False
        },
        "crosstalk_db": -65.0,
        "output_gain_db": 0.0
    },
    "clean_transparent": {
        "name": "Clean Transparent Audiophile Polish",
        "description": "Minimal coloration mastering path: ultra-gentle 1.5:1 ratio compression, wide 30ms attack, Auto release, and subtle 12kHz air sparkle.",
        "ssl": {
            "threshold_db": -10.0,
            "ratio": 1.5,
            "attack_ms": 30.0,
            "release_sec": -1.0,
            "sidechain_hpf_hz": 90.0,
            "makeup_gain_db": 1.0,
            "dry_wet": 1.0,
            "bypass": False
        },
        "neve": {
            "preamp_drive": 1.0,
            "transformer_warmth": 0.05,
            "hpf_hz": 0.0,
            "low_shelf_hz": 35.0,
            "low_shelf_gain_db": 0.5,
            "mid_freq_hz": 3200.0,
            "mid_gain_db": 0.0,
            "high_shelf_gain_db": 1.0,
            "bypass": False
        },
        "crosstalk_db": -80.0,
        "output_gain_db": 0.0
    }
}


def render_console_strip(
    input_path: str,
    output_path: Optional[str] = None,
    preset: str = "master_bus_glue",
    custom_ssl: Optional[Dict[str, Any]] = None,
    custom_neve: Optional[Dict[str, Any]] = None,
    crosstalk_db: float = -65.0,
    analog_noise: bool = False,
    output_gain_db: float = 0.0
) -> Dict[str, Any]:
    """
    Renders input audio through the complete British Class-A Console Channel Strip & SSL G-Comp.
    Exports 24-bit linear PCM WAV master.
    """
    audio, sr = read_audio_stereo(input_path)

    # Load base preset
    p_data = FACTORY_PRESETS.get(preset, FACTORY_PRESETS["master_bus_glue"])
    ssl_dict = dict(p_data.get("ssl", {}))
    neve_dict = dict(p_data.get("neve", {}))

    if custom_ssl:
        ssl_dict.update(custom_ssl)
    if custom_neve:
        neve_dict.update(custom_neve)

    ssl_cfg = SSLBusCompressorConfig(
        threshold_db=float(ssl_dict.get("threshold_db", -14.0)),
        ratio=float(ssl_dict.get("ratio", 2.0)),
        attack_ms=float(ssl_dict.get("attack_ms", 30.0)),
        release_sec=float(ssl_dict.get("release_sec", -1.0)),
        sidechain_hpf_hz=float(ssl_dict.get("sidechain_hpf_hz", 90.0)),
        makeup_gain_db=float(ssl_dict.get("makeup_gain_db", 2.0)),
        dry_wet=float(ssl_dict.get("dry_wet", 1.0)),
        bypass=bool(ssl_dict.get("bypass", False))
    )

    neve_cfg = Neve1073Config(
        preamp_drive=float(neve_dict.get("preamp_drive", 1.25)),
        transformer_warmth=float(neve_dict.get("transformer_warmth", 0.25)),
        hpf_hz=float(neve_dict.get("hpf_hz", 45.0)),
        low_shelf_hz=float(neve_dict.get("low_shelf_hz", 60.0)),
        low_shelf_gain_db=float(neve_dict.get("low_shelf_gain_db", 1.5)),
        mid_freq_hz=float(neve_dict.get("mid_freq_hz", 3200.0)),
        mid_gain_db=float(neve_dict.get("mid_gain_db", 1.0)),
        high_shelf_gain_db=float(neve_dict.get("high_shelf_gain_db", 1.5)),
        bypass=bool(neve_dict.get("bypass", False))
    )

    # 1. Neve 1073 Preamp & Inductor EQ Stage
    staged = process_neve_1073(audio, neve_cfg, sr)

    # 2. SSL 4000 G-Master Bus Compressor Stage
    compressed, comp_telemetry = process_ssl_bus_compressor(staged, ssl_cfg, sr)

    # 3. Analog Console Crosstalk (frequency-shaped channel inter-leakage)
    if crosstalk_db < -30.0:
        leak_coeff = 10.0 ** (crosstalk_db / 20.0)
        b_xtalk, a_xtalk = make_peaking_coeffs(3500.0, -3.0, 0.5, sr)
        l_leak = apply_biquad_filter(compressed[1:2], b_xtalk, a_xtalk)[0] * leak_coeff
        r_leak = apply_biquad_filter(compressed[0:1], b_xtalk, a_xtalk)[0] * leak_coeff
        compressed[0] += l_leak
        compressed[1] += r_leak

    # 4. Optional Analog Thermal Noise Floor (-90 dBFS)
    if analog_noise:
        noise_level = 10.0 ** (-90.0 / 20.0)
        rng = np.random.RandomState(42)
        noise = rng.normal(0.0, noise_level, compressed.shape).astype(np.float32)
        compressed += noise

    # 5. Output Gain Staging
    if abs(output_gain_db) > 0.01:
        compressed *= (10.0 ** (output_gain_db / 20.0))

    # 6. Master Safety True-Peak Limiter (-0.2 dBFS Ceiling)
    peak_ceiling = 10.0 ** (-0.2 / 20.0)  # ~0.9772
    peak_val = np.max(np.abs(compressed))
    if peak_val > peak_ceiling:
        compressed = (compressed / peak_val) * peak_ceiling

    # Output path setup
    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_console_master.wav"

    write_wav_24bit(output_path, compressed, sr)

    # Metrics
    duration_sec = compressed.shape[1] / float(sr)
    out_peak_db = 20.0 * math.log10(max(1e-6, np.max(np.abs(compressed))))
    out_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(compressed ** 2))))
    crest_factor_db = out_peak_db - out_rms_db

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "preset": preset,
        "preset_name": p_data.get("name", preset),
        "sample_rate": sr,
        "duration_sec": round(duration_sec, 2),
        "channels": 2,
        "bit_depth": 24,
        "peak_db": round(out_peak_db, 2),
        "rms_db": round(out_rms_db, 2),
        "crest_factor_db": round(crest_factor_db, 2),
        "compressor_telemetry": comp_telemetry,
        "neve_summary": {
            "drive": neve_cfg.preamp_drive,
            "warmth": neve_cfg.transformer_warmth,
            "hpf_hz": neve_cfg.hpf_hz,
            "low_shelf": f"{neve_cfg.low_shelf_gain_db:+.1f} dB @ {neve_cfg.low_shelf_hz} Hz",
            "mid_band": f"{neve_cfg.mid_gain_db:+.1f} dB @ {neve_cfg.mid_freq_hz} Hz",
            "high_shelf": f"{neve_cfg.high_shelf_gain_db:+.1f} dB @ 12 kHz",
            "bypass": neve_cfg.bypass
        }
    }


# ---------------------------------------------------------------------------
# Standalone CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sonance Phase 30: British Class-A Console Channel Strip & SSL G-Master Bus Compressor Studio"
    )
    parser.add_argument("input", type=str, help="Path to input audio file")
    parser.add_argument("output", type=str, nargs="?", default=None, help="Path to output 24-bit PCM WAV")
    parser.add_argument(
        "--preset", type=str, default="master_bus_glue",
        choices=list(FACTORY_PRESETS.keys()),
        help="Master factory preset (default: master_bus_glue)"
    )
    parser.add_argument("--threshold", type=float, default=None, help="SSL threshold in dB (-30 to +10)")
    parser.add_argument("--ratio", type=float, default=None, choices=[1.5, 2.0, 4.0, 10.0], help="SSL ratio")
    parser.add_argument("--attack", type=float, default=None, choices=[0.1, 0.3, 1.0, 3.0, 10.0, 30.0], help="SSL attack ms")
    parser.add_argument("--release", type=float, default=None, help="SSL release sec (0.1, 0.3, 0.6, 1.2, or -1 for Auto)")
    parser.add_argument("--hpf", type=float, default=None, help="SSL sidechain HPF cutoff in Hz (0, 60, 90, 120, 185)")
    parser.add_argument("--makeup", type=float, default=None, help="SSL makeup gain in dB (-6 to +18)")
    parser.add_argument("--dry-wet", type=float, default=None, help="SSL dry/wet mix (0.0 to 1.0)")
    parser.add_argument("--drive", type=float, default=None, help="Neve 1073 preamp drive (1.0 to 4.0)")
    parser.add_argument("--warmth", type=float, default=None, help="Neve 1073 transformer warmth (0.0 to 1.0)")
    parser.add_argument("--high-shelf", type=float, default=None, help="Neve 1073 12kHz high shelf gain in dB")
    parser.add_argument("--low-shelf", type=float, default=None, help="Neve 1073 low shelf gain in dB")
    parser.add_argument("--mid-gain", type=float, default=None, help="Neve 1073 mid band gain in dB")
    parser.add_argument("--crosstalk", type=float, default=-65.0, help="Analog console crosstalk in dB (default: -65)")
    parser.add_argument("--noise", action="store_true", help="Enable subtle analog console noise floor (-90 dBFS)")
    parser.add_argument("--gain", type=float, default=0.0, help="Master output gain in dB")

    args = parser.parse_args()

    custom_ssl = {}
    if args.threshold is not None:
        custom_ssl["threshold_db"] = args.threshold
    if args.ratio is not None:
        custom_ssl["ratio"] = args.ratio
    if args.attack is not None:
        custom_ssl["attack_ms"] = args.attack
    if args.release is not None:
        custom_ssl["release_sec"] = args.release
    if args.hpf is not None:
        custom_ssl["sidechain_hpf_hz"] = args.hpf
    if args.makeup is not None:
        custom_ssl["makeup_gain_db"] = args.makeup
    if args.dry_wet is not None:
        custom_ssl["dry_wet"] = args.dry_wet

    custom_neve = {}
    if args.drive is not None:
        custom_neve["preamp_drive"] = args.drive
    if args.warmth is not None:
        custom_neve["transformer_warmth"] = args.warmth
    if args.high_shelf is not None:
        custom_neve["high_shelf_gain_db"] = args.high_shelf
    if args.low_shelf is not None:
        custom_neve["low_shelf_gain_db"] = args.low_shelf
    if args.mid_gain is not None:
        custom_neve["mid_gain_db"] = args.mid_gain

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.0.0")
    print("  Phase 30: British Class-A Console Channel Strip & SSL G-Master Bus Studio")
    print("=" * 70)
    print(f"[*] Input File     : {args.input}")
    print(f"[*] Master Preset  : {args.preset} ({FACTORY_PRESETS.get(args.preset, {}).get('name', '')})")

    res = render_console_strip(
        input_path=args.input,
        output_path=args.output,
        preset=args.preset,
        custom_ssl=custom_ssl or None,
        custom_neve=custom_neve or None,
        crosstalk_db=args.crosstalk,
        analog_noise=args.noise,
        output_gain_db=args.gain
    )

    t = res["compressor_telemetry"]
    n = res["neve_summary"]

    print("\n[+] Mastering Results:")
    print(f"    - Output Path       : {res['output_path']}")
    print(f"    - Format            : 24-bit Linear PCM WAV @ {res['sample_rate']} Hz")
    print(f"    - Duration          : {res['duration_sec']}s")
    print(f"    - Peak Level        : {res['peak_db']} dBFS")
    print(f"    - RMS Level         : {res['rms_db']} dBFS (Crest Factor: {res['crest_factor_db']} dB)")
    print(f"    - Max Gain Reduction: -{t['max_gain_reduction_db']:.2f} dB (Avg: -{t['avg_gain_reduction_db']:.2f} dB)")
    print(f"    - SSL Bus Settings  : Ratio {t['ratio']}:1 | Attack {t['attack_ms']}ms | Release {t['release']} | Makeup +{t['makeup_db']}dB")
    print(f"    - Neve 1073 Preamp  : Drive {n['drive']}x | Low {n['low_shelf']} | Mid {n['mid_band']} | High {n['high_shelf']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
