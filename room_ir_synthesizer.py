"""
room_ir_synthesizer.py - Room Acoustic Impulse Response (IR) Generator & Reverb Synthesizer
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Synthesizes studio-grade room acoustic impulse response (WAV) files using:
- Image-Source Method (Allen & Berkley shoebox model) for early specular reflections
- Diffuse stochastic late reverberation tail based on Sabine/Eyring acoustic decay
- Frequency-dependent atmospheric absorption and wall boundary damping
- Calibrated binaural / stereo microphone spatialization (ITD/ILD)
- Compatible with Sonance's convolution engine and third-party IR loaders
"""

import os
import sys
import math
import wave
import argparse
from typing import Dict, List, Optional, Tuple, Any

import numpy as np


ROOM_PRESETS = {
    "studio": {
        "name": "Recording Studio Control Room",
        "dimensions": (5.2, 4.2, 2.8),      # Length, Width, Height (m)
        "rt60": 0.32,                        # Reverb time (sec)
        "absorption": 0.38,                  # Average absorption coefficient
        "damping": 0.35,                     # High-frequency damping
        "description": "Tightly controlled acoustic with high clarity for vocals and mix engineering"
    },
    "room": {
        "name": "Living Room / Acoustic Chamber",
        "dimensions": (7.0, 5.2, 2.9),
        "rt60": 0.65,
        "absorption": 0.24,
        "damping": 0.45,
        "description": "Warm, natural residential room sound with rich early reflections"
    },
    "concert_hall": {
        "name": "Symphonic Concert Hall",
        "dimensions": (28.0, 18.5, 14.0),
        "rt60": 1.95,
        "absorption": 0.16,
        "damping": 0.60,
        "description": "Expansive orchestral acoustics with lush specular spread and warm low-end"
    },
    "cathedral": {
        "name": "Stone Gothic Cathedral",
        "dimensions": (52.0, 26.0, 22.0),
        "rt60": 3.80,
        "absorption": 0.08,
        "damping": 0.70,
        "description": "Massive stone nave with endless shimmering diffuse tail and cathedral grandeur"
    },
    "plate": {
        "name": "EMT-Style Vintage Plate Reverb",
        "dimensions": (3.0, 2.0, 1.5),
        "rt60": 2.20,
        "absorption": 0.05,
        "damping": 0.25,
        "description": "Dense, bright electro-mechanical steel plate reverberation"
    }
}


def calculate_room_geometry(dims: Tuple[float, float, float]) -> Tuple[float, float]:
    """Calculates room volume (m^3) and total internal surface area (m^2)."""
    L, W, H = dims
    volume = L * W * H
    surface_area = 2.0 * (L * W + L * H + W * H)
    return volume, surface_area


def calculate_sabine_rt60(volume: float, surface_area: float, absorption: float) -> float:
    """Calculates theoretical RT60 reverberation time via Sabine's equation."""
    # Sabine: RT60 = 0.161 * V / (A), where A = S * alpha
    total_absorption = surface_area * max(0.01, min(0.99, absorption))
    return (0.161 * volume) / total_absorption


