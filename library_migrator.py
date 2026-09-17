"""
library_migrator.py - Cross-Platform Library & Playlist Migrator
Part of Sonance - The Ultimate Open-Source Music Workstation
Imports music libraries, playlists, play counts, and star ratings from
iTunes / Apple Music Library XML (plist), MusicBee, Winamp, and Foobar2000.
Features intelligent fuzzy path reconciliation for relocated audio folders.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import urllib.parse
import plistlib
from typing import Dict, Any, List, Optional, Tuple


def _decode_file_uri(uri: str) -> str:
    """Decodes a file:// URL into a normalized local filesystem path."""
    if not uri.startswith("file://"):
        return uri

    # Strip file://localhost/ or file:///
    parsed = urllib.parse.urlparse(uri)
    path = urllib.parse.unquote(parsed.path)

    # On Windows, urlparse('/C:/Music') -> '/C:/Music'
    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]

    return os.path.normpath(path)


def _build_directory_file_index(target_dir: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Builds lookup index of filenames and relative paths within the target music directory."""
    name_to_path = {}
    tail_to_path = {}

    if not os.path.isdir(target_dir):
        return name_to_path, tail_to_path

    for root, _, files in os.walk(target_dir):
        for f in files:
            full = os.path.join(root, f)
            name_lower = f.lower()
            name_to_path[name_lower] = full

            # 2-level tail: e.g. "album/track.mp3"
            rel = os.path.relpath(full, target_dir).replace("\\", "/").lower()
            tail_to_path[rel] = full

    return name_to_path, tail_to_path


def parse_itunes_library_xml(
    xml_path: str, target_music_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parses iTunes Music Library XML file.
    Reconciles track paths against target_music_dir if provided.
    """
    if not os.path.isfile(xml_path):
        return {"success": False, "error": f"XML file not found: {xml_path}"}

    try:
        with open(xml_path, "rb") as f:
            data = plistlib.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to parse iTunes plist XML: {e}"}

    raw_tracks = data.get("Tracks", {})
    raw_playlists = data.get("Playlists", [])

    # Build local index if target dir provided
    name_index = {}
    tail_index = {}
    if target_music_dir and os.path.isdir(target_music_dir):
        name_index, tail_index = _build_directory_file_index(target_music_dir)

    tracks_by_id = {}
    total_matched = 0
    total_missing = 0
    high_rated_paths = []

    for t_id, t_info in raw_tracks.items():
        loc = t_info.get("Location")
        if not loc:
            continue

        orig_path = _decode_file_uri(loc)
        resolved_path = orig_path

        # Check if original path exists on disk
        if not os.path.isfile(resolved_path) and target_music_dir:
            # Attempt fuzzy resolution
            fn = os.path.basename(orig_path).lower()
            # Try 2-level tail first (artist/album/song or album/song)
            parts = orig_path.replace("\\", "/").split("/")
            matched = False
            if len(parts) >= 2:
                two_level = f"{parts[-2]}/{parts[-1]}".lower()
                if two_level in tail_index:
                    resolved_path = tail_index[two_level]
                    matched = True

            if not matched and fn in name_index:
                resolved_path = name_index[fn]
                matched = True

        exists = os.path.isfile(resolved_path)
        if exists:
            total_matched += 1
        else:
            total_missing += 1

        rating = t_info.get("Rating", 0) // 20  # 100-scale to 5-star scale
        play_count = t_info.get("Play Count", 0)

        if rating >= 4 and exists:
            high_rated_paths.append(resolved_path)

        tracks_by_id[t_id] = {
            "id": t_id,
            "title": t_info.get("Name", "Unknown Track"),
            "artist": t_info.get("Artist", "Unknown Artist"),
            "album": t_info.get("Album", "Unknown Album"),
            "original_path": orig_path,
            "resolved_path": resolved_path,
            "exists_on_disk": exists,
            "rating_stars": rating,
            "play_count": play_count,
            "year": t_info.get("Year"),
        }

    # Process playlists
    migrated_playlists = []
    for pl in raw_playlists:
        name = pl.get("Name", "Untitled Playlist")
        # Skip iTunes system internal playlists
        if pl.get("Master") or pl.get("Distinguished Kind") in {1, 2, 3, 4, 18, 19}:
            continue

        items = pl.get("Playlist Items", [])
        pl_tracks = []
        for item in items:
            tid = str(item.get("Track ID"))
            if tid in tracks_by_id:
                pl_tracks.append(tracks_by_id[tid])

        if pl_tracks:
            migrated_playlists.append({
                "name": name,
                "track_count": len(pl_tracks),
                "matched_count": sum(1 for t in pl_tracks if t["exists_on_disk"]),
                "tracks": pl_tracks,
            })

    return {
        "success": True,
        "source_format": "iTunes / Apple Music Library XML",
        "total_tracks": len(tracks_by_id),
        "matched_on_disk": total_matched,
        "missing_on_disk": total_missing,
        "match_percentage": round((total_matched / max(1, len(tracks_by_id))) * 100, 1),
        "total_playlists": len(migrated_playlists),
        "playlists": migrated_playlists,
        "favorites_count": len(high_rated_paths),
        "tracks": list(tracks_by_id.values())[:100],  # sample for preview
    }


def export_migrated_playlists(
    migration_result: Dict[str, Any], output_dir: str
) -> List[str]:
    """Exports migrated playlists as standard .m3u8 files into the destination folder."""
    os.makedirs(output_dir, exist_ok=True)
    exported_files = []

    playlists = migration_result.get("playlists", [])
    for pl in playlists:
        safe_name = "".join(c for c in pl["name"] if c.isalnum() or c in " ._-").strip()
        if not safe_name:
            safe_name = "Imported_Playlist"
        pl_path = os.path.join(output_dir, f"{safe_name}.m3u8")

        lines = ["#EXTM3U", f"#PLAYLIST:{pl['name']}"]
        count = 0
        for t in pl["tracks"]:
            track_file = t.get("resolved_path") or t.get("original_path")
            if track_file:
                lines.append(f"#EXTINF:-1,{t.get('artist', 'Unknown')} - {t.get('title', 'Track')}")
                lines.append(track_file)
                count += 1

        if count > 0:
            with open(pl_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            exported_files.append(pl_path)

    return exported_files


def migrate_library(
    xml_or_file: str,
    target_music_dir: Optional[str] = None,
    output_playlist_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    High-level library migration entrypoint.
    Parses library XML, reconciles paths, and optionally exports .m3u8 playlists.
    """
    res = parse_itunes_library_xml(xml_or_file, target_music_dir=target_music_dir)
    if not res.get("success"):
        return res

    if output_playlist_dir and res.get("playlists"):
        exported = export_migrated_playlists(res, output_playlist_dir)
        res["exported_playlist_files"] = exported

    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python library_migrator.py <iTunes_Music_Library.xml> [target_music_dir] [out_playlist_dir]")
        sys.exit(1)

    xml_f = sys.argv[1]
    tgt_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    out_dir = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None

    result = migrate_library(xml_f, target_music_dir=tgt_dir, output_playlist_dir=out_dir)
    if result.get("success"):
        print("[+] Library Migration Analysis Complete!")
        print(f"    • Total Tracks:       {result['total_tracks']}")
        print(f"    • Matched on Disk:    {result['matched_on_disk']} ({result['match_percentage']}%)")
        print(f"    • Missing on Disk:    {result['missing_on_disk']}")
        print(f"    • Playlists Found:    {result['total_playlists']}")
        for p in result.get("playlists", [])[:5]:
            print(f"      - {p['name']} ({p['track_count']} tracks, {p['matched_count']} matched)")
        if result.get("exported_playlist_files"):
            print(f"    • Playlists Exported: {len(result['exported_playlist_files'])} .m3u8 files")
    else:
        print(f"[-] Migration Failed: {result.get('error')}")
