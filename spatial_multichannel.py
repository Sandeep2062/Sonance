"""
Sonance - Dolby Atmos 7.1.4 Bed Spatializer & Multichannel Audio Renderer Studio
Phase 29 Studio Audio Architecture

Renders stereo music tracks into immersive 7.1.4 spatial audio beds:
- 7 Bed Channels: Left, Right, Center, LFE (Subwoofer), L Side Surround, R Side Surround, L Rear Surround, R Rear Surround
- 4 Height / Ceiling Channels: Top Front Left (TFL), Top Front Right (TFR), Top Rear Left (TRL), Top Rear Right (TRR)
Provides both discrete 12-channel 24-bit PCM WAV export and binaural 7.1.4 headphone downmix.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import math
import wave
import time
import struct
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

APP_VERSION = "2.9.0"

# Standard 7.1.4 Speaker Azimuth (degrees, 0=front, 90=right, -90=left, 180=rear) & Elevation (degrees, 0=ear level, +45=overhead)
SPEAKERS_714 = {
    "L":   {"name": "Left Front",           "azimuth": -30.0, "elevation":  0.0, "is_height": False, "is_lfe": False},
    "R":   {"name": "Right Front",          "azimuth":  30.0, "elevation":  0.0, "is_height": False, "is_lfe": False},
    "C":   {"name": "Center",               "azimuth":   0.0, "elevation":  0.0, "is_height": False, "is_lfe": False},
    "LFE": {"name": "Low Frequency Effects","azimuth":   0.0, "elevation":  0.0, "is_height": False, "is_lfe": True},
    "Lss": {"name": "Left Side Surround",   "azimuth": -90.0, "elevation":  0.0, "is_height": False, "is_lfe": False},
    "Rss": {"name": "Right Side Surround",  "azimuth":  90.0, "elevation":  0.0, "is_height": False, "is_lfe": False},
    "Lsr": {"name": "Left Rear Surround",   "azimuth": -140.0,"elevation":  0.0, "is_height": False, "is_lfe": False},
    "Rsr": {"name": "Right Rear Surround",  "azimuth":  140.0,"elevation":  0.0, "is_height": False, "is_lfe": False},
    "TFL": {"name": "Top Front Left",       "azimuth": -45.0, "elevation": 45.0, "is_height": True,  "is_lfe": False},
    "TFR": {"name": "Top Front Right",      "azimuth":  45.0, "elevation": 45.0, "is_height": True,  "is_lfe": False},
    "TRL": {"name": "Top Rear Left",        "azimuth": -135.0,"elevation": 45.0, "is_height": True,  "is_lfe": False},
    "TRR": {"name": "Top Rear Right",       "azimuth":  135.0,"elevation": 45.0, "is_height": True,  "is_lfe": False},
}


def read_audio_file(file_path: str) -> Tuple[np.ndarray, int, int]:
    """Reads audio file into float32 array in [-1.0, 1.0], returning (samples, sample_rate, bit_depth)."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    is_wav = file_path.lower().endswith(".wav")
    temp_wav = None

    if not is_wav:
        import subprocess
        import tempfile
        fd, temp_wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        cmd = ["ffmpeg", "-y", "-i", file_path, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", temp_wav]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            target_path = temp_wav
        except Exception:
            if os.path.exists(temp_wav):
                os.unlink(temp_wav)
            raise RuntimeError("FFmpeg required to decode non-WAV audio formats.")
    else:
        target_path = file_path

    try:
        with wave.open(target_path, "rb") as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)

            if sample_width == 1:
                data = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            elif sample_width == 2:
                data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            elif sample_width == 3:
                raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
                raw_reshaped = raw_arr.reshape(-1, 3)
                padded = np.column_stack([np.zeros(len(raw_reshaped), dtype=np.uint8), raw_reshaped])
                data = padded.view(np.int32).flatten().astype(np.float32) / 2147483648.0
            elif sample_width == 4:
                data = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                raise ValueError(f"Unsupported sample width: {sample_width} bytes")

            if num_channels == 1:
                data = np.column_stack([data, data])
            else:
                data = data.reshape(-1, num_channels)
                if num_channels > 2:
                    data = data[:, :2]

            bit_depth = sample_width * 8
            return data, sample_rate, bit_depth
    finally:
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.unlink(temp_wav)
            except Exception:
                pass


