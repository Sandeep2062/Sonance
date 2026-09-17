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

### 🔄 17. In-App Updates & Releases
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
