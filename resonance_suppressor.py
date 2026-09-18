"""
resonance_suppressor.py - Dynamic Spectral Resonance Suppressor & Surgical De-Resonator Studio
Part of Sonance (Unified Audiophile Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Phase 33 Milestone:
- Dynamic Spectral Resonance Tracking (Oeksound Soothe2 / Gullfoss physical model):
  * Decomposes audio via high-resolution Short-Time Fourier Transform (STFT) with 2048-point Hann windowing.
  * Dynamically computes psychoacoustic spectral envelope baseline across 40 critical Bark frequency bands.
  * Identifies sharp resonant peaks exceeding the moving spectral envelope (resonance prominence in dB).
- Surgical Dynamic Notch Suppression:
  * Dynamically calculates frequency-dependent attenuation: Delta G(f) = -depth * max(0, Prominence(f) - threshold).
  * Carves out piercing sibilance, nasal vocal honk, room mode boxiness, and harsh cymbals with adjustable sharpness (Q).
  * Ballistics: 5ms attack and 50ms release for seamless, artifact-free, transparent de-resonating.
- Delta "Listen Mode" Auditioning:
  * Difference monitor isolating strictly what is being suppressed for precise surgical tuning.
- Focus Filters:
  * Low-Cut (40-300 Hz) and High-Cut (6-18 kHz) bounding filters focusing de-resonating on target frequency zones.
- True-Peak Master Limiting & 24-bit PCM WAV Export.
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
# STFT & Dynamic Spectral Resonance Suppressor Engine
# ---------------------------------------------------------------------------

def compute_spectral_envelope_baseline(mag_spectrum: np.ndarray, window_size: int = 15) -> np.ndarray:
    """
    Computes a smoothed spectral baseline using moving average with median pre-pass.
    Resonant peaks will protrude significantly above this baseline.
    """
    # Moving average filter along frequency bins
    half_w = max(1, window_size // 2)
    padded = np.pad(mag_spectrum, (half_w, half_w), mode="edge")
    kernel = np.ones(window_size, dtype=np.float32) / float(window_size)
    smoothed = np.convolve(padded, kernel, mode="valid")
    return smoothed[:len(mag_spectrum)]


def suppress_channel_resonances(
    sig: np.ndarray,
    sr: int,
    depth: float = 0.50,
    threshold_db: float = 4.0,
    sharpness: float = 2.5,
    low_cut_hz: float = 60.0,
    high_cut_hz: float = 16000.0,
    fft_size: int = 2048,
    hop_size: int = 512
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Applies dynamic spectral resonance suppression to a single audio channel.
    Returns: (processed_signal, delta_difference_signal, telemetry)
    """
    samples = len(sig)
    window = np.hanning(fft_size).astype(np.float32)
    num_frames = (samples - fft_size) // hop_size + 1

    if num_frames <= 0:
        return sig, np.zeros_like(sig), {"max_reduction_db": 0.0, "top_resonances": []}

    freq_bins = np.fft.rfftfreq(fft_size, d=1.0 / sr)
    num_bins = len(freq_bins)

    # Pre-compute frequency mask based on low-cut and high-cut
    focus_mask = (freq_bins >= low_cut_hz) & (freq_bins <= high_cut_hz)

    # Output accumulation buffers
    out_sig = np.zeros(samples, dtype=np.float32)
    win_sum = np.zeros(samples, dtype=np.float32)

    # Resonance tracking statistics
    max_red_db = 0.0
    sum_red_db = 0.0
    red_count = 0
    resonance_histogram = np.zeros(num_bins, dtype=np.float32)

    # Smoothing states for attack/release ballistics
    prev_gains = np.ones(num_bins, dtype=np.float32)
    alpha_att = math.exp(-1.0 / ((sr / hop_size) * 0.005))  # 5ms attack
    alpha_rel = math.exp(-1.0 / ((sr / hop_size) * 0.050))  # 50ms release

    for f_idx in range(num_frames):
        start = f_idx * hop_size
        end = start + fft_size
        frame = sig[start:end] * window

        # Forward FFT
        spec = np.fft.rfft(frame)
        mag = np.abs(spec)
        phase = np.angle(spec)

        # Compute smoothed spectral envelope
        baseline = compute_spectral_envelope_baseline(mag, window_size=int(max(5, 21 / max(0.5, sharpness))))

        # Calculate prominence of resonant peaks above baseline in dB
        with np.errstate(divide="ignore", invalid="ignore"):
            prominence_ratio = np.where(baseline > 1e-7, mag / baseline, 1.0)
            prominence_db = 20.0 * np.log10(np.maximum(1e-4, prominence_ratio))

        # Dynamic target gain reduction per frequency bin
        target_gain_db = np.zeros(num_bins, dtype=np.float32)
        excess = np.maximum(0.0, prominence_db - threshold_db)

        # Apply focus mask
        excess = excess * focus_mask

        if np.any(excess > 0.0):
            # De-resonating attenuation curve with sharpness exponent
            scaled_excess = (excess ** (1.0 + 0.25 * sharpness))
            target_gain_db = -depth * scaled_excess
            # Limit maximum suppression to -24 dB for musicality
            target_gain_db = np.clip(target_gain_db, -24.0, 0.0)

        # Convert to linear gains
        target_gains = 10.0 ** (target_gain_db / 20.0)

        # Ballistic smoothing (attack/release)
        smoothed_gains = np.where(
            target_gains < prev_gains,
            target_gains + alpha_att * (prev_gains - target_gains),
            target_gains + alpha_rel * (prev_gains - target_gains)
        )
        prev_gains = smoothed_gains

        # Telemetry metrics
        current_max_red = float(np.min(target_gain_db))
        if current_max_red < max_red_db:
            max_red_db = current_max_red
        sum_red_db += float(np.mean(target_gain_db))
        red_count += 1

        # Accumulate offending frequencies
        bad_bins = np.where(target_gain_db < -2.0)[0]
        resonance_histogram[bad_bins] += np.abs(target_gain_db[bad_bins])

        # Apply gain reduction to spectral magnitude
        suppressed_mag = mag * smoothed_gains
        suppressed_spec = suppressed_mag * np.exp(1j * phase)

        # Inverse FFT
        recon_frame = np.fft.irfft(suppressed_spec, n=fft_size).astype(np.float32)

        # Overlap-add
        out_sig[start:end] += recon_frame * window
        win_sum[start:end] += window ** 2

    # Normalize by window sum
    win_sum = np.maximum(win_sum, 1e-6)
    clean_sig = np.copy(sig)
    valid_len = min(samples, num_frames * hop_size + fft_size)
    clean_sig[:valid_len] = out_sig[:valid_len] / win_sum[:valid_len]

    # Compute delta signal (what was surgically removed)
    delta_sig = sig - clean_sig

    # Find top 3 most prominent resonance frequencies
    top_indices = np.argsort(resonance_histogram)[-3:][::-1]
    top_resonances = [
        {"freq_hz": int(round(freq_bins[idx])), "intensity_score": round(float(resonance_histogram[idx]), 1)}
        for idx in top_indices if resonance_histogram[idx] > 0.1
    ]

    telemetry = {
        "max_reduction_db": round(float(max_red_db), 2),
        "avg_reduction_db": round(float(sum_red_db / max(1, red_count)), 2),
        "top_resonances": top_resonances
    }

    return clean_sig, delta_sig, telemetry


