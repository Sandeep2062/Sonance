"""
dr_meter.py - TT Dynamic Range (DR) Meter & Loudness War Crest Factor Analyzer
Part of Sonance - The Ultimate Open-Source Music Workstation
Official Pleasurize Music Foundation algorithm implementation (DR4 to DR18+).

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import math
import wave
import subprocess
import shutil
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Supported audio extensions
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".aiff", ".aif"}


def _decode_audio_to_numpy(audio_path: str, max_duration_sec: Optional[float] = None) -> Tuple[np.ndarray, int]:
    """
    Decodes an audio file to a float32 numpy array [channels, samples] normalized to [-1.0, 1.0].
    Uses wave module for WAV files if standard PCM, or FFmpeg for all formats.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ext = os.path.splitext(audio_path)[1].lower()

    # Try native wave if standard uncompressed PCM
    if ext in {".wav", ".wave"}:
        try:
            with wave.open(audio_path, "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                if max_duration_sec:
                    n_frames = min(n_frames, int(max_duration_sec * framerate))

                raw_bytes = wf.readframes(n_frames)

                if sampwidth == 1:
                    data = np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32)
                    data = (data - 128.0) / 128.0
                elif sampwidth == 2:
                    data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                elif sampwidth == 3:
                    # 24-bit PCM
                    raw_array = np.frombuffer(raw_bytes, dtype=np.uint8)
                    n_samples = len(raw_array) // 3
                    reshaped = raw_array[: n_samples * 3].reshape(-1, 3)
                    int24 = (
                        reshaped[:, 0].astype(np.int32)
                        | (reshaped[:, 1].astype(np.int32) << 8)
                        | (reshaped[:, 2].astype(np.int32) << 16)
                    )
                    int24[int24 >= 0x800000] -= 0x1000000
                    data = int24.astype(np.float32) / 8388608.0
                elif sampwidth == 4:
                    data = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
                else:
                    raise ValueError("Unsupported bit depth in WAV")

                if n_channels > 1:
                    data = data.reshape(-1, n_channels).T
                else:
                    data = data.reshape(1, -1)
                return data, framerate
        except Exception:
            pass  # Fallback to FFmpeg

    # Use FFmpeg to decode raw 32-bit float PCM
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-v", "error",
        "-i", audio_path,
    ]
    if max_duration_sec:
        cmd.extend(["-t", str(max_duration_sec)])
    cmd.extend([
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-"
    ])

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        raw_pcm, stderr = proc.communicate()
        if proc.returncode != 0 or not raw_pcm:
            raise RuntimeError(f"FFmpeg decoding failed: {stderr.decode('utf-8', errors='ignore')}")

        samples = np.frombuffer(raw_pcm, dtype=np.float32)

        # Get audio channel count and sample rate via ffprobe
        probe_cmd = [
            shutil.which("ffprobe") or "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=channels,sample_rate",
            "-of", "csv=p=0:s=,",
            audio_path
        ]
        probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        parts = probe_res.stdout.strip().split(",")
        channels = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else 2
        sample_rate = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 44100

        total_frames = len(samples) // channels
        samples = samples[: total_frames * channels].reshape(-1, channels).T
        return samples, sample_rate

    except Exception as e:
        raise RuntimeError(f"Could not decode audio file: {e}")


