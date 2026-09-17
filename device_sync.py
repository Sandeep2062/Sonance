"""
device_sync.py - Portable DAP, Walkman & USB Flash Device Synchronizer
Part of Sonance - The Ultimate Open-Source Music Workstation
Synchronizes playlists & music collections to DAPs, Walkmans, and USB storage with
automatic on-the-fly transcoding, companion .lrc lyrics migration, and M3U8 generation.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import shutil
import subprocess
import re
from typing import List, Dict, Any, Optional, Callable
import mutagen

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma"}

# Reserved characters in FAT32, exFAT, and NTFS
ILLEGAL_CHARS_REGEX = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_dap_path_segment(segment: str) -> str:
    """Sanitizes a directory or file name segment for FAT32 / exFAT portable device storage."""
    clean = ILLEGAL_CHARS_REGEX.sub("-", segment)
    clean = clean.strip(". ")
    return clean if clean else "Unknown"


def detect_portable_drives() -> List[Dict[str, Any]]:
    """
    Detects mounted portable USB storage, SD cards, and Digital Audio Players (DAPs)
    such as Sony Walkman, FiiO, Shanling, Astell&Kern, and HiBy.
    """
    devices = []

    # Windows detection using kernel32
    if sys.platform == "win32":
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    drive_path = f"{letter}:\\"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    # 2 = DRIVE_REMOVABLE, 3 = DRIVE_FIXED, 4 = DRIVE_REMOTE
                    if drive_type in (2, 3):
                        vol_name = ctypes.create_unicode_buffer(261)
                        fs_name = ctypes.create_unicode_buffer(261)
                        ctypes.windll.kernel32.GetVolumeInformationW(
                            drive_path, vol_name, 261, None, None, None, fs_name, 261
                        )
                        label = vol_name.value or ("Removable Disk" if drive_type == 2 else "Local Disk")
                        fs = fs_name.value or "FAT32"

                        # Retrieve disk usage
                        try:
                            usage = shutil.disk_usage(drive_path)
                            free_gb = round(usage.free / (1024 ** 3), 2)
                            total_gb = round(usage.total / (1024 ** 3), 2)
                        except Exception:
                            free_gb = 0.0
                            total_gb = 0.0

                        is_removable = (drive_type == 2)
                        devices.append({
                            "letter": letter,
                            "path": drive_path,
                            "label": label,
                            "filesystem": fs,
                            "is_removable": is_removable,
                            "free_gb": free_gb,
                            "total_gb": total_gb,
                            "display_name": f"[{letter}:] {label} ({free_gb} GB free / {total_gb} GB)",
                        })
                bitmask >>= 1
        except Exception:
            pass

    # Linux / macOS fallback mounts
    else:
        mount_dirs = ["/media", "/run/media", "/Volumes"]
        for base in mount_dirs:
            if os.path.exists(base):
                try:
                    for entry in os.scandir(base):
                        if entry.is_dir():
                            path = entry.path
                            try:
                                usage = shutil.disk_usage(path)
                                free_gb = round(usage.free / (1024 ** 3), 2)
                                total_gb = round(usage.total / (1024 ** 3), 2)
                            except Exception:
                                free_gb = 0.0
                                total_gb = 0.0

                            devices.append({
                                "letter": os.path.basename(path),
                                "path": path,
                                "label": os.path.basename(path),
                                "filesystem": "exFAT/EXT",
                                "is_removable": True,
                                "free_gb": free_gb,
                                "total_gb": total_gb,
                                "display_name": f"{os.path.basename(path)} ({free_gb} GB free / {total_gb} GB)",
                            })
                except Exception:
                    pass

    return devices


def _extract_track_tags(audio_path: str) -> Dict[str, str]:
    """Reads artist, album, title, year, track number from metadata."""
    artist = "Unknown Artist"
    album = "Unknown Album"
    title = os.path.splitext(os.path.basename(audio_path))[0]
    track_no = "01"

    try:
        f = mutagen.File(audio_path, easy=True)
        if f:
            if "artist" in f and f["artist"]:
                artist = f["artist"][0]
            if "album" in f and f["album"]:
                album = f["album"][0]
            if "title" in f and f["title"]:
                title = f["title"][0]
            if "tracknumber" in f and f["tracknumber"]:
                tn = str(f["tracknumber"][0]).split("/")[0]
                if tn.isdigit():
                    track_no = f"{int(tn):02d}"
    except Exception:
        pass

    return {
        "artist": artist,
        "album": album,
        "title": title,
        "track_no": track_no,
    }


def _transcode_or_copy(
    src_path: str,
    dst_path: str,
    transcode_mode: str = "copy",
    bitrate: str = "320k"
) -> bool:
    """Copies or transcodes an audio file to the destination."""
    src_ext = os.path.splitext(src_path)[1].lower()
    dst_dir = os.path.dirname(dst_path)
    os.makedirs(dst_dir, exist_ok=True)

    # 1. Direct copy
    if transcode_mode == "copy" or (transcode_mode.startswith("mp3") and src_ext == ".mp3"):
        shutil.copy2(src_path, dst_path)
        return True

    # 2. FFmpeg transcode
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-v", "error",
        "-i", src_path,
        "-map_metadata", "0",
    ]

    if transcode_mode.startswith("mp3"):
        cmd.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
    elif transcode_mode.startswith("aac") or transcode_mode.startswith("m4a"):
        cmd.extend(["-c:a", "aac", "-b:a", bitrate])
    else:
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k"])

    cmd.append(dst_path)

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(dst_path):
            return True
        else:
            # Fallback to direct copy if transcode fails
            shutil.copy2(src_path, dst_path)
            return True
    except Exception:
        shutil.copy2(src_path, dst_path)
        return True


def sync_tracks_to_device(
    track_paths: List[str],
    target_root: str,
    playlist_name: Optional[str] = "Sonance Sync",
    transcode_mode: str = "copy",
    bitrate: str = "320k",
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Synchronizes a list of audio tracks to a target portable device storage directory.
    - Preserves/organizes by Artist/Album/Track.
    - Copies companion .lrc synced lyrics files.
    - Generates a relative-path .m3u8 playlist file.
    """
    if not os.path.exists(target_root):
        try:
            os.makedirs(target_root, exist_ok=True)
        except Exception as e:
            return {"success": False, "error": f"Cannot create target directory: {e}"}

    music_dir = os.path.join(target_root, "Music")
    playlists_dir = os.path.join(target_root, "Playlists")
    os.makedirs(music_dir, exist_ok=True)
    os.makedirs(playlists_dir, exist_ok=True)

    total_tracks = len(track_paths)
    synced_files = []
    playlist_entries = []
    lyrics_copied = 0
    errors = []

    for idx, src_path in enumerate(track_paths):
        if not os.path.isfile(src_path):
            continue

        filename = os.path.basename(src_path)
        if progress_callback:
            progress_callback(idx + 1, total_tracks, filename)

        tags = _extract_track_tags(src_path)
        safe_artist = sanitize_dap_path_segment(tags["artist"])
        safe_album = sanitize_dap_path_segment(tags["album"])
        safe_title = sanitize_dap_path_segment(tags["title"])
        track_no = tags["track_no"]

        # Determine target extension
        src_ext = os.path.splitext(src_path)[1].lower()
        if transcode_mode.startswith("mp3"):
            dst_ext = ".mp3"
        elif transcode_mode.startswith("aac") or transcode_mode.startswith("m4a"):
            dst_ext = ".m4a"
        else:
            dst_ext = src_ext

        dst_filename = f"{track_no} - {safe_title}{dst_ext}"
        dst_rel_path = os.path.join("Music", safe_artist, safe_album, dst_filename)
        dst_abs_path = os.path.join(target_root, dst_rel_path)

        # Transcode or copy audio
        try:
            ok = _transcode_or_copy(src_path, dst_abs_path, transcode_mode=transcode_mode, bitrate=bitrate)
            if ok:
                synced_files.append(dst_abs_path)
                # Playlist entry relative to Playlists/ folder: ../Music/Artist/Album/Track.ext
                m3u_entry = f"../Music/{safe_artist}/{safe_album}/{dst_filename}".replace("\\", "/")
                playlist_entries.append(m3u_entry)

                # Check companion .lrc
                src_lrc = os.path.splitext(src_path)[0] + ".lrc"
                if os.path.isfile(src_lrc):
                    dst_lrc = os.path.splitext(dst_abs_path)[0] + ".lrc"
                    try:
                        shutil.copy2(src_lrc, dst_lrc)
                        lyrics_copied += 1
                    except Exception:
                        pass
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    # Generate M3U8 Playlist
    playlist_file = None
    if playlist_name and playlist_entries:
        safe_pl_name = sanitize_dap_path_segment(playlist_name)
        playlist_file = os.path.join(playlists_dir, f"{safe_pl_name}.m3u8")
        try:
            with open(playlist_file, "w", encoding="utf-8") as pf:
                pf.write("#EXTM3U\n")
                for entry in playlist_entries:
                    pf.write(f"{entry}\n")
        except Exception as e:
            errors.append(f"Failed to write playlist: {e}")

    return {
        "success": True,
        "target_root": target_root,
        "total_requested": total_tracks,
        "total_synced": len(synced_files),
        "lyrics_copied": lyrics_copied,
        "transcode_mode": transcode_mode,
        "playlist_file": playlist_file,
        "errors": errors,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python device_sync.py list")
        print("       python device_sync.py sync <target_dir> <source_dir_or_file> [--mode copy|mp3_320] [--playlist <name>]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "list":
        devs = detect_portable_drives()
        print("Detected Portable & Local Storage Devices:")
        for d in devs:
            print(f"  {d['display_name']} [{d['filesystem']}] (Removable: {d['is_removable']})")
    elif cmd == "sync":
        if len(sys.argv) < 4:
            print("Error: Target directory and source directory are required.")
            sys.exit(1)

        target = sys.argv[2]
        source = sys.argv[3]
        mode = "copy"
        pl_name = "Sonance Sync"

        idx = 4
        while idx < len(sys.argv):
            if sys.argv[idx] == "--mode" and idx + 1 < len(sys.argv):
                mode = sys.argv[idx + 1]
                idx += 2
            elif sys.argv[idx] == "--playlist" and idx + 1 < len(sys.argv):
                pl_name = sys.argv[idx + 1]
                idx += 2
            else:
                idx += 1

        tracks_to_sync = []
        if os.path.isdir(source):
            for root, _, files in os.walk(source):
                for f in sorted(files):
                    if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                        tracks_to_sync.append(os.path.join(root, f))
        elif os.path.isfile(source):
            tracks_to_sync.append(source)

        print(f"Syncing {len(tracks_to_sync)} tracks to {target} (Mode: {mode})...")
        res = sync_tracks_to_device(
            tracks_to_sync,
            target,
            playlist_name=pl_name,
            transcode_mode=mode,
            progress_callback=lambda c, t, f: print(f"[{c}/{t}] Syncing: {f}"),
        )
        print("Sync Complete!")
        print(f"  Synced: {res['total_synced']}/{res['total_requested']} tracks")
        print(f"  Lyrics Synced: {res['lyrics_copied']}")
        if res.get("playlist_file"):
            print(f"  Playlist Created: {res['playlist_file']}")
