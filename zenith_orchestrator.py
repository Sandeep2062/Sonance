"""
zenith_orchestrator.py - The Grand Workstation Zenith & Master Orchestration Suite
Part of Sonance (Unified Audiophile Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Phase 35 Milestone (The Grand Workstation Finale):
- End-to-End Serial Mastering Chain Orchestration:
  Executes an unbroken, mastering-grade 7-stage serial pipeline:
  * Stage 1: Dynamic Spectral Resonance Suppression (Oeksound Soothe2 physical model)
  * Stage 2: Psychoacoustic Subharmonic Bass & Missing Fundamental Synthesis (dbx 120XP / MaxxBass)
  * Stage 3: British Class-A Console Channel Strip & EQ (Neve 1073 Class-A & Baxandall air sheen)
  * Stage 4: Vintage Dynamics Master Glue (Teletronix LA-2A T4 optical or Fairchild 670 variable-mu)
  * Stage 5: Mid/Side Spatial Width & Elliptical Monomaker (orthogonal M/S matrix & air exciter)
  * Stage 6: Master Studer A800 Analog Tape Saturation & Tube Warmth (30/15 ips head-bump)
  * Stage 7: Audiophile Lookahead True-Peak Brickwall Safety Limiter (-0.2 dBFS ceiling)
- Zenith Macro Profiles:
  * audiophile_pure_master (Transparent audiophile fidelity, high dynamic crest)
  * club_edm_banger (Maximum subterranean punch, variable-mu glue, -9 LUFS density)
  * acoustic_intimate (Velvety vocal leveling, mid-side acoustic dimension, smooth highs)
  * broadcast_radio_sheen (EBU R128 compliance, cohesive console & tape sheen)
  * vinyl_cutting_prep (Subsonic highpass, 140 Hz monomaker, conservative headroom)
- Album Batch Processing:
  * Automates identical multi-stage mastering across entire folders or albums.
- Complete Audio Telemetry & Master Quality Manifest:
  * Input/Output Peak, RMS, Dynamic Crest Factor, stages audited, and SHA-256 integrity checksums.
"""

import os
import sys
import math
import time
import wave
import hashlib
import tempfile
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# Import core phase studio engines
import resonance_suppressor
import subharmonic_bass
import console_channel_strip
import vintage_compressor
import midside_processor
import analog_tape_emulator
import mastering_limiter


# ---------------------------------------------------------------------------
# Master Macro Profiles
# ---------------------------------------------------------------------------

