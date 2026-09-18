"""
Sonance - Offline Audiophile Guide & Workstation Manual Generator Studio
Phase 27 Grand Finale Documentation Engine

Generates an interactive, standalone single-file HTML manual & DSP engineering handbook
documenting all 27 phases, CLI cheat sheets, audio engineering formulas, and workflows.
"""

import os
import sys
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional

APP_VERSION = "3.6.4"
WORKSTATION_NAME = "Sonance Audiophile Workstation"
ROOT_DIR = Path(__file__).parent.resolve()
DEFAULT_MANUAL_PATH = ROOT_DIR / "ui" / "manual.html"

PHASES_DATA = [
    {
        "phase": 1,
        "title": "Core Multi-Threaded Engine, Synchronized Lyrics & Metadata Tagging",
        "category": "Core Architecture",
        "modules": ["downloader_engine.py", "lyrics_engine.py", "tag_editor.py"],
        "cli": "python sonance.py --lyrics \"Track Title\" --artist \"Artist Name\"",
        "desc": "Foundational multi-threaded downloading engine with high-speed stream extraction and intelligent ID3v2/Vorbis/MP4 metadata tagging.",
        "dsp_math": "Multi-provider scoring weight: S = 0.5 * Similarity(title) + 0.3 * Similarity(artist) + 0.2 * SyncPrecision",
        "features": ["Multi-threaded download pipeline", "Synced lyrics engine (.lrc)", "Automated ID3v2/Vorbis/MP4 cover art & tags", "Multi-provider fallback (NetEase, LRCLIB, Megalobiz, Musixmatch)"]
    },
    {
        "phase": 2,
        "title": "Local Audio Caching, Offline Waveform Indexer & History",
        "category": "Playback & Storage",
        "modules": ["cache_manager.py"],
        "cli": "python sonance.py --cache-clean --max-size-gb 10",
        "desc": "High-performance LRU cache management system with RMS audio waveform indexer for instantaneous offline playback and instant track seeking.",
        "dsp_math": "Waveform amplitude decimation: A_peak[k] = max_{t in [k*w, (k+1)*w]} |x(t)|",
        "features": ["Smart LRU disk cache eviction", "Pre-computed 100-point RMS seek waveforms", "Persistent listening history & playback state", "Zero-latency offline playback"]
    },
    {
        "phase": 3,
        "title": "High-Resolution Cloud Streaming & Audio Pre-Fetch",
        "category": "Streaming",
        "modules": ["cloud_streamer.py", "cookie_manager.py"],
        "cli": "python sonance.py --stream \"https://open.spotify.com/track/...\"",
        "desc": "Adaptive bit-rate streaming with browser cookie extraction for premium high-bitrate playback across Spotify, YouTube Music, and Deezer.",
        "dsp_math": "Adaptive buffer window: B_{target}(t) = clamp(4.0 * RTT(t), 5.0, 30.0) seconds",
        "features": ["One-click Chrome/Firefox/Edge cookie extraction", "320kbps MP3 / 256kbps AAC / Lossless FLAC streams", "Intelligent next-track pre-caching", "Direct HTTP audio chunk streaming"]
    },
    {
        "phase": 4,
        "title": "Portable Device Synchronization & Transcoding",
        "category": "Hardware & Devices",
        "modules": ["device_sync.py", "audio_transcoder.py"],
        "cli": "python sonance.py --sync-device D:\\Music --format mp3 --bitrate 320",
        "desc": "Bi-directional synchronization for high-resolution DAPs, Astell&Kern, FiiO, USB storage, and MTP portable media players.",
        "dsp_math": "Dynamic bitrate allocation: CBR / VBR target with libmp3lame/libopus psychoacoustic models",
        "features": ["Hardware device auto-detection", "On-the-fly multi-threaded audio transcoding", "Preserves ID3v2 metadata & embedded artwork", "Playlist M3U8 synchronization"]
    },
    {
        "phase": 5,
        "title": "Music Library Health Doctor & Lossless FLAC Stream Verifier",
        "category": "Library Management",
        "modules": ["library_doctor.py", "flac_verifier.py"],
        "cli": "python sonance.py --doctor C:\\Music --verify-flac",
        "desc": "Automated diagnosis and healing of audio collection corruption, missing tags, orphan tracks, and bit-exact FLAC frame decoding verification.",
        "dsp_math": "MD5 checksum verification over raw uncompressed linear PCM audio stream payload",
        "features": ["Deep recursive directory audio health auditing", "Bit-exact FLAC frame CRC-16 and stream MD5 auditing", "Broken header & zero-byte track identification", "One-click tag repair and reorganization"]
    },
    {
        "phase": 6,
        "title": "AccurateRip Bit-Accurate Verification & Rip Confidence",
        "category": "Audiophile Verification",
        "modules": ["accuraterip_verifier.py"],
        "cli": "python sonance.py --accuraterip track01.flac",
        "desc": "Cross-verifies ripped tracks against the global AccurateRip database of over 100 million rips to guarantee zero drive offset and zero bit rot.",
        "dsp_math": "CRC32 checksum computed across 44.1kHz 16-bit PCM frames excluding sector lead-in/lead-out",
        "features": ["Global AccurateRip V1 & V2 CRC calculation", "Drive sample offset compensation", "Rip confidence score generation", "AccurateRip log file export"]
    },
    {
        "phase": 7,
        "title": "Headphone AutoEq & Parametric Target Profiler",
        "category": "DSP & Audio Science",
        "modules": ["headphone_autoeq.py"],
        "cli": "python sonance.py --autoeq \"Sennheiser HD 650\" --target harman",
        "desc": "Over 5,000 headphone measurement profiles calibrated to the Harman 2020 Target, Diffuse Field, and Optimum HiFi curves via biquad peaking filters.",
        "dsp_math": "H(s) = (s^2 + (omega_0/Q) * A * s + omega_0^2) / (s^2 + (omega_0/(Q*A)) * s + omega_0^2), A = 10^(G/40)",
        "features": ["Instant search across 5,000+ headphone models", "Harman AE/OE, Harman In-Ear, and Flat targets", "Calculates exact Parametric EQ frequency, Q, and Gain", "Graphic 10-band and parametric export (.txt, .json)"]
    },
    {
        "phase": 8,
        "title": "Bit-Exact Audio CD Ripper & CUE Sheet Generator",
        "category": "Archival",
        "modules": ["cd_ripper.py"],
        "cli": "python sonance.py --rip-cd E: --flac --cue",
        "desc": "Industrial-grade Red Book CD digital audio extractor with jitter correction, MusicBrainz metadata lookup, and non-compliant CUE sheet generation.",
        "dsp_math": "Red Book CDDA standard: 44,100 Hz, 16-bit stereo PCM, 75 sectors per second (2352 bytes/sector)",
        "features": ["AccurateRip offset correction and paranoia ripping", "Auto-retrieval of artist, album, tracklist & cover", "Generates single-image FLAC with embedded CUE", "Zero-loss archival preservation"]
    },
    {
        "phase": 9,
        "title": "AI Vocal, Drum, Bass & Stem Separator",
        "category": "AI & Audio Isolation",
        "modules": ["vocal_separator.py"],
        "cli": "python sonance.py --separate input.flac --stems 4",
        "desc": "State-of-the-art deep neural network stem separation into Vocals, Drums, Bass, and Other instruments for remixing, karaoke, and sampling.",
        "dsp_math": "Complex spectrogram phase recovery: S_{stem}(f, t) = M_{stem}(f, t) * e^{i * phi_{mix}(f, t)}",
        "features": ["2-Stem (Vocal / Instrumental) and 4-Stem isolation", "Automatic instrumental karaoke track generation", "High-fidelity 24-bit lossless WAV export", "GPU acceleration with CPU multi-threaded fallback"]
    },
    {
        "phase": 10,
        "title": "360-Degree Binaural 8D Audio Spatializer",
        "category": "Spatial Audio",
        "modules": ["audio_8d_spatializer.py"],
        "cli": "python sonance.py --spatial-8d input.flac --orbit 12.0",
        "desc": "Transforms standard stereo tracks into an immersive 360-degree rotating binaural sphere with Head-Related Impulse Response (HRIR) simulation.",
        "dsp_math": "ITD = (r/c) * (theta + sin(theta)), ILD = 10 * log10(1 + (f/f_0)^2 * sin^2(theta))",
        "features": ["Interaural Time Difference (ITD) delay line", "Interaural Level Difference (ILD) pinna shadow filters", "Smooth sinusoidal and orbital panning trajectories", "Headphone-optimized 3D spatial field"]
    },
    {
        "phase": 11,
        "title": "EBU R128 & ReplayGain 2.0 Loudness Normalizer",
        "category": "DSP & Audio Science",
        "modules": ["replaygain_normalizer.py", "loudness_scanner.py"],
        "cli": "python sonance.py --normalize-loudness album_dir/ --target-lufs -14",
        "desc": "Broadcast-standard loudness normalization complying with ITU-R BS.1770-4 and EBU R128 to eliminate jarring volume jumps between tracks.",
        "dsp_math": "LUFS = -0.691 + 10 * log10( sum_{i} w_i * (1/T) * int z_i^2(t) dt ) with K-weighting pre-filter",
        "features": ["Integrated LUFS, Loudness Range (LRA), and True Peak scanner", "Non-destructive ReplayGain 2.0 metadata tag writing", "True Peak anti-clipping limiter protection", "Streaming platform presets (-14 LUFS Spotify, -16 LUFS Apple)"]
    },
    {
        "phase": 12,
        "title": "10-Band Biquad Parametric Equalizer Studio",
        "category": "DSP & Audio Science",
        "modules": ["parametric_eq.py"],
        "cli": "python sonance.py --eq input.flac --preset audiophile_warmth",
        "desc": "High-precision 64-bit floating point Robert Bristow-Johnson biquad filter bank featuring Low Shelf, Peaking, High Shelf, Notch, and Bandpass.",
        "dsp_math": "y[n] = (b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2]) / a0",
        "features": ["64-bit double precision IIR direct-form II topology", "Real-time interactive slider equalization", "10 frequency bands (31Hz to 16kHz) with variable Q", "Audiophile presets: Flat, Warmth, Vocal Clarity, Bass Punch"]
    },
    {
        "phase": 13,
        "title": "Stereo Phase Correlation & Lissajous Goniometer",
        "category": "Audiophile Verification",
        "modules": ["phase_correlation.py"],
        "cli": "python sonance.py --phase-meter input.flac",
        "desc": "Visualizes acoustic stereo phase alignment, monaural compatibility, and stereo field spread using Pearson correlation and Lissajous patterns.",
        "dsp_math": "rho = sum(L * R) / sqrt( sum(L^2) * sum(R^2) ), [-1 = Out of phase, 0 = True stereo, +1 = Mono]",
        "features": ["Real-time 60 FPS vector oscilloscope (Goniometer)", "Continuous Pearson coefficient correlation meter", "Mono cancellation warning indicators", "Left/Right RMS balance analyzer"]
    },
    {
        "phase": 14,
        "title": "Bit-Depth & Nyquist DAC Performance Tester",
        "category": "Hardware & Calibration",
        "modules": ["dac_tester.py"],
        "cli": "python sonance.py --test-dac --sample-rate 192000 --bits 24",
        "desc": "Generates precision laboratory reference test signals (sine sweeps, J-Test jitter stimuli, Dirac deltas) to verify DAC linearity and bit-transparency.",
        "dsp_math": "f_{nyquist} = f_s / 2, SNR_{ideal} = 6.02 * N + 1.76 dB (N = bit depth)",
        "features": ["16-bit vs 24-bit vs 32-bit float resolution test signals", "Logarithmic frequency sweep (20 Hz - 96 kHz)", "Julian Dunn J-Test square wave for clock jitter detection", "Impulse response and DAC ringing characterization"]
    },
    {
        "phase": 15,
        "title": "Sub-Millisecond Lyrics Drift & Sync Retimer",
        "category": "Lyrics Engineering",
        "modules": ["lyrics_retimer.py"],
        "cli": "python sonance.py --retime-lyrics song.lrc --offset-ms +350",
        "desc": "Interactive sub-millisecond drift correction, time-stretching, and linear interpolation for out-of-sync LRC and ELRC timestamp files.",
        "dsp_math": "t_{new} = (t_{orig} - t_0) * (T_{audio} / T_{lyrics}) + offset",
        "features": ["Global milliseconds offset adjustment", "Two-point linear drift compensation across live tracks", "Visual side-by-side lyrics line timing editor", "Lossless export of verified .lrc files"]
    },
    {
        "phase": 16,
        "title": "64-Band Real-Time Fast Fourier Spectrum Analyzer",
        "category": "DSP & Audio Science",
        "modules": ["spectrum_analyzer.py"],
        "cli": "python sonance.py --spectrum input.flac",
        "desc": "Laboratory-grade RTA spectrum analyzer with Hann windowing, ANSI 1/3-octave logarithmic bins, and peak frequency hold.",
        "dsp_math": "X[k] = sum_{n=0}^{N-1} x[n] * w[n] * e^{-i * 2*pi*k*n / N}, w[n] = 0.5 * (1 - cos(2*pi*n / (N-1)))",
        "features": ["64 ANSI standard octave frequency bands (20 Hz - 20 kHz)", "Hann / Blackman-Harris windowing functions", "Peak decay ballistics matching analog hardware meters", "Real-time HTML5 Canvas visualization"]
    },
    {
        "phase": 17,
        "title": "Cubic Spline & Harmonic Audio De-Clipper",
        "category": "Restoration & Repair",
        "modules": ["audio_declipper.py"],
        "cli": "python sonance.py --declip clipped.flac -o restored.flac --threshold -0.5",
        "desc": "Detects hard and soft digital clipping flat-tops and mathematically reconstructs truncated audio waveforms via natural cubic spline interpolation.",
        "dsp_math": "S_i(x) = a_i + b_i(x - x_i) + c_i(x - x_i)^2 + d_i(x - x_i)^3 with C^2 continuity",
        "features": ["Automatic flat-top consecutive sample clipping detection", "Piecewise cubic spline waveform interpolation", "Dynamic headroom expansion to prevent secondary clipping", "Detailed before/after THD and peak recovery report"]
    },
    {
        "phase": 18,
        "title": "Silence Detection & Vinyl/Cassette Track Splitter",
        "category": "Restoration & Archival",
        "modules": ["track_splitter.py"],
        "cli": "python sonance.py --split-tracks vinyl_side_a.wav --min-silence 2.0 --threshold -45",
        "desc": "Analyzes continuous vinyl LP rips and cassette recordings, detects inter-track silence gaps, and splits audio into individual indexed tracks.",
        "dsp_math": "Silence condition: 20 * log10( sqrt( (1/N) * sum x[n]^2 ) ) < threshold_db for duration >= min_silence",
        "features": ["RMS energy-based silence detection with hysteresis", "Zero-crossing point cut accuracy to eliminate audio clicks", "Automatic track numbering and CUE sheet export", "Batch lossless FLAC/WAV slicing"]
    },
    {
        "phase": 19,
        "title": "Typography Kinetic Lyrics Video Maker Studio",
        "category": "Video & Social",
        "modules": ["lyrics_video_maker.py"],
        "cli": "python sonance.py --make-video song.mp3 --lrc song.lrc --style neon_glow",
        "desc": "Renders broadcast-quality 1080p/4K 60FPS typography animated lyrics videos with background cover art blurs, audio reactive pulses, and neon glow.",
        "dsp_math": "Bilinear text alpha blending: alpha(t) = smoothstep(t_{start}, t_{start} + fade, t) * (1 - smoothstep(t_{end} - fade, t_{end}, t))",
        "features": ["Hardware accelerated H.264 / NVENC video rendering", "Multi-provider typography styles: Minimalist, Neon Glow, Cyberpunk, Audiophile Dark", "Reactive bass pulse and spectrum background visualization", "TikTok / Instagram Reel vertical (9:16) and YouTube (16:9) aspect ratios"]
    },
    {
        "phase": 20,
        "title": "Band-Limited Whittaker-Shannon Sinc Upsampler",
        "category": "DSP & Audio Science",
        "modules": ["audio_upsampler.py"],
        "cli": "python sonance.py --upsample 44k.flac -o 192k.flac --target-rate 192000 --quality studio",
        "desc": "Ultra-audiophile sample rate converter featuring polyphase sinc FIR filter kernel with Kaiser windowing, achieving -160 dB stopband attenuation.",
        "dsp_math": "x(t) = sum_{n=-inf}^{inf} x[n] * sinc((t - n*T) / T), sinc(u) = sin(pi*u) / (pi*u)",
        "features": ["Up to 384 kHz / 32-bit floating point upsampling", "Linear phase Kaiser window sinc kernel (beta = 10.5)", "Stopband attenuation exceeding -160 dB with zero aliasing", "Preserves ultra-fast transient phase response"]
    },
    {
        "phase": 21,
        "title": "CUE Sheet Fixer, Room IR Synthesizer & ASS Karaoke",
        "category": "Acoustics & Subtitles",
        "modules": ["cue_fixer.py", "room_ir_synthesizer.py", "lrc_to_ass_converter.py"],
        "cli": "python sonance.py --fix-cue album.cue | --synth-ir studio_room.wav | --lrc-to-ass song.lrc",
        "desc": "Trio of audio mastering utilities: fixes damaged CUE file paths, synthesizes acoustic room impulse responses via shoebox ray-tracing, and generates ASS karaoke subtitles.",
        "dsp_math": "Sabine formula: RT_{60} = 0.161 * V / (sum S_i * alpha_i)",
        "features": ["CUE sheet file path repair and UTF-8 encoding sanitizer", "Parametric shoebox acoustic room impulse synthesizer (RT60, room dimensions, absorption)", "Advanced SubStation Alpha (.ass) word-by-word highlighted karaoke subtitles", "Convolver-ready WAV impulse response export"]
    },
    {
        "phase": 22,
        "title": "Bit-Exact DSD/DSF to PCM Decimator & Sub-Sample Phase Aligner",
        "category": "DSP & Audio Science",
        "modules": ["dsd_converter.py", "subsample_delay.py"],
        "cli": "python sonance.py --dsd-to-pcm master.dsf -o pcm.flac --rate 176400 | --phase-align stereo.wav --delay-samples 0.45",
        "desc": "Multi-stage FIR decimator for DSD64/DSD128 1-bit streams with ultrasonic noise shaping removal, paired with sub-sample fractional sinc delay alignment.",
        "dsp_math": "Fractional delay: h[n] = sinc(n - D), D in R; Decimation: y[m] = sum h[k] * x[m*M - k]",
        "features": ["Native DSD64 (2.8224 MHz) and DSD128 (5.6448 MHz) decoding", "Decimates to 88.2 kHz, 176.4 kHz, or 352.8 kHz 24-bit PCM", "Filters out severe DSD 50kHz+ delta-sigma quantization noise", "Sub-sample phase alignment down to 0.01 sample precision"]
    },
    {
        "phase": 23,
        "title": "True Peak Brickwall Mastering Limiter & Album Art Bloat Reducer",
        "category": "Mastering & Optimization",
        "modules": ["mastering_limiter.py", "album_art_studio.py"],
        "cli": "python sonance.py --master-limiter in.wav -o out.wav --ceiling -0.3 | --optimize-art library/",
        "desc": "Broadcast-grade ITU-R BS.1770 true-peak brickwall lookahead limiter with 4x inter-sample oversampling, paired with metadata image bloat reducer.",
        "dsp_math": "True Peak oversampling: x_{4x}[m] = sum sinc(m/4 - k) * x[k]; Gain: g[n] = min(1.0, ceiling / max(|x_{4x}|))",
        "features": ["4x polyphase oversampling for true inter-sample peak detection", "Smooth exponential release curve preventing pumping", "Eliminates DAC inter-sample reconstruction clipping", "Losslessly crushes 50MB+ bloated cover art down to crisp WebP/JPEG"]
    },
    {
        "phase": 24,
        "title": "Multiband De-Esser, Mid-Side Processor, Watermark & CUE Markers",
        "category": "Mastering & Metadata",
        "modules": ["audio_deesser.py", "midside_processor.py", "audio_watermark.py", "cue_markers.py"],
        "cli": "python sonance.py --de-ess vocal.wav | --midside in.wav --width 1.35 | --watermark in.wav --embed \"Key\" | --cue-markers in.flac",
        "desc": "Mastering suite featuring dynamic sibilance suppression (4-9 kHz), M/S spatial width expansion & bass monomaker, inaudible spread-spectrum watermarking, and non-destructive CUE chapter markers.",
        "dsp_math": "Mid = (L + R) / sqrt(2), Side = (L - R) / sqrt(2); Sibilance dynamic band attenuation",
        "features": ["Dynamic multiband de-esser with lookahead peak tracking", "Mid-Side stereophonic processor with low-frequency monomaker below 120Hz", "Spread-spectrum inaudible audio copyright watermarking", "Lossless embedded CUE sheet chapter marking"]
    },
    {
        "phase": 25,
        "title": "Analog Tape Saturation, Formant Shifter, Loudness War & Stems Remixer",
        "category": "Studio FX & Analysis",
        "modules": ["analog_tape_emulator.py", "formant_shifter.py", "loudness_war_studio.py", "stems_remixer.py"],
        "cli": "python sonance.py --tape in.wav --ips 15 --bias hot | --formant vocal.wav --semitones +2.5 | --loudness-war in.wav | --remix-stems ...",
        "desc": "Studer A800 analog tape saturation with 15/30 IPS magnetic head bump, vocal formant envelope shifter, DR dynamic range & crest factor analyzer, and multi-track stems remixer studio.",
        "dsp_math": "Tape magnetization: y(t) = tanh(drive * x(t) + bias); Crest Factor: CF = 20 * log10(Peak / RMS)",
        "features": ["Physical modeling of magnetic hysteresis, 15/30 IPS head bump and high-frequency roll-off", "Independent vocal formant shifting without altering pitch", "Official Pleasurize Music Foundation Dynamic Range (DR) score calculation", "4-channel interactive stems mixer with gain, pan, and mute"]
    },
    {
        "phase": 26,
        "title": "Transient Shaper, 3D Binaural Virtualizer, Noise Gate & Tape Echo",
        "category": "Studio FX & Dynamics",
        "modules": ["transient_shaper.py", "binaural_virtualizer.py", "audio_noisegate.py", "tape_echo_delay.py"],
        "cli": "python sonance.py --transient in.wav --attack +4 | --binaural in.wav --preset control_room | --gate in.wav --threshold -40 | --echo in.wav --delay 375",
        "desc": "Dual-envelope transient punch designer, 3D binaural studio room monitor virtualizer with spherical head shadowing, broadcast lookahead noise gate, and Roland Space Echo BBD tape delay.",
        "dsp_math": "Transient envelope: Env_{att}[n] = (1 - alpha_{att}) * Env_{att}[n-1] + alpha_{att} * |x[n]|; BBD delay: y[n] = x[n] + fb * LP(y[n - D])",
        "features": ["Independent drum attack and sustain energy reshaping", "Acoustic control room monitor virtualizer with ITD, ILD and early reflections", "Broadcast noise gate with lookahead, hold, and hysteresis preventing chatter", "Stereo ping-pong tape echo with treble absorption and motor wow/flutter"]
    },
    {
        "phase": 27,
        "title": "Universal Workstation Release Packaging, Manifest Auditor & Complete Manual",
        "category": "Release Management & Handbook",
        "modules": ["release_packager.py", "docs_generator.py"],
        "cli": "python sonance.py --package-release [--zip] [--verify-only] | --generate-manual [--open]",
        "desc": "Grand Finale milestone: Verifies codebase integrity across all 27 phases, computes cryptographic SHA-256 and MD5 manifests, and generates this standalone offline engineering manual.",
        "dsp_math": "Cryptographic integrity: SHA256(Block_i) = Merkle-Damgard compression over 512-bit message blocks",
        "features": ["45-module automated syntax and importability auditor", "Linux-standard RELEASE.sha256sum & RELEASE.md5sum generator", "Structured RELEASE.manifest.json packaging metadata", "Single-file, 100% offline interactive DSP manual & documentation"]
    },
    {
        "phase": 28,
        "title": "VST3 & CLAP Audio Plugin Host & Multi-Slot Rack Studio",
        "category": "Studio FX & Plugin Architecture",
        "modules": ["plugin_host.py"],
        "cli": "python sonance.py --vst-scan | --vst-rack input.wav [output.wav] --preset mastering_bus",
        "desc": "Universal plugin host and multi-slot serial effect rack capable of scanning system VST3/CLAP plugins or chaining built-in 64-bit virtual studio models (Pultec EQP-1A, Teletronix LA-2A, Triode Valve Exciter, Haas Stereo Expander, Lexicon 480L Plate Reverb).",
        "dsp_math": "Serial rack transfer function: Y(z) = [ prod_{k=1}^N H_k(z) ] * X(z); Haas delay Delta t = 1.2ms; T4 optical decay: env(t) = 0.6 * e^{-t/60ms} + 0.4 * e^{-t/1.2s}",
        "features": ["System VST3 and CLAP directory scanner for host plugins", "5 built-in 64-bit virtual studio audio FX engines", "3-slot serial mastering rack with individual dry/wet, bypass, and gain staging", "Master ITU-R BS.1770 true-peak safety limiter (-0.2 dBFS)"]
    },
    {
        "phase": 29,
        "title": "Dolby Atmos 7.1.4 Bed Spatializer & Multichannel Audio Renderer",
        "category": "Spatial Audio & Multichannel",
        "modules": ["spatial_multichannel.py"],
        "cli": "python sonance.py --atmos master.wav [output.wav] --mode binaural | --mode discrete --format 7.1.4",
        "desc": "Translates stereo masters into an immersive 7.1.4 Dolby Atmos bed (7 ear-level surround + 4 ceiling height channels + dedicated LFE subwoofer crossover) with Woodworth spherical binaural virtualization or discrete 6/8/12-channel 24-bit PCM WAV export.",
        "dsp_math": "Spherical ITD delay: Delta t = (r/c) * (sin(theta) + 0.5 * theta); 4th-order Linkwitz-Riley LFE crossover: H_{LR4}(s) = (omega_c^2 / (s^2 + sqrt(2)*omega_c*s + omega_c^2))^2",
        "features": ["12-channel 7.1.4 immersive spatial audio bed generator", "4th-order Linkwitz-Riley LFE crossover filter (60-160 Hz)", "Ceiling height micro-reflection ambience synthesizer (>800 Hz)", "3D Binaural Headphone Virtualizer (Woodworth ITD + ILD) and 24-bit multichannel PCM WAV export (7.1.4, 7.1, 5.1)"]
    },
    {
        "phase": 30,
        "title": "British Class-A Console Channel Strip & SSL G-Master Bus Compressor Studio",
        "category": "Studio FX & Console Mastering",
        "modules": ["console_channel_strip.py"],
        "cli": "python sonance.py --console in.wav [out.wav] --preset master_bus_glue | --threshold -14 --ratio 2.0 --hpf 90",
        "desc": "Definitive studio console mastering path combining Solid State Logic (SSL 4000 G-Master Bus Compressor) Quad-VCA dynamics, program-dependent Auto-Release, and sidechain HPF with British Class-A Neve 1073 preamp transformer harmonic saturation and 3-band inductor/Baxandall EQ.",
        "dsp_math": "SSL VCA soft-knee curve: y_{dB} = x_{dB} + ((1/R - 1)*(x_{dB} - T + W/2)^2)/(2W); Neve Marinair saturation: y = (tanh(drive*x + bias) - tanh(bias))/tanh(drive) + 0.04*warmth*x^3",
        "features": ["Solid State Logic (SSL 4000 G-Master Bus Compressor) Quad-VCA emulation", "Program-dependent dual-constant Auto-Release (0.1s fast + 1.2s memory)", "Sidechain High-Pass Filter (60, 90, 120, 185 Hz) preventing kick/bass pumping", "Neve 1073 Class-A preamp transformer saturation & 18 dB/oct HPF", "Proportional-Q mid inductor band & 12 kHz Baxandall air sheen", "Master safety True-Peak ceiling limiter (-0.2 dBFS) & 24-bit PCM WAV export"]
    },
    {
        "phase": 31,
        "title": "Higher-Order Ambisonics (HOA 1st/2nd/3rd Order) & 360-Degree VR Spatializer Studio",
        "category": "Spatial Audio & 3D Virtualization",
        "modules": ["ambisonic_hoa.py"],
        "cli": "python sonance.py --hoa master.wav [output.wav] --order 3 --mode binaural | --mode bformat --trajectory orbit_helix",
        "desc": "Encodes stereo audio into real spherical harmonics up to 3rd order (16 channels ACN / SN3D AmbiX) with dynamic 3D spatial trajectories (helix, horizontal orbit, pendulum, overhead halo), air absorption damping, and dual rendering into 3D binaural headphones (Woodworth ITD + pinna notch) or discrete 4/9/16-channel 24-bit PCM AmbiX WAV.",
        "dsp_math": "Spherical harmonics: Y_l^m(theta, phi) = N_l^m * P_l^{|m|}(sin phi) * trig_m(theta); AmbiX ACN index: n = l^2 + l + m; Inverse-distance damping: A(d) = 1/max(1, d) * exp(-alpha * f * d)",
        "features": ["1st, 2nd, and 3rd order Ambisonic B-Format encoding (4, 9, 16 channels)", "Industry-standard ACN channel ordering and SN3D normalization (AmbiX)", "5 dynamic 3D motion trajectories (Orbit Helix, Horizontal 360, Pendulum Arc, Overhead, Fixed)", "3D Binaural Headphone Virtualizer via 14-point spherical loudspeaker array with Woodworth ITD delay & pinna notch", "Discrete multichannel 24-bit linear PCM WAV export ready for VR (Quest, Vision Pro) & YouTube 360"]
    },
    {
        "phase": 32,
        "title": "Psychoacoustic Subharmonic Bass Synthesizer & Missing Fundamental Studio",
        "category": "Bass Processing & Psychoacoustics",
        "modules": ["subharmonic_bass.py"],
        "cli": "python sonance.py --bass master.wav [output.wav] --preset club_sub_boom | --sub-24-36 0.85 --sub-36-56 0.50 --maxxbass 0.35",
        "desc": "Subterranean bass synthesis and psychoacoustic low-end excitation. Emulates the hardware dbx 120XP subharmonic octave divider (24-36 Hz and 36-56 Hz bands) to generate sub-bass one octave down, paired with MaxxBass Chebyshev harmonic overtone synthesis (2nd, 3rd, 4th harmonics) exploiting the auditory cortex missing fundamental effect for massive bass on mobile speakers and headphones. Includes 4th-order subsonic rumble cleanup (20-35 Hz), elliptical bass monomaker (80-150 Hz), analog tube saturation, and True-Peak safety limiting (-0.2 dBFS).",
        "dsp_math": "Subharmonic octave division: f_{sub} = f_0 / 2 via zero-crossing flip-flop tracking; Chebyshev missing fundamental overtones: T_2(x) = 2x^2 - 1, T_3(x) = 4x^3 - 3x, T_4(x) = 8x^4 - 8x^2 + 1; Low-cut subsonic Butterworth: H_{HP4}(s) = s^4 / B_4(s)",
        "features": ["Dual-band subharmonic octave divider (24-36 Hz subterranean & 36-56 Hz kick punch)", "MaxxBass psychoacoustic missing fundamental exciter for small speaker & headphone translation", "Asymmetrical analog tube saturation & transformer warmth", "4th-order Butterworth subsonic rumble high-pass filter (20-35 Hz)", "Elliptical low-end monomaker (80-150 Hz) for club sound system punch and vinyl compliance", "True-Peak brickwall safety limiter (-0.2 dBFS) with 24-bit PCM WAV export"]
    },
    {
        "phase": 33,
        "title": "Dynamic Spectral Resonance Suppressor & Surgical De-Resonator Studio",
        "category": "Mastering & Dynamic Spectral Suppression",
        "modules": ["resonance_suppressor.py"],
        "cli": "python sonance.py --soothe master.wav [output.wav] --preset tame_harshness | --depth 0.55 --threshold 3.5 --sharpness 2.5 --listen",
        "desc": "Dynamic spectral resonance tracking inspired by Oeksound Soothe2 and Soundtheory Gullfoss. Computes 2048-point STFT moving spectral envelope baselines across 40 Bark frequency bands, surgically suppressing harsh sibilance, ringing room modes, nasal vocal honk, and abrasive cymbal bite with 5ms/50ms ballistics and difference Delta 'Listen Mode'.",
        "dsp_math": "Dynamic notch attenuation: \\Delta G(f) = -\\text{depth} \\cdot \\max(0, P_{\\text{prominence}}(f) - \\text{threshold})^{1 + 0.25Q}; Ballistics: g[n] = g[n-1] + \\alpha (g_{\\text{target}} - g[n-1])",
        "features": ["Dynamic STFT spectral resonance tracking across 40 critical Bark frequency bands", "Surgical prominence notch attenuation carving out acoustic harshness and whistle modes", "Ballistic envelope smoothing (5ms attack / 50ms release) for transparent de-resonating", "Delta 'Listen Mode' difference auditioning isolating strictly the suppressed harshness", "Low-Cut and High-Cut focus bounding filters targeting specific problem frequency zones", "True-Peak brickwall safety limiter (-0.2 dBFS) with 24-bit linear PCM WAV export"]
    },
    {
        "phase": 34,
        "title": "Vintage Optical & Variable-Mu Master Compressor Studio",
        "category": "Mastering & Vintage Dynamics",
        "modules": ["vintage_compressor.py"],
        "cli": "python sonance.py --la2a in.wav [out.wav] --reduction 55 --drive 1.25 | --fairchild in.wav --tc 5 --makeup 2.0",
        "desc": "Physical modeling of dual legendary studio dynamics: the Teletronix LA-2A T4 electro-optical cell with dual-stage memory release (60ms fast initial decay + 0.5s-4.5s program-dependent memory tail) and R37 high-frequency emphasis; paired with the Fairchild 670 remote-cutoff variable-mu dual-triode 6386 tube compressor with 6 stepped time-constant positions, sidechain HPF (60-185 Hz), analog tube saturation, and True-Peak safety limiting.",
        "dsp_math": "LA-2A T4 optical decay: y_{\\text{rel}}(t) = 0.5 e^{-t/0.06} + 0.5 e^{-t/\\tau_{\\text{slow}}}; \\quad \\text{Fairchild 6386 Variable-Mu}: \\mu(V_g) = \\frac{\\mu_0}{1 + k \\cdot |V_g|^{1.2}}",
        "features": ["Teletronix LA-2A T4 electro-optical attenuator with non-linear photocell luminescence response", "Dual-stage optical release with multi-second memory accumulation effect", "Fairchild 670 remote-cutoff variable-mu dual-triode 6386 physical tube model", "6 classic stepped hardware time-constant positions including dual-time auto-release", "Sidechain high-pass filter (60, 90, 120, 185 Hz) preventing low-end pumping", "LA-2A R37 high-frequency sidechain emphasis trimming", "12AX7 / 6386 tube harmonic saturation & transformer warmth", "True-Peak brickwall safety limiter (-0.2 dBFS) with 24-bit linear PCM WAV export"]
    },
    {
        "phase": 35,
        "title": "The Grand Workstation Zenith & Master Orchestration Suite",
        "category": "Grand Workstation Finale & Multi-Stage Orchestration",
        "modules": ["zenith_orchestrator.py"],
        "cli": "python sonance.py --zenith master.wav [output.wav] --profile audiophile_pure_master | --batch ./AlbumFolder",
        "desc": "The crowning zenith of the 35-Phase Sonance Audiophile Workstation. Orchestrates an end-to-end 7-stage serial mastering pipeline: 1. Spectral De-Resonator, 2. Subharmonic Bass & Missing Fundamental, 3. British Class-A Console & Baxandall EQ, 4. Vintage Optical/Variable-Mu Dynamics, 5. Mid/Side Spatial Panorama, 6. Studer A800 Analog Tape Saturation, and 7. True-Peak Lookahead Brickwall Limiter with automated batch album processing and cryptographic verification.",
        "dsp_math": "Master serial pipeline transfer function: Y(z) = H_{\\text{Limiter}}(z) \\circ H_{\\text{Tape}}(z) \\circ H_{\\text{M/S}}(z) \\circ H_{\\text{Vintage}}(z) \\circ H_{\\text{Console}}(z) \\circ H_{\\text{Bass}}(z) \\circ H_{\\text{DeRes}}(z) [X(z)]",
        "features": ["7-stage unbroken serial mastering pipeline executing across world-class physical DSP engines", "5 mastering macro profiles (Audiophile Pure Master, Club/EDM Banger, Acoustic Intimate, Broadcast Sheen, Vinyl Lathe)", "Individual stage bypass and parameter overrides for custom mastering chains", "Automated batch album processing ensuring cohesive track-to-track loudness and tone", "Full audio telemetry: peak dBFS, RMS loudness, dynamic crest factor, and SHA-256 integrity manifest", "24-bit linear PCM WAV master export with true-peak inter-sample protection"]
    },
    {
        "phase": 36,
        "title": "Audiophile Exclusive Mode & Hardware DAC Output Studio",
        "category": "Exclusive Audio Output & Hardware Clocking",
        "modules": ["exclusive_audio_engine.py"],
        "cli": "python sonance.py --audio-devices | --test-exclusive [device_id] --sr 96000 | --play-exclusive track.flac",
        "desc": "Direct hardware audio streaming bypassing the Windows Audio Engine (AudioDG.exe) and OS software mixers. Features WASAPI Exclusive mode and ASIO driver discovery/routing on Windows, AAudio Exclusive mode (AAUDIO_SHARING_MODE_EXCLUSIVE) and bit-perfect USB Audio DAC direct access on Android, CoreAudio Hog Mode on macOS, and ALSA direct hardware DMA (hw:X,Y) on Linux. Locks the DAC hardware clock directly to the audio track sample rate (44.1 kHz to 192 kHz) for bit-perfect output with zero resampling and sub-5ms buffer latency.",
        "dsp_math": "Direct Bit-Perfect Hardware Stream: Y[n] = X[n], \\quad f_s^{\\text{DAC}} = f_s^{\\text{file}}, \\quad \\text{Latency} = \\frac{\\text{Buffer Size}}{f_s} \\cdot 1000\\text{ ms}",
        "features": [
            "Bit-perfect playback bypassing OS mixers and forced 48 kHz resampling",
            "Automatic DAC hardware clock rate matching from 44.1 kHz up to 192 kHz / 384 kHz",
            "Windows WASAPI Exclusive mode via IAudioClient with MMCSS Pro Audio scheduling",
            "Windows Registry ASIO driver scanner discovering all manufacturer hardware drivers",
            "Android AAudio Exclusive MMAP stream and userspace USB Audio Class (UAC) DAC direct driver",
            "Real-time bit-perfect telemetry badge, buffer latency tuner, and 440 Hz DAC lock test chime"
        ]
    }
]

