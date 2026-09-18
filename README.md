<div align="center">

# 🎵 Sonance

**The ultimate unified music suite — Stream, download Hi-Res lossless, and sing along with real-time synced lyrics.**

[![GitHub Release](https://img.shields.io/github/v/release/Sandeep2062/Sonance?style=for-the-badge&color=10b981&label=Release)](https://github.com/Sandeep2062/Sonance/releases)
[![License: GPL v3 with Commons Clause](https://img.shields.io/badge/License-GPLv3%20%2B%20Commons-blue?style=for-the-badge)](LICENSE)
[![Platform: Windows | macOS | Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-9333ea?style=for-the-badge)]()
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-0284c7?style=for-the-badge&logo=python)]()

---

<p align="center">
  <b>Sonance</b> merges the best features of <b>Spotube</b>, <b>FluentDL</b>, and <b>Synced Lyrics Downloader</b> into one cohesive, privacy-first desktop music application.
  <br>
  No subscriptions required. No ads. No telemetry. 100% focused on pure audio fidelity and seamless lyrics.
</p>

</div>

---

## 🌟 Key Pillars & Merged Capabilities

Sonance brings together three distinct open-source powerhouses:

```
                      ┌──────────────────────────────────────┐
                      │             SONANCE v2.1             │
                      └──────────────────┬───────────────────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         │                               │                               │
         ▼                               ▼                               ▼
  [ From Spotube ]                [ From FluentDL ]             [ From Synced Lyrics ]
  • Spotify Catalog & Metadata    • Deezer ARL (FLAC/320k)      • Direct LRCLIB & Genius
  • High-Bitrate Streaming        • Qobuz 24-bit Hi-Res Master  • Anti-Mismatch Duration Check
  • In-App Live Karaoke Player    • Spotify Developer OAuth     • Simultaneous .lrc Auto-Download
  • In-App Auto-Update Checker    • Batch Download Queue        • Spek-style Audio Quality Specs
  • Cross-Platform Releases       • ID3v2.4 & Vorbis Tagging    • Local Music Library Scanner
```

---

## ✨ Features

### 🎧 1. Multi-Source Streaming & Search (Spotube)
- **Unified Online Search**: Instantly query tracks and albums across Deezer, Spotify catalog, and YouTube.
- **Built-in Audio Player**: Seamless playback with instant seeking via HTTP byte-range audio streaming.
- **Real-Time Karaoke Sync**: Synchronized lyrics highlight word-for-word and line-for-line as the track plays.
- **Zero Account Requirement**: You can stream and search right out of the box without logging in.

### ⬇️ 2. Lossless & Hi-Res Batch Downloader (FluentDL)
- **Deezer Integration**: Provide your Deezer ARL to unlock direct FLAC (1411 kbps) and 320 kbps MP3 downloading.
- **Qobuz Hi-Res Master**: Connect using your Qobuz ID & token to download genuine 24-bit studio master audio files.
- **Spotify Library & Playlist Sync**: Link your Spotify developer credentials (`Client ID` & `Client Secret`) to import personal playlists and saved albums.
- **Batch Download Queue**: Multi-threaded queue manager showing live download speed, progress percentage, and task status.
- **Complete Tagging Engine**: Automatically embeds high-resolution album artwork, artist, title, album, year, and track numbers into MP3 (ID3v2.4), FLAC, and M4A containers.

### 📝 3. Simultaneous Synced Lyrics Auto-Download (Synced Lyrics)
- **The Signature Feature**: When any track is downloaded, Sonance **simultaneously** queries top lyrics databases (LRCLIB, Musixmatch, Megalobiz, NetEase, and Genius).
- **Anti-Mismatch Verification**: Compares lyrics timestamps with audio duration to prevent downloading mismatched lyrics.
- **Dual Storage**: Saves the timestamped `.lrc` file right alongside the audio file AND embeds the synchronized lyrics into the audio file tags.
- **Local Library Explorer**: Full-height artist & album tree browser, missing lyrics detector, and 1-click batch missing lyrics downloader.

### 📻 4. Social Scrobbling & Artist Insights (Last.fm & ListenBrainz)
- **Live Scrobbling**: Real-time "Now Playing" updates and automatic scrobble submissions after 50% or 4 minutes.
- **Artist Insights Modal**: View rich biographies, genre tags, listener statistics, and similar track recommendations.
- **Open-Source Compatibility**: Support for both Last.fm and decentralized ListenBrainz profiles.

### 🎚️ 5. 10-Band Studio Equalizer (DSP) & Discord RPC
- **Hardware DSP**: 10-Band BiquadFilterNodes (32 Hz to 16 kHz) with 8 studio presets (`Bass Boost`, `Rock`, `Pop`, `Jazz`, `Electronic`, `Classical`, `Vocal Booster`, `Flat`).
- **Discord Rich Presence**: Live playback profile card with track title, artist, album art, remaining time bar, and profile buttons.

### 🏷️ 6. Mp3tag Studio Visual Metadata & Cover Art Editor
- **Full Tag Editor (ID3v2.4 / Vorbis / MP4 / OGG)**: Visual metadata editing per-song directly from your local library.
- **Embedded Cover Art Manager**: Extract embedded album art as high-res preview, replace artwork from disk, or strip unwanted covers.
- **1-Click MusicBrainz & Deezer Auto-Fill**: Automatically fills missing album title, release year, genre, and high-resolution cover art directly from online open-music databases.

### 🎵 7. MusicBee-Grade Playback Engine & Live Sync Tuner
- **Live Lyrics Timing Offset Synchronizer**: Instant `[-0.5s]`, `[-0.1s]`, `[+0.1s]`, `[+0.5s]` live adjustment bar during playback, with 1-click permanent `.lrc` file saving.
- **DJ Crossfade & Gapless Transition**: 0 to 12 second smooth volume crossfade between consecutive tracks, plus intelligent zero-gap transition.
- **Sleep Timer**: 15m, 30m, 45m, 60m, Custom, or "End of Current Track" presets with a gentle 30-second volume fade-out.
- **Smart Stream & Offline Cache**: Pre-caches streamed tracks locally with deterministic SHA-256 hashing for instant offline replay and zero buffering.

### 🎛️ 8. Workstation Master: Mini-Player, Auto-DJ, Library Doctor & Visualizer
- **Floating Mini-Player & Desktop Lyrics Overlay**: Compact 380×240 glassmorphic widget pinned always-on-top, featuring glowing synchronized lyrics line, animated cover art, and playback controls.
- **Auto-DJ & Infinite Radio Mode**: Automatically discovers acoustically similar tracks from Last.fm and Deezer when your playlist ends, keeping playback going endlessly.
- **Studio Volume Normalizer & ReplayGain DSP**: Real-time Web Audio `DynamicsCompressorNode` smoothing out harsh volume jumps across streaming platforms and local files.
- **Library Doctor & Duplicate Audio Cleaner**: Scans your entire music collection, calculates a 0-100% Library Health Score, detects duplicates (with bitrate and lossless quality comparisons), and cleans redundant files. CLI access available via `python sonance.py --doctor [FOLDER]`.
- **Fullscreen Party Visualizer Mode**: Smooth high-FPS canvas spectrum visualizer with neon glow bars, animated backdrop, and centered real-time karaoke lyrics.

### 📱 9. Wireless Mobile Remote, Smart Playlists & Creative Studio DSP
- **Wi-Fi Mobile Remote & Cast Controller**: Integrated background HTTP/SSE server (`http://<local-ip>:5050`) allowing full playback control, volume slider, queue management, and **real-time synchronized lyrics right on any smartphone or tablet**. Includes an in-app QR code for instant camera scan connection!
- **Smart Dynamic Auto-Playlists Engine**: Computes virtual smart playlists live from library metadata: `Pure Lossless` (FLAC/WAV/ALAC), `Karaoke Ready` (.lrc verified), `Recently Added` (last 30 days), `Doctor's Queue`, and `Decades` (80s, 90s, 2000s, 2010s, 2020s). Includes 1-click `.m3u8` playlist export and CLI inspection via `python sonance.py --smart-playlists`.
- **Speed & Creative DSP Studio**: Dynamic audio playback rate slider (0.5x to 2.0x) and studio presets: **Master 1.0x**, **Nightcore 1.25x**, **Slowed + Reverb 0.85x** (powered by a synthetic stereo Web Audio convolver impulse response), and **Practice 0.75x**.
- **Desktop Keyboard Hotkeys & Hardware Media Keys**: Control playback anywhere with `Space` (Play/Pause), `Left`/`Right` (Seek $\pm 5$s), `Up`/`Down` (Volume $\pm 5\%$), `M` (Mute), `L` (Lyrics), `V` (Visualizer), `F11` (Fullscreen), and standard OS hardware media keys (`MediaPlayPause`, `MediaTrackNext`, `MediaTrackPrevious`).

### 🎤 10. Karaoke Sing DSP, Multilingual Lyrics Studio, Audio Transcoder & Wrapped Stats
- **Karaoke Vocal Reducer DSP (`🎤 Sing`)**: Real-time Web Audio Out-of-Phase Stereo (OOPS) center-channel vocal cancellation suppressing lead vocals on-the-fly while keeping stereo backing tracks and instruments vibrant.
- **Multilingual Lyrics Translation & Romanization Studio**: Instant Japanese Romaji (Hiragana/Katakana conversion) and Korean Latin Revised Romanization, with dual-line phonetic rendering in both the Fullscreen Karaoke Stage and Floating Mini-Player.
- **Lossless & Hi-Res Batch Audio Transcoder**: High-performance batch conversion engine between FLAC, WAV, MP3 (320k/256k/192k/128k), M4A, and OGG while preserving full ID3v2.4/Vorbis tags, embedded high-resolution album cover art, and companion `.lrc` lyrics files. Also accessible via CLI: `python sonance.py --transcode <source> [out_dir] [format] [bitrate]`.
- **Listening Stats Studio & "Sonance Wrapped"**: 100% private, local playback tracker computing total play counts, listening hours, active streaks, top artists, top songs, and audio quality distribution (% Lossless vs 320k vs streaming). Export summaries with 1 click or view in terminal via `python sonance.py --stats`.
- **Interactive Waveform Timeline**: Dynamic audio energy waveform scrubber canvas rendered live across the player progress bar.

### 💎 11. Visual LRC Studio, Acoustic Audio Fingerprinting, 3D Spatial DSP & Discographies
- **Visual Interactive LRC Studio & Live Time-Stamper**: Create and sync `.lrc` lyrics from scratch! Paste raw lyrics, listen along, and tap `Space` or `[Enter]` on each beat to stamp line-by-line timestamps in real-time with millisecond precision adjusters (`+0.1s`/`-0.1s`), and save directly to companion `.lrc` and embedded metadata.
- **Acoustic Audio Identification & Auto-Tagger (`audio_fingerprint.py`)**: Automatically recognizes unknown or untagged tracks (`Track01.mp3`, `recording.wav`) using acoustic fingerprint signatures and duration matching across online databases (iTunes, Deezer, MusicBrainz) to auto-populate Title, Artist, Album, Year, Genre, Track Number, and high-res cover art. Available via the desktop Tag Editor or CLI: `python sonance.py --identify <audio_file>`.
- **Headphone Binaural Crossfeed & 3D Spatial Stereo DSP**: Bauer/Chu crossfeed algorithm in Web Audio blending microsecond-delayed, low-pass crosstalk between channels to eliminate headphone acoustic fatigue, plus a real-time 3D Spatial Stereo Width slider (0% Mono to 200% Ultra-Wide 3D).
- **Artist Discography & Full-Album Downloader (`discography_scraper.py`)**: Explore complete artist discographies, inspect studio albums, EPs, and full tracklists, and batch-download entire albums with synchronized lyrics with 1 click. Also available via CLI: `python sonance.py --discography "Artist Name"`.
- **Podcast & Audiobook Smart Resuming**: Automatically saves and restores exact playback positions for long audio tracks (>15 minutes), displaying a 1-click "Resume from MM:SS" toast notification.

### 💿 12. CUE Sheet Lossless Splitter, Audio Cutter Studio, DAC Selector & Ambient Visuals
- **CUE Sheet Album Lossless Splitter & Virtual Track Engine (`cue_splitter.py`)**: Parse Red Book CD `.cue` index sheets, browse and play virtual tracks on-the-fly without copying files, or perform sample-accurate lossless physical track splitting with full metadata tagging and cover preservation. CLI: `python sonance.py --cue-split <cue_file> [out_dir] [format] [bitrate]`.
- **Visual Waveform Audio Cutter & Ringtone Studio (`audio_cutter.py`)**: Millisecond-accurate visual audio trimmer with draggable range bounds, customizable fade-in/fade-out curves (0.5s - 3.0s), loop preview, and export to iPhone ringtones (`.m4r`), MP3 (320 kbps), WAV, and M4A. CLI: `python sonance.py --trim <audio_file> <start_sec> <end_sec> [format] [out_file]`.
- **Hardware Audio Output Device Selector (DAC & Sink Selector)**: Direct hardware routing to external USB DACs, Bluetooth headphones, and studio monitors via the HTML5 Audio Sink API (`audio.setSinkId()`).
- **Ambient Fluid Album Art Mesh Canvas Backdrop**: Real-time breathing animated canvas mesh gradient extracting dominant color stops from the current playing album cover art.
- **Podcast & Audiobook Silence Skipper DSP**: Real-time silence detection automatically skipping or accelerating pauses > 1.2s in podcasts, audiobooks, and recorded lectures.

### 🔊 13. ReplayGain 2.0, Syllable Karaoke, Audio Dedup, CD Ripper & Spectrogram Waterfall
- **ReplayGain 2.0 & EBU R128 Loudness Scanner (`loudness_scanner.py`)**: ITU-R BS.1770 integrated loudness (LUFS), Loudness Range (LU), and True Peak (dBFS) measurement with standard ReplayGain tag embedding across MP3 (ID3v2 TXXX), FLAC (Vorbis Comments), and M4A. Configurable target loudness (-14 LUFS Streaming, -18 LUFS Audiophile, -23 LUFS EBU R128 Broadcast). CLI: `python sonance.py --scan-loudness <audio_file_or_dir> [-14.0] [--apply]`.
- **Synchronized Word-by-Word Syllable Karaoke Studio (`word_karaoke.py`)**: Advanced Enhanced LRC parser and word/syllable timing synthesizer rendering real-time Apple Music / Spotify Sing style glowing text sweep karaoke fills with zero CPU overhead.
- **Lossless Audio Duplicate Cleaner & Integrity Verifier (`audio_dedup.py`)**: Cross-format acoustic and metadata duplicate detection, fidelity scoring (Lossless 24/96 FLAC > 320k MP3 > 128k AAC), duplicate grouping, and safe redundant audio archiving. CLI: `python sonance.py --dedup <music_folder> [archive_dir]`.
- **Audio CD Ripper & DiscID AccurateRip Studio (`cd_ripper.py`)**: Physical optical CD drive detection, MusicBrainz DiscID querying, and bit-perfect extraction to FLAC, WAV, MP3, or M4A with metadata auto-tagging and companion synced `.lrc` download. CLI: `python sonance.py --rip-cd [drive_letter] [out_dir] [format]`.
- **Real-Time 2D Spectrogram Waterfall Visualizer**: Live scrolling FFT frequency-over-time thermal heatmap canvas (0 Hz to 24 kHz) integrated into the Spek technical specs modal.

### ☁️ 14. Subsonic Personal Cloud Streaming, Room EQ Convolution DSP & Universal Playlist Converter
- **Subsonic / Navidrome / Jellyfin Personal Cloud Streaming (`cloud_streamer.py`)**: Connect Sonance directly to self-hosted personal music servers with Subsonic API token authentication. Browse remote artist directories, stream losslessly over HTTP with auto-matched synchronized `.lrc` lyrics, and query remote cloud libraries. CLI: `python sonance.py --cloud-stream <server_url> <username> [password]`.
- **Acoustic Convolution IR Room Correction & Tube Preamp DSP (`room_eq.py`)**: Web Audio `ConvolverNode` engine loading real-world and synthesized acoustic Impulse Response (IR) profiles: *Abbey Studio Room* (early studio reflections), *Warm Vintage Tube Preamp* (even-order analog harmonic saturation), *Acoustic Concert Hall* (spatial diffusion), and *Audiophile Vinyl Curve* (stylus resonance). Supports custom `.wav` IR file loading with adjustable Wet/Dry mix.
- **Psychoacoustic Sub-Bass Harmonic Synthesizer DSP**: MaxxBass-style virtual fundamental generator creating upper harmonics from sub-bass frequencies (<80 Hz) so deep bass notes are vividly heard on laptop speakers, small monitors, and earphones without cone distortion.
- **Universal Multi-Format Playlist Converter (`playlist_converter.py`)**: Bidirectional playlist converter supporting `.m3u`, `.m3u8`, `.pls`, `.wpl` (Windows Media), `.xspf` (VLC/XML), and Spotify public playlist URL importing into local manifests or download queues. CLI: `python sonance.py --convert-playlist <input_file_or_url> [output_format] [output_file]`.
- **Bit-Perfect DAC Stream Telemetry**: Live bottom bar telemetry displaying DAC resolution: `24-bit / 96.0 kHz Hi-Res Direct`, `16-bit / 44.1 kHz Lossless`, or `Cloud Stream Direct`.

### 🎚️ 15. Stem Separator Studio, Lossless Authenticity Auditor & DJ Camelot Mixing
- **AI & Spectral Audio Stem Separator Studio (`vocal_separator.py`)**: Split any track into isolated, pristine stems: 2-Stem (**Vocals / Acapella** + **Instrumental / Backing**) or 4-Stem (**Vocals**, **Instrumental Backing**, **Bassline**, and **Drums & Percussion**). Features high-efficiency center-channel phase cancellation, formant bandpass filtering, pure-Python/NumPy fallback, and FFmpeg pipeline exporting to FLAC, WAV, or MP3. CLI: `python sonance.py --split-stems <audio_file> [out_dir] [2stems|4stems] [format]`.
- **Lossless Audio Authenticity Auditor & Brickwall Cutoff Inspector (`audio_auditor.py`)**: Detects "Fake Lossless" files (low-bitrate 128 kbps or 192 kbps lossy MP3s upscaled and re-encoded into FLAC or WAV containers) using FFT brickwall frequency analysis. Scans for telltale 16.0 kHz cutoffs (128k MP3), 19.5 kHz roll-offs (320k MP3), and ultrasonic bandwidth (> 20 kHz genuine CD / > 24 kHz Hi-Res Studio Master) with an authenticity confidence score (0-100%). CLI: `python sonance.py --audit <file_or_dir>`.
- **DJ Camelot Harmonic Key & BPM Beatmatcher Engine (`dj_mixer.py`)**: High-precision tempo tracking (BPM) via spectral onset autocorrelation and musical key detection using 12-semitone chromagram pitch-class profiling with Krumhansl-Schmuckler tonal correlation. Maps keys directly to standard Camelot Wheel codes (e.g. `8A / Am`, `8B / C`) and displays live harmonic mixing compatibility recommendations for seamless DJ transitions ($\pm 1$ step energy boost/drop, relative Major/Minor mood shift). CLI: `python sonance.py --analyze-key <audio_file>`.
- **Synchronized Guitar Chord Studio & Tab Companion (`chord_studio.py`)**: Displays real-time synchronized guitar chord progressions (`[Am]`, `[C]`, `[G]`, `[F]`) right above or alongside karaoke lyric lines in the Karaoke Stage. Includes interactive fretboard diagrams (6-string EADGBE fingerings) for 40+ popular chord voicings.
- **Live DJ Telemetry Badge**: Real-time tempo and key badge in the bottom player bar (`⚡ 128 BPM · 8A (Am)`) with 1-click access to harmonic transition pairings.

### 🎛️ 16. Audiophile Resampler, Pitch Transposer, Library Auto-Organizer & Monolithic Album Packer
- **Audiophile Polyphase Sinc Resampler & TPDF Dither Studio (`audio_resampler.py`)**: High-fidelity sample rate conversion up to 192 kHz / 384 kHz utilizing bandlimited Kaiser-windowed sinc interpolation with triangular probability density function (TPDF) random dither and high-pass noise shaping ($e[n] - 0.75 e[n-1]$). Quantization noise is pushed into ultrasonic registers (>18 kHz) ensuring pristine bit-depth reductions (e.g. 24-bit to 16-bit) without harmonic distortion or limit cycles. CLI: `python sonance.py --resample <audio_file> <sample_rate> [bit_depth] [output_file]`.
- **Karaoke Vocal Pitch Transposer & Key Shifter (`pitch_shifter.py`)**: Real-time semitone pitch transposition ($\pm 6$ semitones) without tempo changes using an STFT phase vocoder and FFmpeg `rubberband`/`atempo` pipeline. Ideal for vocalists practicing songs outside their native vocal range or matching karaoke tracks to singing pitch. CLI: `python sonance.py --pitch-shift <audio_file> <semitones> [output_file]`.
- **MusicBee-Style Library Auto-Organizer & File Renamer (`library_organizer.py`)**: Rule-based library reorganization matching tracks by ID3/Vorbis tags into structured directories (`%artist%/[%year%] %album%/%track% - %title%`). Migrates companion `.lrc` synced lyrics and cover artwork, sanitizes Windows reserved characters (`<>:"/\|?*`), and features a dry-run preview before committing moves or copies. CLI: `python sonance.py --organize <folder> [--pattern "<pattern>"] [--execute] [--copy]`.
- **Lossless Monolithic Album Packer & CUE Archiver (`album_packer.py`)**: Merges loose album tracks into a single continuous, gapless FLAC or WAV image accompanied by an exact Red Book audio CD compliant CUE sheet (`mm:ss:ff` 75 fps sector index timing). Supports lossless unpacking of monolithic album images back into pristine tagged tracks. CLI: `python sonance.py --pack-album <folder> [output_flac]` and `python sonance.py --unpack-album <monolithic_flac> [output_dir]`.

### 📊 17. TT Dynamic Range Meter, DAP Synchronizer, A-B Phrase Looper & Word-by-Word Syllable Aligner
- **TT Dynamic Range (DR) Meter & Loudness War Crest Factor Analyzer (`dr_meter.py`)**: Official Pleasurize Music Foundation DR algorithm implementation ($DR4$ to $DR18+$). Analyzes True Peak (dBFS) and top-20% loudest 3-second block RMS levels to evaluate dynamic contrast and Crest Factor across stereo channels for tracks and entire albums. Generates detailed ASCII report summaries (`dr_report.txt`) and color-coded Loudness War diagnostic grades. CLI: `python sonance.py --dr-meter <file_or_dir>`.
- **Portable DAP, Walkman & USB Flash Storage Synchronizer (`device_sync.py`)**: Synchronizes music collections, smart playlists, and favorites to Sony Walkman, FiiO, Astell&Kern, and USB storage drives with auto-detected drive letters and volume labels. Features on-the-fly transcoding (Direct Lossless Copy, MP3 320k, MP3 256k, AAC 256k), FAT32/exFAT path sanitization, companion `.lrc` lyrics migration, and relative-path `.m3u8` playlist generation. CLI: `python sonance.py --sync-device <target_path> <source_dir> [--mode copy|mp3_320] [--playlist <name>]`.
- **Musician A-B Phrase Looper & Metronome Practice Studio (`ab_looper.py`)**: Millisecond-accurate A-B phrase looping for instrumentalists, vocalists, and ear-training. Features seamless micro-cosine crossfades preventing digital boundary clicks, synthesized metronome count-in click tracks (4 beats at adjustable BPM), loop repetition concatenation (1x to 16x), and loop sample audio export. CLI: `python sonance.py --loop <audio_file> <start_sec> <end_sec> [repeats] [--count-in] [output_file]`.
- **Enhanced Word-by-Word ELRC Syllable Aligner (`word_aligner.py`)**: Generates Apple Music and Spotify Sing style Enhanced LRC files (`<mm:ss.xx> word <mm:ss.xx> word`) by pairing acoustic spectral flux onset transient detection with phonetic syllable length weighting. Supports interactive spacebar tap-to-align in the desktop workstation and companion `.elrc` export. CLI: `python sonance.py --align-words <lrc_file> [audio_file] [output_elrc]`.

### 🎧 18. Phase 17: Headphone AutoEq, FLAC MD5 Verifier, DJ Auto-Mixer & Lyrics Aggregator
- **Headphone AutoEq & Harman Target Calibration Studio (`headphone_autoeq.py`)**: Calibrates headphone and IEM frequency response to the Harman 2020 Target curve. Includes 17+ audiophile profiles (Sennheiser HD 600/650/800 S, Sony WH-1000XM4/XM5, Apple AirPods Max/Pro 2, Beyerdynamic DT 770/990 Pro, Audio-Technica ATH-M50x, Moondrop Blessing 2/Aria/Chu, Hifiman Sundara/Edition XS) with negative preamp headroom compensation. Supports importing custom EqualizerAPO / Peace GraphicEQ & parametric `.txt` configs and 1-click application to the 10-band hardware equalizer. CLI: `python sonance.py --autoeq <model_key|--list>`.
- **Lossless FLAC Stream MD5 Integrity Auditor & Bit-Rot Scanner (`flac_verifier.py`)**: Native extraction of the 128-bit unencoded audio MD5 signature from the 34-byte FLAC `STREAMINFO` metadata block. Decodes raw uncompressed PCM samples to compute an exact MD5 checksum, catching silent bit rot, truncated downloads, hard drive sector degradation, and corrupted audio streams with individual and folder-wide library audit reports. CLI: `python sonance.py --verify-flac <flac_file_or_dir>`.
- **DJ Harmonic Auto-Mix & Phrase-Synced Crossfade Engine (`dj_automix.py`)**: Club-style continuous DJ set generator combining Camelot key harmonic matching with BPM phrase onset alignment. Features club bass-swap filter sweeps (outgoing track high-pass sweep paired with incoming low-pass opening) to eliminate low-end kick frequency clashes, customizable 8s–20s blend durations, and gapless master WAV export. CLI: `python sonance.py --automix <track1> <track2> ... [--trans <seconds>] [--output <file>]`.
- **Multi-Source Synced Lyrics Aggregator & Fusion Studio (`lyrics_aggregator.py`)**: Multi-provider lyrics engine aggregating LRCLIB, Deezer, and Megalobiz with intelligent timestamp scoring, fallback cascading, automatic Asian phonetic romanization (Romaji, Hangul, Pinyin), and a 1-click batch downloader that scans music libraries and automatically saves missing companion `.lrc` files. CLI: `python sonance.py --fetch-lyrics <artist> <title> [--romanize] [--output <file>]` and `python sonance.py --batch-lyrics <folder> [--overwrite]`.

### 🔬 19. Phase 18: Audio Bitstream Inspector, Vinyl/Tape Audio Restorer, Library Migrator & Lyrics Translator
- **Hi-Res Audio Stream Inspector & Bitstream Forensics (`audio_inspector.py`)**: Deep container and bitstream forensics across FLAC, WAV, MP3, AAC/M4A, OGG, Opus. Extracts exact uncompressed PCM metrics, compression ratios, LAME/FLAC/Apple encoder signatures, padding waste analysis, and formatted ASCII inspection cards. CLI: `python sonance.py --inspect-stream <audio_file> [--json]`.
- **Analog Audio Restoration & Vinyl De-Clicker / De-Hisser Studio (`audio_restorer.py`)**: Restoration DSP for vinyl record rips and analog cassette tapes. Features cubic spline impulsive de-clicking/de-popping, 50 Hz / 60 Hz AC mains ground hum notch filters, 18 Hz turntable motor rumble subsonic filtering, and high-frequency tape hiss spectral gating. CLI: `python sonance.py --restore-audio <input_file> <output_file> [--declick] [--dehum 50|60] [--derumble] [--dehiss]`.
- **Cross-Platform Library & Playlist Migrator (`library_migrator.py`)**: 1-click library and playlist importer migrating from iTunes / Apple Music XML (`iTunes Music Library.xml`), MusicBee library exports, Winamp, and Foobar2000 with intelligent fuzzy path reconciliation across drive letters and folders, star rating preservation, and `.m3u8` playlist export. CLI: `python sonance.py --migrate-library <library_xml> [--target-dir <dir>] [--output-playlist <file>]`.
- **Dual-Language Synchronized Lyrics Translator (`lyrics_translator.py`)**: Multi-lingual lyrics translator preserving millisecond timestamps to produce bilingual synchronized LRC files (`[mm:ss.xx] Original line \n [mm:ss.xx] (Translated line)`) across 50+ languages with 1-click companion `.lrc` export. CLI: `python sonance.py --translate-lyrics <lrc_file> [--lang <code>] [--translated-only] [--output <file>]`.

### 💿 20. Phase 19: AccurateRip CD Verifier, Playlist Doctor, 8D Spatial Audio Orbit & ReplayGain Normalizer
- **AccurateRip CD Integrity & Sample Offset Verifier (`accuraterip_verifier.py`)**: Computes official AccurateRip CRCv1, CRCv2, and DiscID signatures across CD audio PCM samples. Scans common CD drive read offsets (-1000 to +1000 samples, including +6, +12, +30, +102, +667) to identify uncorrected drive offsets and verify bit-perfect community accuracy. CLI: `python sonance.py --accuraterip <file_or_dir>`.
- **M3U / M3U8 Playlist Doctor & Dead Link Healer (`playlist_doctor.py`)**: Full health diagnosis for `.m3u`, `.m3u8`, and `.pls` playlists. Recursively indexes local music collections to heal broken paths across drive letters or reorganized directories, cleans duplicate tracks, and automatically upgrades lossy `.mp3` entries to `.flac` lossless files. CLI: `python sonance.py --heal-playlist <playlist> [--library-dir <dir>] [--output <file>] [--lossless]`.
- **Binaural 8D Spatial Audio Orbit & Ambisonic Panner DSP (`audio_8d_spatializer.py`)**: Synthesizes immersive 360-degree rotating binaural audio for headphones utilizing Interaural Time Difference (ITD microsecond fractional delays), Interaural Level Difference (ILD head-shadow filtering), and Haas room reflections with real-time Web Audio orbit playback and offline master rendering. CLI: `python sonance.py --spatial-8d <input_file> [output_file] [--orbit <sec>] [--depth <float>]`.
- **ReplayGain 2.0 Mass-Applier & True-Peak Hard Normalizer (`replaygain_normalizer.py`)**: Measures ITU-R BS.1770-4 / EBU R128 integrated loudness (LUFS) and True Peak (dBFS). Features non-destructive Track/Album Gain tag writing across FLAC, MP3 (TXXX), M4A, and OGG, as well as hard peak-limited volume normalization with a lookahead True-Peak brickwall limiter (-0.5 dBFS ceiling). CLI: `python sonance.py --normalize-gain <file_or_dir> [--mode tag|hard] [--target-lufs <float>]`.

### 🎚️ 21. Phase 20: Parametric Master EQ, Stereo Phase Meter, DAC Tester & Lyrics Drift Corrector
- **Audiophile Parametric 5-Band Master EQ Studio (`parametric_eq.py`)**: Robert Bristow-Johnson (RBJ) Audio EQ biquad filter equations with continuous frequency (20 Hz - 20 kHz), gain (±18 dB), Q factor (0.1 - 10.0), Low/High shelves, composite complex frequency response calculation ($H(f)$ in dB), live interactive SVG curve rendering, and audio filtering export to WAV/FLAC/MP3. CLI: `python sonance.py --parametric-eq <input_file> [output_file]`.
- **Audio Phase Correlation & Stereo Goniometer Studio (`phase_correlation.py`)**: Computes Pearson stereo phase correlation coefficient ($[-1.0, +1.0]$), stereo width (Side/Mid energy ratio), L/R balance tilt (dB), mono collapse loss, downsampled Lissajous vector scope oscilloscope coordinates, and 1-click inverted-phase / elliptical mono bass correction. CLI: `python sonance.py --phase-meter <audio_file> [--correct]`.
- **Audiophile DAC Bit-Perfect Test Tone & Jitter Generator (`dac_tester.py`)**: Synthesizes reference laboratory test signals for DAC linearity, jitter, and room calibration: Logarithmic Sine Sweeps (20 Hz - 20 kHz, -0.1 dBFS), SMPTE IMD (60 Hz + 7 kHz, 4:1), CCIF IMD (19 kHz + 20 kHz, 1:1), Julian Dunn J-Test (AES clock jitter provocation), Voss-McCartney Pink Noise (-3 dB/octave), and Dithered Digital Black Floor (-140 dBFS). Supports 16/24-bit PCM up to 192 kHz. CLI: `python sonance.py --test-tone <sweep|imd_smpte|imd_ccif|jtest|pink_noise|digital_black> [output] [--rate 96000] [--bits 24] [--dur 10]`.
- **Smart Lyrics Sync Offset Drift Corrector & Two-Point Re-Timer (`lyrics_retimer.py`)**: Eliminates cumulative timing drift across synced `.lrc` files via two-point linear slope calibration ($t_{\text{new}} = \alpha \cdot t_{\text{old}} + \beta$), tempo stretch factor compensation (e.g. PAL 25fps vs Film 23.976fps), uniform lead-in shifts, and companion `.lrc` export. CLI: `python sonance.py --retime-lyrics <lrc_file> <t1_old> <t1_new> <t2_old> <t2_new> [output_lrc]`.

### 📊 22. Phase 21: Hi-Res Spectrogram Analyzer, Dynamic Audio De-Clipper, Silence Track Splitter & Lyrics Video Maker
- **Hi-Res Audio Spectrogram & Bandwidth Cutoff Analyzer (`spectrum_analyzer.py`)**: Computes high-resolution STFT power spectral density (20 Hz - 96 kHz), spectral centroid (audio brightness), 85% & 95% energy rolloff, Wiener entropy (spectral flatness), and detects authentic Hi-Res vs. upsampled audio or lossy MP3 brickwall cutoffs (16 kHz, 18 kHz, 20 kHz). CLI: `python sonance.py --spectrum <audio_file> [--max-sec 60]`.
- **Multiband Dynamic Range Expander & Audio De-Clipper Studio (`audio_declipper.py`)**: Reconstructs harsh flat-topped digital clipping artifacts caused by the "Loudness War" using cubic Hermite spline interpolation, automatic lookahead headroom pre-attenuation (-1.0 dB to -8.0 dB), and multiband transient dynamic expansion (0.0 dB to +6.0 dB) to restore punch and snare bite. CLI: `python sonance.py --declip <audio_file> [output_file] [--expansion 2.0] [--headroom 4.0]`.
- **Smart Silence Audio Track Splitter & Auto-CUE Generator (`track_splitter.py`)**: Splits continuous vinyl record side digitizations, live concert recordings, and DJ sets into individual tagged tracks based on adaptive silence thresholding (-50 dBFS to -30 dBFS) and zero-crossing snapping to prevent clicks, with automatic Red Book `.cue` sheet export. CLI: `python sonance.py --auto-split <audio_file> [output_dir] [--threshold -42.0] [--min-silence 1.5]`.
- **Synchronized LRC Karaoke Video & Theater Generator (`lyrics_video_maker.py`)**: Transforms any audio track and synchronized `.lrc` into an animated karaoke presentation with glowing typography transitions and smooth vertical line scrolling, supporting both standalone HTML5 Karaoke Theater and MP4 video generation. CLI: `python sonance.py --lyrics-video <audio_file> [lrc_file] [output_video] [--resolution 1080p|720p]`.

### 🚀 23. Phase 22: High-Tap Sinc Upsampler, CUE Sheet Doctor, Room IR Synthesizer & ASS Karaoke Subtitles
- **Audiophile High-Tap Sinc Audio Upsampler & Apodizing Studio (`audio_upsampler.py`)**: Bandlimited Whittaker-Shannon polyphase sinc interpolation supporting up to 192 kHz / 384 kHz ultra Hi-Res, with selectable Linear Phase (zero phase distortion, symmetrical delay) and Minimum Phase (apodizing, zero pre-ringing, natural acoustic transient decay), Kaiser windowing (>120 dB stopband rejection), and 24-bit PCM WAV master export. CLI: `python sonance.py --upsample <audio_file> [output_file] [--rate 192000] [--filter linear|minimum]`.
- **Smart CUE Sheet Doctor, File Re-Aligner & Red Book Validator (`cue_fixer.py`)**: Audits and auto-heals broken `.cue` sheets, fixes missing or mismatched `FILE` references (e.g. `.wav` referenced when `.flac` is on disk), converts legacy encodings (Shift-JIS, CP1252, GBK) to UTF-8, fixes illegal sector frames ($f \ge 75$), verifies track index chronology, and computes per-track durations. CLI: `python sonance.py --fix-cue <cue_file> [target_audio] [--output <repaired_cue>]`.
- **Room Acoustic Impulse Response (IR) Generator & Reverb Synthesizer (`room_ir_synthesizer.py`)**: 3D image-source ray-tracing room acoustics simulator that synthesizes calibrated stereo impulse response (WAV) files from room dimensions ($L \times W \times H$), surface absorption ($\alpha$), and target RT60 reverberation times ($0.2\text{s} - 5.0\text{s}$) with frequency-dependent air damping and binaural ITD/ILD ear spacing. Fully compatible with Sonance's convolution engine. CLI: `python sonance.py --synthesize-ir [output_wav] [--preset studio|room|concert_hall|cathedral] [--rt60 1.5] [--sr 48000]`.
- **Word-by-Word LRC to Karaoke Subtitle Styler & ASS Converter (`lrc_to_ass_converter.py`)**: Converts plain and syllable-timed synchronized `.lrc` / `.elrc` files into broadcast-quality Advanced SubStation Alpha (`.ass`) and `.srt` subtitle files with progressive syllable sweep animation (`{\k<duration>}`), custom typography, glowing drop shadows, and color wipes for VLC, MPV, Aegisub, and video muxing. CLI: `python sonance.py --lrc-to-ass <lrc_file> [output_ass] [--style karaoke|minimal|cinematic] [--color #FFD700] [--srt]`.

### 📻 24. Phase 23: DSD to PCM Decimator, Sub-Sample Phase Aligner, Mastering Limiter & Album Art Studio
- **Audiophile DSD to PCM Decimator & DoP Stream Studio (`dsd_converter.py`)**: Direct Stream Digital 1-bit Delta-Sigma bitstream decoder (DSD64 / 2.8224 MHz, DSD128 / 5.6448 MHz) for `.dsf` and `.dff` files. Features multi-stage Kaiser FIR decimation filtering to eliminate ultrasonic quantization noise above 30 kHz, or packages directly into DSD-over-PCM (DoP v1.1) with 0x05/0xFA sync markers for bit-perfect USB DAC playback. CLI: `python sonance.py --dsd-to-pcm <input.dsf> [output.wav] [--rate 88200|176400|352800] [--dop]`.
- **Sub-Sample Fractional Delay & Stereo Phase Alignment Studio (`subsample_delay.py`)**: Eliminates acoustic comb filtering, hollow midrange, and smeared transients from physical microphone distance offsets. Detects inter-channel delay down to sub-samples via cross-correlation with parabolic peak interpolation, and shifts channels using a windowed sinc fractional delay filter with microsecond / sub-millimeter precision. CLI: `python sonance.py --align-phase <audio_file> [output_file] [--max-delay-ms 10.0] [--channel left|right|auto]`.
- **Mastering Brickwall Limiter & True-Peak (ISP) Studio (`mastering_limiter.py`)**: Broadcast-grade mastering limiter with 4x oversampled Inter-Sample Peak (ISP) detection. Features a lookahead delay buffer (4ms) ensuring absolute 0.000000 clipping prevention, program-dependent dual-stage release recovery, and streaming compliance for Spotify, Apple Music (-1.0 dBFS), and CD Red Book (-0.1 dBFS). CLI: `python sonance.py --master-limit <audio_file> [output_file] [--ceiling -1.0] [--threshold -3.0] [--release 120]`.
- **Album Art Optimizer, Cover Normalizer & Bloat Reducer (`album_art_studio.py`)**: Audits and manages embedded album artwork across audio libraries (FLAC, MP3, M4A, OGG, WAV). Pure-Python binary header parser for PNG, JPEG, and WebP dimensions without external dependencies. Pinpoints oversized embedded images that bloat tags, extracts external companion `cover.jpg` for DAPs & MusicBee, and non-destructively strips bloated embedded art. CLI: `python sonance.py --album-art <file_or_dir> [--extract] [--strip]`.

### 🗣️ 25. Phase 24: Dynamic De-Esser, Mid-Side Studio, Audio Watermark & Cue Markers
- **Multiband Dynamic De-Esser & Vocal Sibilance Tamer Studio (`audio_deesser.py`)**: Split-band dynamic attenuator targeting harsh vocal frequency zones ($4.0\text{ kHz} - 9.0\text{ kHz}$) caused by sibilant consonants ('s', 'sh', 't', 'ch') and aggressive streaming audio codecs. Features an ultra-fast $1\text{ms}$ RMS sidechain peak follower, adaptive $30-80\text{ms}$ recovery, customizable attenuation threshold ($-36\text{ dBFS}$ to $-6\text{ dBFS}$), maximum gain reduction depth, and "Listen Sibilance" audition mode for pinpoint frequency calibration. CLI: `python sonance.py --deess <audio_file> [output_file] [--freq 6500] [--threshold -18] [--reduction -9] [--listen]`.
- **M/S (Mid-Side) Spatial Width & Elliptical Bass Monomaker Studio (`midside_processor.py`)**: Orthogonal Mid/Side matrix transformer ($M = [L+R]/\sqrt{2}$, $S = [L-R]/\sqrt{2}$) for mastering and spatial enhancement. Features continuously variable stereo width scaling ($0\%$ mono to $200\%$ hyper-wide panorama), 2nd-order Butterworth elliptical bass monomaker filter ($60 - 300\text{ Hz}$) eliminating low-end phase cancellation on subwoofers and vinyl cuts, and high-frequency Side air excitation ($>10\text{ kHz}$) for panoramic acoustic ambience. CLI: `python sonance.py --midside <audio_file> [output_file] [--width 125] [--monomaker 120] [--mid 0] [--side 0] [--air 1.5]`.
- **Lossless Audio Watermark & Forensic Fingerprint Studio (`audio_watermark.py`)**: Inaudible psychoacoustic high-frequency FSK watermark embedder and forensic detector operating in the near-Nyquist ultrasonic spectrum ($18 - 20\text{ kHz}$) at sub-audible amplitudes ($-50\text{ dBFS}$ to $-75\text{ dBFS}$). Encodes arbitrary text payloads (ISRC tokens, copyright metadata, cryptographic ownership IDs) with CRC-16 integrity validation and dual-layer RIFF container forensic tagging (`wmrk` chunk) without loss of acoustic fidelity. CLI: `python sonance.py --watermark <audio_file> [--embed <text>] [--detect] [--output <out_file>] [--strength -65]`.
- **Broadcast Audio Cue Marker & Podcast Chapter Studio (`cue_markers.py`)**: Reads, embeds, and exports broadcast-grade cue points and timeline chapter markers across WAV (`cue ` and `LIST adtl` / `labl` chunks) and FLAC (Vorbis `CHAPTERxxx` tags). Imports YouTube, SoundCloud, and podcast timestamp descriptions directly into sample-accurate audio markers, and generates standard Red Book / EBU `.cue` sheet files ($75\text{ frames/sec}$) with lossless container rewriting. CLI: `python sonance.py --markers <audio_file> [--import-timestamps <text_or_file>] [--export-cue <cue_file>] [--output <out_file>]`.

### 📼 26. Phase 25: Analog Tape Saturation, Formant Shifter, Loudness War & Stems Remixer
- **Analog Tape Saturation & Tube Warmth Studio (`analog_tape_emulator.py`)**: Models physical tape head flux and tube preamps using a continuous soft-knee hyperbolic tangent curve $y = \tanh(x \cdot \text{drive})/\tanh(\text{drive})$, asymmetrical 2nd-harmonic tube saturation, low-frequency tape head-bump resonance filter ($50\text{--}100\text{ Hz}$), high-frequency tape flux compression, multi-speed head simulation ($30\text{ ips}$ Ultra-Fi, $15\text{ ips}$ Classic, $7.5\text{ ips}$ Vintage Lo-Fi), and optional tape hiss ($-75\text{ to }-95\text{ dBFS}$) with 24-bit PCM WAV master export. CLI: `python sonance.py --tape <audio_file> [--drive 2.5] [--speed 15.0] [--warmth 2.0] [--bias 0.5] [--tape-hiss] [--hiss-level -82.0] [--output <out_file>]`.
- **Multi-Rate Pitch Shifter & Formant-Preserving Vocal Resizer (`formant_shifter.py`)**: Transposes vocal and musical pitch ($\pm 12\text{ semitones}$) while strictly preserving natural vocal tract formants (eliminating the chipmunk or giant effect) using an STFT phase vocoder combined with cepstral liftering spectral envelope preservation. Features independent vocal tract scaling ($0.75\times$ to $1.35\times$) for gender and timbre modification. CLI: `python sonance.py --formant <audio_file> [--pitch 2.0] [--formant-scale 1.15] [--no-formant-lock] [--output <out_file>]`.
- **Mastering Loudness War & True Dynamic Spread Analyzer Studio (`loudness_war_studio.py`)**: Comprehensive ITU-R BS.1770-4 / EBU R128 compliance suite computing dual-stage gated Integrated LUFS, 3-second Short-term LUFS, 400ms Momentary LUFS, Loudness Range (LRA in LU), sample peak, RMS, Crest Factor (dB), Dynamic Health rating (0–100%), and streaming gain penalties for Spotify, Apple Music, YouTube, and Tidal. CLI: `python sonance.py --loudness-war <audio_file> [--target -14.0]`.
- **Multi-Track Stems & Audio Remixer Studio (`stems_remixer.py`)**: Professional multi-track mixing and rebalancing console for 4 stems (Vocals, Drums, Bass, Other). Implements constant-power sinusoidal stereo panning ($-100\%$ L to $+100\%$ R), independent volume faders ($-30\text{ dB}$ to $+12\text{ dB}$), one-click production presets (Custom, Acapella, Karaoke, Drum & Bass, Vocal Boost), and 24-bit PCM WAV master summing. CLI: `python sonance.py --remix [--vocals <path>] [--drums <path>] [--bass <path>] [--other <path>] [--vocals-gain 0.0] [--preset acapella] [--output <out_file>]`.

### 💥 27. Phase 26: Transient Shaper, 3D Binaural Virtualizer, Noise Gate & Tape Echo Delay
- **Audiophile Transient Shaper & Drum Punch Designer Studio (`transient_shaper.py`)**: Dual-ballistics envelope detector (fast vs. slow envelope followers) to independently reshape transient Attack ($-24\text{ dB}$ to $+24\text{ dB}$) and acoustic Sustain ($-24\text{ dB}$ to $+24\text{ dB}$) with customizable reaction speeds ($1\text{--}300\text{ ms}$) and soft-knee hyperbolic tangent saturation limiting to prevent digital overs. CLI: `python sonance.py --transient <audio_file> [output_file] [--attack +4.0] [--sustain -2.0] [--attack-speed 4.0] [--sustain-speed 80.0]`.
- **Binaural 3D Ambisonic Room & Headphone Virtualizer Studio (`binaural_virtualizer.py`)**: Simulates physical studio reference monitors in an acoustically treated control room over headphones. Models spherical head diffraction (Woodworth Interaural Time Difference ITD: $\text{ITD}=\frac{r}{c}(\theta+\sin\theta)$), pinna head-shadow damping (Interaural Level Difference ILD), early room boundary reflections (floor, ceiling, side walls), and configurable speaker angles ($20^\circ\text{--}60^\circ$) and distance ($1.0\text{--}5.0\text{ m}$). CLI: `python sonance.py --binaural <audio_file> [output_file] [--preset control_room|mastering_lab|live_lounge] [--angle 30] [--distance 1.8] [--crossfeed 1.0] [--ambience 0.35]`.
- **Broadcast Audio Noise Gate & Downward Expander Studio (`audio_noisegate.py`)**: Downward expander / noise gate featuring lookahead delay buffer ($0\text{--}10\text{ ms}$) to preserve transient attacks without clicks, hysteresis anti-chatter gating, sidechain bandpass filtering, and smooth Attack-Hold-Release envelopes to silence preamp hum, room rumble, headphone bleed, and vinyl surface noise. CLI: `python sonance.py --gate <audio_file> [output_file] [--threshold -40] [--reduction -60] [--ratio 10] [--attack 1.5] [--hold 40] [--release 120] [--lookahead 2.0]`.
- **Stereo Ping-Pong & Multi-Tap BBD Tape Echo Studio (`tape_echo_delay.py`)**: Vintage magnetic tape loop echo (Roland Space Echo RE-201 / Echoplex) and analog Bucket Brigade Device (BBD) delay emulator. Features alternating stereo ping-pong bounce ($L \to R \to L \to R$), high-cut damping filter ($1000\text{--}10000\text{ Hz}$), capstan wow & flutter micro-pitch modulation, and soft feedback loop saturation. CLI: `python sonance.py --echo <audio_file> [output_file] [--delay 375] [--feedback 45] [--damping 3800] [--flutter 0.12] [--drive 1.3] [--mix 35] [--no-ping-pong]`.

### 📦 28. Phase 27: Universal Workstation Release Packaging & Complete Handbook
- **Universal Workstation Release Packaging & Manifest Auditor Studio (`release_packager.py`)**: Comprehensive release management and integrity audit suite. Verifies syntax (`py_compile`) and importability of all 45 DSP engines and core modules spanning all phases ($100\%$ integrity pass rate), generates cryptographic SHA-256 and MD5 checksum manifests (`RELEASE.sha256sum`, `RELEASE.md5sum`), outputs structured JSON metadata (`RELEASE.manifest.json`), and packages clean standalone distribution bundles (`dist/sonance-workstation-v2.8.0.zip`) omitting caches, virtual environments, and temporary artifacts. CLI: `python sonance.py --package-release [--zip] [--verify-only] [--out-dir <dir>]`.
- **Offline Audiophile Guide & Workstation Manual Generator (`docs_generator.py`)**: Single-file interactive HTML handbook (`ui/manual.html`) compiling complete documentation for all phases, quick CLI cheat sheets, mathematical formulas (EBU R128 LUFS, Biquad Direct-Form II, Sinc interpolation, Woodworth ITD, Pearson correlation, Tape saturation), global keyboard shortcuts, and cryptographic verification workflows. 100% offline with zero external CDNs. CLI: `python sonance.py --generate-manual [output_path] [--open]`.

### 🔌 29. Phase 28: VST3 & CLAP Audio Plugin Host & Multi-Slot Rack Studio
- **VST3 & CLAP Audio Plugin Host & Multi-Slot Rack Studio (`plugin_host.py`)**: Comprehensive audio effect plugin hosting environment. Discovers installed 3rd-party `.vst3` and `.clap` plugin bundles on Windows (`%COMMONPROGRAMFILES%\VST3`, `%LOCALAPPDATA%\Programs\Common\VST3`, `%COMMONPROGRAMFILES%\CLAP`), macOS, and Linux, and embeds 5 built-in 64-bit virtual studio audio engines: Pultec EQP-1A Passive EQ, Teletronix LA-2A Optical Leveling Amplifier, Triode Valve Saturator & Exciter, Haas Stereophonic Expander, and Lexicon 480L Algorithmic Plate Reverb. Features serial multi-slot rack routing with per-slot dry/wet mix ($0\text{--}100\%$), bypass switching, gain staging, factory presets (Mastering Bus Polish, Vocal Magic & Reverb, Vintage Analog Space), and master true-peak safety limiting ($-0.2\text{ dBFS}$) with 24-bit PCM WAV export. CLI: `python sonance.py --vst-scan` / `python sonance.py --vst-rack <audio_file> [output_file] [--preset mastering_bus|vocal_magic|analog_space]`.

### 🔄 30. In-App Updates & Releases
- Automatic update detection checking against [GitHub Releases](https://github.com/Sandeep2062/Sonance/releases).
- Every release includes SHA-256 and MD5 checksum manifests (`RELEASE.sha256sum`, `RELEASE.md5sum`).

---

## 🚀 Quick Start & Installation

### Requirements
- **Windows 10 / 11** or **Linux**
- **Python 3.10+** (standard install from [python.org](https://python.org))

### 1. Clone the Repository
```bash
git clone https://github.com/Sandeep2062/Sonance.git
cd Sonance
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# or manually:
pip install pywebview tinytag requests beautifulsoup4 syncedlyrics yt-dlp mutagen
```

### 3. Launch Sonance
```bash
# Launch modern desktop workstation (Default launcher)
python sonance.py

# Or launch classic tkinter GUI
python sonance.py --classic
```

---

## ⚙️ Authentication & Accounts (Optional)

You can use Sonance completely free without any accounts. To unlock lossless and Hi-Res downloads, head to **Settings**:

| Service | Setting | What It Unlocks |
|---------|---------|-----------------|
| **Deezer** | `Deezer ARL` | Direct 16-bit / 44.1kHz FLAC Lossless & 320 kbps MP3 |
| **Qobuz** | `User ID`, `Token`, `App ID/Secret` | True 24-bit Studio Master Hi-Res FLAC |
| **Spotify** | `Client ID`, `Client Secret` | Private playlist import & library syncing |
| **YouTube** | *None required* | Free high-bitrate audio streaming & downloading fallback |

---

## 📦 Multi-Platform Release Assets

Pre-built binaries are published under [Releases](https://github.com/Sandeep2062/Sonance/releases):

| Asset | Platform | Description |
|---|---|---|
| `Sonance-windows-x86_64-setup.exe` | Windows | Standalone portable executable |
| `RELEASE.sha256sum` | All | SHA-256 integrity verification hash |
| `RELEASE.md5sum` | All | MD5 verification hash |

To verify download integrity on Windows PowerShell:
```powershell
Get-FileHash -Algorithm SHA256 .\Sonance-windows-x86_64-setup.exe
```

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 with Commons Clause**:
- **Attribution (Credit)**: Must credit **Sandeep Khadka**.
- **Copyleft**: Derivative works must remain 100% open-source under the same license — cannot be made proprietary or closed-source.
- **Non-Commercial**: Selling or commercial monetization of the software is strictly prohibited under the Commons Clause condition.

See [LICENSE](LICENSE) for full details.

---

<p align="center">
  Crafted with ❤️ by <a href="https://github.com/Sandeep2062"><b>Sandeep Khadka</b></a>
</p>
