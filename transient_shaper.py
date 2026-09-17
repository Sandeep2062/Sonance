"""
transient_shaper.py - Audiophile Transient Shaper & Drum Punch Designer Studio
Part of the Sonance Music Workstation (Phase 26).

Implements dual-ballistics envelope detection (fast vs. slow envelope followers)
to independently adjust transient Attack (-24 dB to +24 dB) and acoustic Sustain
(-24 dB to +24 dB). Restores drum punch, tightens boomy reverb tails, or softens
overly aggressive percussive transients without dynamic pumping artifacts.
Includes soft-knee saturation output limiting to prevent digital overs.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import sys
import os
import struct
import wave
import argparse
import numpy as np


def read_audio_file(file_path):
    """
    Reads a WAV or raw PCM audio file into float32 numpy array normalized to [-1.0, 1.0].
    Returns (samples_array_2d, sample_rate, num_channels, sample_width).
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    try:
        with wave.open(file_path, "rb") as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)

            if sample_width == 1:
                dtype = np.uint8
                data = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32)
                data = (data - 128.0) / 128.0
            elif sample_width == 2:
                dtype = np.int16
                data = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32) / 32768.0
            elif sample_width == 3:
                # 24-bit PCM
                raw_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
                raw_reshaped = raw_arr.reshape(-1, 3)
                padded = np.column_stack([np.zeros(len(raw_reshaped), dtype=np.uint8), raw_reshaped])
                data = padded.view(np.int32).flatten().astype(np.float32) / 2147483648.0
            elif sample_width == 4:
                dtype = np.int32
                data = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32) / 2147483648.0
            else:
                raise ValueError(f"Unsupported sample width: {sample_width} bytes")

            if num_channels > 1:
                data = data.reshape(-1, num_channels)
            else:
                data = data.reshape(-1, 1)

            return data, sample_rate, num_channels, sample_width
    except wave.Error:
        raise ValueError(f"File {file_path} is not a valid standard PCM WAV file.")


def write_wav_file(file_path, samples, sample_rate, bit_depth=24):
    """
    Writes float32 numpy array (channels x samples or samples x channels) to PCM WAV.
    """
    samples = np.clip(samples, -1.0, 1.0)
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
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


def envelope_follower(signal, sample_rate, attack_time_ms, release_time_ms):
    """
    One-pole lowpass envelope detector for signal magnitude.
    """
    alpha_attack = np.exp(-1.0 / (sample_rate * (attack_time_ms / 1000.0)))
    alpha_release = np.exp(-1.0 / (sample_rate * (release_time_ms / 1000.0)))

    rectified = np.abs(signal)
    n_samples = len(signal)
    envelope = np.zeros(n_samples, dtype=np.float32)

    current_env = 0.0
    for i in range(n_samples):
        x = rectified[i]
        if x > current_env:
            current_env = alpha_attack * current_env + (1.0 - alpha_attack) * x
        else:
            current_env = alpha_release * current_env + (1.0 - alpha_release) * x
        envelope[i] = current_env

    return envelope


