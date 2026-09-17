"""
auto_dj.py - Sonance Intelligent Auto-DJ & Infinite Radio Engine

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Continuously discovers and enqueues acoustically matching music based on
the user's listening queue, Last.fm scrobble intelligence, and the Deezer catalog.
"""

import urllib.parse
from typing import List, Dict, Any, Set
import requests
import scrobbler


class AutoDJEngine:
    def __init__(self):
        self._played_history: Set[str] = set()
        self._max_history = 200

    def _track_key(self, artist: str, title: str) -> str:
        return f"{artist.strip().lower()} - {title.strip().lower()}"

    def mark_played(self, artist: str, title: str):
        """Marks a track as played to prevent repeat recommendations."""
        key = self._track_key(artist, title)
        self._played_history.add(key)
        if len(self._played_history) > self._max_history:
            # Pop older items
            self._played_history.pop()

    def get_recommendations(self, artist: str, title: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Discovers matching tracks for the given seed artist and title.
        Uses Last.fm similar tracks and queries Deezer catalog for full metadata.
        """
        if not artist and not title:
            return []

        self.mark_played(artist, title)
        results: List[Dict[str, Any]] = []
        seed_candidates = []

        # 1. Try Last.fm Similar Tracks
        try:
            similar_tracks = scrobbler.lastfm_client.get_similar_tracks(artist, title)
            for st in similar_tracks:
                st_artist = st.get("artist", "")
                st_title = st.get("title", "")
                if st_artist and st_title:
                    key = self._track_key(st_artist, st_title)
                    if key not in self._played_history:
                        seed_candidates.append((st_artist, st_title))
        except Exception:
            pass

        # 2. Query Deezer catalog for each candidate to get stream preview & artwork
        for cand_artist, cand_title in seed_candidates[:count + 3]:
            try:
                q = f'{cand_artist} {cand_title}'
                url = f"https://api.deezer.com/search?q={urllib.parse.quote(q)}&limit=1"
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    if data:
                        item = data[0]
                        res_artist = item.get("artist", {}).get("name", cand_artist)
                        res_title = item.get("title", cand_title)
                        key = self._track_key(res_artist, res_title)

                        if key not in self._played_history:
                            self._played_history.add(key)
                            results.append({
                                "id": f"autodj_{item.get('id', len(results))}",
                                "title": res_title,
                                "artist": res_artist,
                                "album": item.get("album", {}).get("title", "Auto-DJ Radio"),
                                "duration": item.get("duration", 210),
                                "cover_url": item.get("album", {}).get("cover_medium") or item.get("album", {}).get("cover_big", ""),
                                "stream_url": item.get("preview", ""),
                                "quality": "Preview 128k" if item.get("preview") else "Online",
                                "format": "MP3",
                                "source": "Auto-DJ Radio",
                                "is_auto_dj": True,
                            })
                            if len(results) >= count:
                                break
            except Exception:
                continue

        # 3. Fallback to direct Deezer artist radio search if Last.fm returned few results
        if len(results) < count:
            try:
                url = f"https://api.deezer.com/search?q={urllib.parse.quote(artist)}&limit={count + 5}"
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    for item in data:
                        res_artist = item.get("artist", {}).get("name", artist)
                        res_title = item.get("title", "")
                        key = self._track_key(res_artist, res_title)

                        if key not in self._played_history and res_title:
                            self._played_history.add(key)
                            results.append({
                                "id": f"autodj_{item.get('id', len(results))}",
                                "title": res_title,
                                "artist": res_artist,
                                "album": item.get("album", {}).get("title", "Auto-DJ Radio"),
                                "duration": item.get("duration", 210),
                                "cover_url": item.get("album", {}).get("cover_medium") or item.get("album", {}).get("cover_big", ""),
                                "stream_url": item.get("preview", ""),
                                "quality": "Preview 128k" if item.get("preview") else "Online",
                                "format": "MP3",
                                "source": "Auto-DJ Radio",
                                "is_auto_dj": True,
                            })
                            if len(results) >= count:
                                break
            except Exception:
                pass

        return results


# Global Singleton
auto_dj_engine = AutoDJEngine()
