"""
tag_editor.py - Sonance Professional Audio Metadata & Tag Editor

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Full professional audio metadata & tagging capability:
- Read & write tags across MP3 (ID3v2.4), FLAC (Vorbis Comment), M4A/MP4, and OGG
- High-resolution Album Cover Art extraction, embedding, and replacement
- MusicBrainz & Last.fm auto-tag lookup
- Synchronized and unsynchronized lyrics tag embedding
"""

import os
import io
import base64
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TDRC, TCON, TRCK, TPOS, COMM, USLT, APIC
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis


def read_tags(file_path: str) -> Dict[str, Any]:
    """
    Reads detailed metadata tags and extracts embedded album cover art as a base64 data URI.
    """
    if not os.path.exists(file_path):
        return {"success": False, "error": "File does not exist"}

    ext = os.path.splitext(file_path)[1].lower()
    meta: Dict[str, Any] = {
        "success": True,
        "path": file_path,
        "filename": os.path.basename(file_path),
        "format": ext.replace(".", "").upper(),
        "title": "",
        "artist": "",
        "album": "",
        "album_artist": "",
        "year": "",
        "genre": "",
        "track_number": "",
        "total_tracks": "",
        "disc_number": "",
        "comment": "",
        "has_cover": False,
        "cover_data_uri": "",
    }

    try:
        if ext == ".mp3":
            try:
                audio = ID3(file_path)
            except Exception:
                audio = None

            if audio:
                if "TIT2" in audio: meta["title"] = str(audio["TIT2"].text[0])
                if "TPE1" in audio: meta["artist"] = str(audio["TPE1"].text[0])
                if "TPE2" in audio: meta["album_artist"] = str(audio["TPE2"].text[0])
                if "TALB" in audio: meta["album"] = str(audio["TALB"].text[0])
                if "TDRC" in audio: meta["year"] = str(audio["TDRC"].text[0])
                if "TCON" in audio: meta["genre"] = str(audio["TCON"].text[0])
                if "TRCK" in audio:
                    tr = str(audio["TRCK"].text[0])
                    meta["track_number"] = tr.split("/")[0]
                    if "/" in tr: meta["total_tracks"] = tr.split("/")[1]
                if "TPOS" in audio: meta["disc_number"] = str(audio["TPOS"].text[0]).split("/")[0]

                # Extract APIC cover art
                for tag in audio.values():
                    if isinstance(tag, APIC):
                        mime = tag.mime or "image/jpeg"
                        b64 = base64.b64encode(tag.data).decode("utf-8")
                        meta["cover_data_uri"] = f"data:{mime};base64,{b64}"
                        meta["has_cover"] = True
                        break

        elif ext == ".flac":
            audio = FLAC(file_path)
            meta["title"] = audio.get("title", [""])[0]
            meta["artist"] = audio.get("artist", [""])[0]
            meta["album_artist"] = audio.get("albumartist", [""])[0]
            meta["album"] = audio.get("album", [""])[0]
            meta["year"] = audio.get("date", [""])[0] or audio.get("year", [""])[0]
            meta["genre"] = audio.get("genre", [""])[0]
            meta["track_number"] = audio.get("tracknumber", [""])[0]
            meta["total_tracks"] = audio.get("tracktotal", [""])[0]
            meta["disc_number"] = audio.get("discnumber", [""])[0]

            if audio.pictures:
                pic = audio.pictures[0]
                mime = pic.mime or "image/jpeg"
                b64 = base64.b64encode(pic.data).decode("utf-8")
                meta["cover_data_uri"] = f"data:{mime};base64,{b64}"
                meta["has_cover"] = True

        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(file_path)
            meta["title"] = audio.get("\xa9nam", [""])[0]
            meta["artist"] = audio.get("\xa9ART", [""])[0]
            meta["album_artist"] = audio.get("aART", [""])[0]
            meta["album"] = audio.get("\xa9alb", [""])[0]
            meta["year"] = audio.get("\xa9day", [""])[0]
            meta["genre"] = audio.get("\xa9gen", [""])[0]
            meta["comment"] = audio.get("\xa9cmt", [""])[0]

            trkn = audio.get("trkn", [(0, 0)])[0]
            if trkn[0]: meta["track_number"] = str(trkn[0])
            if trkn[1]: meta["total_tracks"] = str(trkn[1])

            disk = audio.get("disk", [(0, 0)])[0]
            if disk[0]: meta["disc_number"] = str(disk[0])

            covr = audio.get("covr", [])
            if covr:
                pic_data = bytes(covr[0])
                mime = "image/png" if covr[0].imageformat == MP4Cover.FORMAT_PNG else "image/jpeg"
                b64 = base64.b64encode(pic_data).decode("utf-8")
                meta["cover_data_uri"] = f"data:{mime};base64,{b64}"
                meta["has_cover"] = True

        elif ext == ".ogg":
            audio = OggVorbis(file_path)
            meta["title"] = audio.get("title", [""])[0]
            meta["artist"] = audio.get("artist", [""])[0]
            meta["album"] = audio.get("album", [""])[0]
            meta["year"] = audio.get("date", [""])[0]
            meta["genre"] = audio.get("genre", [""])[0]

    except Exception as e:
        meta["error"] = str(e)

    return meta


