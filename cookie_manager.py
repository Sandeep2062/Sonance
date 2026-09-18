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
try:
    import webview
except ImportError:
    webview = None

import yt_dlp.cookies
import downloader_engine
import sonance_paths

from http.cookies import BaseCookie, SimpleCookie, Morsel

APP_DIR = Path(__file__).parent.resolve()
COOKIES_DIR = sonance_paths.get_cookies_dir()
YOUTUBE_COOKIE_FILE = str(COOKIES_DIR / "youtube_cookies.txt")
SECRETS_FILE = sonance_paths.get_secrets_path()

PLATFORM_URLS = {
    "youtube": "https://accounts.google.com/ServiceLogin?service=youtube",
    "deezer": "https://www.deezer.com/login",
    "spotify": "https://accounts.spotify.com/login",
    "soundcloud": "https://soundcloud.com/signin",
}

ACTIVE_LOGIN_WINDOWS: Dict[str, Any] = {}


# ------------------ Cookie Normalizer & Netscape Formatter ------------------

def extract_cookie_dicts(cookies: List[Any]) -> List[Dict[str, Any]]:
    """
    Normalizes cookies from pywebview (SimpleCookie, Morsel, or dict) into a unified dictionary format.
    """
    results: List[Dict[str, Any]] = []
    if not cookies:
        return results

    for item in cookies:
        try:
            if isinstance(item, (BaseCookie, SimpleCookie)):
                for key, morsel in item.items():
                    dom = morsel.get("domain", "") or ".youtube.com"
                    path = morsel.get("path", "/") or "/"
                    results.append({
                        "name": key,
                        "value": morsel.value,
                        "domain": dom,
                        "path": path,
                        "secure": bool(morsel.get("secure")),
                        "expires": morsel.get("expires", ""),
                    })
            elif isinstance(item, Morsel):
                dom = item.get("domain", "") or ".youtube.com"
                path = item.get("path", "/") or "/"
                results.append({
                    "name": item.key,
                    "value": item.value,
                    "domain": dom,
                    "path": path,
                    "secure": bool(item.get("secure")),
                    "expires": item.get("expires", ""),
                })
            elif isinstance(item, dict):
                name = item.get("name") or item.get("key")
                val = item.get("value")
                if name and val is not None:
                    results.append({
                        "name": name,
                        "value": val,
                        "domain": item.get("domain", "") or ".youtube.com",
                        "path": item.get("path", "/") or "/",
                        "secure": bool(item.get("secure")),
                        "expires": item.get("expires", ""),
                    })
        except Exception:
            continue

    return results


def save_netscape_cookies(cookies: List[Any], target_file: str):
    """
    Writes cookies into standard Netscape format compatible with yt-dlp, curl, and requests.
    """
    cookie_dicts = extract_cookie_dicts(cookies)
    Path(target_file).parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# Generated automatically by Sonance\n\n")

        for c in cookie_dicts:
            name = c.get("name")
            value = c.get("value")
            if not name or not value:
                continue

            domain = c.get("domain", "") or ".youtube.com"
            if not domain.startswith(".") and not domain.startswith("http"):
                domain = "." + domain
            path = c.get("path", "/") or "/"
            secure = "TRUE" if c.get("secure") else "FALSE"
            expires_ts = str(int(time.time() + 60 * 86400))  # 60 days default
            include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"

            f.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires_ts}\t{name}\t{value}\n")


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


# ------------------ Cookie Processor ------------------

def _process_extracted_cookies(platform: str, cookies: List[Any]) -> bool:
    """
    Processes and saves normalized cookies. Returns True if authentication credentials were found.
    """
    cookie_dicts = extract_cookie_dicts(cookies)
    if not cookie_dicts:
        return False

    auth_cfg = downloader_engine.load_auth_config()
    plat = platform.lower()
    saved_auth = False

    if plat == "youtube":
        save_netscape_cookies(cookies, YOUTUBE_COOKIE_FILE)
        # Check if user session cookies are present
        has_auth = any(
            c.get("name") in ("LOGIN_INFO", "SID", "SSID", "SAPISID", "APISID", "__Secure-3PSID", "__Secure-1PSID")
            for c in cookie_dicts
        )
        if has_auth or len(cookie_dicts) >= 3:
            saved_auth = True

    elif plat == "deezer":
        for c in cookie_dicts:
            if c.get("name") == "arl" and c.get("value"):
                auth_cfg["deezer_arl"] = c["value"]
                downloader_engine.save_auth_config(auth_cfg)
                saved_auth = True
                break

    elif plat == "spotify":
        for c in cookie_dicts:
            if c.get("name") == "sp_dc" and c.get("value"):
                auth_cfg["spotify_sp_dc"] = c["value"]
                downloader_engine.save_auth_config(auth_cfg)
                saved_auth = True
                break

    elif plat == "soundcloud":
        for c in cookie_dicts:
            if c.get("name") == "oauth_token" and c.get("value"):
                auth_cfg["soundcloud_token"] = c["value"]
                downloader_engine.save_auth_config(auth_cfg)
                saved_auth = True
                break

    return saved_auth


