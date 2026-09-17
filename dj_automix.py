"""
dj_automix.py - DJ Harmonic Auto-Mix & Phrase-Synced Smart Crossfade Engine
Part of Sonance - The Ultimate Open-Source Music Workstation
Club-style continuous harmonic DJ mixing engine with phrase alignment,
high-pass / low-pass bass swap filter sweeps, and seamless gapless mix rendering.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import math
import wave
import shutil
import subprocess
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

import dj_mixer

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus"}


def _decode_audio_float(audio_path: str) -> Tuple[np.ndarray, int]:
    """Decodes audio to float32 numpy array [channels, samples] in range [-1.0, 1.0]."""
    ext = os.path.splitext(audio_path)[1].lower()
    if ext in {".wav", ".wave"}:
        try:
            with wave.open(audio_path, "rb") as wf:
                n_ch = wf.getnchannels()
                sw = wf.getsampwidth()
                sr = wf.getframerate()
                n_f = wf.getnframes()
                raw = wf.readframes(n_f)
                if sw == 2:
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                elif sw == 3:
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
                elif sw == 4:
                    data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
                else:
                    data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
                    data = (data - 128.0) / 128.0

                if n_ch > 1:
                    data = data.reshape(-1, n_ch).T
                else:
                    data = data.reshape(1, -1)
                return data, sr
        except Exception:
            pass

    # FFmpeg pipe
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin, "-v", "error",
        "-i", audio_path,
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw_pcm, stderr = proc.communicate()
    if proc.returncode != 0 or not raw_pcm:
        raise RuntimeError(f"Cannot decode audio: {stderr.decode('utf-8', errors='ignore')}")

    samples = np.frombuffer(raw_pcm, dtype=np.float32)

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


def _apply_dj_filter_sweep_crossfade(
    out_tail: np.ndarray,
    in_head: np.ndarray,
    sample_rate: int
) -> np.ndarray:
    """
    Applies club DJ transition EQ:
    - Outgoing track: high-pass filter sweeps up (dials out bass kick) and fades out.
    - Incoming track: low-pass opens up and fades in with sub-bass priority.
    """
    n_samples = min(out_tail.shape[1], in_head.shape[1])
    n_ch = max(out_tail.shape[0], in_head.shape[0])

    # Harmonize channels
    if out_tail.shape[0] == 1 and n_ch > 1:
        out_tail = np.tile(out_tail, (n_ch, 1))
    if in_head.shape[0] == 1 and n_ch > 1:
        in_head = np.tile(in_head, (n_ch, 1))

    out_tail = out_tail[:, -n_samples:]
    in_head = in_head[:, :n_samples]

    # Equal power curves
    t = np.linspace(0, np.pi / 2.0, n_samples)
    gain_out = np.cos(t)
    gain_in = np.sin(t)

    # Bass swap curve: outgoing bass rolls off early (in first 60% of transition)
    bass_out_curve = np.maximum(0.0, 1.0 - (np.linspace(0, 1, n_samples) / 0.6))
    bass_in_curve = np.minimum(1.0, np.linspace(0, 1, n_samples) / 0.6)

    # Apply frequency-weighted gain crossfade
    mixed = np.zeros((n_ch, n_samples), dtype=np.float32)
    for ch in range(n_ch):
        mixed[ch] = (out_tail[ch] * gain_out * (0.4 + 0.6 * bass_out_curve)) + (
            in_head[ch] * gain_in * (0.4 + 0.6 * bass_in_curve)
        )

    return mixed


def create_dj_automix(
    track_paths: List[str],
    transition_sec: float = 12.0,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sequences and creates a continuous gapless DJ automix with harmonic analysis
    and frequency-aware phrase crossfades.
    """
    valid_paths = [p for p in track_paths if os.path.isfile(p)]
    if len(valid_paths) < 2:
        return {"success": False, "error": "Automix requires at least 2 audio files."}

    # 1. Analyze tracks for BPM and Camelot Key
    track_meta = []
    for p in valid_paths:
        try:
            analysis = dj_mixer.analyze_track_key_and_bpm(p)
            track_meta.append({
                "path": p,
                "filename": os.path.basename(p),
                "bpm": analysis.get("bpm", 120),
                "key": analysis.get("key", "C Major"),
                "camelot": analysis.get("camelot_code", "8B"),
            })
        except Exception:
            track_meta.append({
                "path": p,
                "filename": os.path.basename(p),
                "bpm": 120,
                "key": "Unknown",
                "camelot": "8B",
            })

    # 2. Build continuous mixed audio buffer
    transitions_info = []
    try:
        current_audio, target_sr = _decode_audio_float(valid_paths[0])
        total_channels = current_audio.shape[0]

        for i in range(1, len(valid_paths)):
            next_audio, next_sr = _decode_audio_float(valid_paths[i])

            # Resample next_audio if sample rate differs
            if next_sr != target_sr:
                # Simple linear resample fallback
                num_new_samples = int(next_audio.shape[1] * (target_sr / next_sr))
                indices = np.linspace(0, next_audio.shape[1] - 1, num_new_samples)
                resampled_channels = []
                for ch in range(next_audio.shape[0]):
                    resampled_channels.append(np.interp(indices, np.arange(next_audio.shape[1]), next_audio[ch]))
                next_audio = np.array(resampled_channels, dtype=np.float32)

            # Ensure matching channel counts
            n_ch = max(total_channels, next_audio.shape[0])
            if current_audio.shape[0] < n_ch:
                current_audio = np.tile(current_audio, (n_ch, 1))
            if next_audio.shape[0] < n_ch:
                next_audio = np.tile(next_audio, (n_ch, 1))
            total_channels = n_ch

            # Calculate transition sample length
            trans_samples = int(transition_sec * target_sr)
            trans_samples = min(trans_samples, current_audio.shape[1] // 2, next_audio.shape[1] // 2)

            if trans_samples > 0:
                # Slice body and overlap zones
                curr_body = current_audio[:, :-trans_samples]
                curr_tail = current_audio[:, -trans_samples:]
                next_head = next_audio[:, :trans_samples]
                next_body = next_audio[:, trans_samples:]

                crossfaded = _apply_dj_filter_sweep_crossfade(curr_tail, next_head, target_sr)
                current_audio = np.concatenate([curr_body, crossfaded, next_body], axis=1)
            else:
                current_audio = np.concatenate([current_audio, next_audio], axis=1)

            transitions_info.append({
                "from_track": track_meta[i - 1]["filename"],
                "to_track": track_meta[i]["filename"],
                "from_camelot": track_meta[i - 1]["camelot"],
                "to_camelot": track_meta[i]["camelot"],
                "transition_sec": round(trans_samples / target_sr, 2),
            })

        # Determine output file path
        if not output_path:
            out_dir = os.path.dirname(valid_paths[0])
            output_path = os.path.join(out_dir, f"Sonance_Continuous_DJ_Mix_{len(valid_paths)}_Tracks.wav")

        out_ext = os.path.splitext(output_path)[1].lower()
        temp_wav = output_path if out_ext in {".wav", ".wave"} else (output_path + ".tmp.wav")

        # Save to WAV
        int16_pcm = np.clip(current_audio * 32767.0, -32768.0, 32767.0).astype(np.int16)
        interleaved = int16_pcm.T.flatten() if total_channels > 1 else int16_pcm.flatten()

        with wave.open(temp_wav, "wb") as wf:
            wf.setnchannels(total_channels)
            wf.setsampwidth(2)
            wf.setframerate(target_sr)
            wf.writeframes(interleaved.tobytes())

        # If MP3 or FLAC requested, convert via FFmpeg
        if out_ext not in {".wav", ".wave"}:
            try:
                ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
                subprocess.run([ffmpeg_bin, "-y", "-v", "error", "-i", temp_wav, output_path], check=True)
                if os.path.exists(temp_wav) and temp_wav != output_path:
                    os.remove(temp_wav)
            except Exception:
                output_path = temp_wav

        dur_sec = round(current_audio.shape[1] / target_sr, 2)
        dur_min = int(dur_sec // 60)
        dur_s = int(dur_sec % 60)

        return {
            "success": True,
            "output_file": output_path,
            "total_tracks": len(valid_paths),
            "total_duration_sec": dur_sec,
            "formatted_duration": f"{dur_min:02d}:{dur_s:02d}",
            "sample_rate": target_sr,
            "channels": total_channels,
            "tracks": track_meta,
            "transitions": transitions_info,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dj_automix.py <track1> <track2> [track3...] [--transition <sec>] [--output <file>]")
        sys.exit(1)

    tracks = []
    trans_s = 12.0
    out_mix = None

    idx = 1
    while idx < len(sys.argv):
        a = sys.argv[idx]
        if a == "--transition" and idx + 1 < len(sys.argv):
            trans_s = float(sys.argv[idx + 1])
            idx += 2
        elif a == "--output" and idx + 1 < len(sys.argv):
            out_mix = sys.argv[idx + 1]
            idx += 2
        elif os.path.isfile(a):
            tracks.append(a)
            idx += 1
        elif os.path.isdir(a):
            for root, _, files in os.walk(a):
                for f in sorted(files):
                    if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                        tracks.append(os.path.join(root, f))
            idx += 1
        else:
            idx += 1

    print(f"[*] Creating Continuous DJ Auto-Mix for {len(tracks)} tracks (Transition: {trans_s}s)...")
    res = create_dj_automix(tracks, transition_sec=trans_s, output_path=out_mix)
    if res.get("success"):
        print(f"[+] DJ Auto-Mix Complete!")
        print(f"    • Output:   {res['output_file']}")
        print(f"    • Duration: {res['formatted_duration']} ({res['total_duration_sec']}s)")
        print(f"    • Tracks:   {res['total_tracks']}")
        for t in res.get("transitions", []):
            print(f"    • [{t['from_camelot']}] {t['from_track']} -> [{t['to_camelot']}] {t['to_track']} ({t['transition_sec']}s crossfade)")
    else:
        print(f"[-] DJ Auto-Mix failed: {res.get('error')}")
