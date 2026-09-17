#!/usr/bin/env python3
"""
sonance.py - Unified Main Launcher for Sonance

The ultimate unified music suite — Stream, download Hi-Res lossless, and sing along with real-time synced lyrics.
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause
https://github.com/Sandeep2062/Sonance
"""

import sys
import argparse
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

  if args.classic:
    print("[*] Launching Sonance (Classic Tkinter UI)...")
    import lyrics_downloader_ultimate
  else:
    print("[*] Starting Sonance Music Platform...")
    # Attempt Discord RPC connection in background
    try:
      discord_rpc.rpc_manager.connect()
    except Exception:
      pass

    modern_lyrics_downloader.main()


if __name__ == "__main__":
  main()
