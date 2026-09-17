"""
cache_manager.py - Sonance Smart Audio Cache & Offline Mode Manager

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Caches online previews and downloaded streams locally for zero-latency replay and offline listening.
"""

import os
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

CACHE_DIR = Path(__file__).parent.resolve() / "cache" / "audio"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_filename(key: str, ext: str = ".mp3") -> Path:
    """Generates unique deterministic filename for cached track."""
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"cached_{h}{ext}"


def is_cached(key: str, ext: str = ".mp3") -> bool:
    """Checks if a track stream is cached locally."""
    target = _get_cache_filename(key, ext)
    return target.exists() and target.stat().st_size > 1024


def get_cached_path(key: str, ext: str = ".mp3") -> Optional[str]:
    """Returns local file path if cached, else None."""
    target = _get_cache_filename(key, ext)
    if target.exists() and target.stat().st_size > 1024:
        return str(target)
    return None


def save_to_cache(key: str, data: bytes, ext: str = ".mp3") -> str:
    """Saves raw audio bytes to cache and returns the path."""
    target = _get_cache_filename(key, ext)
    try:
        with open(target, "wb") as f:
            f.write(data)
        return str(target)
    except Exception:
        return ""


def get_cache_stats() -> Dict[str, Any]:
    """Calculates total cached files and total size in MB."""
    if not CACHE_DIR.exists():
        return {"total_files": 0, "size_mb": 0.0}

    total_bytes = 0
    count = 0
    for entry in CACHE_DIR.iterdir():
        if entry.is_file():
            total_bytes += entry.stat().st_size
            count += 1

    return {
        "total_files": count,
        "files_count": count,
        "size_mb": round(total_bytes / (1024 * 1024), 2),
        "dir": str(CACHE_DIR),
    }


def clear_cache() -> bool:
    """Clears all cached audio files."""
    try:
        if CACHE_DIR.exists():
            for item in CACHE_DIR.iterdir():
                if item.is_file():
                    item.unlink()
        return True
    except Exception:
        return False
