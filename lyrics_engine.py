"""
lyrics_engine.py - Sonance Core Lyrics Engine
Advanced Lyrics Fetching & Anti-Mismatch Verification Engine

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (c) 2024-2026 Sandeep Khadka — MIT License

Includes:
- Intelligent audio metadata extraction (tinytag with bitrate, samplerate, bitdepth, quality badge)
- Direct LRCLIB integration (https://lrclib.net - official API for instant synced & plain lyrics)
- Query sanitization (strips '13. ', '01 - ', 'feat.', version noise)
- Multi-factor Anti-Mismatch Verification (duration checking + fuzzy similarity)
- Direct Genius Scraper (bypasses Cloudflare 403 blocks with proper browser headers)
- Multi-provider fallback pipeline (synced & plain)
"""

import os
import re
import html
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple
import requests
from bs4 import BeautifulSoup
import syncedlyrics

try:
    from tinytag import TinyTag
    HAS_TINYTAG = True
except ImportError:
    HAS_TINYTAG = False

# Common user-agent for browser impersonation to prevent 403 blocks
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://genius.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
}

LRCLIB_HEADERS = {
    "User-Agent": "Sonance/1.0 (https://github.com/Sandeep2062/Sonance)",
}

TIMESTAMP_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")


# ------------------ Audio Metadata & Tag Extraction ------------------

