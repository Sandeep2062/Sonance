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