def _compute_channel_dr(samples: np.ndarray, sample_rate: int, block_duration: float = 3.0) -> Dict[str, float]:
    """
    Computes TT Dynamic Range metrics for a single channel (1D float32 array).
    """
    if len(samples) == 0:
        return {"dr": 0, "peak_db": -99.0, "rms_db": -99.0, "crest_db": 0.0}

    # 1. True Peak (Peak linear and peak dBFS)
    peak_linear = float(np.max(np.abs(samples)))
    if peak_linear <= 1e-9:
        return {"dr": 0, "peak_db": -99.0, "rms_db": -99.0, "crest_db": 0.0}
    peak_db = 20.0 * math.log10(peak_linear)

    # 2. Total RMS across entire signal
    total_rms_linear = float(np.sqrt(np.mean(samples ** 2)))
    total_rms_db = 20.0 * math.log10(total_rms_linear) if total_rms_linear > 1e-9 else -99.0
    crest_factor_db = peak_db - total_rms_db

    # 3. Block RMS computation (3.0s contiguous windows)
    block_samples = int(block_duration * sample_rate)
    if block_samples <= 0:
        block_samples = 44100 * 3

    n_blocks = len(samples) // block_samples
    if n_blocks == 0:
        # Fallback if track is shorter than 3 seconds
        top20_rms_db = total_rms_db
        dr_val = max(0.0, peak_db - top20_rms_db)
        return {
            "dr": int(round(dr_val)),
            "peak_db": round(peak_db, 2),
            "rms_db": round(total_rms_db, 2),
            "top20_rms_db": round(top20_rms_db, 2),
            "crest_db": round(crest_factor_db, 2),
        }

    # Truncate to whole blocks
    usable_samples = samples[: n_blocks * block_samples].reshape(n_blocks, block_samples)
    block_rms = np.sqrt(np.mean(usable_samples ** 2, axis=1))

    # 4. Sort block RMS descending and take top 20%
    sorted_rms = np.sort(block_rms)[::-1]
    top20_count = max(1, int(round(0.20 * n_blocks)))
    top20_blocks = sorted_rms[:top20_count]

    # Combined RMS of the top 20% blocks
    top20_rms_linear = float(np.sqrt(np.mean(top20_blocks ** 2)))
    top20_rms_db = 20.0 * math.log10(top20_rms_linear) if top20_rms_linear > 1e-9 else -99.0

    # DR = Peak (dB) - Top 20% RMS (dB)
    raw_dr = peak_db - top20_rms_db
    dr_val = max(0.0, raw_dr)

    return {
        "dr": int(round(dr_val)),
        "peak_db": round(peak_db, 2),
        "rms_db": round(total_rms_db, 2),
        "top20_rms_db": round(top20_rms_db, 2),
        "crest_db": round(crest_factor_db, 2),
    }


def get_loudness_war_rating(dr: int) -> Dict[str, str]:
    """
    Returns description and color badge for a given DR value according to
    Pleasurize Music Foundation standards.
    """
    if dr >= 14:
        return {
            "rating": "Pristine / Audiophile Dynamic Master",
            "tier": "Audiophile",
            "color": "#10b981",  # emerald
            "description": "Superb dynamic contrast; zero audible loudness compression artifacts.",
        }
    elif dr >= 11:
        return {
            "rating": "Healthy Dynamic Range",
            "tier": "Good",
            "color": "#3b82f6",  # blue
            "description": "Well-balanced modern master with punchy dynamics and clarity.",
        }
    elif dr >= 8:
        return {
            "rating": "Moderate Compression",
            "tier": "Standard",
            "color": "#f59e0b",  # amber
            "description": "Standard modern pop/rock master; moderate dynamic range reduction.",
        }
    elif dr >= 5:
        return {
            "rating": "Heavy Compression (Loudness War Casualty)",
            "tier": "Poor",
            "color": "#ef4444",  # red
            "description": "Heavily limited and compressed; audible loss of transient punch.",
        }
    else:
        return {
            "rating": "Severely Brickwalled / Distorted Master",
            "tier": "Critical",
            "color": "#dc2626",  # dark red
            "description": "Extreme loudness war victim; severe flat-top waveform clipping.",
        }


def analyze_track_dynamic_range(audio_path: str, max_duration_sec: Optional[float] = None) -> Dict[str, Any]:
    """
    Analyzes an audio file and returns official TT Dynamic Range metrics.
    """
    if not os.path.exists(audio_path):
        return {"success": False, "error": f"File not found: {audio_path}"}

    try:
        samples, sr = _decode_audio_to_numpy(audio_path, max_duration_sec=max_duration_sec)
        n_channels = samples.shape[0]

        channel_results = []
        for ch in range(n_channels):
            res = _compute_channel_dr(samples[ch], sr)
            channel_results.append(res)

        # Official spec: Track DR is integer-rounded average of channels
        avg_dr = sum(c["dr"] for c in channel_results) / max(1, n_channels)
        track_dr = int(round(avg_dr))

        overall_peak_db = max(c["peak_db"] for c in channel_results)
        overall_rms_db = (
            20.0 * math.log10(np.sqrt(np.mean([10 ** (c["rms_db"] / 10.0) for c in channel_results])))
            if channel_results
            else -99.0
        )
        overall_crest_db = overall_peak_db - overall_rms_db

        rating_info = get_loudness_war_rating(track_dr)

        return {
            "success": True,
            "file": audio_path,
            "filename": os.path.basename(audio_path),
            "sample_rate": sr,
            "channels": n_channels,
            "duration_sec": round(samples.shape[1] / sr, 2),
            "dr": track_dr,
            "dr_badge": f"DR{track_dr}",
            "peak_db": round(overall_peak_db, 2),
            "rms_db": round(overall_rms_db, 2),
            "crest_factor_db": round(overall_crest_db, 2),
            "channels_detail": channel_results,
            "rating": rating_info["rating"],
            "tier": rating_info["tier"],
            "color": rating_info["color"],
            "description": rating_info["description"],
        }
    except Exception as e:
        return {"success": False, "file": audio_path, "error": str(e)}