# ------------------ Interactive Browser Window Login ------------------

def open_browser_login(platform: str, on_complete: Optional[Any] = None) -> Dict[str, Any]:
    """
    Opens an embedded WebView window directly to the platform login page.
    Actively monitors cookies in real-time and auto-saves as soon as login is detected.
    Also captures cookies before window closing.
    """
    if webview is None:
        return {
            "success": False,
            "error": "pywebview is not installed. You can extract cookies directly from your browser using: python sonance.py --extract-cookies chrome",
        }

    plat = platform.lower()
    target_url = PLATFORM_URLS.get(plat)
    if not target_url:
        return {"success": False, "error": f"Unsupported platform: {platform}"}

    def _login_thread():
        login_win = webview.create_window(
            title=f"Sonance - Log in to {platform.capitalize()}",
            url=target_url,
            width=920,
            height=720,
        )
        ACTIVE_LOGIN_WINDOWS[plat] = login_win

        stop_polling = threading.Event()

        def _poll_cookies():
            while not stop_polling.is_set():
                time.sleep(1.5)
                try:
                    raw = login_win.get_cookies()
                    if raw:
                        saved = _process_extracted_cookies(plat, list(raw))
                        if saved:
                            # Successful auto-detection!
                            stop_polling.set()
                            ACTIVE_LOGIN_WINDOWS.pop(plat, None)
                            time.sleep(0.5)
                            try:
                                login_win.destroy()
                            except Exception:
                                pass
                            if on_complete:
                                on_complete(plat, True)
                            break
                except Exception:
                    pass

        poller = threading.Thread(target=_poll_cookies, daemon=True)
        poller.start()

        def on_closing():
            stop_polling.set()
            try:
                raw = login_win.get_cookies()
                if raw:
                    _process_extracted_cookies(plat, list(raw))
            except Exception:
                pass
            ACTIVE_LOGIN_WINDOWS.pop(plat, None)

        def on_closed():
            stop_polling.set()
            ACTIVE_LOGIN_WINDOWS.pop(plat, None)

        try:
            login_win.events.closing += on_closing
        except Exception:
            pass
        try:
            login_win.events.closed += on_closed
        except Exception:
            pass

    threading.Thread(target=_login_thread, daemon=True).start()
    return {"success": True, "message": f"Login window opened for {platform.capitalize()}."}


def save_active_login_cookies(platform: str) -> Dict[str, Any]:
    """
    Manually captures and saves cookies from the active popup login window.
    """
    plat = platform.lower()
    win = ACTIVE_LOGIN_WINDOWS.get(plat)
    if not win:
        return {"success": False, "message": f"No active login window found for {platform.capitalize()}."}

    try:
        raw = win.get_cookies()
        if raw:
            saved = _process_extracted_cookies(plat, list(raw))
            if saved:
                try:
                    win.destroy()
                except Exception:
                    pass
                ACTIVE_LOGIN_WINDOWS.pop(plat, None)
                return {
                    "success": True,
                    "message": f"Successfully captured and saved {platform.capitalize()} session cookies!",
                }
            else:
                # Still try to write whatever cookies were captured
                if plat == "youtube":
                    save_netscape_cookies(list(raw), YOUTUBE_COOKIE_FILE)
                    try:
                        win.destroy()
                    except Exception:
                        pass
                    ACTIVE_LOGIN_WINDOWS.pop(plat, None)
                    return {
                        "success": True,
                        "message": "Cookies captured and saved to youtube_cookies.txt.",
                    }
    except Exception as e:
        return {"success": False, "message": f"Error capturing cookies: {e}"}

    return {
        "success": False,
        "message": f"No session cookies detected yet. Please ensure you are logged into {platform.capitalize()} first.",
    }


# ------------------ 1-Click Desktop Browser Extraction ------------------

def extract_cookies_from_browser(browser_name: str = "chrome") -> Dict[str, Any]:
    """
    Extracts cookies directly from installed desktop browsers (chrome, edge, firefox, brave, opera).
    """
    browser_name = browser_name.lower().strip()
    try:
        # Extract cookies via yt-dlp browser cookie jar
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
        err_msg = str(e)
        if "DPAPI" in err_msg or "v20" in err_msg:
            err_msg = (
                f"{browser_name.capitalize()} protects cookies with Windows App-Bound encryption. "
                "Please use the '🌐 Login via Window' button above to log in directly — Sonance will automatically capture your session!"
            )
        elif "could not find" in err_msg.lower() or "not found" in err_msg.lower():
            err_msg = f"{browser_name.capitalize()} profile was not found on this computer. Use '🌐 Login via Window' instead."

        return {
            "success": False,
            "browser": browser_name,
            "error": str(e),
            "message": f"Could not extract from {browser_name.capitalize()}: {err_msg}",
        }

    return {"success": False, "message": f"No cookies found in {browser_name.capitalize()}."}
