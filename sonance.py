#!/usr/bin/env python3
"""
sonance.py - Unified Main Launcher for Sonance

The ultimate unified music suite — Stream, download Hi-Res lossless, and sing along with real-time synced lyrics.
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause
https://github.com/Sandeep2062/Sonance
"""

import sys
import argparse

if sys.platform == "win32":
  try:
    if hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
      sys.stderr.reconfigure(encoding="utf-8")
  except Exception:
    pass

import modern_lyrics_downloader
import cookie_manager
import discord_rpc


def main():
  parser = argparse.ArgumentParser(
      description="Sonance - The Ultimate All-in-One Music Platform",
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
Examples:
  python sonance.py                 # Launch modern desktop application (Default)
  python sonance.py --classic       # Launch classic tkinter GUI
  python sonance.py --extract-cookies chrome  # Extract cookies from Chrome
  python sonance.py --extract-cookies edge    # Extract cookies from Microsoft Edge
        """,
  )

  parser.add_argument(
      "--classic",
      action="store_true",
      help="Launch the classic lightweight tkinter interface",
  )
  parser.add_argument(
      "--extract-cookies",
      metavar="BROWSER",
      choices=["chrome", "edge", "firefox", "brave", "opera"],
      help="Extract YouTube and platform cookies from installed browser",
  )
  parser.add_argument(
      "--check-update",
      action="store_true",
      help="Check GitHub for latest release updates",
  )
  parser.add_argument(
      "--clear-cache",
      action="store_true",
      help="Clear local offline and stream audio cache",
  )
  parser.add_argument(
      "--inspect-tags",
      metavar="AUDIO_FILE",
      help="Inspect metadata tags & cover art of an audio file",
  )
  parser.add_argument(
      "--doctor",
      metavar="FOLDER",
      nargs="?",
      const=".",
      help="Scan music library with Sonance Library Doctor to detect duplicates & health score",
  )
  parser.add_argument(
      "--remote",
      action="store_true",
      help="Start embedded Wi-Fi mobile remote web server on launch",
  )
  parser.add_argument(
      "--smart-playlists",
      metavar="FOLDER",
      nargs="?",
      const=".",
      help="List smart dynamic playlists and track counts for FOLDER",
  )
  parser.add_argument(
      "--stats",
      action="store_true",
      help="Display local listening habits, top artists, and Sonance Wrapped stats",
  )
  parser.add_argument(
      "--transcode",
      nargs="+",
      metavar="PARAM",
      help="Batch convert audio files: --transcode <source> [output_dir] [format] [bitrate]",
  )
  parser.add_argument(
      "--identify",
      metavar="AUDIO_FILE",
      help="Identify an unknown audio file via acoustic fingerprints & catalog matching",
  )
  parser.add_argument(
      "--discography",
      metavar="ARTIST_NAME",
      help="Inspect complete album discography and tracklists for an artist",
  )
  parser.add_argument(
      "--cue-split",
      nargs="+",
      metavar="PARAM",
      help="Split CUE sheet album image: --cue-split <cue_file> [output_dir] [format] [bitrate]",
  )
  parser.add_argument(
      "--trim",
      nargs="+",
      metavar="PARAM",
      help="Trim audio clip: --trim <audio_file> <start_sec> <end_sec> [output_format] [output_file]",
  )
  parser.add_argument(
      "--version",
      action="version",
      version=f"Sonance v{modern_lyrics_downloader.APP_VERSION}",
  )

  args = parser.parse_args()

  if args.extract_cookies:
    print(
        f"[*] Extracting cookies from {args.extract_cookies.capitalize()}..."
    )
    res = cookie_manager.extract_cookies_from_browser(args.extract_cookies)
    if res.get("success"):
      print(f"[+] Success: {res.get('message')}")
    else:
      print(f"[-] Failed: {res.get('message') or res.get('error')}")
    return

  if args.check_update:
    api = modern_lyrics_downloader.LyricsAPI()
    res = api.check_for_updates()
    if res.get("update_available"):
      print(
          f"[+] New update available: v{res.get('latest_version')} (Current:"
          f" v{res.get('current_version')})"
      )
      print(f"[+] Download: {res.get('download_url')}")
    else:
      print(
          f"[*] Sonance is up to date (v{modern_lyrics_downloader.APP_VERSION})."
      )
    return

  if args.clear_cache:
    import cache_manager
    ok = cache_manager.clear_cache()
    print("[+] Stream cache cleared successfully." if ok else "[-] Failed to clear cache.")
    return

  if args.inspect_tags:
    import tag_editor
    tags = tag_editor.read_tags(args.inspect_tags)
    print(f"[*] Metadata for: {args.inspect_tags}")
    for k, v in tags.items():
      if k != "cover_data_uri":
        print(f"  {k}: {v}")
    return

  if args.doctor is not None:
    import library_doctor
    folder = args.doctor or "."
    print(f"[*] Running Sonance Library Doctor on: {folder}")
    res = library_doctor.scan_library_health(folder)
    if not res.get("success"):
      print(f"[-] Error: {res.get('error')}")
      return
    print(f"[+] Total Tracks Scanned: {res['total_tracks']}")
    print(f"[+] Library Health Score: {res['health_score']}%")
    print(f"[+] Missing Lyrics (.lrc): {res['missing_lyrics_count']}")
    print(f"[+] Missing Tags: {res['missing_tags_count']}")
    print(f"[+] Duplicate Groups Found: {res['total_duplicate_groups']} ({res['total_duplicate_files']} redundant files)")
    if res['duplicate_groups']:
      print("\n--- Duplicate Groups Detected ---")
      for g in res['duplicate_groups'][:10]:
        print(f"  * {g['artist']} - {g['title']} ({g['count']} files)")
        for tr in g['tracks']:
          status = "[RECOMMENDED KEEP]" if tr['is_recommended_keep'] else "[DUPLICATE]"
          print(f"    - {status} {tr['filename']} ({tr['quality']}, {tr['size_mb']}MB)")
    return

  if args.smart_playlists is not None:
    import smart_playlists
    folder = args.smart_playlists or "."
    print(f"[*] Scanning smart dynamic playlists in: {folder}")
    lists = smart_playlists.get_smart_playlists(folder)
    print("\n=== Sonance Smart Playlists ===")
    for p in lists:
      print(f"  {p['icon']} {p['name']} ({p['count']} tracks)")
      print(f"     Description: {p['description']}")
    return

  if args.stats:
    import listening_stats
    st = listening_stats.get_listening_stats()
    print("\n=== 🎵 Sonance Wrapped & Listening Stats ===")
    print(f"  Total Tracks Played: {st['total_plays']}")
    print(f"  Total Listening Time: {st['total_hours']} hours ({st['total_minutes']} mins)")
    print(f"  Active Listening Days: {st['active_days']} (Streak: {st['current_streak']} days)")
    
    bd = st['format_breakdown']
    print(f"\n  Audio Quality Breakdown:")
    print(f"    - Lossless (FLAC/WAV/ALAC): {bd['lossless']}%")
    print(f"    - High-Bitrate (320k MP3): {bd['mp3_320']}%")
    print(f"    - Online Streams: {bd['streaming']}%")

    if st['top_artists']:
      print("\n  ⭐ Top 5 Artists:")
      for i, a in enumerate(st['top_artists'], 1):
        print(f"    {i}. {a['artist']} ({a['plays']} plays)")

    if st['top_tracks']:
      print("\n  🎧 Top 5 Tracks:")
      for i, t in enumerate(st['top_tracks'][:5], 1):
        print(f"    {i}. {t['track']} ({t['plays']} plays)")
    print()
    return

  if args.transcode:
    import audio_transcoder
    src = args.transcode[0]
    out = args.transcode[1] if len(args.transcode) > 1 else src
    fmt = args.transcode[2] if len(args.transcode) > 2 else "mp3"
    bitrate = args.transcode[3] if len(args.transcode) > 3 else "320k"

    print(f"[*] Sonance Audio Batch Transcoder: {src} -> {out} [{fmt.upper()} {bitrate}]")
    if os.path.isfile(src):
      files = [src]
    elif os.path.isdir(src):
      exts = (".mp3", ".flac", ".wav", ".m4a", ".ogg")
      files = [os.path.join(src, f) for f in os.listdir(src) if f.lower().endswith(exts)]
    else:
      print(f"[-] Source path not found: {src}")
      return

    print(f"[*] Converting {len(files)} audio tracks...")
    res = audio_transcoder.batch_transcode(files, fmt, bitrate, out)
    print(f"[+] Transcode Complete: {res['success_count']} succeeded, {res['fail_count']} failed.")
    return

  if args.identify:
    import audio_fingerprint
    print(f"[*] Identifying audio file: {args.identify}...")
    res = audio_fingerprint.identify_track(args.identify)
    if res.get("success"):
      t = res["track"]
      print(f"[+] Recognized Track: {t.get('title')} - {t.get('artist')}")
      print(f"    Album: {t.get('album')} ({t.get('year')})")
      print(f"    Genre: {t.get('genre') or 'Unknown'} | Track #{t.get('track_number')}")
      print(f"    Confidence: {int(t.get('confidence', 0) * 100)}% ({t.get('source')})")
      if t.get("cover_url"):
        print(f"    Cover Art: {t.get('cover_url')}")
    else:
      print(f"[-] Identification failed: {res.get('error')}")
    return

  if args.discography:
    import discography_scraper
    print(f"[*] Fetching discography for '{args.discography}'...")
    res = discography_scraper.get_full_discography(args.discography)
    if res.get("success"):
      art = res["artist"]
      print(f"\n=== 📚 Discography: {art['name']} ({res['total_albums']} albums found) ===")
      for alb in res["albums"]:
        print(f"\n  💿 {alb['title']} [{alb['type']}] ({alb['year']}) - {len(alb.get('tracks', []))} tracks")
        for trk in alb.get("tracks", []):
          print(f"     {trk['track_number']:02d}. {trk['title']} ({trk['duration_str']})")
      print()
    else:
      print(f"[-] Failed: {res.get('error')}")
  if args.cue_split:
    import cue_splitter
    cue_file = args.cue_split[0]
    out_dir = args.cue_split[1] if len(args.cue_split) > 1 else None
    out_fmt = args.cue_split[2] if len(args.cue_split) > 2 else "flac"
    out_bitrate = args.cue_split[3] if len(args.cue_split) > 3 else "320k"

    print(f"[*] Parsing CUE Sheet: {cue_file}")
    res = cue_splitter.split_cue_sheet(cue_file, output_dir=out_dir, output_format=out_fmt, bitrate=out_bitrate)
    if res.get("success"):
      print(f"[+] CUE Split Succeeded! Processed {res.get('track_count', 0)} tracks into: {res.get('output_directory')}")
      for t in res.get("tracks", []):
        print(f"    Track {t.get('track_number'):02d}: {t.get('title')} ({t.get('duration_str')}) -> {os.path.basename(t.get('file', ''))}")
    else:
      print(f"[-] CUE Split failed: {res.get('error')}")
    return

  if args.trim:
    import audio_cutter
    src = args.trim[0]
    try:
      start_sec = float(args.trim[1])
      end_sec = float(args.trim[2])
    except (IndexError, ValueError):
      print("[-] Error: start_sec and end_sec must be valid numeric seconds.")
      return
    out_fmt = args.trim[3] if len(args.trim) > 3 else "mp3"
    out_file = args.trim[4] if len(args.trim) > 4 else None

    print(f"[*] Trimming audio: {src} [{start_sec}s -> {end_sec}s] to format: {out_fmt.upper()}")
    res = audio_cutter.trim_audio_clip(src, start_sec, end_sec, output_format=out_fmt, output_path=out_file)
    if res.get("success"):
      print(f"[+] Audio clip exported successfully: {res.get('output_path')} ({res.get('duration')}s)")
    else:
      print(f"[-] Audio trimming failed: {res.get('error')}")
    return

  if args.classic:
    print("[*] Launching Sonance (Classic Tkinter UI)...")
    import lyrics_downloader_ultimate
  else:
    print("[*] Starting Sonance Music Platform...")
    if args.remote:
      import remote_server
      res = remote_server.remote_server.start()
      if res.get("success"):
        print(f"[+] Wi-Fi Mobile Remote active: {res.get('url')}")

    # Attempt Discord RPC connection in background
    try:
      discord_rpc.rpc_manager.connect()
    except Exception:
      pass

    modern_lyrics_downloader.main()


if __name__ == "__main__":
  main()
