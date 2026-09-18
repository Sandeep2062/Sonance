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
      allow_abbrev=False,
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
      "--dsd-to-pcm",
      nargs="+",
      metavar="PARAM",
      help="Audiophile DSD to PCM decimator & DoP studio: --dsd-to-pcm <input.dsf> [output.wav] [--rate 88200|176400|352800] [--dop]",
  )
  parser.add_argument(
      "--align-phase",
      nargs="+",
      metavar="PARAM",
      help="Sub-sample fractional delay & phase alignment: --align-phase <audio_file> [output_file] [--max-delay-ms 10.0] [--channel left|right|auto]",
  )
  parser.add_argument(
      "--master-limit",
      nargs="+",
      metavar="PARAM",
      help="Mastering brickwall limiter & ISP true-peak studio: --master-limit <audio_file> [output_file] [--ceiling -1.0] [--threshold -3.0] [--release 120]",
  )
  parser.add_argument(
      "--album-art",
      nargs="+",
      metavar="PARAM",
      help="Album art optimizer, cover normalizer & bloat reducer: --album-art <file_or_dir> [--extract] [--strip]",
  )
  parser.add_argument(
      "--deess",
      nargs="+",
      metavar="PARAM",
      help="Dynamic multiband de-esser & sibilance tamer: --deess <audio_file> [output_file] [--freq 6500] [--threshold -18] [--reduction -9] [--listen]",
  )
  parser.add_argument(
      "--midside",
      nargs="+",
      metavar="PARAM",
      help="Mid/Side spatial width & elliptical bass monomaker: --midside <audio_file> [output_file] [--width 125] [--monomaker 120] [--mid 0] [--side 0] [--air 0]",
  )
  parser.add_argument(
      "--watermark",
      nargs="+",
      metavar="PARAM",
      help="Lossless ultrasonic audio watermark studio: --watermark <audio_file> [--embed <text>] [--detect] [--output <out_file>] [--strength -65]",
  )
  parser.add_argument(
      "--markers",
      nargs="+",
      metavar="PARAM",
      help="Broadcast cue markers & podcast chapter studio: --markers <audio_file> [--import-timestamps <text_or_file>] [--export-cue <cue_file>] [--output <out_file>]",
  )
  parser.add_argument(
      "--tape",
      nargs="+",
      metavar="PARAM",
      help="Analog tape saturation & tube warmth studio: --tape <audio_file> [output_file] [--drive 2.5] [--speed 15|30|7.5] [--warmth 2.0] [--bias 0.5] [--hiss]",
  )
  parser.add_argument(
      "--formant",
      nargs="+",
      metavar="PARAM",
      help="Pitch shifter & formant vocal resizer: --formant <audio_file> [output_file] [--pitch +2] [--formant 1.1] [--no-preserve-formants]",
  )
  parser.add_argument(
      "--loudness-war",
      nargs="+",
      metavar="PARAM",
      help="Mastering loudness war & dynamic spread analyzer: --loudness-war <audio_file> [--target -14.0]",
  )
  parser.add_argument(
      "--remix",
      nargs="*",
      metavar="PARAM",
      help="Multi-track stems remixer studio: --remix [--vocals <file>] [--drums <file>] [--bass <file>] [--other <file>] [--folder <dir>] [--output <file>] [--preset acapella|karaoke|drum_and_bass|vocal_boost]",
  )
  parser.add_argument(
      "--transient",
      nargs="*",
      metavar="PARAM",
      help="Audiophile transient shaper & drum punch designer: --transient <audio_file> [output_file] [--attack +4.0] [--sustain -2.0] [--attack-speed 4.0] [--sustain-speed 80.0]",
  )
  parser.add_argument(
      "--binaural",
      nargs="*",
      metavar="PARAM",
      help="Binaural 3D ambisonic room & headphone virtualizer: --binaural <audio_file> [output_file] [--preset control_room|mastering_lab|live_lounge] [--angle 30] [--distance 1.8] [--crossfeed 1.0] [--ambience 0.35]",
  )
  parser.add_argument(
      "--gate",
      nargs="*",
      metavar="PARAM",
      help="Broadcast noise gate & downward expander: --gate <audio_file> [output_file] [--threshold -40] [--reduction -60] [--ratio 10] [--attack 1.5] [--hold 40] [--release 120] [--lookahead 2.0]",
  )
  parser.add_argument(
      "--echo",
      nargs="*",
      metavar="PARAM",
      help="Stereo ping-pong & multi-tap tape echo studio: --echo <audio_file> [output_file] [--delay 375] [--feedback 45] [--damping 3800] [--flutter 0.12] [--drive 1.3] [--mix 35] [--no-ping-pong]",
  )
  parser.add_argument(
      "--package-release",
      "--audit-release",
      nargs="*",
      metavar="PARAM",
      help="Universal workstation release packager & manifest auditor: --package-release [--zip] [--verify-only] [--out-dir <dir>]",
  )
  parser.add_argument(
      "--generate-manual",
      nargs="*",
      metavar="PARAM",
      help="Offline audiophile guide & workstation handbook generator: --generate-manual [output_path] [--open]",
  )
  parser.add_argument(
      "--vst-scan",
      action="store_true",
      help="Scan host system and virtual registry for installed VST3 and CLAP audio plugins",
  )
  parser.add_argument(
      "--vst-rack",
      nargs="*",
      metavar="PARAM",
      help="VST3 & CLAP audio effect rack chain: --vst-rack <audio_file> [output_file] [--preset mastering_bus|vocal_magic|analog_space]",
  )
  parser.add_argument(
      "--spatial-714",
      "--atmos",
      nargs="*",
      metavar="PARAM",
      help="Dolby Atmos 7.1.4 bed spatializer & multichannel renderer: --spatial-714 <audio_file> [output_file] [--mode binaural|discrete] [--format 7.1.4|7.1|5.1] [--lfe-cutoff 80] [--height 0.35] [--spread 1.15]",
  )
  parser.add_argument(
      "--console",
      "--channel-strip",
      "--ssl-comp",
      nargs="*",
      metavar="PARAM",
      help="British Class-A Console Channel Strip & SSL G-Master Bus Studio: --console <audio_file> [output_file] [--preset master_bus_glue|analog_warmth|drum_bus_punch|vocal_channel|radio_broadcast]",
  )
  parser.add_argument(
      "--hoa",
      "--ambisonics",
      nargs="*",
      metavar="PARAM",
      help="Higher-Order Ambisonics & 360-Degree VR Spatializer: --hoa <audio_file> [output_file] [--order 1|2|3] [--mode binaural|bformat] [--trajectory orbit_helix|orbit_horizontal|orbit_pendulum|fixed] [--azimuth 0] [--elevation 0] [--period 12]",
  )
  parser.add_argument(
      "--bass",
      "--subharmonic",
      nargs="*",
      metavar="PARAM",
      help="Psychoacoustic subharmonic bass synthesizer & missing fundamental studio: --bass <audio_file> [output_file] [--preset club_sub_boom|punchy_kick_thump|earbuds_maxxbass|audiophile_warm_bass|sub_rumble_cleanup] [--sub-24-36 0.85] [--sub-36-56 0.5] [--maxxbass 0.35] [--drive 1.25] [--subsonic-hpf 25] [--monomaker 120] [--mix 0.9]",
  )
  parser.add_argument(
      "--soothe",
      "--de-resonate",
      "--suppress-resonance",
      nargs="*",
      metavar="PARAM",
      help="Dynamic spectral resonance suppressor & de-resonator: --soothe <audio_file> [output_file] [--preset tame_harshness|vocal_de_boxer|muddy_low_mid|cymbal_silencer|extreme_surgical] [--depth 0.55] [--threshold 3.5] [--sharpness 2.5] [--low-cut 1200] [--high-cut 9000] [--listen]",
  )
  parser.add_argument(
      "--vintage-compressor",
      "--la2a",
      "--fairchild",
      nargs="*",
      metavar="PARAM",
      help="Vintage optical & variable-mu compressor: --la2a <audio_file> [output_file] [--mode la2a|fairchild] [--preset la2a_smooth_vocal|la2a_acoustic_warmth|fairchild_master_bus|fairchild_drum_crush|vintage_warm_glue] [--reduction 50] [--hpf 90] [--hf-emphasis] [--tc 1-6] [--drive 1.25] [--makeup 2.0] [--mix 1.0]",
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

  if args.dsd_to_pcm:
    import dsd_converter
    dsd_params = list(args.dsd_to_pcm) + list(unknown)
    inp = dsd_params[0]
    out = None
    rate = 88200
    dop = False
    idx = 1
    while idx < len(dsd_params):
      arg = dsd_params[idx]
      if arg in ("--rate", "--sr", "--sample-rate") and idx + 1 < len(dsd_params):
        rate = int(dsd_params[idx + 1])
        idx += 2
      elif arg == "--dop":
        dop = True
        idx += 1
      elif arg in ("--output", "--out") and idx + 1 < len(dsd_params):
        out = dsd_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Processing DSD bitstream ({'DoP v1.1' if dop else f'PCM {rate} Hz'}): {inp}...")
    res = dsd_converter.process_dsd_stream(inp, target_pcm_rate=rate, output_path=out, dop_mode=dop)
    print(dsd_converter.format_dsd_card(res))
    return

  if args.align_phase:
    import subsample_delay
    ap_params = list(args.align_phase) + list(unknown)
    inp = ap_params[0]
    out = None
    max_ms = 10.0
    chan = "auto"
    idx = 1
    while idx < len(ap_params):
      arg = ap_params[idx]
      if arg in ("--max-delay-ms", "--max-ms", "--window") and idx + 1 < len(ap_params):
        max_ms = float(ap_params[idx + 1])
        idx += 2
      elif arg in ("--channel", "--ch") and idx + 1 < len(ap_params):
        chan = ap_params[idx + 1]
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(ap_params):
        out = ap_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Measuring sub-sample fractional delay & aligning phase: {inp}...")
    res = subsample_delay.align_audio_phase(inp, output_path=out, max_delay_ms=max_ms, target_channel=chan)
    print(subsample_delay.format_delay_card(res))
    return

  if args.master_limit:
    import mastering_limiter
    ml_params = list(args.master_limit) + list(unknown)
    inp = ml_params[0]
    out = None
    ceil = -1.0
    thresh = -3.0
    rel = 120.0
    idx = 1
    while idx < len(ml_params):
      arg = ml_params[idx]
      if arg in ("--ceiling", "--ceil") and idx + 1 < len(ml_params):
        ceil = float(ml_params[idx + 1])
        idx += 2
      elif arg in ("--threshold", "--thresh", "--drive") and idx + 1 < len(ml_params):
        thresh = float(ml_params[idx + 1])
        idx += 2
      elif arg in ("--release", "--rel") and idx + 1 < len(ml_params):
        rel = float(ml_params[idx + 1])
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(ml_params):
        out = ml_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Applying mastering brickwall limiter (Ceiling: {ceil} dBFS, Drive: {-thresh:+.1f} dB): {inp}...")
    res = mastering_limiter.process_mastering_limiter(
        inp, output_path=out, ceiling_db=ceil, threshold_db=thresh, release_ms=rel
    )
    print(mastering_limiter.format_limiter_card(res))
    return

  if args.album_art:
    import album_art_studio
    aa_params = list(args.album_art) + list(unknown)
    tgt = aa_params[0]
    act = "report"
    do_extract = False
    idx = 1
    while idx < len(aa_params):
      arg = aa_params[idx]
      if arg == "--extract":
        act = "extract"
        do_extract = True
        idx += 1
      elif arg == "--strip":
        act = "strip"
        idx += 1
      else:
        idx += 1
    print(f"[*] Scanning album artwork ({act.upper()} mode): {tgt}...")
    res = album_art_studio.scan_and_manage_artwork(tgt, action=act, export_companion=do_extract)
    print(album_art_studio.format_art_card(res))
    return

  if args.deess:
    import audio_deesser
    de_params = list(args.deess) + list(unknown)
    inp = de_params[0]
    out = None
    freq = 6500.0
    thresh = -18.0
    reduc = -9.0
    listen = False
    idx = 1
    while idx < len(de_params):
      arg = de_params[idx]
      if arg in ("--freq", "--frequency") and idx + 1 < len(de_params):
        freq = float(de_params[idx + 1])
        idx += 2
      elif arg in ("--threshold", "--thresh") and idx + 1 < len(de_params):
        thresh = float(de_params[idx + 1])
        idx += 2
      elif arg in ("--reduction", "--max-reduction") and idx + 1 < len(de_params):
        reduc = float(de_params[idx + 1])
        idx += 2
      elif arg in ("--listen", "--audition"):
        listen = True
        idx += 1
      elif arg in ("--output", "--out") and idx + 1 < len(de_params):
        out = de_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Applying dynamic vocal de-esser ({freq} Hz, Threshold: {thresh} dBFS): {inp}...")
    res = audio_deesser.process_deesser(
        inp, output_path=out, sibilance_freq_hz=freq, threshold_dbfs=thresh, max_reduction_db=reduc, listen_sibilance=listen
    )
    print(audio_deesser.format_deesser_card(res))
    return

  if args.midside:
    import midside_processor
    ms_params = list(args.midside) + list(unknown)
    inp = ms_params[0]
    out = None
    width = 125.0
    mono_hz = 120.0
    mid_g = 0.0
    side_g = 0.0
    side_air = 0.0
    idx = 1
    while idx < len(ms_params):
      arg = ms_params[idx]
      if arg in ("--width", "-w") and idx + 1 < len(ms_params):
        width = float(ms_params[idx + 1])
        idx += 2
      elif arg in ("--monomaker", "--mono") and idx + 1 < len(ms_params):
        mono_hz = float(ms_params[idx + 1])
        idx += 2
      elif arg in ("--mid-gain", "--mid") and idx + 1 < len(ms_params):
        mid_g = float(ms_params[idx + 1])
        idx += 2
      elif arg in ("--side-gain", "--side") and idx + 1 < len(ms_params):
        side_g = float(ms_params[idx + 1])
        idx += 2
      elif arg in ("--side-air", "--air") and idx + 1 < len(ms_params):
        side_air = float(ms_params[idx + 1])
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(ms_params):
        out = ms_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Processing Mid/Side spatial width ({width}%, Monomaker: {mono_hz} Hz): {inp}...")
    res = midside_processor.process_midside(
        inp, output_path=out, width_percent=width, monomaker_hz=mono_hz, mid_gain_db=mid_g, side_gain_db=side_g, side_air_db=side_air
    )
    print(midside_processor.format_midside_card(res))
    return

  if args.watermark:
    import audio_watermark
    wm_params = list(args.watermark) + list(unknown)
    inp = wm_params[0]
    out = None
    payload = None
    do_detect = False
    strength = -65.0
    idx = 1
    while idx < len(wm_params):
      arg = wm_params[idx]
      if arg in ("--embed", "-e") and idx + 1 < len(wm_params):
        payload = wm_params[idx + 1]
        idx += 2
      elif arg in ("--detect", "-d"):
        do_detect = True
        idx += 1
      elif arg in ("--output", "--out") and idx + 1 < len(wm_params):
        out = wm_params[idx + 1]
        idx += 2
      elif arg in ("--strength", "-s") and idx + 1 < len(wm_params):
        strength = float(wm_params[idx + 1])
        idx += 2
      else:
        idx += 1
    if payload:
      print(f"[*] Embedding ultrasonic audio watermark ({strength} dBFS): {inp}...")
      res = audio_watermark.embed_watermark(inp, payload, output_path=out, strength_db=strength)
      print(audio_watermark.format_watermark_card(res))
    else:
      print(f"[*] Forensically detecting audio watermark: {inp}...")
      res = audio_watermark.detect_watermark(inp)
      print(audio_watermark.format_watermark_card(res))
    return

  if args.markers:
    import cue_markers
    cm_params = list(args.markers) + list(unknown)
    inp = cm_params[0]
    out = None
    ts_text = None
    export_cue = None
    idx = 1
    while idx < len(cm_params):
      arg = cm_params[idx]
      if arg in ("--import-timestamps", "--timestamps", "-i") and idx + 1 < len(cm_params):
        ts_text = cm_params[idx + 1]
        idx += 2
      elif arg in ("--export-cue", "--cue") and idx + 1 < len(cm_params):
        export_cue = cm_params[idx + 1]
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(cm_params):
        out = cm_params[idx + 1]
        idx += 2
      else:
        idx += 1
    if ts_text:
      if os.path.isfile(ts_text):
        with open(ts_text, "r", encoding="utf-8") as f:
          ts_text = f.read()
      markers = cue_markers.parse_timestamp_text(ts_text)
      print(f"[*] Importing {len(markers)} timestamps into: {inp}...")
      if export_cue:
        cue_str = cue_markers.export_cue_sheet(markers, inp)
        with open(export_cue, "w", encoding="utf-8") as f:
          f.write(cue_str)
        print(f"[+] Exported CUE sheet to: {export_cue}")
      res = cue_markers.write_cue_markers(inp, markers, output_path=out or inp)
      print(cue_markers.format_markers_card(res))
    elif export_cue:
      res = cue_markers.read_cue_markers(inp)
      markers = res.get("markers", [])
      cue_str = cue_markers.export_cue_sheet(markers, inp)
      with open(export_cue, "w", encoding="utf-8") as f:
        f.write(cue_str)
      print(f"[+] Exported {len(markers)} markers to CUE sheet: {export_cue}")
    else:
      print(f"[*] Reading cue points & chapter markers: {inp}...")
      res = cue_markers.read_cue_markers(inp)
      print(cue_markers.format_markers_card(res))
    return

  if args.tape:
    import analog_tape_emulator
    tp_params = list(args.tape) + list(unknown)
    inp = tp_params[0]
    out = None
    drv = 2.5
    spd = 15.0
    wrm = 2.0
    bias = 0.5
    hiss = False
    hiss_db = -80.0
    idx = 1
    while idx < len(tp_params):
      arg = tp_params[idx]
      if arg in ("--drive", "-d") and idx + 1 < len(tp_params):
        drv = float(tp_params[idx + 1])
        idx += 2
      elif arg in ("--speed", "-s") and idx + 1 < len(tp_params):
        spd = float(tp_params[idx + 1])
        idx += 2
      elif arg in ("--warmth", "-w") and idx + 1 < len(tp_params):
        wrm = float(tp_params[idx + 1])
        idx += 2
      elif arg in ("--bias", "-b") and idx + 1 < len(tp_params):
        bias = float(tp_params[idx + 1])
        idx += 2
      elif arg == "--hiss":
        hiss = True
        idx += 1
      elif arg == "--hiss-db" and idx + 1 < len(tp_params):
        hiss_db = float(tp_params[idx + 1])
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(tp_params):
        out = tp_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Simulating analog tape saturation ({spd} ips, Drive: {drv}x): {inp}...")
    res = analog_tape_emulator.process_analog_tape(
        inp, output_path=out, drive=drv, tape_speed_ips=spd, warmth=wrm, tube_bias=bias, add_hiss=hiss, hiss_db=hiss_db
    )
    print(analog_tape_emulator.format_tape_card(res))
    return

  if args.formant:
    import formant_shifter
    fm_params = list(args.formant) + list(unknown)
    inp = fm_params[0]
    out = None
    pitch = 0.0
    formant = 1.0
    preserve = True
    idx = 1
    while idx < len(fm_params):
      arg = fm_params[idx]
      if arg in ("--pitch", "-p") and idx + 1 < len(fm_params):
        pitch = float(fm_params[idx + 1])
        idx += 2
      elif arg in ("--scale", "--ratio", "--formant-scale", "-f") and idx + 1 < len(fm_params):
        formant = float(fm_params[idx + 1])
        idx += 2
      elif arg == "--no-preserve-formants":
        preserve = False
        idx += 1
      elif arg in ("--output", "--out") and idx + 1 < len(fm_params):
        out = fm_params[idx + 1]
        idx += 2
      elif not arg.startswith("--") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1
    print(f"[*] Processing pitch transposition ({pitch:+0.1f} st) & formant scaling ({formant}x): {inp}...")
    res = formant_shifter.process_formant_shifter(
        inp, output_path=out, pitch_semitones=pitch, formant_ratio=formant, preserve_formants=preserve
    )
    print(formant_shifter.format_formant_card(res))
    return

  if args.loudness_war:
    import loudness_war_studio
    lw_params = list(args.loudness_war) + list(unknown)
    inp = lw_params[0]
    tgt = -14.0
    idx = 1
    while idx < len(lw_params):
      arg = lw_params[idx]
      if arg in ("--target", "-t") and idx + 1 < len(lw_params):
        tgt = float(lw_params[idx + 1])
        idx += 2
      else:
        idx += 1
    print(f"[*] Analyzing ITU-R BS.1770-4 loudness war metrics: {inp}...")
    res = loudness_war_studio.analyze_loudness_war(inp, target_lufs=tgt)
    print(loudness_war_studio.format_loudness_war_card(res))
    return

  if args.remix is not None:
    import stems_remixer
    rm_params = list(args.remix) + list(unknown)
    stems = {}
    gains = {"vocals": 0.0, "drums": 0.0, "bass": 0.0, "other": 0.0}
    preset = None
    out = None
    idx = 0
    while idx < len(rm_params):
      arg = rm_params[idx]
      if arg == "--vocals" and idx + 1 < len(rm_params):
        stems["vocals"] = rm_params[idx + 1]
        idx += 2
      elif arg == "--drums" and idx + 1 < len(rm_params):
        stems["drums"] = rm_params[idx + 1]
        idx += 2
      elif arg == "--bass" and idx + 1 < len(rm_params):
        stems["bass"] = rm_params[idx + 1]
        idx += 2
      elif arg == "--other" and idx + 1 < len(rm_params):
        stems["other"] = rm_params[idx + 1]
        idx += 2
      elif arg == "--folder" and idx + 1 < len(rm_params):
        folder = rm_params[idx + 1]
        if os.path.isdir(folder):
          for f in os.listdir(folder):
            fl = f.lower()
            fp = os.path.join(folder, f)
            if "vocal" in fl: stems["vocals"] = fp
            elif "drum" in fl: stems["drums"] = fp
            elif "bass" in fl: stems["bass"] = fp
            elif "other" in fl or "inst" in fl: stems["other"] = fp
        idx += 2
      elif arg == "--preset" and idx + 1 < len(rm_params):
        preset = rm_params[idx + 1]
        idx += 2
      elif arg in ("--output", "--out") and idx + 1 < len(rm_params):
        out = rm_params[idx + 1]
        idx += 2
      elif arg == "--vocal-gain" and idx + 1 < len(rm_params):
        gains["vocals"] = float(rm_params[idx + 1])
        idx += 2
      elif arg == "--drums-gain" and idx + 1 < len(rm_params):
        gains["drums"] = float(rm_params[idx + 1])
        idx += 2
      elif arg == "--bass-gain" and idx + 1 < len(rm_params):
        gains["bass"] = float(rm_params[idx + 1])
        idx += 2
      elif arg == "--other-gain" and idx + 1 < len(rm_params):
        gains["other"] = float(rm_params[idx + 1])
        idx += 2
      else:
        idx += 1
    print(f"[*] Remixing multi-track audio stems...")
    res = stems_remixer.remix_stems(stems, output_path=out, gains_db=gains, preset=preset)
    print(stems_remixer.format_remix_card(res))
    return

  if args.transient is not None:
    import transient_shaper
    ts_params = list(args.transient) + list(unknown)
    if not ts_params:
      print("[-] Error: --transient requires an input audio file.")
      print("    Usage: python sonance.py --transient <audio_file> [output_file] [--attack +4.0] [--sustain -2.0]")
      return
    inp = ts_params[0]
    out = None
    attack = 0.0
    sustain = 0.0
    att_speed = 4.0
    sus_speed = 80.0
    soft_clip = True

    idx = 1
    while idx < len(ts_params):
      arg = ts_params[idx]
      if arg == "--attack" and idx + 1 < len(ts_params):
        attack = float(ts_params[idx + 1])
        idx += 2
      elif arg == "--sustain" and idx + 1 < len(ts_params):
        sustain = float(ts_params[idx + 1])
        idx += 2
      elif arg == "--attack-speed" and idx + 1 < len(ts_params):
        att_speed = float(ts_params[idx + 1])
        idx += 2
      elif arg == "--sustain-speed" and idx + 1 < len(ts_params):
        sus_speed = float(ts_params[idx + 1])
        idx += 2
      elif arg == "--no-soft-clip":
        soft_clip = False
        idx += 1
      elif not arg.startswith("-") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1

    print(f"[*] Processing transient attack and sustain shaping on {inp}...")
    res = transient_shaper.run_transient_shaping(
        inp, output_path=out, attack_db=attack, sustain_db=sustain,
        attack_speed_ms=att_speed, sustain_speed_ms=sus_speed, soft_clip=soft_clip
    )
    print("=" * 60)
    print("  AUDIOPHILE TRANSIENT SHAPER & DRUM PUNCH STUDIO")
    print("=" * 60)
    print(f"Input File    : {res['input_path']}")
    print(f"Output File   : {res['output_path']}")
    print(f"Attack Gain   : {res['attack_db']:+.1f} dB (speed: {att_speed:.1f}ms)")
    print(f"Sustain Gain  : {res['sustain_db']:+.1f} dB (speed: {sus_speed:.1f}ms)")
    print(f"In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
    print(f"Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
    print(f"Duration      : {res['duration_sec']:.2f}s @ {res['sample_rate']} Hz")
    print("=" * 60)
    return

  if args.binaural is not None:
    import binaural_virtualizer
    bin_params = list(args.binaural) + list(unknown)
    if not bin_params:
      print("[-] Error: --binaural requires an input audio file.")
      print("    Usage: python sonance.py --binaural <audio_file> [output_file] [--preset control_room] [--angle 30] [--distance 1.8]")
      return
    inp = bin_params[0]
    out = None
    preset = "control_room"
    angle = 30.0
    dist = 1.8
    crossfeed = 1.0
    ambience = 0.35

    idx = 1
    while idx < len(bin_params):
      arg = bin_params[idx]
      if arg == "--preset" and idx + 1 < len(bin_params):
        preset = bin_params[idx + 1]
        idx += 2
      elif arg == "--angle" and idx + 1 < len(bin_params):
        angle = float(bin_params[idx + 1])
        idx += 2
      elif arg == "--distance" and idx + 1 < len(bin_params):
        dist = float(bin_params[idx + 1])
        idx += 2
      elif arg == "--crossfeed" and idx + 1 < len(bin_params):
        crossfeed = float(bin_params[idx + 1])
        idx += 2
      elif arg == "--ambience" and idx + 1 < len(bin_params):
        ambience = float(bin_params[idx + 1])
        idx += 2
      elif not arg.startswith("-") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1

    print(f"[*] Simulating binaural 3D studio control room monitor space for {inp}...")
    res = binaural_virtualizer.run_binaural_virtualization(
        inp, output_path=out, speaker_angle_deg=angle,
        distance_m=dist, crossfeed_amount=crossfeed,
        room_ambience=ambience, preset=preset
    )
    print("=" * 60)
    print("  BINAURAL 3D ROOM & HEADPHONE VIRTUALIZER STUDIO")
    print("=" * 60)
    print(f"Input File    : {res['input_path']}")
    print(f"Output File   : {res['output_path']}")
    print(f"Room Preset   : {res['preset']}")
    print(f"Speaker Angle : {res['speaker_angle_deg']:.1f} deg | Distance: {res['distance_m']:.1f} m")
    print(f"Woodworth ITD : {res['itd_ms']:.2f} ms ({res['itd_samples']} samples)")
    print(f"In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
    print(f"Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
    print(f"Duration      : {res['duration_sec']:.2f}s @ {res['sample_rate']} Hz")
    print("=" * 60)
    return

  if args.gate is not None:
    import audio_noisegate
    gate_params = list(args.gate) + list(unknown)
    if not gate_params:
      print("[-] Error: --gate requires an input audio file.")
      print("    Usage: python sonance.py --gate <audio_file> [output_file] [--threshold -40] [--reduction -60] [--ratio 10]")
      return
    inp = gate_params[0]
    out = None
    thresh = -40.0
    reduc = -60.0
    ratio = 10.0
    att = 1.5
    hold = 40.0
    rel = 120.0
    look = 2.0

    idx = 1
    while idx < len(gate_params):
      arg = gate_params[idx]
      if arg == "--threshold" and idx + 1 < len(gate_params):
        thresh = float(gate_params[idx + 1])
        idx += 2
      elif arg == "--reduction" and idx + 1 < len(gate_params):
        reduc = float(gate_params[idx + 1])
        idx += 2
      elif arg == "--ratio" and idx + 1 < len(gate_params):
        ratio = float(gate_params[idx + 1])
        idx += 2
      elif arg == "--attack" and idx + 1 < len(gate_params):
        att = float(gate_params[idx + 1])
        idx += 2
      elif arg == "--hold" and idx + 1 < len(gate_params):
        hold = float(gate_params[idx + 1])
        idx += 2
      elif arg == "--release" and idx + 1 < len(gate_params):
        rel = float(gate_params[idx + 1])
        idx += 2
      elif arg == "--lookahead" and idx + 1 < len(gate_params):
        look = float(gate_params[idx + 1])
        idx += 2
      elif not arg.startswith("-") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1

    print(f"[*] Applying lookahead noise gate & downward expander on {inp}...")
    res = audio_noisegate.run_noise_gate(
        inp, output_path=out, threshold_db=thresh,
        reduction_db=reduc, ratio=ratio, attack_ms=att,
        hold_ms=hold, release_ms=rel, lookahead_ms=look
    )
    print("=" * 60)
    print("  BROADCAST AUDIO NOISE GATE & DOWNWARD EXPANDER STUDIO")
    print("=" * 60)
    print(f"Input File    : {res['input_path']}")
    print(f"Output File   : {res['output_path']}")
    print(f"Threshold     : {res['threshold_db']:.1f} dBFS (Floor: {res['reduction_db']:.1f} dB)")
    print(f"Timing (A/H/R): {res['attack_ms']:.1f}ms / {res['hold_ms']:.1f}ms / {res['release_ms']:.1f}ms")
    print(f"Lookahead     : {res['lookahead_ms']:.1f}ms (Gated Duration: {res['attenuation_pct']}%)")
    print(f"In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
    print(f"Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
    print(f"Duration      : {res['duration_sec']:.2f}s @ {res['sample_rate']} Hz")
    print("=" * 60)
    return

  if args.echo is not None:
    import tape_echo_delay
    echo_params = list(args.echo) + list(unknown)
    if not echo_params:
      print("[-] Error: --echo requires an input audio file.")
      print("    Usage: python sonance.py --echo <audio_file> [output_file] [--delay 375] [--feedback 45] [--damping 3800] [--mix 35]")
      return
    inp = echo_params[0]
    out = None
    delay = 375.0
    fb = 45.0
    damp = 3800.0
    flutter = 0.12
    drive = 1.3
    mix = 35.0
    ping_pong = True

    idx = 1
    while idx < len(echo_params):
      arg = echo_params[idx]
      if arg == "--delay" and idx + 1 < len(echo_params):
        delay = float(echo_params[idx + 1])
        idx += 2
      elif arg == "--feedback" and idx + 1 < len(echo_params):
        fb = float(echo_params[idx + 1])
        idx += 2
      elif arg == "--damping" and idx + 1 < len(echo_params):
        damp = float(echo_params[idx + 1])
        idx += 2
      elif arg == "--flutter" and idx + 1 < len(echo_params):
        flutter = float(echo_params[idx + 1])
        idx += 2
      elif arg == "--drive" and idx + 1 < len(echo_params):
        drive = float(echo_params[idx + 1])
        idx += 2
      elif arg == "--mix" and idx + 1 < len(echo_params):
        mix = float(echo_params[idx + 1])
        idx += 2
      elif arg == "--no-ping-pong":
        ping_pong = False
        idx += 1
      elif not arg.startswith("-") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1

    print(f"[*] Emulating stereo ping-pong tape echo & analog delay on {inp}...")
    res = tape_echo_delay.run_tape_echo(
        inp, output_path=out, delay_ms=delay,
        feedback_pct=fb, damping_hz=damp, flutter_pct=flutter,
        drive=drive, dry_wet_pct=mix, ping_pong=ping_pong
    )
    print("=" * 60)
    print("  STEREO PING-PONG & MULTI-TAP TAPE ECHO STUDIO")
    print("=" * 60)
    print(f"Input File    : {res['input_path']}")
    print(f"Output File   : {res['output_path']}")
    print(f"Delay / Feed  : {res['delay_ms']:.1f}ms | Feedback: {res['feedback_pct']:.1f}%")
    print(f"Mode / Damp   : {'Stereo Ping-Pong' if res['ping_pong'] else 'Standard Stereo'} | Damping: {res['damping_hz']:.0f} Hz")
    print(f"Dry/Wet Mix   : {res['dry_wet_pct']:.1f}% (Drive: {res['drive']:.1f}x, Flutter: {res['flutter_pct']:.2f}%)")
    print(f"In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
    print(f"Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
    print(f"Duration      : {res['duration_sec']:.2f}s @ {res['sample_rate']} Hz")
    print("=" * 60)
    return

  if args.package_release is not None:
    import release_packager
    pkg_params = list(args.package_release) + list(unknown)
    create_zip = False
    verify_only = False
    out_dir = None

    idx = 0
    while idx < len(pkg_params):
      arg = pkg_params[idx]
      if arg == "--zip":
        create_zip = True
        idx += 1
      elif arg in ["--verify-only", "--audit-only"]:
        verify_only = True
        idx += 1
      elif arg == "--out-dir" and idx + 1 < len(pkg_params):
        out_dir = pkg_params[idx + 1]
        idx += 2
      else:
        idx += 1

    print("=" * 70)
    print(f"  SONANCE AUDIOPHILE WORKSTATION v{release_packager.APP_VERSION}")
    print("  Universal Release Packaging & Manifest Auditor Studio")
    print("=" * 70)
    print("[*] Auditing all 27 phase engines and computing manifests...")

    res = release_packager.audit_and_package(
        output_dir=out_dir,
        create_zip=create_zip,
        verify_only=verify_only
    )

    audit = res["audit"]
    print(f"[+] Total Modules Audited : {audit['total_modules']}")
    print(f"[+] Modules Passed        : {audit['passed_count']}")
    print(f"[+] Modules Failed        : {audit['failed_count']}")
    print(f"[+] Overall Integrity     : {audit['integrity_percent']:.1f}%")

    if audit["failed"]:
      print("\n[-] Module Integrity Warnings:")
      for f in audit["failed"]:
        print(f"    - {f['module']}: {f['error']}")

    if not verify_only and res.get("manifests"):
      print("\n[+] Cryptographic Manifests:")
      print(f"    - SHA-256 Manifest : {res['manifests']['sha256sum']}")
      print(f"    - MD5 Manifest     : {res['manifests']['md5sum']}")
      print(f"    - JSON Metadata    : {res['manifests']['manifest']}")
      print(f"[+] Repository Scope   : {res['total_files']} files ({res['total_bytes_formatted']})")

      if res.get("zip_package"):
        print(f"[+] Distribution Bundle: {res['zip_package']}")

    print("=" * 70)
    print("  RELEASE OPERATION COMPLETE")
    print("=" * 70)
    return

  if args.generate_manual is not None:
    import docs_generator
    man_params = list(args.generate_manual) + list(unknown)
    out_path = None
    open_browser = False

    idx = 0
    while idx < len(man_params):
      arg = man_params[idx]
      if arg == "--open":
        open_browser = True
        idx += 1
      elif not arg.startswith("-") and out_path is None:
        out_path = arg
        idx += 1
      else:
        idx += 1

    print("=" * 70)
    print(f"  SONANCE AUDIOPHILE WORKSTATION v{docs_generator.APP_VERSION}")
    print("  Offline Audiophile Guide & Workstation Manual Studio")
    print("=" * 70)
    print("[*] Generating standalone interactive manual for all 27 phases...")

    res = docs_generator.generate_offline_manual(output_path=out_path)
    print(f"[+] Manual Generated Successfully: {res['output_path']}")
    print(f"[+] Handbook Scope : {res['total_phases']} Phases Documented ({res['file_size_formatted']})")
    print("=" * 70)

    if open_browser:
      print("[*] Launching manual in default web browser...")
      import webbrowser
      webbrowser.open(f"file://{os.path.abspath(res['output_path'])}")
    return

  if args.vst_scan:
    import plugin_host
    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v2.8.0")
    print("  Phase 28: VST3 & CLAP Audio Plugin Scanner")
    print("=" * 70)
    plugins = plugin_host.scan_installed_plugins()
    print(f"[+] Total Available Plugins Found: {len(plugins)}")
    print("-" * 70)
    for p in plugins:
      origin = "[VIRTUAL]" if p.get("is_virtual") else "[HOST]"
      print(f"  {origin:<9} | {p['format']:<12} | {p['name']:<35} | {p['category']}")
    print("=" * 70)
    return

  if args.vst_rack is not None:
    import plugin_host
    rack_params = list(args.vst_rack) + list(unknown)
    if not rack_params:
      print("[-] Error: --vst-rack requires an input audio file.")
      print("    Usage: python sonance.py --vst-rack <audio_file> [output_file] [--preset mastering_bus|vocal_magic|analog_space]")
      return
    inp = rack_params[0]
    out = None
    preset_name = "mastering_bus"

    idx = 1
    while idx < len(rack_params):
      arg = rack_params[idx]
      if arg == "--preset" and idx + 1 < len(rack_params):
        preset_name = rack_params[idx + 1]
        idx += 2
      elif not arg.startswith("-") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v2.8.0")
    print("  Phase 28: VST3 & CLAP Audio Plugin Host & Rack Studio")
    print("=" * 70)
    print(f"[*] Processing {inp} through VST rack preset '{preset_name}'...")

    slots = plugin_host.FACTORY_PRESETS.get(preset_name, plugin_host.FACTORY_PRESETS["mastering_bus"])["slots"]
    res = plugin_host.process_plugin_rack(inp, output_path=out, rack_slots=slots)

    print(f"[+] Input File    : {res['input_path']}")
    print(f"[+] Output File   : {res['output_path']}")
    print(f"[+] In Peak/RMS   : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
    print(f"[+] Out Peak/RMS  : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
    print(f"[+] Crest Factor  : {res['crest_factor_db']:.2f} dB")
    print(f"[+] Render Time   : {res['elapsed_sec']:.2f}s ({res['duration_sec']:.1f}s @ {res['sample_rate']} Hz)")
    print("-" * 70)
    print("  RACK CHAIN SLOTS:")
    for s in res["slot_reports"]:
      print(f"    Slot {s['slot']}: {s['plugin_id']} -> {s['status']} (Mix: {s['dry_wet']})")
    print("=" * 70)
    return

  if args.spatial_714 is not None:
    import spatial_multichannel
    atmos_params = list(args.spatial_714) + list(unknown)
    if not atmos_params:
      print("[-] Error: --spatial-714 requires an input audio file.")
      print("    Usage: python sonance.py --spatial-714 <audio_file> [output_file] [--mode binaural|discrete] [--format 7.1.4|7.1|5.1] [--lfe-cutoff 80] [--height 0.35]")
      return
    inp = atmos_params[0]
    out = None
    mode = "binaural"
    format_type = "7.1.4"
    lfe_cut = 80.0
    height = 0.35
    spread = 1.15

    idx = 1
    while idx < len(atmos_params):
      arg = atmos_params[idx]
      if arg == "--mode" and idx + 1 < len(atmos_params):
        mode = atmos_params[idx + 1]
        idx += 2
      elif arg == "--format" and idx + 1 < len(atmos_params):
        format_type = atmos_params[idx + 1]
        idx += 2
      elif arg == "--lfe-cutoff" and idx + 1 < len(atmos_params):
        lfe_cut = float(atmos_params[idx + 1])
        idx += 2
      elif arg == "--height" and idx + 1 < len(atmos_params):
        height = float(atmos_params[idx + 1])
        idx += 2
      elif arg == "--spread" and idx + 1 < len(atmos_params):
        spread = float(atmos_params[idx + 1])
        idx += 2
      elif not arg.startswith("-") and out is None:
        out = arg
        idx += 1
      else:
        idx += 1

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v2.9.0")
    print("  Phase 29: Dolby Atmos 7.1.4 Bed Spatializer & Multichannel Renderer")
    print("=" * 70)
    print(f"[*] Rendering {inp} into {format_type} Spatial Audio ({mode.upper()} mode)...")

    res = spatial_multichannel.render_spatial_714(
        inp,
        output_path=out,
        mode=mode,
        format_type=format_type,
        lfe_cutoff_hz=lfe_cut,
        height_level=height,
        spread=spread,
    )

    print(f"[+] Input File       : {res['input_path']}")
    print(f"[+] Output File      : {res['output_path']}")
    print(f"[+] Render Mode      : {res['mode'].capitalize()} ({res['format']} bed, {res['channels']} channels)")
    print(f"[+] LFE Crossover    : {res['lfe_cutoff_hz']:.1f} Hz (4th-order Linkwitz-Riley alignment)")
    print(f"[+] Height Ambience  : {res['height_level_pct']:.1f}% overhead energy")
    print(f"[+] Surround Spread  : {res['spread_pct']:.1f}%")
    print(f"[+] In Peak / RMS    : {res['in_peak_dbfs']:.2f} dBFS / {res['in_rms_dbfs']:.2f} dBFS")
    print(f"[+] Out Peak / RMS   : {res['out_peak_dbfs']:.2f} dBFS / {res['out_rms_dbfs']:.2f} dBFS")
    print(f"[+] Render Time      : {res['elapsed_sec']:.2f}s ({res['duration_sec']:.1f}s @ {res['sample_rate']} Hz)")
    print("=" * 70)
    return

  if args.console is not None:
    import console_channel_strip
    params = list(args.console) + list(unknown)
    if not params:
      print("[-] Error: --console requires an input audio file.")
      print("    Usage: python sonance.py --console <audio_file> [output_file] [--preset <name>]")
      return

    inp = params[0]
    out = None
    preset = "master_bus_glue"
    threshold = None
    ratio = None
    attack = None
    release = None
    hpf = None
    makeup = None
    dry_wet = None
    drive = None
    warmth = None
    high_shelf = None
    low_shelf = None
    mid_gain = None
    crosstalk = -65.0
    noise = False
    gain = 0.0

    idx = 1
    while idx < len(params):
      item = params[idx]
      if item == "--preset" and idx + 1 < len(params):
        preset = params[idx + 1]
        idx += 2
      elif item == "--threshold" and idx + 1 < len(params):
        threshold = float(params[idx + 1])
        idx += 2
      elif item == "--ratio" and idx + 1 < len(params):
        ratio = float(params[idx + 1])
        idx += 2
      elif item == "--attack" and idx + 1 < len(params):
        attack = float(params[idx + 1])
        idx += 2
      elif item == "--release" and idx + 1 < len(params):
        release = float(params[idx + 1])
        idx += 2
      elif item == "--hpf" and idx + 1 < len(params):
        hpf = float(params[idx + 1])
        idx += 2
      elif item == "--makeup" and idx + 1 < len(params):
        makeup = float(params[idx + 1])
        idx += 2
      elif item == "--dry-wet" and idx + 1 < len(params):
        dry_wet = float(params[idx + 1])
        idx += 2
      elif item == "--drive" and idx + 1 < len(params):
        drive = float(params[idx + 1])
        idx += 2
      elif item == "--warmth" and idx + 1 < len(params):
        warmth = float(params[idx + 1])
        idx += 2
      elif item == "--high-shelf" and idx + 1 < len(params):
        high_shelf = float(params[idx + 1])
        idx += 2
      elif item == "--low-shelf" and idx + 1 < len(params):
        low_shelf = float(params[idx + 1])
        idx += 2
      elif item == "--mid-gain" and idx + 1 < len(params):
        mid_gain = float(params[idx + 1])
        idx += 2
      elif item == "--crosstalk" and idx + 1 < len(params):
        crosstalk = float(params[idx + 1])
        idx += 2
      elif item == "--noise":
        noise = True
        idx += 1
      elif item == "--gain" and idx + 1 < len(params):
        gain = float(params[idx + 1])
        idx += 2
      elif not item.startswith("-") and out is None:
        out = item
        idx += 1
      else:
        idx += 1

    custom_ssl = {}
    if threshold is not None:
      custom_ssl["threshold_db"] = threshold
    if ratio is not None:
      custom_ssl["ratio"] = ratio
    if attack is not None:
      custom_ssl["attack_ms"] = attack
    if release is not None:
      custom_ssl["release_sec"] = release
    if hpf is not None:
      custom_ssl["sidechain_hpf_hz"] = hpf
    if makeup is not None:
      custom_ssl["makeup_gain_db"] = makeup
    if dry_wet is not None:
      custom_ssl["dry_wet"] = dry_wet

    custom_neve = {}
    if drive is not None:
      custom_neve["preamp_drive"] = drive
    if warmth is not None:
      custom_neve["transformer_warmth"] = warmth
    if high_shelf is not None:
      custom_neve["high_shelf_gain_db"] = high_shelf
    if low_shelf is not None:
      custom_neve["low_shelf_gain_db"] = low_shelf
    if mid_gain is not None:
      custom_neve["mid_gain_db"] = mid_gain

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.0.0")
    print("  Phase 30: British Class-A Console Channel Strip & SSL G-Master Bus Studio")
    print("=" * 70)
    print(f"[*] Processing: {inp} through {preset.upper()} preset...")

    res = console_channel_strip.render_console_strip(
        input_path=inp,
        output_path=out,
        preset=preset,
        custom_ssl=custom_ssl or None,
        custom_neve=custom_neve or None,
        crosstalk_db=crosstalk,
        analog_noise=noise,
        output_gain_db=gain,
    )

    t = res["compressor_telemetry"]
    n = res["neve_summary"]

    print(f"[+] Output Master    : {res['output_path']}")
    print(f"[+] Audio Format     : 24-bit Linear PCM WAV @ {res['sample_rate']} Hz ({res['duration_sec']}s)")
    print(f"[+] Peak / RMS Level : {res['peak_db']} dBFS / {res['rms_db']} dBFS (Crest Factor: {res['crest_factor_db']} dB)")
    print(f"[+] SSL Gain Reduct. : -{t['max_gain_reduction_db']:.2f} dB max (Avg: -{t['avg_gain_reduction_db']:.2f} dB)")
    print(f"[+] SSL VCA Settings : Ratio {t['ratio']}:1 | Attack {t['attack_ms']}ms | Release {t['release']} | Makeup +{t['makeup_db']}dB")
    print(f"[+] Neve 1073 Preamp : Drive {n['drive']}x | Low {n['low_shelf']} | Mid {n['mid_band']} | High {n['high_shelf']}")
    print("=" * 70)
    return

  if args.hoa is not None:
    import ambisonic_hoa
    params = list(args.hoa) + list(unknown)
    if not params:
      print("[-] Error: --hoa requires an input audio file.")
      print("    Usage: python sonance.py --hoa <audio_file> [output_file] [--order 1|2|3] [--mode binaural|bformat] [--trajectory <type>]")
      return

    inp = params[0]
    out = None
    order = 3
    mode = "binaural"
    trajectory = "orbit_helix"
    azimuth = 0.0
    elevation = 0.0
    period = 12.0

    idx = 1
    while idx < len(params):
      item = params[idx]
      if item == "--order" and idx + 1 < len(params):
        order = int(params[idx + 1])
        idx += 2
      elif item == "--mode" and idx + 1 < len(params):
        mode = params[idx + 1].lower()
        idx += 2
      elif item in ("--trajectory", "--motion") and idx + 1 < len(params):
        trajectory = params[idx + 1].lower()
        idx += 2
      elif item in ("--azimuth", "--azim") and idx + 1 < len(params):
        azimuth = float(params[idx + 1])
        idx += 2
      elif item in ("--elevation", "--elev") and idx + 1 < len(params):
        elevation = float(params[idx + 1])
        idx += 2
      elif item in ("--period", "--orbit") and idx + 1 < len(params):
        period = float(params[idx + 1])
        idx += 2
      elif not item.startswith("-") and out is None:
        out = item
        idx += 1
      else:
        idx += 1

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.1.0")
    print("  Phase 31: Higher-Order Ambisonics & 360-Degree VR Spatializer Studio")
    print("=" * 70)
    print(f"[*] Input Source     : {inp}")
    print(f"[*] Ambisonic Order  : {order} ({ (order + 1)**2 } Spherical Harmonics Channels)")
    print(f"[*] Output Mode      : {mode.upper()}")
    print(f"[*] 3D Trajectory    : {trajectory.upper()} ({period}s orbit)")
    if trajectory == "fixed":
      print(f"[*] Target Position  : Azimuth {azimuth:+.1f} deg | Elevation {elevation:+.1f} deg")

    res = ambisonic_hoa.render_ambisonic_hoa(
        input_path=inp,
        output_path=out,
        order=order,
        mode=mode,
        trajectory_type=trajectory,
        base_azimuth_deg=azimuth,
        base_elevation_deg=elevation,
        orbit_period_sec=period,
    )

    print(f"[+] Output Master    : {res['output_path']}")
    print(f"[+] Audio Format     : 24-bit Linear PCM WAV @ {res['sample_rate']} Hz ({res['duration_sec']}s)")
    print(f"[+] Channels Exported: {res['channels']} ({res['mode_label']})")
    print(f"[+] Peak / RMS Level : {res['peak_dbfs']} dBFS / {res['rms_dbfs']} dBFS")
    print("=" * 70)
    return

  if args.bass is not None:
    import subharmonic_bass
    params = list(args.bass) + list(unknown)
    if not params:
      print("[-] Error: --bass requires an input audio file.")
      print("    Usage: python sonance.py --bass <audio_file> [output_file] [--preset <name>] [--sub-24-36 <val>] [--sub-36-56 <val>] [--maxxbass <val>]")
      return

    inp = params[0]
    out = None
    preset = "club_sub_boom"
    sub_1 = None
    sub_2 = None
    maxxbass = None
    mb_cutoff = None
    drive = None
    hpf = None
    monomaker = None
    mix = None
    gain = 0.0

    idx = 1
    while idx < len(params):
      item = params[idx]
      if item == "--preset" and idx + 1 < len(params):
        preset = params[idx + 1]
        idx += 2
      elif item in ("--sub-24-36", "--sub1") and idx + 1 < len(params):
        sub_1 = float(params[idx + 1])
        idx += 2
      elif item in ("--sub-36-56", "--sub2") and idx + 1 < len(params):
        sub_2 = float(params[idx + 1])
        idx += 2
      elif item in ("--maxxbass", "--harmonics") and idx + 1 < len(params):
        maxxbass = float(params[idx + 1])
        idx += 2
      elif item == "--maxxbass-cutoff" and idx + 1 < len(params):
        mb_cutoff = float(params[idx + 1])
        idx += 2
      elif item == "--drive" and idx + 1 < len(params):
        drive = float(params[idx + 1])
        idx += 2
      elif item in ("--subsonic-hpf", "--hpf") and idx + 1 < len(params):
        hpf = float(params[idx + 1])
        idx += 2
      elif item in ("--monomaker", "--mono") and idx + 1 < len(params):
        monomaker = float(params[idx + 1])
        idx += 2
      elif item in ("--mix", "--dry-wet") and idx + 1 < len(params):
        mix = float(params[idx + 1])
        idx += 2
      elif item in ("--gain", "--makeup") and idx + 1 < len(params):
        gain = float(params[idx + 1])
        idx += 2
      elif not item.startswith("-") and out is None:
        out = item
        idx += 1
      else:
        idx += 1

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.2.0")
    print("  Phase 32: Psychoacoustic Subharmonic Bass & Missing Fundamental Studio")
    print("=" * 70)
    print(f"[*] Input Source     : {inp}")
    print(f"[*] Preset Selected  : {preset.upper()}")

    res = subharmonic_bass.render_subharmonic_bass(
        input_path=inp,
        output_path=out,
        preset=preset,
        sub_24_36_gain=sub_1,
        sub_36_56_gain=sub_2,
        maxxbass_intensity=maxxbass,
        maxxbass_cutoff_hz=mb_cutoff,
        tube_drive=drive,
        subsonic_hpf_hz=hpf,
        monomaker_hz=monomaker,
        dry_wet=mix,
        output_gain_db=gain,
    )

    s = res["settings"]
    print(f"[+] Output Master    : {res['output_path']}")
    print(f"[+] Audio Format     : 24-bit Linear PCM WAV @ {res['sample_rate']} Hz ({res['duration_sec']}s)")
    print(f"[+] In Peak / RMS    : {res['in_peak_dbfs']} dBFS / {res['in_rms_dbfs']} dBFS")
    print(f"[+] Out Peak / RMS   : {res['out_peak_dbfs']} dBFS / {res['out_rms_dbfs']} dBFS (Sub Energy: {res['sub_energy_gain_db']:+0.2f} dB)")
    print(f"[+] Subharmonics     : 24-36Hz: {s['sub_24_36_gain']:.2f} ({res['sub_1_rms_dbfs']} dBFS) | 36-56Hz: {s['sub_36_56_gain']:.2f} ({res['sub_2_rms_dbfs']} dBFS)")
    print(f"[+] MaxxBass Missing : Intensity: {s['maxxbass_intensity']:.2f} | HPF Cutoff: {s['maxxbass_cutoff_hz']:.0f} Hz ({res['maxxbass_rms_dbfs']} dBFS)")
    print(f"[+] Low-End Shaping  : Subsonic HPF: {s['subsonic_hpf_hz']:.0f} Hz | Monomaker: {s['monomaker_hz']:.0f} Hz | Tube Drive: {s['tube_drive']:.2f}x")
    print("=" * 70)
    return

  if args.soothe is not None:
    import resonance_suppressor
    params = list(args.soothe) + list(unknown)
    if not params:
      print("[-] Error: --soothe requires an input audio file.")
      print("    Usage: python sonance.py --soothe <audio_file> [output_file] [--preset <name>] [--depth <val>] [--threshold <dB>] [--listen]")
      return

    inp = params[0]
    out = None
    preset = "tame_harshness"
    depth = None
    threshold = None
    sharpness = None
    low_cut = None
    high_cut = None
    listen = False
    mix = None
    gain = 0.0

    idx = 1
    while idx < len(params):
      item = params[idx]
      if item == "--preset" and idx + 1 < len(params):
        preset = params[idx + 1]
        idx += 2
      elif item in ("--depth", "-d") and idx + 1 < len(params):
        depth = float(params[idx + 1])
        idx += 2
      elif item in ("--threshold", "-t") and idx + 1 < len(params):
        threshold = float(params[idx + 1])
        idx += 2
      elif item in ("--sharpness", "-q") and idx + 1 < len(params):
        sharpness = float(params[idx + 1])
        idx += 2
      elif item == "--low-cut" and idx + 1 < len(params):
        low_cut = float(params[idx + 1])
        idx += 2
      elif item == "--high-cut" and idx + 1 < len(params):
        high_cut = float(params[idx + 1])
        idx += 2
      elif item in ("--listen", "--delta"):
        listen = True
        idx += 1
      elif item in ("--mix", "--dry-wet") and idx + 1 < len(params):
        mix = float(params[idx + 1])
        idx += 2
      elif item in ("--gain", "--makeup") and idx + 1 < len(params):
        gain = float(params[idx + 1])
        idx += 2
      elif not item.startswith("-") and out is None:
        out = item
        idx += 1
      else:
        idx += 1

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.3.0")
    print("  Phase 33: Dynamic Spectral Resonance Suppressor & Surgical De-Resonator")
    print("=" * 70)
    print(f"[*] Input Source     : {inp}")
    print(f"[*] Preset Selected  : {preset.upper()}")
    if listen:
      print("[!] LISTEN MODE ACTIVE: Auditioning suppressed delta resonances only")

    res = resonance_suppressor.render_resonance_suppressor(
        input_path=inp,
        output_path=out,
        preset=preset,
        depth=depth,
        threshold_db=threshold,
        sharpness=sharpness,
        low_cut_hz=low_cut,
        high_cut_hz=high_cut,
        listen_mode=listen,
        dry_wet=mix,
        output_gain_db=gain,
    )

    s = res["settings"]
    print(f"[+] Output Master    : {res['output_path']}")
    print(f"[+] Audio Format     : 24-bit Linear PCM WAV @ {res['sample_rate']} Hz ({res['duration_sec']}s)")
    print(f"[+] Mode             : {res['mode_label']}")
    print(f"[+] Max Reduction    : {res['max_reduction_db']:.2f} dB (Avg: {res['avg_reduction_db']:.2f} dB)")
    print(f"[+] Focus Bandwidth  : {s['low_cut_hz']:.0f} Hz - {s['high_cut_hz']:.0f} Hz (Sharpness Q: {s['sharpness']:.1f}x)")
    if res["top_resonances"]:
      res_str = ", ".join([f"{r['freq_hz']} Hz ({r['intensity_score']})" for r in res["top_resonances"]])
      print(f"[+] Detected Resonances: {res_str}")
    print("=" * 70)
    return

  if args.vintage_compressor is not None:
    import vintage_compressor
    params = list(args.vintage_compressor) + list(unknown)
    if not params:
      print("[-] Error: --vintage-compressor requires an input audio file.")
      print("    Usage: python sonance.py --vintage-compressor <audio_file> [output_file] [--mode la2a|fairchild] [--preset <name>] [--reduction <0-100>] [--drive <1.0-2.5>]")
      return

    inp = params[0]
    out = None
    preset = "la2a_smooth_vocal"
    mode = None
    reduction = None
    hpf = None
    hf_emphasis = None
    tc = None
    drive = None
    makeup = None
    mix = None
    dual_mono = False

    idx = 1
    while idx < len(params):
      item = params[idx]
      if item == "--preset" and idx + 1 < len(params):
        preset = params[idx + 1]
        idx += 2
      elif item == "--mode" and idx + 1 < len(params):
        mode = params[idx + 1]
        idx += 2
      elif item in ("--reduction", "--pr") and idx + 1 < len(params):
        reduction = float(params[idx + 1])
        idx += 2
      elif item == "--hpf" and idx + 1 < len(params):
        hpf = float(params[idx + 1])
        idx += 2
      elif item in ("--hf-emphasis", "--r37"):
        hf_emphasis = True
        idx += 1
      elif item in ("--tc", "--time-constant") and idx + 1 < len(params):
        tc = int(params[idx + 1])
        idx += 2
      elif item in ("--drive", "--tube-drive") and idx + 1 < len(params):
        drive = float(params[idx + 1])
        idx += 2
      elif item in ("--makeup", "--gain") and idx + 1 < len(params):
        makeup = float(params[idx + 1])
        idx += 2
      elif item in ("--mix", "--dry-wet") and idx + 1 < len(params):
        mix = float(params[idx + 1])
        idx += 2
      elif item in ("--dual-mono", "--split"):
        dual_mono = True
        idx += 1
      elif not item.startswith("-") and out is None:
        out = item
        idx += 1
      else:
        idx += 1

    print("=" * 70)
    print("  SONANCE AUDIOPHILE WORKSTATION v3.4.0")
    print("  Phase 34: Vintage Optical & Variable-Mu Master Compressor Studio")
    print("=" * 70)
    print(f"[*] Input Source     : {inp}")
    print(f"[*] Preset Selected  : {preset.upper()}")

    stereo_link = not dual_mono
    res = vintage_compressor.render_vintage_compressor(
        input_path=inp,
        output_path=out,
        preset=preset,
        mode=mode,
        peak_reduction=reduction,
        sidechain_hpf_hz=hpf,
        hf_emphasis=hf_emphasis,
        time_constant=tc,
        tube_drive=drive,
        makeup_gain_db=makeup,
        dry_wet=mix,
        stereo_link=stereo_link,
    )

    s = res["settings"]
    print(f"[+] Output Master    : {res['output_path']}")
    print(f"[+] Audio Format     : 24-bit Linear PCM WAV @ {res['sample_rate']} Hz ({res['duration_sec']}s)")
    print(f"[+] Model Emulation  : {res['telemetry']['model']}")
    print(f"[+] Peak Gain Reduct : {res['max_gain_reduction_db']:.2f} dB (Avg: {res['avg_gain_reduction_db']:.2f} dB)")
    print(f"[+] Dynamics Crest   : {res['crest_factor_in_db']:.2f} dB -> {res['crest_factor_out_db']:.2f} dB")
    print(f"[+] Tube Drive Stage : {s['tube_drive']:.2f}x | Makeup: {s['makeup_gain_db']:+.1f} dB | Mix: {int(s['dry_wet']*100)}%")
    print("=" * 70)
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