def write_multichannel_wav(file_path: str, channels_data: List[np.ndarray], sample_rate: int, bit_depth: int = 24):
    """
    Writes multi-channel PCM WAV file (e.g. 12 channels for 7.1.4, 8 for 7.1, 6 for 5.1, or 2 for stereo).
    """
    num_channels = len(channels_data)
    n_frames = len(channels_data[0])

    # Interleave channel buffers
    stacked = np.column_stack(channels_data)
    stacked = np.clip(stacked, -1.0, 1.0)

    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setframerate(sample_rate)

        if bit_depth == 16:
            wf.setsampwidth(2)
            scaled = (stacked * 32767.0).astype(np.int16)
            wf.writeframes(scaled.tobytes())
        elif bit_depth == 24:
            wf.setsampwidth(3)
            scaled = (stacked * 8388607.0).astype(np.int32)
            raw_bytes = scaled.tobytes()
            byte_arr = bytearray(n_frames * num_channels * 3)
            int_bytes = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(-1, 4)
            byte_arr[0::3] = int_bytes[:, 0].tobytes()
            byte_arr[1::3] = int_bytes[:, 1].tobytes()
            byte_arr[2::3] = int_bytes[:, 2].tobytes()
            wf.writeframes(bytes(byte_arr))
        else:
            wf.setsampwidth(4)
            scaled = (stacked * 2147483647.0).astype(np.int32)
            wf.writeframes(scaled.tobytes())


def apply_biquad_lowpass(samples: np.ndarray, sample_rate: int, cutoff_hz: float = 80.0, q: float = 0.707) -> np.ndarray:
    """Computes and applies 2nd-order Butterworth low-pass biquad filter."""
    w0 = 2.0 * np.pi * min(cutoff_hz, sample_rate * 0.45) / sample_rate
    cos_w = np.cos(w0)
    sin_w = np.sin(w0)
    alpha = sin_w / (2.0 * q)

    b0 = (1.0 - cos_w) / 2.0
    b1 = 1.0 - cos_w
    b2 = (1.0 - cos_w) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w
    a2 = 1.0 - alpha

    norm_b0 = b0 / a0
    norm_b1 = b1 / a0
    norm_b2 = b2 / a0
    norm_a1 = a1 / a0
    norm_a2 = a2 / a0

    out = np.zeros(len(samples), dtype=np.float32)
    d1 = 0.0
    d2 = 0.0
    for i in range(len(samples)):
        xi = float(samples[i])
        yi = norm_b0 * xi + d1
        d1 = norm_b1 * xi - norm_a1 * yi + d2
        d2 = norm_b2 * xi - norm_a2 * yi
        out[i] = yi

    return out


def apply_biquad_highpass(samples: np.ndarray, sample_rate: int, cutoff_hz: float = 80.0, q: float = 0.707) -> np.ndarray:
    """Computes and applies 2nd-order Butterworth high-pass biquad filter."""
    w0 = 2.0 * np.pi * min(cutoff_hz, sample_rate * 0.45) / sample_rate
    cos_w = np.cos(w0)
    sin_w = np.sin(w0)
    alpha = sin_w / (2.0 * q)

    b0 = (1.0 + cos_w) / 2.0
    b1 = -(1.0 + cos_w)
    b2 = (1.0 + cos_w) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w
    a2 = 1.0 - alpha

    norm_b0 = b0 / a0
    norm_b1 = b1 / a0
    norm_b2 = b2 / a0
    norm_a1 = a1 / a0
    norm_a2 = a2 / a0

    out = np.zeros(len(samples), dtype=np.float32)
    d1 = 0.0
    d2 = 0.0
    for i in range(len(samples)):
        xi = float(samples[i])
        yi = norm_b0 * xi + d1
        d1 = norm_b1 * xi - norm_a1 * yi + d2
        d2 = norm_b2 * xi - norm_a2 * yi
        out[i] = yi

    return out


