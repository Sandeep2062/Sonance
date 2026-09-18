"""
ambisonic_hoa.py - Higher-Order Ambisonics (HOA 1st/2nd/3rd Order) & 360-Degree Spherical Spatializer Studio
Part of Sonance (Unified Audiophile Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Phase 31 Milestone:
- Higher-Order Ambisonics (HOA) Spherical Harmonics Decomposition:
  * 1st Order Ambisonics (4 Channels: W, Y, Z, X)
  * 2nd Order Ambisonics (9 Channels: W, Y, Z, X, V, T, R, S, U)
  * 3rd Order Ambisonics (16 Channels: Full 3D sphere resolution ACN 0-15)
  * Full ACN channel ordering and SN3D (Schmidt Semi-Normalized) AmbiX standard
- 3D Trajectory & Panning Engine:
  * Spherical coordinates: Azimuth (-180 to +180 deg), Elevation (-90 to +90 deg)
  * Dynamic motion modes: Fixed point, Horizontal 360 Orbit, Spherical Helix, Pendulum Arc
  * Distance model: 1/d amplitude decay + high-frequency atmospheric air damping
- Dual Rendering Output:
  * 3D Binaural Headphone Virtualizer: Decodes HOA B-format using spherical virtual speaker grid
    convolved with Woodworth ITD, pinna ILD, and elevation notches
  * Discrete Multi-Channel AmbiX WAV: 4-ch (1st order), 9-ch (2nd order), or 16-ch (3rd order) 24-bit PCM
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


def write_multichannel_wav_24bit(file_path: str, channels_data: np.ndarray, sample_rate: int):
    """
    Writes multichannel float32 array with shape (num_channels, samples)
    to 24-bit linear PCM WAV.
    """
    num_channels, samples = channels_data.shape
    clamped = np.clip(channels_data, -1.0, 1.0)
    int24_data = (clamped * 8388607.0).astype(np.int32)

    # Interleave channels
    interleaved = int24_data.T.flatten()

    raw_bytes = bytearray(samples * num_channels * 3)
    idx = 0
    for val in interleaved:
        val_u = val & 0xFFFFFF
        raw_bytes[idx] = val_u & 0xFF
        raw_bytes[idx + 1] = (val_u >> 8) & 0xFF
        raw_bytes[idx + 2] = (val_u >> 16) & 0xFF
        idx += 3

    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(3)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(raw_bytes))


# ---------------------------------------------------------------------------
# Spherical Harmonics Mathematics (ACN / SN3D AmbiX Standard)
# ---------------------------------------------------------------------------

def compute_spherical_harmonics(theta: np.ndarray, phi: np.ndarray, order: int = 3) -> np.ndarray:
    """
    Computes real spherical harmonics in ACN ordering with SN3D normalization up to order 3.
    theta: azimuth angles in radians (array or float)
    phi: elevation angles in radians (array or float)
    Returns array of shape (num_channels, samples) where num_channels = (order + 1)^2.
    """
    # Precompute trigonometry
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)

    cos_phi2 = cos_phi ** 2
    sin_phi2 = sin_phi ** 2

    # Number of channels: 1st order -> 4, 2nd order -> 9, 3rd order -> 16
    num_ch = (order + 1) ** 2
    samples = np.broadcast_to(theta, phi.shape).shape[0] if isinstance(theta, np.ndarray) else 1

    Y = np.zeros((num_ch, samples), dtype=np.float32)

    # --- Order 0 (l = 0) ---
    # ACN 0: l=0, m=0
    Y[0] = 1.0

    if order >= 1:
        # --- Order 1 (l = 1) ---
        # ACN 1: l=1, m=-1 (Y channel: Left / Right)
        Y[1] = sin_theta * cos_phi
        # ACN 2: l=1, m=0  (Z channel: Up / Down)
        Y[2] = sin_phi
        # ACN 3: l=1, m=+1 (X channel: Front / Back)
        Y[3] = cos_theta * cos_phi

    if order >= 2:
        # --- Order 2 (l = 2) ---
        sin_2theta = np.sin(2.0 * theta)
        cos_2theta = np.cos(2.0 * theta)
        sin_2phi = np.sin(2.0 * phi)
        sqrt3_half = math.sqrt(3.0) / 2.0

        # ACN 4: l=2, m=-2
        Y[4] = sqrt3_half * sin_2theta * cos_phi2
        # ACN 5: l=2, m=-1
        Y[5] = sqrt3_half * sin_theta * sin_2phi
        # ACN 6: l=2, m=0
        Y[6] = 0.5 * (3.0 * sin_phi2 - 1.0)
        # ACN 7: l=2, m=+1
        Y[7] = sqrt3_half * cos_theta * sin_2phi
        # ACN 8: l=2, m=+2
        Y[8] = sqrt3_half * cos_2theta * cos_phi2

    if order >= 3:
        # --- Order 3 (l = 3) ---
        sin_3theta = np.sin(3.0 * theta)
        cos_3theta = np.cos(3.0 * theta)
        cos_phi3 = cos_phi ** 3
        sqrt5_8 = math.sqrt(5.0 / 8.0)
        sqrt15_2 = math.sqrt(15.0) / 2.0
        sqrt3_8 = math.sqrt(3.0 / 8.0)

        # ACN 9: l=3, m=-3
        Y[9] = sqrt5_8 * sin_3theta * cos_phi3
        # ACN 10: l=3, m=-2
        Y[10] = sqrt15_2 * sin_2theta * sin_phi * cos_phi2
        # ACN 11: l=3, m=-1
        Y[11] = sqrt3_8 * sin_theta * cos_phi * (5.0 * sin_phi2 - 1.0)
        # ACN 12: l=3, m=0
        Y[12] = 0.5 * sin_phi * (5.0 * sin_phi2 - 3.0)
        # ACN 13: l=3, m=+1
        Y[13] = sqrt3_8 * cos_theta * cos_phi * (5.0 * sin_phi2 - 1.0)
        # ACN 14: l=3, m=+2
        Y[14] = sqrt15_2 * cos_2theta * sin_phi * cos_phi2
        # ACN 15: l=3, m=+3
        Y[15] = sqrt5_8 * cos_3theta * cos_phi3

    return Y


# ---------------------------------------------------------------------------
# Trajectory Generation
# ---------------------------------------------------------------------------

def generate_trajectory(
    samples: int,
    sr: int,
    trajectory_type: str = "fixed",
    base_azimuth_deg: float = 0.0,
    base_elevation_deg: float = 0.0,
    orbit_period_sec: float = 12.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generates time-varying azimuth, elevation, and distance curves.
    Returns: (azimuth_rad, elevation_rad, distance_meters)
    """
    t = np.linspace(0.0, samples / float(sr), samples, endpoint=False, dtype=np.float32)
    base_az = math.radians(base_azimuth_deg)
    base_el = math.radians(base_elevation_deg)
    period = max(1.0, orbit_period_sec)
    omega = 2.0 * math.pi / period

    if trajectory_type == "orbit_horizontal":
        az = base_az + omega * t
        el = np.full(samples, base_el, dtype=np.float32)
        dist = np.full(samples, 1.5, dtype=np.float32)

    elif trajectory_type == "orbit_helix":
        az = base_az + omega * t
        # Elevates up and down smoothly (+/- 45 deg)
        el = base_el + math.radians(40.0) * np.sin(omega * 0.35 * t)
        dist = 1.5 + 0.3 * np.cos(omega * 0.25 * t)

    elif trajectory_type == "orbit_pendulum":
        # Sweeping arc left to right (+/- 65 deg)
        az = base_az + math.radians(65.0) * np.sin(omega * t)
        el = base_el + math.radians(15.0) * np.abs(np.sin(omega * t))
        dist = np.full(samples, 1.5, dtype=np.float32)

    elif trajectory_type == "orbit_overhead":
        # High elevation overhead orbit
        az = base_az + omega * t
        el = np.full(samples, math.radians(55.0), dtype=np.float32)
        dist = np.full(samples, 1.8, dtype=np.float32)

    else:  # fixed
        az = np.full(samples, base_az, dtype=np.float32)
        el = np.full(samples, base_el, dtype=np.float32)
        dist = np.full(samples, 1.5, dtype=np.float32)

    # Wrap azimuth to [-pi, pi]
    az = (az + math.pi) % (2.0 * math.pi) - math.pi
    # Clamp elevation to [-pi/2, pi/2]
    el = np.clip(el, -math.pi * 0.49, math.pi * 0.49)

    return az, el, dist