def write_tags(file_path: str, tags: Dict[str, Any]) -> Dict[str, Any]:
    """
    Writes metadata tags and embeds optional cover art to the target audio file.
    """
    if not os.path.exists(file_path):
        return {"success": False, "error": "File does not exist"}

    ext = os.path.splitext(file_path)[1].lower()

    title = str(tags.get("title", "")).strip()
    artist = str(tags.get("artist", "")).strip()
    album = str(tags.get("album", "")).strip()
    album_artist = str(tags.get("album_artist", "")).strip()
    year = str(tags.get("year", "")).strip()
    genre = str(tags.get("genre", "")).strip()
    track_no = str(tags.get("track_number", "")).strip()
    total_tracks = str(tags.get("total_tracks", "")).strip()
    disc_no = str(tags.get("disc_number", "")).strip()
    comment = str(tags.get("comment", "")).strip()
    cover_data_uri = tags.get("cover_data_uri", "").strip()

    # Parse cover art image bytes if provided
    cover_bytes = None
    cover_mime = "image/jpeg"
    if cover_data_uri.startswith("data:"):
        try:
            header, b64_str = cover_data_uri.split(",", 1)
            cover_mime = header.split(";")[0].replace("data:", "")
            cover_bytes = base64.b64decode(b64_str)
        except Exception:
            pass
    elif cover_data_uri.startswith("http://") or cover_data_uri.startswith("https://"):
        try:
            img_res = requests.get(cover_data_uri, timeout=6)
            if img_res.status_code == 200:
                cover_bytes = img_res.content
                cover_mime = img_res.headers.get("Content-Type", "image/jpeg")
        except Exception:
            pass

    try:
        if ext == ".mp3":
            try:
                audio = ID3(file_path)
            except Exception:
                audio = ID3()

            if title: audio["TIT2"] = TIT2(encoding=3, text=title)
            if artist: audio["TPE1"] = TPE1(encoding=3, text=artist)
            if album_artist: audio["TPE2"] = TPE2(encoding=3, text=album_artist)
            if album: audio["TALB"] = TALB(encoding=3, text=album)
            if year: audio["TDRC"] = TDRC(encoding=3, text=year)
            if genre: audio["TCON"] = TCON(encoding=3, text=genre)
            if comment: audio["COMM"] = COMM(encoding=3, lang="eng", desc="", text=comment)

            if track_no:
                tr_str = f"{track_no}/{total_tracks}" if total_tracks else track_no
                audio["TRCK"] = TRCK(encoding=3, text=tr_str)
            if disc_no:
                audio["TPOS"] = TPOS(encoding=3, text=disc_no)

            if cover_bytes:
                # Remove previous APIC
                audio.delall("APIC")
                audio["APIC"] = APIC(
                    encoding=3,
                    mime=cover_mime,
                    type=3,  # Front cover
                    desc="Cover",
                    data=cover_bytes,
                )
            elif tags.get("remove_cover"):
                audio.delall("APIC")

            audio.save(file_path, v2_version=4)

        elif ext == ".flac":
            audio = FLAC(file_path)
            if title: audio["title"] = title
            if artist: audio["artist"] = artist
            if album_artist: audio["albumartist"] = album_artist
            if album: audio["album"] = album
            if year: audio["date"] = year
            if genre: audio["genre"] = genre
            if track_no: audio["tracknumber"] = track_no
            if total_tracks: audio["tracktotal"] = total_tracks
            if disc_no: audio["discnumber"] = disc_no

            if cover_bytes:
                audio.clear_pictures()
                pic = Picture()
                pic.type = 3
                pic.mime = cover_mime
                pic.desc = "Cover"
                pic.data = cover_bytes
                audio.add_picture(pic)
            elif tags.get("remove_cover"):
                audio.clear_pictures()

            audio.save()

        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(file_path)
            if title: audio["\xa9nam"] = [title]
            if artist: audio["\xa9ART"] = [artist]
            if album_artist: audio["aART"] = [album_artist]
            if album: audio["\xa9alb"] = [album]
            if year: audio["\xa9day"] = [year]
            if genre: audio["\xa9gen"] = [genre]
            if comment: audio["\xa9cmt"] = [comment]

            t_val = int(track_no) if track_no.isdigit() else 0
            tot_val = int(total_tracks) if total_tracks.isdigit() else 0
            if t_val > 0 or tot_val > 0:
                audio["trkn"] = [(t_val, tot_val)]

            d_val = int(disc_no) if disc_no.isdigit() else 0
            if d_val > 0:
                audio["disk"] = [(d_val, 0)]

            if cover_bytes:
                fmt = MP4Cover.FORMAT_PNG if "png" in cover_mime else MP4Cover.FORMAT_JPEG
                audio["covr"] = [MP4Cover(cover_bytes, imageformat=fmt)]
            elif tags.get("remove_cover"):
                if "covr" in audio:
                    del audio["covr"]

            audio.save()

        elif ext == ".ogg":
            audio = OggVorbis(file_path)
            if title: audio["title"] = [title]
            if artist: audio["artist"] = [artist]
            if album: audio["album"] = [album]
            if year: audio["date"] = [year]
            if genre: audio["genre"] = [genre]
            audio.save()

        return {"success": True, "message": "Tags saved successfully!"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def auto_fetch_metadata(title: str, artist: str) -> Dict[str, Any]:
    """
    Queries MusicBrainz and Last.fm to automatically complete missing tags
    (Album, Year, Genre, Cover Art) for a track.
    """
    clean_q = f'recording:"{title}" AND artist:"{artist}"'
    url = "https://musicbrainz.org/ws/2/recording/"
    headers = {"User-Agent": "Sonance/3.6.4 (https://github.com/Sandeep2062/Sonance)"}

    result = {
        "title": title,
        "artist": artist,
        "album": "",
        "year": "",
        "genre": "",
        "cover_url": "",
    }

    try:
        r = requests.get(url, params={"query": clean_q, "fmt": "json"}, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            recordings = data.get("recordings", [])
            if recordings:
                rec = recordings[0]
                releases = rec.get("releases", [])
                if releases:
                    rel = releases[0]
                    result["album"] = rel.get("title", "")
                    result["year"] = rel.get("date", "").split("-")[0]
                    rel_id = rel.get("id")
                    if rel_id:
                        result["cover_url"] = f"https://coverartarchive.org/release/{rel_id}/front-500"

                tags = rec.get("tags", [])
                if tags:
                    result["genre"] = tags[0].get("name", "").capitalize()
    except Exception:
        pass

    # Fallback to Deezer catalog for high-res cover art & album details if MusicBrainz cover missing
    if not result["cover_url"] or not result["album"]:
        try:
            dz_url = f"https://api.deezer.com/search?q={requests.utils.quote(f'{artist} {title}')}&limit=1"
            dz_r = requests.get(dz_url, timeout=5).json()
            items = dz_r.get("data", [])
            if items:
                item = items[0]
                if not result["album"]: result["album"] = item.get("album", {}).get("title", "")
                if not result["cover_url"]: result["cover_url"] = item.get("album", {}).get("cover_xl") or item.get("album", {}).get("cover_big", "")
        except Exception:
            pass

    if result.get("cover_url"):
        try:
            cov_res = requests.get(result["cover_url"], timeout=5)
            if cov_res.status_code == 200:
                c_mime = cov_res.headers.get("Content-Type", "image/jpeg")
                result["cover_data_uri"] = f"data:{c_mime};base64,{base64.b64encode(cov_res.content).decode('ascii')}"
        except Exception:
            pass

    return result
