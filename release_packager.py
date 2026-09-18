"""
Sonance - Universal Workstation Release Packaging & Manifest Auditor Studio
Phase 27 Grand Finale Release Management System

Audits codebase integrity across all 27 phases, verifies 40+ DSP engines and core modules,
computes cryptographic SHA-256 and MD5 manifests, and generates clean distribution bundles.
"""

import os
import sys
import json
import time
import hashlib
import zipfile
import py_compile
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

APP_VERSION = "3.6.1"
WORKSTATION_NAME = "Sonance Audiophile Workstation"
ROOT_DIR = Path(__file__).parent.resolve()

# Modules across all 27 phases to audit for integrity
CORE_PHASE_MODULES = [
    # Phase 1-5: Core Downloader, Engine, Tagging, Caching, Cloud
    ("downloader_engine", "Phase 1: High-Performance Engine & Multi-Threaded Engine"),
    ("lyrics_engine", "Phase 1: Multi-Provider Synchronized Lyrics Engine"),
    ("tag_editor", "Phase 1: Comprehensive ID3v2/Vorbis/MP4 Tag Editor"),
    ("cache_manager", "Phase 2: Local Audio Cache & Waveform Indexer"),
    ("cloud_streamer", "Phase 3: High-Res Streaming & Cloud Pre-fetch"),
    ("device_sync", "Phase 4: Portable Device Sync & MTP Transfer"),
    ("library_doctor", "Phase 5: Music Library Health & Orphan Scanner"),
    ("flac_verifier", "Phase 5: Lossless FLAC Bit-Exact Stream Verifier"),
    
    # Phase 6-10: AccurateRip, AutoEq, CD Ripper, Stems, 8D Audio
    ("accuraterip_verifier", "Phase 6: AccurateRip V1/V2 Bit-Accurate Verification"),
    ("headphone_autoeq", "Phase 7: Headphone AutoEq & Parametric Target Profiler"),
    ("cd_ripper", "Phase 8: Bit-Exact Audio CD Ripper & CUE Sheet Generator"),
    ("vocal_separator", "Phase 9: AI Vocal, Drum, Bass & Stem Separator"),
    ("audio_8d_spatializer", "Phase 10: 360-Degree Binaural 8D Audio Spatializer"),
    
    # Phase 11-15: ReplayGain 2.0, Parametric EQ, Phase Meter, DAC Tester, Drift Retimer
    ("replaygain_normalizer", "Phase 11: EBU R128 & ReplayGain 2.0 Loudness Normalizer"),
    ("parametric_eq", "Phase 12: 10-Band Biquad Parametric Equalizer Studio"),
    ("phase_correlation", "Phase 13: Stereo Phase Correlation & Lissajous Goniometer"),
    ("dac_tester", "Phase 14: Bit-Depth & Nyquist DAC Performance Tester"),
    ("lyrics_retimer", "Phase 15: Sub-Millisecond Lyrics Drift & Sync Retimer"),
    
    # Phase 16-20: Spectrum Analyzer, De-Clipper, Track Splitter, Lyrics Video, Upsampler
    ("spectrum_analyzer", "Phase 16: 64-Band Real-Time Fast Fourier Spectrum Analyzer"),
    ("audio_declipper", "Phase 17: Cubic Spline & Harmonic Audio De-Clipper"),
    ("track_splitter", "Phase 18: Silence Detection & Vinyl/Cassette Track Splitter"),
    ("lyrics_video_maker", "Phase 19: Typography Kinetic Lyrics Video Maker Studio"),
    ("audio_upsampler", "Phase 20: Band-Limited Whittaker-Shannon Sinc Upsampler"),
    
    # Phase 21-25: CUE Fixer, Room IR, DSD to PCM, Limiter, Bloat, De-Esser, Mid-Side, Tape, Formants, Loudness War, Stems Remixer
    ("cue_fixer", "Phase 21: CUE Sheet Drift & Multi-Track Fixer"),
    ("room_ir_synthesizer", "Phase 21: Synthetic Acoustic Room Impulse Response Engine"),
    ("lrc_to_ass_converter", "Phase 21: Advanced SubStation Alpha (ASS) Karaoke Generator"),
    ("dsd_converter", "Phase 22: Bit-Exact DSD/DSF to High-Resolution PCM Decimator"),
    ("subsample_delay", "Phase 22: Sub-Sample Fractional Delay Phase Aligner"),
    ("mastering_limiter", "Phase 23: Audiophile True Peak Brickwall Mastering Limiter"),
    ("album_art_studio", "Phase 23: Metadata Embedded Album Art Bloat Reducer"),
    ("audio_deesser", "Phase 24: Dynamic Multiband Audio De-Esser & Sibilance Reducer"),
    ("midside_processor", "Phase 24: Mid-Side Spatial Width & Monomaker Studio"),
    ("audio_watermark", "Phase 24: Inaudible Spread-Spectrum Lossless Audio Watermark"),
    ("cue_markers", "Phase 24: Non-Destructive CUE Markers & Chapter Indexer"),
    ("analog_tape_emulator", "Phase 25: Master Studer A800 Analog Tape Saturation Studio"),
    ("formant_shifter", "Phase 25: Vocal Formant Shifter & Spectral Envelope Morph"),
    ("loudness_war_studio", "Phase 25: Loudness War Dynamics & Crest Factor Analyzer"),
    ("stems_remixer", "Phase 25: Multi-Track Stems & Audio Remixer Studio"),
    
    # Phase 26: Transient Shaper, 3D Binaural Virtualizer, Noise Gate, Tape Echo
    ("transient_shaper", "Phase 26: Audiophile Transient Shaper & Drum Punch Designer"),
    ("binaural_virtualizer", "Phase 26: Binaural 3D Ambisonic Room & Headphone Virtualizer"),
    ("audio_noisegate", "Phase 26: Broadcast Audio Noise Gate & Downward Expander"),
    ("tape_echo_delay", "Phase 26: Stereo Ping-Pong & Multi-Tap BBD Tape Echo Studio"),

    # Phase 27: Release Packager & Offline Manual
    ("release_packager", "Phase 27: Universal Workstation Release Packaging & Manifest Auditor"),
    ("docs_generator", "Phase 27: Offline Audiophile Guide & Workstation Manual Generator"),

    # Phase 28: VST3 & CLAP Audio Plugin Host & Rack
    ("plugin_host", "Phase 28: VST3 & CLAP Audio Plugin Host & Multi-Slot Rack Studio"),

    # Phase 29: Dolby Atmos 7.1.4 Spatializer & Multichannel Audio Renderer
    ("spatial_multichannel", "Phase 29: Dolby Atmos 7.1.4 Bed Spatializer & Multichannel Audio Renderer"),

    # Phase 30: British Class-A Console Channel Strip & SSL G-Master Bus Studio
    ("console_channel_strip", "Phase 30: British Class-A Console Channel Strip & SSL G-Master Bus Studio"),

    # Phase 31: Higher-Order Ambisonics & 360-Degree VR Spatializer Studio
    ("ambisonic_hoa", "Phase 31: Higher-Order Ambisonics & 360-Degree VR Spatializer Studio"),

    # Phase 32: Psychoacoustic Subharmonic Bass Synthesizer & Missing Fundamental Studio
    ("subharmonic_bass", "Phase 32: Psychoacoustic Subharmonic Bass Synthesizer & Missing Fundamental Studio"),

    # Phase 33: Dynamic Spectral Resonance Suppressor & Surgical De-Resonator Studio
    ("resonance_suppressor", "Phase 33: Dynamic Spectral Resonance Suppressor & Surgical De-Resonator Studio"),

    # Phase 34: Vintage Optical & Variable-Mu Master Compressor Studio
    ("vintage_compressor", "Phase 34: Vintage Optical & Variable-Mu Master Compressor Studio"),

    # Phase 35: The Grand Workstation Zenith & Master Orchestration Suite
    ("zenith_orchestrator", "Phase 35: The Grand Workstation Zenith & Master Orchestration Suite"),

    # Phase 36: Audiophile Exclusive Audio & Hardware DAC Output Engine
    ("exclusive_audio_engine", "Phase 36: Audiophile Exclusive Audio & Hardware DAC Output Engine"),
]

