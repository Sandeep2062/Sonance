#!/usr/bin/env bash
# ==============================================================================
# Sonance Universal Version Bumper (Bash / Linux / macOS / Git Bash)
# ==============================================================================
# Prompts for new version or accepts it as command-line argument.
# Examples:
#   ./bump_version.sh
#   ./bump_version.sh 2.25
#   ./bump_version.sh 4.8
#   ./bump_version.sh 3.7.0
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="$1"

if [ -z "$VERSION" ]; then
    echo "========================================================================"
    echo "       🎵 Sonance Audiophile Workstation - Version Bumper       "
    echo "========================================================================"
    printf "Enter new version (e.g. 2.25, 4.8, 3.7.0): "
    read -r VERSION
fi

if [ -z "$VERSION" ]; then
    echo "[-] Error: Version cannot be empty."
    exit 1
fi

# Detect python command
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
elif command -v py &>/dev/null; then
    PYTHON_CMD="py"
else
    echo "[-] Error: Python is not found in PATH."
    exit 1
fi

$PYTHON_CMD update_version.py "$VERSION"
