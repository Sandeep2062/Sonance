"""
playlist_manager.py - Sonance User Playlists & Favorites Management

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Stores custom user playlists, liked tracks, history, and exports standard M3U playlists.
"""

import os
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

LIBRARY_FILE = Path(__file__).parent.resolve() / "user_library.json"
_LOCK = threading.Lock()


def load_library() -> Dict[str, Any]:
  """Loads user playlists and favorites from disk."""
  with _LOCK:
    if LIBRARY_FILE.exists():
      try:
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
          return json.load(f)
      except Exception:
        pass
    return {"favorites": [], "playlists": {}, "history": []}


def save_library(data: Dict[str, Any]):
  """Saves user playlists and favorites to disk."""
  with _LOCK:
    try:
      with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
      pass


# ------------------ Favorites ------------------

def toggle_favorite(track: Dict[str, Any]) -> bool:
  """Toggles track favorite status. Returns True if now favored, False if removed."""
  lib = load_library()
  favs = lib.get("favorites", [])
  t_id = track.get("id")

  existing_idx = next((i for i, t in enumerate(favs) if t.get("id") == t_id), -1)
  if existing_idx >= 0:
    favs.pop(existing_idx)
    is_fav = False
  else:
    favs.append(track)
    is_fav = True

  lib["favorites"] = favs
  save_library(lib)
  return is_fav


def get_favorites() -> List[Dict[str, Any]]:
  lib = load_library()
  return lib.get("favorites", [])


# ------------------ Custom Playlists ------------------

def create_playlist(name: str) -> bool:
  name = name.strip()
  if not name:
    return False
  lib = load_library()
  if name in lib.get("playlists", {}):
    return False
  lib.setdefault("playlists", {})[name] = []
  save_library(lib)
  return True


def add_track_to_playlist(playlist_name: str, track: Dict[str, Any]) -> bool:
  lib = load_library()
  pls = lib.setdefault("playlists", {})
  if playlist_name not in pls:
    pls[playlist_name] = []

  t_id = track.get("id")
  if not any(t.get("id") == t_id for t in pls[playlist_name]):
    pls[playlist_name].append(track)
    save_library(lib)
    return True
  return False


def get_all_playlists() -> Dict[str, List[Dict[str, Any]]]:
  lib = load_library()
  return lib.get("playlists", {})


def export_playlist_m3u(playlist_name: str, output_path: str) -> bool:
  """Exports playlist into standard .m3u format with track paths."""
  lib = load_library()
  tracks = lib.get("playlists", {}).get(playlist_name, [])
  if not tracks:
    return False

  try:
    with open(output_path, "w", encoding="utf-8") as f:
      f.write("#EXTM3U\n")
      for t in tracks:
        dur = t.get("duration", 0)
        artist = t.get("artist", "Unknown")
        title = t.get("title", "Unknown")
        path = t.get("localFilePath") or t.get("streamUrl") or ""
        f.write(f"#EXTINF:{dur},{artist} - {title}\n")
        f.write(f"{path}\n")
    return True
  except Exception:
    return False
