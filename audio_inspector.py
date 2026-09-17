"""
audio_inspector.py - Hi-Res Audio Stream Inspector & Bitstream Forensics
Part of Sonance - The Ultimate Open-Source Music Workstation
Performs deep structural container and bitstream forensics across FLAC, WAV,
MP3, AAC/M4A, OGG, and Opus. Extracts exact uncompressed PCM metrics, compression
ratios, LAME/FLAC/Apple encoder signatures, padding waste analysis, and technical specsheets.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import math
import struct
from typing import Dict, Any, Optional, List

try:
    import mutagen
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    from mutagen.oggopus import OggOpus
except ImportError:
    mutagen = None


def _inspect_flac_blocks(file_path: str) -> Dict[str, Any]:
    """Inspects native FLAC metadata blocks to measure padding, comments, and picture sizes."""
    blocks = []
    total_padding = 0
    total_metadata = 4  # 'fLaC' magic
    streaminfo = {}

    try:
        with open(file_path, "rb") as f:
            magic = f.read(4)
            if magic != b"fLaC":
                return {}

            is_last = False
            while not is_last:
                header = f.read(4)
                if len(header) < 4:
                    break
                total_metadata += 4
                byte0 = header[0]
                is_last = bool(byte0 & 0x80)
                block_type = byte0 & 0x7F
                length = (header[1] << 16) | (header[2] << 8) | header[3]
                total_metadata += length

                type_names = {
                    0: "STREAMINFO",
                    1: "PADDING",
                    2: "APPLICATION",
                    3: "SEEKTABLE",
                    4: "VORBIS_COMMENT",
                    5: "CUESHEET",
                    6: "PICTURE",
                }
                t_name = type_names.get(block_type, f"CUSTOM_{block_type}")

                if block_type == 1:
                    total_padding += length

                if block_type == 0 and length >= 34:
                    raw_si = f.read(length)
                    min_block, max_block, min_frame, max_frame = struct.unpack(">HHHH", raw_si[0:8])
                    b10_13 = struct.unpack(">I", raw_si[10:14])[0]
                    sample_rate = (raw_si[10] << 12) | (raw_si[11] << 4) | (raw_si[12] >> 4)
                    channels = ((raw_si[12] >> 1) & 0x07) + 1
                    bps = (((raw_si[12] & 0x01) << 4) | (raw_si[13] >> 4)) + 1
                    total_samples = ((raw_si[13] & 0x0F) << 32) | struct.unpack(">I", raw_si[14:18])[0]
                    md5_hex = raw_si[18:34].hex()

                    streaminfo = {
                        "min_block_size": min_block,
                        "max_block_size": max_block,
                        "min_frame_size": min_frame,
                        "max_frame_size": max_frame,
                        "sample_rate": sample_rate,
                        "channels": channels,
                        "bits_per_sample": bps,
                        "total_samples": total_samples,
                        "audio_md5": md5_hex,
                    }
                else:
                    f.seek(length, os.SEEK_CUR)

                blocks.append({"type": t_name, "length_bytes": length})

            audio_stream_offset = f.tell()
    except Exception:
        pass

    return {
        "blocks": blocks,
        "total_metadata_bytes": total_metadata,
        "total_padding_bytes": total_padding,
        "streaminfo": streaminfo,
    }


def _inspect_mp3_lame(file_path: str) -> Dict[str, Any]:
    """Scans for Xing, Info, or VBRI headers and extracts LAME encoder info."""
    info = {"encoder": "Unknown MP3 Encoder", "lame_version": None, "vbr_mode": "Unknown", "lowpass_hz": None}
    try:
        with open(file_path, "rb") as f:
            buf = f.read(8192)
            # Find Xing or Info header
            idx = buf.find(b"Xing")
            if idx == -1:
                idx = buf.find(b"Info")

            if idx != -1:
                # Xing/Info header found
                # Check for LAME string: usually 120 bytes after Xing or around offset + 0x78
                lame_idx = buf.find(b"LAME", idx)
                if lame_idx != -1 and lame_idx + 9 <= len(buf):
                    ver_raw = buf[lame_idx : lame_idx + 9].decode("latin1", errors="ignore")
                    info["lame_version"] = ver_raw.strip()
                    info["encoder"] = f"LAME MP3 ({info['lame_version']})"

                    # Extract revision & VBR method byte (lame_idx + 9)
                    if lame_idx + 10 <= len(buf):
                        vbr_byte = buf[lame_idx + 9] & 0x0F
                        vbr_types = {1: "CBR", 2: "ABR", 3: "VBR (Method 1)", 4: "VBR (Method 2)", 5: "VBR (Method 3)", 6: "VBR (Method 4)"}
                        info["vbr_mode"] = vbr_types.get(vbr_byte, "VBR")

                    # Extract lowpass filter frequency (lame_idx + 10) in 100 Hz units
                    if lame_idx + 11 <= len(buf):
                        lp_val = buf[lame_idx + 10]
                        if lp_val > 0:
                            info["lowpass_hz"] = lp_val * 100
            elif b"VBRI" in buf:
                info["encoder"] = "Fraunhofer IIS (VBRI)"
                info["vbr_mode"] = "VBR (VBRI)"
    except Exception:
        pass
    return info


def inspect_audio_stream(file_path: str) -> Dict[str, Any]:
    """
    Performs comprehensive structural bitstream inspection on an audio file.
    Returns technical forensics, compression ratios, and encoder details.
    """
    if not os.path.isfile(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    file_size = os.path.getsize(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    fn = os.path.basename(file_path)

    res = {
        "success": True,
        "filename": fn,
        "filepath": file_path,
        "format": ext.lstrip(".").upper(),
        "filesize_bytes": file_size,
        "filesize_mb": round(file_size / (1024 * 1024), 2),
        "duration_sec": 0.0,
        "sample_rate": 44100,
        "bits_per_sample": 16,
        "channels": 2,
        "channel_layout": "Stereo",
        "bitrate_kbps": 0,
        "bitrate_mode": "Constant",
        "encoder": "Standard Audio Encoder",
        "compression_ratio": 0.0,
        "space_saved_pct": 0.0,
        "uncompressed_pcm_bytes": 0,
        "padding_bytes": 0,
        "padding_overhead_pct": 0.0,
        "technical_summary": "",
        "audio_md5": None,
        "flac_blocks": [],
    }

    # 1. Inspect FLAC native blocks
    if ext == ".flac":
        flac_data = _inspect_flac_blocks(file_path)
        if flac_data and "streaminfo" in flac_data and flac_data["streaminfo"]:
            si = flac_data["streaminfo"]
            res["sample_rate"] = si.get("sample_rate", 44100)
            res["channels"] = si.get("channels", 2)
            res["bits_per_sample"] = si.get("bits_per_sample", 16)
            res["audio_md5"] = si.get("audio_md5")
            total_samples = si.get("total_samples", 0)
            if res["sample_rate"] > 0:
                res["duration_sec"] = round(total_samples / res["sample_rate"], 2)

            res["padding_bytes"] = flac_data.get("total_padding_bytes", 0)
            if file_size > 0:
                res["padding_overhead_pct"] = round((res["padding_bytes"] / file_size) * 100, 2)
            res["flac_blocks"] = flac_data.get("blocks", [])
            res["encoder"] = "Reference libFLAC"

    # 2. Inspect MP3 LAME headers
    elif ext in {".mp3"}:
        lame = _inspect_mp3_lame(file_path)
        if lame.get("lame_version"):
            res["encoder"] = lame["encoder"]
            res["bitrate_mode"] = lame.get("vbr_mode", "VBR")
            if lame.get("lowpass_hz"):
                res["lowpass_filter"] = f"{lame['lowpass_hz']} Hz"

    # 3. Use Mutagen if available for high-level metadata & audio info
    if mutagen:
        try:
            m = mutagen.File(file_path)
            if m and hasattr(m, "info") and m.info:
                if hasattr(m.info, "length") and m.info.length:
                    res["duration_sec"] = round(float(m.info.length), 2)
                if hasattr(m.info, "sample_rate") and m.info.sample_rate:
                    res["sample_rate"] = int(m.info.sample_rate)
                if hasattr(m.info, "channels") and m.info.channels:
                    res["channels"] = int(m.info.channels)
                if hasattr(m.info, "bits_per_sample") and m.info.bits_per_sample:
                    res["bits_per_sample"] = int(m.info.bits_per_sample)
                if hasattr(m.info, "bitrate") and m.info.bitrate:
                    res["bitrate_kbps"] = round(m.info.bitrate / 1000)

                # Channel layout name
                ch = res["channels"]
                if ch == 1:
                    res["channel_layout"] = "Mono"
                elif ch == 2:
                    res["channel_layout"] = "Stereo (2.0)"
                elif ch == 6:
                    res["channel_layout"] = "Surround (5.1)"
                elif ch == 8:
                    res["channel_layout"] = "Surround (7.1)"
                else:
                    res["channel_layout"] = f"{ch} Channels"

                # Check tags for encoder
                if m.tags:
                    for key in ["encoder", "tsse", "writing library", "encoded_by"]:
                        for k, v in m.tags.items():
                            if key in str(k).lower():
                                val_str = str(v[0] if isinstance(v, list) else v).strip()
                                if val_str:
                                    res["encoder"] = val_str
                                    break
        except Exception:
            pass

    # 4. Fallback for WAV using wave module if bit depth or duration missing
    if ext in {".wav", ".wave"} and (res["duration_sec"] == 0 or res["bits_per_sample"] == 16):
        try:
            import wave
            with wave.open(file_path, "rb") as wf:
                res["channels"] = wf.getnchannels()
                res["sample_rate"] = wf.getframerate()
                res["bits_per_sample"] = wf.getsampwidth() * 8
                n_frames = wf.getnframes()
                if res["sample_rate"] > 0:
                    res["duration_sec"] = round(n_frames / res["sample_rate"], 2)
                res["encoder"] = "Linear PCM (Uncompressed RIFF)"
        except Exception:
            pass

    # 5. Calculate uncompressed raw PCM stream size and compression ratio
    bytes_per_sample = math.ceil(res["bits_per_sample"] / 8)
    pcm_bytes = int(res["duration_sec"] * res["sample_rate"] * res["channels"] * bytes_per_sample)
    res["uncompressed_pcm_bytes"] = pcm_bytes

    if pcm_bytes > 0 and file_size > 0:
        ratio = round(pcm_bytes / file_size, 2)
        saved = round(((pcm_bytes - file_size) / pcm_bytes) * 100, 1)
        res["compression_ratio"] = ratio
        res["space_saved_pct"] = max(0.0, saved)

    # 6. Format technical summary
    sr_khz = res["sample_rate"] / 1000.0
    sr_str = f"{sr_khz:.1f} kHz" if (sr_khz != int(sr_khz)) else f"{int(sr_khz)} kHz"
    dur_min = int(res["duration_sec"] // 60)
    dur_sec = int(res["duration_sec"] % 60)

    res["formatted_duration"] = f"{dur_min:02d}:{dur_sec:02d}"
    res["audio_resolution"] = f"{res['bits_per_sample']}-bit / {sr_str} ({res['channel_layout']})"

    res["technical_summary"] = (
        f"{res['format']} | {res['audio_resolution']} | {res['bitrate_kbps']} kbps | "
        f"Saved: {res['space_saved_pct']}% vs Raw PCM | Encoder: {res['encoder']}"
    )

    return res


def format_inspection_card(info: Dict[str, Any]) -> str:
    """Formats inspection details into a clean ASCII report card."""
    if not info.get("success"):
        return f"[-] Stream Inspection Failed: {info.get('error')}"

    lines = [
        "+-------------------------------------------------------------------------------+",
        "|  [SONANCE HI-RES BITSTREAM & AUDIO CONTAINER INSPECTION]                      |",
        "+-------------------------------------------------------------------------------+",
        f"|  File:          {info['filename'][:56]:<60}|",
        f"|  Format:        {info['format']} Container ({info['filesize_mb']} MB)".ljust(79) + "|",
        f"|  Duration:      {info['formatted_duration']} ({info['duration_sec']}s)".ljust(79) + "|",
        f"|  Resolution:    {info['audio_resolution']:<60}|",
        f"|  Bitrate:       {info['bitrate_kbps']} kbps ({info['bitrate_mode']})".ljust(79) + "|",
        f"|  Encoder:       {info['encoder'][:56]:<60}|",
        "+-------------------------------------------------------------------------------+",
        f"|  Raw PCM Size:  {round(info['uncompressed_pcm_bytes'] / (1024 * 1024), 2)} MB (Uncompressed Benchmark)".ljust(79) + "|",
        f"|  Compression:   {info['compression_ratio']}:1 Ratio ({info['space_saved_pct']}% Savings vs Raw PCM)".ljust(79) + "|",
    ]

    if info.get("padding_bytes", 0) > 0:
        lines.append(f"|  Padding Waste: {info['padding_bytes']} bytes ({info['padding_overhead_pct']}% metadata overhead)".ljust(79) + "|")

    if info.get("audio_md5"):
        lines.append(f"|  FLAC Audio MD5:{info['audio_md5']:<60}|")

    lines.append("+-------------------------------------------------------------------------------+")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audio_inspector.py <audio_file>")
        sys.exit(1)

    target = sys.argv[1]
    res = inspect_audio_stream(target)
    print(format_inspection_card(res))
