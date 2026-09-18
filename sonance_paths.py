"""
sonance_paths.py - Sonance Persistent User Data & Storage Path Manager
======================================================================
Ensures user data, configurations, playlists, cookies, and cache are
safely isolated in the operating system's persistent user profile.

Guarantees zero data loss across app upgrades, installer overwrites,
and multi-version side-by-side installations.
"""

import os
import sys
import shutil
from pathlib import Path

# Application Directory (where the app binary/scripts are installed)
APP_DIR = Path(__file__).parent.resolve()


def is_portable_mode() -> bool:
    """Returns True if the application is running in portable mode."""
    return (APP_DIR / "PORTABLE").exists() or (APP_DIR / "portable.txt").exists()


def get_user_data_dir() -> Path:
    """
    Returns the persistent application data directory for the current user.
    - Windows: %APPDATA%/Sonance (e.g. C:/Users/<User>/AppData/Roaming/Sonance)
    - macOS: ~/Library/Application Support/Sonance
    - Linux: ~/.config/sonance (or $XDG_CONFIG_HOME/sonance)
    """
    if is_portable_mode():
        return APP_DIR

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    data_dir = base / "Sonance"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_path() -> Path:
    """Returns path to the persistent GUI configuration JSON."""
    persistent = get_user_data_dir() / "lyrics_gui_config.json"
    legacy = APP_DIR / "lyrics_gui_config.json"
    # Auto-migrate legacy configuration if it exists and persistent does not
    if not persistent.exists() and legacy.exists():
        try:
            shutil.copy2(legacy, persistent)
        except Exception:
            pass
    return persistent


def get_secrets_path() -> Path:
    """Returns path to the persistent user secrets and auth JSON."""
    persistent = get_user_data_dir() / "user_secrets.json"
    legacy = APP_DIR / "user_secrets.json"
    if not persistent.exists() and legacy.exists():
        try:
            shutil.copy2(legacy, persistent)
        except Exception:
            pass
    return persistent


def get_cookies_dir() -> Path:
    """Returns directory for platform login cookies (YouTube, Deezer, Spotify)."""
    cookie_dir = get_user_data_dir() / "cookies"
    cookie_dir.mkdir(parents=True, exist_ok=True)
    legacy_cookie = APP_DIR / "cookies" / "youtube_cookies.txt"
    dest_cookie = cookie_dir / "youtube_cookies.txt"
    if not dest_cookie.exists() and legacy_cookie.exists():
        try:
            shutil.copy2(legacy_cookie, dest_cookie)
        except Exception:
            pass
    return cookie_dir


def get_cache_dir() -> Path:
    """Returns directory for local audio streaming cache."""
    cache_dir = get_user_data_dir() / "cache" / "audio"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_library_path() -> Path:
    """Returns path to the persistent user playlists and favorites database."""
    persistent = get_user_data_dir() / "user_library.json"
    legacy = APP_DIR / "user_library.json"
    if not persistent.exists() and legacy.exists():
        try:
            shutil.copy2(legacy, persistent)
        except Exception:
            pass
    return persistent


def get_scrobbler_config_path() -> Path:
    """Returns path to the Last.fm / ListenBrainz scrobbler credentials."""
    persistent = get_user_data_dir() / "scrobbler_config.json"
    legacy = APP_DIR / "scrobbler_config.json"
    if not persistent.exists() and legacy.exists():
        try:
            shutil.copy2(legacy, persistent)
        except Exception:
            pass
    return persistent


def get_default_download_dir() -> Path:
    """Returns user's default music download directory."""
    music_dir = Path.home() / "Music" / "Sonance"
    music_dir.mkdir(parents=True, exist_ok=True)
    return music_dir
