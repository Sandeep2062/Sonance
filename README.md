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

### 🔄 6. In-App Updates & Releases
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
# Launch the modern WebView desktop application
python modern_lyrics_downloader.py

# Or launch the lightweight classic tkinter GUI
python lyrics_downloader_ultimate.py
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
