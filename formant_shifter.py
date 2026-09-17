"""
formant_shifter.py - Multi-Rate Pitch Shifter & Formant-Preserving Vocal Resizer
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Audiophile spectral pitch shifter and vocal formant manipulator:
- Independent pitch transposition (+/- 12 semitones / 1 octave)
- True formant preservation: eliminates the "chipmunk" / "munchkin" effect
- Vocal tract resizer: independent formant scaling (0.70x deeper chest resonance to 1.40x youthful head voice)
- High-resolution STFT phase vocoder with cepstral spectral envelope extraction
- Overlap-Add (OLA) reconstruction with Hann windowing and zero phase distortion
- 24-bit PCM stereo WAV master export
"""

import os
import sys
import math
import wave
import struct
import argparse
from typing import Dict, List, Optional, Tuple, Any

import numpy as np


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
            data = data.reshape(-1, n_ch).T[:2]
        else:
            data = np.vstack([data, data])
        return data, sr

    raise ValueError(f"Unsupported audio format: {file_path}")


def write_stereo_wav(output_path: str, left: np.ndarray, right: np.ndarray, sample_rate: int):
    """Writes stereo float32 channels into 24-bit PCM WAV."""
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    num_samples = min(len(left), len(right))
    l_int = np.clip(left[:num_samples] * 8388607.0, -8388608.0, 8388607.0).astype(np.int32)
    r_int = np.clip(right[:num_samples] * 8388607.0, -8388608.0, 8388607.0).astype(np.int32)

    interleaved = np.empty(num_samples * 2, dtype=np.int32)
    interleaved[0::2] = l_int
    interleaved[1::2] = r_int

    raw_24 = bytearray(num_samples * 6)
    u_vals = interleaved.view(np.uint32)
    b0 = (u_vals & 0xFF).astype(np.uint8)
    b1 = ((u_vals >> 8) & 0xFF).astype(np.uint8)
    b2 = ((u_vals >> 16) & 0xFF).astype(np.uint8)
    raw_24[0::3] = b0.tobytes()
    raw_24[1::3] = b1.tobytes()
    raw_24[2::3] = b2.tobytes()

    fmt_chunk = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 2, sample_rate, sample_rate * 6, 6, 24)
    data_chunk = b"data" + struct.pack("<I", len(raw_24)) + bytes(raw_24)
    riff_header = b"RIFF" + struct.pack("<I", 4 + len(fmt_chunk) + len(data_chunk)) + b"WAVE"

    with open(output_path, "wb") as f:
        f.write(riff_header)
        f.write(fmt_chunk)
        f.write(data_chunk)


def extract_spectral_envelope(mag: np.ndarray, lifter_cutoff: int = 32) -> np.ndarray:
    """
    Extracts smooth vocal tract formant envelope using cepstral liftering.
    Separates the slow spectral shape (formants) from fast harmonic ripples (pitch).
    """
    log_mag = np.log(np.maximum(mag, 1e-6))
    cepstrum = np.fft.irfft(log_mag)

    # Lifter window: keep low quefrency components (formant resonance)
    lifter = np.zeros_like(cepstrum)
    lifter[:lifter_cutoff] = 1.0
    lifter[-lifter_cutoff + 1:] = 1.0
    smooth_cep = cepstrum * lifter

    smooth_log_mag = np.fft.rfft(smooth_cep, n=len(cepstrum))
    envelope = np.exp(np.real(smooth_log_mag[:len(mag)]))
    return np.maximum(envelope, 1e-5)


