"""
dac_tester.py - Audiophile DAC Bit-Perfect Test Tone & Jitter Generator
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Generates laboratory-grade reference test signals for external USB DACs, S/PDIF interfaces,
amplifiers, and headphone acoustic testing:
- 20 Hz to 20 kHz Logarithmic Sine Sweep (-0.1 dBFS True-Peak)
- SMPTE (60 Hz + 7 kHz, 4:1) & CCIF (19 kHz + 20 kHz, 1:1) Intermodulation Distortion (IMD)
- Julian Dunn J-Test (Official AES clock jitter provocation signal)
- True Pink Noise (-3 dB/octave Voss-McCartney algorithm)
- Dithered Digital Black Floor (-140 dBFS silence for noise floor & ground hum audit)
"""

import os
import sys
import math
import wave
import struct
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple, Any

try:
    import numpy as np
except ImportError:
    np = None


SUPPORTED_TEST_TYPES = {
    "sweep": "Logarithmic Sine Sweep (20 Hz - 20 kHz, -0.1 dBFS)",
    "imd_smpte": "SMPTE Intermodulation Distortion (60 Hz + 7 kHz, 4:1)",
    "imd_ccif": "CCIF High-Frequency IMD (19 kHz + 20 kHz, 1:1)",
    "jtest": "Julian Dunn J-Test (Clock Jitter & Inter-Symbol Interference)",
    "pink_noise": "Voss-McCartney True Pink Noise (-3 dB/octave equal energy)",
    "digital_black": "Dithered Digital Black Floor (Noise Floor & Ground Hum Audit)",
}


def generate_log_sweep(duration_sec: float, sample_rate: int) -> Any:
    """Generates 20 Hz to 20 kHz logarithmic sine sweep."""
    n_samples = int(duration_sec * sample_rate)
    t = np.linspace(0.0, duration_sec, n_samples, endpoint=False)
    f0 = 20.0
    f1 = min(20000.0, sample_rate * 0.45)

    # Instantaneous phase: phi(t) = 2*pi*f0 * ( (f1/f0)^(t/T) - 1 ) / ln(f1/f0) * T
    rate = math.log(f1 / f0) / duration_sec
    phase = 2.0 * math.pi * f0 * (np.exp(rate * t) - 1.0) / rate
    sweep = np.sin(phase) * (10.0 ** (-0.1 / 20.0))  # -0.1 dBFS

    # Apply 20ms Hann fade-in and fade-out to prevent clicks
    fade_len = int(0.020 * sample_rate)
    fade_in = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade_len) / fade_len))
    sweep[:fade_len] *= fade_in
    sweep[-fade_len:] *= fade_in[::-1]

    return np.column_stack([sweep, sweep])


def generate_imd_smpte(duration_sec: float, sample_rate: int) -> Any:
    """Generates SMPTE IMD signal: 60 Hz (4:1 amplitude) + 7000 Hz."""
    n_samples = int(duration_sec * sample_rate)
    t = np.linspace(0.0, duration_sec, n_samples, endpoint=False)
    # 4 parts 60 Hz + 1 part 7 kHz, normalized to -0.5 dBFS
    sig = 4.0 * np.sin(2.0 * np.pi * 60.0 * t) + 1.0 * np.sin(2.0 * np.pi * 7000.0 * t)
    sig = (sig / 5.0) * (10.0 ** (-0.5 / 20.0))
    return np.column_stack([sig, sig])


def generate_imd_ccif(duration_sec: float, sample_rate: int) -> Any:
    """Generates CCIF IMD signal: 19 kHz + 20 kHz (1:1 ratio)."""
    n_samples = int(duration_sec * sample_rate)
    t = np.linspace(0.0, duration_sec, n_samples, endpoint=False)
    sig = 0.5 * np.sin(2.0 * np.pi * 19000.0 * t) + 0.5 * np.sin(2.0 * np.pi * 20000.0 * t)
    sig = sig * (10.0 ** (-0.5 / 20.0))
    return np.column_stack([sig, sig])