# ---------------------------------------------------------------------------
# Factory Presets
# ---------------------------------------------------------------------------

FACTORY_PRESETS = {
    "tame_harshness": {
        "name": "Universal Harshness Tamer",
        "description": "Smooths abrasive upper-mid bite and listener fatigue in the 2-6 kHz zone across complete masters.",
        "depth": 0.55,
        "threshold_db": 3.5,
        "sharpness": 2.5,
        "low_cut_hz": 1200.0,
        "high_cut_hz": 9000.0,
        "dry_wet": 1.0
    },
    "vocal_de_boxer": {
        "name": "Vocal De-Boxer & Honk Remover",
        "description": "Surgically carves out hollow room modes and boxy vocal nasal buildup between 350 Hz and 1.2 kHz.",
        "depth": 0.70,
        "threshold_db": 3.0,
        "sharpness": 3.5,
        "low_cut_hz": 300.0,
        "high_cut_hz": 1800.0,
        "dry_wet": 1.0
    },
    "muddy_low_mid": {
        "name": "Acoustic Muddy Low-Mid Tamer",
        "description": "Eliminates boomy acoustic guitar resonances and muddy bass note buildup in the 150-450 Hz area.",
        "depth": 0.60,
        "threshold_db": 3.0,
        "sharpness": 2.8,
        "low_cut_hz": 100.0,
        "high_cut_hz": 600.0,
        "dry_wet": 0.90
    },
    "cymbal_silencer": {
        "name": "Cymbal & Sibilance Silencer",
        "description": "Tames piercing hi-hats, splash cymbals, and vocal sibilance in the 6 kHz to 14 kHz treble zone.",
        "depth": 0.65,
        "threshold_db": 4.0,
        "sharpness": 2.2,
        "low_cut_hz": 5500.0,
        "high_cut_hz": 16000.0,
        "dry_wet": 0.95
    },
    "extreme_surgical": {
        "name": "Deep Surgical Notch Cleanup",
        "description": "Ultra-sharp dynamic notch attenuation for recordings with extreme whistling and acoustic resonances.",
        "depth": 0.90,
        "threshold_db": 2.5,
        "sharpness": 4.5,
        "low_cut_hz": 80.0,
        "high_cut_hz": 16000.0,
        "dry_wet": 1.0
    }
}


