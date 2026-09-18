#!/usr/bin/env python3
"""
update_version.py - Sonance Universal Version Bumper
====================================================
Automatically propagates a new version string across all components of Sonance:
- Flutter/Dart (pubspec.yaml, settings_view.dart, tag_service.dart, update_service.dart)
- Desktop Native Runners (Linux CMakeLists.txt, Windows CMakeLists.txt, macOS Info.plist)
- Python Core (release_packager.py, docs_generator.py, modern_lyrics_downloader.py, sonance.py, cd_ripper.py, scrobbler.py, tag_editor.py)
- Web Workstation UI & Docs (ui/index.html, ui/manual.html, README.md)
- Release Manifests & Cryptographic Checksums (RELEASE.manifest.json, RELEASE.sha256sum, RELEASE.md5sum)

Usage:
  Interactive:
    python update_version.py
  CLI Argument:
    python update_version.py 2.25
    python update_version.py 4.8
    python update_version.py 3.7.0
"""

import os
import re
import sys
from pathlib import Path
from typing import Tuple, Dict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).parent.resolve()


def parse_version_input(raw: str) -> Tuple[str, str, str, str]:
    """
    Parses user input into:
    - raw_clean: cleaned raw input, e.g. "2.25", "4.8", "3.7.0"
    - semver: standard semantic version, e.g. "2.25.0", "4.8.0", "3.7.0"
    - short_ver: major.minor, e.g. "2.25", "4.8", "3.7"
    - display_ver: user-friendly version string for titles & badges
    """
    cleaned = raw.strip()
    if cleaned.lower().startswith("v"):
        cleaned = cleaned[1:].strip()

    # Extract version numbers
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(.*)$", cleaned)
    if not match:
        raise ValueError(f"Invalid version format: '{raw}'. Expected numbers like 2.25, 4.8, or 3.7.0")

    major = match.group(1)
    minor = match.group(2) if match.group(2) is not None else "0"
    patch = match.group(3) if match.group(3) is not None else "0"
    suffix = match.group(4) or ""

    semver = f"{major}.{minor}.{patch}{suffix}"
    short_ver = f"{major}.{minor}"
    display_ver = cleaned

    return cleaned, semver, short_ver, display_ver


def update_file(path: Path, transform_fn) -> bool:
    """Safely reads, transforms, and writes a file if changed."""
    if not path.exists():
        print(f"  [-] Warning: File not found: {path.relative_to(ROOT_DIR)}")
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = transform_fn(content)
        if new_content != content:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_content)
            print(f"  [+] Updated: {path.relative_to(ROOT_DIR)}")
            return True
        else:
            print(f"  [.] Unchanged (already current): {path.relative_to(ROOT_DIR)}")
            return False
    except Exception as e:
        print(f"  [-] Error updating {path.relative_to(ROOT_DIR)}: {e}")
        return False


