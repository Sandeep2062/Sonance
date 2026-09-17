"""
listening_stats.py - Sonance Listening Habits & 'Sonance Wrapped' Studio

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Maintains 100% private local listening history and computes Wrapped statistics:
total hours, top artists, favorite tracks, audio quality breakdown (% Lossless vs 320k),
and listening streaks.
"""

import json
import os
import time
from collections import Counter
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional


APP_DIR = Path(__file__).parent.resolve()
HISTORY_FILE = APP_DIR / "listening_history.json"


def _load_history() -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_history(history: List[Dict[str, Any]]):
    try:
        # Keep last 5000 plays to avoid bloated json
        trimmed = history[-5000:]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, indent=2)
    except Exception:
        pass


def record_playback_event(
    title: str,
    artist: str,
    album: str = "",
    duration: float = 0.0,
    format_name: str = "MP3",
    quality: str = "320 kbps",
    is_stream: bool = False
) -> Dict[str, Any]:
    """Records a completed or significant track listen into local history."""
    if not title or not artist:
        return {"success": False, "error": "Missing title or artist"}

    history = _load_history()
    event = {
        "title": title.strip(),
        "artist": artist.strip(),
        "album": (album or "").strip(),
        "duration": round(float(duration or 0), 1),
        "format": (format_name or "MP3").upper(),
        "quality": quality or "Standard",
        "is_stream": bool(is_stream),
        "timestamp": int(time.time()),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    history.append(event)
    _save_history(history)
    return {"success": True, "total_events": len(history)}


def get_listening_stats() -> Dict[str, Any]:
    """
    Computes complete 'Sonance Wrapped' listening stats from local history.
    """
    history = _load_history()
    total_plays = len(history)

    if total_plays == 0:
        return {
            "success": True,
            "total_plays": 0,
            "total_minutes": 0,
            "total_hours": 0.0,
            "top_artists": [],
            "top_tracks": [],
            "format_breakdown": {
                "lossless": 0,
                "high_res": 0,
                "mp3_320": 0,
                "streaming": 0,
            },
            "active_days": 0,
            "current_streak": 0,
            "first_played": "",
            "last_played": "",
        }

    total_seconds = sum(t.get("duration", 180) for t in history)
    total_minutes = round(total_seconds / 60)
    total_hours = round(total_seconds / 3600, 1)

    # Top Artists
    artist_counter = Counter(t["artist"] for t in history if t.get("artist"))
    top_artists = [
        {"artist": artist, "plays": count}
        for artist, count in artist_counter.most_common(5)
    ]

    # Top Tracks
    track_counter = Counter(f"{t['artist']} — {t['title']}" for t in history if t.get("title"))
    top_tracks = [
        {"track": track, "plays": count}
        for track, count in track_counter.most_common(10)
    ]

    # Quality Breakdown
    lossless_count = 0
    mp3_320_count = 0
    stream_count = 0
    other_count = 0

    for t in history:
        fmt = (t.get("format") or "").upper()
        is_str = t.get("is_stream", False)
        if is_str:
            stream_count += 1
        elif fmt in ("FLAC", "WAV", "ALAC"):
            lossless_count += 1
        elif "320" in str(t.get("quality", "")) or fmt == "MP3":
            mp3_320_count += 1
        else:
            other_count += 1

    lossless_pct = round((lossless_count / total_plays) * 100)
    mp3_pct = round((mp3_320_count / total_plays) * 100)
    stream_pct = round((stream_count / total_plays) * 100)
    other_pct = max(0, 100 - (lossless_pct + mp3_pct + stream_pct))

    # Active Days & Streaks
    dates = sorted(set(t.get("date") for t in history if t.get("date")))
    active_days = len(dates)

    # Calculate streak ending today or yesterday
    streak = 0
    if dates:
        today = date.today()
        # Parse sorted dates
        parsed_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
        check_date = today
        if parsed_dates[-1] < today:
            check_date = parsed_dates[-1]

        for d in reversed(parsed_dates):
            if d == check_date:
                streak += 1
                check_date = date.fromordinal(check_date.toordinal() - 1)
            elif d < check_date:
                break

    return {
        "success": True,
        "total_plays": total_plays,
        "total_minutes": total_minutes,
        "total_hours": total_hours,
        "top_artists": top_artists,
        "top_tracks": top_tracks,
        "format_breakdown": {
            "lossless": lossless_pct,
            "mp3_320": mp3_pct,
            "streaming": stream_pct,
            "other": other_pct,
        },
        "active_days": active_days,
        "current_streak": streak,
        "first_played": dates[0] if dates else "",
        "last_played": dates[-1] if dates else "",
    }


def clear_listening_history() -> Dict[str, Any]:
    """Resets local listening history."""
    try:
        if HISTORY_FILE.exists():
            os.remove(HISTORY_FILE)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