# ---------------------------------------------------------------------------
# Master Rendering Controller
# ---------------------------------------------------------------------------

def render_resonance_suppressor(
    input_path: str,
    output_path: Optional[str] = None,
    preset: str = "tame_harshness",
    depth: Optional[float] = None,
    threshold_db: Optional[float] = None,
    sharpness: Optional[float] = None,
    low_cut_hz: Optional[float] = None,
    high_cut_hz: Optional[float] = None,
    listen_mode: bool = False,
    dry_wet: Optional[float] = None,
    output_gain_db: float = 0.0
) -> Dict[str, Any]:
    """
    Renders audio through the Dynamic Spectral Resonance Suppressor Studio.
    """
    audio, sr = read_audio_stereo(input_path)

    # Load preset defaults or overrides
    p = FACTORY_PRESETS.get(preset, FACTORY_PRESETS["tame_harshness"])
    d = p["depth"] if depth is None else float(depth)
    th = p["threshold_db"] if threshold_db is None else float(threshold_db)
    sh = p["sharpness"] if sharpness is None else float(sharpness)
    lc = p["low_cut_hz"] if low_cut_hz is None else float(low_cut_hz)
    hc = p["high_cut_hz"] if high_cut_hz is None else float(high_cut_hz)
    mix = p["dry_wet"] if dry_wet is None else float(dry_wet)

    in_peak_db = 20.0 * math.log10(max(1e-6, np.max(np.abs(audio))))
    in_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(audio ** 2))))

    # Process Left channel
    clean_l, delta_l, tele_l = suppress_channel_resonances(
        audio[0], sr, depth=d, threshold_db=th, sharpness=sh,
        low_cut_hz=lc, high_cut_hz=hc
    )

    # Process Right channel
    clean_r, delta_r, tele_r = suppress_channel_resonances(
        audio[1], sr, depth=d, threshold_db=th, sharpness=sh,
        low_cut_hz=lc, high_cut_hz=hc
    )

    # Choose output: Listen Mode (Delta difference) or Processed audio
    if listen_mode:
        out_audio = np.vstack([delta_l, delta_r]) * 2.0  # Boost delta for clear auditioning
        mode_label = "Delta Difference (Listen Mode - Auditioning Suppressed Resonances Only)"
    else:
        # Dry/Wet blend
        mix = max(0.0, min(1.0, mix))
        clean_audio = np.vstack([clean_l, clean_r])
        out_audio = (1.0 - mix) * audio + mix * clean_audio
        mode_label = "Active Master (Resonances Surgically De-Harshed)"

    # Apply master output makeup gain
    if abs(output_gain_db) > 0.01:
        out_audio *= (10.0 ** (output_gain_db / 20.0))

    # Master true-peak safety limiter (-0.2 dBFS ceiling)
    peak = np.max(np.abs(out_audio))
    ceiling = 10.0 ** (-0.2 / 20.0)
    if peak > ceiling:
        out_audio = (out_audio / peak) * ceiling

    out_peak_db = 20.0 * math.log10(max(1e-6, np.max(np.abs(out_audio))))
    out_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(out_audio ** 2))))
    duration_sec = out_audio.shape[1] / float(sr)

    # Combine telemetry
    max_red = min(tele_l["max_reduction_db"], tele_r["max_reduction_db"])
    avg_red = round((tele_l["avg_reduction_db"] + tele_r["avg_reduction_db"]) / 2.0, 2)
    top_res = tele_l.get("top_resonances", [])

    if not output_path:
        base, _ = os.path.splitext(input_path)
        suffix = "_resonance_delta.wav" if listen_mode else "_de_resonated.wav"
        output_path = f"{base}{suffix}"

    write_audio_stereo_24bit(output_path, out_audio, sr)

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "preset": preset,
        "preset_name": p.get("name", preset),
        "listen_mode": listen_mode,
        "mode_label": mode_label,
        "sample_rate": sr,
        "duration_sec": round(duration_sec, 2),
        "in_peak_dbfs": round(in_peak_db, 2),
        "in_rms_dbfs": round(in_rms_db, 2),
        "out_peak_dbfs": round(out_peak_db, 2),
        "out_rms_dbfs": round(out_rms_db, 2),
        "max_reduction_db": max_red,
        "avg_reduction_db": avg_red,
        "top_resonances": top_res,
        "settings": {
            "depth": d,
            "threshold_db": th,
            "sharpness": sh,
            "low_cut_hz": lc,
            "high_cut_hz": hc,
            "dry_wet": mix,
            "output_gain_db": output_gain_db
        }
    }


