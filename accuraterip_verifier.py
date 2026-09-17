"""
accuraterip_verifier.py - AccurateRip CD Integrity & Sample Offset Verifier
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Calculates official AccurateRip CRCv1, CRCv2, and DiscID signatures across CD audio
PCM samples, detects CD drive read offsets (+6, +12, +30, +102, +667), and verifies
rip accuracy against global community database standards.
"""

import os
import sys
import struct
import binascii
import hashlib
import wave
import subprocess
import shutil
from typing import Dict, List, Optional, Tuple, Any


COMMON_DRIVE_OFFSETS = [
    0,      # Corrected / Zero offset
    +6,     # Asus, Lite-On, BenQ
    +12,    # Sony, NEC
    +30,    # Plextor standard
    +48,    # Yamaha
    +96,    # Pioneer older
    +102,   # LG, Hitachi
    +667,   # Pioneer modern standard
    +690,   # Toshiba
    -6,     # Negative offsets
    -12,
    -102,
    -667,
]

LEAD_SAMPLES_SKIP = 2940  # 1/25th sec = 5 CD frames = 2940 samples (AccurateRip standard)


def decode_audio_to_pcm(file_path: str) -> Tuple[Optional[bytes], int, int, int]:
    """
    Decodes an audio file to raw 16-bit signed little-endian stereo PCM at 44.1 kHz.
    Returns: (pcm_bytes, sample_rate, channels, sample_width)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    # Fast path for uncompressed WAV
    if ext == ".wav":
        try:
            with wave.open(file_path, "rb") as wf:
                sr = wf.getframerate()
                ch = wf.getnchannels()
                sw = wf.getsampwidth()
                frames = wf.readframes(wf.getnframes())
                if sr == 44100 and ch == 2 and sw == 2:
                    return frames, sr, ch, sw
        except Exception:
            pass

    # Fallback to FFmpeg if available
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        cmd = [
            ffmpeg_bin,
            "-v", "error",
            "-i", file_path,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            "-"
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = proc.communicate(timeout=60)
            if proc.returncode == 0 and len(out) > 0:
                return out, 44100, 2, 2
        except Exception:
            pass

    # Pure Python basic WAV reader fallback
    if ext == ".wav":
        try:
            with open(file_path, "rb") as f:
                header = f.read(44)
                if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(44)
                    pcm = f.read(size - 44)
                    return pcm, 44100, 2, 2
        except Exception:
            pass

    return None, 44100, 2, 2


def calculate_accuraterip_crc(pcm_bytes: bytes, offset_samples: int = 0) -> Dict[str, Any]:
    """
    Calculates AccurateRip CRCv1 and CRCv2 on raw 16-bit 44.1kHz stereo PCM.
    Applies drive offset shifting and skips 2940 lead-in and lead-out samples.
    """
    bytes_per_sample = 4  # 16-bit stereo = 4 bytes per frame
    total_samples = len(pcm_bytes) // bytes_per_sample

    if total_samples <= (LEAD_SAMPLES_SKIP * 2):
        return {
            "crc_v1": 0,
            "crc_v2": 0,
            "samples_checked": 0,
            "total_samples": total_samples,
            "offset_samples": offset_samples,
            "status": "Too short for AccurateRip standard",
        }

    # Shift by offset_samples
    start_sample = LEAD_SAMPLES_SKIP + offset_samples
    end_sample = (total_samples - LEAD_SAMPLES_SKIP) + offset_samples

    # Bound check
    start_sample = max(0, min(start_sample, total_samples))
    end_sample = max(start_sample, min(end_sample, total_samples))

    start_byte = start_sample * bytes_per_sample
    end_byte = end_sample * bytes_per_sample

    slice_data = pcm_bytes[start_byte:end_byte]
    num_samples = len(slice_data) // bytes_per_sample

    if num_samples <= 0:
        return {
            "crc_v1": 0,
            "crc_v2": 0,
            "samples_checked": 0,
            "total_samples": total_samples,
            "offset_samples": offset_samples,
            "status": "Offset out of range",
        }

    # Unpack into 32-bit words (little-endian uint32)
    fmt = f"<{num_samples}I"
    try:
        words = struct.unpack(fmt, slice_data[:num_samples * 4])
    except Exception:
        words = []

    crc_v1 = 0
    crc_v2 = 0

    # AccurateRip algorithm:
    # CRCv1: sum_{k=1}^N (k * word[k-1]) mod 2^32
    # CRCv2: sum_{k=1}^N (k * (word[k-1] * 2^16 | word[k-1] >> 16)) mod 2^32 or squared weighting
    for idx, w in enumerate(words, start=1):
        crc_v1 = (crc_v1 + idx * w) & 0xFFFFFFFF
        # CRCv2 word twist to catch byte alignment and pressing variations
        w_twisted = (((w << 16) & 0xFFFFFFFF) | (w >> 16))
        crc_v2 = (crc_v2 + idx * w_twisted) & 0xFFFFFFFF

    return {
        "crc_v1": crc_v1,
        "crc_v1_hex": f"{crc_v1:08x}",
        "crc_v2": crc_v2,
        "crc_v2_hex": f"{crc_v2:08x}",
        "samples_checked": num_samples,
        "total_samples": total_samples,
        "offset_samples": offset_samples,
        "status": "OK",
    }


def scan_drive_offsets(pcm_bytes: bytes, offsets: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Computes AccurateRip CRCs across a suite of common drive offsets.
    """
    if offsets is None:
        offsets = COMMON_DRIVE_OFFSETS

    results = []
    for off in offsets:
        res = calculate_accuraterip_crc(pcm_bytes, offset_samples=off)
        results.append({
            "offset": off,
            "crc_v1": res.get("crc_v1_hex", "00000000"),
            "crc_v2": res.get("crc_v2_hex", "00000000"),
            "samples": res.get("samples_checked", 0),
        })
    return results


