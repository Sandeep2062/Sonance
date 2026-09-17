"""
binaural_virtualizer.py - Binaural 3D Ambisonic Room & Headphone Virtualizer Studio
Part of the Sonance Music Workstation (Phase 26).

Transforms flat "in-your-head" stereo headphone listening into a natural, out-of-head
acoustic experience replicating physical reference studio monitors in a calibrated
acoustically-treated control room.
Implements:
1. Spherical head diffraction model (Woodworth ITD: Interaural Time Difference)
2. Head-shadow acoustic pinna frequency damping (ILD: Interaural Level Difference)
3. Early room boundaries reflections (floor, ceiling, side walls)
4. Configurable speaker azimuth angles (30 deg, 45 deg, 60 deg) and acoustic distance

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import sys
import os
import wave
import argparse
import numpy as np


def read_audio_file(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    with wave.open(file_path, "rb") as wf:
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
            # Mono to dual-mono
            data = np.column_stack([data, data])
        else:
            data = data.reshape(-1, num_channels)
            if num_channels > 2:
                data = data[:, :2]

        return data, sample_rate, 2, sample_width


def write_wav_file(file_path, samples, sample_rate, bit_depth=24):
    samples = np.clip(samples, -1.0, 1.0)
    num_channels = samples.shape[1]
    n_frames = samples.shape[0]

    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setframerate(sample_rate)

        if bit_depth == 16:
            wf.setsampwidth(2)
            scaled = (samples * 32767.0).astype(np.int16)
            wf.writeframes(scaled.tobytes())
        elif bit_depth == 24:
            wf.setsampwidth(3)
            scaled = (samples * 8388607.0).astype(np.int32)
            raw_bytes = scaled.tobytes()
            byte_arr = bytearray(n_frames * num_channels * 3)
            int_bytes = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(-1, 4)
            byte_arr[0::3] = int_bytes[:, 0].tobytes()
            byte_arr[1::3] = int_bytes[:, 1].tobytes()
            byte_arr[2::3] = int_bytes[:, 2].tobytes()
            wf.writeframes(bytes(byte_arr))
        else:
            wf.setsampwidth(4)
            scaled = (samples * 2147483647.0).astype(np.int32)
            wf.writeframes(scaled.tobytes())


def apply_fractional_delay(signal, delay_samples):
    """
    Applies a sub-sample / integer delay to a 1D audio signal using linear interpolation.
    """
    if delay_samples <= 0:
        return signal.copy()

    n = len(signal)
    int_delay = int(np.floor(delay_samples))
    frac_delay = delay_samples - int_delay

    delayed = np.zeros(n, dtype=np.float32)
    if int_delay >= n:
        return delayed

    if frac_delay < 1e-4:
        delayed[int_delay:] = signal[:n - int_delay]
    else:
        # Linear interpolation between adjacent samples
        s1 = np.zeros(n, dtype=np.float32)
        s2 = np.zeros(n, dtype=np.float32)

        s1[int_delay:] = signal[:n - int_delay]
        if int_delay + 1 < n:
            s2[int_delay + 1:] = signal[:n - int_delay - 1]

        delayed = (1.0 - frac_delay) * s1 + frac_delay * s2

    return delayed


def head_shadow_filter(signal, sample_rate, cutoff_hz=2200.0):
    """
    Simulates acoustic head shadow damping on far ear using a 1st order IIR low-pass filter.
    """
    dt = 1.0 / sample_rate
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    alpha = dt / (rc + dt)

    filtered = np.zeros_like(signal)
    prev = 0.0
    for i in range(len(signal)):
        curr = prev + alpha * (signal[i] - prev)
        filtered[i] = curr
        prev = curr
    return filtered


def virtualize_binaural(samples, sample_rate, speaker_angle_deg=30.0,
                         distance_m=1.8, crossfeed_amount=1.0,
                         room_ambience=0.35, preset="control_room"):
    """
    Processes stereo signal into binaural virtual monitor space.
    - speaker_angle_deg: Azimuth angle of speakers from center line (typically 30 deg).
    - distance_m: Distance from listener to monitors in meters (1.0 - 5.0m).
    - crossfeed_amount: Strength of crossfeed blending (0.0 to 1.0).
    - room_ambience: Strength of early room reflection cues (0.0 to 1.0).
    - preset: 'control_room', 'mastering_lab', 'live_lounge'.
    """
    if preset == "mastering_lab":
        speaker_angle_deg = 30.0
        distance_m = 2.4
        room_ambience = 0.22
    elif preset == "live_lounge":
        speaker_angle_deg = 45.0
        distance_m = 3.2
        room_ambience = 0.55
    elif preset == "control_room":
        speaker_angle_deg = 30.0
        distance_m = 1.6
        room_ambience = 0.32

    # Physical constants
    c_sound = 343.0  # Speed of sound in air (m/s)
    head_radius = 0.0875  # 8.75 cm average human head radius

    theta_rad = np.radians(speaker_angle_deg)

    # Woodworth's formula for ITD (Interaural Time Difference):
    # ITD = (r / c) * (theta + sin(theta))
    itd_sec = (head_radius / c_sound) * (theta_rad + np.sin(theta_rad))
    itd_samples = itd_sec * sample_rate

    # Distance attenuation factor (inverse square law with baseline 1m)
    dist_gain = 1.0 / np.sqrt(max(1.0, distance_m))

    left_in = samples[:, 0] * dist_gain
    right_in = samples[:, 1] * dist_gain
    n = len(left_in)

    # Direct acoustic path (ipsilateral ear)
    left_direct = left_in
    right_direct = right_in

    # Crossfeed acoustic path (contralateral ear): delayed by ITD & damped by head shadow ILD
    left_cross = head_shadow_filter(apply_fractional_delay(left_in, itd_samples), sample_rate, cutoff_hz=2100.0)
    right_cross = head_shadow_filter(apply_fractional_delay(right_in, itd_samples), sample_rate, cutoff_hz=2100.0)

    # Combine direct and crossfeed
    out_left = left_direct + (right_cross * crossfeed_amount * 0.75)
    out_right = right_direct + (left_cross * crossfeed_amount * 0.75)

    # Early room reflections simulation (floor, side walls, ceiling)
    if room_ambience > 0.01:
        # Floor reflection (approx 4.5 ms delay, -9 dB)
        floor_delay = int(0.0045 * sample_rate)
        # Left/Right side wall reflections (approx 12-16 ms delay, -12 dB)
        wall_delay_l = int(0.0135 * sample_rate)
        wall_delay_r = int(0.0152 * sample_rate)
        # Ceiling reflection (approx 8.5 ms delay, -11 dB)
        ceil_delay = int(0.0085 * sample_rate)

        refl_l = (
            apply_fractional_delay(left_in, floor_delay) * 0.28 +
            apply_fractional_delay(left_in, wall_delay_l) * 0.22 +
            apply_fractional_delay(right_in, wall_delay_r) * 0.18 +
            apply_fractional_delay(left_in, ceil_delay) * 0.20
        )
        refl_r = (
            apply_fractional_delay(right_in, floor_delay) * 0.28 +
            apply_fractional_delay(right_in, wall_delay_r) * 0.22 +
            apply_fractional_delay(left_in, wall_delay_l) * 0.18 +
            apply_fractional_delay(right_in, ceil_delay) * 0.20
        )

        out_left += refl_l * room_ambience
        out_right += refl_r * room_ambience

    out = np.column_stack([out_left, out_right])

    # Normalize gain to match perceived listening loudness
    max_val = np.max(np.abs(out)) + 1e-9
    in_max = np.max(np.abs(samples)) + 1e-9
    if max_val > in_max:
        out = out * (in_max / max_val)

    in_peak = float(np.max(np.abs(samples)))
    out_peak = float(np.max(np.abs(out)))
    in_rms = float(np.sqrt(np.mean(samples ** 2))) + 1e-12
    out_rms = float(np.sqrt(np.mean(out ** 2))) + 1e-12

    return out, {
        "speaker_angle_deg": speaker_angle_deg,
        "distance_m": distance_m,
        "itd_ms": itd_sec * 1000.0,
        "itd_samples": round(itd_samples, 2),
        "preset": preset,
        "room_ambience": room_ambience,
        "in_peak_dbfs": 20.0 * np.log10(in_peak) if in_peak > 0 else -120.0,
        "out_peak_dbfs": 20.0 * np.log10(out_peak) if out_peak > 0 else -120.0,
        "in_rms_dbfs": 20.0 * np.log10(in_rms),
        "out_rms_dbfs": 20.0 * np.log10(out_rms),
        "duration_sec": n / sample_rate,
        "sample_rate": sample_rate
    }


def run_binaural_virtualization(input_path, output_path=None, speaker_angle_deg=30.0,
                                distance_m=1.8, crossfeed_amount=1.0,
                                room_ambience=0.35, preset="control_room"):
    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_binaural{ext if ext.lower() == '.wav' else '.wav'}"

    samples, sr, channels, width = read_audio_file(input_path)
    processed, stats = virtualize_binaural(
        samples, sr,
        speaker_angle_deg=speaker_angle_deg,
        distance_m=distance_m,
        crossfeed_amount=crossfeed_amount,
        room_ambience=room_ambience,
        preset=preset
    )

    write_wav_file(output_path, processed, sr, bit_depth=24)
    stats["input_path"] = input_path
    stats["output_path"] = output_path
    stats["status"] = "success"
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Binaural 3D Ambisonic Room & Headphone Virtualizer Studio (Sonance Phase 26)",
        allow_abbrev=False
    )
    parser.add_argument("input", help="Path to input audio file (WAV)")
    parser.add_argument("output", nargs="?", default=None, help="Path to output WAV file")
    parser.add_argument("--preset", choices=["control_room", "mastering_lab", "live_lounge", "custom"], default="control_room", help="Acoustic room preset")
    parser.add_argument("--angle", type=float, default=30.0, help="Speaker azimuth angle in degrees (default: 30.0)")
    parser.add_argument("--distance", type=float, default=1.8, help="Speaker distance in meters (default: 1.8)")
    parser.add_argument("--crossfeed", type=float, default=1.0, help="Crossfeed level 0.0 to 1.0 (default: 1.0)")
    parser.add_argument("--ambience", type=float, default=0.35, help="Early reflections room ambience 0.0 to 1.0 (default: 0.35)")

    args = parser.parse_args()

    try:
        res = run_binaural_virtualization(
            args.input,
            output_path=args.output,
            speaker_angle_deg=args.angle,
            distance_m=args.distance,
            crossfeed_amount=args.crossfeed,
            room_ambience=args.ambience,
            preset=args.preset
        )
        print("=" * 60)
        print("  BINAURAL 3D ROOM & HEADPHONE VIRTUALIZER STUDIO")
        print("=" * 60)
        print(f"Input File    : {res['input_path']}")
        print(f"Output File   : {res['output_path']}")
        print(f"Room Preset   : {res['preset']}")
        print(f"Speaker Angle : {res['speaker_angle_deg']:.1f} deg | Distance: {res['distance_m']:.1f} m")
        print(f"Woodworth ITD : {res['itd_ms']:.2f} ms ({res['itd_samples']} samples)")
        print(f"In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
        print(f"Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
        print(f"Duration      : {res['duration_sec']:.2f}s @ {res['sample_rate']} Hz")
        print("=" * 60)
    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
