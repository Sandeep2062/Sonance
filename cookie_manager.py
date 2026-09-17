"""
cookie_manager.py - Sonance Browser Login & Cookie Extraction Engine

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Supports:
- YouTube & YouTube Music (bypasses bot check, age gate, unlocks 256k HQ audio)
- Deezer (auto-captures ARL cookie without DevTools inspection)
- Spotify (auto-captures sp_dc session cookie for web API & personal library)
- SoundCloud (auto-captures oauth_token)
- 1-Click extraction from installed desktop browsers (Chrome, Edge, Firefox, Brave, Opera)
"""

import os
import sys
import time
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
import webview

import yt_dlp.cookies
import downloader_engine

APP_DIR = Path(__file__).parent.resolve()
COOKIES_DIR = APP_DIR / "cookies"
COOKIES_DIR.mkdir(parents=True, exist_ok=True)

YOUTUBE_COOKIE_FILE = str(COOKIES_DIR / "youtube_cookies.txt")
SECRETS_FILE = APP_DIR / "user_secrets.json"

PLATFORM_URLS = {
    "youtube": "https://accounts.google.com/ServiceLogin?service=youtube",
    "deezer": "https://www.deezer.com/login",
    "spotify": "https://accounts.spotify.com/login",
    "soundcloud": "https://soundcloud.com/signin",
}


# ------------------ Netscape Cookies File Formatter ------------------

def save_netscape_cookies(cookies: List[Any], target_file: str):
    """
    Writes cookies into standard Netscape format compatible with yt-dlp, curl, and requests.
    """
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# Generated automatically by Sonance\n\n")

        for c in cookies:
            try:
                # Support both dict and http.cookies.Morsel
                if hasattr(c, "key") and hasattr(c, "value"):
                    name = c.key
                    value = c.value
                    domain = c.get("domain", "") or ".youtube.com"
                    path = c.get("path", "/") or "/"
                    secure = "TRUE" if c.get("secure") else "FALSE"
                    expires = c.get("expires", "")
                    expires_ts = str(int(time.time() + 30 * 86400))
                elif isinstance(c, dict):
                    name = c.get("name") or c.get("key")
                    value = c.get("value")
                    domain = c.get("domain", "") or ".youtube.com"
                    path = c.get("path", "/") or "/"
                    secure = "TRUE" if c.get("secure") else "FALSE"
                    expires_ts = str(c.get("expires") or int(time.time() + 30 * 86400))
                else:
                    continue

                if not name or not value:
                    continue

                include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
                f.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires_ts}\t{name}\t{value}\n")
            except Exception:
                continue


# ------------------ Status Checker ------------------

def get_cookie_status() -> Dict[str, Any]:
    """Returns the authentication and cookie status for all supported platforms."""
    auth_cfg = downloader_engine.load_auth_config()

    has_yt_cookies = os.path.exists(YOUTUBE_COOKIE_FILE) and os.path.getsize(YOUTUBE_COOKIE_FILE) > 100
    has_deezer_arl = bool(auth_cfg.get("deezer_arl", "").strip())
    has_spotify_sp_dc = bool(auth_cfg.get("spotify_sp_dc", "").strip())
    has_qobuz = bool(auth_cfg.get("qobuz_token", "").strip())
    has_soundcloud = bool(auth_cfg.get("soundcloud_token", "").strip())

    return {
        "youtube": {
            "active": has_yt_cookies,
            "badge": "Cookies Active" if has_yt_cookies else "Not Logged In",
            "file": YOUTUBE_COOKIE_FILE if has_yt_cookies else None,
        },
        "deezer": {
            "active": has_deezer_arl,
            "badge": "ARL Active" if has_deezer_arl else "Not Logged In",
        },
        "spotify": {
            "active": has_spotify_sp_dc or bool(auth_cfg.get("spotify_client_id")),
            "badge": "Session Active" if has_spotify_sp_dc else ("API Configured" if auth_cfg.get("spotify_client_id") else "Not Logged In"),
        },
        "qobuz": {
            "active": has_qobuz,
            "badge": "Token Active" if has_qobuz else "Not Logged In",
        },
        "soundcloud": {
            "active": has_soundcloud,
            "badge": "Token Active" if has_soundcloud else "Not Logged In",
        },
    }


