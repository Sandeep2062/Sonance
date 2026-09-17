#!/usr/bin/env python3
"""
Sonance - Universal Multi-Format Playlist Converter
===================================================
Converts playlists seamlessly between M3U/M3U8, PLS, WPL (Windows Media),
and XSPF (VLC/XML). Also parses Spotify public playlist URLs to convert
online tracklists into local or downloadable playlist manifests.

Author: Sandeep Khadka (Sandeep2062) <sandeepkhadka9090@gmail.com>
License: GNU GPLv3 with Commons Clause
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import urllib.parse
import requests


def parse_m3u(file_path: str) -> List[Dict[str, Any]]:
    """Parses standard and extended M3U/M3U8 playlists."""
    tracks = []
    current_title = ""
    current_artist = ""
    current_duration = 0

    base_dir = os.path.dirname(os.path.abspath(file_path))

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#EXTINF:"):
                # Format: #EXTINF:180,Artist - Title  OR  #EXTINF:180,Title
                meta = line[8:].strip()
                comma_idx = meta.find(",")
                if comma_idx != -1:
                    dur_str = meta[:comma_idx].strip()
                    try:
                        current_duration = int(float(dur_str))
                    except ValueError:
                        current_duration = 0
                    full_title = meta[comma_idx + 1:].strip()
                    if " - " in full_title:
                        parts = full_title.split(" - ", 1)
                        current_artist = parts[0].strip()
                        current_title = parts[1].strip()
                    else:
                        current_title = full_title
                        current_artist = "Unknown"
            elif not line.startswith("#"):
                # Audio file path or URL
                track_path = line
                if not os.path.isabs(track_path) and not track_path.startswith("http"):
                    track_path = os.path.normpath(os.path.join(base_dir, track_path))

                if not current_title:
                    fname = os.path.splitext(os.path.basename(track_path))[0]
                    if " - " in fname:
                        parts = fname.split(" - ", 1)
                        current_artist = parts[0].strip()
                        current_title = parts[1].strip()
                    else:
                        current_title = fname
                        current_artist = "Unknown"

                tracks.append({
                    "title": current_title,
                    "artist": current_artist,
                    "duration": current_duration,
                    "path": track_path,
                })
                current_title = ""
                current_artist = ""
                current_duration = 0

    return tracks


def parse_pls(file_path: str) -> List[Dict[str, Any]]:
    """Parses INI-style PLS playlists."""
    tracks_dict = {}
    base_dir = os.path.dirname(os.path.abspath(file_path))

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("["):
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()

                m_file = re.match(r"File(\d+)", key, re.IGNORECASE)
                m_title = re.match(r"Title(\d+)", key, re.IGNORECASE)
                m_len = re.match(r"Length(\d+)", key, re.IGNORECASE)

                if m_file:
                    idx = int(m_file.group(1))
                    if idx not in tracks_dict:
                        tracks_dict[idx] = {}
                    p = val
                    if not os.path.isabs(p) and not p.startswith("http"):
                        p = os.path.normpath(os.path.join(base_dir, p))
                    tracks_dict[idx]["path"] = p
                elif m_title:
                    idx = int(m_title.group(1))
                    if idx not in tracks_dict:
                        tracks_dict[idx] = {}
                    tracks_dict[idx]["raw_title"] = val
                elif m_len:
                    idx = int(m_len.group(1))
                    if idx not in tracks_dict:
                        tracks_dict[idx] = {}
                    try:
                        tracks_dict[idx]["duration"] = int(val)
                    except ValueError:
                        tracks_dict[idx]["duration"] = 0

    tracks = []
    for idx in sorted(tracks_dict.keys()):
        item = tracks_dict[idx]
        path = item.get("path", "")
        raw_title = item.get("raw_title", "")
        if " - " in raw_title:
            parts = raw_title.split(" - ", 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        else:
            artist = "Unknown"
            title = raw_title or (os.path.splitext(os.path.basename(path))[0] if path else f"Track {idx}")

        tracks.append({
            "title": title,
            "artist": artist,
            "duration": item.get("duration", 0),
            "path": path,
        })
    return tracks


def parse_wpl(file_path: str) -> List[Dict[str, Any]]:
    """Parses Windows Media Player XML playlists (.wpl)."""
    tracks = []
    base_dir = os.path.dirname(os.path.abspath(file_path))

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for media in root.findall(".//media"):
            src = media.attrib.get("src", "")
            if src:
                if not os.path.isabs(src) and not src.startswith("http"):
                    src = os.path.normpath(os.path.join(base_dir, src))
                fname = os.path.splitext(os.path.basename(src))[0]
                if " - " in fname:
                    parts = fname.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                else:
                    artist = "Unknown"
                    title = fname

                tracks.append({
                    "title": title,
                    "artist": artist,
                    "duration": 0,
                    "path": src,
                })
    except Exception:
        pass
    return tracks


def parse_xspf(file_path: str) -> List[Dict[str, Any]]:
    """Parses XML Shareable Playlist Format (.xspf)."""
    tracks = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        # Handle XML namespaces if present
        ns = {"x": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
        prefix = "x:" if ns else ""

        for t in root.findall(f".//{prefix}track", ns):
            title_node = t.find(f"{prefix}title", ns)
            artist_node = t.find(f"{prefix}creator", ns)
            loc_node = t.find(f"{prefix}location", ns)
            dur_node = t.find(f"{prefix}duration", ns)

            path = loc_node.text.strip() if loc_node is not None and loc_node.text else ""
            if path.startswith("file:///"):
                path = urllib.parse.unquote(path[8:])
            elif path.startswith("file://"):
                path = urllib.parse.unquote(path[7:])

            title = title_node.text.strip() if title_node is not None and title_node.text else ""
            artist = artist_node.text.strip() if artist_node is not None and artist_node.text else "Unknown"
            dur_ms = int(dur_node.text.strip()) if dur_node is not None and dur_node.text and dur_node.text.isdigit() else 0

            tracks.append({
                "title": title or (os.path.splitext(os.path.basename(path))[0] if path else "Unknown"),
                "artist": artist,
                "duration": int(dur_ms / 1000),
                "path": path,
            })
    except Exception:
        pass
    return tracks


def parse_spotify_url(url: str) -> Dict[str, Any]:
    """Parses Spotify playlist link using public oEmbed or catalog metadata."""
    m = re.search(r"playlist[/:]([a-zA-Z0-9]+)", url)
    if not m:
        return {"success": False, "error": "Invalid Spotify playlist URL or URI."}

    playlist_id = m.group(1)
    oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/playlist/{playlist_id}"

    try:
        resp = requests.get(oembed_url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title", f"Spotify Playlist {playlist_id}")
            return {
                "success": True,
                "title": title,
                "spotify_id": playlist_id,
                "thumbnail": data.get("thumbnail_url", ""),
                "tracks": [],
                "note": "Imported metadata from Spotify. Matching with local tracks or Deezer/YouTube catalog.",
            }
    except Exception:
        pass

    return {
        "success": True,
        "title": f"Spotify Playlist {playlist_id}",
        "spotify_id": playlist_id,
        "tracks": [],
    }


def parse_any_playlist(source: str) -> Dict[str, Any]:
    """Universal parser detecting file extension or URL type."""
    if source.startswith("http://") or source.startswith("https://"):
        if "spotify.com" in source:
            return parse_spotify_url(source)
        return {"success": False, "error": "Only local playlist files and Spotify links are currently supported."}

    if not os.path.isfile(source):
        return {"success": False, "error": f"Playlist file not found: {source}"}

    ext = os.path.splitext(source)[1].lower()
    title = os.path.splitext(os.path.basename(source))[0]

    if ext in [".m3u", ".m3u8"]:
        tracks = parse_m3u(source)
        fmt = "M3U"
    elif ext == ".pls":
        tracks = parse_pls(source)
        fmt = "PLS"
    elif ext == ".wpl":
        tracks = parse_wpl(source)
        fmt = "WPL"
    elif ext == ".xspf":
        tracks = parse_xspf(source)
        fmt = "XSPF"
    else:
        # Fallback to M3U parser
        tracks = parse_m3u(source)
        fmt = "Unknown (Parsed as M3U)"

    return {
        "success": True,
        "format": fmt,
        "title": title,
        "source_path": source,
        "track_count": len(tracks),
        "tracks": tracks,
    }


def export_playlist(
    tracks: List[Dict[str, Any]],
    output_format: str,
    output_file: str,
    playlist_title: str = "Sonance Playlist"
) -> Dict[str, Any]:
    """
    Exports a list of tracks into the specified playlist format (.m3u8, .pls, .wpl, .xspf).
    """
    out_fmt = output_format.lower().replace(".", "").strip()
    if not out_fmt:
        out_fmt = "m3u8"

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    try:
        if out_fmt in ["m3u", "m3u8"]:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"#PLAYLIST:{playlist_title}\n\n")
                for t in tracks:
                    dur = t.get("duration", 0)
                    artist = t.get("artist", "Unknown")
                    title = t.get("title", "Track")
                    p = t.get("path", "")
                    f.write(f"#EXTINF:{dur},{artist} - {title}\n")
                    f.write(f"{p}\n")

        elif out_fmt == "pls":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("[playlist]\n")
                f.write(f"NumberOfEntries={len(tracks)}\n\n")
                for i, t in enumerate(tracks, 1):
                    artist = t.get("artist", "Unknown")
                    title = t.get("title", "Track")
                    p = t.get("path", "")
                    dur = t.get("duration", 0)
                    f.write(f"File{i}={p}\n")
                    f.write(f"Title{i}={artist} - {title}\n")
                    f.write(f"Length{i}={dur}\n\n")
                f.write("Version=2\n")

        elif out_fmt == "wpl":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write('<?wpl version="1.0"?>\n')
                f.write('<smil>\n  <head>\n')
                f.write(f'    <meta name="Generator" content="Sonance"/>\n')
                f.write(f'    <title>{playlist_title}</title>\n')
                f.write('  </head>\n  <body>\n    <seq>\n')
                for t in tracks:
                    p = t.get("path", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    f.write(f'      <media src="{p}"/>\n')
                f.write('    </seq>\n  </body>\n</smil>\n')

        elif out_fmt == "xspf":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<playlist version="1" xmlns="http://xspf.org/ns/0/">\n')
                f.write(f'  <title>{playlist_title}</title>\n')
                f.write('  <creator>Sonance Music Workstation</creator>\n')
                f.write('  <trackList>\n')
                for t in tracks:
                    title = t.get("title", "Track").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    artist = t.get("artist", "Unknown").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    p = t.get("path", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    dur_ms = int(t.get("duration", 0) * 1000)
                    f.write('    <track>\n')
                    f.write(f'      <location>{p}</location>\n')
                    f.write(f'      <title>{title}</title>\n')
                    f.write(f'      <creator>{artist}</creator>\n')
                    f.write(f'      <duration>{dur_ms}</duration>\n')
                    f.write('    </track>\n')
                f.write('  </trackList>\n</playlist>\n')
        else:
            return {"success": False, "error": f"Unsupported export format: {out_fmt}"}

        return {
            "success": True,
            "output_file": output_file,
            "format": out_fmt.upper(),
            "track_count": len(tracks),
            "title": playlist_title,
        }
    except Exception as e:
        return {"success": False, "error": f"Export failed: {str(e)}"}


def convert_playlist(
    input_file: str,
    output_format: str = "m3u8",
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """Converts a playlist file directly into another format."""
    parsed = parse_any_playlist(input_file)
    if not parsed.get("success"):
        return parsed

    tracks = parsed.get("tracks", [])
    title = parsed.get("title", "Converted Playlist")

    out_fmt = output_format.lower().replace(".", "").strip()
    if not output_file:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_dir = os.path.dirname(os.path.abspath(input_file))
        output_file = os.path.join(output_dir, f"{base_name}.{out_fmt}")

    return export_playlist(tracks, out_fmt, output_file, title)


if __name__ == "__main__":
    print("Testing Universal Playlist Converter...")
    mock_tracks = [
        {"title": "Bohemian Rhapsody", "artist": "Queen", "duration": 354, "path": "C:\\Music\\queen.flac"},
        {"title": "Hotel California", "artist": "Eagles", "duration": 390, "path": "C:\\Music\\eagles.mp3"}
    ]

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        m3u_file = os.path.join(tmpdir, "test.m3u8")
        pls_file = os.path.join(tmpdir, "test.pls")
        xspf_file = os.path.join(tmpdir, "test.xspf")
        wpl_file = os.path.join(tmpdir, "test.wpl")

        # Test export M3U8
        res = export_playlist(mock_tracks, "m3u8", m3u_file, "Rock Classics")
        assert res["success"] is True and os.path.exists(m3u_file)

        # Test parse M3U8
        p_m3u = parse_any_playlist(m3u_file)
        assert p_m3u["track_count"] == 2
        assert p_m3u["tracks"][0]["artist"] == "Queen"

        # Test export PLS
        res_pls = export_playlist(mock_tracks, "pls", pls_file, "Rock Classics")
        assert res_pls["success"] is True
        p_pls = parse_any_playlist(pls_file)
        assert p_pls["track_count"] == 2

        # Test export XSPF
        res_xspf = export_playlist(mock_tracks, "xspf", xspf_file, "Rock Classics")
        assert res_xspf["success"] is True
        p_xspf = parse_any_playlist(xspf_file)
        assert p_xspf["track_count"] == 2

        # Test convert PLS -> WPL
        conv_res = convert_playlist(pls_file, "wpl", wpl_file)
        assert conv_res["success"] is True and os.path.exists(wpl_file)

    print("Universal Playlist Converter unit tests passed successfully!")