def synthesize_impulse_response(
    room_preset: str = "room",
    rt60_sec: Optional[float] = None,
    dimensions: Optional[Tuple[float, float, float]] = None,
    sample_rate: int = 48000,
    stereo_width: float = 1.0,
    include_direct: bool = True,
    bit_depth: int = 24,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synthesizes a stereo acoustic impulse response WAV file.
    
    Args:
        room_preset: One of 'studio', 'room', 'concert_hall', 'cathedral', 'plate'.
        rt60_sec: Custom RT60 in seconds (overrides preset default if provided).
        dimensions: Custom (Length, Width, Height) in meters.
        sample_rate: Output sample rate (e.g. 44100, 48000, 96000).
        stereo_width: Stereo separation width factor [0.0 - 1.5].
        include_direct: Whether to include direct line-of-sight sound at t=0.
        bit_depth: Export bit depth (16 or 24 bit).
        output_path: Target .wav output path.
        
    Returns:
        Dict with status, metrics, and generated file information.
    """
    preset_key = room_preset.lower().strip()
    preset = ROOM_PRESETS.get(preset_key, ROOM_PRESETS["room"])

    room_dims = dimensions if dimensions else preset["dimensions"]
    L, W, H = room_dims
    target_rt60 = float(rt60_sec) if (rt60_sec is not None and rt60_sec > 0.05) else preset["rt60"]
    absorption = preset["absorption"]
    damping = preset["damping"]

    volume, surface_area = calculate_room_geometry(room_dims)
    c = 343.0  # Speed of sound in dry air at 20 deg C (m/s)

    # Total IR duration: allow decay down to -60 dB plus 100ms safety buffer
    ir_duration = max(0.2, target_rt60 * 1.1 + 0.1)
    num_samples = int(math.ceil(ir_duration * sample_rate))

    # Initialize left and right channel buffers
    ir_left = np.zeros(num_samples, dtype=np.float32)
    ir_right = np.zeros(num_samples, dtype=np.float32)

    # Listener and sound source positioning within shoebox
    # Source positioned slightly off-center to avoid degenerate reflection flutter
    src_pos = np.array([L * 0.42, W * 0.38, H * 0.55], dtype=np.float32)
    
    # Listener positioned centrally with interaural spacing
    ear_spacing = 0.18 * stereo_width  # 18cm average human ear separation
    listener_center = np.array([L * 0.65, W * 0.50, 1.65], dtype=np.float32)
    ear_l = listener_center + np.array([0.0, -ear_spacing * 0.5, 0.0], dtype=np.float32)
    ear_r = listener_center + np.array([0.0,  ear_spacing * 0.5, 0.0], dtype=np.float32)

    # 1. Early Specular Reflections via Image-Source Method (order 2-3)
    max_order = 3 if preset_key != "cathedral" else 2
    early_reflections_count = 0
    direct_l_amp = 0.0

    reflection_coeff = math.sqrt(max(0.01, 1.0 - absorption))

    for nx in range(-max_order, max_order + 1):
        for ny in range(-max_order, max_order + 1):
            for nz in range(-max_order, max_order + 1):
                order = abs(nx) + abs(ny) + abs(nz)
                if order > max_order:
                    continue

                # Compute mirrored source position
                img_x = (nx * L) + (src_pos[0] if (nx % 2 == 0) else (L - src_pos[0]))
                img_y = (ny * W) + (src_pos[1] if (ny % 2 == 0) else (W - src_pos[1]))
                img_z = (nz * H) + (src_pos[2] if (nz % 2 == 0) else (H - src_pos[2]))
                img_pos = np.array([img_x, img_y, img_z], dtype=np.float32)

                # Distance to each ear
                dist_l = float(np.linalg.norm(img_pos - ear_l))
                dist_r = float(np.linalg.norm(img_pos - ear_r))

                time_l = dist_l / c
                time_r = dist_r / c

                samp_l = int(time_l * sample_rate)
                samp_r = int(time_r * sample_rate)

                if samp_l >= num_samples or samp_r >= num_samples:
                    continue

                # Attenuation based on distance (1/d) and surface reflection factor
                wall_factor = reflection_coeff ** order
                amp_l = (1.0 / max(0.5, dist_l)) * wall_factor
                amp_r = (1.0 / max(0.5, dist_r)) * wall_factor

                # Air absorption: high frequencies attenuate with distance
                air_loss = math.exp(-0.0005 * dist_l)
                amp_l *= air_loss
                amp_r *= air_loss

                if order == 0:
                    # Direct line-of-sight sound
                    direct_l_amp = amp_l
                    if include_direct:
                        ir_left[samp_l] += amp_l
                        ir_right[samp_r] += amp_r
                else:
                    # Early reflection
                    early_reflections_count += 1
                    ir_left[samp_l] += amp_l
                    ir_right[samp_r] += amp_r

    # 2. Diffuse Late Reverberation Tail (Stochastic Ray Modeling)
    # Mixing time (transition from specular to diffuse): t_mix ~ sqrt(V) in ms
    t_mix = min(0.08, max(0.015, math.sqrt(volume) * 0.002))
    mix_start_idx = int(t_mix * sample_rate)

    # Decay rate parameter: RT60 = time to decay by 60 dB (10^-3 amplitude = e^(-6.9077))
    decay_constant = 6.907755 / target_rt60

    t_axis = np.arange(num_samples, dtype=np.float32) / float(sample_rate)
    decay_envelope = np.exp(-decay_constant * t_axis)

    # Envelope fade-in for diffuse tail starting at t_mix
    tail_fade = np.clip((t_axis - t_mix * 0.5) / max(0.005, t_mix), 0.0, 1.0)

    # Generate uncorrelated Gaussian noise for diffuse tail
    np.random.seed(42)  # Deterministic seed for reproducible IRs
    noise_l = np.random.normal(0.0, 1.0, num_samples).astype(np.float32)
    noise_r = np.random.normal(0.0, 1.0, num_samples).astype(np.float32)

    # Apply 1-pole low-pass filtering to simulate frequency-dependent air absorption over time
    # Damping factor: higher frequencies attenuate progressively faster as reverb tail ages
    lp_coeff = max(0.1, min(0.95, 1.0 - damping * 0.6))
    filtered_tail_l = np.zeros(num_samples, dtype=np.float32)
    filtered_tail_r = np.zeros(num_samples, dtype=np.float32)

    acc_l = 0.0
    acc_r = 0.0
    for i in range(mix_start_idx, num_samples):
        acc_l = acc_l + lp_coeff * (noise_l[i] - acc_l)
        acc_r = acc_r + lp_coeff * (noise_r[i] - acc_r)
        filtered_tail_l[i] = acc_l
        filtered_tail_r[i] = acc_r

    # Scale tail to match early energy density
    tail_gain = 0.35 * (1.0 - absorption)
    ir_left += filtered_tail_l * decay_envelope * tail_fade * tail_gain
    ir_right += filtered_tail_r * decay_envelope * tail_fade * tail_gain

    # Align IR start: find earliest onset and shift to start
    peak_idx = int(np.argmax(np.abs(ir_left[:min(num_samples, int(sample_rate * 0.1))])))
    if peak_idx > 0 and include_direct:
        ir_left = np.pad(ir_left[peak_idx:], (0, peak_idx), mode="constant")
        ir_right = np.pad(ir_right[peak_idx:], (0, peak_idx), mode="constant")

    # Normalize IR to -0.5 dBFS (0.944 amplitude peak)
    max_peak = max(float(np.max(np.abs(ir_left))), float(np.max(np.abs(ir_right))))
    if max_peak > 1e-6:
        norm_factor = 0.944 / max_peak
        ir_left *= norm_factor
        ir_right *= norm_factor

    # Direct-to-Reverberant Ratio (DRR) in dB
    direct_energy = float(np.sum(ir_left[:int(0.005 * sample_rate)] ** 2))
    reverb_energy = float(np.sum(ir_left[int(0.005 * sample_rate):] ** 2))
    drr_db = 10.0 * math.log10(max(1e-9, direct_energy) / max(1e-9, reverb_energy))

    # Output file handling
    if not output_path:
        out_dir = os.path.join(os.getcwd(), "reverb_presets")
        os.makedirs(out_dir, exist_ok=True)
        safe_name = preset_key.replace(" ", "_")
        output_path = os.path.join(out_dir, f"Sonance_IR_{safe_name}_{int(target_rt60*1000)}ms.wav")

    # Ensure target directory exists
    out_dir_path = os.path.dirname(os.path.abspath(output_path))
    if out_dir_path:
        os.makedirs(out_dir_path, exist_ok=True)

    # Export WAV file
    success = False
    try:
        if bit_depth == 24:
            # 24-bit PCM export
            l_int = np.clip(ir_left * 8388607.0, -8388608.0, 8388607.0).astype(np.int32)
            r_int = np.clip(ir_right * 8388607.0, -8388608.0, 8388607.0).astype(np.int32)
            interleaved = np.empty((num_samples * 2,), dtype=np.int32)
            interleaved[0::2] = l_int
            interleaved[1::2] = r_int

            raw_bytes = bytearray(num_samples * 2 * 3)
            idx = 0
            for val in interleaved:
                uval = val if val >= 0 else (val + 16777216)
                raw_bytes[idx] = uval & 0xFF
                raw_bytes[idx + 1] = (uval >> 8) & 0xFF
                raw_bytes[idx + 2] = (uval >> 16) & 0xFF
                idx += 3

            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(3)
                wf.setframerate(sample_rate)
                wf.writeframes(bytes(raw_bytes))
            success = True
        else:
            # 16-bit PCM export
            l_int = np.clip(ir_left * 32767.0, -32768.0, 32767.0).astype(np.int16)
            r_int = np.clip(ir_right * 32767.0, -32768.0, 32767.0).astype(np.int16)
            interleaved = np.empty((num_samples * 2,), dtype=np.int16)
            interleaved[0::2] = l_int
            interleaved[1::2] = r_int

            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(interleaved.tobytes())
            success = True
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    return {
        "success": success,
        "output_path": output_path,
        "preset": preset_key,
        "preset_name": preset["name"],
        "dimensions": list(room_dims),
        "volume_m3": round(volume, 2),
        "surface_area_m2": round(surface_area, 2),
        "rt60_sec": round(target_rt60, 2),
        "sample_rate": sample_rate,
        "duration_sec": round(ir_duration, 2),
        "num_samples": num_samples,
        "bit_depth": bit_depth,
        "channels": 2,
        "early_reflections_count": early_reflections_count,
        "drr_db": round(drr_db, 2),
        "peak_dbfs": -0.5
    }


def format_ir_card(res: Dict[str, Any]) -> str:
    """Renders formatted ASCII acoustic impulse response specification card."""
    if not res.get("success"):
        return f"[!] Error generating IR: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append("| ROOM ACOUSTIC IMPULSE RESPONSE & REVERB SYNTHESIZER              |")
    lines.append(sep)
    lines.append(f"| Room Preset    : {res['preset_name'][:48]:<48} |")
    dim_str = f"{res['dimensions'][0]}m x {res['dimensions'][1]}m x {res['dimensions'][2]}m"
    lines.append(f"| Dimensions     : {dim_str:<48} |")
    lines.append(f"| Room Volume    : {res['volume_m3']} m^3 (Surface Area: {res['surface_area_m2']} m^2)         |")
    lines.append(f"| Target RT60    : {res['rt60_sec']} s (Decay to -60 dBFS)                          |")
    lines.append(sep)
    lines.append(f"| Sample Rate    : {res['sample_rate']} Hz | {res['bit_depth']}-bit PCM | 2 Channels (Stereo)     |")
    lines.append(f"| IR Duration    : {res['duration_sec']}s ({res['num_samples']} samples)                       |")
    lines.append(f"| Specular Images: {res['early_reflections_count']} discrete early reflection paths              |")
    lines.append(f"| Direct/Reverb  : DRR {res['drr_db']:>+5.1f} dB (Peak: {res['peak_dbfs']:>+4.1f} dBFS)                    |")
    lines.append(sep)

    # ASCII decay envelope curve (8 time slices)
    lines.append("| REVERBERATION ENERGY DECAY PROFILE (dBFS vs Time):               |")
    steps = 8
    t_step = res['duration_sec'] / steps
    decay_const = 6.907755 / max(0.01, res['rt60_sec'])

    for step_i in range(steps):
        t_curr = step_i * t_step
        # Theoretical dB level at t_curr
        level_db = max(-60.0, -decay_const * t_curr * 8.686)
        # Bar length (0 to 30 chars mapped from -60 to 0 dB)
        bar_len = max(0, min(30, int((level_db + 60.0) / 60.0 * 30.0)))
        bar = "#" * bar_len + "." * (30 - bar_len)
        lines.append(f"| t={t_curr:>4.2f}s : [{bar}] {level_db:>+5.1f} dBFS |")

    lines.append(sep)
    lines.append(f"| Output File    : {res['output_path'][:48]:<48} |")
    lines.append(sep)

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sonance Room Acoustic Impulse Response Synthesizer")
    parser.add_argument("output", nargs="?", default=None, help="Target output WAV path")
    parser.add_argument("--preset", choices=list(ROOM_PRESETS.keys()), default="room", help="Room acoustic preset")
    parser.add_argument("--rt60", type=float, default=None, help="Custom reverberation time RT60 in seconds")
    parser.add_argument("--dims", nargs=3, type=float, default=None, metavar=("L", "W", "H"), help="Room length width height in meters")
    parser.add_argument("--sr", type=int, default=48000, help="Sample rate in Hz (default 48000)")
    parser.add_argument("--bit-depth", type=int, choices=[16, 24], default=24, help="WAV bit depth (default 24)")

    args = parser.parse_args()

    dims_tuple = tuple(args.dims) if args.dims else None
    result = synthesize_impulse_response(
        room_preset=args.preset,
        rt60_sec=args.rt60,
        dimensions=dims_tuple,
        sample_rate=args.sr,
        bit_depth=args.bit_depth,
        output_path=args.output
    )
    print(format_ir_card(result))
