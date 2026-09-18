"""
subharmonic_bass.py - Psychoacoustic Subharmonic Bass Synthesizer & Missing Fundamental Exciter Studio
Part of Sonance (Unified Audiophile Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Phase 32 Milestone:
- Dual-Band Subharmonic Synthesizer (dbx 120XP physical modeling):
  * Divides fundamental bass frequencies by 2 (one octave down) via zero-crossing phase tracking.
  * Independent dual-band synthesis: 24-36 Hz (Subterranean rumble) and 36-56 Hz (Kick punch).
- MaxxBass Psychoacoustic Missing Fundamental Exciter:
  * Generates 2nd, 3rd, and 4th harmonic series of low frequencies using Chebyshev wave-shaping.
  * Exploits the auditory cortex missing fundamental psychoacoustic phenomenon to deliver deep perceived bass on small speakers and headphones.
- Analog Low-End Tube Saturation:
  * Asymmetrical warm transformer and tube saturation for rich low-end character.
- Subsonic High-Pass Filter & Elliptical Monomaker:
  * 4th-order Butterworth subsonic cleanup (20-35 Hz) preventing inaudible speaker excursion.
  * Elliptical monomaker below 80-140 Hz ensuring club system mono punch and vinyl compliance.
- True-Peak Master Limiter & 24-bit PCM WAV Export.
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
# Biquad Filter Design & Processing (Direct Form II)
# ---------------------------------------------------------------------------

def design_biquad(filter_type: str, f0: float, sr: int, q: float = 0.7071, gain_db: float = 0.0) -> Tuple[float, float, float, float, float]:
    """Designs digital biquad filter coefficients (b0, b1, b2, a1, a2) normalized by a0."""
    w0 = 2.0 * math.pi * max(10.0, min(f0, sr * 0.45)) / sr
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / (2.0 * max(0.01, q))

    if filter_type == "lowpass":
        b0 = (1.0 - cos_w0) / 2.0
        b1 = 1.0 - cos_w0
        b2 = (1.0 - cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
    elif filter_type == "highpass":
        b0 = (1.0 + cos_w0) / 2.0
        b1 = -(1.0 + cos_w0)
        b2 = (1.0 + cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
    elif filter_type == "bandpass":
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
    else:
        return 1.0, 0.0, 0.0, 0.0, 0.0

    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def apply_biquad(sig: np.ndarray, b0: float, b1: float, b2: float, a1: float, a2: float) -> np.ndarray:
    """Applies biquad IIR filter using difference equation."""
    out = np.zeros_like(sig)
    y1, y2 = 0.0, 0.0
    x1, x2 = 0.0, 0.0
    for n in range(len(sig)):
        x0 = sig[n]
        y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out[n] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return out


def apply_butterworth_4th_hp(sig: np.ndarray, f0: float, sr: int) -> np.ndarray:
    """Cascaded 4th-order (24 dB/oct) Butterworth high-pass filter."""
    b0_1, b1_1, b2_1, a1_1, a2_1 = design_biquad("highpass", f0, sr, q=0.5412)
    b0_2, b1_2, b2_2, a1_2, a2_2 = design_biquad("highpass", f0, sr, q=1.3065)
    s1 = apply_biquad(sig, b0_1, b1_1, b2_1, a1_1, a2_1)
    return apply_biquad(s1, b0_2, b1_2, b2_2, a1_2, a2_2)


def apply_butterworth_4th_lp(sig: np.ndarray, f0: float, sr: int) -> np.ndarray:
    """Cascaded 4th-order (24 dB/oct) Butterworth low-pass filter."""
    b0_1, b1_1, b2_1, a1_1, a2_1 = design_biquad("lowpass", f0, sr, q=0.5412)
    b0_2, b1_2, b2_2, a1_2, a2_2 = design_biquad("lowpass", f0, sr, q=1.3065)
    s1 = apply_biquad(sig, b0_1, b1_1, b2_1, a1_1, a2_1)
    return apply_biquad(s1, b0_2, b1_2, b2_2, a1_2, a2_2)


# ---------------------------------------------------------------------------
# Core Subharmonic Synthesizer (dbx 120XP Physical Model)
# ---------------------------------------------------------------------------

def synthesize_subharmonic_octave(
    mono_bass: np.ndarray,
    sr: int,
    band_low_hz: float,
    band_high_hz: float,
    drive_gain: float = 1.0
) -> np.ndarray:
    """Synthesizes a subharmonic one octave below the input signal in a specified band."""
    center_f = (band_low_hz + band_high_hz)
    bw = (band_high_hz - band_low_hz) * 2.0
    q = max(0.5, center_f / max(10.0, bw))

    b0, b1, b2, a1, a2 = design_biquad("bandpass", center_f, sr, q=q)
    trigger = apply_biquad(mono_bass, b0, b1, b2, a1, a2)

    rectified = np.abs(trigger)
    alpha_att = math.exp(-1.0 / (sr * 0.005))
    alpha_rel = math.exp(-1.0 / (sr * 0.050))

    envelope = np.zeros_like(rectified)
    env = 0.0
    for n in range(len(rectified)):
        val = rectified[n]
        if val > env:
            env = val + alpha_att * (env - val)
        else:
            env = val + alpha_rel * (env - val)
        envelope[n] = env

    sub_wave = np.zeros_like(trigger)
    state = 1.0
    phase = 0.0

    period_samples = sr / max(20.0, center_f)
    phase_inc = (2.0 * math.pi) / (period_samples * 2.0)

    prev_val = trigger[0]
    for n in range(1, len(trigger)):
        curr_val = trigger[n]
        if prev_val <= 0.0 and curr_val > 0.0:
            state = -state

        phase += phase_inc
        if phase >= 2.0 * math.pi:
            phase -= 2.0 * math.pi

        sub_wave[n] = math.sin(phase) * state
        prev_val = curr_val

    sub_signal = sub_wave * envelope * drive_gain
    sub_lp = apply_butterworth_4th_lp(sub_signal, band_high_hz * 1.15, sr)
    return sub_lp


# ---------------------------------------------------------------------------
# MaxxBass Psychoacoustic Missing Fundamental Generator
# ---------------------------------------------------------------------------

def generate_missing_fundamental_harmonics(
    mono_bass: np.ndarray,
    sr: int,
    intensity: float = 1.0,
    hpf_cutoff_hz: float = 50.0
) -> np.ndarray:
    """Synthesizes 2nd, 3rd, and 4th order harmonics using Chebyshev wave-shaping."""
    b0_lp, b1_lp, b2_lp, a1_lp, a2_lp = design_biquad("lowpass", 110.0, sr, q=0.7071)
    b0_hp, b1_hp, b2_hp, a1_hp, a2_hp = design_biquad("highpass", 35.0, sr, q=0.7071)
    fund = apply_biquad(mono_bass, b0_lp, b1_lp, b2_lp, a1_lp, a2_lp)
    fund = apply_biquad(fund, b0_hp, b1_hp, b2_hp, a1_hp, a2_hp)

    peak = np.max(np.abs(fund))
    if peak > 1e-6:
        x = fund / peak
    else:
        return np.zeros_like(mono_bass)

    h2 = (2.0 * (x ** 2) - 1.0)
    h3 = (4.0 * (x ** 3) - 3.0 * x)
    h4 = (8.0 * (x ** 4) - 8.0 * (x ** 2) + 1.0)

    harmonics = (0.55 * h2 + 0.30 * h3 + 0.15 * h4) * peak * intensity

    b0_hpf, b1_hpf, b2_hpf, a1_hpf, a2_hpf = design_biquad("highpass", hpf_cutoff_hz, sr, q=0.7071)
    harmonics_filtered = apply_biquad(harmonics, b0_hpf, b1_hpf, b2_hpf, a1_hpf, a2_hpf)

    b0_harm_lp, b1_harm_lp, b2_harm_lp, a1_harm_lp, a2_harm_lp = design_biquad("lowpass", 320.0, sr, q=0.7071)
    harmonics_shaped = apply_biquad(harmonics_filtered, b0_harm_lp, b1_harm_lp, b2_harm_lp, a1_harm_lp, a2_harm_lp)

    return harmonics_shaped


# ---------------------------------------------------------------------------
# Analog Tube Drive & Elliptical Monomaker
# ---------------------------------------------------------------------------

def apply_analog_tube_drive(sig: np.ndarray, drive: float = 1.0) -> np.ndarray:
    """Applies asymmetric soft-clipping tube warmth to low frequencies."""
    if drive <= 1.01:
        return sig
    d = max(1.0, drive)
    x = sig * d
    sat = np.tanh(x) / (1.0 + 0.15 * (x ** 2))
    return sat / math.sqrt(d)


def apply_elliptical_monomaker(audio: np.ndarray, sr: int, monomaker_hz: float = 100.0) -> np.ndarray:
    """Converts frequencies below monomaker_hz to pure mono while preserving stereo above."""
    if monomaker_hz <= 20.0:
        return audio

    mid = 0.5 * (audio[0] + audio[1])
    side = 0.5 * (audio[0] - audio[1])

    b0, b1, b2, a1, a2 = design_biquad("highpass", monomaker_hz, sr, q=0.7071)
    filtered_side = apply_biquad(side, b0, b1, b2, a1, a2)

    out = np.zeros_like(audio)
    out[0] = mid + filtered_side
    out[1] = mid - filtered_side
    return out


# ---------------------------------------------------------------------------
# Factory Presets
# ---------------------------------------------------------------------------

FACTORY_PRESETS = {
    "club_sub_boom": {
        "name": "Club Sub-Bass Boom",
        "description": "Massive subterranean 24-36Hz rumble with tight monomaker for EDM, Hip-Hop, and festival sound systems.",
        "sub_24_36_gain": 0.85,
        "sub_36_56_gain": 0.50,
        "maxxbass_intensity": 0.35,
        "maxxbass_cutoff_hz": 55.0,
        "tube_drive": 1.25,
        "subsonic_hpf_hz": 22.0,
        "monomaker_hz": 120.0,
        "dry_wet": 0.90
    },
    "punchy_kick_thump": {
        "name": "Punchy Kick Thump",
        "description": "Reinforces 36-56Hz fundamental kick punch and chest-thumping impact for Rock, Pop, and modern masters.",
        "sub_24_36_gain": 0.30,
        "sub_36_56_gain": 0.80,
        "maxxbass_intensity": 0.45,
        "maxxbass_cutoff_hz": 65.0,
        "tube_drive": 1.35,
        "subsonic_hpf_hz": 28.0,
        "monomaker_hz": 100.0,
        "dry_wet": 0.85
    },
    "earbuds_maxxbass": {
        "name": "Earbuds & Mobile MaxxBass",
        "description": "High-intensity psychoacoustic missing fundamental harmonics allowing deep bass to thump on phones, laptops, and AirPods.",
        "sub_24_36_gain": 0.15,
        "sub_36_56_gain": 0.35,
        "maxxbass_intensity": 0.95,
        "maxxbass_cutoff_hz": 75.0,
        "tube_drive": 1.15,
        "subsonic_hpf_hz": 32.0,
        "monomaker_hz": 90.0,
        "dry_wet": 0.90
    },
    "audiophile_warm_bass": {
        "name": "Audiophile Warm Bass",
        "description": "Subtle natural octave extension with vintage tube warmth for Jazz, Acoustic, and Vinyl mastering.",
        "sub_24_36_gain": 0.35,
        "sub_36_56_gain": 0.40,
        "maxxbass_intensity": 0.25,
        "maxxbass_cutoff_hz": 50.0,
        "tube_drive": 1.40,
        "subsonic_hpf_hz": 20.0,
        "monomaker_hz": 80.0,
        "dry_wet": 0.75
    },
    "sub_rumble_cleanup": {
        "name": "Subsonic Rumble Clean-Up",
        "description": "Removes inaudible woofer excursion and focuses low-end punch without adding synthetic subharmonics.",
        "sub_24_36_gain": 0.0,
        "sub_36_56_gain": 0.0,
        "maxxbass_intensity": 0.0,
        "maxxbass_cutoff_hz": 60.0,
        "tube_drive": 1.0,
        "subsonic_hpf_hz": 30.0,
        "monomaker_hz": 110.0,
        "dry_wet": 1.0
    }
}


# ---------------------------------------------------------------------------
# Master Rendering Controller
# ---------------------------------------------------------------------------

def render_subharmonic_bass(
    input_path: str,
    output_path: Optional[str] = None,
    preset: str = "club_sub_boom",
    sub_24_36_gain: Optional[float] = None,
    sub_36_56_gain: Optional[float] = None,
    maxxbass_intensity: Optional[float] = None,
    maxxbass_cutoff_hz: Optional[float] = None,
    tube_drive: Optional[float] = None,
    subsonic_hpf_hz: Optional[float] = None,
    monomaker_hz: Optional[float] = None,
    dry_wet: Optional[float] = None,
    output_gain_db: float = 0.0
) -> Dict[str, Any]:
    """Renders input audio through the Psychoacoustic Subharmonic Bass Synthesizer & Missing Fundamental Engine."""
    audio, sr = read_audio_stereo(input_path)

    p = FACTORY_PRESETS.get(preset, FACTORY_PRESETS["club_sub_boom"])
    sub_1_gain = p["sub_24_36_gain"] if sub_24_36_gain is None else float(sub_24_36_gain)
    sub_2_gain = p["sub_36_56_gain"] if sub_36_56_gain is None else float(sub_36_56_gain)
    mb_intensity = p["maxxbass_intensity"] if maxxbass_intensity is None else float(maxxbass_intensity)
    mb_cutoff = p["maxxbass_cutoff_hz"] if maxxbass_cutoff_hz is None else float(maxxbass_cutoff_hz)
    t_drive = p["tube_drive"] if tube_drive is None else float(tube_drive)
    sub_hpf = p["subsonic_hpf_hz"] if subsonic_hpf_hz is None else float(subsonic_hpf_hz)
    mono_cutoff = p["monomaker_hz"] if monomaker_hz is None else float(monomaker_hz)
    mix = p["dry_wet"] if dry_wet is None else float(dry_wet)

    in_peak_db = 20.0 * math.log10(max(1e-6, np.max(np.abs(audio))))
    in_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(audio ** 2))))

    mono_bass = 0.5 * (audio[0] + audio[1])

    sub_1 = np.zeros_like(mono_bass)
    if sub_1_gain > 0.01:
        sub_1 = synthesize_subharmonic_octave(mono_bass, sr, 24.0, 36.0, drive_gain=sub_1_gain)

    sub_2 = np.zeros_like(mono_bass)
    if sub_2_gain > 0.01:
        sub_2 = synthesize_subharmonic_octave(mono_bass, sr, 36.0, 56.0, drive_gain=sub_2_gain)

    mb_harmonics = np.zeros_like(mono_bass)
    if mb_intensity > 0.01:
        mb_harmonics = generate_missing_fundamental_harmonics(mono_bass, sr, intensity=mb_intensity, hpf_cutoff_hz=mb_cutoff)

    synthetic_low = sub_1 + sub_2 + mb_harmonics

    if t_drive > 1.01:
        synthetic_low = apply_analog_tube_drive(synthetic_low, drive=t_drive)

    if sub_hpf > 10.0:
        audio_l = apply_butterworth_4th_hp(audio[0], sub_hpf, sr)
        audio_r = apply_butterworth_4th_hp(audio[1], sub_hpf, sr)
        audio = np.vstack([audio_l, audio_r])
        synthetic_low = apply_butterworth_4th_hp(synthetic_low, sub_hpf, sr)

    processed = np.zeros_like(audio)
    processed[0] = audio[0] + synthetic_low
    processed[1] = audio[1] + synthetic_low

    if mono_cutoff > 20.0:
        processed = apply_elliptical_monomaker(processed, sr, monomaker_hz=mono_cutoff)

    mix = max(0.0, min(1.0, mix))
    out_audio = (1.0 - mix) * audio + mix * processed

    if abs(output_gain_db) > 0.01:
        out_audio *= (10.0 ** (output_gain_db / 20.0))

    peak = np.max(np.abs(out_audio))
    ceiling = 10.0 ** (-0.2 / 20.0)
    if peak > ceiling:
        out_audio = (out_audio / peak) * ceiling

    out_peak_db = 20.0 * math.log10(max(1e-6, np.max(np.abs(out_audio))))
    out_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(out_audio ** 2))))
    duration_sec = out_audio.shape[1] / float(sr)

    sub1_rms = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(sub_1 ** 2)))) if sub_1_gain > 0.01 else -99.0
    sub2_rms = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(sub_2 ** 2)))) if sub_2_gain > 0.01 else -99.0
    mb_rms = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(mb_harmonics ** 2)))) if mb_intensity > 0.01 else -99.0

    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_subharmonic_bass.wav"

    write_audio_stereo_24bit(output_path, out_audio, sr)

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "preset": preset,
        "preset_name": p.get("name", preset),
        "sample_rate": sr,
        "duration_sec": round(duration_sec, 2),
        "in_peak_dbfs": round(in_peak_db, 2),
        "in_rms_dbfs": round(in_rms_db, 2),
        "out_peak_dbfs": round(out_peak_db, 2),
        "out_rms_dbfs": round(out_rms_db, 2),
        "sub_energy_gain_db": round(out_rms_db - in_rms_db, 2),
        "sub_1_rms_dbfs": round(sub1_rms, 2),
        "sub_2_rms_dbfs": round(sub2_rms, 2),
        "maxxbass_rms_dbfs": round(mb_rms, 2),
        "settings": {
            "sub_24_36_gain": sub_1_gain,
            "sub_36_56_gain": sub_2_gain,
            "maxxbass_intensity": mb_intensity,
            "maxxbass_cutoff_hz": mb_cutoff,
            "tube_drive": t_drive,
            "subsonic_hpf_hz": sub_hpf,
            "monomaker_hz": mono_cutoff,
            "dry_wet": mix,
            "output_gain_db": output_gain_db
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Sonance Phase 32: Psychoacoustic Subharmonic Bass Synthesizer & Missing Fundamental Studio"
    )
    parser.add_argument("input", type=str, help="Path to input audio file")
    parser.add_argument("output", type=str, nargs="?", default=None, help="Path to output 24-bit PCM WAV")
    parser.add_argument(
        "--preset", type=str, default="club_sub_boom",
        choices=list(FACTORY_PRESETS.keys()),
        help="Master preset (default: club_sub_boom)"
    )
    parser.add_argument("--sub-24-36", type=float, default=None, help="24-36 Hz subharmonic gain (0.0 to 1.5)")
    parser.add_argument("--sub-36-56", type=float, default=None, help="36-56 Hz subharmonic gain (0.0 to 1.5)")
    parser.add_argument("--maxxbass", type=float, default=None, help="MaxxBass missing fundamental intensity (0.0 to 1.5)")
    parser.add_argument("--maxxbass-cutoff", type=float, default=None, help="MaxxBass HPF cutoff Hz (40 to 100)")
    parser.add_argument("--drive", type=float, default=None, help="Analog tube saturation drive (1.0 to 3.0)")
    parser.add_argument("--subsonic-hpf", type=float, default=None, help="Subsonic rumble HPF Hz (0, 20, 25, 30, 35)")
    parser.add_argument("--monomaker", type=float, default=None, help="Elliptical monomaker cutoff Hz (0 to 180)")
    parser.add_argument("--mix", type=float, default=None, help="Dry / wet mix (0.0 to 1.0)")
    parser.add_argument("--gain", type=float, default=0.0, help="Output master makeup gain in dB")

    args = parser.parse_args()

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.2.0")
    print("  Phase 32: Psychoacoustic Subharmonic Bass & Missing Fundamental Studio")
    print("=" * 70)
    print(f"[*] Input File       : {args.input}")
    print(f"[*] Preset Selected  : {args.preset.upper()}")

    res = render_subharmonic_bass(
        input_path=args.input,
        output_path=args.output,
        preset=args.preset,
        sub_24_36_gain=args.sub_24_36,
        sub_36_56_gain=args.sub_36_56,
        maxxbass_intensity=args.maxxbass,
        maxxbass_cutoff_hz=args.maxxbass_cutoff,
        tube_drive=args.drive,
        subsonic_hpf_hz=args.subsonic_hpf,
        monomaker_hz=args.monomaker,
        dry_wet=args.mix,
        output_gain_db=args.gain
    )

    s = res["settings"]
    print("\n[+] Subharmonic Bass Mastering Report:")
    print(f"    - Output Master  : {res['output_path']}")
    print(f"    - Format         : 24-bit Linear PCM WAV @ {res['sample_rate']} Hz ({res['duration_sec']}s)")
    print(f"    - In Peak / RMS  : {res['in_peak_dbfs']} dBFS / {res['in_rms_dbfs']} dBFS")
    print(f"    - Out Peak / RMS : {res['out_peak_dbfs']} dBFS / {res['out_rms_dbfs']} dBFS (Gain: {res['sub_energy_gain_db']:+0.2f} dB)")
    print(f"    - Sub 24-36 Hz   : Level {s['sub_24_36_gain']:.2f} (RMS: {res['sub_1_rms_dbfs']} dBFS)")
    print(f"    - Sub 36-56 Hz   : Level {s['sub_36_56_gain']:.2f} (RMS: {res['sub_2_rms_dbfs']} dBFS)")
    print(f"    - MaxxBass Synth : Intensity {s['maxxbass_intensity']:.2f} (Cutoff: {s['maxxbass_cutoff_hz']:.0f} Hz, RMS: {res['maxxbass_rms_dbfs']} dBFS)")
    print(f"    - Subsonic HPF   : {s['subsonic_hpf_hz']:.0f} Hz | Monomaker: {s['monomaker_hz']:.0f} Hz | Drive: {s['tube_drive']:.2f}x")
    print("=" * 70)


if __name__ == "__main__":
    main()