def generate_714_bed(
    stereo_audio: np.ndarray,
    sample_rate: int,
    lfe_cutoff_hz: float = 80.0,
    height_level: float = 0.35,
    spread: float = 1.15,
    center_focus: float = 0.65,
) -> Dict[str, np.ndarray]:
    """
    Deconstructs stereo audio into discrete 7.1.4 immersive bed channels:
    - Left & Right Front: L / R with center content gently subtracted
    - Center: Correlated Mid mono signal (L+R)/2 filtered with center focus
    - LFE: Dedicated Subwoofer channel with 4th order Linkwitz-Riley low-pass
    - Side & Rear Surrounds: Decorrelated phase-shifted ambient side channels
    - Top Heights (TFL, TFR, TRL, TRR): Diffused overhead ceiling energy
    """
    n_samples = len(stereo_audio)
    in_l = stereo_audio[:, 0]
    in_r = stereo_audio[:, 1]

    # 1. Mid / Side Decomposition
    mid = (in_l + in_r) * 0.5
    side = (in_l - in_r) * 0.5 * spread

    # 2. Center Channel Extraction & Front L/R Separation
    center_raw = mid * center_focus
    front_l = in_l - (center_raw * 0.5)
    front_r = in_r - (center_raw * 0.5)

    # 3. LFE Subwoofer Channel (4th order Linkwitz-Riley low-pass: cascaded 2x Butterworth)
    sub_raw = apply_biquad_lowpass(mid, sample_rate, lfe_cutoff_hz)
    lfe_channel = apply_biquad_lowpass(sub_raw, sample_rate, lfe_cutoff_hz) * 1.414  # +3dB alignment

    # 4. Surround Channels (Side & Rear) with Haas micro-delays & decorrelation
    delay_side_samples = max(1, int(sample_rate * 0.012))  # 12 ms
    delay_rear_samples = max(1, int(sample_rate * 0.022))  # 22 ms

    side_l_buf = np.zeros(n_samples, dtype=np.float32)
    side_r_buf = np.zeros(n_samples, dtype=np.float32)
    side_l_buf[delay_side_samples:] = side[:-delay_side_samples]
    side_r_buf[delay_side_samples:] = -side[:-delay_side_samples]

    rear_l_buf = np.zeros(n_samples, dtype=np.float32)
    rear_r_buf = np.zeros(n_samples, dtype=np.float32)
    rear_l_buf[delay_rear_samples:] = (side * 0.7 - mid * 0.3)[:-delay_rear_samples]
    rear_r_buf[delay_rear_samples:] = (-side * 0.7 - mid * 0.3)[:-delay_rear_samples]

    lss = side_l_buf * 0.75
    rss = side_r_buf * 0.75
    lsr = rear_l_buf * 0.65
    rsr = rear_r_buf * 0.65

    # 5. Top 4 Height Overhead Channels (TFL, TFR, TRL, TRR)
    # High-pass filter above 800 Hz + diffuse early reflections simulating ceiling reverberation
    hp_l = apply_biquad_highpass(in_l, sample_rate, 800.0)
    hp_r = apply_biquad_highpass(in_r, sample_rate, 800.0)

    delay_height_front = max(1, int(sample_rate * 0.007))  # 7 ms
    delay_height_rear = max(1, int(sample_rate * 0.016))   # 16 ms

    tfl = np.zeros(n_samples, dtype=np.float32)
    tfr = np.zeros(n_samples, dtype=np.float32)
    trl = np.zeros(n_samples, dtype=np.float32)
    trr = np.zeros(n_samples, dtype=np.float32)

    tfl[delay_height_front:] = (hp_l * 0.8 + side * 0.4)[:-delay_height_front] * height_level
    tfr[delay_height_front:] = (hp_r * 0.8 - side * 0.4)[:-delay_height_front] * height_level
    trl[delay_height_rear:] = (hp_l * 0.5 - side * 0.6)[:-delay_height_rear] * height_level
    trr[delay_height_rear:] = (hp_r * 0.5 + side * 0.6)[:-delay_height_rear] * height_level

    return {
        "L": front_l,
        "R": front_r,
        "C": center_raw,
        "LFE": lfe_channel,
        "Lss": lss,
        "Rss": rss,
        "Lsr": lsr,
        "Rsr": rsr,
        "TFL": tfl,
        "TFR": tfr,
        "TRL": trl,
        "TRR": trr
    }