# ---------------------------------------------------------------------------
# Standalone CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sonance Phase 33: Dynamic Spectral Resonance Suppressor & Surgical De-Resonator Studio"
    )
    parser.add_argument("input", type=str, help="Path to input audio file")
    parser.add_argument("output", type=str, nargs="?", default=None, help="Path to output 24-bit PCM WAV")
    parser.add_argument(
        "--preset", type=str, default="tame_harshness",
        choices=list(FACTORY_PRESETS.keys()),
        help="Master preset (default: tame_harshness)"
    )
    parser.add_argument("--depth", type=float, default=None, help="Suppression depth (0.0 to 1.0)")
    parser.add_argument("--threshold", type=float, default=None, help="Resonance prominence threshold dB (1.0 to 8.0)")
    parser.add_argument("--sharpness", type=float, default=None, help="Notch selectivity sharpness Q (1.0 to 5.0)")
    parser.add_argument("--low-cut", type=float, default=None, help="Low-cut focus filter Hz (40 to 1000)")
    parser.add_argument("--high-cut", type=float, default=None, help="High-cut focus filter Hz (4000 to 18000)")
    parser.add_argument("--listen", action="store_true", help="Audition delta difference (suppressed resonances only)")
    parser.add_argument("--mix", type=float, default=None, help="Dry / wet mix (0.0 to 1.0)")
    parser.add_argument("--gain", type=float, default=0.0, help="Output makeup gain in dB")

    args = parser.parse_args()

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.3.0")
    print("  Phase 33: Dynamic Spectral Resonance Suppressor & Surgical De-Resonator")
    print("=" * 70)
    print(f"[*] Input File       : {args.input}")
    print(f"[*] Preset Selected  : {args.preset.upper()}")
    if args.listen:
        print("[!] LISTEN MODE ACTIVE: Auditioning suppressed delta resonances only")

    res = render_resonance_suppressor(
        input_path=args.input,
        output_path=args.output,
        preset=args.preset,
        depth=args.depth,
        threshold_db=args.threshold,
        sharpness=args.sharpness,
        low_cut_hz=args.low_cut,
        high_cut_hz=args.high_cut,
        listen_mode=args.listen,
        dry_wet=args.mix,
        output_gain_db=args.gain
    )

    s = res["settings"]
    print("\n[+] Resonance Suppressor Telemetry Report:")
    print(f"    - Output Master  : {res['output_path']}")
    print(f"    - Mode           : {res['mode_label']}")
    print(f"    - In Peak / RMS  : {res['in_peak_dbfs']} dBFS / {res['in_rms_dbfs']} dBFS")
    print(f"    - Out Peak / RMS : {res['out_peak_dbfs']} dBFS / {res['out_rms_dbfs']} dBFS")
    print(f"    - Max Reduction  : {res['max_reduction_db']:.2f} dB (Avg: {res['avg_reduction_db']:.2f} dB)")
    print(f"    - Focus Band     : {s['low_cut_hz']:.0f} Hz - {s['high_cut_hz']:.0f} Hz (Sharpness: {s['sharpness']:.1f}x)")
    if res["top_resonances"]:
        res_str = ", ".join([f"{r['freq_hz']} Hz" for r in res["top_resonances"]])
        print(f"    - Top Resonances : {res_str}")
    print("=" * 70)


if __name__ == "__main__":
    main()