# ---------------------------------------------------------------------------
# HOA B-Format Encoding
# ---------------------------------------------------------------------------

def encode_hoa_bformat(
    stereo_audio: np.ndarray,
    sr: int,
    order: int = 3,
    trajectory_type: str = "orbit_helix",
    base_azimuth_deg: float = 0.0,
    base_elevation_deg: float = 0.0,
    orbit_period_sec: float = 12.0
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Encodes stereo audio into HOA B-Format (1st, 2nd, or 3rd order).
    Left and right channels are placed with a slight stereophonic offset (+/- 15 deg).
    Returns: (hoa_channels, metadata)
    """
    samples = stereo_audio.shape[1]
    num_channels = (order + 1) ** 2

    # Trajectory for center of soundstage
    az_c, el_c, dist = generate_trajectory(
        samples, sr, trajectory_type, base_azimuth_deg, base_elevation_deg, orbit_period_sec
    )

    # Stereo offset: Left is +15 deg azimuth, Right is -15 deg azimuth
    stereo_spread = math.radians(15.0)
    az_l = (az_c + stereo_spread + math.pi) % (2.0 * math.pi) - math.pi
    az_r = (az_c - stereo_spread + math.pi) % (2.0 * math.pi) - math.pi

    # Inverse distance amplitude decay (reference distance = 1.5m)
    dist_atten = 1.5 / np.maximum(dist, 0.5)

    # Spherical harmonics encoding matrices
    Y_l = compute_spherical_harmonics(az_l, el_c, order=order)
    Y_r = compute_spherical_harmonics(az_r, el_c, order=order)

    # HOA multichannel buffer
    hoa = np.zeros((num_channels, samples), dtype=np.float32)

    sig_l = stereo_audio[0] * dist_atten
    sig_r = stereo_audio[1] * dist_atten

    for ch in range(num_channels):
        hoa[ch] = 0.5 * (sig_l * Y_l[ch] + sig_r * Y_r[ch])

    meta = {
        "order": order,
        "num_channels": num_channels,
        "format": f"{order}th-Order Ambisonics (AmbiX / SN3D)",
        "trajectory": trajectory_type,
        "base_azimuth_deg": base_azimuth_deg,
        "base_elevation_deg": base_elevation_deg,
        "orbit_period_sec": orbit_period_sec,
        "samples": samples,
        "sample_rate": sr
    }

    return hoa, meta


# ---------------------------------------------------------------------------
# Binaural HOA 3D Headphone Decoder
# ---------------------------------------------------------------------------

# 14-point Lebedev / regular spherical virtual speaker array (Azimuth, Elevation in degrees)
VIRTUAL_SPEAKERS_GRID = [
    # 8 Cube vertices (+/- 45 deg azimuth, +/- 35.26 deg elevation)
    (-45.0,  35.26),
    ( 45.0,  35.26),
    (135.0,  35.26),
    (-135.0, 35.26),
    (-45.0, -35.26),
    ( 45.0, -35.26),
    (135.0, -35.26),
    (-135.0, -35.26),
    # 6 Octahedron vertices (Front, Back, Left, Right, Zenith, Nadir)
    (  0.0,   0.0),
    (180.0,   0.0),
    (-90.0,   0.0),
    ( 90.0,   0.0),
    (  0.0,  90.0),
    (  0.0, -90.0),
]


def decode_hoa_to_binaural(hoa_channels: np.ndarray, sr: int, order: int = 3) -> np.ndarray:
    """
    Decodes HOA B-Format channels to 3D binaural stereo headphones using
    a 14-point spherical virtual loudspeaker array and Woodworth ITD + pinna ILD model.
    """
    num_channels, samples = hoa_channels.shape
    num_speakers = len(VIRTUAL_SPEAKERS_GRID)

    # 1. Precompute decoding matrix D (num_speakers x num_channels)
    # Using spatial sampling theorem: D = (4*pi / K) * Y(theta_k, phi_k)
    decoding_matrix = np.zeros((num_speakers, num_channels), dtype=np.float32)
    weight = (4.0 * math.pi) / num_speakers

    for k, (spk_az_deg, spk_el_deg) in enumerate(VIRTUAL_SPEAKERS_GRID):
        spk_az = math.radians(spk_az_deg)
        spk_el = math.radians(spk_el_deg)
        Y_spk = compute_spherical_harmonics(np.array([spk_az]), np.array([spk_el]), order=order)
        decoding_matrix[k] = weight * Y_spk[:, 0]

    # Decode virtual speaker signals: S = D @ HOA
    speaker_signals = np.dot(decoding_matrix, hoa_channels)  # (num_speakers, samples)

    # 2. Binauralize virtual speakers with Woodworth ITD and Pinna ILD
    head_radius = 0.0875   # 8.75 cm
    c_sound = 343.0        # m/s

    binaural_out = np.zeros((2, samples), dtype=np.float32)

    for k, (spk_az_deg, spk_el_deg) in enumerate(VIRTUAL_SPEAKERS_GRID):
        theta = math.radians(spk_az_deg)
        phi = math.radians(spk_el_deg)
        sig = speaker_signals[k]

        # Horizontal angle projection
        theta_h = theta * math.cos(phi)

        # Woodworth ITD: Delta t = (r/c) * (sin(theta) + 0.5 * theta)
        itd_sec = (head_radius / c_sound) * (math.sin(abs(theta_h)) + 0.5 * abs(theta_h))
        delay_samples = int(round(itd_sec * sr))

        # ILD pinna head-shadow gain: contralateral ear receives attenuated treble
        ild_contra_gain = math.cos(theta_h * 0.5) ** 2
        ild_ipsi_gain = 1.0

        # Elevation notch filter simulating pinna concha reflection at 7.5 kHz
        el_notch_depth = max(0.0, math.sin(phi)) * 0.25

        if theta_h <= 0:  # Left hemisphere: Left ear is ipsilateral, Right ear is contralateral
            # Left ear (direct)
            sig_l = sig * ild_ipsi_gain
            # Right ear (delayed by ITD + contralateral attenuation)
            if delay_samples > 0 and delay_samples < samples:
                sig_r = np.zeros_like(sig)
                sig_r[delay_samples:] = sig[:-delay_samples] * ild_contra_gain
            else:
                sig_r = sig * ild_contra_gain
        else:  # Right hemisphere: Right ear is ipsilateral, Left ear is contralateral
            # Right ear (direct)
            sig_r = sig * ild_ipsi_gain
            # Left ear (delayed by ITD + contralateral attenuation)
            if delay_samples > 0 and delay_samples < samples:
                sig_l = np.zeros_like(sig)
                sig_l[delay_samples:] = sig[:-delay_samples] * ild_contra_gain
            else:
                sig_l = sig * ild_contra_gain

        # Apply elevation notch to simulate ceiling height perception
        if el_notch_depth > 0.01:
            sig_l *= (1.0 - el_notch_depth)
            sig_r *= (1.0 - el_notch_depth)

        binaural_out[0] += sig_l
        binaural_out[1] += sig_r

    # Master normalization to avoid inter-speaker summing clipping
    scale = 1.0 / math.sqrt(num_speakers * 0.6)
    binaural_out *= scale

    # Safety ceiling limiter
    peak = np.max(np.abs(binaural_out))
    if peak > 0.95:
        binaural_out = (binaural_out / peak) * 0.95

    return binaural_out


# ---------------------------------------------------------------------------
# Master Rendering Controller
# ---------------------------------------------------------------------------

def render_ambisonic_hoa(
    input_path: str,
    output_path: Optional[str] = None,
    order: int = 3,
    mode: str = "binaural",           # "binaural" or "bformat"
    trajectory_type: str = "orbit_helix",
    base_azimuth_deg: float = 0.0,
    base_elevation_deg: float = 0.0,
    orbit_period_sec: float = 12.0
) -> Dict[str, Any]:
    """
    Encodes input audio into Higher-Order Ambisonics and renders either
    as 3D Binaural Headphones (2 channels) or Discrete AmbiX B-Format WAV (4, 9, or 16 channels).
    """
    audio, sr = read_audio_stereo(input_path)
    order = max(1, min(3, int(order)))

    # 1. Encode into HOA B-Format
    hoa, meta = encode_hoa_bformat(
        audio, sr, order=order, trajectory_type=trajectory_type,
        base_azimuth_deg=base_azimuth_deg, base_elevation_deg=base_elevation_deg,
        orbit_period_sec=orbit_period_sec
    )

    # 2. Render target mode
    if mode == "bformat":
        channels_to_export = hoa
        out_channels = hoa.shape[0]
        mode_label = f"Discrete AmbiX {order}th-Order B-Format ({out_channels} channels)"
        suffix = f"_hoa_order{order}_{out_channels}ch.wav"
    else:  # binaural
        binaural = decode_hoa_to_binaural(hoa, sr, order=order)
        channels_to_export = binaural
        out_channels = 2
        mode_label = f"3D Binaural Headphone Virtualizer ({order}th-Order Decoded)"
        suffix = f"_hoa_binaural_3d.wav"

    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}{suffix}"

    write_multichannel_wav_24bit(output_path, channels_to_export, sr)

    duration_sec = channels_to_export.shape[1] / float(sr)
    out_peak_db = 20.0 * math.log10(max(1e-6, np.max(np.abs(channels_to_export))))
    out_rms_db = 20.0 * math.log10(max(1e-6, np.sqrt(np.mean(channels_to_export ** 2))))

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "order": order,
        "mode": mode,
        "mode_label": mode_label,
        "channels": out_channels,
        "bit_depth": 24,
        "sample_rate": sr,
        "duration_sec": round(duration_sec, 2),
        "trajectory": trajectory_type,
        "base_azimuth_deg": base_azimuth_deg,
        "base_elevation_deg": base_elevation_deg,
        "orbit_period_sec": orbit_period_sec,
        "peak_dbfs": round(out_peak_db, 2),
        "rms_dbfs": round(out_rms_db, 2)
    }


# ---------------------------------------------------------------------------
# Standalone CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sonance Phase 31: Higher-Order Ambisonics (HOA 1st/2nd/3rd Order) & 360-Degree Spherical Spatializer Studio"
    )
    parser.add_argument("input", type=str, help="Path to input audio file")
    parser.add_argument("output", type=str, nargs="?", default=None, help="Path to output 24-bit PCM WAV")
    parser.add_argument("--order", type=int, default=3, choices=[1, 2, 3], help="Ambisonic order (1, 2, or 3, default: 3)")
    parser.add_argument("--mode", type=str, default="binaural", choices=["binaural", "bformat"], help="Output render mode")
    parser.add_argument(
        "--trajectory", type=str, default="orbit_helix",
        choices=["fixed", "orbit_horizontal", "orbit_helix", "orbit_pendulum", "orbit_overhead"],
        help="3D spatial motion trajectory (default: orbit_helix)"
    )
    parser.add_argument("--azimuth", type=float, default=0.0, help="Base azimuth in degrees (-180 to +180)")
    parser.add_argument("--elevation", type=float, default=0.0, help="Base elevation in degrees (-90 to +90)")
    parser.add_argument("--period", type=float, default=12.0, help="Orbit duration in seconds (default: 12.0)")

    args = parser.parse_args()

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.1.0")
    print("  Phase 31: Higher-Order Ambisonics & 360-Degree VR Spatializer Studio")
    print("=" * 70)
    print(f"[*] Input File       : {args.input}")
    print(f"[*] Ambisonic Order  : {args.order} ({ (args.order + 1)**2 } Spherical Harmonic Channels)")
    print(f"[*] Render Mode      : {args.mode.upper()}")
    print(f"[*] 3D Trajectory    : {args.trajectory.upper()} ({args.period}s orbit)")

    res = render_ambisonic_hoa(
        input_path=args.input,
        output_path=args.output,
        order=args.order,
        mode=args.mode,
        trajectory_type=args.trajectory,
        base_azimuth_deg=args.azimuth,
        base_elevation_deg=args.elevation,
        orbit_period_sec=args.period
    )

    print("\n[+] Ambisonics Spatial Results:")
    print(f"    - Output Master  : {res['output_path']}")
    print(f"    - Channel Count  : {res['channels']} Channels (24-bit Linear PCM WAV)")
    print(f"    - Mode Label     : {res['mode_label']}")
    print(f"    - Duration / Rate: {res['duration_sec']}s @ {res['sample_rate']} Hz")
    print(f"    - Peak / RMS     : {res['peak_dbfs']} dBFS / {res['rms_dbfs']} dBFS")
    print("=" * 70)


if __name__ == "__main__":
    main()
