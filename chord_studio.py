#!/usr/bin/env python3
"""
Sonance - Synchronized Guitar & Piano Chord Studio
===================================================
Provides synchronized chord accompaniment for karaoke lyrics, interactive
guitar chord tab diagrams, and key-based progression generators.

Author: Sandeep Khadka (Sandeep2062) <sandeepkhadka9090@gmail.com>
License: GNU GPLv3 with Commons Clause
"""

import re
from typing import Dict, Any, List, Optional, Tuple

# Comprehensive database of standard guitar chords (6-string E-A-D-G-B-E)
# Frets: -1 means muted (X), 0 means open string.
GUITAR_CHORDS_DB: Dict[str, Dict[str, Any]] = {
    # Major Chords
    "C": {"frets": [-1, 3, 2, 0, 1, 0], "fingers": [0, 3, 2, 0, 1, 0], "base_fret": 1},
    "D": {"frets": [-1, -1, 0, 2, 3, 2], "fingers": [0, 0, 0, 1, 3, 2], "base_fret": 1},
    "E": {"frets": [0, 2, 2, 1, 0, 0], "fingers": [0, 2, 3, 1, 0, 0], "base_fret": 1},
    "F": {"frets": [1, 3, 3, 2, 1, 1], "fingers": [1, 3, 4, 2, 1, 1], "base_fret": 1, "barre": 1},
    "G": {"frets": [3, 2, 0, 0, 0, 3], "fingers": [2, 1, 0, 0, 0, 3], "base_fret": 1},
    "A": {"frets": [-1, 0, 2, 2, 2, 0], "fingers": [0, 0, 1, 2, 3, 0], "base_fret": 1},
    "B": {"frets": [-1, 2, 4, 4, 4, 2], "fingers": [0, 1, 2, 3, 4, 1], "base_fret": 2, "barre": 2},
    "C#": {"frets": [-1, 4, 6, 6, 6, 4], "fingers": [0, 1, 2, 3, 4, 1], "base_fret": 4, "barre": 4},
    "Db": {"frets": [-1, 4, 6, 6, 6, 4], "fingers": [0, 1, 2, 3, 4, 1], "base_fret": 4, "barre": 4},
    "Eb": {"frets": [-1, 6, 8, 8, 8, 6], "fingers": [0, 1, 2, 3, 4, 1], "base_fret": 6, "barre": 6},
    "F#": {"frets": [2, 4, 4, 3, 2, 2], "fingers": [1, 3, 4, 2, 1, 1], "base_fret": 2, "barre": 2},
    "Gb": {"frets": [2, 4, 4, 3, 2, 2], "fingers": [1, 3, 4, 2, 1, 1], "base_fret": 2, "barre": 2},
    "Ab": {"frets": [4, 6, 6, 5, 4, 4], "fingers": [1, 3, 4, 2, 1, 1], "base_fret": 4, "barre": 4},
    "Bb": {"frets": [-1, 1, 3, 3, 3, 1], "fingers": [0, 1, 2, 3, 4, 1], "base_fret": 1, "barre": 1},

    # Minor Chords
    "Am": {"frets": [-1, 0, 2, 2, 1, 0], "fingers": [0, 0, 2, 3, 1, 0], "base_fret": 1},
    "Bm": {"frets": [-1, 2, 4, 4, 3, 2], "fingers": [0, 1, 3, 4, 2, 1], "base_fret": 2, "barre": 2},
    "Cm": {"frets": [-1, 3, 5, 5, 4, 3], "fingers": [0, 1, 3, 4, 2, 1], "base_fret": 3, "barre": 3},
    "Dm": {"frets": [-1, -1, 0, 2, 3, 1], "fingers": [0, 0, 0, 2, 3, 1], "base_fret": 1},
    "Em": {"frets": [0, 2, 2, 0, 0, 0], "fingers": [0, 2, 3, 0, 0, 0], "base_fret": 1},
    "Fm": {"frets": [1, 3, 3, 1, 1, 1], "fingers": [1, 3, 4, 1, 1, 1], "base_fret": 1, "barre": 1},
    "Gm": {"frets": [3, 5, 5, 3, 3, 3], "fingers": [1, 3, 4, 1, 1, 1], "base_fret": 3, "barre": 3},
    "C#m": {"frets": [-1, 4, 6, 6, 5, 4], "fingers": [0, 1, 3, 4, 2, 1], "base_fret": 4, "barre": 4},
    "Ebm": {"frets": [-1, 6, 8, 8, 7, 6], "fingers": [0, 1, 3, 4, 2, 1], "base_fret": 6, "barre": 6},
    "F#m": {"frets": [2, 4, 4, 2, 2, 2], "fingers": [1, 3, 4, 1, 1, 1], "base_fret": 2, "barre": 2},
    "G#m": {"frets": [4, 6, 6, 4, 4, 4], "fingers": [1, 3, 4, 1, 1, 1], "base_fret": 4, "barre": 4},
    "Bbm": {"frets": [-1, 1, 3, 3, 2, 1], "fingers": [0, 1, 3, 4, 2, 1], "base_fret": 1, "barre": 1},

    # Dominant 7th Chords
    "C7": {"frets": [-1, 3, 2, 3, 1, 0], "fingers": [0, 3, 2, 4, 1, 0], "base_fret": 1},
    "D7": {"frets": [-1, -1, 0, 2, 1, 2], "fingers": [0, 0, 0, 2, 1, 3], "base_fret": 1},
    "E7": {"frets": [0, 2, 0, 1, 0, 0], "fingers": [0, 2, 0, 1, 0, 0], "base_fret": 1},
    "F7": {"frets": [1, 3, 1, 2, 1, 1], "fingers": [1, 3, 1, 2, 1, 1], "base_fret": 1, "barre": 1},
    "G7": {"frets": [3, 2, 0, 0, 0, 1], "fingers": [3, 2, 0, 0, 0, 1], "base_fret": 1},
    "A7": {"frets": [-1, 0, 2, 0, 2, 0], "fingers": [0, 0, 2, 0, 3, 0], "base_fret": 1},
    "B7": {"frets": [-1, 2, 1, 2, 0, 2], "fingers": [0, 2, 1, 3, 0, 4], "base_fret": 1},

    # Major 7th Chords
    "Cmaj7": {"frets": [-1, 3, 2, 0, 0, 0], "fingers": [0, 3, 2, 0, 0, 0], "base_fret": 1},
    "Dmaj7": {"frets": [-1, -1, 0, 2, 2, 2], "fingers": [0, 0, 0, 1, 1, 1], "base_fret": 1},
    "Fmaj7": {"frets": [-1, -1, 3, 2, 1, 0], "fingers": [0, 0, 3, 2, 1, 0], "base_fret": 1},
    "Gmaj7": {"frets": [3, 2, 0, 0, 0, 2], "fingers": [2, 1, 0, 0, 0, 3], "base_fret": 1},
    "Amaj7": {"frets": [-1, 0, 2, 1, 2, 0], "fingers": [0, 0, 2, 1, 3, 0], "base_fret": 1},

    # Minor 7th Chords
    "Am7": {"frets": [-1, 0, 2, 0, 1, 0], "fingers": [0, 0, 2, 0, 1, 0], "base_fret": 1},
    "Dm7": {"frets": [-1, -1, 0, 2, 1, 1], "fingers": [0, 0, 0, 2, 1, 1], "base_fret": 1},
    "Em7": {"frets": [0, 2, 0, 0, 0, 0], "fingers": [0, 2, 0, 0, 0, 0], "base_fret": 1},
    "Bm7": {"frets": [-1, 2, 0, 2, 0, 2], "fingers": [0, 1, 0, 2, 0, 3], "base_fret": 1},

    # Sus4 and Sus2 Chords
    "Dsus4": {"frets": [-1, -1, 0, 2, 3, 3], "fingers": [0, 0, 0, 1, 2, 3], "base_fret": 1},
    "Asus4": {"frets": [-1, 0, 2, 2, 3, 0], "fingers": [0, 0, 1, 2, 3, 0], "base_fret": 1},
    "Esus4": {"frets": [0, 2, 2, 2, 0, 0], "fingers": [0, 2, 3, 4, 0, 0], "base_fret": 1},
    "Gsus4": {"frets": [3, 3, 0, 0, 1, 3], "fingers": [2, 3, 0, 0, 1, 4], "base_fret": 1},
    "Dsus2": {"frets": [-1, -1, 0, 2, 3, 0], "fingers": [0, 0, 0, 1, 3, 0], "base_fret": 1},
    "Asus2": {"frets": [-1, 0, 2, 2, 0, 0], "fingers": [0, 0, 2, 3, 0, 0], "base_fret": 1},
}

