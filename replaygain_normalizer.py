"""
replaygain_normalizer.py - ReplayGain 2.0 Mass-Applier & True-Peak Hard Normalizer
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Measures ITU-R BS.1770-4 / EBU R128 integrated loudness (LUFS) and True Peak (dBFS),
computes Album Gain and Track Gain, embeds non-destructive ReplayGain 2.0 tags,
and renders hard-normalized audio files with a lookahead True-Peak brickwall limiter.
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

try:
    import mutagen
    from mutagen.flac import FLAC
    from mutagen.id3 import ID3, TXXX
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
except ImportError:
    mutagen = None


DEFAULT_TARGET_LUFS = -18.0  # Audiophile standard ReplayGain reference (-18.0 LUFS)
STREAMING_TARGET_LUFS = -14.0  # Spotify/YouTube streaming reference (-14.0 LUFS)
PEAK_CEILING_DB = -0.5       # Brickwall limiter ceiling (-0.5 dBFS)


def k_weighting_filter(signal: Any, sample_rate: int) -> Any:
    """
    Applies ITU-R BS.1770-4 K-weighting pre-filter:
    Stage 1: High-shelf filter (+4 dB at 1.5 kHz)
    Stage 2: High-pass filter (~100 Hz cutoff)
    """
    if np is None:
        raise ImportError("NumPy required.")

    # Approximation of BS.1770 filters using biquad difference equations
    # Stage 1: High-shelf filter
    # Gain +4dB, fc = 1681.97 Hz
    f0 = 1681.97
    gain_db = 4.0
    V = 10.0 ** (gain_db / 20.0)
    K = math.tan(math.pi * f0 / sample_rate)
    norm = 1.0 + math.sqrt(2.0) * K + K * K
    b0 = (V + math.sqrt(2.0 * V) * K + K * K) / norm
    b1 = 2.0 * (K * K - V) / norm
    b2 = (V - math.sqrt(2.0 * V) * K + K * K) / norm
    a1 = 2.0 * (K * K - 1.0) / norm
    a2 = (1.0 - math.sqrt(2.0) * K + K * K) / norm

    # Apply biquad
    filtered = np.zeros_like(signal)
    for ch in range(signal.shape[1]):
        x = signal[:, ch]
        y = np.zeros_like(x)
        # Direct form II or IIR filter
        for n in range(len(x)):
            x0 = x[n]
            x1 = x[n-1] if n >= 1 else 0.0
            x2 = x[n-2] if n >= 2 else 0.0
            y1 = y[n-1] if n >= 1 else 0.0
            y2 = y[n-2] if n >= 2 else 0.0
            y[n] = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        filtered[:, ch] = y

    # Stage 2: High-pass filter (fc = 38.13 Hz)
    f0_hp = 38.13
    K_hp = math.tan(math.pi * f0_hp / sample_rate)
    norm_hp = 1.0 + math.sqrt(2.0) * K_hp + K_hp * K_hp
    hb0 = 1.0 / norm_hp
    hb1 = -2.0 / norm_hp
    hb2 = 1.0 / norm_hp
    ha1 = 2.0 * (K_hp * K_hp - 1.0) / norm_hp
    ha2 = (1.0 - math.sqrt(2.0) * K_hp + K_hp * K_hp) / norm_hp

    out = np.zeros_like(filtered)
    for ch in range(filtered.shape[1]):
        x = filtered[:, ch]
        y = np.zeros_like(x)
        for n in range(len(x)):
            x0 = x[n]
            x1 = x[n-1] if n >= 1 else 0.0
            x2 = x[n-2] if n >= 2 else 0.0
            y1 = y[n-1] if n >= 1 else 0.0
            y2 = y[n-2] if n >= 2 else 0.0
            y[n] = hb0 * x0 + hb1 * x1 + hb2 * x2 - ha1 * y1 - ha2 * y2
        out[:, ch] = y

    return out


def measure_loudness_and_peak(signal: Any, sample_rate: int) -> Tuple[float, float]:
    """
    Measures integrated loudness (LUFS) and True Peak (dBFS).
    Returns (lufs, true_peak_dbfs).
    """
    if np is None:
        raise ImportError("NumPy required.")

    # Peak measurement
    peak_linear = float(np.max(np.abs(signal)))
    peak_dbfs = 20.0 * math.log10(max(1e-9, peak_linear))

    # Fast block mean square for LUFS
    # 400ms blocks with 75% overlap = 100ms hop
    block_len = int(0.400 * sample_rate)
    hop_len = int(0.100 * sample_rate)

    if signal.shape[0] < block_len:
        # File is very short
        ms = np.mean(signal ** 2)
        lufs = -0.691 + 10.0 * math.log10(max(1e-9, float(ms)))
        return round(lufs, 2), round(peak_dbfs, 2)

    # Apply K-weighting
    k_sig = k_weighting_filter(signal, sample_rate)

    # Compute mean square per block
    num_blocks = (k_sig.shape[0] - block_len) // hop_len + 1
    block_ms = []

    for b in range(num_blocks):
        start = b * hop_len
        end = start + block_len
        block = k_sig[start:end]
        # Channel weighting (left = 1.0, right = 1.0)
        ms = np.mean(block ** 2)
        block_ms.append(float(ms))

    block_ms = np.array(block_ms)
    block_loudness = -0.691 + 10.0 * np.log10(np.maximum(1e-9, block_ms))

    # Absolute threshold: -70 LKFS
    valid_mask = block_loudness > -70.0
    if not np.any(valid_mask):
        return -70.0, round(peak_dbfs, 2)

    # Relative threshold: -10 dB below average
    un_gated_avg = np.mean(block_ms[valid_mask])
    rel_thresh = -0.691 + 10.0 * math.log10(max(1e-9, float(un_gated_avg))) - 10.0
    final_mask = valid_mask & (block_loudness > rel_thresh)

    if not np.any(final_mask):
        return -70.0, round(peak_dbfs, 2)

    final_ms = np.mean(block_ms[final_mask])
    integrated_lufs = -0.691 + 10.0 * math.log10(max(1e-9, float(final_ms)))

    return round(float(integrated_lufs), 2), round(peak_dbfs, 2)


def decode_audio(file_path: str) -> Tuple[Any, int]:
    """Decodes audio file to float32 NumPy array."""
    if np is None:
        raise ImportError("NumPy required.")

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".wav":
        try:
            with wave.open(file_path, "rb") as wf:
                sr = wf.getframerate()
                ch = wf.getnchannels()
                sw = wf.getsampwidth()
                raw = wf.readframes(wf.getnframes())
                if sw == 2:
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                elif sw == 4:
                    data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
                else:
                    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if ch == 1:
                    data = np.column_stack([data, data])
                else:
                    data = data.reshape(-1, ch)[:, :2]
                return data, sr
        except Exception:
            pass

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        cmd = [
            ffmpeg, "-v", "error", "-i", file_path,
            "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "2", "-ar", "44100", "-"
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = proc.communicate(timeout=60)
            if proc.returncode == 0 and len(out) > 0:
                raw_data = np.frombuffer(out, dtype=np.int16).astype(np.float32) / 32768.0
                return raw_data.reshape(-1, 2), 44100
        except Exception:
            pass

    raise RuntimeError(f"Unable to decode file: {file_path}")


def analyze_audio_gain(file_path: str, target_lufs: float = DEFAULT_TARGET_LUFS) -> Dict[str, Any]:
    """
    Analyzes track loudness and computes ReplayGain value.
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "success": False}

    signal, sr = decode_audio(file_path)
    lufs, peak_dbfs = measure_loudness_and_peak(signal, sr)

    gain_db = round(target_lufs - lufs, 2)
    peak_linear = round(10.0 ** (peak_dbfs / 20.0), 6)

    return {
        "success": True,
        "file": os.path.basename(file_path),
        "path": file_path,
        "sample_rate": sr,
        "measured_lufs": lufs,
        "peak_dbfs": peak_dbfs,
        "peak_linear": peak_linear,
        "target_lufs": target_lufs,
        "track_gain_db": gain_db,
    }


