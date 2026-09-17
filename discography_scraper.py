#!/usr/bin/env python3
"""
discography_scraper.py - Artist Discography Enumerator & Full-Album Batch Downloader Engine
Author: Sandeep Khadka (Sandeep2062 <sandeepkhadka9090@gmail.com>)
License: GNU GPLv3 with Commons Clause

Queries public music databases (iTunes & Deezer APIs) to resolve complete artist discographies,
studio albums, EPs, and singles with full tracklists, cover art, and durations.
"""

import sys
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional

# Ensure standard UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def search_artist(artist_name: str) -> Optional[Dict[str, Any]]:
    """Searches for an artist by name on Deezer / iTunes and returns the best matching artist profile."""
    if not artist_name.strip():
        return None

    # Try Deezer first
    url = f"https://api.deezer.com/search/artist?q={urllib.parse.quote(artist_name)}&limit=5"
    req = urllib.request.Request(url, headers={"User-Agent": "Sonance/2.1"})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            artists = data.get("data", [])
            if artists:
                best = artists[0]
                return {
                    "id": str(best.get("id", "")),
                    "name": best.get("name", ""),
                    "picture": best.get("picture_xl") or best.get("picture_big") or best.get("picture_medium") or "",
                    "nb_album": best.get("nb_album", 0),
                    "nb_fan": best.get("nb_fan", 0),
                    "source": "Deezer"
                }
    except Exception:
        pass

    # Fallback to iTunes
    itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(artist_name)}&entity=musicArtist&limit=5"
    itunes_req = urllib.request.Request(itunes_url, headers={"User-Agent": "Sonance/2.1"})

    try:
        with urllib.request.urlopen(itunes_req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                best = results[0]
                return {
                    "id": str(best.get("artistId", "")),
                    "name": best.get("artistName", ""),
                    "picture": "",
                    "nb_album": 0,
                    "nb_fan": 0,
                    "source": "iTunes"
                }
    except Exception:
        pass

    return None


def get_artist_albums(artist_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Fetches all albums and releases for a Deezer artist ID."""
    url = f"https://api.deezer.com/artist/{artist_id}/albums?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Sonance/2.1"})

    albums = []
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])

            for item in items:
                album_id = str(item.get("id", ""))
                title = item.get("title", "")
                cover = item.get("cover_xl") or item.get("cover_big") or item.get("cover_medium") or ""
                release_date = item.get("release_date", "")
                year = release_date[:4] if release_date else ""
                record_type = item.get("record_type", "album").capitalize()
                genre_id = item.get("genre_id", 0)

                albums.append({
                    "id": album_id,
                    "title": title,
                    "year": year,
                    "release_date": release_date,
                    "type": record_type,
                    "cover_url": cover,
                    "genre_id": genre_id,
                    "tracks": []
                })
    except Exception:
        pass

    # Sort chronologically by year descending
    albums.sort(key=lambda x: x["year"], reverse=True)
    return albums


def get_album_tracklist(album_id: str) -> List[Dict[str, Any]]:
    """Fetches the complete tracklist for a given album ID."""
    url = f"https://api.deezer.com/album/{album_id}/tracks?limit=100"
    req = urllib.request.Request(url, headers={"User-Agent": "Sonance/2.1"})

    tracks = []
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])

            for item in items:
                track_id = str(item.get("id", ""))
                title = item.get("title", "")
                duration = item.get("duration", 0)
                track_num = item.get("track_position", len(tracks) + 1)
                artist = item.get("artist", {}).get("name", "")

                mins = duration // 60
                secs = duration % 60
                dur_str = f"{mins}:{secs:02d}"

                tracks.append({
                    "id": track_id,
                    "track_number": track_num,
                    "title": title,
                    "artist": artist,
                    "duration_sec": duration,
                    "duration_str": dur_str
                })
    except Exception:
        pass

    return tracks


def get_full_discography(artist_name: str, include_tracks: bool = True, max_albums: int = 15) -> Dict[str, Any]:
    """
    High-level entry point:
    Finds the artist, fetches all studio albums/EPs, and optionally hydrates tracklists.
    """
    artist = search_artist(artist_name)
    if not artist:
        return {"success": False, "error": f"Artist '{artist_name}' not found."}

    albums = get_artist_albums(artist["id"], limit=max_albums)

    if include_tracks and albums:
        # Hydrate top 5 albums with complete tracklists
        for alb in albums[:5]:
            alb["tracks"] = get_album_tracklist(alb["id"])

    total_tracks_found = sum(len(a.get("tracks", [])) for a in albums)

    return {
        "success": True,
        "artist": artist,
        "albums": albums,
        "total_albums": len(albums),
        "hydrated_tracks_count": total_tracks_found
    }


if __name__ == "__main__":
    print("Testing discography_scraper module...")

    artist_profile = search_artist("Daft Punk")
    assert artist_profile is not None, "Failed to find artist 'Daft Punk'"
    print(f"✓ Found artist: {artist_profile['name']} (ID: {artist_profile['id']})")

    albums = get_artist_albums(artist_profile["id"], limit=5)
    assert len(albums) > 0, "Expected at least 1 album for Daft Punk"
    print(f"✓ Found {len(albums)} albums. Latest: {albums[0]['title']} ({albums[0]['year']})")

    tracks = get_album_tracklist(albums[0]["id"])
    assert len(tracks) > 0, f"Expected tracks for album {albums[0]['title']}"
    print(f"✓ Album '{albums[0]['title']}' has {len(tracks)} tracks. Track 1: {tracks[0]['title']} ({tracks[0]['duration_str']})")

    print("✓ All discography_scraper unit tests passed successfully!")