# File classification patterns
CATEGORIES = {
    "core": [".py"],
    "ui": [".html", ".css", ".js", ".svg", ".png", ".jpg", ".ico"],
    "docs": [".md", ".txt", ".rst"],
    "config": [".json", ".yaml", ".yml", ".ini", ".toml", ".cue"],
}

EXCLUDE_DIRS = {
    "__pycache__", ".git", ".github", ".venv", "venv", "env", 
    ".pytest_cache", ".idea", ".vscode", "dist", "build", "node_modules"
}

EXCLUDE_FILES = {
    ".DS_Store", "desktop.ini", "thumbs.db", "*.pyc", "*.pyo"
}


def compute_hashes(file_path: Path) -> Tuple[str, str, int]:
    """Computes SHA-256, MD5, and file size in bytes."""
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    size = 0
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return sha256.hexdigest(), md5.hexdigest(), size


def categorize_file(path_str: str) -> str:
    """Categorizes a file based on extension and path."""
    ext = os.path.splitext(path_str)[1].lower()
    p_lower = path_str.lower()
    
    if "ui" in p_lower:
        return "ui"
    if p_lower.endswith(".py"):
        if any(term in p_lower for term in ["dsp", "audio", "eq", "filter", "limiter", "tape", "echo", "transient", "binaural", "gate", "deesser", "stems"]):
            return "dsp"
        return "core"
    if ext in [".md", ".txt", ".rst"]:
        return "docs"
    if ext in [".json", ".yaml", ".yml", ".ini", ".toml"]:
        return "config"
    return "asset"


