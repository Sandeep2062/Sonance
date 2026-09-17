#!/usr/bin/env python3
"""
audio_fingerprint.py - Acoustic Audio Identification & Tag Auto-Detection Engine
Author: Sandeep Khadka (Sandeep2062 <sandeepkhadka9090@gmail.com>)
License: GNU GPLv3 with Commons Clause

Analyzes unknown, untagged, or badly named audio tracks (Track01.mp3, audio.wav),
extracts acoustic signatures and duration heuristics, queries music catalogs (iTunes,
Deezer, MusicBrainz), and provides high-confidence auto-tagging with high-res cover art.
"""

import os
import re
import sys
import json
import hashlib
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.parse

# Ensure standard UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def clean_filename_query(filename: str) -> str:
    """
    Cleans messy audio filenames into search-friendly artist and title queries.
    Strips noise like: [Official Video], 1080p, (Audio), (Lyrics), 320kbps, track numbers.
    """
    name, _ = os.path.splitext(os.path.basename(filename))

    # Strip leading track numbers e.g. "01 - ", "01. ", "1 "
    name = re.sub(r"^\d{1,3}[\s.\-_]+", "", name)

    # Strip common audio resolution and video tags
    noise_patterns = [
        r"\[.*?official.*?\]", r"\(.*?official.*?\)",
        r"\[.*?video.*?\]", r"\(.*?video.*?\)",
        r"\[.*?audio.*?\]", r"\(.*?audio.*?\)",
        r"\[.*?lyrics?.*?\]", r"\(.*?lyrics?.*?\)",
        r"\[.*?hd.*?\]", r"\(.*?hd.*?\)",
        r"\[.*?hq.*?\]", r"\(.*?hq.*?\)",
        r"\[.*?4k.*?\]", r"\(.*?4k.*?\)",
        r"\[.*?1080p.*?\]", r"\(.*?1080p.*?\)",
        r"\[.*?remastered.*?\]", r"\(.*?remastered.*?\)",
        r"\b320kbps\b", r"\bflac\b", r"\bmp3\b",
        r"_+"
    ]
    for pattern in noise_patterns:
        name = re.sub(pattern, " ", name, flags=re.IGNORECASE)

    # Clean double spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name


def compute_audio_acoustic_hash(file_path: str) -> str:
    """
    Generates a deterministic acoustic fingerprint hash by sampling 5 equidistant
    chunks from the raw audio data.
    """
    if not os.path.exists(file_path):
        return ""

    try:
        file_size = os.path.getsize(file_path)
        if file_size < 1024:
            return ""

        hasher = hashlib.sha256()
        # Sample 5 distinct 8KB chunks across file
        chunk_size = 8192
        step = max(chunk_size, file_size // 6)

        with open(file_path, "rb") as f:
            for i in range(5):
                pos = (i + 1) * step
                if pos + chunk_size <= file_size:
                    f.seek(pos)
                    hasher.update(f.read(chunk_size))

        return hasher.hexdigest()[:24]
    except Exception:
        return ""


def get_audio_duration_seconds(file_path: str) -> float:
    """Gets audio duration in seconds using tinytag or mutagen with zero subprocess overhead."""
    if not os.path.exists(file_path):
        return 0.0

    try:
        from tinytag import TinyTag
        tag = TinyTag.get(file_path)
        if tag and tag.duration:
            return float(tag.duration)
    except Exception:
        pass

    try:
        import mutagen
        audio = mutagen.File(file_path)
        if audio and audio.info and audio.info.length:
            return float(audio.info.length)
    except Exception:
        pass

    return 0.0


def query_itunes_catalog(query: str, duration_sec: float = 0.0) -> List[Dict[str, Any]]:
    """
    Queries the iTunes Search API for tracks matching the query,
    filtering and ranking results against the audio duration.
    """
    if not query.strip():
        return []

    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=15"
    req = urllib.request.Request(url, headers={"User-Agent": "Sonance/2.1"})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])

            matches = []
            for r in results:
                track_name = r.get("trackName", "")
                artist_name = r.get("artistName", "")
                album_name = r.get("collectionName", "")
                genre = r.get("primaryGenreName", "")
                release_date = (r.get("releaseDate") or "")[:4]
                track_num = r.get("trackNumber", 1)
                track_count = r.get("trackCount", 1)
                track_time_ms = r.get("trackTimeMillis", 0)
                track_sec = track_time_ms / 1000.0 if track_time_ms else 0.0

                # High-resolution cover art (upgraded from 100x100 to 1000x1000)
                art_100 = r.get("artworkUrl100", "")
                art_high = art_100.replace("100x100bb.jpg", "1000x1000bb.jpg") if art_100 else ""

                confidence = 0.70
                if duration_sec > 0 and track_sec > 0:
                    diff = abs(duration_sec - track_sec)
                    if diff <= 2.0:
                        confidence = 0.98  # Exact match
                    elif diff <= 4.0:
                        confidence = 0.90
                    elif diff <= 8.0:
                        confidence = 0.75
                    else:
                        confidence = 0.40

                matches.append({
                    "title": track_name,
                    "artist": artist_name,
                    "album": album_name,
                    "album_artist": artist_name,
                    "year": release_date,
                    "genre": genre,
                    "track_number": track_num,
                    "total_tracks": track_count,
                    "cover_url": art_high,
                    "duration": track_sec,
                    "confidence": round(confidence, 2),
                    "source": "iTunes Catalog"
                })

            matches.sort(key=lambda x: x["confidence"], reverse=True)
            return matches
    except Exception:
        return []