# Diatonic progressions for common keys
DIATONIC_PROGRESSIONS: Dict[str, Dict[str, Any]] = {
    "C Major": {
        "chords": ["C", "Dm", "Em", "F", "G", "Am", "Bdim"],
        "progression": ["C", "G", "Am", "F"],
    },
    "A Minor": {
        "chords": ["Am", "Bdim", "C", "Dm", "Em", "F", "G"],
        "progression": ["Am", "F", "C", "G"],
    },
    "G Major": {
        "chords": ["G", "Am", "Bm", "C", "D", "Em", "F#dim"],
        "progression": ["G", "D", "Em", "C"],
    },
    "E Minor": {
        "chords": ["Em", "F#dim", "G", "Am", "Bm", "C", "D"],
        "progression": ["Em", "C", "G", "D"],
    },
    "D Major": {
        "chords": ["D", "Em", "F#m", "G", "A", "Bm", "C#dim"],
        "progression": ["D", "A", "Bm", "G"],
    },
    "B Minor": {
        "chords": ["Bm", "C#dim", "D", "Em", "F#m", "G", "A"],
        "progression": ["Bm", "G", "D", "A"],
    },
    "F Major": {
        "chords": ["F", "Gm", "Am", "Bb", "C", "Dm", "Edim"],
        "progression": ["F", "C", "Dm", "Bb"],
    },
    "D Minor": {
        "chords": ["Dm", "Edim", "F", "Gm", "Am", "Bb", "C"],
        "progression": ["Dm", "Bb", "F", "C"],
    },
    "E Major": {
        "chords": ["E", "F#m", "G#m", "A", "B", "C#m", "D#dim"],
        "progression": ["E", "B", "C#m", "A"],
    },
    "A Major": {
        "chords": ["A", "Bm", "C#m", "D", "E", "F#m", "G#dim"],
        "progression": ["A", "E", "F#m", "D"],
    },
}