def binaural_virtualize_714(bed_channels: Dict[str, np.ndarray], sample_rate: int) -> np.ndarray:
    """
    Renders all 12 discrete 7.1.4 bed channels into a 3D binaural headphone mix.
    Uses Woodworth Interaural Time Difference (ITD) and spherical head shadowing (ILD).
    """
    n_samples = len(bed_channels["L"])
    head_radius = 0.0875  # 8.75 cm
    speed_sound = 343.0   # m/s

    binaural_l = np.zeros(n_samples, dtype=np.float32)
    binaural_r = np.zeros(n_samples, dtype=np.float32)

    for ch_name, ch_data in bed_channels.items():
        spk = SPEAKERS_714[ch_name]
        azimuth_deg = spk["azimuth"]
        elevation_deg = spk["elevation"]

        if spk["is_lfe"]:
            # LFE is non-directional sub-bass, sum equally to both ears with zero latency
            binaural_l += ch_data * 0.6
            binaural_r += ch_data * 0.6
            continue

        theta = np.radians(azimuth_deg)

        # Woodworth formula for ITD
        itd_sec = (head_radius / speed_sound) * (np.sin(theta) + theta * 0.5)
        itd_samples = int(abs(itd_sec) * sample_rate)

        # Interaural Level Difference (ILD) damping on far ear
        # High frequencies shadow more strongly
        level_near = 1.0
        level_far = max(0.2, 1.0 - 0.55 * abs(np.sin(theta)))

        # Elevation pinna spectral cue (overhead notch filter simulation)
        elev_gain = 1.0 + 0.2 * np.sin(np.radians(elevation_deg))

        delayed_far = np.zeros(n_samples, dtype=np.float32)
        if itd_samples < n_samples and itd_samples > 0:
            delayed_far[itd_samples:] = ch_data[:-itd_samples]
        else:
            delayed_far = ch_data.copy()

        if azimuth_deg < 0:
            # Source on the Left
            binaural_l += ch_data * level_near * elev_gain
            binaural_r += delayed_far * level_far * elev_gain
        elif azimuth_deg > 0:
            # Source on the Right
            binaural_r += ch_data * level_near * elev_gain
            binaural_l += delayed_far * level_far * elev_gain
        else:
            # Center channel (azimuth = 0)
            binaural_l += ch_data * 0.707
            binaural_r += ch_data * 0.707

    # Master limiter / normalization for headphone output
    max_peak = max(np.max(np.abs(binaural_l)), np.max(np.abs(binaural_r)))
    if max_peak > 0.95:
        scale = 0.95 / max_peak
        binaural_l *= scale
        binaural_r *= scale

    return np.column_stack([binaural_l, binaural_r])


