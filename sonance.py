#!/usr/bin/env python3
"""
sonance.py - Unified Main Launcher for Sonance

The ultimate unified music suite — Stream, download Hi-Res lossless, and sing along with real-time synced lyrics.
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause
https://github.com/Sandeep2062/Sonance
"""

import os
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
      "--scan-loudness",
      nargs="+",
      metavar="PARAM",
      help="Analyze audio loudness & ReplayGain: --scan-loudness <file_or_dir> [--apply-tags] [--target-lufs <lufs>]",
  )
  parser.add_argument(
      "--dedup",
      metavar="FOLDER",
      help="Detect cross-format audio duplicates and identify best lossless copies",
  )
  parser.add_argument(
      "--rip-cd",
      nargs="*",
      metavar="PARAM",
      help="Rip Audio CD tracks: --rip-cd [drive_letter] [output_dir] [format]",
  )
  parser.add_argument(
      "--cloud-stream",
      nargs="+",
      metavar="PARAM",
      help="Stream from Subsonic/Navidrome server: --cloud-stream <server_url> <username> [password]",
  )
  parser.add_argument(
      "--convert-playlist",
      nargs="+",
      metavar="PARAM",
      help="Convert playlist: --convert-playlist <input_file_or_url> [output_format] [output_file]",
  )
  parser.add_argument(
      "--split-stems",
      nargs="+",
      metavar="PARAM",
      help="Separate audio file into stems: --split-stems <audio_file> [output_dir] [2stems|4stems] [format]",
  )
  parser.add_argument(
      "--audit",
      metavar="FILE_OR_DIR",
      help="Audit lossless audio authenticity & detect fake upscaled MP3 files",
  )
  parser.add_argument(
      "--analyze-key",
      metavar="AUDIO_FILE",
      help="Analyze track BPM tempo, musical key, and Camelot DJ wheel mixing code",
  )
  parser.add_argument(
      "--resample",
      nargs="+",
      metavar="PARAM",
      help="Resample audio file: --resample <audio_file> <sample_rate> [bit_depth] [output_file]",
  )
  parser.add_argument(
      "--pitch-shift",
      nargs="+",
      metavar="PARAM",
      help="Transpose audio key: --pitch-shift <audio_file> <semitones> [output_file]",
  )
  parser.add_argument(
      "--organize",
      nargs="+",
      metavar="PARAM",
      help="Organize music library: --organize <folder> [--pattern \"<pattern>\"] [--execute] [--copy]",
  )
  parser.add_argument(
      "--pack-album",
      nargs="+",
      metavar="PARAM",
      help="Pack loose album tracks into monolithic FLAC: --pack-album <folder> [output_flac]",
  )
  parser.add_argument(
      "--unpack-album",
      nargs="+",
      metavar="PARAM",
      help="Unpack monolithic FLAC into individual tracks: --unpack-album <monolithic_flac> [output_dir]",
  )
  parser.add_argument(
      "--dr-meter",
      metavar="FILE_OR_DIR",
      help="Measure official TT Dynamic Range and Crest Factor (Pleasurize Music Foundation DR4-DR18+)",
  )
  parser.add_argument(
      "--sync-device",
      nargs="+",
      metavar="PARAM",
      help="Sync music to portable DAP/USB device: --sync-device <target_path> <source_dir> [--mode copy|mp3_320] [--playlist <name>]",
  )
  parser.add_argument(
      "--loop",
      nargs="+",
      metavar="PARAM",
      help="Create seamless A-B phrase practice loop: --loop <audio_file> <start_sec> <end_sec> [repeats] [--count-in] [output_file]",
  )
  parser.add_argument(
      "--align-words",
      nargs="+",
      metavar="PARAM",
      help="Generate Enhanced Word-by-Word ELRC lyrics: --align-words <lrc_file> [audio_file] [output_elrc]",
  )
  parser.add_argument(
      "--autoeq",
      nargs="?",
      const="list",
      metavar="HEADPHONE_OR_FILE",
      help="Inspect or apply Headphone AutoEq Harman 2020 calibration profiles: --autoeq [model_name|custom.txt]",
  )
  parser.add_argument(
      "--verify-flac",
      metavar="FILE_OR_DIR",
      help="Audit lossless FLAC stream MD5 checksums to detect bit rot or corrupted files",
  )
  parser.add_argument(
      "--automix",
      nargs="+",
      metavar="PARAM",
      help="Generate continuous harmonic DJ mix: --automix <track1> <track2> ... [--transition <sec>] [--output <file>]",
  )
  parser.add_argument(
      "--fetch-lyrics",
      nargs="+",
      metavar="PARAM",
      help="Search multi-provider synchronized lyrics: --fetch-lyrics <artist> <title> [--romanize] [output.lrc]",
  )
  parser.add_argument(
      "--batch-lyrics",
      nargs="+",
      metavar="PARAM",
      help="Batch download missing companion .lrc lyrics for library folder: --batch-lyrics <folder> [--overwrite]",
  )
  parser.add_argument(
      "--inspect-stream",
      metavar="AUDIO_FILE",
      help="Deep inspection of audio bitstream, container, and encoder: --inspect-stream <file>",
  )
  parser.add_argument(
      "--restore-audio",
      nargs="+",
      metavar="PARAM",
      help="Restore analog vinyl/tape audio (declick, dehum, rumble, dehiss): --restore-audio <input> [output] [--dehum 50|60]",
  )
  parser.add_argument(
      "--migrate-library",
      nargs="+",
      metavar="PARAM",
      help="Migrate iTunes / MusicBee library XML & playlists: --migrate-library <xml_file> [--target-dir <dir>]",
  )
  parser.add_argument(
      "--translate-lyrics",
      nargs="+",
      metavar="PARAM",
      help="Translate synchronized lyrics to bilingual subtitles: --translate-lyrics <lrc_file> <target_lang> [output_file]",
  )
  parser.add_argument(
      "--accuraterip",
      metavar="FILE_OR_DIR",
      help="Audit CD rip audio against AccurateRip CRCv1, CRCv2 and scan drive offsets: --accuraterip <file_or_dir>",
  )
  parser.add_argument(
      "--heal-playlist",
      nargs="+",
      metavar="PARAM",
      help="Heal broken playlist links & upgrade to lossless: --heal-playlist <playlist> [--library-dir <dir>] [--lossless]",
  )
  parser.add_argument(
      "--spatial-8d",
      nargs="+",
      metavar="PARAM",
      help="Render 360-degree binaural 8D spatial audio master: --spatial-8d <input_file> [output_file] [--orbit <sec>] [--depth <float>]",
  )
  parser.add_argument(
      "--normalize-gain",
      nargs="+",
      metavar="PARAM",
      help="ReplayGain 2.0 & True-Peak loudness normalizer: --normalize-gain <file_or_dir> [--mode tag|hard] [--target-lufs <float>]",
  )
  parser.add_argument(
      "--parametric-eq",
      nargs="+",
      metavar="PARAM",
      help="Process audio with 5-band parametric master EQ: --parametric-eq <input> [output]",
  )
  parser.add_argument(
      "--phase-meter",
      nargs="+",
      metavar="PARAM",
      help="Analyze stereo phase correlation & correct anti-phase: --phase-meter <audio_file> [--correct]",
  )
  parser.add_argument(
      "--test-tone",
      nargs="+",
      metavar="PARAM",
      help="Generate DAC bit-perfect test audio: --test-tone <sweep|imd_smpte|imd_ccif|jtest|pink_noise|digital_black> [output] [--rate 96000] [--bits 24] [--dur 10]",
  )
  parser.add_argument(
      "--retime-lyrics",
      nargs="+",
      metavar="PARAM",
      help="Recalibrate drifting lyrics sync: --retime-lyrics <lrc_file> <t1_old> <t1_new> <t2_old> <t2_new> [output_lrc]",
  )
  parser.add_argument(
      "--spectrum",
      nargs="+",
      metavar="PARAM",
      help="Analyze audio frequency spectrum & genuine Hi-Res bandwidth: --spectrum <audio_file> [--max-sec 60]",
  )
  parser.add_argument(
      "--declip",
      nargs="+",
      metavar="PARAM",
      help="Repair digital clipping & expand dynamic range: --declip <audio_file> [output_file] [--expansion 2.0] [--headroom 4.0]",
  )
  parser.add_argument(
      "--auto-split",
      nargs="+",
      metavar="PARAM",
      help="Split continuous audio by silence gaps & generate CUE: --auto-split <audio_file> [output_dir] [--threshold -42.0] [--min-silence 1.5]",
  )
  parser.add_argument(
      "--lyrics-video",
      nargs="+",
      metavar="PARAM",
      help="Generate animated synchronized lyrics karaoke video: --lyrics-video <audio_file> [lrc_file] [output_video] [--resolution 1080p|720p]",
  )
  parser.add_argument(
      "--upsample",
      nargs="+",
      metavar="PARAM",
      help="Audiophile polyphase sinc upsampler: --upsample <audio_file> [output_file] [--rate 192000] [--filter linear|minimum]",
  )
  parser.add_argument(
      "--fix-cue",
      nargs="+",
      metavar="PARAM",
      help="Audit & repair broken CUE sheets: --fix-cue <cue_file> [target_audio] [--output <repaired_cue>]",
  )
  parser.add_argument(
      "--synthesize-ir",
      nargs="+",
      metavar="PARAM",
      help="Synthesize room acoustic impulse response (IR): --synthesize-ir [output_wav] [--preset studio|room|concert_hall|cathedral] [--rt60 1.5] [--sr 48000]",
  )
  parser.add_argument(
      "--lrc-to-ass",
      nargs="+",
      metavar="PARAM",
      help="Convert LRC to animated karaoke ASS subtitles: --lrc-to-ass <lrc_file> [output_ass] [--style karaoke|minimal|cinematic] [--color #FFD700] [--srt]",
  )
  parser.add_argument(
      "--version",
      action="version",
      version=f"Sonance v{modern_lyrics_downloader.APP_VERSION}",
  )

  args, unknown = parser.parse_known_args()

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

  if args.scan_loudness:
    import loudness_scanner
    target_path = args.scan_loudness[0]
    apply_tags = "--apply-tags" in args.scan_loudness
    target_lufs = -14.0
    for i, p in enumerate(args.scan_loudness):
      if p == "--target-lufs" and i + 1 < len(args.scan_loudness):
        try:
          target_lufs = float(args.scan_loudness[i + 1])
        except ValueError:
          pass

    print(f"[*] Sonance Loudness & ReplayGain Scanner: {target_path} (Target: {target_lufs} LUFS)")
    if os.path.isfile(target_path):
      res = loudness_scanner.scan_file_loudness(target_path, target_lufs=target_lufs, apply_tags=apply_tags)
      if res.get("success"):
        print(f"[+] Integrated Loudness: {res['integrated_lufs']} LUFS | True Peak: {res['true_peak_dbfs']} dBFS")
        print(f"    Recommended Track Gain: {res['track_gain_str']} (Peak ratio: {res['track_peak_ratio']})")
        if apply_tags:
          print(f"    Tags Applied: {'Yes' if res.get('tags_applied') else 'Failed'}")
      else:
        print(f"[-] Failed: {res.get('error')}")
    elif os.path.isdir(target_path):
      exts = (".mp3", ".flac", ".wav", ".m4a", ".ogg")
      files = [os.path.join(target_path, f) for f in os.listdir(target_path) if f.lower().endswith(exts)]
      res = loudness_scanner.scan_batch_loudness(files, target_lufs=target_lufs, apply_tags=apply_tags)
      if res.get("success"):
        print(f"[+] Processed {res['total_tracks']} tracks | Album Integrated Loudness: {res['album_integrated_lufs']} LUFS")
        print(f"    Recommended Album Gain: {res['album_gain_str']} | Max True Peak Ratio: {res['album_peak_ratio']}")
        for t in res.get("tracks", []):
          print(f"    - {t['filename']}: {t['integrated_lufs']} LUFS -> Gain: {t['track_gain_str']}")
        if apply_tags:
          print(f"    [+] Successfully embedded ReplayGain tags into {res.get('tags_applied_count')} tracks.")
      else:
        print(f"[-] Failed: {res.get('error')}")
    else:
      print(f"[-] Path not found: {target_path}")
    return

  if args.dedup:
    import audio_dedup
    folder = args.dedup
    print(f"[*] Scanning for cross-format audio duplicates in: {folder}...")
    res = audio_dedup.scan_for_duplicates(folder)
    if res.get("success"):
      print(f"[+] Scanned {res['scanned_count']} tracks. Found {res['duplicate_groups_count']} duplicate groups ({res['total_redundant_files']} redundant files).")
      print(f"    Potential space to reclaim: {res['potential_space_freed_mb']} MB\n")
      for group in res.get("duplicate_sets", []):
        k = group["keeper"]
        print(f"  🎵 {group['song']}")
        print(f"     ⭐ Best (Keeper): {k['filename']} [{k['format']} {k['bitrate']}k] Score: {k['quality_score']}")
        for d in group["duplicates"]:
          print(f"     🗑️ Duplicate:    {d['filename']} [{d['format']} {d['bitrate']}k] Score: {d['quality_score']}")
        print()
    else:
      print(f"[-] Failed: {res.get('error')}")
    return

  if args.rip_cd is not None:
    import cd_ripper
    drive = args.rip_cd[0] if len(args.rip_cd) > 0 else "D:"
    out_dir = args.rip_cd[1] if len(args.rip_cd) > 1 else None
    fmt = args.rip_cd[2] if len(args.rip_cd) > 2 else "flac"
    print(f"[*] Attempting to rip Audio CD from drive {drive} [{fmt.upper()}]...")
    res = cd_ripper.rip_audio_cd(drive, output_dir=out_dir, output_format=fmt)
    if res.get("success"):
      print(f"[+] Success: {res.get('message')}")
      for t in res.get("tracks", []):
        print(f"    - Track {t.get('track')}: {t.get('file')}")
    else:
      print(f"[-] CD Rip: {res.get('error')}")
    return

  if args.cloud_stream:
    import cloud_streamer
    url = args.cloud_stream[0]
    user = args.cloud_stream[1] if len(args.cloud_stream) > 1 else "admin"
    pw = args.cloud_stream[2] if len(args.cloud_stream) > 2 else ""
    print(f"[*] Connecting to Personal Cloud Music Server: {url} as '{user}'...")
    res = cloud_streamer.test_connection(url, user, pw)
    if res.get("success"):
      print(f"[+] Connected to {res.get('type')} (Server v{res.get('server_version')}, API v{res.get('api_version')})")
      artists_res = cloud_streamer.get_artists(url, user, pw)
      if artists_res.get("success"):
        print(f"    Total Artists Indexed: {artists_res.get('count')}")
    else:
      print(f"[-] Cloud connection failed: {res.get('error')}")
    return

  if args.convert_playlist:
    import playlist_converter
    inp = args.convert_playlist[0]
    out_fmt = args.convert_playlist[1] if len(args.convert_playlist) > 1 else "m3u8"
    out_file = args.convert_playlist[2] if len(args.convert_playlist) > 2 else None
    print(f"[*] Converting playlist: {inp} -> {out_fmt.upper()}...")
    res = playlist_converter.convert_playlist(inp, out_fmt, out_file)
    if res.get("success"):
      print(f"[+] Successfully converted {res.get('track_count')} tracks to {res.get('format')} playlist:")
      print(f"    Saved: {res.get('output_file')}")
    else:
      print(f"[-] Playlist conversion failed: {res.get('error')}")
    return

  if args.split_stems:
    import vocal_separator
    audio_file = args.split_stems[0]
    out_dir = args.split_stems[1] if len(args.split_stems) > 1 and args.split_stems[1] not in ["2stems", "4stems", "wav", "mp3", "flac", "m4a"] else None
    mode = "4stems" if "4stems" in args.split_stems else "2stems"
    fmt = "flac"
    for p in args.split_stems[1:]:
      if p in ["wav", "mp3", "flac", "m4a"]:
        fmt = p
        break
    print(f"[*] Separating stems for {audio_file} (Mode: {mode.upper()}, Format: {fmt.upper()})...")
    res = vocal_separator.separate_stems(audio_file, out_dir, mode, fmt)
    if res.get("success"):
      print(f"[+] Successfully separated stems to: {res.get('output_dir')}")
      for stem_name, path in res.get("stems", {}).items():
        print(f"    • {stem_name.capitalize()}: {os.path.basename(path)}")
    else:
      print(f"[-] Stem separation failed: {res.get('error')}")
    return

  if args.audit:
    import audio_auditor
    target = args.audit
    if os.path.isdir(target):
      print(f"[*] Batch auditing audio authenticity in folder: {target}...")
      res = audio_auditor.audit_directory(target)
      if res.get("success"):
        print(f"[+] Scanned {res.get('total_scanned')} lossless files:")
        print(f"    • Genuine Lossless: {res.get('genuine_count')}")
        print(f"    • Fake / Upscaled:  {res.get('fake_count')}")
        for f in res.get("files", []):
          icon = "[+]" if "genuine" in f.get("verdict_category", "") else "[-]"
          print(f"    {icon} {f.get('filename')}: {f.get('verdict_label')} (Cutoff: {f.get('cutoff_frequency_hz')} Hz)")
      else:
        print(f"[-] Audit failed: {res.get('error')}")
    else:
      print(f"[*] Auditing audio authenticity for: {target}...")
      res = audio_auditor.audit_file(target)
      if res.get("success"):
        print(f"[+] Verdict: {res.get('verdict_label')} (Score: {res.get('authenticity_score', 95)}/100)")
        print(f"    • Cutoff Frequency: {res.get('cutoff_frequency_hz')} Hz")
        print(f"    • Nyquist Limit:    {res.get('nyquist_hz')} Hz")
        print(f"    • Analysis:         {res.get('notes')}")
      else:
        print(f"[-] Audit failed: {res.get('error')}")
    return

  if args.analyze_key:
    import dj_mixer
    audio_file = args.analyze_key
    print(f"[*] Analyzing BPM tempo & Camelot harmonic key for: {audio_file}...")
    res = dj_mixer.analyze_track_bpm_and_key(audio_file)
    if res.get("success"):
      print(f"[+] Track:   {res.get('filename')}")
      print(f"[+] Tempo:   {res.get('bpm')} BPM")
      print(f"[+] Key:     {res.get('key')} [{res.get('camelot_full')}] (Confidence: {res.get('confidence')*100:.0f}%)")
      print("[*] Harmonically Compatible DJ Transition Keys:")
      for k in res.get("compatible_keys", []):
        print(f"    • {k['camelot']} ({k['key']}) -> {k['relation']}")
    else:
      print(f"[-] Key analysis failed: {res.get('error')}")
    return

  if args.resample:
    import audio_resampler
    inp = args.resample[0]
    rate = int(args.resample[1]) if len(args.resample) > 1 else 96000
    bd = int(args.resample[2]) if len(args.resample) > 2 and args.resample[2] in ["16", "24", "32"] else 24
    out = args.resample[3] if len(args.resample) > 3 else None
    print(f"[*] Resampling {inp} to {rate} Hz ({bd}-bit)...")
    res = audio_resampler.resample_audio_file(inp, rate, bd, out)
    if res.get("success"):
      print(f"[+] Resampled audio saved to: {res.get('output_file')} (Engine: {res.get('engine')})")
    else:
      print(f"[-] Resampling failed: {res.get('error')}")
    return

  if args.pitch_shift:
    import pitch_shifter
    inp = args.pitch_shift[0]
    semi = float(args.pitch_shift[1]) if len(args.pitch_shift) > 1 else 0.0
    out = args.pitch_shift[2] if len(args.pitch_shift) > 2 else None
    print(f"[*] Shifting pitch for {inp} by {semi:+g} semitones...")
    res = pitch_shifter.shift_pitch_file(inp, semi, out)
    if res.get("success"):
      print(f"[+] Transposed audio saved: {res.get('output_file')} (Shift ratio: {res.get('key_shift_ratio')})")
    else:
      print(f"[-] Pitch shift failed: {res.get('error')}")
    return

  if args.organize:
    import library_organizer
    folder = args.organize[0]
    pat = library_organizer.DEFAULT_ORGANIZER_PATTERN
    execute_flag = "--execute" in args.organize
    copy_flag = "--copy" in args.organize
    for i, a in enumerate(args.organize):
      if a == "--pattern" and i + 1 < len(args.organize):
        pat = args.organize[i + 1]

    if not execute_flag:
      print(f"[*] Previewing library organization for: {folder} (Pattern: {pat})...")
      res = library_organizer.preview_library_organization(folder, pat)
      if res.get("success"):
        print(f"[+] Found {res.get('total_tracks')} tracks ({res.get('tracks_to_move')} to move, {res.get('unchanged_tracks')} unchanged):")
        for item in res.get("preview_items", [])[:10]:
          print(f"    • {item['filename']} -> {item['new_rel_path']}")
        if len(res.get("preview_items", [])) > 10:
          print(f"    ... and {len(res.get('preview_items', [])) - 10} more tracks.")
        print("[*] To apply these changes on disk, run with --execute (or add --copy to preserve sources).")
      else:
        print(f"[-] Preview failed: {res.get('error')}")
    else:
      mode_str = "copying" if copy_flag else "moving"
      print(f"[*] Organizing library tracks in {folder} ({mode_str})...")
      res = library_organizer.execute_library_organization(folder, pat, copy_mode=copy_flag)
      if res.get("success"):
        print(f"[+] Successfully organized {res.get('success_count')} tracks (Mode: {res.get('mode')}).")
      else:
        print(f"[-] Organization failed: {res.get('error')}")
    return

  if args.pack_album:
    import album_packer
    folder = args.pack_album[0]
    out = args.pack_album[1] if len(args.pack_album) > 1 else None
    print(f"[*] Packing album from {folder} into monolithic FLAC/CUE...")
    res = album_packer.pack_album(folder, out)
    if res.get("success"):
      print(f"[+] Successfully packed {res.get('total_tracks')} tracks:")
      print(f"    • Master Audio: {res.get('output_audio')}")
      print(f"    • CUE Sheet:    {res.get('output_cue')}")
    else:
      print(f"[-] Packing failed: {res.get('error')}")
    return

  if args.unpack_album:
    import album_packer
    alb_file = args.unpack_album[0]
    out_d = args.unpack_album[1] if len(args.unpack_album) > 1 else None
    print(f"[*] Unpacking monolithic album: {alb_file}...")
    res = album_packer.unpack_album(alb_file, output_dir=out_d)
    if res.get("success"):
      print(f"[+] Successfully extracted {res.get('tracks_extracted')} tracks to: {res.get('output_dir')}")
    else:
      print(f"[-] Unpacking failed: {res.get('error')}")
    return

  if args.dr_meter:
    import dr_meter
    target = args.dr_meter
    if os.path.isdir(target):
      print(f"[*] Measuring Album Dynamic Range for: {target}...")
      res = dr_meter.analyze_album_dynamic_range(target)
      if res.get("success"):
        print(res["report_text"])
      else:
        print(f"[-] DR analysis failed: {res.get('error')}")
    else:
      print(f"[*] Measuring Track Dynamic Range for: {target}...")
      res = dr_meter.analyze_track_dynamic_range(target)
      if res.get("success"):
        print(f"[+] File:          {res['filename']}")
        print(f"[+] Dynamic Range: {res['dr_badge']} ({res['tier']} - {res['rating']})")
        print(f"[+] Peak Level:    {res['peak_db']} dBFS")
        print(f"[+] Total RMS:     {res['rms_db']} dBFS")
        print(f"[+] Crest Factor:  {res['crest_factor_db']} dB")
        print(f"[+] Summary:       {res['description']}")
      else:
        print(f"[-] DR analysis failed: {res.get('error')}")
    return

  if args.sync_device:
    import device_sync
    if len(args.sync_device) < 2:
      print("[-] Error: --sync-device requires <target_dir> and <source_dir_or_file>.")
      return
    target = args.sync_device[0]
    source = args.sync_device[1]
    mode = "copy"
    pl_name = "Sonance Sync"
    idx = 2
    while idx < len(args.sync_device):
      if args.sync_device[idx] == "--mode" and idx + 1 < len(args.sync_device):
        mode = args.sync_device[idx + 1]
        idx += 2
      elif args.sync_device[idx] == "--playlist" and idx + 1 < len(args.sync_device):
        pl_name = args.sync_device[idx + 1]
        idx += 2
      else:
        idx += 1

    tracks_to_sync = []
    if os.path.isdir(source):
      for root, _, files in os.walk(source):
        for f in sorted(files):
          if os.path.splitext(f)[1].lower() in device_sync.AUDIO_EXTS:
            tracks_to_sync.append(os.path.join(root, f))
    elif os.path.isfile(source):
      tracks_to_sync.append(source)

    print(f"[*] Syncing {len(tracks_to_sync)} tracks to portable storage {target} (Mode: {mode})...")
    res = device_sync.sync_tracks_to_device(
        tracks_to_sync,
        target,
        playlist_name=pl_name,
        transcode_mode=mode,
        progress_callback=lambda c, t, f: print(f"    [{c}/{t}] Syncing: {f}"),
    )
    if res.get("success"):
      print(f"[+] Successfully synced {res.get('total_synced')}/{res.get('total_requested')} tracks.")
      print(f"[+] Synced Companion Lyrics (.lrc): {res.get('lyrics_copied')}")
      if res.get("playlist_file"):
        print(f"[+] Created Device Playlist: {res.get('playlist_file')}")
    else:
      print(f"[-] Sync failed: {res.get('error')}")
    return

  if args.loop:
    import ab_looper
    if len(args.loop) < 3:
      print("[-] Error: --loop requires <audio_file> <start_sec> <end_sec>.")
      return
    audio_f = args.loop[0]
    start_s = float(args.loop[1])
    end_s = float(args.loop[2])
    rep = 4
    count_in = False
    out_f = None
    idx = 3
    while idx < len(args.loop):
      a = args.loop[idx]
      if a == "--count-in":
        count_in = True
      elif a.isdigit():
        rep = int(a)
      elif not out_f:
        out_f = a
      idx += 1

    print(f"[*] Rendering A-B loop for {audio_f} [{start_s}s -> {end_s}s] ({rep} repeats)...")
    res = ab_looper.create_ab_loop(audio_f, start_s, end_s, repeats=rep, add_count_in=count_in, output_path=out_f)
    if res.get("success"):
      print(f"[+] Success! Loop exported to: {res.get('output_file')}")
      print(f"    • Duration: {res.get('total_duration_sec')}s (Slice: {res.get('slice_duration_sec')}s x {res.get('repeats')})")
    else:
      print(f"[-] Looper error: {res.get('error')}")
    return

  if args.align_words:
    import word_aligner
    lrc_f = args.align_words[0]
    audio_f = args.align_words[1] if len(args.align_words) > 1 and os.path.isfile(args.align_words[1]) else None
    out_f = args.align_words[2] if len(args.align_words) > 2 else (os.path.splitext(lrc_f)[0] + ".elrc")

    if not os.path.isfile(lrc_f):
      print(f"[-] Error: LRC file not found: {lrc_f}")
      return

    with open(lrc_f, "r", encoding="utf-8") as f:
      content = f.read()

    print(f"[*] Aligning words in {lrc_f} to Enhanced LRC...")
    res = word_aligner.generate_enhanced_lrc(content, audio_path=audio_f)
    if res.get("success"):
      word_aligner.save_enhanced_lrc(res["enhanced_lrc"], out_f)
      print(f"[+] Success! Aligned {res.get('total_words_aligned')} words across {res.get('total_lines')} lines.")
      print(f"[+] Saved Enhanced LRC to: {out_f}")
    else:
      print("[-] Alignment failed.")
    return

  if args.autoeq:
    import headphone_autoeq
    arg = args.autoeq
    if arg in ("list", None):
      print("[*] Available Built-in Headphone AutoEq Profiles (Harman 2020 Target):")
      for p in headphone_autoeq.get_available_profiles():
        print(f"    • [{p['key']}] {p['name']} ({p['type']}) - Preamp: {p['preamp_db']} dB")
      print("[*] Run 'python sonance.py --autoeq <model_key>' to view calibration gains.")
    elif os.path.isfile(arg):
      print(f"[*] Parsing custom EqualizerAPO profile: {arg}...")
      with open(arg, "r", encoding="utf-8") as f:
        res = headphone_autoeq.parse_equalizer_apo_text(f.read())
      if res.get("success"):
        print(f"[+] Successfully parsed {res['name']} (Preamp: {res['preamp_db']} dB):")
        for f_hz, g_db in zip(headphone_autoeq.EQ_10_BANDS, res["gains"]):
          print(f"    • {f_hz:>5} Hz: {g_db:>+5.1f} dB")
      else:
        print(f"[-] Parse failed: {res.get('error')}")
    else:
      prof = headphone_autoeq.get_profile_by_key(arg)
      if prof:
        print(f"[+] Headphone AutoEq Profile: {prof['name']} [{prof['brand']}]")
        print(f"    • Type:        {prof['type']}")
        print(f"    • Preamp:      {prof['preamp_db']} dB")
        print(f"    • Description: {prof['description']}")
        print("    --- 10-Band Studio Hardware EQ Gains ---")
        for f_hz, g_db in zip(headphone_autoeq.EQ_10_BANDS, prof["gains"]):
          print(f"    • {f_hz:>5} Hz: {g_db:>+5.1f} dB")
      else:
        print(f"[-] Profile '{arg}' not found. Run with --autoeq to list available models.")
    return

  if args.verify_flac:
    import flac_verifier
    target = args.verify_flac
    if os.path.isdir(target):
      print(f"[*] Auditing FLAC stream integrity in: {target}...")
      res = flac_verifier.verify_flac_directory(target)
      if res.get("success"):
        print(res["report_text"])
      else:
        print(f"[-] Audit failed: {res.get('error')}")
    else:
      print(f"[*] Verifying FLAC stream integrity for: {target}...")
      res = flac_verifier.verify_single_flac(target)
      if res.get("success"):
        print(f"[+] File:        {res['filename']}")
        print(f"[+] Status:      {res['status']} ({'Bit-Perfect Lossless' if res.get('is_bit_perfect') else res.get('message')})")
        print(f"[+] Stored MD5:  {res['stored_md5']}")
        if res.get("calculated_md5"):
          print(f"[+] Calc MD5:    {res['calculated_md5']}")
        print(f"[+] Resolution:  {res['bits_per_sample']}-bit / {res['sample_rate']} Hz ({res['channels']} ch)")
      else:
        print(f"[-] Verification failed: {res.get('error')}")
    return

  if args.automix:
    import dj_automix
    tracks = []
    trans_s = 12.0
    out_mix = None
    idx = 0
    while idx < len(args.automix):
      a = args.automix[idx]
      if a == "--transition" and idx + 1 < len(args.automix):
        trans_s = float(args.automix[idx + 1])
        idx += 2
      elif a == "--output" and idx + 1 < len(args.automix):
        out_mix = args.automix[idx + 1]
        idx += 2
      elif os.path.isfile(a):
        tracks.append(a)
        idx += 1
      elif os.path.isdir(a):
        for root, _, files in os.walk(a):
          for f in sorted(files):
            if os.path.splitext(f)[1].lower() in dj_automix.AUDIO_EXTS:
              tracks.append(os.path.join(root, f))
        idx += 1
      else:
        idx += 1

    if len(tracks) < 2:
      print("[-] Error: --automix requires at least 2 audio files or a directory containing audio files.")
      return

    print(f"[*] Creating Continuous DJ Auto-Mix for {len(tracks)} tracks (Transition: {trans_s}s)...")
    res = dj_automix.create_dj_automix(tracks, transition_sec=trans_s, output_path=out_mix)
    if res.get("success"):
      print(f"[+] DJ Auto-Mix Complete!")
      print(f"    • Output:   {res['output_file']}")
      print(f"    • Duration: {res['formatted_duration']} ({res['total_duration_sec']}s)")
      print(f"    • Tracks:   {res['total_tracks']}")
      for t in res.get("transitions", []):
        print(f"    • [{t['from_camelot']}] {t['from_track']} -> [{t['to_camelot']}] {t['to_track']} ({t['transition_sec']}s crossfade)")
    else:
      print(f"[-] DJ Auto-Mix failed: {res.get('error')}")
    return

  if args.fetch_lyrics:
    import lyrics_aggregator
    if len(args.fetch_lyrics) < 2:
      print("[-] Error: --fetch-lyrics requires <artist> <title>.")
      return
    art = args.fetch_lyrics[0]
    tit = args.fetch_lyrics[1]
    rom = "--romanize" in args.fetch_lyrics
    out_f = None
    for a in args.fetch_lyrics[2:]:
      if not a.startswith("--"):
        out_f = a
        break

    print(f"[*] Searching multi-provider synchronized lyrics for: {art} - {tit}...")
    res = lyrics_aggregator.aggregate_lyrics(art, tit, romanize=rom)
    if res.get("success"):
      print(f"[+] Found from: {res['source']} ({res['line_count']} lines, Synced: {res['synced']})")
      if out_f:
        with open(out_f, "w", encoding="utf-8") as f:
          f.write(res["lyrics"])
        print(f"[+] Saved to: {out_f}")
      else:
        print("\n--- Preview ---")
        for l in res["lyrics"].splitlines()[:6]:
          print(f"  {l}")
    else:
      print(f"[-] {res.get('error')}")
    return

  if args.batch_lyrics:
    import lyrics_aggregator
    folder = args.batch_lyrics[0]
    ow = "--overwrite" in args.batch_lyrics
    print(f"[*] Batch scanning folder for missing lyrics: {folder}...")
    res = lyrics_aggregator.batch_download_folder_lyrics(
        folder,
        overwrite=ow,
        progress_callback=lambda c, t, f: print(f"    [{c}/{t}] Scanning: {f}"),
    )
    if res.get("success"):
      print("[+] Batch Download Complete!")
      print(f"    • Total Tracks:      {res['total_tracks']}")
      print(f"    • Downloaded Lyrics: {res['downloaded_count']}")
      print(f"    • Already Present:   {res['already_present']}")
      print(f"    • Missing/Failed:    {res['failed_count']}")
    else:
      print(f"[-] Batch failed: {res.get('error')}")
    return

  if args.inspect_stream:
    import audio_inspector
    res = audio_inspector.inspect_audio_stream(args.inspect_stream)
    print(audio_inspector.format_inspection_card(res))
    return

  if args.restore_audio:
    import audio_restorer
    restore_params = list(args.restore_audio) + list(unknown)
    inp = restore_params[0]
    out = None
    hum = 60.0 if "--dehum" in restore_params else None
    if "--dehum" in restore_params:
      h_idx = restore_params.index("--dehum")
      if h_idx + 1 < len(restore_params) and restore_params[h_idx + 1] in ("50", "60"):
        hum = float(restore_params[h_idx + 1])
    for a in restore_params[1:]:
      if not a.startswith("--") and a not in ("50", "60"):
        out = a
        break
    print(f"[*] Restoring analog audio: {inp}...")
    res = audio_restorer.restore_analog_audio(
        inp,
        output_path=out,
        declick="--no-declick" not in restore_params,
        dehum_freq=hum,
        rumble_filter="--no-rumble" not in restore_params,
        dehiss="--no-dehiss" not in restore_params,
    )
    if res.get("success"):
      print("[+] Analog Audio Restoration Succeeded!")
      print(f"    • Output:          {res['output_file']}")
      print(f"    • Clicks Repaired: {res['clicks_repaired']}")
      print(f"    • Rumble Filtered: {res['rumble_filtered']}")
      print(f"    • Dehum Applied:   {res['dehum_applied']}")
      print(f"    • Dehiss Applied:  {res['dehiss_applied']}")
    else:
      print(f"[-] Restoration failed: {res.get('error')}")
    return

  if args.migrate_library:
    import library_migrator
    mig_params = list(args.migrate_library) + list(unknown)
    xml_f = mig_params[0]
    tgt = None
    out = None
    idx = 1
    while idx < len(mig_params):
      a = mig_params[idx]
      if a == "--target-dir" and idx + 1 < len(mig_params):
        tgt = mig_params[idx + 1]
        idx += 2
      elif a == "--output-playlists" and idx + 1 < len(mig_params):
        out = mig_params[idx + 1]
        idx += 2
      elif not a.startswith("--") and not tgt:
        tgt = a
        idx += 1
      elif not a.startswith("--") and not out:
        out = a
        idx += 1
      else:
        idx += 1
    print(f"[*] Migrating library from: {xml_f}...")
    res = library_migrator.migrate_library(xml_f, target_music_dir=tgt, output_playlist_dir=out)
    if res.get("success"):
      print("[+] Library Migration Complete!")
      print(f"    • Total Tracks:       {res['total_tracks']}")
      print(f"    • Matched on Disk:    {res['matched_on_disk']} ({res['match_percentage']}%)")
      print(f"    • Missing on Disk:    {res['missing_on_disk']}")
      print(f"    • Playlists Found:    {res['total_playlists']}")
      if res.get("exported_playlist_files"):
        print(f"    • Exported Playlists: {len(res['exported_playlist_files'])} .m3u8 files")
    else:
      print(f"[-] Migration failed: {res.get('error')}")
    return

  if args.translate_lyrics:
    import lyrics_translator
    trans_params = list(args.translate_lyrics) + list(unknown)
    if len(trans_params) < 2:
      print("[-] Error: --translate-lyrics requires <lrc_file_or_text> <target_lang> [output_file]")
      return
    src = trans_params[0]
    tgt = trans_params[1]
    out = trans_params[2] if len(trans_params) > 2 and not trans_params[2].startswith("--") else None
    dual = "--translated-only" not in trans_params

    content = src
    if os.path.isfile(src):
      with open(src, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"[*] Translating lyrics to {tgt.upper()}...")
    res = lyrics_translator.translate_lyrics(content, target_lang=tgt, dual_format=dual, output_path=out)
    if res.get("success"):
      print(f"[+] Lyrics Translated to {res['language_name']} ({res['total_lines_translated']} lines):")
      if out:
        print(f"[+] Saved to: {out}")
      else:
        print("\n--- Preview ---")
        for l in res["translated_lyrics"].splitlines()[:6]:
          print(f"  {l}")
    else:
      print(f"[-] Translation failed: {res.get('error')}")
    return

  if args.accuraterip:
    import accuraterip_verifier
    tgt = args.accuraterip
    if os.path.isdir(tgt):
      res = accuraterip_verifier.verify_album_directory(tgt)
    else:
      res = accuraterip_verifier.verify_audio_file(tgt)
    print(accuraterip_verifier.format_accuraterip_card(res))
    return

  if args.heal_playlist:
    import playlist_doctor
    p_params = list(args.heal_playlist) + list(unknown)
    pl_path = p_params[0]
    lib_dir = None
    out_pl = None
    up_lossless = "--lossless" in p_params
    rem_dup = "--no-dedup" not in p_params
    idx = 1
    while idx < len(p_params):
      arg = p_params[idx]
      if arg == "--library-dir" and idx + 1 < len(p_params):
        lib_dir = p_params[idx + 1]
        idx += 2
      elif arg == "--output" and idx + 1 < len(p_params):
        out_pl = p_params[idx + 1]
        idx += 2
      else:
        idx += 1
    print(f"[*] Healing playlist: {pl_path}...")
    res = playlist_doctor.heal_playlist(
        pl_path,
        library_dir=lib_dir,
        output_path=out_pl,
        upgrade_lossless=up_lossless,
        remove_duplicates=rem_dup,
    )
    if res.get("success"):
      print("[+] Playlist Doctor Healed Successfully!")
      print(f"    • Output Playlist:     {res['output_playlist']}")
      print(f"    • Restored Links:      {res['healed_tracks']}")
      print(f"    • Upgraded to FLAC:    {res['upgraded_to_lossless']}")
      print(f"    • Health Score:        {res['pre_health_score']}% -> {res['post_health_score']}%")
    else:
      print(f"[-] Playlist healing failed: {res.get('error')}")
    return

  if args.spatial_8d:
    import audio_8d_spatializer
    s_params = list(args.spatial_8d) + list(unknown)
    inp = s_params[0]
    out = None
    orbit_sec = 12.0
    depth_val = 0.85
    idx = 1
    while idx < len(s_params):
      arg = s_params[idx]
      if arg == "--orbit" and idx + 1 < len(s_params):
        orbit_sec = float(s_params[idx + 1])
        idx += 2
      elif arg == "--depth" and idx + 1 < len(s_params):
        depth_val = float(s_params[idx + 1])
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Rendering 360-degree Binaural 8D Audio: {inp} (Orbit: {orbit_sec}s, Depth: {int(depth_val*100)}%)...")
    res = audio_8d_spatializer.render_8d_audio_file(
        inp, output_path=out, orbit_period_sec=orbit_sec, spatial_depth=depth_val
    )
    print(audio_8d_spatializer.format_8d_card(res))
    return

  if args.normalize_gain:
    import replaygain_normalizer
    n_params = list(args.normalize_gain) + list(unknown)
    tgt = n_params[0]
    mode = "tag"
    target_lufs = -18.0
    idx = 1
    while idx < len(n_params):
      arg = n_params[idx]
      if arg == "--mode" and idx + 1 < len(n_params):
        mode = n_params[idx + 1].lower()
        idx += 2
      elif arg == "--target-lufs" and idx + 1 < len(n_params):
        target_lufs = float(n_params[idx + 1])
        idx += 2
      else:
        idx += 1
    print(f"[*] Processing ReplayGain / Loudness Normalizer: {tgt} (Mode: {mode.upper()}, Target: {target_lufs} LUFS)...")
    if os.path.isdir(tgt):
      res = replaygain_normalizer.process_folder_replaygain(tgt, mode=mode, target_lufs=target_lufs)
    else:
      if mode == "hard":
        res = replaygain_normalizer.hard_normalize_audio(tgt, target_lufs=target_lufs)
      else:
        res = replaygain_normalizer.analyze_audio_gain(tgt, target_lufs=target_lufs)
    print(replaygain_normalizer.format_replaygain_card(res))
    return

  if args.parametric_eq:
    import parametric_eq
    eq_params = list(args.parametric_eq) + list(unknown)
    inp = eq_params[0]
    out = None
    idx = 1
    while idx < len(eq_params):
      arg = eq_params[idx]
      if arg in ("--output", "--out", "--peq-out") and idx + 1 < len(eq_params):
        out = eq_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Processing audio through 5-Band Parametric Master EQ: {inp}...")
    res = parametric_eq.render_parametric_eq(inp, output_path=out)
    print(parametric_eq.format_parametric_card(res, parametric_eq.DEFAULT_BANDS))
    return

  if args.phase_meter:
    import phase_correlation
    pm_params = list(args.phase_meter) + list(unknown)
    inp = pm_params[0]
    should_correct = "--correct" in pm_params
    if should_correct:
      print(f"[*] Correcting inverted phase & mono bass: {inp}...")
      res = phase_correlation.correct_stereo_phase(inp)
      if res.get("success"):
        print(f"[+] Corrected Audio Saved: {res['output_file']}")
        print(f"    • Inverted Right Channel: {res['inverted_right']}")
        print(f"    • Elliptical Mono Bass:   {res['mono_bass_applied']}")
        print(f"    • New Phase Correlation:  {res['new_correlation']} ({res['new_status']})")
      else:
        print(f"[-] Correction failed: {res.get('error')}")
    else:
      print(f"[*] Analyzing stereo phase correlation: {inp}...")
      res = phase_correlation.analyze_phase_correlation(inp)
      print(phase_correlation.format_phase_card(res))
    return

  if args.test_tone:
    import dac_tester
    tt_params = list(args.test_tone) + list(unknown)
    t_type = tt_params[0]
    out_f = None
    rate = 96000
    bits = 24
    dur = 10.0
    idx = 1
    while idx < len(tt_params):
      arg = tt_params[idx]
      if arg in ("--rate", "--sr", "--sample-rate") and idx + 1 < len(tt_params):
        rate = int(tt_params[idx + 1])
        idx += 2
      elif arg in ("--bits", "--bit-depth") and idx + 1 < len(tt_params):
        bits = int(tt_params[idx + 1])
        idx += 2
      elif arg in ("--dur", "--duration") and idx + 1 < len(tt_params):
        dur = float(tt_params[idx + 1])
        idx += 2
      elif arg in ("--output", "--out", "--out-tone") and idx + 1 < len(tt_params):
        out_f = tt_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out_f is None:
        out_f = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Synthesizing DAC Test Signal: {t_type.upper()} ({bits}-bit / {rate} Hz)...")
    res = dac_tester.generate_test_signal_file(t_type, sample_rate=rate, bit_depth=bits, duration_sec=dur, output_path=out_f)
    print(dac_tester.format_dac_card(res))
    return

  if args.retime_lyrics:
    import lyrics_retimer
    rt_params = list(args.retime_lyrics) + list(unknown)
    lrc_f = rt_params[0]
    t1_o = None
    t1_n = None
    t2_o = None
    t2_n = None
    out_f = None

    pos_args = []
    idx = 1
    while idx < len(rt_params):
      arg = rt_params[idx]
      if arg == "--t1-old" and idx + 1 < len(rt_params):
        t1_o = float(rt_params[idx + 1])
        idx += 2
      elif arg == "--t1-new" and idx + 1 < len(rt_params):
        t1_n = float(rt_params[idx + 1])
        idx += 2
      elif arg == "--t2-old" and idx + 1 < len(rt_params):
        t2_o = float(rt_params[idx + 1])
        idx += 2
      elif arg == "--t2-new" and idx + 1 < len(rt_params):
        t2_n = float(rt_params[idx + 1])
        idx += 2
      elif arg in ("--output", "--out", "--out-lrc") and idx + 1 < len(rt_params):
        out_f = rt_params[idx + 1]
        idx += 2
      elif not arg.startswith("--"):
        pos_args.append(arg)
        idx += 1
      else:
        idx += 1

    if t1_o is None and len(pos_args) >= 4:
      t1_o = float(pos_args[0])
      t1_n = float(pos_args[1])
      t2_o = float(pos_args[2])
      t2_n = float(pos_args[3])
      if len(pos_args) > 4 and out_f is None:
        out_f = pos_args[4]

    if t1_o is None or t1_n is None or t2_o is None or t2_n is None:
      print("[-] Error: --retime-lyrics requires <lrc_file> <t1_old> <t1_new> <t2_old> <t2_new> [output_lrc]")
      print("    Or named flags: --retime-lyrics <file> --t1-old 10.0 --t1-new 10.5 --t2-old 100.0 --t2-new 101.5 [--out-lrc file.lrc]")
      return

    with open(lrc_f, "r", encoding="utf-8") as f:
      content = f.read()
    print(f"[*] Recalibrating lyrics drift for: {lrc_f}...")
    res = lyrics_retimer.retime_lyrics(content, t1_o, t1_n, t2_o, t2_n, output_path=out_f)
    print(lyrics_retimer.format_retimer_card(res))
    return

  if args.spectrum:
    import spectrum_analyzer
    sp_params = list(args.spectrum) + list(unknown)
    target = sp_params[0]
    max_sec = 60.0
    idx = 1
    while idx < len(sp_params):
      if sp_params[idx] in ("--max-sec", "--sec", "--duration") and idx + 1 < len(sp_params):
        max_sec = float(sp_params[idx + 1])
        idx += 2
      else:
        idx += 1
    print(f"[*] Analyzing frequency spectrum & bandwidth forensics: {target}...")
    res = spectrum_analyzer.analyze_spectrum(target, max_duration_sec=max_sec)
    print(spectrum_analyzer.format_spectrum_card(res))
    return

  if args.declip:
    import audio_declipper
    dc_params = list(args.declip) + list(unknown)
    inp = dc_params[0]
    out = None
    exp = 2.0
    hdr = 4.0
    idx = 1
    while idx < len(dc_params):
      arg = dc_params[idx]
      if arg in ("--expansion", "--expand") and idx + 1 < len(dc_params):
        exp = float(dc_params[idx + 1])
        idx += 2
      elif arg in ("--headroom", "--attenuation") and idx + 1 < len(dc_params):
        hdr = float(dc_params[idx + 1])
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(dc_params):
        out = dc_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Auditing digital clipping & expanding dynamic range: {inp}...")
    res = audio_declipper.declip_audio(inp, output_path=out, expansion_db=exp, headroom_db=hdr)
    print(audio_declipper.format_declipper_card(res))
    return

  if args.auto_split:
    import track_splitter
    as_params = list(args.auto_split) + list(unknown)
    inp = as_params[0]
    out_dir = None
    th = -42.0
    ms = 1.5
    idx = 1
    while idx < len(as_params):
      arg = as_params[idx]
      if arg in ("--threshold", "--silence-threshold") and idx + 1 < len(as_params):
        th = float(as_params[idx + 1])
        idx += 2
      elif arg in ("--min-silence", "--silence-sec") and idx + 1 < len(as_params):
        ms = float(as_params[idx + 1])
        idx += 2
      elif arg in ("--output-dir", "--out", "--dir") and idx + 1 < len(as_params):
        out_dir = as_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out_dir is None:
        out_dir = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Scanning audio silence gaps and generating CUE tracks: {inp}...")
    res = track_splitter.auto_split_audio(inp, output_dir=out_dir, silence_threshold_db=th, min_silence_sec=ms)
    print(track_splitter.format_splitter_card(res))
    return

  if args.lyrics_video:
    import lyrics_video_maker
    lv_params = list(args.lyrics_video) + list(unknown)
    aud = lv_params[0]
    lrc = None
    out = None
    res_mode = "1080p"
    idx = 1
    while idx < len(lv_params):
      arg = lv_params[idx]
      if arg in ("--resolution", "--res") and idx + 1 < len(lv_params):
        res_mode = lv_params[idx + 1]
        idx += 2
      elif arg in ("--lrc", "--lyrics") and idx + 1 < len(lv_params):
        lrc = lv_params[idx + 1]
        idx += 2
      elif arg in ("--output", "--out", "--video") and idx + 1 < len(lv_params):
        out = lv_params[idx + 1]
        idx += 2
      elif not arg.startswith("--"):
        if lrc is None and arg.endswith(".lrc"):
          lrc = arg
        elif out is None:
          out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Generating synchronized lyrics karaoke video: {aud}...")
    res = lyrics_video_maker.generate_lyrics_video(aud, lrc_path=lrc, output_path=out, resolution=res_mode)
    print(lyrics_video_maker.format_video_card(res))
    return

  if args.upsample:
    import audio_upsampler
    us_params = list(args.upsample) + list(unknown)
    inp = us_params[0]
    out = None
    rate = 192000
    filt = "linear"
    idx = 1
    while idx < len(us_params):
      arg = us_params[idx]
      if arg in ("--rate", "--sr", "--sample-rate") and idx + 1 < len(us_params):
        rate = int(us_params[idx + 1])
        idx += 2
      elif arg in ("--filter", "--phase") and idx + 1 < len(us_params):
        filt = us_params[idx + 1]
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(us_params):
        out = us_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Upsampling audio with Whittaker-Shannon polyphase sinc filter ({filt.title()} Phase -> {rate} Hz): {inp}...")
    res = audio_upsampler.upsample_audio(inp, target_sr=rate, output_path=out, filter_type=filt)
    print(audio_upsampler.format_upsampler_card(res))
    return

  if args.fix_cue:
    import cue_fixer
    fc_params = list(args.fix_cue) + list(unknown)
    cue_in = fc_params[0]
    aud_in = None
    out_cue = None
    idx = 1
    while idx < len(fc_params):
      arg = fc_params[idx]
      if arg in ("--audio", "--audio-target") and idx + 1 < len(fc_params):
        aud_in = fc_params[idx + 1]
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(fc_params):
        out_cue = fc_params[idx + 1]
        idx += 2
      elif not arg.startswith("--"):
        if aud_in is None and not arg.endswith(".cue"):
          aud_in = arg
        elif out_cue is None:
          out_cue = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Auditing and repairing CUE sheet: {cue_in}...")
    res = cue_fixer.audit_and_fix_cue(cue_in, target_audio_file=aud_in, output_cue_path=out_cue)
    print(cue_fixer.format_cue_card(res))
    return

  if args.synthesize_ir:
    import room_ir_synthesizer
    ir_params = list(args.synthesize_ir) + list(unknown)
    out_f = None
    preset = "room"
    rt60 = None
    sr = 48000
    idx = 0
    while idx < len(ir_params):
      arg = ir_params[idx]
      if arg in ("--preset", "--room") and idx + 1 < len(ir_params):
        preset = ir_params[idx + 1]
        idx += 2
      elif arg in ("--rt60", "--decay") and idx + 1 < len(ir_params):
        rt60 = float(ir_params[idx + 1])
        idx += 2
      elif arg in ("--sr", "--rate") and idx + 1 < len(ir_params):
        sr = int(ir_params[idx + 1])
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(ir_params):
        out_f = ir_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out_f is None:
        out_f = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Synthesizing room acoustic impulse response ({preset} preset, RT60={rt60 or 'auto'}s)...")
    res = room_ir_synthesizer.synthesize_impulse_response(
        room_preset=preset, rt60_sec=rt60, sample_rate=sr, output_path=out_f
    )
    print(room_ir_synthesizer.format_ir_card(res))
    return

  if args.lrc_to_ass:
    import lrc_to_ass_converter
    ass_params = list(args.lrc_to_ass) + list(unknown)
    lrc_in = ass_params[0]
    out_ass = None
    style = "karaoke"
    color = "#FFD700"
    font = "Trebuchet MS"
    do_srt = False
    idx = 1
    while idx < len(ass_params):
      arg = ass_params[idx]
      if arg in ("--style", "--preset") and idx + 1 < len(ass_params):
        style = ass_params[idx + 1]
        idx += 2
      elif arg in ("--color", "--hex") and idx + 1 < len(ass_params):
        color = ass_params[idx + 1]
        idx += 2
      elif arg in ("--font", "--typeface") and idx + 1 < len(ass_params):
        font = ass_params[idx + 1]
        idx += 2
      elif arg == "--srt":
        do_srt = True
        idx += 1
      elif arg in ("--output", "--out") and idx + 1 < len(ass_params):
        out_ass = ass_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out_ass is None:
        out_ass = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Converting lyrics to broadcast karaoke ASS subtitles: {lrc_in}...")
    res = lrc_to_ass_converter.convert_lrc_to_subtitles(
        lrc_path=lrc_in,
        output_path=out_ass,
        style_preset=style,
        primary_color_hex=color,
        font_name=font,
        export_srt=do_srt,
    )
    print(lrc_to_ass_converter.format_ass_card(res))
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