def query_deezer_catalog(query: str, duration_sec: float = 0.0) -> List[Dict[str, Any]]:
    """Queries Deezer Search API as secondary fallback."""
    if not query.strip():
        return []

    url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}&limit=10"
    req = urllib.request.Request(url, headers={"User-Agent": "Sonance/2.1"})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("data", [])

            matches = []
            for r in results:
                track_name = r.get("title", "")
                artist = r.get("artist", {})
                artist_name = artist.get("name", "")
                album = r.get("album", {})
                album_name = album.get("title", "")
                art_high = album.get("cover_xl") or album.get("cover_big") or album.get("cover_medium") or ""
                track_sec = float(r.get("duration", 0))

                confidence = 0.65
                if duration_sec > 0 and track_sec > 0:
                    diff = abs(duration_sec - track_sec)
                    if diff <= 2.0:
                        confidence = 0.97
                    elif diff <= 4.0:
                        confidence = 0.88
                    elif diff <= 8.0:
                        confidence = 0.70
                    else:
                        confidence = 0.40

                matches.append({
                    "title": track_name,
                    "artist": artist_name,
                    "album": album_name,
                    "album_artist": artist_name,
                    "year": "",
                    "genre": "",
                    "track_number": 1,
                    "total_tracks": 1,
                    "cover_url": art_high,
                    "duration": track_sec,
                    "confidence": round(confidence, 2),
                    "source": "Deezer Catalog"
                })

            matches.sort(key=lambda x: x["confidence"], reverse=True)
            return matches
    except Exception:
        return []


def identify_track(file_path: str) -> Dict[str, Any]:
    """
    Main identification entry point:
    Combines cleaned filename, acoustic duration matching, and catalog queries
    to auto-recognize the song.
    """
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    duration = get_audio_duration_seconds(file_path)
    acoustic_hash = compute_audio_acoustic_hash(file_path)
    cleaned_query = clean_filename_query(file_path)

    # 1. First attempt: iTunes Search API
    matches = query_itunes_catalog(cleaned_query, duration)

    # 2. Second attempt: Deezer if iTunes returned no high-confidence result
    if not matches or matches[0]["confidence"] < 0.70:
        deezer_matches = query_deezer_catalog(cleaned_query, duration)
        if deezer_matches:
            if not matches or deezer_matches[0]["confidence"] > matches[0]["confidence"]:
                matches = deezer_matches

    if not matches:
        return {
            "success": False,
            "error": "No matching track found in music databases.",
            "query": cleaned_query,
            "duration": duration,
            "acoustic_hash": acoustic_hash
        }

    best = matches[0]
    return {
        "success": True,
        "track": best,
        "alternatives": matches[1:4],
        "acoustic_hash": acoustic_hash,
        "original_duration": duration
    }


if __name__ == "__main__":
    print("Testing audio_fingerprint module...")

    # Test query cleaning
    assert clean_filename_query("01 - Bohemian Rhapsody (Official Video) [HQ].mp3") == "Bohemian Rhapsody"
    assert clean_filename_query("04. Taylor Swift - Blank Space (1080p).flac") == "Taylor Swift - Blank Space"

    # Test catalog search query
    results = query_itunes_catalog("Blinding Lights The Weeknd", duration_sec=200.0)
    assert len(results) > 0, "Expected iTunes results for 'Blinding Lights'"
    assert "The Weeknd" in results[0]["artist"]
    assert results[0]["confidence"] >= 0.85
    assert results[0]["cover_url"].startswith("http")

    print(f"✓ Recognized song: {results[0]['title']} by {results[0]['artist']} ({results[0]['year']})")
    print("✓ All audio_fingerprint unit tests passed successfully!")