KEYBOARD_SHORTCUTS = [
    {"key": "Space", "action": "Toggle Play / Pause", "context": "Global Playback"},
    {"key": "Arrow Left / Right", "action": "Seek backward / forward 5 seconds", "context": "Global Playback"},
    {"key": "Shift + Arrow Left / Right", "action": "Previous track / Next track in queue", "context": "Global Playback"},
    {"key": "Arrow Up / Down", "action": "Increase / decrease volume by 5%", "context": "Global Playback"},
    {"key": "M", "action": "Mute / Unmute audio", "context": "Global Playback"},
    {"key": "Ctrl + F", "action": "Focus search input", "context": "Navigation"},
    {"key": "Ctrl + L", "action": "Toggle Fullscreen Synchronized Lyrics View", "context": "View"},
    {"key": "Ctrl + E", "action": "Open 10-Band Parametric Equalizer Studio", "context": "DSP Studio"},
    {"key": "Ctrl + M", "action": "Open Stereo Phase Correlation & Lissajous Goniometer", "context": "DSP Studio"},
    {"key": "Ctrl + S", "action": "Open Real-Time FFT Spectrum Analyzer", "context": "DSP Studio"},
    {"key": "Escape", "action": "Close any active modal, popup, or overlay", "context": "Global UI"},
]