def render_spatial_714(
    input_path: str,
    output_path: Optional[str] = None,
    mode: str = "binaural",
    format_type: str = "7.1.4",
    lfe_cutoff_hz: float = 80.0,
    height_level: float = 0.35,
    spread: float = 1.15,
) -> Dict[str, Any]:
    """
    Main entrypoint: Decodes audio and renders into 7.1.4 spatial audio bed.
    - mode: 'binaural' (stereo headphone 3D render) or 'discrete' (multichannel WAV)
    - format_type: '7.1.4' (12-ch), '7.1' (8-ch), or '5.1' (6-ch)
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    t_start = time.time()
    samples, sample_rate, bit_depth = read_audio_file(input_path)
    in_peak = float(np.max(np.abs(samples)))
    in_rms = float(np.sqrt(np.mean(samples ** 2)))

    # Generate 12-channel 7.1.4 discrete bed
    bed = generate_714_bed(
        samples,
        sample_rate,
        lfe_cutoff_hz=lfe_cutoff_hz,
        height_level=height_level,
        spread=spread,
    )

    stem = Path(input_path).stem

    if mode == "discrete":
        if format_type == "5.1":
            channel_order = ["L", "R", "C", "LFE", "Lss", "Rss"]
            suffix = "_5point1.wav"
        elif format_type == "7.1":
            channel_order = ["L", "R", "C", "LFE", "Lss", "Rss", "Lsr", "Rsr"]
            suffix = "_7point1.wav"
        else:  # 7.1.4
            channel_order = ["L", "R", "C", "LFE", "Lss", "Rss", "Lsr", "Rsr", "TFL", "TFR", "TRL", "TRR"]
            suffix = "_7point1point4.wav"

        out_channels = [bed[name] for name in channel_order]
        dest_path = output_path or str(Path(input_path).parent / f"{stem}{suffix}")
        write_multichannel_wav(dest_path, out_channels, sample_rate, bit_depth=24)

        out_peak = max([float(np.max(np.abs(ch))) for ch in out_channels])
        out_rms = float(np.sqrt(np.mean(np.array([np.mean(ch ** 2) for ch in out_channels]))))
        channel_count = len(channel_order)
    else:
        # Binaural 3D Headphone Render
        binaural_stereo = binaural_virtualize_714(bed, sample_rate)
        dest_path = output_path or str(Path(input_path).parent / f"{stem}_atmos_binaural.wav")

        from plugin_host import write_wav_file
        write_wav_file(dest_path, binaural_stereo, sample_rate, bit_depth=24)

        out_peak = float(np.max(np.abs(binaural_stereo)))
        out_rms = float(np.sqrt(np.mean(binaural_stereo ** 2)))
        channel_count = 2

    elapsed_time = time.time() - t_start
    duration_sec = len(samples) / float(sample_rate)

    in_peak_dbfs = 20.0 * np.log10(max(1e-9, in_peak))
    in_rms_dbfs = 20.0 * np.log10(max(1e-9, in_rms))
    out_peak_dbfs = 20.0 * np.log10(max(1e-9, out_peak))
    out_rms_dbfs = 20.0 * np.log10(max(1e-9, out_rms))

    return {
        "success": True,
        "input_path": input_path,
        "output_path": dest_path,
        "mode": mode,
        "format": format_type,
        "channels": channel_count,
        "sample_rate": sample_rate,
        "duration_sec": duration_sec,
        "elapsed_sec": elapsed_time,
        "lfe_cutoff_hz": lfe_cutoff_hz,
        "height_level_pct": height_level * 100.0,
        "spread_pct": spread * 100.0,
        "in_peak_dbfs": in_peak_dbfs,
        "in_rms_dbfs": in_rms_dbfs,
        "out_peak_dbfs": out_peak_dbfs,
        "out_rms_dbfs": out_rms_dbfs,
    }


def main():
    parser = argparse.ArgumentParser(description="Sonance Dolby Atmos 7.1.4 Bed Spatializer & Multichannel Audio Renderer")
    parser.add_argument("input", type=str, help="Path to input audio file")
    parser.add_argument("output", type=str, nargs="?", default=None, help="Output destination for spatial audio file")
    parser.add_argument("--mode", type=str, default="binaural", choices=["binaural", "discrete"], help="Render mode: binaural (headphones) or discrete (multichannel)")
    parser.add_argument("--format", type=str, default="7.1.4", choices=["7.1.4", "7.1", "5.1"], help="Multichannel format")
    parser.add_argument("--lfe-cutoff", type=float, default=80.0, help="LFE Subwoofer crossover cutoff in Hz (default: 80.0)")
    parser.add_argument("--height-level", type=float, default=0.35, help="Top ceiling height ambience level (0.0 - 1.0, default: 0.35)")
    parser.add_argument("--spread", type=float, default=1.15, help="Surround field spatial spread multiplier (default: 1.15)")

    args = parser.parse_args()

    print("=" * 70)
    print(f"  SONANCE AUDIOPHILE WORKSTATION v{APP_VERSION}")
    print("  Phase 29: Dolby Atmos 7.1.4 Bed Spatializer & Multichannel Renderer")
    print("=" * 70)

    print(f"[*] Rendering {args.input} into {args.format} Spatial Audio ({args.mode.upper()} mode)...")
    res = render_spatial_714(
        args.input,
        output_path=args.output,
        mode=args.mode,
        format_type=args.format,
        lfe_cutoff_hz=args.lfe_cutoff,
        height_level=args.height_level,
        spread=args.spread,
    )

    print(f"[+] Input File       : {res['input_path']}")
    print(f"[+] Output File      : {res['output_path']}")
    print(f"[+] Render Mode      : {res['mode'].capitalize()} ({res['format']} bed, {res['channels']} channels)")
    print(f"[+] LFE Crossover    : {res['lfe_cutoff_hz']:.1f} Hz (4th-order Linkwitz-Riley alignment)")
    print(f"[+] Height Ambience  : {res['height_level_pct']:.1f}% overhead energy")
    print(f"[+] Surround Spread  : {res['spread_pct']:.1f}%")
    print(f"[+] In Peak / RMS    : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
    print(f"[+] Out Peak / RMS   : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
    print(f"[+] Render Time      : {res['elapsed_sec']:.2f}s ({res['duration_sec']:.1f}s @ {res['sample_rate']} Hz)")
    print("=" * 70)


if __name__ == "__main__":
    main()