def render_ascii_chord_diagram(chord_name: str) -> str:
    """Generates an ASCII text diagram of the guitar fretboard for a chord."""
    info = GUITAR_CHORDS_DB.get(chord_name)
    if not info:
        return f"[{chord_name}] (Fretboard diagram unavailable)"

    frets = info["frets"]
    base = info.get("base_fret", 1)

    # Top string indicator
    header = "  "
    for f in frets:
        if f == -1:
            header += "x "
        elif f == 0:
            header += "o "
        else:
            header += "  "

    lines = [f" {chord_name}", header, " +-----------+"]
    for fret_row in range(base, base + 4):
        row_str = f"{fret_row}|"
        for f in frets:
            if f == fret_row:
                row_str += "O|"
            else:
                row_str += " |"
        lines.append(row_str)
        lines.append(" +-----------+")

    return "\n".join(lines)


def parse_chordpro_string(text: str) -> List[Dict[str, Any]]:
    """
    Parses ChordPro bracketed notation into chord events and lyric words.
    Example: "[Am]Hello [C]darkness [G]my old friend"
    """
    pattern = re.compile(r"\[([A-G][b#]?(?:m|maj|min|dim|aug|sus)?\d*)\]")
    events = []
    last_idx = 0

    for match in pattern.finditer(text):
        chord = match.group(1)
        start = match.start()
        # Word text preceding or following
        events.append({
            "chord": chord,
            "char_offset": start,
            "diagram": GUITAR_CHORDS_DB.get(chord, {})
        })

    clean_text = pattern.sub("", text).strip()
    return [{"clean_text": clean_text, "chords": events}]


def merge_chords_with_lrc_lines(lrc_lines: List[Dict[str, Any]], key_name: str = "A Minor") -> List[Dict[str, Any]]:
    """
    Synchronizes harmonic chord progressions with karaoke LRC timestamp lines.
    Each lyric line is enriched with the active chord and guitar fret data.
    """
    profile = DIATONIC_PROGRESSIONS.get(key_name, DIATONIC_PROGRESSIONS.get("A Minor", {}))
    prog = profile.get("progression", ["Am", "F", "C", "G"])

    enriched_lines = []
    prog_len = len(prog)

    for i, line in enumerate(lrc_lines):
        chord_name = prog[i % prog_len]
        chord_info = GUITAR_CHORDS_DB.get(chord_name, {})

        enriched_lines.append({
            "time": line.get("time", 0.0),
            "text": line.get("text", ""),
            "chord": chord_name,
            "chord_diagram": chord_info,
            "ascii_fretboard": render_ascii_chord_diagram(chord_name),
        })

    return enriched_lines


def get_chord_details(chord_name: str) -> Dict[str, Any]:
    """Retrieves full voicing and fretboard details for a specific chord."""
    info = GUITAR_CHORDS_DB.get(chord_name)
    if not info:
        # Fallback to simple root chord if exact match not found
        root = chord_name[0].upper()
        info = GUITAR_CHORDS_DB.get(root, {"frets": [0, 0, 0, 0, 0, 0], "fingers": [0, 0, 0, 0, 0, 0], "base_fret": 1})

    return {
        "chord": chord_name,
        "frets": info.get("frets", []),
        "fingers": info.get("fingers", []),
        "base_fret": info.get("base_fret", 1),
        "barre": info.get("barre"),
        "ascii_art": render_ascii_chord_diagram(chord_name),
    }


def get_song_chord_studio_data(artist: str, title: str, key_name: Optional[str] = "A Minor") -> Dict[str, Any]:
    """
    Returns complete chord studio package: harmonic key, progression,
    and interactive diagrams for the Karaoke Stage.
    """
    if not key_name or key_name not in DIATONIC_PROGRESSIONS:
        key_name = "A Minor"

    profile = DIATONIC_PROGRESSIONS.get(key_name, {})
    progression = profile.get("progression", ["Am", "F", "C", "G"])
    scale_chords = profile.get("chords", [])

    diagrams = {c: get_chord_details(c) for c in progression}

    return {
        "success": True,
        "artist": artist,
        "title": title,
        "key": key_name,
        "progression": progression,
        "diatonic_scale_chords": scale_chords,
        "chord_diagrams": diagrams,
    }


if __name__ == "__main__":
    import sys
    print("Sonance Synchronized Guitar Chord Studio")
    test_chord = "Am"
    if len(sys.argv) > 1:
        test_chord = sys.argv[1]
    print(render_ascii_chord_diagram(test_chord))