def shift_pitch_and_formants_channel(
    samples: np.ndarray,
    sample_rate: int,
    pitch_semitones: float,
    formant_ratio: float,
    preserve_formants: bool = True
) -> np.ndarray:
    """
    Shifts pitch and modifies vocal formants on a mono audio channel using
    STFT phase vocoder and cepstral envelope re-imposition.
    """
    if abs(pitch_semitones) < 0.01 and abs(formant_ratio - 1.0) < 0.01:
        return np.copy(samples)

    pitch_ratio = 2.0 ** (pitch_semitones / 12.0)
    effective_formant_ratio = formant_ratio if not preserve_formants else (formant_ratio / pitch_ratio)

    n_fft = 2048
    hop_size = 512
    window = np.hanning(n_fft).astype(np.float64)

    # Pad input
    pad_len = n_fft
    padded = np.pad(samples, (pad_len, pad_len), mode="reflect")
    num_frames = (len(padded) - n_fft) // hop_size

    # Phase vocoder synthesis parameters
    synth_hop = hop_size
    analysis_hop = int(round(hop_size / pitch_ratio))
    if analysis_hop < 64:
        analysis_hop = 64

    omega = 2.0 * np.pi * np.arange(n_fft // 2 + 1) * synth_hop / n_fft
    phase_acc = np.zeros(n_fft // 2 + 1, dtype=np.float64)
    last_phase = np.zeros(n_fft // 2 + 1, dtype=np.float64)

    # Output buffer
    out_len = int(len(samples) * pitch_ratio) + n_fft * 2
    out_buf = np.zeros(out_len, dtype=np.float64)
    win_sum = np.zeros(out_len, dtype=np.float64)

    n_bins = n_fft // 2 + 1
    bin_indices = np.arange(n_bins)

    for i in range(num_frames):
        a_start = i * analysis_hop
        if a_start + n_fft > len(padded):
            break

        frame = padded[a_start:a_start + n_fft] * window
        spectrum = np.fft.rfft(frame)
        mag = np.abs(spectrum)
        phase = np.angle(spectrum)

        # 1. Extract Formant Envelope
        envelope = extract_spectral_envelope(mag, lifter_cutoff=28)
        residual = mag / envelope

        # 2. Phase Vocoder Pitch Propagation
        d_phase = phase - last_phase - (2.0 * np.pi * np.arange(n_bins) * analysis_hop / n_fft)
        d_phase = (d_phase + np.pi) % (2.0 * np.pi) - np.pi
        freq_est = (2.0 * np.pi * np.arange(n_bins) / n_fft) + (d_phase / analysis_hop)
        phase_acc += freq_est * synth_hop
        last_phase = phase

        # 3. Formant Envelope Transformation
        # If preserving formants: apply original envelope to shifted residual
        # If resizing vocal tract: scale envelope frequency axis by effective_formant_ratio
        if abs(effective_formant_ratio - 1.0) > 0.005:
            scaled_bins = np.clip(bin_indices / effective_formant_ratio, 0, n_bins - 1)
            target_env = np.interp(scaled_bins, bin_indices, envelope)
        else:
            target_env = envelope

        # 4. Reconstruct Spectrum
        synth_mag = residual * target_env
        synth_spec = synth_mag * np.exp(1j * phase_acc)
        synth_frame = np.fft.irfft(synth_spec, n=n_fft) * window

        # 5. Overlap-Add
        s_start = i * synth_hop
        if s_start + n_fft <= out_len:
            out_buf[s_start:s_start + n_fft] += synth_frame
            win_sum[s_start:s_start + n_fft] += window * window

    # Normalize window overlap
    non_zero = win_sum > 1e-4
    out_buf[non_zero] /= win_sum[non_zero]

    # Time-stretch resample back to original length so tempo is preserved
    target_samples = len(samples)
    curr_samples = min(len(out_buf) - pad_len, int(target_samples * pitch_ratio))
    clipped_out = out_buf[pad_len:pad_len + curr_samples]

    if len(clipped_out) > 0 and len(clipped_out) != target_samples:
        orig_indices = np.linspace(0, len(clipped_out) - 1, target_samples)
        res = np.interp(orig_indices, np.arange(len(clipped_out)), clipped_out)
    else:
        res = clipped_out[:target_samples]

    return res.astype(np.float32)


def process_formant_shifter(
    input_path: str,
    output_path: Optional[str] = None,
    pitch_semitones: float = 0.0,
    formant_ratio: float = 1.0,
    preserve_formants: bool = True
) -> Dict[str, Any]:
    """
    Shifts pitch and scales vocal formants while preserving rhythm/duration.
    
    Args:
        input_path: Input audio file (WAV, FLAC)
        output_path: Target output WAV path
        pitch_semitones: Pitch offset (-12.0 to +12.0 semitones)
        formant_ratio: Vocal tract scale (0.75x = deep/masculine to 1.35x = youthful/feminine)
        preserve_formants: Whether to lock original vocal timbre during pitch shifts
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_formant.wav"

    channels, sr = read_audio_stereo(input_path)
    left, right = channels[0], channels[1]

    out_l = shift_pitch_and_formants_channel(
        left, sr, pitch_semitones, formant_ratio, preserve_formants
    )
    out_r = shift_pitch_and_formants_channel(
        right, sr, pitch_semitones, formant_ratio, preserve_formants
    )

    # Normalize ceiling to avoid clipping
    peak = max(np.max(np.abs(out_l)), np.max(np.abs(out_r)))
    if peak > 0.99:
        scale = 0.98 / peak
        out_l *= scale
        out_r *= scale
        peak_dbfs = -0.18
    else:
        peak_dbfs = 20.0 * math.log10(max(1e-7, float(peak)))

    write_stereo_wav(output_path, out_l, out_r, sample_rate=sr)

    timbre_desc = "Natural (Formant Locked)" if preserve_formants else f"{formant_ratio:.2f}x Vocal Tract Scaling"
    if formant_ratio > 1.08:
        timbre_desc += " [Youthful / Bright]"
    elif formant_ratio < 0.92:
        timbre_desc += " [Deep Chest / Authoritative]"

    return {
        "success": True,
        "input_file": os.path.basename(input_path),
        "output_path": output_path,
        "sample_rate": sr,
        "pitch_semitones": round(pitch_semitones, 2),
        "pitch_ratio": f"{2.0 ** (pitch_semitones / 12.0):.3f}x",
        "formant_ratio": round(formant_ratio, 2),
        "preserve_formants": preserve_formants,
        "timbre_character": timbre_desc,
        "peak_dbfs": round(peak_dbfs, 2),
    }


def format_formant_card(res: Dict[str, Any]) -> str:
    """Formats ASCII-safe report card for pitch & formant processing."""
    lines = []
    lines.append("=" * 65)
    lines.append("  PITCH SHIFTER & FORMANT VOCAL RESIZER STUDIO")
    lines.append("=" * 65)
    lines.append(f"  Input Track    : {res.get('input_file', '')}")
    lines.append(f"  Pitch Offset   : {res.get('pitch_semitones'):+0.1f} semitones ({res.get('pitch_ratio')})")
    lines.append(f"  Formant Lock   : {'[+] Enabled (Chipmunk Free)' if res.get('preserve_formants') else '[-] Disabled'}")
    lines.append(f"  Vocal Tract    : {res.get('formant_ratio')}x - {res.get('timbre_character')}")
    lines.append(f"  Master Peak    : {res.get('peak_dbfs')} dBFS (24-bit Stereo Master)")
    lines.append(f"  Output File    : {os.path.basename(res.get('output_path', ''))}")
    lines.append("=" * 65)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sonance Pitch & Formant Vocal Studio")
    parser.add_argument("input_file", help="Path to audio file (WAV/FLAC)")
    parser.add_argument("output_file", nargs="?", help="Output 24-bit WAV file")
    parser.add_argument("--pitch", type=float, default=0.0, help="Pitch shift in semitones (-12 to +12, default: 0)")
    parser.add_argument("--formant", type=float, default=1.0, help="Formant vocal tract scale (0.75 to 1.35, default: 1.0)")
    parser.add_argument("--preserve-formants", action="store_true", default=True, help="Lock formants to eliminate chipmunk effect")
    parser.add_argument("--no-preserve-formants", dest="preserve_formants", action="store_false", help="Allow formants to pitch shift naturally")

    args = parser.parse_args()

    res = process_formant_shifter(
        args.input_file,
        output_path=args.output_file,
        pitch_semitones=args.pitch,
        formant_ratio=args.formant,
        preserve_formants=args.preserve_formants,
    )
    print(format_formant_card(res))


if __name__ == "__main__":
    main()