ZENITH_PROFILES: Dict[str, Dict[str, Any]] = {
    "audiophile_pure_master": {
        "name": "Audiophile Pure Master (Ultra-High Fidelity)",
        "description": "Transparent, dynamic master with gentle de-resonating, subtle LA-2A optical leveling, Neve warmth, and tape sheen.",
        "stages": {
            "de_resonance": {"enabled": True, "preset": "tame_harshness", "depth": 0.40},
            "sub_bass": {"enabled": True, "preset": "audiophile_warm_bass"},
            "console_strip": {"enabled": True, "preset": "analog_warmth"},
            "vintage_comp": {"enabled": True, "preset": "la2a_smooth_vocal", "mode": "la2a", "reduction": 35.0, "makeup": 1.0},
            "midside": {"enabled": True, "width": 110.0, "monomaker": 80.0, "air": 1.0},
            "analog_tape": {"enabled": True, "drive": 1.4, "speed": 30.0, "warmth": 1.5},
            "master_limiter": {"enabled": True, "ceiling": -0.3, "threshold": -1.5}
        }
    },
    "club_edm_banger": {
        "name": "Club & EDM Heavy Master (Massive Sub & Density)",
        "description": "Explosive subterranean subharmonic punch, Fairchild variable-mu glue, monomaker bass, and maximum loudness density.",
        "stages": {
            "de_resonance": {"enabled": True, "preset": "cymbal_silencer", "depth": 0.50},
            "sub_bass": {"enabled": True, "preset": "club_sub_boom"},
            "console_strip": {"enabled": True, "preset": "drum_bus_punch"},
            "vintage_comp": {"enabled": True, "preset": "fairchild_drum_crush", "mode": "fairchild", "reduction": 65.0, "makeup": 2.5},
            "midside": {"enabled": True, "width": 130.0, "monomaker": 120.0, "air": 2.0},
            "analog_tape": {"enabled": True, "drive": 2.0, "speed": 15.0, "warmth": 2.0},
            "master_limiter": {"enabled": True, "ceiling": -0.2, "threshold": -4.0}
        }
    },
    "acoustic_intimate": {
        "name": "Acoustic Intimate (Velvety Vocals & Strings)",
        "description": "Preserves breath, wood, and room acoustics with surgical boxiness removal, smooth optical compression, and wide stereo air.",
        "stages": {
            "de_resonance": {"enabled": True, "preset": "vocal_de_boxer", "depth": 0.50},
            "sub_bass": {"enabled": False},
            "console_strip": {"enabled": True, "preset": "analog_warmth"},
            "vintage_comp": {"enabled": True, "preset": "la2a_acoustic_warmth", "mode": "la2a", "reduction": 40.0, "makeup": 1.5},
            "midside": {"enabled": True, "width": 120.0, "monomaker": 80.0, "air": 1.5},
            "analog_tape": {"enabled": True, "drive": 1.2, "speed": 30.0, "warmth": 1.2},
            "master_limiter": {"enabled": True, "ceiling": -0.5, "threshold": -1.0}
        }
    },
    "broadcast_radio_sheen": {
        "name": "Broadcast Radio Sheen (EBU R128 Cohesive)",
        "description": "Commercial radio mix with SSL master bus glue, MaxxBass translation on mobile, and controlled broadcast dynamics.",
        "stages": {
            "de_resonance": {"enabled": True, "preset": "tame_harshness", "depth": 0.55},
            "sub_bass": {"enabled": True, "preset": "earbuds_maxxbass"},
            "console_strip": {"enabled": True, "preset": "radio_broadcast"},
            "vintage_comp": {"enabled": True, "preset": "vintage_warm_glue", "mode": "la2a", "reduction": 45.0, "makeup": 2.0},
            "midside": {"enabled": True, "width": 115.0, "monomaker": 100.0, "air": 1.5},
            "analog_tape": {"enabled": True, "drive": 1.8, "speed": 15.0, "warmth": 1.8},
            "master_limiter": {"enabled": True, "ceiling": -1.0, "threshold": -3.0}
        }
    },
    "vinyl_cutting_prep": {
        "name": "Vinyl Lathe Cutting Prep (Phase Coherent)",
        "description": "Specialized mastering for vinyl cutting with subsonic high-pass filtering, 140 Hz monomaker, and conservative peak headroom.",
        "stages": {
            "de_resonance": {"enabled": True, "preset": "tame_harshness", "depth": 0.45},
            "sub_bass": {"enabled": True, "preset": "sub_rumble_cleanup"},
            "console_strip": {"enabled": True, "preset": "analog_warmth"},
            "vintage_comp": {"enabled": True, "preset": "la2a_acoustic_warmth", "mode": "la2a", "reduction": 30.0, "makeup": 1.0},
            "midside": {"enabled": True, "width": 100.0, "monomaker": 140.0, "air": 0.0},
            "analog_tape": {"enabled": True, "drive": 1.1, "speed": 30.0, "warmth": 1.0},
            "master_limiter": {"enabled": True, "ceiling": -1.5, "threshold": 0.0}
        }
    }
}


# ---------------------------------------------------------------------------
# Audio Utility Helpers
# ---------------------------------------------------------------------------