MATH_FORMULAS = [
    {
        "name": "EBU R128 Loudness (LUFS / LKFS)",
        "formula": "LUFS = -0.691 + 10 * log10( sum_{i=1}^M w_i * (1/T) * int_0^T z_i^2(t) dt )",
        "explanation": "Applies a two-stage K-weighting filter (high-frequency shelf + highpass filter simulating human ear acoustic curves) followed by gating at -70 LKFS (absolute) and -10 LU relative."
    },
    {
        "name": "Bristow-Johnson Biquad Peaking EQ Filter",
        "formula": "y[n] = (b_0 * x[n] + b_1 * x[n-1] + b_2 * x[n-2] - a_1 * y[n-1] - a_2 * y[n-2]) / a_0",
        "explanation": "Direct-form II recursive IIR filter coefficients: b_0 = 1 + alpha*A, b_1 = -2*cos(w_0), b_2 = 1 - alpha*A, a_0 = 1 + alpha/A, a_1 = -2*cos(w_0), a_2 = 1 - alpha/A, where alpha = sin(w_0)/(2*Q) and A = 10^(Gain/40)."
    },
    {
        "name": "Interaural Time Difference (ITD - Woodworth Formula)",
        "formula": "Delta t = (r / c) * (theta + sin(theta))",
        "explanation": "Calculates acoustic propagation time difference between ears for a sound source at angle theta, head radius r (approx 0.0875m), and speed of sound c (343 m/s)."
    },
    {
        "name": "Band-Limited Sinc Interpolation (Whittaker-Shannon)",
        "formula": "x(t) = sum_{n=-inf}^{inf} x[n] * sinc( (t - n*T) / T ),   where sinc(u) = sin(pi * u) / (pi * u)",
        "explanation": "Allows mathematically perfect continuous-time signal reconstruction from discrete samples with zero aliasing below the Nyquist frequency."
    },
    {
        "name": "Stereo Pearson Phase Correlation Coefficient",
        "formula": "rho = sum(L[n] * R[n]) / sqrt( sum(L[n]^2) * sum(R[n]^2) )",
        "explanation": "Ranges from -1.0 (complete out-of-phase stereo cancellation) through 0.0 (independent stereo channels) to +1.0 (pure coherent mono)."
    },
    {
        "name": "Analog Tape Saturation Transfer Function",
        "formula": "y[n] = tanh( drive * x[n] + bias ) + alpha * (x[n] - x[n-1])",
        "explanation": "Hyperbolic tangent non-linear soft clipping emulates magnetic particle alignment saturation, introducing warm odd harmonics and natural transient compression."
    },
    {
        "name": "SSL 4000 Quad-VCA Master Bus Compression",
        "formula": "y_{dB} = T + (x_{dB} - T) / R,   \\text{for } x_{dB} > T + W/2",
        "explanation": "Quad-VCA log-domain gain reduction with soft-knee transition and dual-time constant Auto-Release (tau_fast=100ms, tau_slow=1200ms) delivering classic cohesive mix bus 'glue'."
    },
    {
        "name": "Neve 1073 Marinair Transformer Saturation",
        "formula": "y(t) = \\frac{\\tanh(\\text{drive} \\cdot x(t) + \\text{bias}) - \\tanh(\\text{bias})}{\\tanh(\\text{drive})} + \\alpha \\cdot x^3(t)",
        "explanation": "Simulates single-ended Class-A preamp asymmetrical 2nd-order tube/transistor warmth plus magnetic core 3rd-order hysteresis saturation from the vintage British output transformer."
    },
    {
        "name": "Higher-Order Ambisonics Spherical Harmonics (ACN / SN3D)",
        "formula": "B_l^m(t) = S(t) \\cdot Y_l^m(\\theta, \\phi) = S(t) \\cdot N_l^{|m|} P_l^{|m|}(\\sin\\phi) \\begin{cases} \\cos(m\\theta) & m \\ge 0 \\\\ \\sin(|m|\\theta) & m < 0 \\end{cases}",
        "explanation": "Decomposes directional sound fields on the surface of a sphere into orthogonal spherical harmonic basis functions of degree l and order m, indexed by Ambisonic Channel Number (ACN n = l^2 + l + m) under Schmidt Semi-Normalized (SN3D) convention."
    },
    {
        "name": "dbx 120XP Subharmonic Octave Division",
        "formula": "y_{\\text{sub}}(t) = A_{\\text{env}}(t) \\cdot \\sin\\left(\\frac{\\omega_0}{2} t + \\phi_0\\right) \\cdot \\text{sgn}\\left(z(t)\\right)",
        "explanation": "Extracts the fundamental bass envelope in the 48-112 Hz band, divides cycle frequency by 2 via zero-crossing transition detection, and synthesizes pure sub-octave energy locked to musical dynamics."
    },
    {
        "name": "MaxxBass Psychoacoustic Missing Fundamental (Chebyshev Polynomials)",
        "formula": "H_{\\text{synth}}(x) = c_2 T_2(x) + c_3 T_3(x) + c_4 T_4(x) = c_2(2x^2 - 1) + c_3(4x^3 - 3x) + c_4(8x^4 - 8x^2 + 1)",
        "explanation": "Generates 2nd, 3rd, and 4th order harmonic overtones of low-frequency fundamentals. The auditory cortex perceives the missing fundamental frequency even on mobile transducers incapable of reproducing physical sub-bass."
    },
    {
        "name": "Dynamic Spectral Resonance Prominence & Ballistic Suppression",
        "formula": "P(f) = 20 \\log_{10}\\left(\\frac{|X(f)|}{\\text{Env}_{\\text{baseline}}(f)}\\right); \\quad \\Delta G(f) = -\\text{depth} \\cdot \\max(0, P(f) - T)^{1 + 0.25Q}",
        "explanation": "Extracts dynamic spectral prominence P(f) above a smoothed moving baseline. When prominence exceeds threshold T, applies frequency-dependent notch attenuation smoothed across time with 5ms attack and 50ms release ballistics."
    },
    {
        "name": "Teletronix LA-2A T4 Electro-Optical Memory Decay",
        "formula": "y_{\\text{rel}}(t) = 0.5 \\cdot e^{-t/0.060} + 0.5 \\cdot e^{-t/\\tau_{\\text{slow}}}, \\quad \\tau_{\\text{slow}} = 0.5 + \\min(4.0, 0.25 \\cdot \\text{History}_{\\text{GR}})",
        "explanation": "Dual-stage photocell ballistic release modeled after cadmium sulfide (CdS) photoresistors: 50% initial release drops in 60ms, while the remaining 50% decay exhibits a multi-second memory tail scaling with sustained past gain reduction."
    },
    {
        "name": "Fairchild 670 Variable-Mu Remote-Cutoff Gain Transfer",
        "formula": "\\mu(V_g) = \\frac{\\mu_0}{1 + k \\cdot |V_g|^{1.2}}, \\quad \\text{GR}_{\\text{dB}} = 20 \\log_{10}\\left(\\frac{1}{1 + 1.6 \\cdot |V_g|^{1.15}}\\right)",
        "explanation": "Remote-cutoff dual-triode 6386 tube physical model where rectified control voltage Vg dynamically reduces amplification factor mu without a fixed threshold or sharp knee, creating an ultra-smooth, continuous variable ratio."
    },
    {
        "name": "Master Serial Pipeline Discrete Transfer Composition",
        "formula": "Y(z) = \\prod_{k=N}^1 \\mathcal{T}_k \\left[ X(z) \\right] = \\left( \\mathcal{T}_{\\text{Limiter}} \\circ \\mathcal{T}_{\\text{Tape}} \\circ \\mathcal{T}_{\\text{M/S}} \\circ \\mathcal{T}_{\\text{Dyn}} \\circ \\mathcal{T}_{\\text{Console}} \\circ \\mathcal{T}_{\\text{Bass}} \\circ \\mathcal{T}_{\\text{DeRes}} \\right) X(z)",
        "explanation": "Composes N non-linear, time-variant discrete mastering stages in strict causal sequence. Each stage processes the conditioned output of the previous stage, ensuring surgical artifact removal precedes dynamic expansion, saturation, and final true-peak brickwall limiting."
    },
    {
        "name": "Bit-Perfect Exclusive Hardware DMA & Sample Clock Direct Coupling",
        "formula": "Y[n] = X[n], \\quad \\Delta t_{\\text{buffer}} = \\frac{N_{\\text{frames}}}{f_s} \\cdot 1000\\text{ ms}, \\quad f_{\\text{DAC}} = f_{\\text{source}}",
        "explanation": "Bypasses the OS audio mixer kernel (AudioDG.exe on Windows, AudioFlinger on Android) via WASAPI Exclusive, ASIO, or AAudio MMAP. Guarantees an identity transfer function where output discrete PCM samples Y[n] match input file samples X[n] without digital filtering, sample rate interpolation, or dither quantization noise."
    }
]