def process_transients(samples, sample_rate, attack_db=0.0, sustain_db=0.0,
                       attack_speed_ms=4.0, sustain_speed_ms=80.0,
                       soft_clip=True):
    """
    Processes audio using dual envelope ballistics.
    - attack_db: -24.0 to +24.0 dB gain on percussive onset transients.
    - sustain_db: -24.0 to +24.0 dB gain on body, resonance, and room tails.
    - attack_speed_ms: fast envelope reaction window (default 4.0 ms).
    - sustain_speed_ms: slow envelope decay window (default 80.0 ms).
    - soft_clip: tanh soft saturation to prevent clipping overs when boosting.
    """
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)

    n_samples, num_channels = samples.shape
    out_samples = np.zeros_like(samples)

    attack_gain = 10.0 ** (attack_db / 20.0) - 1.0
    sustain_gain = 10.0 ** (sustain_db / 20.0) - 1.0

    for ch in range(num_channels):
        channel_data = samples[:, ch]

        env_fast = envelope_follower(channel_data, sample_rate, attack_time_ms=attack_speed_ms, release_time_ms=attack_speed_ms * 4.0)
        env_slow = envelope_follower(channel_data, sample_rate, attack_time_ms=attack_speed_ms * 5.0, release_time_ms=sustain_speed_ms)

        transient_diff = env_fast - env_slow
        transient_mask = np.maximum(0.0, transient_diff) / (env_fast + 1e-6)
        transient_mask = np.clip(transient_mask, 0.0, 1.0)
        sustain_mask = 1.0 - transient_mask

        gain_curve = 1.0 + (attack_gain * transient_mask) + (sustain_gain * sustain_mask)
        gain_curve = np.maximum(0.01, gain_curve)

        processed = channel_data * gain_curve

        if soft_clip:
            threshold = 0.85
            over = np.abs(processed) > threshold
            if np.any(over):
                sgn = np.sign(processed)
                mag = np.abs(processed)
                mag[over] = threshold + (1.0 - threshold) * np.tanh((mag[over] - threshold) / (1.0 - threshold))
                processed = sgn * mag

        out_samples[:, ch] = np.clip(processed, -1.0, 1.0)

    in_peak = float(np.max(np.abs(samples)))
    out_peak = float(np.max(np.abs(out_samples)))
    in_rms = float(np.sqrt(np.mean(samples ** 2))) + 1e-12
    out_rms = float(np.sqrt(np.mean(out_samples ** 2))) + 1e-12

    in_peak_db = 20.0 * np.log10(in_peak) if in_peak > 0 else -120.0
    out_peak_db = 20.0 * np.log10(out_peak) if out_peak > 0 else -120.0
    in_rms_db = 20.0 * np.log10(in_rms)
    out_rms_db = 20.0 * np.log10(out_rms)

    return out_samples, {
        "in_peak_dbfs": in_peak_db,
        "out_peak_dbfs": out_peak_db,
        "in_rms_dbfs": in_rms_db,
        "out_rms_dbfs": out_rms_db,
        "attack_db": attack_db,
        "sustain_db": sustain_db,
        "duration_sec": n_samples / sample_rate,
        "sample_rate": sample_rate
    }


def run_transient_shaping(input_path, output_path=None, attack_db=0.0, sustain_db=0.0,
                          attack_speed_ms=4.0, sustain_speed_ms=80.0, soft_clip=True):
    """
    Top-level API method for transient shaping.
    """
    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_transient{ext if ext.lower() == '.wav' else '.wav'}"

    samples, sr, channels, width = read_audio_file(input_path)
    processed, stats = process_transients(
        samples, sr,
        attack_db=attack_db,
        sustain_db=sustain_db,
        attack_speed_ms=attack_speed_ms,
        sustain_speed_ms=sustain_speed_ms,
        soft_clip=soft_clip
    )

    write_wav_file(output_path, processed, sr, bit_depth=24)
    stats["input_path"] = input_path
    stats["output_path"] = output_path
    stats["status"] = "success"
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Audiophile Transient Shaper & Drum Punch Designer Studio (Sonance Phase 26)",
        allow_abbrev=False
    )
    parser.add_argument("input", help="Path to input audio file (WAV)")
    parser.add_argument("output", nargs="?", default=None, help="Path to output WAV file")
    parser.add_argument("--attack", type=float, default=0.0, help="Transient attack gain in dB (-24.0 to +24.0)")
    parser.add_argument("--sustain", type=float, default=0.0, help="Sustain tail gain in dB (-24.0 to +24.0)")
    parser.add_argument("--attack-speed", type=float, default=4.0, help="Attack envelope speed in ms (default: 4.0)")
    parser.add_argument("--sustain-speed", type=float, default=80.0, help="Sustain envelope speed in ms (default: 80.0)")
    parser.add_argument("--no-soft-clip", action="store_true", help="Disable tanh soft-knee output limiting")

    args = parser.parse_args()

    try:
        res = run_transient_shaping(
            args.input,
            output_path=args.output,
            attack_db=args.attack,
            sustain_db=args.sustain,
            attack_speed_ms=args.attack_speed,
            sustain_speed_ms=args.sustain_speed,
            soft_clip=not args.no_soft_clip
        )
        print("=" * 60)
        print("  AUDIOPHILE TRANSIENT SHAPER & DRUM PUNCH STUDIO")
        print("=" * 60)
        print(f"Input File    : {res['input_path']}")
        print(f"Output File   : {res['output_path']}")
        print(f"Attack Gain   : {res['attack_db']:+.1f} dB (speed: {args.attack_speed:.1f}ms)")
        print(f"Sustain Gain  : {res['sustain_db']:+.1f} dB (speed: {args.sustain_speed:.1f}ms)")
        print(f"In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
        print(f"Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
        print(f"Duration      : {res['duration_sec']:.2f}s @ {res['sample_rate']} Hz")
        print("=" * 60)
    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