def analyze_album_dynamic_range(album_dir: str) -> Dict[str, Any]:
    """
    Scans an album directory and analyzes Dynamic Range for all audio tracks,
    producing track-by-track breakdown, official Album DR, and formatted report.
    """
    if not os.path.isdir(album_dir):
        return {"success": False, "error": f"Directory not found: {album_dir}"}

    tracks = []
    for root, _, files in os.walk(album_dir):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTS:
                tracks.append(os.path.join(root, f))

    if not tracks:
        return {"success": False, "error": f"No audio files found in: {album_dir}"}

    track_results = []
    dr_values = []
    peak_values = []
    rms_values = []

    for path in tracks:
        res = analyze_track_dynamic_range(path)
        if res.get("success"):
            track_results.append(res)
            dr_values.append(res["dr"])
            peak_values.append(res["peak_db"])
            rms_values.append(res["rms_db"])
        else:
            track_results.append({
                "file": path,
                "filename": os.path.basename(path),
                "dr": 0,
                "dr_badge": "ERR",
                "peak_db": 0.0,
                "rms_db": 0.0,
                "crest_factor_db": 0.0,
                "error": res.get("error", "Analysis failed"),
            })

    if not dr_values:
        return {"success": False, "error": "Failed to analyze any audio tracks."}

    album_dr = int(round(sum(dr_values) / len(dr_values)))
    rating_info = get_loudness_war_rating(album_dr)

    # Generate ASCII DR Report Table
    report_lines = [
        "--------------------------------------------------------------------------------",
        " Analyzed: " + os.path.basename(album_dir),
        " Standard: Pleasurize Music Foundation TT Dynamic Range Meter",
        "--------------------------------------------------------------------------------",
        " DR     Peak       RMS        Duration   Track",
        "--------------------------------------------------------------------------------",
    ]
    for t in track_results:
        if "error" in t:
            report_lines.append(f" ERR    --         --         --         {t['filename']} ({t['error']})")
        else:
            dr_str = f"DR{t['dr']:<2}"
            peak_str = f"{t['peak_db']:>6.2f} dB"
            rms_str = f"{t['rms_db']:>6.2f} dB"
            dur_m = int(t['duration_sec'] // 60)
            dur_s = int(t['duration_sec'] % 60)
            dur_str = f"{dur_m:02d}:{dur_s:02d}"
            report_lines.append(f" {dr_str}   {peak_str}   {rms_str}   {dur_str}      {t['filename']}")

    report_lines.extend([
        "--------------------------------------------------------------------------------",
        f" Official Album DR: DR{album_dr} ({rating_info['tier']} - {rating_info['rating']})",
        f" Number of Tracks: {len(dr_values)}",
        "--------------------------------------------------------------------------------",
    ])
    report_text = "\n".join(report_lines)

    return {
        "success": True,
        "album_dir": album_dir,
        "album_name": os.path.basename(album_dir),
        "album_dr": album_dr,
        "album_dr_badge": f"DR{album_dr}",
        "rating": rating_info["rating"],
        "tier": rating_info["tier"],
        "color": rating_info["color"],
        "description": rating_info["description"],
        "track_count": len(dr_values),
        "tracks": track_results,
        "report_text": report_text,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dr_meter.py <audio_file_or_directory>")
        sys.exit(1)

    target = sys.argv[1]
    if os.path.isdir(target):
        res = analyze_album_dynamic_range(target)
        if res.get("success"):
            print(res["report_text"])
        else:
            print("Error:", res.get("error"))
    else:
        res = analyze_track_dynamic_range(target)
        if res.get("success"):
            print(f"File:        {res['filename']}")
            print(f"Dynamic Range: {res['dr_badge']} ({res['tier']} - {res['rating']})")
            print(f"Peak Level:    {res['peak_db']} dBFS")
            print(f"Total RMS:     {res['rms_db']} dBFS")
            print(f"Crest Factor:  {res['crest_factor_db']} dB")
            print(f"Channels:      {res['channels']} ({res['sample_rate']} Hz)")
            print(f"Summary:       {res['description']}")
        else:
            print("Error:", res.get("error"))
