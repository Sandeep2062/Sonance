"""
flac_verifier.py - Lossless FLAC Stream MD5 Integrity Auditor & Bit-Rot Scanner
Part of Sonance - The Ultimate Open-Source Music Workstation
Extracts the 128-bit unencoded audio MD5 signature from the FLAC STREAMINFO header,
decodes raw PCM samples, and verifies bit-perfect integrity to detect silent bit rot.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import hashlib
import struct
import shutil
import subprocess
from typing import Dict, List, Any, Optional, Tuple


def read_flac_streaminfo(flac_path: str) -> Optional[Dict[str, Any]]:
    """
    Reads the 34-byte FLAC STREAMINFO metadata block.
    Extracts sample rate, channels, bits per sample, total samples, and stored MD5.
    """
    if not os.path.isfile(flac_path):
        return None

    try:
        with open(flac_path, "rb") as f:
            magic = f.read(4)
            if magic != b"fLaC":
                return None

            header = f.read(4)
            if len(header) < 4:
                return None

            block_type = header[0] & 0x7F
            block_len = (header[1] << 16) | (header[2] << 8) | header[3]

            if block_type != 0 or block_len < 34:
                return None

            streaminfo = f.read(34)
            if len(streaminfo) < 34:
                return None

            min_block_size = (streaminfo[0] << 8) | streaminfo[1]
            max_block_size = (streaminfo[2] << 8) | streaminfo[3]
            min_frame_size = (streaminfo[4] << 16) | (streaminfo[5] << 8) | streaminfo[6]
            max_frame_size = (streaminfo[7] << 16) | (streaminfo[8] << 8) | streaminfo[9]

            # 8 bytes: sample_rate (20 bits), channels (3 bits), bps (5 bits), total_samples (36 bits)
            b8 = streaminfo[10:18]
            val = struct.unpack(">Q", b8)[0]
            sample_rate = val >> 44
            channels = ((val >> 41) & 0x07) + 1
            bits_per_sample = ((val >> 36) & 0x1F) + 1
            total_samples = val & 0xFFFFFFFFF

            stored_md5 = streaminfo[18:34].hex()

            return {
                "sample_rate": sample_rate,
                "channels": channels,
                "bits_per_sample": bits_per_sample,
                "total_samples": total_samples,
                "duration_sec": round(total_samples / sample_rate, 2) if sample_rate > 0 else 0,
                "stored_md5": stored_md5,
                "has_stored_md5": stored_md5 != "00000000000000000000000000000000",
            }
    except Exception:
        return None


def verify_single_flac(flac_path: str) -> Dict[str, Any]:
    """
    Decodes the FLAC audio stream, calculates the MD5 hash of raw PCM samples,
    and compares it with the stored STREAMINFO MD5 checksum.
    """
    info = read_flac_streaminfo(flac_path)
    if not info:
        return {
            "success": False,
            "file": flac_path,
            "filename": os.path.basename(flac_path),
            "status": "INVALID_FLAC",
            "error": "Not a valid FLAC file or missing STREAMINFO header.",
        }

    stored_md5 = info["stored_md5"]
    if not info["has_stored_md5"]:
        return {
            "success": True,
            "file": flac_path,
            "filename": os.path.basename(flac_path),
            "status": "NO_MD5_STORED",
            "stored_md5": stored_md5,
            "calculated_md5": None,
            "sample_rate": info["sample_rate"],
            "channels": info["channels"],
            "bits_per_sample": info["bits_per_sample"],
            "duration_sec": info["duration_sec"],
            "message": "Encoder omitted MD5 signature during creation (all zeros).",
        }

    # Format for FFmpeg raw PCM extraction matching FLAC bit depth
    bps = info["bits_per_sample"]
    if bps == 16:
        pcm_fmt = "s16le"
    elif bps == 24:
        pcm_fmt = "s24le"
    elif bps == 32:
        pcm_fmt = "s32le"
    elif bps == 8:
        pcm_fmt = "u8"
    else:
        pcm_fmt = "s16le"

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-v", "error",
        "-i", flac_path,
        "-f", pcm_fmt,
        "-"
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        hasher = hashlib.md5()
        total_bytes = 0

        while True:
            chunk = proc.stdout.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
            total_bytes += len(chunk)

        _, stderr = proc.communicate()
        if proc.returncode != 0 and total_bytes == 0:
            return {
                "success": False,
                "file": flac_path,
                "filename": os.path.basename(flac_path),
                "status": "DECODE_ERROR",
                "error": stderr.decode("utf-8", errors="ignore"),
            }

        calculated_md5 = hasher.hexdigest()
        is_match = (calculated_md5.lower() == stored_md5.lower())

        if is_match:
            status = "BIT_PERFECT_MATCH"
            msg = "100% Bit-Perfect & Genuine Lossless Master. No corruption or bit rot detected."
        elif proc.returncode != 0:
            status = "TRUNCATED_STREAM"
            msg = "Premature end of file / truncated audio stream."
        else:
            status = "CORRUPTED_MISMATCH"
            msg = "Checksum mismatch! Audio data has been corrupted or altered."

        return {
            "success": True,
            "file": flac_path,
            "filename": os.path.basename(flac_path),
            "status": status,
            "is_bit_perfect": is_match,
            "stored_md5": stored_md5,
            "calculated_md5": calculated_md5,
            "sample_rate": info["sample_rate"],
            "channels": info["channels"],
            "bits_per_sample": info["bits_per_sample"],
            "duration_sec": info["duration_sec"],
            "decoded_bytes": total_bytes,
            "message": msg,
        }

    except FileNotFoundError:
        return {
            "success": True,
            "file": flac_path,
            "filename": os.path.basename(flac_path),
            "status": "HEADER_VERIFIED",
            "is_bit_perfect": None,
            "stored_md5": stored_md5,
            "calculated_md5": None,
            "sample_rate": info["sample_rate"],
            "channels": info["channels"],
            "bits_per_sample": info["bits_per_sample"],
            "duration_sec": info["duration_sec"],
            "message": "FLAC STREAMINFO header is valid and stored MD5 extracted (Install FFmpeg for full PCM sample stream verification).",
        }
    except Exception as e:
        return {
            "success": False,
            "file": flac_path,
            "filename": os.path.basename(flac_path),
            "status": "AUDIT_FAILED",
            "error": str(e),
        }


def verify_flac_directory(dir_path: str) -> Dict[str, Any]:
    """
    Recursively scans a directory for all .flac files and performs bit-perfect integrity checks.
    """
    if not os.path.isdir(dir_path):
        return {"success": False, "error": f"Directory not found: {dir_path}"}

    flac_files = []
    for root, _, files in os.walk(dir_path):
        for f in sorted(files):
            if f.lower().endswith(".flac"):
                flac_files.append(os.path.join(root, f))

    if not flac_files:
        return {"success": False, "error": f"No FLAC files found in: {dir_path}"}

    results = []
    passed = 0
    failed = 0
    unverified = 0

    for fpath in flac_files:
        res = verify_single_flac(fpath)
        results.append(res)
        if res.get("is_bit_perfect"):
            passed += 1
        elif res.get("status") in ("CORRUPTED_MISMATCH", "TRUNCATED_STREAM", "DECODE_ERROR"):
            failed += 1
        else:
            unverified += 1

    # Format ASCII Report Table
    report_lines = [
        "================================================================================",
        " FLAC Stream MD5 Integrity Audit Report",
        f" Directory: {os.path.basename(dir_path)}",
        "================================================================================",
        " Status        Format         Stored MD5                       Filename",
        "--------------------------------------------------------------------------------",
    ]

    for r in results:
        status_str = f"[{r.get('status', 'ERR')[:10]}]"
        if r.get("status") == "BIT_PERFECT_MATCH":
            status_tag = "✓ PASS      "
        elif r.get("status") == "NO_MD5_STORED":
            status_tag = "? NO_MD5    "
        else:
            status_tag = "✕ FAIL      "

        fmt_str = f"{r.get('bits_per_sample', 16)}b/{r.get('sample_rate', 44100)//1000}k"
        md5_snip = (r.get("stored_md5") or "--------------------------------")[:16] + "..."
        fn = r.get("filename", "unknown")
        report_lines.append(f" {status_tag} {fmt_str:<8} {md5_snip:<19} {fn}")

    report_lines.extend([
        "--------------------------------------------------------------------------------",
        f" Total Files: {len(flac_files)} | Passed: {passed} | Corrupted/Errors: {failed} | No MD5: {unverified}",
        f" Integrity Score: {round((passed / len(flac_files)) * 100, 1)}%",
        "================================================================================",
    ])
    report_text = "\n".join(report_lines)

    return {
        "success": True,
        "directory": dir_path,
        "total_files": len(flac_files),
        "passed_count": passed,
        "failed_count": failed,
        "unverified_count": unverified,
        "integrity_score": round((passed / len(flac_files)) * 100, 1),
        "results": results,
        "report_text": report_text,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python flac_verifier.py <flac_file_or_directory>")
        sys.exit(1)

    target = sys.argv[1]
    if os.path.isdir(target):
        res = verify_flac_directory(target)
        if res.get("success"):
            print(res["report_text"])
        else:
            print("Error:", res.get("error"))
    else:
        res = verify_single_flac(target)
        if res.get("success"):
            print(f"File:           {res['filename']}")
            print(f"Status:         {res['status']} ({'Bit-Perfect Lossless' if res.get('is_bit_perfect') else 'Integrity Check Failed'})")
            print(f"Stored MD5:     {res['stored_md5']}")
            print(f"Calculated MD5: {res.get('calculated_md5') or 'N/A'}")
            print(f"Resolution:     {res['bits_per_sample']}-bit / {res['sample_rate']} Hz ({res['channels']} ch)")
            print(f"Summary:        {res['message']}")
        else:
            print("Error:", res.get("error"))