def build_manual_html() -> str:
    """Constructs the complete, standalone offline HTML manual."""
    total_phases = len(PHASES_DATA)
    # Build phase items
    phase_cards_html = []
    toc_links = []
    
    for item in PHASES_DATA:
        p_num = item["phase"]
        p_id = f"phase-{p_num}"
        toc_links.append(f"""<a href="#{p_id}" class="toc-item" onclick="setActiveLink(this)">
            <span class="toc-num">{p_num:02d}</span>
            <span class="toc-name">{item['title']}</span>
        </a>""")

        features_li = "".join([f"<li>{feat}</li>" for feat in item["features"]])
        modules_tags = " ".join([f'<span class="badge-module">{mod}</span>' for mod in item["modules"]])

        phase_cards_html.append(f"""
        <article class="phase-card" id="{p_id}">
            <div class="phase-card-header">
                <div class="phase-badge-row">
                    <span class="phase-pill">PHASE {p_num:02d}</span>
                    <span class="phase-cat">{item['category']}</span>
                </div>
                <h2 class="phase-title">{item['title']}</h2>
                <div class="module-bar">{modules_tags}</div>
            </div>
            
            <p class="phase-desc">{item['desc']}</p>
            
            <div class="code-box">
                <div class="code-label">CLI INVOCATION</div>
                <div class="code-line">
                    <code>{item['cli']}</code>
                    <button class="copy-btn" onclick="copyCode(this, '{item['cli']}')">Copy</button>
                </div>
            </div>
            
            <div class="math-box">
                <div class="math-label">MATHEMATICAL / DSP FOUNDATION</div>
                <div class="math-equation">{item['dsp_math']}</div>
            </div>
            
            <div class="features-box">
                <div class="features-label">KEY CAPABILITIES</div>
                <ul class="features-list">{features_li}</ul>
            </div>
        </article>
        """)

    # Build shortcuts table
    shortcut_rows = []
    for sc in KEYBOARD_SHORTCUTS:
        shortcut_rows.append(f"""<tr>
            <td><kbd>{sc['key']}</kbd></td>
            <td>{sc['action']}</td>
            <td><span class="badge-cat">{sc['context']}</span></td>
        </tr>""")
    shortcuts_html = "".join(shortcut_rows)

    # Build math formulas cards
    math_cards = []
    for m in MATH_FORMULAS:
        math_cards.append(f"""
        <div class="formula-card">
            <h3 class="formula-title">{m['name']}</h3>
            <div class="formula-math">{m['formula']}</div>
            <p class="formula-desc">{m['explanation']}</p>
        </div>
        """)
    math_cards_html = "".join(math_cards)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sonance Audiophile Workstation - Engineering Handbook &amp; User Manual</title>
    <style>
        :root {{
            --bg-deep: #07090e;
            --bg-surface: #0e111a;
            --bg-card: #141824;
            --bg-elevated: #1b2132;
            --border: #232a3f;
            --border-highlight: #3a4668;
            --text: #e2e8f0;
            --text-dim: #94a3b8;
            --text-muted: #64748b;
            --cyan: #00f2fe;
            --cyan-glow: rgba(0, 242, 254, 0.25);
            --blue: #4facfe;
            --violet: #9d4edd;
            --gold: #f59e0b;
            --emerald: #10b981;
            --rose: #f43f5e;
            --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: "JetBrains Mono", "Fira Code", Consolas, Menlo, monospace;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background: var(--bg-deep);
            color: var(--text);
            font-family: var(--font-main);
            line-height: 1.6;
            overflow-x: hidden;
        }}

        /* Header Bar */
        header {{
            position: sticky;
            top: 0;
            z-index: 1000;
            background: rgba(14, 17, 26, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: #fff;
        }}

        .brand-pill {{
            background: linear-gradient(135deg, var(--cyan), var(--blue));
            color: #000;
            font-size: 10px;
            font-weight: 800;
            padding: 2px 8px;
            border-radius: 12px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        .search-box {{
            flex: 1;
            max-width: 480px;
            position: relative;
        }}

        .search-box input {{
            width: 100%;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px 14px 8px 36px;
            color: var(--text);
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        .search-box input:focus {{
            border-color: var(--cyan);
            box-shadow: 0 0 0 3px var(--cyan-glow);
        }}

        .search-icon {{
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 14px;
            pointer-events: none;
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .btn-link {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.2s, color 0.2s;
        }}

        .btn-link:hover {{
            background: var(--bg-elevated);
            color: var(--cyan);
            border-color: var(--cyan);
        }}

        /* App Layout */
        .app-container {{
            display: flex;
            min-height: calc(100vh - 61px);
        }}

        /* Sidebar Navigation */
        aside {{
            width: 320px;
            min-width: 320px;
            background: var(--bg-surface);
            border-right: 1px solid var(--border);
            height: calc(100vh - 61px);
            position: sticky;
            top: 61px;
            overflow-y: auto;
            padding: 16px 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .sidebar-section-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            padding: 8px 12px 4px;
        }}

        .toc-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 7px 12px;
            border-radius: 6px;
            color: var(--text-dim);
            text-decoration: none;
            font-size: 12px;
            transition: background 0.15s, color 0.15s;
        }}

        .toc-item:hover {{
            background: var(--bg-card);
            color: #fff;
        }}

        .toc-item.active {{
            background: var(--bg-elevated);
            color: var(--cyan);
            font-weight: 600;
            border-left: 3px solid var(--cyan);
        }}

        .toc-num {{
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
        }}

        .toc-name {{
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* Main Content */
        main {{
            flex: 1;
            padding: 40px;
            max-width: 1080px;
            margin: 0 auto;
        }}

        .hero-banner {{
            background: linear-gradient(135deg, rgba(0, 242, 254, 0.08), rgba(157, 78, 221, 0.08));
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 40px;
        }}

        .hero-banner h1 {{
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -1px;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #fff, var(--cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .hero-banner p {{
            font-size: 15px;
            color: var(--text-dim);
            max-width: 800px;
            margin-bottom: 20px;
        }}

        .meta-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .meta-tag {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 12px;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        /* Section Headings */
        .section-header {{
            margin: 48px 0 24px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .section-header h2 {{
            font-size: 22px;
            font-weight: 700;
            color: #fff;
        }}

        /* Phase Cards */
        .phase-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            transition: border-color 0.2s, box-shadow 0.2s;
            scroll-margin-top: 80px;
        }}

        .phase-card:hover {{
            border-color: var(--border-highlight);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }}

        .phase-card-header {{
            margin-bottom: 16px;
        }}

        .phase-badge-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}

        .phase-pill {{
            background: var(--bg-elevated);
            color: var(--cyan);
            border: 1px solid var(--border-highlight);
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .phase-cat {{
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .phase-title {{
            font-size: 18px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 8px;
        }}

        .module-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .badge-module {{
            background: #080a10;
            border: 1px solid var(--border);
            color: var(--violet);
            font-family: var(--font-mono);
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .phase-desc {{
            font-size: 14px;
            color: var(--text-dim);
            margin-bottom: 16px;
        }}

        .code-box {{
            background: #07090e;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 14px;
        }}

        .code-label {{
            font-size: 10px;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}

        .code-line {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }}

        .code-line code {{
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--cyan);
            word-break: break-all;
        }}

        .copy-btn {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-dim);
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            white-space: nowrap;
            transition: background 0.15s, color 0.15s;
        }}

        .copy-btn:hover {{
            background: var(--bg-elevated);
            color: var(--cyan);
        }}

        .math-box {{
            background: rgba(157, 78, 221, 0.05);
            border: 1px solid rgba(157, 78, 221, 0.2);
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 14px;
        }}

        .math-label {{
            font-size: 10px;
            font-weight: 700;
            color: var(--violet);
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}

        .math-equation {{
            font-family: var(--font-mono);
            font-size: 12px;
            color: #e9d5ff;
        }}

        .features-box {{
            margin-top: 12px;
        }}

        .features-label {{
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}

        .features-list {{
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 6px 16px;
        }}

        .features-list li {{
            font-size: 12px;
            color: var(--text-dim);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .features-list li::before {{
            content: "•";
            color: var(--cyan);
            font-weight: bold;
        }}

        /* Shortcuts Table */
        .table-wrap {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 32px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 13px;
        }}

        th {{
            background: var(--bg-surface);
            padding: 12px 16px;
            color: var(--text-muted);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
        }}

        td {{
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            color: var(--text);
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        kbd {{
            background: var(--bg-surface);
            border: 1px solid var(--border-highlight);
            box-shadow: 0 2px 0 var(--border-highlight);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--cyan);
        }}

        .badge-cat {{
            background: var(--bg-elevated);
            color: var(--text-dim);
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 12px;
        }}

        /* Formula Cards */
        .formula-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}

        .formula-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 18px;
        }}

        .formula-title {{
            font-size: 14px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 10px;
        }}

        .formula-math {{
            background: #07090e;
            border: 1px solid var(--border);
            padding: 10px;
            border-radius: 6px;
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--emerald);
            margin-bottom: 10px;
            overflow-x: auto;
        }}

        .formula-desc {{
            font-size: 12px;
            color: var(--text-dim);
            line-height: 1.5;
        }}

        /* Verification Guide */
        .verify-box {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 40px;
        }}

        .verify-box h3 {{
            font-size: 15px;
            color: var(--gold);
            margin-bottom: 10px;
        }}

        .verify-box p {{
            font-size: 13px;
            color: var(--text-dim);
            margin-bottom: 12px;
        }}

        /* Toast notification */
        #toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--cyan);
            color: #000;
            font-weight: 600;
            font-size: 12px;
            padding: 8px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            opacity: 0;
            transform: translateY(10px);
            transition: opacity 0.2s, transform 0.2s;
            pointer-events: none;
            z-index: 9999;
        }}

        #toast.show {{
            opacity: 1;
            transform: translateY(0);
        }}

        @media (max-width: 900px) {{
            aside {{
                display: none;
            }}
            main {{
                padding: 20px;
            }}
        }}

        @media print {{
            header, aside, .copy-btn {{
                display: none;
            }}
            body, main {{
                background: #fff;
                color: #000;
            }}
            .phase-card {{
                border: 1px solid #ccc;
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <span>🎵 SONANCE</span>
            <span class="brand-pill">WORKSTATION MANUAL</span>
        </div>
        <div class="search-box">
            <span class="search-icon">🔍</span>
            <input type="text" id="manualSearchInput" placeholder="Search {total_phases} phases, DSP algorithms, CLI commands..." onkeyup="filterManualContent()">
        </div>
        <div class="header-actions">
            <a href="#shortcuts-section" class="btn-link">⌨️ Shortcuts</a>
            <a href="#math-section" class="btn-link">📐 DSP Math</a>
            <a href="#verify-section" class="btn-link">🔒 Verification</a>
            <button class="btn-link" onclick="window.print()">🖨️ Print</button>
        </div>
    </header>

    <div class="app-container">
        <aside id="sidebarNav">
            <div class="sidebar-section-title">Master Roadmap (Phases 1-{total_phases})</div>
            {"".join(toc_links)}
            
            <div class="sidebar-section-title" style="margin-top:16px;">Reference &amp; Theory</div>
            <a href="#shortcuts-section" class="toc-item"><span class="toc-num">KB</span><span class="toc-name">Keyboard Shortcuts</span></a>
            <a href="#math-section" class="toc-item"><span class="toc-num">MT</span><span class="toc-name">Audio Engineering Math</span></a>
            <a href="#verify-section" class="toc-item"><span class="toc-num">VR</span><span class="toc-name">Release &amp; Verification</span></a>
        </aside>

        <main>
            <div class="hero-banner">
                <h1>Sonance Audiophile Workstation</h1>
                <p>
                    The unified open-source desktop music platform combining high-resolution streaming, offline caching, 
                    bit-exact CD extraction, stem separation, and over 25 professional mastering and DSP engineering studios.
                </p>
                <div class="meta-tags">
                    <span class="meta-tag">⚡ Version {APP_VERSION}</span>
                    <span class="meta-tag">🎼 {total_phases} Master Phases</span>
                    <span class="meta-tag">🎛️ 53 DSP Engines &amp; Core Modules</span>
                    <span class="meta-tag">🌐 100% Offline Single-File Architecture</span>
                </div>
            </div>

            <div class="section-header" id="catalog-section">
                <h2>Master Phase Catalog (1 - {total_phases})</h2>
                <span style="font-size:12px; color:var(--text-muted);">Click any phase to jump</span>
            </div>

            {"".join(phase_cards_html)}

            <div class="section-header" id="shortcuts-section">
                <h2>Master Keyboard Shortcuts</h2>
                <span style="font-size:12px; color:var(--text-muted);">Global Desktop Hotkeys</span>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th style="width:25%;">Keybinding</th>
                            <th style="width:50%;">Action</th>
                            <th style="width:25%;">Category</th>
                        </tr>
                    </thead>
                    <tbody>
                        {shortcuts_html}
                    </tbody>
                </table>
            </div>

            <div class="section-header" id="math-section">
                <h2>Audio Engineering &amp; DSP Formulas</h2>
                <span style="font-size:12px; color:var(--text-muted);">Mathematical Implementations</span>
            </div>

            <div class="formula-grid">
                {math_cards_html}
            </div>

            <div class="section-header" id="verify-section">
                <h2>Cryptographic Release Verification</h2>
                <span style="font-size:12px; color:var(--text-muted);">Integrity Assurance</span>
            </div>

            <div class="verify-box">
                <h3>Verifying Sonance Codebase Checksums</h3>
                <p>
                    Sonance generates SHA-256 and MD5 cryptographic manifests during every release packaging cycle. 
                    You can verify that zero files have been modified or corrupted using standard terminal utilities:
                </p>
                <div class="code-box" style="margin-bottom:12px;">
                    <div class="code-label">LINUX / MACOS VERIFICATION</div>
                    <div class="code-line">
                        <code>sha256sum -c RELEASE.sha256sum</code>
                    </div>
                </div>
                <div class="code-box">
                    <div class="code-label">WINDOWS POWERSHELL VERIFICATION</div>
                    <div class="code-line">
                        <code>python sonance.py --package-release --verify-only</code>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <div id="toast">Copied to clipboard!</div>

    <script>
        function copyCode(btn, text) {{
            navigator.clipboard.writeText(text).then(() => {{
                showToast('CLI command copied to clipboard!');
                btn.innerText = 'Copied!';
                setTimeout(() => btn.innerText = 'Copy', 1500);
            }}).catch(() => {{
                showToast('Failed to copy');
            }});
        }}

        function showToast(msg) {{
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2200);
        }}

        function setActiveLink(el) {{
            document.querySelectorAll('.toc-item').forEach(item => item.classList.remove('active'));
            el.classList.add('active');
        }}

        function filterManualContent() {{
            const query = document.getElementById('manualSearchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.phase-card');
            cards.forEach(card => {{
                const text = card.innerText.toLowerCase();
                card.style.display = text.includes(query) ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""
    return html_content


def generate_offline_manual(output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates the offline HTML manual and writes it to disk.
    Returns path and byte size.
    """
    dest = Path(output_path).resolve() if output_path else DEFAULT_MANUAL_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)

    html_code = build_manual_html()
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html_code)

    file_size = dest.stat().st_size
    return {
        "success": True,
        "output_path": str(dest),
        "total_phases": len(PHASES_DATA),
        "file_size": file_size,
        "file_size_formatted": f"{file_size / 1024:.1f} KB"
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sonance Offline Audiophile Guide & Manual Generator")
    parser.add_argument("--output", type=str, default=None, help="Output file path for manual.html")
    parser.add_argument("--open", action="store_true", help="Automatically open generated manual in default browser")

    args = parser.parse_args()

    print("=" * 70)
    print(f"  {WORKSTATION_NAME} v{APP_VERSION}")
    print("  Phase 27 Grand Finale: Offline Audiophile Guide & Handbook Generator")
    print("=" * 70)

    print(f"[*] Compiling interactive single-file manual for all {len(PHASES_DATA)} phases...")
    res = generate_offline_manual(args.output)

    print(f"[+] Manual Generated Successfully: {res['output_path']}")
    print(f"[+] Document Scope : {res['total_phases']} Phases Documented ({res['file_size_formatted']})")
    print("=" * 70)

    if args.open:
        print("[*] Opening manual in default browser...")
        webbrowser.open(f"file://{os.path.abspath(res['output_path'])}")


if __name__ == "__main__":
    main()
