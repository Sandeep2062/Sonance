"""
scrobbler.py - Sonance Last.fm & ListenBrainz Scrobbling & Metadata Engine

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Supports:
- Last.fm API 2.0: Now Playing updates, Scrobbling, Artist Info & Bio, Similar Tracks
- ListenBrainz API: Open-source decentralized scrobbling (playing_now & single)
- MusicBrainz metadata integration
"""

import os
import time
import json
import hashlib
import threading
import urllib.parse
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
import sonance_paths

CONFIG_FILE = sonance_paths.get_scrobbler_config_path()
_LOCK = threading.Lock()

LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
LISTENBRAINZ_API_URL = "https://api.listenbrainz.org/1/submit-listens"
LISTENBRAINZ_VALIDATE_URL = "https://api.listenbrainz.org/1/validate-token"

# Default Sonance API Key for Last.fm (Public Client Key)
DEFAULT_LASTFM_API_KEY = "4a9f2c8d234f51e1948087e5498fa670"
DEFAULT_LASTFM_SECRET = "26440e5e32927d312e7cad35edd5fcd5"


def load_config() -> Dict[str, Any]:
    """Loads scrobbler configuration from disk."""
    with _LOCK:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "lastfm_enabled": False,
            "lastfm_api_key": DEFAULT_LASTFM_API_KEY,
            "lastfm_secret": DEFAULT_LASTFM_SECRET,
            "lastfm_session_key": "",
            "lastfm_username": "",
            "listenbrainz_enabled": False,
            "listenbrainz_token": "",
            "listenbrainz_username": "",
        }


def save_config(cfg: Dict[str, Any]):
    """Saves scrobbler configuration to disk."""
    with _LOCK:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass


# ------------------ Last.fm Client ------------------

class LastFmClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Sonance/4.0.0 (https://github.com/Sandeep2062/Sonance)"})

    def _generate_signature(self, params: Dict[str, Any], secret: str) -> str:
        """Generates MD5 api_sig required by Last.fm write APIs."""
        filtered = {k: v for k, v in params.items() if k not in ("format", "callback")}
        sorted_keys = sorted(filtered.keys())
        sig_str = "".join(f"{k}{filtered[k]}" for k in sorted_keys) + secret
        return hashlib.md5(sig_str.encode("utf-8")).hexdigest()

    def update_now_playing(self, artist: str, track: str, album: Optional[str] = None, duration: Optional[int] = None) -> bool:
        """Sends 'Now Playing' status to Last.fm profile."""
        cfg = load_config()
        if not cfg.get("lastfm_enabled"):
            return False

        sk = cfg.get("lastfm_session_key", "").strip()
        api_key = cfg.get("lastfm_api_key") or DEFAULT_LASTFM_API_KEY
        secret = cfg.get("lastfm_secret") or DEFAULT_LASTFM_SECRET

        if not sk:
            return False

        params = {
            "method": "track.updateNowPlaying",
            "artist": artist,
            "track": track,
            "api_key": api_key,
            "sk": sk,
        }
        if album:
            params["album"] = album
        if duration and duration > 0:
            params["duration"] = str(int(duration))

        params["api_sig"] = self._generate_signature(params, secret)
        params["format"] = "json"

        try:
            r = self.session.post(LASTFM_API_URL, data=params, timeout=8)
            res = r.json()
            return "nowplaying" in res
        except Exception:
            return False

    def scrobble(self, artist: str, track: str, timestamp: int, album: Optional[str] = None, duration: Optional[int] = None) -> bool:
        """Submits scrobble to Last.fm after track is played."""
        cfg = load_config()
        if not cfg.get("lastfm_enabled"):
            return False

        sk = cfg.get("lastfm_session_key", "").strip()
        api_key = cfg.get("lastfm_api_key") or DEFAULT_LASTFM_API_KEY
        secret = cfg.get("lastfm_secret") or DEFAULT_LASTFM_SECRET

        if not sk:
            return False

        params = {
            "method": "track.scrobble",
            "artist": artist,
            "track": track,
            "timestamp": str(int(timestamp)),
            "api_key": api_key,
            "sk": sk,
        }
        if album:
            params["album"] = album
        if duration and duration > 0:
            params["duration"] = str(int(duration))

        params["api_sig"] = self._generate_signature(params, secret)
        params["format"] = "json"

        try:
            r = self.session.post(LASTFM_API_URL, data=params, timeout=8)
            res = r.json()
            return "scrobbles" in res
        except Exception:
            return False

    def _fetch_wikipedia_artist(self, artist: str) -> Dict[str, Any]:
        """Fetches artist bio and portrait thumbnail from Wikipedia REST API with disambiguation fallback."""
        clean_artist = re.sub(r"\s*[\(\[\{]?(?:feat\.?|ft\.?|prod\.?).*?[\)\]\}]?$", "", artist, flags=re.IGNORECASE).strip()
        if not clean_artist:
            clean_artist = artist.strip()

        ca_slug = clean_artist.replace(" ", "_")
        candidates = [
            ca_slug,
            f"{ca_slug}_(musician)",
            f"{ca_slug}_(rapper)",
            f"{ca_slug}_(singer)",
            f"{ca_slug}_(band)",
        ]
        headers = {"User-Agent": "SonanceMusicPlayer/1.0 (https://github.com/Sandeep2062/Sonance)"}

        for slug in candidates:
            try:
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(slug)}"
                r = self.session.get(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    extract = data.get("extract", "").strip()
                    if data.get("type") != "disambiguation" and extract and len(extract) > 40:
                        thumb = data.get("thumbnail", {}).get("source") or data.get("originalimage", {}).get("source")
                        return {
                            "bio": extract,
                            "image_url": thumb,
                            "title": data.get("title", clean_artist)
                        }
            except Exception:
                pass

        # If direct page lookup failed, search Wikipedia
        try:
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_artist + ' musician')}&utf8=&format=json"
            sr = self.session.get(search_url, headers=headers, timeout=5).json()
            items = sr.get("query", {}).get("search", [])
            if items:
                top_title = items[0].get("title", "")
                if top_title:
                    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(top_title.replace(' ', '_'))}"
                    r = self.session.get(url, headers=headers, timeout=5)
                    if r.status_code == 200:
                        data = r.json()
                        extract = data.get("extract", "").strip()
                        if extract:
                            thumb = data.get("thumbnail", {}).get("source") or data.get("originalimage", {}).get("source")
                            return {
                                "bio": extract,
                                "image_url": thumb,
                                "title": data.get("title", top_title)
                            }
        except Exception:
            pass

        return {}

    def _fetch_deezer_artist(self, artist: str) -> Dict[str, Any]:
        """Fetches artist details, fans count, image, and related artists from Deezer API."""
        clean_artist = re.sub(r"\s*[\(\[\{]?(?:feat\.?|ft\.?|prod\.?).*?[\)\]\}]?$", "", artist, flags=re.IGNORECASE).strip()
        if not clean_artist:
            clean_artist = artist.strip()

        res = {"image_url": None, "fans": 0, "similar_artists": []}
        headers = {"User-Agent": "SonanceMusicPlayer/1.0"}

        try:
            search_url = f"https://api.deezer.com/search/artist?q={urllib.parse.quote(clean_artist)}"
            r = self.session.get(search_url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    top = data[0]
                    res["image_url"] = top.get("picture_big") or top.get("picture_medium")
                    res["fans"] = int(top.get("nb_fan", 0))
                    artist_id = top.get("id")
                    if artist_id:
                        try:
                            rel_url = f"https://api.deezer.com/artist/{artist_id}/related"
                            rr = self.session.get(rel_url, headers=headers, timeout=5)
                            if rr.status_code == 200:
                                related_data = rr.json().get("data", [])
                                res["similar_artists"] = [a.get("name") for a in related_data[:8] if a.get("name")]
                        except Exception:
                            pass
        except Exception:
            pass

        return res

    def get_artist_info(self, artist: str) -> Dict[str, Any]:
        """Fetches artist bio, genres/tags, portrait image, and listener counts with Last.fm, Wikipedia & Deezer fallbacks."""
        cfg = load_config()
        api_key = cfg.get("lastfm_api_key") or DEFAULT_LASTFM_API_KEY

        params = {
            "method": "artist.getInfo",
            "artist": artist,
            "api_key": api_key,
            "format": "json",
            "autocorrect": "1",
        }
        name = artist
        bio = ""
        tags = []
        similar = []
        listeners = "0"
        playcount = "0"
        image_url = None

        try:
            r = self.session.get(LASTFM_API_URL, params=params, timeout=8)
            data = r.json().get("artist", {})
            name = data.get("name", artist)
            bio = data.get("bio", {}).get("summary", "")
            if "<a href=" in bio:
                bio = bio.split("<a href=")[0].strip()

            tags = [t.get("name") for t in data.get("tags", {}).get("tag", []) if isinstance(t, dict)]
            similar = [s.get("name") for s in data.get("similar", {}).get("artist", []) if isinstance(s, dict)]
            listeners = str(data.get("stats", {}).get("listeners", "0"))
            playcount = str(data.get("stats", {}).get("playcount", "0"))
        except Exception:
            pass

        # Multi-provider fallback: Wikipedia & Deezer
        deezer_info = self._fetch_deezer_artist(artist)
        if deezer_info.get("image_url"):
            image_url = deezer_info["image_url"]
        if deezer_info.get("fans") and (listeners == "0" or not listeners):
            listeners = str(deezer_info["fans"])
        if not similar and deezer_info.get("similar_artists"):
            similar = deezer_info["similar_artists"]

        if not bio or bio.lower().startswith("no biography") or len(bio) < 25:
            wiki_info = self._fetch_wikipedia_artist(artist)
            if wiki_info.get("bio"):
                bio = wiki_info["bio"]
            if not image_url and wiki_info.get("image_url"):
                image_url = wiki_info["image_url"]

        return {
            "name": name,
            "bio": bio or "No biography available.",
            "tags": tags[:8],
            "similar_artists": similar[:8],
            "listeners": listeners,
            "playcount": playcount,
            "image_url": image_url,
            "fans": deezer_info.get("fans", 0),
        }

    def get_similar_tracks(self, artist: str, track: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Gets recommended/similar tracks for the current song with Last.fm & Deezer fallback."""
        cfg = load_config()
        api_key = cfg.get("lastfm_api_key") or DEFAULT_LASTFM_API_KEY

        params = {
            "method": "track.getSimilar",
            "artist": artist,
            "track": track,
            "api_key": api_key,
            "format": "json",
            "autocorrect": "1",
            "limit": str(limit),
        }
        try:
            r = self.session.get(LASTFM_API_URL, params=params, timeout=8)
            tracks_data = r.json().get("similartracks", {}).get("track", [])
            if isinstance(tracks_data, dict):
                tracks_data = [tracks_data]

            results = []
            for t in tracks_data:
                results.append({
                    "title": t.get("name"),
                    "artist": t.get("artist", {}).get("name") if isinstance(t.get("artist"), dict) else str(t.get("artist")),
                    "match": float(t.get("match", 0.0)),
                    "duration": int(t.get("duration", 0)),
                })
            if results:
                return results
        except Exception:
            pass

        # Deezer search fallback for recommended tracks
        try:
            headers = {"User-Agent": "SonanceMusicPlayer/1.0"}
            q = f"{artist} {track}".strip()
            r = self.session.get(f"https://api.deezer.com/search?q={urllib.parse.quote(q)}", headers=headers, timeout=5)
            if r.status_code == 200:
                tracks = r.json().get("data", [])
                results = []
                for t in tracks[:limit]:
                    results.append({
                        "title": t.get("title", ""),
                        "artist": t.get("artist", {}).get("name", artist) if isinstance(t.get("artist"), dict) else str(t.get("artist")),
                        "match": 1.0,
                        "duration": int(t.get("duration", 0)),
                    })
                if results:
                    return results
        except Exception:
            pass

        return []

    def get_session_from_token(self, token: str) -> Dict[str, Any]:
        """Exchanges an authorized web token for a permanent session key."""
        cfg = load_config()
        api_key = cfg.get("lastfm_api_key") or DEFAULT_LASTFM_API_KEY
        secret = cfg.get("lastfm_secret") or DEFAULT_LASTFM_SECRET

        params = {
            "method": "auth.getSession",
            "api_key": api_key,
            "token": token,
        }
        params["api_sig"] = self._generate_signature(params, secret)
        params["format"] = "json"

        try:
            r = self.session.get(LASTFM_API_URL, params=params, timeout=8)
            res = r.json()
            session = res.get("session", {})
            sk = session.get("key")
            name = session.get("name")
            if sk:
                cfg["lastfm_session_key"] = sk
                cfg["lastfm_username"] = name or ""
                cfg["lastfm_enabled"] = True
                save_config(cfg)
                return {"success": True, "session_key": sk, "username": name}
            return {"success": False, "error": res.get("message", "Failed to get session")}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ------------------ ListenBrainz Client ------------------

class ListenBrainzClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Sonance/4.0.0 (https://github.com/Sandeep2062/Sonance)"})

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validates a ListenBrainz user token."""
        token = token.strip()
        if not token:
            return {"valid": False, "error": "Token is empty"}
        try:
            r = self.session.get(
                LISTENBRAINZ_VALIDATE_URL,
                headers={"Authorization": f"Token {token}"},
                timeout=8,
            )
            data = r.json()
            if data.get("valid"):
                return {"valid": True, "username": data.get("user_name", "")}
            return {"valid": False, "error": data.get("message", "Invalid token")}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def submit_listen(
        self,
        artist: str,
        track: str,
        album: Optional[str] = None,
        listen_type: str = "single",
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Submits listen to ListenBrainz.
        listen_type: 'playing_now' or 'single'
        """
        cfg = load_config()
        if not cfg.get("listenbrainz_enabled"):
            return False

        token = cfg.get("listenbrainz_token", "").strip()
        if not token:
            return False

        track_meta = {
            "artist_name": artist,
            "track_name": track,
        }
        if album:
            track_meta["release_name"] = album

        payload_item: Dict[str, Any] = {"track_metadata": track_meta}
        if listen_type == "single":
            payload_item["listened_at"] = int(timestamp or time.time())

        body = {
            "listen_type": listen_type,
            "payload": [payload_item],
        }

        try:
            r = self.session.post(
                LISTENBRAINZ_API_URL,
                headers={
                    "Authorization": f"Token {token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=8,
            )
            return r.status_code == 200
        except Exception:
            return False


# Global singleton clients
lastfm_client = LastFmClient()
listenbrainz_client = ListenBrainzClient()


# ------------------ Unified Dispatcher ------------------

def scrobble_now_playing(artist: str, track: str, album: Optional[str] = None, duration: Optional[int] = None):
    """Dispatches 'Now Playing' to all enabled scrobblers asynchronously."""
    def _run():
        lastfm_client.update_now_playing(artist, track, album, duration)
        listenbrainz_client.submit_listen(artist, track, album, listen_type="playing_now")

    threading.Thread(target=_run, daemon=True).start()


def scrobble_track(artist: str, track: str, album: Optional[str] = None, duration: Optional[int] = None, timestamp: Optional[int] = None):
    """Dispatches track listen scrobble to all enabled scrobblers asynchronously."""
    ts = timestamp or int(time.time())

    def _run():
        lastfm_client.scrobble(artist, track, timestamp=ts, album=album, duration=duration)
        listenbrainz_client.submit_listen(artist, track, album, listen_type="single", timestamp=ts)

    threading.Thread(target=_run, daemon=True).start()