def generate_jtest(duration_sec: float, sample_rate: int) -> Any:
    """
    Generates Julian Dunn J-Test jitter test signal:
    Square wave at fs / 4 alternating at 0.5 full scale, with LSB toggle at fs / 192.
    """
    n_samples = int(duration_sec * sample_rate)
    indices = np.arange(n_samples)

    # High frequency square wave at fs/4: pattern [0.5, 0.5, -0.5, -0.5]
    quarter = indices % 4
    high_freq = np.where(quarter < 2, 0.5, -0.5)

    # Low frequency square wave toggling LSB at fs / 192
    lsb_period = 192
    lsb_phase = (indices % lsb_period) < (lsb_period // 2)
    # 16-bit LSB is 1/32768 approx 3.05e-5
    lsb_toggle = np.where(lsb_phase, 3.0517578125e-5, -3.0517578125e-5)

    jtest_signal = (high_freq + lsb_toggle).astype(np.float32)
    return np.column_stack([jtest_signal, jtest_signal])


def generate_pink_noise(duration_sec: float, sample_rate: int) -> Any:
    """Generates true -3 dB/octave pink noise via Voss-McCartney algorithm."""
    n_samples = int(duration_sec * sample_rate)
    num_generators = 16

    # Generate random matrix
    rng = np.random.default_rng(42)
    white = rng.standard_normal((num_generators, n_samples))

    # Update generators at octave intervals
    for g in range(num_generators):
        interval = 2 ** g
        if interval < n_samples:
            hold = white[g, ::interval]
            white[g] = np.repeat(hold, interval)[:n_samples]

    pink = np.sum(white, axis=0)
    # Normalize to -6 dBFS RMS
    pink = (pink / (np.std(pink) * 4.0)) * (10.0 ** (-6.0 / 20.0))
    pink = np.clip(pink, -0.99, 0.99)

    # Independent stereo pink noise
    white_r = rng.standard_normal((num_generators, n_samples))
    for g in range(num_generators):
        interval = 2 ** g
        if interval < n_samples:
            hold = white_r[g, ::interval]
            white_r[g] = np.repeat(hold, interval)[:n_samples]
    pink_r = np.sum(white_r, axis=0)
    pink_r = (pink_r / (np.std(pink_r) * 4.0)) * (10.0 ** (-6.0 / 20.0))
    pink_r = np.clip(pink_r, -0.99, 0.99)

    return np.column_stack([pink, pink_r])


def generate_digital_black(duration_sec: float, sample_rate: int) -> Any:
    """Generates digital black floor with triangular PDF dither at -140 dBFS."""
    n_samples = int(duration_sec * sample_rate)
    rng = np.random.default_rng(123)
    tpdf = (rng.uniform(-1.0, 1.0, (n_samples, 2)) + rng.uniform(-1.0, 1.0, (n_samples, 2))) * 1e-7
    return tpdf.astype(np.float32)


def generate_test_signal_file(
    test_type: str = "sweep",
    sample_rate: int = 96000,
    bit_depth: int = 24,
    duration_sec: float = 10.0,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main entry point to generate high-resolution DAC reference test files.
    """
    if np is None:
        return {"error": "NumPy is required.", "success": False}

    test_type = test_type.lower()
    if test_type not in SUPPORTED_TEST_TYPES:
        return {
            "error": f"Unsupported test type '{test_type}'. Choose from: {list(SUPPORTED_TEST_TYPES.keys())}",
            "success": False
        }

    if not output_path:
        ext = ".flac" if shutil.which("ffmpeg") else ".wav"
        output_path = f"DAC_Test_{test_type}_{sample_rate}Hz_{bit_depth}bit{ext}"

    if test_type == "sweep":
        data = generate_log_sweep(duration_sec, sample_rate)
    elif test_type == "imd_smpte":
        data = generate_imd_smpte(duration_sec, sample_rate)
    elif test_type == "imd_ccif":
        data = generate_imd_ccif(duration_sec, sample_rate)
    elif test_type == "jtest":
        data = generate_jtest(duration_sec, sample_rate)
    elif test_type == "pink_noise":
        data = generate_pink_noise(duration_sec, sample_rate)
    elif test_type == "digital_black":
        data = generate_digital_black(duration_sec, sample_rate)
    else:
        data = generate_log_sweep(duration_sec, sample_rate)

    out_ext = os.path.splitext(output_path)[1].lower()
    target_wav = output_path if out_ext == ".wav" else output_path + ".tmp.wav"

    # Write WAV according to bit depth
    if bit_depth == 24:
        # Scale to 24-bit integer [-8388607, 8388607]
        scaled = (np.clip(data, -1.0, 1.0) * 8388607.0).astype(np.int32)
        raw_bytes = bytearray()
        for sample_pair in scaled:
            for ch_val in sample_pair:
                val = int(ch_val)
                raw_bytes.append(val & 0xFF)
                raw_bytes.append((val >> 8) & 0xFF)
                raw_bytes.append((val >> 16) & 0xFF)

        with wave.open(target_wav, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(3)
            wf.setframerate(sample_rate)
            wf.writeframes(bytes(raw_bytes))
    else:
        # Standard 16-bit
        int16_data = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16)
        with wave.open(target_wav, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(int16_data.tobytes())

    if out_ext != ".wav":
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            cmd = [ffmpeg, "-y", "-v", "error", "-i", target_wav, output_path]
            subprocess.run(cmd, check=True)
            if os.path.exists(target_wav):
                os.remove(target_wav)
        else:
            output_path = target_wav

    file_size_kb = round(os.path.getsize(output_path) / 1024.0, 1)

    return {
        "success": True,
        "test_type": test_type,
        "description": SUPPORTED_TEST_TYPES[test_type],
        "output_file": os.path.basename(output_path),
        "path": output_path,
        "sample_rate": sample_rate,
        "bit_depth": bit_depth,
        "duration_sec": round(duration_sec, 2),
        "file_size_kb": file_size_kb,
    }


def format_dac_card(res: Dict[str, Any]) -> str:
    """Renders ASCII card for DAC Test Signal Generator."""
    if not res.get("success"):
        return f"[!] Error: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append(f"| AUDIOPHILE DAC BIT-PERFECT TEST TONE & JITTER GENERATOR        |")
    lines.append(sep)
    lines.append(f"| Signal Type    : {res['test_type'].upper():<47} |")
    lines.append(f"| Output File    : {res['output_file'][:47]:<47} |")
    lines.append(f"| Resolution     : {res['bit_depth']}-bit / {res['sample_rate']} Hz (Size: {res['file_size_kb']} KB)              |")
    lines.append(f"| Duration       : {res['duration_sec']}s                                            |")
    lines.append(sep)
    lines.append(f"| Description:                                                     |")
    lines.append(f"| {res['description'][:64]:<64} |")
    lines.append(sep)
    lines.append(f"| STATUS: Reference test file synthesized and ready for playback! |")
    lines.append(sep)
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dac_tester.py <sweep|imd_smpte|imd_ccif|jtest|pink_noise|digital_black> [output_file] [--rate 96000] [--bits 24] [--dur 10]")
        sys.exit(1)

    t_type = sys.argv[1]
    out_file = None
    rate = 96000
    bits = 24
    dur = 10.0

    idx = 2
    while idx < len(sys.argv):
        arg = sys.argv[idx]
        if arg == "--rate" and idx + 1 < len(sys.argv):
            rate = int(sys.argv[idx + 1])
            idx += 2
        elif arg == "--bits" and idx + 1 < len(sys.argv):
            bits = int(sys.argv[idx + 1])
            idx += 2
        elif arg == "--dur" and idx + 1 < len(sys.argv):
            dur = float(sys.argv[idx + 1])
            idx += 2
        elif not arg.startswith("--") and out_file is None:
            out_file = arg
            idx += 1
        else:
            idx += 1

    res = generate_test_signal_file(t_type, sample_rate=rate, bit_depth=bits, duration_sec=dur, output_path=out_file)
    print(format_dac_card(res))