def calculate_sha256(file_path: str) -> str:
    """Computes SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_audio_stats(file_path: str) -> Dict[str, float]:
    """Extracts peak dBFS, RMS dBFS, and duration from audio file."""
    try:
        audio, sr = resonance_suppressor.read_audio_stereo(file_path)
        peak = float(np.max(np.abs(audio)))
        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak_db = 20.0 * math.log10(max(1e-6, peak))
        rms_db = 20.0 * math.log10(max(1e-6, rms))
        duration = audio.shape[1] / float(sr)
        crest = peak_db - rms_db
        return {
            "peak_dbfs": round(peak_db, 2),
            "rms_dbfs": round(rms_db, 2),
            "crest_factor_db": round(crest, 2),
            "duration_sec": round(duration, 2),
            "sample_rate": sr
        }
    except Exception:
        return {"peak_dbfs": 0.0, "rms_dbfs": -100.0, "crest_factor_db": 0.0, "duration_sec": 0.0, "sample_rate": 44100}


# ---------------------------------------------------------------------------
# Zenith Master Pipeline Execution
# ---------------------------------------------------------------------------

def render_zenith_master(
    input_path: str,
    output_path: Optional[str] = None,
    profile: str = "audiophile_pure_master",
    stage_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes the 7-stage Zenith Master Orchestration pipeline on a single audio file.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input audio file not found: {input_path}")

    start_time = time.time()
    p_data = ZENITH_PROFILES.get(profile, ZENITH_PROFILES["audiophile_pure_master"])
    stages_config = dict(p_data["stages"])
    if stage_overrides:
        for k, v in stage_overrides.items():
            if k in stages_config and isinstance(v, dict):
                stages_config[k].update(v)

    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_ZenithMaster.wav"

    in_stats = compute_audio_stats(input_path)

    temp_files = []
    current_input = input_path
    stage_telemetry = []

    try:
        # -------------------------------------------------------------------
        # Stage 1: Dynamic Spectral Resonance Suppression
        # -------------------------------------------------------------------
        cfg_1 = stages_config.get("de_resonance", {})
        if cfg_1.get("enabled", True):
            s1_out = tempfile.NamedTemporaryFile(suffix="_stage1_deres.wav", delete=False).name
            temp_files.append(s1_out)
            res1 = resonance_suppressor.render_resonance_suppressor(
                input_path=current_input,
                output_path=s1_out,
                preset=cfg_1.get("preset", "tame_harshness"),
                depth=cfg_1.get("depth", None)
            )
            current_input = s1_out
            stage_telemetry.append({
                "stage": 1,
                "name": "Dynamic Spectral De-Resonator",
                "engine": "resonance_suppressor.py",
                "max_reduction_db": res1.get("max_reduction_db", 0.0),
                "top_resonances": res1.get("top_resonances", [])
            })

        # -------------------------------------------------------------------
        # Stage 2: Psychoacoustic Subharmonic Bass & Missing Fundamental
        # -------------------------------------------------------------------
        cfg_2 = stages_config.get("sub_bass", {})
        if cfg_2.get("enabled", True):
            s2_out = tempfile.NamedTemporaryFile(suffix="_stage2_bass.wav", delete=False).name
            temp_files.append(s2_out)
            res2 = subharmonic_bass.render_subharmonic_bass(
                input_path=current_input,
                output_path=s2_out,
                preset=cfg_2.get("preset", "audiophile_warm_bass")
            )
            current_input = s2_out
            stage_telemetry.append({
                "stage": 2,
                "name": "Psychoacoustic Subharmonic Bass",
                "engine": "subharmonic_bass.py",
                "sub_energy_gain_db": res2.get("sub_energy_gain_db", 0.0)
            })

        # -------------------------------------------------------------------
        # Stage 3: British Class-A Console Channel Strip & EQ
        # -------------------------------------------------------------------
        cfg_3 = stages_config.get("console_strip", {})
        if cfg_3.get("enabled", True):
            s3_out = tempfile.NamedTemporaryFile(suffix="_stage3_console.wav", delete=False).name
            temp_files.append(s3_out)
            res3 = console_channel_strip.render_console_strip(
                input_path=current_input,
                output_path=s3_out,
                preset=cfg_3.get("preset", "analog_warmth")
            )
            current_input = s3_out
            stage_telemetry.append({
                "stage": 3,
                "name": "British Class-A Console Strip",
                "engine": "console_channel_strip.py",
                "bus_gr_db": res3.get("bus_max_reduction_db", 0.0)
            })

        # -------------------------------------------------------------------
        # Stage 4: Vintage Dynamics Master Glue (LA-2A / Fairchild 670)
        # -------------------------------------------------------------------
        cfg_4 = stages_config.get("vintage_comp", {})
        if cfg_4.get("enabled", True):
            s4_out = tempfile.NamedTemporaryFile(suffix="_stage4_vcomp.wav", delete=False).name
            temp_files.append(s4_out)
            res4 = vintage_compressor.render_vintage_compressor(
                input_path=current_input,
                output_path=s4_out,
                preset=cfg_4.get("preset", "la2a_smooth_vocal"),
                mode=cfg_4.get("mode", "la2a"),
                peak_reduction=cfg_4.get("reduction", 35.0),
                makeup_gain_db=cfg_4.get("makeup", 1.0)
            )
            current_input = s4_out
            stage_telemetry.append({
                "stage": 4,
                "name": f"Vintage Dynamics ({res4.get('mode', 'la2a').upper()})",
                "engine": "vintage_compressor.py",
                "gr_db": res4.get("max_gain_reduction_db", 0.0)
            })

        # -------------------------------------------------------------------
        # Stage 5: Mid/Side Spatial Width & Elliptical Monomaker
        # -------------------------------------------------------------------
        cfg_5 = stages_config.get("midside", {})
        if cfg_5.get("enabled", True):
            s5_out = tempfile.NamedTemporaryFile(suffix="_stage5_ms.wav", delete=False).name
            temp_files.append(s5_out)
            res5 = midside_processor.process_midside_audio(
                input_path=current_input,
                output_path=s5_out,
                width_percent=cfg_5.get("width", 110.0),
                monomaker_hz=cfg_5.get("monomaker", 80.0),
                side_air_db=cfg_5.get("air", 1.0)
            )
            current_input = s5_out
            stage_telemetry.append({
                "stage": 5,
                "name": "Mid/Side Spatial Width & Monomaker",
                "engine": "midside_processor.py",
                "stereo_correlation": res5.get("correlation_out", 0.0)
            })

        # -------------------------------------------------------------------
        # Stage 6: Master Analog Tape Saturation & Tube Warmth
        # -------------------------------------------------------------------
        cfg_6 = stages_config.get("analog_tape", {})
        if cfg_6.get("enabled", True):
            s6_out = tempfile.NamedTemporaryFile(suffix="_stage6_tape.wav", delete=False).name
            temp_files.append(s6_out)
            res6 = analog_tape_emulator.process_analog_tape(
                input_path=current_input,
                output_path=s6_out,
                drive=cfg_6.get("drive", 1.4),
                tape_speed_ips=cfg_6.get("speed", 30.0),
                warmth=cfg_6.get("warmth", 1.5)
            )
            current_input = s6_out
            stage_telemetry.append({
                "stage": 6,
                "name": "Master Studer Tape Saturation",
                "engine": "analog_tape_emulator.py",
                "tape_speed": f"{cfg_6.get('speed', 30.0)} ips"
            })

        # -------------------------------------------------------------------
        # Stage 7: True-Peak Brickwall Limiter
        # -------------------------------------------------------------------
        cfg_7 = stages_config.get("master_limiter", {})
        if cfg_7.get("enabled", True):
            res7 = mastering_limiter.process_mastering_limiter(
                input_path=current_input,
                output_path=output_path,
                ceiling_db=cfg_7.get("ceiling", -0.2),
                threshold_db=cfg_7.get("threshold", -2.0)
            )
            stage_telemetry.append({
                "stage": 7,
                "name": "Audiophile True-Peak Limiter",
                "engine": "mastering_limiter.py",
                "ceiling_dbfs": cfg_7.get("ceiling", -0.2),
                "isps_prevented": res7.get("isps_prevented", 0)
            })
        else:
            # If limiter disabled, export current input to final output
            audio, sr = resonance_suppressor.read_audio_stereo(current_input)
            resonance_suppressor.write_audio_stereo_24bit(output_path, audio, sr)

    finally:
        # Safely remove all intermediate temporary stage WAV files
        for tmp in temp_files:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    out_stats = compute_audio_stats(output_path)
    total_elapsed = round(time.time() - start_time, 2)
    master_sha256 = calculate_sha256(output_path)

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "profile": profile,
        "profile_name": p_data["name"],
        "elapsed_seconds": total_elapsed,
        "stages_executed": len(stage_telemetry),
        "stage_telemetry": stage_telemetry,
        "in_stats": in_stats,
        "out_stats": out_stats,
        "density_gain_db": round(in_stats["crest_factor_db"] - out_stats["crest_factor_db"], 2),
        "sha256": master_sha256
    }


# ---------------------------------------------------------------------------
# Batch Album Mastering Processor
# ---------------------------------------------------------------------------

def batch_master_directory(
    input_dir: str,
    output_dir: Optional[str] = None,
    profile: str = "audiophile_pure_master"
) -> Dict[str, Any]:
    """
    Executes the Zenith Master Orchestration pipeline across all audio files in a directory.
    """
    in_path = Path(input_path if os.path.isfile(input_dir) else input_dir)
    if not in_path.is_dir():
        raise NotADirectoryError(f"Directory not found: {input_dir}")

    out_dir_path = Path(output_dir) if output_dir else in_path / "Zenith_Masters"
    out_dir_path.mkdir(parents=True, exist_ok=True)

    supported_exts = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".aiff"}
    audio_files = [f for f in in_path.iterdir() if f.is_file() and f.suffix.lower() in supported_exts]

    results = []
    total_start = time.time()

    for idx, audio_file in enumerate(audio_files, 1):
        target_name = f"{audio_file.stem}_ZenithMaster.wav"
        target_path = str(out_dir_path / target_name)
        try:
            res = render_zenith_master(
                input_path=str(audio_file),
                output_path=target_path,
                profile=profile
            )
            results.append({"file": audio_file.name, "status": "success", "result": res})
        except Exception as e:
            results.append({"file": audio_file.name, "status": "failed", "error": str(e)})

    total_elapsed = round(time.time() - total_start, 2)
    successful = [r for r in results if r["status"] == "success"]

    return {
        "success": True,
        "total_files": len(audio_files),
        "processed_count": len(successful),
        "failed_count": len(audio_files) - len(successful),
        "output_directory": str(out_dir_path),
        "total_elapsed_sec": total_elapsed,
        "results": results
    }


# ---------------------------------------------------------------------------
# Standalone CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sonance Phase 35 Grand Finale: Zenith Master Orchestration Suite"
    )
    parser.add_argument("input", type=str, help="Path to input audio file or folder")
    parser.add_argument("output", type=str, nargs="?", default=None, help="Output master WAV or directory")
    parser.add_argument("--profile", type=str, choices=list(ZENITH_PROFILES.keys()),
                        default="audiophile_pure_master", help="Master macro profile preset")
    parser.add_argument("--batch", action="store_true", help="Process entire input directory as album")

    args = parser.parse_args()

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.5.0")
    print("  Phase 35 Grand Finale: Zenith Master Orchestration Suite")
    print("=" * 70)

    if args.batch or os.path.isdir(args.input):
        print(f"[*] Batch Album Mode: Processing {args.input}...")
        res = batch_master_directory(args.input, args.output, profile=args.profile)
        print(f"[+] Total Tracks Mastered: {res['processed_count']} / {res['total_files']} ({res['total_elapsed_sec']}s)")
        print(f"[+] Destination Directory: {res['output_directory']}")
    else:
        print(f"[*] Single Master Mode: {args.input}")
        print(f"[*] Selected Profile  : {args.profile.upper()}")
        res = render_zenith_master(args.input, args.output, profile=args.profile)
        print(f"[+] Output Master     : {res['output_path']}")
        print(f"[+] Stages Executed   : {res['stages_executed']} / 7 Serial Mastering Stages")
        print(f"[+] Elapsed Render    : {res['elapsed_seconds']}s")
        print(f"[+] Input -> Output   : Peak {res['in_stats']['peak_dbfs']} -> {res['out_stats']['peak_dbfs']} dBFS")
        print(f"[+] Dynamic Density   : +{res['density_gain_db']:.2f} dB Crest Factor Compression")
        print(f"[+] SHA-256 Checksum  : {res['sha256']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