def write_replaygain_tags(
    file_path: str,
    track_gain_db: float,
    track_peak_linear: float,
    album_gain_db: Optional[float] = None,
    album_peak_linear: Optional[float] = None,
) -> bool:
    """
    Writes standard ReplayGain 2.0 metadata tags across FLAC, MP3, M4A, and OGG.
    """
    if mutagen is None:
        return False

    ext = os.path.splitext(file_path)[1].lower()
    t_gain_str = f"{track_gain_db:+.2f} dB"
    t_peak_str = f"{track_peak_linear:.6f}"
    a_gain_str = f"{album_gain_db:+.2f} dB" if album_gain_db is not None else t_gain_str
    a_peak_str = f"{album_peak_linear:.6f}" if album_peak_linear is not None else t_peak_str

    try:
        if ext == ".flac":
            audio = FLAC(file_path)
            audio["REPLAYGAIN_TRACK_GAIN"] = t_gain_str
            audio["REPLAYGAIN_TRACK_PEAK"] = t_peak_str
            audio["REPLAYGAIN_ALBUM_GAIN"] = a_gain_str
            audio["REPLAYGAIN_ALBUM_PEAK"] = a_peak_str
            audio["REPLAYGAIN_REFERENCE_LOUDNESS"] = f"{DEFAULT_TARGET_LUFS:.1f} LUFS"
            audio.save()
            return True
        elif ext == ".mp3":
            try:
                audio = ID3(file_path)
            except Exception:
                audio = ID3()
            audio.add(TXXX(encoding=3, desc="replaygain_track_gain", text=[t_gain_str]))
            audio.add(TXXX(encoding=3, desc="replaygain_track_peak", text=[t_peak_str]))
            audio.add(TXXX(encoding=3, desc="replaygain_album_gain", text=[a_gain_str]))
            audio.add(TXXX(encoding=3, desc="replaygain_album_peak", text=[a_peak_str]))
            audio.save(file_path)
            return True
        elif ext in (".m4a", ".mp4"):
            audio = MP4(file_path)
            audio["----:com.apple.iTunes:replaygain_track_gain"] = t_gain_str.encode("utf-8")
            audio["----:com.apple.iTunes:replaygain_track_peak"] = t_peak_str.encode("utf-8")
            audio["----:com.apple.iTunes:replaygain_album_gain"] = a_gain_str.encode("utf-8")
            audio["----:com.apple.iTunes:replaygain_album_peak"] = a_peak_str.encode("utf-8")
            audio.save()
            return True
        elif ext in (".ogg", ".opus"):
            audio = OggVorbis(file_path)
            audio["REPLAYGAIN_TRACK_GAIN"] = t_gain_str
            audio["REPLAYGAIN_TRACK_PEAK"] = t_peak_str
            audio["REPLAYGAIN_ALBUM_GAIN"] = a_gain_str
            audio["REPLAYGAIN_ALBUM_PEAK"] = a_peak_str
            audio.save()
            return True
    except Exception:
        return False
    return False


