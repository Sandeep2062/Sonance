"""
audio_noisegate.py - Broadcast Audio Noise Gate & Downward Expander Studio
Part of the Sonance Music Workstation (Phase 26).

Implements professional broadcast-grade downward expansion and noise gating with
lookahead detection buffer (0-10ms), hysteresis chatter prevention, sidechain
bandpass filtering, and smooth Attack-Hold-Release envelopes.
Eliminates preamp hum, room rumble, headphone bleed, and vinyl surface noise
between vocal takes or instrumental hits without clipping off phrase beginnings.

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

        if num_channels > 1:
            data = data.reshape(-1, num_channels)
        else:
            data = data.reshape(-1, 1)

        return data, sample_rate, num_channels, sample_width


def write_wav_file(file_path, samples, sample_rate, bit_depth=24):
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


def simple_biquad_bandpass(signal, sample_rate, low_hz=80.0, high_hz=5000.0):
    """
    Applies high-pass and low-pass 1st-order IIR filters to condition sidechain detection.
    """
    dt = 1.0 / sample_rate
    # High-pass
    rc_hp = 1.0 / (2.0 * np.pi * max(10.0, low_hz))
    alpha_hp = rc_hp / (rc_hp + dt)
    hp_filtered = np.zeros_like(signal)
    prev_in = 0.0
    prev_out = 0.0
    for i in range(len(signal)):
        curr_out = alpha_hp * (prev_out + signal[i] - prev_in)
        hp_filtered[i] = curr_out
        prev_in = signal[i]
        prev_out = curr_out

    # Low-pass
    rc_lp = 1.0 / (2.0 * np.pi * min(sample_rate * 0.45, high_hz))
    alpha_lp = dt / (rc_lp + dt)
    bp_filtered = np.zeros_like(signal)
    prev_lp = 0.0
    for i in range(len(hp_filtered)):
        curr_lp = prev_lp + alpha_lp * (hp_filtered[i] - prev_lp)
        bp_filtered[i] = curr_lp
        prev_lp = curr_lp

    return bp_filtered


def process_noise_gate(samples, sample_rate, threshold_db=-40.0,
                       reduction_db=-60.0, ratio=10.0, attack_ms=1.5,
                       hold_ms=40.0, release_ms=120.0, lookahead_ms=2.0,
                       hysteresis_db=3.0, sidechain_hp_hz=80.0,
                       sidechain_lp_hz=6000.0):
    """
    Processes audio with a downward expander / noise gate.
    - threshold_db: Open threshold level in dBFS.
    - reduction_db: Maximum gate floor attenuation (e.g. -60 dB is silent, -12 dB is gentle).
    - ratio: Expansion slope below threshold (e.g. 10.0 for gating, 2.0 for subtle expander).
    - attack_ms: Opening time.
    - hold_ms: Open hold duration before starting release.
    - release_ms: Closing time.
    - lookahead_ms: Lookahead delay to preserve transient punch without clicks.
    - hysteresis_db: Close threshold is (threshold_db - hysteresis_db).
    """
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)

    n_samples, num_channels = samples.shape
    lookahead_samples = int(round((lookahead_ms / 1000.0) * sample_rate))

    # Delayed audio buffer to align with lookahead detector
    if lookahead_samples > 0:
        delayed_samples = np.vstack([np.zeros((lookahead_samples, num_channels), dtype=np.float32), samples])[:n_samples]
    else:
        delayed_samples = samples.copy()

    # Link channels for stereo detection
    det_signal = np.max(np.abs(samples), axis=1)

    # Sidechain filtering
    filtered_det = simple_biquad_bandpass(det_signal, sample_rate, low_hz=sidechain_hp_hz, high_hz=sidechain_lp_hz)
    env_det = np.abs(filtered_det)

    # Convert to dBFS
    env_db = 20.0 * np.log10(np.maximum(1e-6, env_det))

    # Envelope ballistics coefficients
    alpha_attack = np.exp(-1.0 / max(1.0, (sample_rate * (attack_ms / 1000.0))))
    alpha_release = np.exp(-1.0 / max(1.0, (sample_rate * (release_ms / 1000.0))))
    hold_samples = int((hold_ms / 1000.0) * sample_rate)

    open_thresh = threshold_db
    close_thresh = threshold_db - abs(hysteresis_db)
    min_gain_linear = 10.0 ** (reduction_db / 20.0)

    is_open = False
    hold_counter = 0
    current_gain = min_gain_linear
    gain_curve = np.zeros(n_samples, dtype=np.float32)

    for i in range(n_samples):
        level_db = env_db[i]

        if is_open:
            if level_db < close_thresh:
                if hold_counter > 0:
                    hold_counter -= 1
                    target_gain = 1.0
                else:
                    is_open = False
                    # Downward expansion slope
                    diff = close_thresh - level_db
                    att_db = min(-reduction_db, diff * (ratio - 1.0))
                    target_gain = max(min_gain_linear, 10.0 ** (-att_db / 20.0))
            else:
                target_gain = 1.0
                hold_counter = hold_samples
        else:
            if level_db >= open_thresh:
                is_open = True
                target_gain = 1.0
                hold_counter = hold_samples
            else:
                diff = open_thresh - level_db
                att_db = min(-reduction_db, diff * (ratio - 1.0))
                target_gain = max(min_gain_linear, 10.0 ** (-att_db / 20.0))

        # Smooth attack / release
        if target_gain > current_gain:
            current_gain = alpha_attack * current_gain + (1.0 - alpha_attack) * target_gain
        else:
            current_gain = alpha_release * current_gain + (1.0 - alpha_release) * target_gain

        gain_curve[i] = current_gain

    # Apply gain curve across channels
    out_samples = delayed_samples * gain_curve[:, np.newaxis]
    out_samples = np.clip(out_samples, -1.0, 1.0)

    in_peak = float(np.max(np.abs(samples)))
    out_peak = float(np.max(np.abs(out_samples)))
    in_rms = float(np.sqrt(np.mean(samples ** 2))) + 1e-12
    out_rms = float(np.sqrt(np.mean(out_samples ** 2))) + 1e-12

    # Percentage of time gate was closed or actively reducing
    attenuated_frames = np.sum(gain_curve < 0.95)
    attenuation_ratio_pct = (attenuated_frames / n_samples) * 100.0

    return out_samples, {
        "threshold_db": threshold_db,
        "reduction_db": reduction_db,
        "ratio": ratio,
        "attack_ms": attack_ms,
        "hold_ms": hold_ms,
        "release_ms": release_ms,
        "lookahead_ms": lookahead_ms,
        "attenuation_pct": round(attenuation_ratio_pct, 1),
        "in_peak_dbfs": 20.0 * np.log10(in_peak) if in_peak > 0 else -120.0,
        "out_peak_dbfs": 20.0 * np.log10(out_peak) if out_peak > 0 else -120.0,
        "in_rms_dbfs": 20.0 * np.log10(in_rms),
        "out_rms_dbfs": 20.0 * np.log10(out_rms),
        "duration_sec": n_samples / sample_rate,
        "sample_rate": sample_rate
    }


def run_noise_gate(input_path, output_path=None, threshold_db=-40.0,
                   reduction_db=-60.0, ratio=10.0, attack_ms=1.5,
                   hold_ms=40.0, release_ms=120.0, lookahead_ms=2.0,
                   hysteresis_db=3.0):
    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_gated{ext if ext.lower() == '.wav' else '.wav'}"

    samples, sr, channels, width = read_audio_file(input_path)
    processed, stats = process_noise_gate(
        samples, sr,
        threshold_db=threshold_db,
        reduction_db=reduction_db,
        ratio=ratio,
        attack_ms=attack_ms,
        hold_ms=hold_ms,
        release_ms=release_ms,
        lookahead_ms=lookahead_ms,
        hysteresis_db=hysteresis_db
    )

    write_wav_file(output_path, processed, sr, bit_depth=24)
    stats["input_path"] = input_path
    stats["output_path"] = output_path
    stats["status"] = "success"
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Broadcast Audio Noise Gate & Downward Expander Studio (Sonance Phase 26)",
        allow_abbrev=False
    )
    parser.add_argument("input", help="Path to input audio file (WAV)")
    parser.add_argument("output", nargs="?", default=None, help="Path to output WAV file")
    parser.add_argument("--threshold", type=float, default=-40.0, help="Gate threshold in dBFS (default: -40.0)")
    parser.add_argument("--reduction", type=float, default=-60.0, help="Maximum floor reduction in dB (default: -60.0)")
    parser.add_argument("--ratio", type=float, default=10.0, help="Expansion ratio (default: 10.0)")
    parser.add_argument("--attack", type=float, default=1.5, help="Attack time in ms (default: 1.5)")
    parser.add_argument("--hold", type=float, default=40.0, help="Hold time in ms (default: 40.0)")
    parser.add_argument("--release", type=float, default=120.0, help="Release time in ms (default: 120.0)")
    parser.add_argument("--lookahead", type=float, default=2.0, help="Lookahead time in ms (default: 2.0)")

    args = parser.parse_args()

    try:
        res = run_noise_gate(
            args.input,
            output_path=args.output,
            threshold_db=args.threshold,
            reduction_db=args.reduction,
            ratio=args.ratio,
            attack_ms=args.attack,
            hold_ms=args.hold,
            release_ms=args.release,
            lookahead_ms=args.lookahead
        )
        print("=" * 60)
        print("  BROADCAST AUDIO NOISE GATE & DOWNWARD EXPANDER STUDIO")
        print("=" * 60)
        print(f"Input File    : {res['input_path']}")
        print(f"Output File   : {res['output_path']}")
        print(f"Threshold     : {res['threshold_db']:.1f} dBFS (Floor: {res['reduction_db']:.1f} dB)")
        print(f"Timing (A/H/R): {res['attack_ms']:.1f}ms / {res['hold_ms']:.1f}ms / {res['release_ms']:.1f}ms")
        print(f"Lookahead     : {res['lookahead_ms']:.1f}ms (Gated Duration: {res['attenuation_pct']}%)")
        print(f"In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
        print(f"Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
        print(f"Duration      : {res['duration_sec']:.2f}s @ {res['sample_rate']} Hz")
        print("=" * 60)
    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