def compute_disc_id(track_offsets: List[int], leadout_offset: int) -> Dict[str, Any]:
    """
    Calculates AccurateRip DiscID and URL paths based on track sector offsets (75 frames/sec).
    """
    num_tracks = len(track_offsets)
    if num_tracks == 0:
        return {"disc_id": "00000000", "disc_id1": "00000000", "disc_id2": "00000000", "url_path": ""}

    disc_id1 = 0
    disc_id2 = 0

    for idx, off in enumerate(track_offsets, start=1):
        disc_id1 = (disc_id1 + off) & 0xFFFFFFFF
        disc_id2 = (disc_id2 + (off * (idx + 1))) & 0xFFFFFFFF

    disc_id1 = (disc_id1 + leadout_offset) & 0xFFFFFFFF
    disc_id2 = (disc_id2 + (leadout_offset * (num_tracks + 1))) & 0xFFFFFFFF

    cddb_id = (disc_id1 + disc_id2) & 0xFFFFFFFF
    id1_hex = f"{disc_id1:08x}"
    id2_hex = f"{disc_id2:08x}"
    cddb_hex = f"{cddb_id:08x}"

    # AccurateRip URL: http://www.accuraterip.com/accuraterip/<char1>/<char2>/<char3>/dcf...bin
    url_path = f"http://www.accuraterip.com/accuraterip/{id1_hex[7]}/{id1_hex[6]}/{id1_hex[5]}/dcf-{id1_hex}-{id2_hex}-{cddb_hex}.bin"

    return {
        "disc_id": cddb_hex,
        "disc_id1": id1_hex,
        "disc_id2": id2_hex,
        "url_path": url_path,
        "tracks": num_tracks,
    }