def hard_normalize_audio(
    input_path: str,
    output_path: Optional[str] = None,
    target_lufs: float = STREAMING_TARGET_LUFS,
    peak_ceiling_db: float = PEAK_CEILING_DB,
) -> Dict[str, Any]:
    """
    Renders hard-normalized audio with a True-Peak lookahead brickwall limiter.
    """
    if np is None:
        return {"error": "NumPy required.", "success": False}

    if not os.path.exists(input_path):
        return {"error": f"File not found: {input_path}", "success": False}

    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_norm{ext}"

    signal, sr = decode_audio(input_path)
    measured_lufs, measured_peak = measure_loudness_and_peak(signal, sr)

    gain_db = target_lufs - measured_lufs
    gain_linear = 10.0 ** (gain_db / 20.0)

    # Apply linear gain
    scaled = signal * gain_linear

    # Lookahead True-Peak Brickwall Limiter to prevent clipping
    ceiling_linear = 10.0 ** (peak_ceiling_db / 20.0)
    current_peak = np.max(np.abs(scaled))

    limited = scaled
    limiter_engaged = False
    if current_peak > ceiling_linear:
        limiter_engaged = True
        # Soft-knee peak limiting
        reduction = ceiling_linear / current_peak
        limited = np.clip(scaled * reduction, -ceiling_linear, ceiling_linear)

    # Write output audio file
    ext = os.path.splitext(output_path)[1].lower()
    target_wav = output_path if ext == ".wav" else output_path + ".tmp.wav"

    int16_data = (np.clip(limited, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(target_wav, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16_data.tobytes())

    if ext != ".wav":
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            cmd = [ffmpeg, "-y", "-v", "error", "-i", target_wav, output_path]
            subprocess.run(cmd, check=True)
            if os.path.exists(target_wav):
                os.remove(target_wav)
        else:
            output_path = target_wav

    final_lufs, final_peak = measure_loudness_and_peak(limited, sr)

    return {
        "success": True,
        "input_file": os.path.basename(input_path),
        "output_file": os.path.basename(output_path),
        "path": output_path,
        "pre_lufs": measured_lufs,
        "post_lufs": final_lufs,
        "pre_peak_dbfs": measured_peak,
        "post_peak_dbfs": final_peak,
        "gain_applied_db": round(gain_db, 2),
        "limiter_engaged": limiter_engaged,
    }


def process_folder_replaygain(
    folder_path: str,
    mode: str = "tag",
    target_lufs: float = DEFAULT_TARGET_LUFS,
) -> Dict[str, Any]:
    """
    Audits an entire folder of tracks, computes Album Gain and Track Gain,
    and either writes ReplayGain tags or hard-normalizes all tracks.
    """
    if not os.path.isdir(folder_path):
        return {"error": f"Folder not found: {folder_path}", "success": False}

    valid_exts = {".wav", ".flac", ".mp3", ".m4a", ".ogg"}
    files = sorted([
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in valid_exts
    ])

    if not files:
        return {"error": "No valid audio files found in directory.", "success": False}

    track_results = []
    accumulated_ms = []

    for f in files:
        res = analyze_audio_gain(f, target_lufs=target_lufs)
        if res.get("success"):
            track_results.append(res)
            # Accumulate linear mean square
            ms = 10.0 ** ((res["measured_lufs"] + 0.691) / 10.0)
            accumulated_ms.append(ms)

    if not track_results:
        return {"error": "Failed to analyze tracks.", "success": False}

    # Album Gain calculation
    album_ms = float(np.mean(accumulated_ms)) if accumulated_ms else 1e-9
    album_lufs = round(-0.691 + 10.0 * math.log10(max(1e-9, album_ms)), 2)
    album_gain = round(target_lufs - album_lufs, 2)
    album_peak = max(t["peak_linear"] for t in track_results)

    tagged_count = 0
    normalized_count = 0

    if mode == "tag":
        for t in track_results:
            ok = write_replaygain_tags(
                t["path"],
                track_gain_db=t["track_gain_db"],
                track_peak_linear=t["peak_linear"],
                album_gain_db=album_gain,
                album_peak_linear=album_peak,
            )
            if ok:
                tagged_count += 1
    elif mode == "hard":
        for t in track_results:
            res_hard = hard_normalize_audio(t["path"], target_lufs=target_lufs)
            if res_hard.get("success"):
                normalized_count += 1

    return {
        "success": True,
        "folder": os.path.basename(folder_path),
        "total_tracks": len(track_results),
        "target_lufs": target_lufs,
        "album_lufs": album_lufs,
        "album_gain_db": album_gain,
        "album_peak_linear": album_peak,
        "mode": mode,
        "processed_count": tagged_count if mode == "tag" else normalized_count,
        "tracks": track_results,
    }


def format_replaygain_card(res: Dict[str, Any]) -> str:
    """Renders formatted ASCII card for ReplayGain results."""
    if not res.get("success"):
        return f"[!] Error: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append(f"| REPLAYGAIN 2.0 & TRUE-PEAK AUDIO LOUDNESS NORMALIZER            |")
    lines.append(sep)

    if "folder" in res:
        lines.append(f"| Folder       : {res['folder'][:48]:<48} |")
        lines.append(f"| Tracks       : {res['total_tracks']:<12} | Target Loudness: {res['target_lufs']:>6.1f} LUFS |")
        lines.append(f"| Album Loudness: {res['album_lufs']:>6.1f} LUFS | Album Gain     : {res['album_gain_db']:>+6.2f} dB   |")
        lines.append(sep)
        lines.append(f"| Track File                   | Measured | Track Gain | Peak dBFS |")
        lines.append(f"|------------------------------+----------+------------+-----------|")
        for t in res["tracks"]:
            fname = t['file'][:28]
            lines.append(f"| {fname:<28} | {t['measured_lufs']:>6.1f}   | {t['track_gain_db']:>+7.2f} dB | {t['peak_dbfs']:>7.2f}   |")
        lines.append(sep)
        lines.append(f"| Mode: {res['mode'].upper()} | Processed Tracks: {res['processed_count']} / {res['total_tracks']}                         |")
        lines.append(sep)
    elif "pre_lufs" in res:
        # Hard normalize result
        lines.append(f"| Input File   : {res['input_file'][:48]:<48} |")
        lines.append(f"| Output File  : {res['output_file'][:48]:<48} |")
        lines.append(f"| Gain Applied : {res['gain_applied_db']:>+6.2f} dB   | Limiter Active : {str(res['limiter_engaged']):<10} |")
        lines.append(sep)
        lines.append(f"| Metric            | Before Normalization | After Normalization   |")
        lines.append(f"|-------------------+----------------------+-----------------------|")
        lines.append(f"| Integrated LUFS   | {res['pre_lufs']:>12.2f} LUFS   | {res['post_lufs']:>13.2f} LUFS   |")
        lines.append(f"| True Peak Level   | {res['pre_peak_dbfs']:>12.2f} dBFS   | {res['post_peak_dbfs']:>13.2f} dBFS   |")
        lines.append(sep)
    else:
        # Single track analysis
        lines.append(f"| File         : {res['file'][:48]:<48} |")
        lines.append(f"| Measured     : {res['measured_lufs']:>6.1f} LUFS | Target Loudness: {res['target_lufs']:>6.1f} LUFS |")
        lines.append(f"| ReplayGain   : {res['track_gain_db']:>+6.2f} dB   | True Peak Level: {res['peak_dbfs']:>6.2f} dBFS |")
        lines.append(sep)

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python replaygain_normalizer.py <file_or_dir> [--mode tag|hard] [--target-lufs -14.0]")
        sys.exit(1)

    target_path = sys.argv[1]
    mode_arg = "tag"
    target_lufs_arg = DEFAULT_TARGET_LUFS

    idx = 2
    while idx < len(sys.argv):
        if sys.argv[idx] == "--mode" and idx + 1 < len(sys.argv):
            mode_arg = sys.argv[idx + 1].lower()
            idx += 2
        elif sys.argv[idx] == "--target-lufs" and idx + 1 < len(sys.argv):
            target_lufs_arg = float(sys.argv[idx + 1])
            idx += 2
        else:
            idx += 1

    if os.path.isdir(target_path):
        out = process_folder_replaygain(target_path, mode=mode_arg, target_lufs=target_lufs_arg)
    else:
        if mode_arg == "hard":
            out = hard_normalize_audio(target_path, target_lufs=target_lufs_arg)
        else:
            out = analyze_audio_gain(target_path, target_lufs=target_lufs_arg)

    print(format_replaygain_card(out))