def audit_phase_modules(verbose: bool = False) -> Dict[str, Any]:
    """
    Validates module integrity and importability across all 27 phases.
    Returns detailed audit report.
    """
    passed = []
    failed = []
    
    for mod_name, phase_desc in CORE_PHASE_MODULES:
        file_path = ROOT_DIR / f"{mod_name}.py"
        if not file_path.exists():
            failed.append({
                "module": mod_name,
                "phase": phase_desc,
                "error": "File not found on disk"
            })
            continue
            
        # Verify syntax with py_compile
        try:
            py_compile.compile(str(file_path), doraise=True)
        except py_compile.PyCompileError as pe:
            failed.append({
                "module": mod_name,
                "phase": phase_desc,
                "error": f"Syntax error: {pe.msg}"
            })
            continue
            
        # Verify module import
        try:
            mod = importlib.import_module(mod_name)
            passed.append({
                "module": mod_name,
                "phase": phase_desc,
                "status": "OK",
                "doc": (mod.__doc__ or "").strip().split("\n")[0] if mod.__doc__ else "No docstring"
            })
        except Exception as e:
            failed.append({
                "module": mod_name,
                "phase": phase_desc,
                "error": f"Import error: {str(e)}"
            })

    return {
        "total_modules": len(CORE_PHASE_MODULES),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "passed": passed,
        "failed": failed,
        "integrity_percent": (len(passed) / len(CORE_PHASE_MODULES)) * 100.0 if CORE_PHASE_MODULES else 0.0
    }