def bump_all_versions(raw_version: str) -> Dict[str, str]:
    raw_clean, semver, short_ver, display_ver = parse_version_input(raw_version)

    print("\n" + "=" * 70)
    print("  🎵 SONANCE UNIVERSAL VERSION BUMPER")
    print("=" * 70)
    print(f"  Target Version Input : {raw_clean}")
    print(f"  Normalized SemVer    : {semver}")
    print(f"  Short Version (UI)   : {short_ver}")
    print(f"  Display Version      : {display_ver}")
    print("=" * 70 + "\n")

    updated_count = 0

    # 1. pubspec.yaml
    def update_pubspec(c: str) -> str:
        return re.sub(r"^(version:\s*)[\d\.]+(\+\d+)?", rf"\g<1>{semver}+1", c, flags=re.MULTILINE)
    if update_file(ROOT_DIR / "pubspec.yaml", update_pubspec): updated_count += 1

    # 2. README.md
    def update_readme(c: str) -> str:
        box_title = f"SONANCE v{display_ver}".center(38)
        # Update ASCII banner
        c = re.sub(r"│\s*SONANCE\s+v[^\s│]+\s*│", f"│{box_title}│", c)
        return c
    if update_file(ROOT_DIR / "README.md", update_readme): updated_count += 1

    # 3. ui/index.html
    def update_index_html(c: str) -> str:
        c = re.sub(r'<div class="brand-badge">v[^<]+</div>', f'<div class="brand-badge">v{short_ver}</div>', c)
        c = re.sub(r'<span>Sonance v[^<]+</span>', f'<span>Sonance v{semver}</span>', c)
        return c
    if update_file(ROOT_DIR / "ui" / "index.html", update_index_html): updated_count += 1

    # 4. ui/manual.html
    def update_manual_html(c: str) -> str:
        return re.sub(r'<span class="meta-tag">⚡ Version [^<]+</span>', f'<span class="meta-tag">⚡ Version {semver}</span>', c)
    if update_file(ROOT_DIR / "ui" / "manual.html", update_manual_html): updated_count += 1

    # 5. release_packager.py
    def update_packager(c: str) -> str:
        return re.sub(r'^(APP_VERSION\s*=\s*")[^"]+(")', rf'\g<1>{semver}\g<2>', c, flags=re.MULTILINE)
    if update_file(ROOT_DIR / "release_packager.py", update_packager): updated_count += 1

    # 6. docs_generator.py
    def update_docs(c: str) -> str:
        return re.sub(r'^(APP_VERSION\s*=\s*")[^"]+(")', rf'\g<1>{semver}\g<2>', c, flags=re.MULTILINE)
    if update_file(ROOT_DIR / "docs_generator.py", update_docs): updated_count += 1

    # 7. modern_lyrics_downloader.py
    def update_modern_lyrics(c: str) -> str:
        return re.sub(r'^(APP_VERSION\s*=\s*")[^"]+(")', rf'\g<1>{semver}\g<2>', c, flags=re.MULTILINE)
    if update_file(ROOT_DIR / "modern_lyrics_downloader.py", update_modern_lyrics): updated_count += 1

    # 8. sonance.py
    def update_sonance_py(c: str) -> str:
        return re.sub(r'SONANCE AUDIOPHILE WORKSTATION v[\d\.]+', f'SONANCE AUDIOPHILE WORKSTATION v{semver}', c)
    if update_file(ROOT_DIR / "sonance.py", update_sonance_py): updated_count += 1

    # 9. lib/ui/views/settings_view.dart
    def update_settings_view(c: str) -> str:
        return re.sub(r"(title:\s*'Sonance v)[\d\.]+(',)", rf"\g<1>{semver}\g<2>", c)
    if update_file(ROOT_DIR / "lib" / "ui" / "views" / "settings_view.dart", update_settings_view): updated_count += 1

    # 10. lib/core/services/tag_service.dart
    def update_tag_service(c: str) -> str:
        return re.sub(r"(Sonance/)[\d\.]+(\s*\([^)]+\))", rf"\g<1>{semver}\g<2>", c)
    if update_file(ROOT_DIR / "lib" / "core" / "services" / "tag_service.dart", update_tag_service): updated_count += 1

    # 11. lib/core/services/update_service.dart
    def update_update_service(c: str) -> str:
        c = re.sub(r"(final currentVersion = pkgInfo\.version\.isNotEmpty \? pkgInfo\.version : ')[^']*(';)", rf"\g<1>{semver}\g<2>", c)
        c = re.sub(r"(currentVersion:\s*')[^']*(',)", rf"\g<1>{semver}\g<2>", c)
        c = re.sub(r"(latestVersion:\s*')[^']*(',)", rf"\g<1>{semver}\g<2>", c)
        return c
    if update_file(ROOT_DIR / "lib" / "core" / "services" / "update_service.dart", update_update_service): updated_count += 1

    # 12. cd_ripper.py
    def update_cd_ripper(c: str) -> str:
        return re.sub(r'("User-Agent":\s*"Sonance/)[\d\.]+(\s*\([^"]+\)")', rf'\g<1>{semver}\g<2>', c)
    if update_file(ROOT_DIR / "cd_ripper.py", update_cd_ripper): updated_count += 1

    # 13. scrobbler.py
    def update_scrobbler(c: str) -> str:
        return re.sub(r'("User-Agent":\s*"Sonance/)[\d\.]+(\s*\([^"]+\)")', rf'\g<1>{semver}\g<2>', c)
    if update_file(ROOT_DIR / "scrobbler.py", update_scrobbler): updated_count += 1

    # 14. tag_editor.py
    def update_tag_editor(c: str) -> str:
        return re.sub(r'("User-Agent":\s*"Sonance/)[\d\.]+(\s*\([^"]+\)")', rf'\g<1>{semver}\g<2>', c)
    if update_file(ROOT_DIR / "tag_editor.py", update_tag_editor): updated_count += 1

    # 15. linux/CMakeLists.txt
    def update_linux_cmake(c: str) -> str:
        return re.sub(r'(add_definitions\(-DFLUTTER_VERSION=")[^"]+("\))', rf'\g<1>{semver}\g<2>', c)
    if update_file(ROOT_DIR / "linux" / "CMakeLists.txt", update_linux_cmake): updated_count += 1

    # 16. windows/CMakeLists.txt
    def update_windows_cmake(c: str) -> str:
        return re.sub(r'(add_definitions\(-DFLUTTER_VERSION=")[^"]+("\))', rf'\g<1>{semver}\g<2>', c)
    if update_file(ROOT_DIR / "windows" / "CMakeLists.txt", update_windows_cmake): updated_count += 1

    # 17. macos/Runner/Info.plist
    def update_macos_plist(c: str) -> str:
        return re.sub(r'(<key>CFBundleShortVersionString</key>\s*<string>)[^<]+(</string>)', rf'\g<1>{semver}\g<2>', c)
    if update_file(ROOT_DIR / "macos" / "Runner" / "Info.plist", update_macos_plist): updated_count += 1

    # 18. Regenerate offline manual HTML
    print("\n[*] Regenerating ui/manual.html via docs_generator.py...")
    try:
        from docs_generator import generate_offline_manual
        generate_offline_manual()
        print("  [+] ui/manual.html refreshed.")
    except Exception as e:
        print(f"  [-] Note: docs_generator failed: {e}")

    # 19. Regenerate cryptographic release manifests (RELEASE.manifest.json, sha256sum, md5sum)
    print("\n[*] Auditing and refreshing release manifests via release_packager.py...")
    try:
        from release_packager import audit_and_package
        res = audit_and_package(verify_only=False)
        audit = res["audit"]
        print(f"  [+] Modules Audited : {audit['total_modules']} ({audit['integrity_percent']:.1f}% integrity)")
        print(f"  [+] Manifest Path    : {res['manifests']['manifest']}")
        print(f"  [+] SHA-256 Hashes   : {res['manifests']['sha256sum']}")
    except Exception as e:
        print(f"  [-] Note: release_packager failed: {e}")

    print("\n" + "=" * 70)
    print(f"  ✅ SUCCESS: Version updated to v{semver} (Display: {display_ver}) across {updated_count} files!")
    print("=" * 70 + "\n")

    return {
        "raw": raw_clean,
        "semver": semver,
        "short": short_ver,
        "display": display_ver,
    }


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        raw_version = sys.argv[1]
    else:
        print("=" * 70)
        print("       🎵 Sonance Audiophile Workstation - Version Bumper       ")
        print("=" * 70)
        try:
            raw_version = input("Enter new version (e.g. 2.25, 4.8, 3.7.0): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[!] Operation cancelled by user.")
            sys.exit(0)

    if not raw_version:
        print("[-] Error: Version string cannot be empty.")
        sys.exit(1)

    try:
        bump_all_versions(raw_version)
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
