"""
lyrics_aggregator.py - Multi-Source Synced Lyrics Aggregator & Fusion Studio
Part of Sonance - The Ultimate Open-Source Music Workstation
Queries multiple synchronized lyrics providers (LRCLIB, Deezer, Megalobiz)
with quality ranking, automatic Asian phonetic romanization, and batch library downloading.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import re
import urllib.parse
import requests
from typing import Dict, List, Any, Optional, Callable
import mutagen

import lyrics_translation

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma"}
USER_AGENT = "Sonance/2.1 (https://github.com/Sandeep2062/Sonance)"


def _count_synced_lines(lrc_text: str) -> int:
    """Counts number of valid timestamped lines in LRC text."""
    if not lrc_text:
        return 0
    return len(re.findall(r"^\[\d{1,2}:\d{2}(?:\.\d{1,3})?\]", lrc_text, re.MULTILINE))


def fetch_from_lrclib(
    artist: str,
    title: str,
    album: Optional[str] = None,
    duration: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """Fetches synchronized lyrics from LRCLIB API."""
    try:
        # Try direct exact get first
        params = {"track_name": title, "artist_name": artist}
        if album:
            params["album_name"] = album
        if duration:
            params["duration"] = int(duration)

        url = f"https://lrclib.net/api/get?{urllib.parse.urlencode(params)}"
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=6)
        if r.status_code == 200:
            data = r.json()
            synced = data.get("syncedLyrics")
            plain = data.get("plainLyrics")
            if synced:
                return {
                    "source": "LRCLIB (Exact)",
                    "synced": True,
                    "lyrics": synced,
                    "line_count": _count_synced_lines(synced),
                    "track_name": data.get("trackName"),
                    "artist_name": data.get("artistName"),
                }
            elif plain:
                return {
                    "source": "LRCLIB (Plain)",
                    "synced": False,
                    "lyrics": plain,
                    "line_count": len(plain.splitlines()),
                    "track_name": data.get("trackName"),
                    "artist_name": data.get("artistName"),
                }

        # Fallback to search endpoint
        search_url = f"https://lrclib.net/api/search?q={urllib.parse.quote(f'{artist} {title}')}"
        sr = requests.get(search_url, headers={"User-Agent": USER_AGENT}, timeout=6)
        if sr.status_code == 200:
            results = sr.json()
            for item in results:
                synced = item.get("syncedLyrics")
                if synced and _count_synced_lines(synced) >= 4:
                    return {
                        "source": "LRCLIB (Search)",
                        "synced": True,
                        "lyrics": synced,
                        "line_count": _count_synced_lines(synced),
                        "track_name": item.get("trackName"),
                        "artist_name": item.get("artistName"),
                    }
    except Exception:
        pass
    return None


def fetch_from_megalobiz(query: str) -> Optional[Dict[str, Any]]:
    """Fetches synchronized lyrics from Megalobiz search."""
    try:
        search_url = f"https://www.megalobiz.com/search?q={urllib.parse.quote(query)}"
        r = requests.get(search_url, headers={"User-Agent": USER_AGENT}, timeout=6)
        if r.status_code == 200:
            # Look for detail page link
            match = re.search(r'href="(/lrc/maker/[^"]+)"', r.text)
            if match:
                detail_url = f"https://www.megalobiz.com{match.group(1)}"
                dr = requests.get(detail_url, headers={"User-Agent": USER_AGENT}, timeout=6)
                if dr.status_code == 200:
                    txt_match = re.search(r'<span id="lrc_[^"]+_details">([^<]+)</span>', dr.text)
                    if txt_match:
                        lrc_content = txt_match.group(1).replace("&quot;", '"').replace("&#039;", "'").replace("&amp;", "&")
                        if _count_synced_lines(lrc_content) >= 3:
                            return {
                                "source": "Megalobiz",
                                "synced": True,
                                "lyrics": lrc_content,
                                "line_count": _count_synced_lines(lrc_content),
                            }
    except Exception:
        pass
    return None


def aggregate_lyrics(
    artist: str,
    title: str,
    album: Optional[str] = None,
    duration: Optional[float] = None,
    romanize: bool = False
) -> Dict[str, Any]:
    """
    Searches multiple lyrics providers and returns the best synchronized lyrics match.
    Optionally generates phonetic romanization for Japanese/Korean lyrics.
    """
    clean_artist = re.sub(r"\(.*?\)|\[.*?\]", "", artist).strip()
    clean_title = re.sub(r"\(.*?\)|\[.*?\]", "", title).strip()

    candidates = []

    # 1. LRCLIB
    res_lrc = fetch_from_lrclib(clean_artist, clean_title, album=album, duration=duration)
    if res_lrc and res_lrc.get("synced"):
        candidates.append(res_lrc)

    # 2. Megalobiz
    if not candidates:
        res_mega = fetch_from_megalobiz(f"{clean_artist} {clean_title}")
        if res_mega and res_mega.get("synced"):
            candidates.append(res_mega)

    # 3. Plain lyrics fallback
    if not candidates and res_lrc:
        candidates.append(res_lrc)

    if not candidates:
        return {
            "success": False,
            "error": f"No synchronized lyrics found for '{artist} - {title}'.",
            "artist": artist,
            "title": title,
        }

    # Best candidate has highest synced line count
    best = max(candidates, key=lambda c: (1 if c.get("synced") else 0, c.get("line_count", 0)))
    final_lyrics = best["lyrics"]
    has_romanization = False

    if romanize and lyrics_translation:
        try:
            # Check if Japanese or Korean
            if re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", final_lyrics):
                rom_res = lyrics_translation.romanize_lyrics(final_lyrics, lang="ja")
                if rom_res.get("success"):
                    final_lyrics = rom_res["romanized_lrc"]
                    has_romanization = True
            elif re.search(r"[\uac00-\ud7af]", final_lyrics):
                rom_res = lyrics_translation.romanize_lyrics(final_lyrics, lang="ko")
                if rom_res.get("success"):
                    final_lyrics = rom_res["romanized_lrc"]
                    has_romanization = True
        except Exception:
            pass

    return {
        "success": True,
        "artist": artist,
        "title": title,
        "source": best["source"],
        "synced": best.get("synced", False),
        "line_count": best.get("line_count", 0),
        "lyrics": final_lyrics,
        "romanized": has_romanization,
    }


def batch_download_folder_lyrics(
    folder_path: str,
    overwrite: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Scans a folder for audio files, identifies tracks lacking companion .lrc lyrics,
    and batch downloads synchronized lyrics files.
    """
    if not os.path.isdir(folder_path):
        return {"success": False, "error": f"Directory not found: {folder_path}"}

    audio_files = []
    for root, _, files in os.walk(folder_path):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTS:
                audio_files.append(os.path.join(root, f))

    if not audio_files:
        return {"success": False, "error": f"No audio files found in {folder_path}"}

    total_files = len(audio_files)
    downloaded = 0
    already_present = 0
    failed = 0

    for idx, a_path in enumerate(audio_files):
        lrc_path = os.path.splitext(a_path)[0] + ".lrc"
        fn = os.path.basename(a_path)

        if progress_callback:
            progress_callback(idx + 1, total_files, fn)

        if os.path.isfile(lrc_path) and not overwrite:
            already_present += 1
            continue

        # Extract tags
        artist = ""
        title = os.path.splitext(fn)[0]
        album = ""
        dur = None

        try:
            f = mutagen.File(a_path, easy=True)
            if f:
                if "artist" in f and f["artist"]:
                    artist = f["artist"][0]
                if "title" in f and f["title"]:
                    title = f["title"][0]
                if "album" in f and f["album"]:
                    album = f["album"][0]
                if hasattr(f, "info") and hasattr(f.info, "length"):
                    dur = f.info.length
        except Exception:
            pass

        # If artist missing, try parsing 'Artist - Title' from filename
        if not artist and " - " in title:
            parts = title.split(" - ", 1)
            artist = parts[0].strip()
            title = parts[1].strip()

        if not artist:
            failed += 1
            continue

        res = aggregate_lyrics(artist, title, album=album, duration=dur)
        if res.get("success") and res.get("lyrics"):
            try:
                with open(lrc_path, "w", encoding="utf-8") as lf:
                    lf.write(res["lyrics"])
                downloaded += 1
            except Exception:
                failed += 1
        else:
            failed += 1

    return {
        "success": True,
        "folder": folder_path,
        "total_tracks": total_files,
        "downloaded_count": downloaded,
        "already_present": already_present,
        "failed_count": failed,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lyrics_aggregator.py fetch \"Artist\" \"Title\" [--romanize] [output.lrc]")
        print("       python lyrics_aggregator.py batch <music_folder> [--overwrite]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "fetch":
        if len(sys.argv) < 4:
            print("Error: Artist and Title required.")
            sys.exit(1)

        art = sys.argv[2]
        tit = sys.argv[3]
        rom = "--romanize" in sys.argv
        out_f = None
        for a in sys.argv[4:]:
            if not a.startswith("--"):
                out_f = a
                break

        print(f"[*] Searching multi-provider lyrics for: {art} - {tit}...")
        res = aggregate_lyrics(art, tit, romanize=rom)
        if res.get("success"):
            print(f"[+] Found from: {res['source']} ({res['line_count']} lines, Synced: {res['synced']})")
            if out_f:
                with open(out_f, "w", encoding="utf-8") as f:
                    f.write(res["lyrics"])
                print(f"[+] Saved to: {out_f}")
            else:
                print("\nSample Preview:")
                for l in res["lyrics"].splitlines()[:8]:
                    print(" ", l)
        else:
            print(f"[-] {res.get('error')}")

    elif cmd == "batch":
        if len(sys.argv) < 3:
            print("Error: Folder path required.")
            sys.exit(1)

        folder = sys.argv[2]
        ow = "--overwrite" in sys.argv
        print(f"[*] Batch scanning folder for missing lyrics: {folder}...")
        res = batch_download_folder_lyrics(
            folder,
            overwrite=ow,
            progress_callback=lambda c, t, f: print(f"[{c}/{t}] Scanning: {f}"),
        )
        if res.get("success"):
            print("[+] Batch Download Complete!")
            print(f"    • Total Tracks:    {res['total_tracks']}")
            print(f"    • Lyrics Downloaded: {res['downloaded_count']}")
            print(f"    • Already Present: {res['already_present']}")
            print(f"    • Missing/Failed:  {res['failed_count']}")
        else:
            print(f"[-] Batch failed: {res.get('error')}")