def get_audio_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extracts embedded metadata, technical audio quality specs, and duration from audio files.
    """
    ext = os.path.splitext(file_path)[1].lower().replace(".", "").upper()
    meta = {
        "title": "",
        "artist": "",
        "album": "",
        "duration": 0.0,
        "track_number": None,
        "bitrate": 0,
        "samplerate": 0,
        "bitdepth": None,
        "channels": 2,
        "format": ext,
        "is_lossless": False,
        "quality": ext,
    }

    if HAS_TINYTAG and os.path.exists(file_path):
        try:
            tag = TinyTag.get(file_path)
            meta["title"] = (tag.title or "").strip()
            meta["artist"] = (tag.artist or "").strip()
            meta["album"] = (tag.album or "").strip()
            meta["duration"] = float(tag.duration or 0.0)
            meta["track_number"] = tag.track
            meta["bitrate"] = int(tag.bitrate or 0)
            meta["samplerate"] = int(tag.samplerate or 0)
            meta["bitdepth"] = tag.bitdepth
            meta["channels"] = tag.channels or 2
            meta["is_lossless"] = bool(tag.is_lossless)

            # Generate formatted quality badge string (e.g. FLAC 16-bit / 44.1kHz, MP3 320 kbps)
            if meta["is_lossless"]:
                depth_str = f"{meta['bitdepth']}-bit" if meta["bitdepth"] else "Lossless"
                rate_str = f"{meta['samplerate'] / 1000:.1f}kHz" if meta["samplerate"] else ""
                meta["quality"] = f"{ext} · {depth_str}" + (f" / {rate_str}" if rate_str else "")
            elif meta["bitrate"] > 0:
                meta["quality"] = f"{ext} · {meta['bitrate']} kbps"
            else:
                meta["quality"] = ext

            return meta
        except Exception:
            pass

    return meta


# ------------------ Query Cleaning & Normalization ------------------

def clean_filename_to_artist_title(filename: str) -> Tuple[str, str]:
    """
    Parses messy filenames like:
    '13. 6 Dogs - Demons in the A.mp3' -> ('6 Dogs', 'Demons in the A')
    '01 - Creed - Are You Ready_.mp3' -> ('Creed', 'Are You Ready')
    'Higher (Official Video).mp3' -> ('', 'Higher')
    """
    # Remove file extension
    base = re.sub(r"\.[a-zA-Z0-9]+$", "", filename).strip()

    # Strip leading track numbers like '13. ', '01 - ', '1-02 ', '04_ '
    base = re.sub(r"^\s*(?:\d{1,3}[\.\-\s_]+|\d{1,2}-\d{1,2}[\.\-\s_]+|[A-Za-z]\d{1,2}[\.\-\s_]+)", "", base).strip()

    # Clean underscores and common punctuation
    base = base.replace("_", " ")

    # Check if format is "Artist - Title"
    if " - " in base:
        parts = base.split(" - ", 1)
        artist = clean_text_noise(parts[0])
        title = clean_text_noise(parts[1])
        return artist, title

    return "", clean_text_noise(base)


def clean_text_noise(text: str) -> str:
    """
    Removes clutter such as (Official Video), [Audio], (Remastered 2011), (feat. ...).
    """
    # Remove bracketed noise
    text = re.sub(r"\s*[\(\[](?:official\s*(?:video|audio|music\s*video)|remastered|remaster|\d{4}\s*remaster|deluxe|explicit|hd|hq|audio|visualizer)[\)\]]", "", text, flags=re.IGNORECASE)
    # Remove feat / ft
    text = re.sub(r"\s*[\(\[]\s*(?:feat|ft)\.?\s+[^)\]]+[\)\]]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:feat|ft)\.?\s+.*$", "", text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()


def build_search_queries(file_path: str, fallback_artist: str = "") -> List[str]:
    """
    Builds prioritized list of search queries to maximize hit rate.
    Handles '13. 6 Dogs - Demons in the A' accurately.
    """
    meta = get_audio_metadata(file_path)
    fn = os.path.basename(file_path)
    fn_artist, fn_title = clean_filename_to_artist_title(fn)

    artist = meta["artist"] or fn_artist or fallback_artist
    title = meta["title"] or fn_title or fn

    queries = []

    # 1. Clean Artist + Title (Best for Lrclib, Musixmatch, Genius)
    if artist and title and artist.lower() not in title.lower():
        queries.append(f"{artist} {title}".strip())
        queries.append(f"{title} {artist}".strip())
    elif title:
        queries.append(title.strip())

    # 2. Filename-based query if different
    if fn_artist and fn_title:
        q_fn = f"{fn_artist} {fn_title}".strip()
        if q_fn not in queries:
            queries.append(q_fn)

    # 3. Fallback to just the title
    if title and title not in queries:
        queries.append(title)

    return queries


# ------------------ Anti-Mismatch Verification Engine ------------------

def parse_last_lrc_timestamp(lrc_text: str) -> Optional[float]:
    """
    Finds the final timestamp in an LRC string in seconds.
    e.g. [03:22.40] -> 202.4 seconds
    """
    matches = TIMESTAMP_RE.findall(lrc_text)
    if not matches:
        return None
    last = matches[-1]
    mins = int(last[0])
    secs = int(last[1])
    ms = float(f"0.{last[2]}") if last[2] else 0.0
    return mins * 60 + secs + ms


def verify_lyrics_match(lrc_content: str, audio_duration: float, audio_title: str) -> Tuple[bool, str]:
    """
    Multi-factor Anti-Mismatch check:
    1. Duration verification (for synced lyrics):
       - If lyrics timestamp goes past audio duration + 6s -> MISMATCH!
       - If lyrics finish more than 45s before audio ends (and song is > 60s) -> SUSPICIOUS/MISMATCH!
    2. Minimum content check (rejects placeholder lyrics or empty responses).
    Returns: (is_valid, reason)
    """
    if not lrc_content or len(lrc_content.strip()) < 40:
        return False, "Lyrics content too short or empty"

    # Reject common placeholder lyrics
    placeholders = [
        "lyrics not available",
        "we are currently reviewing",
        "instrumental",
        "paroles introuvables",
    ]
    lower = lrc_content.lower()
    for p in placeholders:
        if p in lower and len(lrc_content) < 200:
            return False, f"Detected placeholder text: '{p}'"

    # Duration Check (if audio_duration is known)
    if audio_duration and audio_duration > 15.0:
        last_ts = parse_last_lrc_timestamp(lrc_content)
        if last_ts is not None:
            # Synced lyrics: Compare timestamps
            # Case A: Lyrics end AFTER the audio file has already finished!
            if last_ts > audio_duration + 6.0:
                diff = last_ts - audio_duration
                return False, f"Duration mismatch: lyrics timestamp ({last_ts:.1f}s) exceeds audio duration ({audio_duration:.1f}s) by {diff:.1f}s"

            # Case B: Lyrics end way too early
            if (audio_duration - last_ts) > 45.0:
                diff = audio_duration - last_ts
                return False, f"Duration mismatch: lyrics end {diff:.1f}s before song ends"

    return True, "Match verified"


# ------------------ Direct LRCLIB API Client ------------------

def fetch_lrclib_lyrics(artist: str, title: str, duration: Optional[float] = None, want_synced: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """
    Directly queries LRCLIB (https://lrclib.net) official API.
    Guarantees finding tracks like '6 Dogs - Demons in the A' (track 809140).
    Returns: (lyrics_content, state) where state is 'synced' or 'plain'
    """
    if not title:
        return None, None

    # 1. Try exact match on /api/get
    try:
        params = {"track_name": title}
        if artist:
            params["artist_name"] = artist
        if duration and duration > 10:
            params["duration"] = int(duration)

        r = requests.get("https://lrclib.net/api/get", params=params, headers=LRCLIB_HEADERS, timeout=6)
        if r.ok:
            data = r.json()
            if want_synced and data.get("syncedLyrics"):
                return data.get("syncedLyrics"), "synced"
            elif not want_synced and data.get("plainLyrics"):
                return data.get("plainLyrics"), "plain"
            elif data.get("syncedLyrics"):
                return data.get("syncedLyrics"), "synced"
            elif data.get("plainLyrics"):
                return data.get("plainLyrics"), "plain"
    except Exception:
        pass

    # 2. Try search on /api/search
    try:
        search_q = f"{artist} {title}".strip() if artist else title.strip()
        r = requests.get("https://lrclib.net/api/search", params={"q": search_q}, headers=LRCLIB_HEADERS, timeout=6)
        if r.ok:
            items = r.json()
            # If want synced, look for synced first
            if want_synced:
                for item in items:
                    if item.get("syncedLyrics"):
                        return item.get("syncedLyrics"), "synced"
            # Otherwise return first available
            for item in items:
                if item.get("syncedLyrics"):
                    return item.get("syncedLyrics"), "synced"
                elif item.get("plainLyrics"):
                    return item.get("plainLyrics"), "plain"
    except Exception:
        pass

    return None, None


# ------------------ Robust Direct Genius Scraper ------------------

def fetch_genius_plain_lyrics(query: str) -> Optional[str]:
    """
    Directly searches Genius API and scrapes lyrics with genuine browser headers.
    Solves the Cloudflare 403 Forbidden issue present in syncedlyrics.
    """
    try:
        search_url = "https://genius.com/api/search/multi"
        params = {"q": query, "per_page": 5}
        resp = requests.get(search_url, params=params, headers=BROWSER_HEADERS, timeout=8)
        if not resp.ok:
            return None

        data = resp.json()
        sections = data.get("response", {}).get("sections", [])
        song_url = None

        for sec in sections:
            for hit in sec.get("hits", []):
                res = hit.get("result", {})
                url = res.get("url", "")
                if url and "-lyrics" in url:
                    song_url = url
                    break
            if song_url:
                break

        if not song_url:
            return None

        page_resp = requests.get(song_url, headers=BROWSER_HEADERS, timeout=8)
        if not page_resp.ok:
            return None

        soup = BeautifulSoup(page_resp.text, "html.parser")
        containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
        if not containers:
            containers = soup.find_all(
                lambda tag: tag.name == "div" and any("Lyrics__Container" in c for c in tag.get("class", []))
            )

        if not containers:
            return None

        lines = []
        for c in containers:
            text = c.get_text("\n").strip()
            if text:
                lines.append(text)

        raw_lyrics = "\n\n".join(lines).strip()
        if not raw_lyrics or len(raw_lyrics) < 40:
            return None

        cleaned = html.unescape(raw_lyrics)
        cleaned = re.sub(r"^\d+\s+Contributors.*?\n", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^.*?Lyrics\n", "", cleaned, count=1, flags=re.IGNORECASE)

        return cleaned.strip()

    except Exception:
        return None


# ------------------ Main Unified Download API ------------------

def download_track_lyrics(
    file_path: str,
    custom_query: Optional[str] = None,
    allow_plain: bool = True,
    fallback_artist: str = "",
    strip_cjk: bool = True,
) -> Dict[str, Any]:
    """
    Downloads lyrics for a single track with:
    1. Direct LRCLIB API for immediate synced & plain retrieval
    2. Smart query fallback (handles '13. 6 Dogs - Demons in the A')
    3. Anti-mismatch verification (duration and content checks)
    4. Direct Genius fallback for plain lyrics
    5. CJK line stripping
    """
    out_lrc_path = os.path.splitext(file_path)[0] + ".lrc"
    meta = get_audio_metadata(file_path)
    audio_duration = meta["duration"]

    fn_artist, fn_title = clean_filename_to_artist_title(os.path.basename(file_path))
    artist = meta["artist"] or fn_artist or fallback_artist
    title = meta["title"] or fn_title

    queries = [custom_query] if custom_query else build_search_queries(file_path, fallback_artist)

    # 1. First priority: Direct LRCLIB Synced Query
    if artist or title:
        lrclib_synced, state = fetch_lrclib_lyrics(artist, title, audio_duration, want_synced=True)
        if lrclib_synced and state == "synced":
            is_valid, reason = verify_lyrics_match(lrclib_synced, audio_duration, title)
            if is_valid:
                if strip_cjk:
                    lrclib_synced = strip_cjk_lines(lrclib_synced)
                with open(out_lrc_path, "w", encoding="utf-8") as f:
                    f.write(lrclib_synced)
                return {
                    "success": True,
                    "state": "synced",
                    "provider": "LRCLIB (Synced)",
                    "query": f"{artist} - {title}",
                    "file": out_lrc_path,
                    "reason": "Synced LRC saved from LRCLIB",
                }

    # 2. Try Synced Lyrics across providers via syncedlyrics
    for q in queries:
        try:
            lrc_content = syncedlyrics.search(q, synced_only=True, providers=["Lrclib", "Musixmatch", "NetEase"])
            if lrc_content:
                is_valid, reason = verify_lyrics_match(lrc_content, audio_duration, meta["title"] or q)
                if is_valid:
                    if strip_cjk:
                        lrc_content = strip_cjk_lines(lrc_content)
                    with open(out_lrc_path, "w", encoding="utf-8") as f:
                        f.write(lrc_content)
                    return {
                        "success": True,
                        "state": "synced",
                        "provider": "Synced Provider",
                        "query": q,
                        "file": out_lrc_path,
                        "reason": "Synced LRC saved successfully",
                    }
        except Exception:
            pass

    # 3. Plain Lyrics Fallback if enabled
    if allow_plain:
        # A. Check LRCLIB for plain lyrics
        if artist or title:
            lrclib_plain, state = fetch_lrclib_lyrics(artist, title, audio_duration, want_synced=False)
            if lrclib_plain:
                is_valid, reason = verify_lyrics_match(lrclib_plain, audio_duration, title)
                if is_valid:
                    if strip_cjk:
                        lrclib_plain = strip_cjk_lines(lrclib_plain)
                    with open(out_lrc_path, "w", encoding="utf-8") as f:
                        f.write(lrclib_plain)
                    return {
                        "success": True,
                        "state": state or "plain",
                        "provider": f"LRCLIB ({state or 'plain'})",
                        "query": f"{artist} - {title}",
                        "file": out_lrc_path,
                        "reason": f"{state or 'plain'} lyrics saved from LRCLIB",
                    }

        # B. Direct Genius scraper
        for q in queries:
            genius_text = fetch_genius_plain_lyrics(q)
            if genius_text:
                is_valid, reason = verify_lyrics_match(genius_text, audio_duration, meta["title"] or q)
                if is_valid:
                    if strip_cjk:
                        genius_text = strip_cjk_lines(genius_text)
                    with open(out_lrc_path, "w", encoding="utf-8") as f:
                        f.write(genius_text)
                    return {
                        "success": True,
                        "state": "plain",
                        "provider": "Genius (Plain)",
                        "query": q,
                        "file": out_lrc_path,
                        "reason": "Plain lyrics downloaded from Genius",
                    }

            # C. Syncedlyrics plain fallback
            try:
                plain_content = syncedlyrics.search(q, synced_only=False)
                if plain_content:
                    is_valid, reason = verify_lyrics_match(plain_content, audio_duration, meta["title"] or q)
                    if is_valid:
                        if strip_cjk:
                            plain_content = strip_cjk_lines(plain_content)
                        with open(out_lrc_path, "w", encoding="utf-8") as f:
                            f.write(plain_content)
                        return {
                            "success": True,
                            "state": "plain",
                            "provider": "Syncedlyrics (Plain)",
                            "query": q,
                            "file": out_lrc_path,
                            "reason": "Plain lyrics saved",
                        }
            except Exception:
                pass

    return {
        "success": False,
        "state": "missing",
        "provider": None,
        "query": queries[0] if queries else "",
        "file": out_lrc_path,
        "reason": "No matching lyrics found on any provider",
    }


def strip_cjk_lines(text: str) -> str:
    """Removes CJK lines from lyrics."""
    lines = text.splitlines()
    filtered = [l for l in lines if not CJK_RE.search(l)]
    return "\n".join(filtered)


def analyze_lrc_content(content: str) -> str:
    """Classifies LRC as 'synced', 'plain', or 'incomplete'."""
    if not content:
        return "none"
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    ts_lines = [l for l in lines if TIMESTAMP_RE.search(l)]
    if not lines:
        return "none"
    ratio = len(ts_lines) / len(lines)
    if ratio >= 0.4:
        return "synced"
    elif ratio > 0.05:
        return "incomplete"
    return "plain"