# ------------------ Interactive Browser Window Login ------------------

def open_browser_login(platform: str, on_complete: Optional[Any] = None):
    """
    Opens an embedded WebView window directly to the platform login page.
    When user logs in, automatically captures cookies and updates configuration.
    """
    target_url = PLATFORM_URLS.get(platform.lower())
    if not target_url:
        return {"success": False, "error": f"Unsupported platform: {platform}"}

    def _login_thread():
        cookies_captured = []

        login_win = webview.create_window(
            title=f"Sonance - Log in to {platform.capitalize()}",
            url=target_url,
            width=900,
            height=700,
        )

        def on_closed():
            nonlocal cookies_captured
            try:
                cookies = login_win.get_cookies()
                if cookies:
                    cookies_captured = list(cookies)
                    _process_extracted_cookies(platform, cookies_captured)
            except Exception:
                pass

        login_win.events.closed += on_closed

    threading.Thread(target=_login_thread, daemon=True).start()
    return {"success": True, "message": f"Login window opened for {platform}."}


def _process_extracted_cookies(platform: str, cookies: List[Any]):
    """Processes cookies extracted from WebView session."""
    auth_cfg = downloader_engine.load_auth_config()

    if platform.lower() == "youtube":
        save_netscape_cookies(cookies, YOUTUBE_COOKIE_FILE)

    elif platform.lower() == "deezer":
        for c in cookies:
            name = getattr(c, "key", None) or (c.get("name") if isinstance(c, dict) else None)
            val = getattr(c, "value", None) or (c.get("value") if isinstance(c, dict) else None)
            if name == "arl" and val:
                auth_cfg["deezer_arl"] = val
                downloader_engine.save_auth_config(auth_cfg)
                break

    elif platform.lower() == "spotify":
        for c in cookies:
            name = getattr(c, "key", None) or (c.get("name") if isinstance(c, dict) else None)
            val = getattr(c, "value", None) or (c.get("value") if isinstance(c, dict) else None)
            if name == "sp_dc" and val:
                auth_cfg["spotify_sp_dc"] = val
                downloader_engine.save_auth_config(auth_cfg)
                break

    elif platform.lower() == "soundcloud":
        for c in cookies:
            name = getattr(c, "key", None) or (c.get("name") if isinstance(c, dict) else None)
            val = getattr(c, "value", None) or (c.get("value") if isinstance(c, dict) else None)
            if name == "oauth_token" and val:
                auth_cfg["soundcloud_token"] = val
                downloader_engine.save_auth_config(auth_cfg)
                break


# ------------------ 1-Click Desktop Browser Extraction ------------------

def extract_cookies_from_browser(browser_name: str = "chrome") -> Dict[str, Any]:
    """
    Extracts cookies directly from installed desktop browsers (chrome, edge, firefox, brave, opera).
    """
    browser_name = browser_name.lower().strip()
    try:
        # Extract YouTube cookies via yt-dlp browser cookie jar
        jar = yt_dlp.cookies.extract_cookies_from_browser(browser_name)
        if jar:
            # Write to Netscape file
            jar.save(YOUTUBE_COOKIE_FILE, ignore_discard=True, ignore_expires=True)

            # Inspect for Deezer ARL and Spotify sp_dc
            auth_cfg = downloader_engine.load_auth_config()
            found_items = ["YouTube"]

            for cookie in jar:
                if "deezer.com" in cookie.domain and cookie.name == "arl":
                    auth_cfg["deezer_arl"] = cookie.value
                    found_items.append("Deezer ARL")
                elif "spotify.com" in cookie.domain and cookie.name == "sp_dc":
                    auth_cfg["spotify_sp_dc"] = cookie.value
                    found_items.append("Spotify sp_dc")

            downloader_engine.save_auth_config(auth_cfg)
            return {
                "success": True,
                "browser": browser_name,
                "extracted": found_items,
                "message": f"Successfully extracted {', '.join(found_items)} from {browser_name.capitalize()}!",
            }
    except Exception as e:
        return {
            "success": False,
            "browser": browser_name,
            "error": str(e),
            "message": f"Could not extract cookies from {browser_name.capitalize()}: {e}",
        }

    return {"success": False, "message": f"No cookies found in {browser_name.capitalize()}."}