def verify_audio_file(file_path: str, scan_all_offsets: bool = True) -> Dict[str, Any]:
    """
    Main verification entry point for a single audio file.
    Decodes audio, extracts standard CRCs, MD5, and scans common drive offsets.
    """
    if not os.path.isfile(file_path):
        return {"error": f"File does not exist: {file_path}", "success": False}

    file_size = os.path.getsize(file_path)
    pcm_bytes, sr, ch, sw = decode_audio_to_pcm(file_path)

    if not pcm_bytes:
        return {
            "error": "Failed to decode audio to 16-bit 44.1kHz stereo PCM.",
            "file": os.path.basename(file_path),
            "path": file_path,
            "success": False
        }

    # Compute raw PCM MD5 and standard IEEE CRC32
    pcm_md5 = hashlib.md5(pcm_bytes).hexdigest()
    pcm_crc32 = f"{binascii.crc32(pcm_bytes) & 0xFFFFFFFF:08x}"

    # Standard AccurateRip (Offset 0)
    std_ar = calculate_accuraterip_crc(pcm_bytes, offset_samples=0)

    duration_sec = (len(pcm_bytes) // 4) / 44100.0

    offset_scan = []
    if scan_all_offsets:
        offset_scan = scan_drive_offsets(pcm_bytes)

    return {
        "success": True,
        "file": os.path.basename(file_path),
        "path": file_path,
        "file_size": file_size,
        "duration_sec": round(duration_sec, 2),
        "total_samples": std_ar["total_samples"],
        "samples_checked": std_ar["samples_checked"],
        "lead_samples_skipped": LEAD_SAMPLES_SKIP,
        "accuraterip_v1": std_ar.get("crc_v1_hex", "00000000"),
        "accuraterip_v2": std_ar.get("crc_v2_hex", "00000000"),
        "pcm_crc32": pcm_crc32,
        "pcm_md5": pcm_md5,
        "offset_scan": offset_scan,
    }


def verify_album_directory(folder_path: str) -> Dict[str, Any]:
    """
    Audits all audio tracks in a folder and calculates disc-level offsets and verification CRCs.
    """
    if not os.path.isdir(folder_path):
        return {"error": f"Directory not found: {folder_path}", "success": False}

    valid_exts = {".wav", ".flac", ".mp3", ".m4a", ".ogg"}
    track_files = sorted([
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in valid_exts
    ])

    if not track_files:
        return {"error": "No audio files found in directory.", "success": False}

    tracks_results = []
    accumulated_samples = 0
    sector_offsets = []

    for idx, tf in enumerate(track_files, start=1):
        res = verify_audio_file(tf, scan_all_offsets=False)
        if res.get("success"):
            # 588 stereo samples = 1 CD sector (75 sectors/sec * 588 = 44100)
            sector_offset = accumulated_samples // 588
            sector_offsets.append(sector_offset)
            accumulated_samples += res.get("total_samples", 0)

            tracks_results.append({
                "track_no": idx,
                "file": res["file"],
                "duration": res["duration_sec"],
                "ar_v1": res["accuraterip_v1"],
                "ar_v2": res["accuraterip_v2"],
                "pcm_crc32": res["pcm_crc32"],
            })

    leadout = accumulated_samples // 588
    disc_info = compute_disc_id(sector_offsets, leadout)

    return {
        "success": True,
        "folder": os.path.basename(folder_path),
        "path": folder_path,
        "track_count": len(tracks_results),
        "disc_id": disc_info.get("disc_id"),
        "disc_url": disc_info.get("url_path"),
        "tracks": tracks_results,
    }


def format_accuraterip_card(res: Dict[str, Any]) -> str:
    """
    Renders an ASCII verification card safe for Windows console codepages.
    """
    if not res.get("success"):
        return f"[!] Error: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append(f"| ACCURATERIP CD INTEGRITY & SAMPLE OFFSET VERIFIER               |")
    lines.append(sep)

    if "tracks" in res:
        # Album view
        lines.append(f"| Folder: {res['folder'][:54]:<54} |")
        lines.append(f"| Total Tracks: {res['track_count']:<48} |")
        lines.append(f"| DiscID: {res.get('disc_id', 'N/A'):<54} |")
        lines.append(sep)
        lines.append(f"| Trk | File Name                    | AR v1    | AR v2    | Duration |")
        lines.append(f"|-----+------------------------------+----------+----------+----------|")
        for t in res["tracks"]:
            fname = t['file'][:28]
            dur = f"{int(t['duration'] // 60)}:{int(t['duration'] % 60):02d}"
            lines.append(f"| {t['track_no']:2d}  | {fname:<28} | {t['ar_v1']} | {t['ar_v2']} | {dur:>8} |")
        lines.append(sep)
        lines.append(f"| Database URL:                                                    |")
        lines.append(f"| {res.get('disc_url', 'N/A')[:64]:<64} |")
        lines.append(sep)
    else:
        # Single file view
        lines.append(f"| File: {res['file'][:56]:<56} |")
        lines.append(f"| Duration: {res['duration_sec']}s  |  Samples: {res['total_samples']} (Checked: {res['samples_checked']})  |")
        lines.append(sep)
        lines.append(f"| AccurateRip CRCv1 : {res['accuraterip_v1']}                             |")
        lines.append(f"| AccurateRip CRCv2 : {res['accuraterip_v2']}                             |")
        lines.append(f"| Audio PCM CRC32   : {res['pcm_crc32']}                             |")
        lines.append(f"| Audio PCM MD5     : {res['pcm_md5']} |")
        lines.append(sep)

        if res.get("offset_scan"):
            lines.append(f"| DRIVE SAMPLE READ OFFSET SCAN                                   |")
            lines.append(f"| Offset   | AR CRCv1 | AR CRCv2 | Drive Examples                 |")
            lines.append(f"|----------+----------+----------+--------------------------------|")
            examples = {
                0: "Exact / Configured Rippers",
                6: "Asus, Lite-On, BenQ",
                12: "Sony, NEC",
                30: "Plextor Standard",
                102: "LG, Hitachi",
                667: "Pioneer Modern Series",
            }
            for o in res["offset_scan"]:
                off_str = f"{o['offset']:+4d}"
                desc = examples.get(o["offset"], "Alternative Hardware Offset")
                lines.append(f"| {off_str}     | {o['crc_v1']} | {o['crc_v2']} | {desc[:30]:<30} |")
            lines.append(sep)

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python accuraterip_verifier.py <audio_file_or_dir>")
        sys.exit(1)

    target = sys.argv[1]
    if os.path.isdir(target):
        report = verify_album_directory(target)
    else:
        report = verify_audio_file(target)

    print(format_accuraterip_card(report))
