"""
ab_looper.py - Musician A-B Phrase Looper & Metronome Practice Studio
Part of Sonance - The Ultimate Open-Source Music Workstation
Millisecond-accurate A-B phrase extraction with de-clicking crossfade smoothing,
loop repetition concatenation, metronome count-in synthesis, and loop sample export.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import wave
import shutil
import subprocess
from typing import Dict, Any, Optional, Tuple
import numpy as np

# Re-use audio decoder from dr_meter or implement pure python wave / ffmpeg
def _load_audio_float32(audio_path: str) -> Tuple[np.ndarray, int]:
    """Loads audio as float32 array [channels, samples] in range [-1.0, 1.0]."""
    ext = os.path.splitext(audio_path)[1].lower()
    if ext in {".wav", ".wave"}:
        try:
            with wave.open(audio_path, "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)

                if sampwidth == 2:
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                elif sampwidth == 3:
                    raw_arr = np.frombuffer(raw, dtype=np.uint8)
                    n_s = len(raw_arr) // 3
                    reshaped = raw_arr[: n_s * 3].reshape(-1, 3)
                    int24 = (
                        reshaped[:, 0].astype(np.int32)
                        | (reshaped[:, 1].astype(np.int32) << 8)
                        | (reshaped[:, 2].astype(np.int32) << 16)
                    )
                    int24[int24 >= 0x800000] -= 0x1000000
                    data = int24.astype(np.float32) / 8388608.0
                elif sampwidth == 4:
                    data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
                else:
                    data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
                    data = (data - 128.0) / 128.0

                if n_channels > 1:
                    data = data.reshape(-1, n_channels).T
                else:
                    data = data.reshape(1, -1)
                return data, sr
        except Exception:
            pass

    # FFmpeg fallback
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-v", "error",
        "-i", audio_path,
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw_pcm, stderr = proc.communicate()
    if proc.returncode != 0 or not raw_pcm:
        raise RuntimeError(f"FFmpeg decoding error: {stderr.decode('utf-8', errors='ignore')}")

    samples = np.frombuffer(raw_pcm, dtype=np.float32)
    # Probe channels and sample rate
    probe_cmd = [
        shutil.which("ffprobe") or "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=channels,sample_rate",
        "-of", "csv=p=0:s=,",
        audio_path
    ]
    res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    parts = res.stdout.strip().split(",")
    channels = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else 2
    sr = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 44100

    total_frames = len(samples) // channels
    samples = samples[: total_frames * channels].reshape(-1, channels).T
    return samples, sr


def _generate_click_count_in(sample_rate: int, bpm: float = 120.0, beats: int = 4, channels: int = 2) -> np.ndarray:
    """Generates synthetic metronome click beats before the loop begins."""
    beat_interval = 60.0 / max(30.0, bpm)
    beat_samples = int(beat_interval * sample_rate)
    total_samples = beat_samples * beats
    click_track = np.zeros((channels, total_samples), dtype=np.float32)

    pip_dur = int(0.04 * sample_rate)  # 40ms pulse
    t_pip = np.linspace(0, 0.04, pip_dur, endpoint=False)
    envelope = np.exp(-t_pip * 100.0)  # fast decaying percussive envelope

    for b in range(beats):
        freq = 1600.0 if b == 0 else 1000.0  # High accent on downbeat
        pip = 0.6 * np.sin(2.0 * np.pi * freq * t_pip) * envelope
        start_idx = b * beat_samples
        end_idx = min(total_samples, start_idx + pip_dur)
        for ch in range(channels):
            click_track[ch, start_idx:end_idx] = pip[: end_idx - start_idx]

    return click_track


def _apply_loop_crossfade(slice_data: np.ndarray, crossfade_ms: float = 10.0, sample_rate: int = 44100) -> np.ndarray:
    """
    Applies a micro equal-power crossfade between head and tail of the slice
    to ensure 100% seamless, click-free audio looping.
    """
    fade_len = int((crossfade_ms / 1000.0) * sample_rate)
    if slice_data.shape[1] <= fade_len * 2:
        return slice_data.copy()

    result = slice_data.copy()
    n_ch = result.shape[0]

    # Half-cosine equal-power window
    t = np.linspace(0, np.pi / 2.0, fade_len)
    fade_in = np.sin(t)
    fade_out = np.cos(t)

    # Blend head and tail
    for ch in range(n_ch):
        result[ch, :fade_len] = result[ch, :fade_len] * fade_in
        result[ch, -fade_len:] = result[ch, -fade_len:] * fade_out

    return result


def create_ab_loop(
    audio_path: str,
    start_sec: float,
    end_sec: float,
    repeats: int = 4,
    add_count_in: bool = False,
    bpm: float = 120.0,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts audio between start_sec and end_sec, applies seamless de-clicking
    crossfades, optionally prefixes with a metronome count-in, repeats N times,
    and saves to output_path.
    """
    if not os.path.isfile(audio_path):
        return {"success": False, "error": f"Audio file not found: {audio_path}"}

    try:
        samples, sr = _load_audio_float32(audio_path)
        total_len_sec = samples.shape[1] / sr

        # Validate range
        t_a = max(0.0, min(start_sec, total_len_sec))
        t_b = max(t_a + 0.1, min(end_sec, total_len_sec))

        idx_a = int(t_a * sr)
        idx_b = int(t_b * sr)

        raw_slice = samples[:, idx_a:idx_b]
        if raw_slice.shape[1] == 0:
            return {"success": False, "error": "Invalid slice selection (zero samples)."}

        # Apply boundary crossfade
        smooth_slice = _apply_loop_crossfade(raw_slice, crossfade_ms=8.0, sample_rate=sr)

        # Build loop blocks
        repeats = max(1, min(repeats, 100))
        loop_blocks = [smooth_slice] * repeats
        concatenated = np.concatenate(loop_blocks, axis=1)

        # Add optional metronome count-in
        if add_count_in:
            click = _generate_click_count_in(sr, bpm=bpm, beats=4, channels=samples.shape[0])
            final_audio = np.concatenate([click, concatenated], axis=1)
        else:
            final_audio = concatenated

        # Determine output file path
        if not output_path:
            base, ext = os.path.splitext(audio_path)
            rep_str = f"{repeats}x" if repeats > 1 else "slice"
            output_path = f"{base}_loop_{int(t_a*1000)}ms_{int(t_b*1000)}ms_{rep_str}.wav"

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        out_ext = os.path.splitext(output_path)[1].lower()

        # Save to WAV
        int16_samples = np.clip(final_audio * 32767.0, -32768.0, 32767.0).astype(np.int16)
        if final_audio.shape[0] > 1:
            interleaved = int16_samples.T.flatten()
        else:
            interleaved = int16_samples.flatten()

        temp_wav = output_path if out_ext in {".wav", ".wave"} else output_path + ".tmp.wav"
        with wave.open(temp_wav, "wb") as wf:
            wf.setnchannels(final_audio.shape[0])
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(interleaved.tobytes())

        # If desired output is MP3 or FLAC, convert via FFmpeg
        if out_ext not in {".wav", ".wave"}:
            ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
            cmd = [
                ffmpeg_bin, "-y", "-v", "error",
                "-i", temp_wav,
                output_path
            ]
            subprocess.run(cmd, check=True)
            if os.path.exists(temp_wav) and temp_wav != output_path:
                os.remove(temp_wav)

        return {
            "success": True,
            "source_file": audio_path,
            "output_file": output_path,
            "start_sec": round(t_a, 3),
            "end_sec": round(t_b, 3),
            "slice_duration_sec": round(t_b - t_a, 3),
            "repeats": repeats,
            "count_in": add_count_in,
            "total_duration_sec": round(final_audio.shape[1] / sr, 3),
            "sample_rate": sr,
            "channels": final_audio.shape[0],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python ab_looper.py <audio_file> <start_sec> <end_sec> [repeats=4] [--count-in] [--bpm=120] [output_file]")
        sys.exit(1)

    audio_file = sys.argv[1]
    start = float(sys.argv[2])
    end = float(sys.argv[3])
    rep = 4
    count_in = False
    bpm_val = 120.0
    out_file = None

    idx = 4
    while idx < len(sys.argv):
        arg = sys.argv[idx]
        if arg == "--count-in":
            count_in = True
        elif arg.startswith("--bpm="):
            bpm_val = float(arg.split("=")[1])
        elif arg.isdigit():
            rep = int(arg)
        elif not out_file:
            out_file = arg
        idx += 1

    print(f"Looping {audio_file} [{start}s -> {end}s] ({rep} repeats)...")
    res = create_ab_loop(
        audio_file,
        start_sec=start,
        end_sec=end,
        repeats=rep,
        add_count_in=count_in,
        bpm=bpm_val,
        output_path=out_file
    )
    if res.get("success"):
        print("Success! Loop exported to:", res["output_file"])
        print(f"Total duration: {res['total_duration_sec']}s (Slice: {res['slice_duration_sec']}s x {res['repeats']})")
    else:
        print("Error:", res.get("error"))