def scan_codebase_files(root_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Scans the repository, computing cryptographic checksums for all distribution files.
    Excludes caches, virtual environments, and temporary artifacts.
    """
    target = root_dir or ROOT_DIR
    records = []

    for root, dirs, files in os.walk(target):
        # Modify dirs in-place to skip excluded folders
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        
        for f in sorted(files):
            if f in EXCLUDE_FILES or f.endswith(".pyc") or f.startswith("."):
                continue
                
            full_path = Path(root) / f
            try:
                rel_path = full_path.relative_to(target).as_posix()
                sha256, md5, size = compute_hashes(full_path)
                cat = categorize_file(rel_path)
                
                records.append({
                    "path": rel_path,
                    "size": size,
                    "sha256": sha256,
                    "md5": md5,
                    "category": cat
                })
            except Exception:
                continue

    return records


def format_bytes(bytes_count: int) -> str:
    """Formats raw byte count into human-readable representation."""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"


def generate_manifests(
    records: List[Dict[str, Any]], 
    audit_report: Dict[str, Any], 
    output_dir: Optional[Path] = None
) -> Dict[str, str]:
    """
    Writes RELEASE.sha256sum, RELEASE.md5sum, and RELEASE.manifest.json.
    """
    out_path = output_dir or ROOT_DIR
    out_path.mkdir(parents=True, exist_ok=True)
    
    sha256_file = out_path / "RELEASE.sha256sum"
    md5_file = out_path / "RELEASE.md5sum"
    manifest_file = out_path / "RELEASE.manifest.json"
    
    # 1. SHA256 sum file (Linux format)
    with open(sha256_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(f"{r['sha256']}  {r['path']}\n")
            
    # 2. MD5 sum file
    with open(md5_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(f"{r['md5']}  {r['path']}\n")
            
    # 3. JSON Manifest
    total_bytes = sum(r["size"] for r in records)
    cat_counts = {}
    for r in records:
        cat = r["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        
    manifest_data = {
        "project": WORKSTATION_NAME,
        "version": APP_VERSION,
        "phase": "Phase 27 (Grand Finale Release)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "audit": {
            "total_modules_audited": audit_report["total_modules"],
            "passed_count": audit_report["passed_count"],
            "failed_count": audit_report["failed_count"],
            "integrity_percent": f"{audit_report['integrity_percent']:.1f}%"
        },
        "summary": {
            "total_files": len(records),
            "total_bytes": total_bytes,
            "total_bytes_formatted": format_bytes(total_bytes),
            "categories": cat_counts
        },
        "files": records
    }
    
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
        
    return {
        "sha256sum": str(sha256_file),
        "md5sum": str(md5_file),
        "manifest": str(manifest_file)
    }


def create_distribution_zip(
    records: List[Dict[str, Any]], 
    output_dir: Optional[Path] = None
) -> str:
    """
    Creates a clean zip distribution archive of the workstation.
    """
    out_path = output_dir or (ROOT_DIR / "dist")
    out_path.mkdir(parents=True, exist_ok=True)
    
    zip_name = f"sonance-workstation-v{APP_VERSION}.zip"
    zip_path = out_path / zip_name
    written = set()
    
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for r in records:
            src = ROOT_DIR / r["path"]
            arc = f"sonance-v{APP_VERSION}/{r['path']}"
            if src.exists() and arc not in written:
                zf.write(src, arcname=arc)
                written.add(arc)
                
        # Also include manifests if present and not already written
        for mf_name in ["RELEASE.sha256sum", "RELEASE.md5sum", "RELEASE.manifest.json"]:
            mf_path = ROOT_DIR / mf_name
            arc = f"sonance-v{APP_VERSION}/{mf_name}"
            if mf_path.exists() and arc not in written:
                zf.write(mf_path, arcname=arc)
                written.add(arc)

    return str(zip_path)


def audit_and_package(
    target_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    create_zip: bool = False,
    verify_only: bool = False
) -> Dict[str, Any]:
    """
    Comprehensive workflow: Audits all phase modules, scans files,
    generates checksum manifests, and optionally creates a release zip archive.
    """
    root = Path(target_dir).resolve() if target_dir else ROOT_DIR
    out = Path(output_dir).resolve() if output_dir else root

    # 1. Audit all 27 Phase modules
    audit_res = audit_phase_modules()

    if verify_only:
        return {
            "status": "verified" if audit_res["failed_count"] == 0 else "degraded",
            "audit": audit_res,
            "manifests": None,
            "zip_package": None
        }

    # 2. Scan codebase and compute cryptographic hashes
    records = scan_codebase_files(root)

    # 3. Generate cryptographic manifests
    manifest_paths = generate_manifests(records, audit_res, out)

    # 4. Optional ZIP packaging
    zip_pkg = None
    if create_zip:
        zip_pkg = create_distribution_zip(records, out / "dist" if out == root else out)

    total_bytes = sum(r["size"] for r in records)
    return {
        "status": "success" if audit_res["failed_count"] == 0 else "warning",
        "version": APP_VERSION,
        "audit": audit_res,
        "manifests": manifest_paths,
        "zip_package": zip_pkg,
        "total_files": len(records),
        "total_bytes": total_bytes,
        "total_bytes_formatted": format_bytes(total_bytes)
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sonance Universal Workstation Release Packaging & Manifest Auditor Studio")
    parser.add_argument("--audit-only", action="store_true", help="Only perform module import & syntax integrity audit")
    parser.add_argument("--zip", action="store_true", help="Create clean distribution ZIP package")
    parser.add_argument("--out-dir", type=str, default=None, help="Custom output directory for release manifests and zip")
    
    args = parser.parse_args()

    print("=" * 70)
    print(f"  {WORKSTATION_NAME} v{APP_VERSION}")
    print("  Phase 27 Grand Finale: Universal Release Packaging & Manifest Auditor")
    print("=" * 70)

    print("[*] Auditing module integrity across all 27 phases...")
    res = audit_and_package(
        output_dir=args.out_dir,
        create_zip=args.zip,
        verify_only=args.audit_only
    )

    audit = res["audit"]
    print(f"[+] Total Modules Checked : {audit['total_modules']}")
    print(f"[+] Modules Passed        : {audit['passed_count']}")
    print(f"[+] Modules Failed        : {audit['failed_count']}")
    print(f"[+] Overall Integrity     : {audit['integrity_percent']:.1f}%")

    if audit["failed"]:
        print("\n[-] Integrity Warnings:")
        for f in audit["failed"]:
            print(f"    - {f['module']}: {f['error']}")

    if args.audit_only:
        print("\n[+] Audit check finished.")
        return

    print("\n[+] Cryptographic Manifests Generated:")
    print(f"    - SHA-256 Manifest : {res['manifests']['sha256sum']}")
    print(f"    - MD5 Manifest     : {res['manifests']['md5sum']}")
    print(f"    - JSON Metadata    : {res['manifests']['manifest']}")
    print(f"[+] Codebase Scope     : {res['total_files']} files ({res['total_bytes_formatted']})")

    if res["zip_package"]:
        print(f"[+] Release Distribution ZIP Archive: {res['zip_package']}")

    print("=" * 70)
    print("  RELEASE INTEGRITY AUDIT COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
