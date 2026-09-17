"""
tape_echo_delay.py - Stereo Ping-Pong & Multi-Tap BBD Tape Echo Studio
Part of the Sonance Music Workstation (Phase 26).

Emulates vintage magnetic tape loop echoes (Roland Space Echo RE-201 / Echoplex)
and analog Bucket Brigade Device (BBD) delay units.
Features:
1. True Stereo Ping-Pong alternating feedback bounce (L -> R -> L -> R)
2. Frequency damping low-pass filter on each echo repeat (tape flux absorption)
3. Subtle capstan wow & flutter pitch micro-modulation
4. Soft-knee feedback saturation preventing harsh digital clipping
5. High-precision 24-bit PCM WAV master export

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


def process_tape_echo(samples, sample_rate, delay_ms=375.0, feedback_pct=45.0,
                      damping_hz=3800.0, flutter_pct=0.12, drive=1.3,
                      dry_wet_pct=35.0, ping_pong=True):
    """
    Processes stereo audio through a vintage tape echo / BBD delay delay line.
    - delay_ms: Delay time in milliseconds (10 to 2000 ms).
    - feedback_pct: Feedback percentage (0 to 100%).
    - damping_hz: Low-pass damping filter on echoes (simulates tape high-frequency loss).
    - flutter_pct: Wow & flutter pitch modulation depth (0.0 to 1.0%).
    - drive: Preamp saturation in feedback path (1.0 to 3.0).
    - dry_wet_pct: Mix percentage (0% = dry only, 100% = wet only).
    - ping_pong: True for alternating L/R stereo bounce, False for standard stereo delay.
    """
    n_samples, num_channels = samples.shape
    base_delay_samples = int(round((delay_ms / 1000.0) * sample_rate))

    # Calculate tail decay length based on feedback
    feedback_linear = np.clip(feedback_pct / 100.0, 0.0, 0.96)
    # Estimate samples for echo to decay below -60 dB
    if feedback_linear > 0.05:
        decay_iterations = int(np.ceil(-60.0 / (20.0 * np.log10(feedback_linear))))
        tail_samples = min(int(sample_rate * 8.0), decay_iterations * base_delay_samples)
    else:
        tail_samples = base_delay_samples

    total_len = n_samples + tail_samples
    buffer_len = base_delay_samples + int(sample_rate * 0.1)

    # Output arrays
    out_wet = np.zeros((total_len, 2), dtype=np.float32)

    # Delay line buffers for L and R
    delay_buf_l = np.zeros(buffer_len, dtype=np.float32)
    delay_buf_r = np.zeros(buffer_len, dtype=np.float32)

    # Damping filter coefficients (1st order low-pass)
    dt = 1.0 / sample_rate
    rc = 1.0 / (2.0 * np.pi * max(100.0, damping_hz))
    alpha_damp = dt / (rc + dt)

    prev_filt_l = 0.0
    prev_filt_r = 0.0

    write_idx_l = 0
    write_idx_r = 0

    # Wow & flutter LFO generator (0.5 Hz to 2.5 Hz composite sinusoidal drift)
    t = np.arange(total_len) / sample_rate
    lfo = np.sin(2.0 * np.pi * 0.8 * t) * 0.7 + np.sin(2.0 * np.pi * 2.3 * t) * 0.3
    flutter_samples_mod = lfo * (flutter_pct / 100.0) * (sample_rate * 0.003)

    for i in range(total_len):
        # Input sample or zero during tail
        in_l = samples[i, 0] if i < n_samples else 0.0
        in_r = samples[i, 1] if i < n_samples else 0.0

        current_delay = base_delay_samples + flutter_samples_mod[i]

        # Read pointers with fractional interpolation
        read_idx_l_float = (write_idx_l - current_delay) % buffer_len
        read_idx_r_float = (write_idx_r - current_delay) % buffer_len

        r0_l = int(read_idx_l_float)
        frac_l = read_idx_l_float - r0_l
        r1_l = (r0_l + 1) % buffer_len
        echo_l = (1.0 - frac_l) * delay_buf_l[r0_l] + frac_l * delay_buf_l[r1_l]

        r0_r = int(read_idx_r_float)
        frac_r = read_idx_r_float - r0_r
        r1_r = (r0_r + 1) % buffer_len
        echo_r = (1.0 - frac_r) * delay_buf_r[r0_r] + frac_r * delay_buf_r[r1_r]

        # High-frequency damping
        prev_filt_l = prev_filt_l + alpha_damp * (echo_l - prev_filt_l)
        damped_l = prev_filt_l

        prev_filt_r = prev_filt_r + alpha_damp * (echo_r - prev_filt_r)
        damped_r = prev_filt_r

        # Feedback saturation (hyperbolic tangent tape warmth)
        sat_l = np.tanh(damped_l * drive) / np.tanh(drive)
        sat_r = np.tanh(damped_r * drive) / np.tanh(drive)

        out_wet[i, 0] = echo_l
        out_wet[i, 1] = echo_r

        # Feedback routing
        if ping_pong:
            # Cross feedback: Left echo feeds Right delay, Right echo feeds Left delay
            delay_buf_l[write_idx_l] = in_l + (sat_r * feedback_linear)
            delay_buf_r[write_idx_r] = in_r + (sat_l * feedback_linear)
        else:
            delay_buf_l[write_idx_l] = in_l + (sat_l * feedback_linear)
            delay_buf_r[write_idx_r] = in_r + (sat_r * feedback_linear)

        write_idx_l = (write_idx_l + 1) % buffer_len
        write_idx_r = (write_idx_r + 1) % buffer_len

    # Blend dry and wet
    wet_gain = dry_wet_pct / 100.0
    dry_gain = 1.0 - (wet_gain * 0.4)  # Preserve dry clarity

    out_final = np.zeros((total_len, 2), dtype=np.float32)
    out_final[:n_samples, 0] += samples[:, 0] * dry_gain
    out_final[:n_samples, 1] += samples[:, 1] * dry_gain

    out_final[:, 0] += out_wet[:, 0] * wet_gain
    out_final[:, 1] += out_wet[:, 1] * wet_gain

    # Peak normalization to prevent clipping
    max_val = np.max(np.abs(out_final)) + 1e-9
    if max_val > 0.99:
        out_final = out_final * (0.98 / max_val)

    in_peak = float(np.max(np.abs(samples)))
    out_peak = float(np.max(np.abs(out_final)))
    in_rms = float(np.sqrt(np.mean(samples ** 2))) + 1e-12
    out_rms = float(np.sqrt(np.mean(out_final ** 2))) + 1e-12

    return out_final, {
        "delay_ms": delay_ms,
        "feedback_pct": feedback_pct,
        "damping_hz": damping_hz,
        "flutter_pct": flutter_pct,
        "drive": drive,
        "dry_wet_pct": dry_wet_pct,
        "ping_pong": ping_pong,
        "in_peak_dbfs": 20.0 * np.log10(in_peak) if in_peak > 0 else -120.0,
        "out_peak_dbfs": 20.0 * np.log10(out_peak) if out_peak > 0 else -120.0,
        "in_rms_dbfs": 20.0 * np.log10(in_rms),
        "out_rms_dbfs": 20.0 * np.log10(out_rms),
        "duration_sec": total_len / sample_rate,
        "sample_rate": sample_rate
    }


def run_tape_echo(input_path, output_path=None, delay_ms=375.0, feedback_pct=45.0,
                  damping_hz=3800.0, flutter_pct=0.12, drive=1.3,
                  dry_wet_pct=35.0, ping_pong=True):
    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_echo{ext if ext.lower() == '.wav' else '.wav'}"

    samples, sr, channels, width = read_audio_file(input_path)
    processed, stats = process_tape_echo(
        samples, sr,
        delay_ms=delay_ms,
        feedback_pct=feedback_pct,
        damping_hz=damping_hz,
        flutter_pct=flutter_pct,
        drive=drive,
        dry_wet_pct=dry_wet_pct,
        ping_pong=ping_pong
    )

    write_wav_file(output_path, processed, sr, bit_depth=24)
    stats["input_path"] = input_path
    stats["output_path"] = output_path
    stats["status"] = "success"
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Stereo Ping-Pong & Multi-Tap BBD Tape Echo Studio (Sonance Phase 26)",
        allow_abbrev=False
    )
    parser.add_argument("input", help="Path to input audio file (WAV)")
    parser.add_argument("output", nargs="?", default=None, help="Path to output WAV file")
    parser.add_argument("--delay", type=float, default=375.0, help="Delay time in ms (default: 375.0)")
    parser.add_argument("--feedback", type=float, default=45.0, help="Feedback percentage 0-100 (default: 45.0)")
    parser.add_argument("--damping", type=float, default=3800.0, help="High-cut damping frequency in Hz (default: 3800.0)")
    parser.add_argument("--flutter", type=float, default=0.12, help="Tape flutter modulation percentage (default: 0.12)")
    parser.add_argument("--drive", type=float, default=1.3, help="Feedback saturation drive factor (default: 1.3)")
    parser.add_argument("--mix", type=float, default=35.0, help="Dry/Wet mix percentage 0-100 (default: 35.0)")
    parser.add_argument("--no-ping-pong", action="store_true", help="Disable alternating stereo ping-pong bounce")

    args = parser.parse_args()

    try:
        res = run_tape_echo(
            args.input,
            output_path=args.output,
            delay_ms=args.delay,
            feedback_pct=args.feedback,
            damping_hz=args.damping,
            flutter_pct=args.flutter,
            drive=args.drive,
            dry_wet_pct=args.mix,
            ping_pong=not args.no_ping_pong
        )
        print("=" * 60)
        print("  STEREO PING-PONG & MULTI-TAP TAPE ECHO STUDIO")
        print("=" * 60)
        print(f"Input File    : {res['input_path']}")
        print(f"Output File   : {res['output_path']}")
        print(f"Delay / Feed  : {res['delay_ms']:.1f}ms | Feedback: {res['feedback_pct']:.1f}%")
        print(f"Mode / Damp   : {'Stereo Ping-Pong' if res['ping_pong'] else 'Standard Stereo'} | Damping: {res['damping_hz']:.0f} Hz")
        print(f"Dry/Wet Mix   : {res['dry_wet_pct']:.1f}% (Drive: {res['drive']:.1f}x, Flutter: {res['flutter_pct']:.2f}%)")
        print(f"In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
        print(f"Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
        print(f"Duration      : {res['duration_sec']:.2f}s @ {res['sample_rate']} Hz")
        print("=" * 60)
    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
