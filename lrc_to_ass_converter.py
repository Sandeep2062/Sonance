"""
lrc_to_ass_converter.py - Word-by-Word LRC to Karaoke Subtitle Styler & ASS Converter
Part of Sonance (Unified Music Workstation)
Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause

Converts plain and syllable-timed synchronized LRC/ELRC files into:
- Broadcast-quality Advanced SubStation Alpha (.ass) with progressive karaoke tags (\\k<dur>)
- SubRip (.srt) subtitle files
- Rich customizable typography, glow outlines, drop shadows, and color wipes
- Automatic syllable timing synthesis for standard non-enhanced LRC lines
"""

import os
import sys
import re
import argparse
from typing import Dict, List, Optional, Tuple, Any


TIME_TAG_REGEX = re.compile(r'\[(\d{1,2}):(\d{2})(?:\.(\d{2,3}))?\]')
SYLLABLE_TAG_REGEX = re.compile(r'<(\d{1,2}):(\d{2})(?:\.(\d{2,3}))?>')
METADATA_REGEX = re.compile(r'\[(ti|ar|al|by|offset|length):([^\]]*)\]', re.IGNORECASE)


def parse_timestamp_to_seconds(m_str: str, s_str: str, ms_str: Optional[str]) -> float:
    """Converts minutes, seconds, and fraction into total seconds."""
    m = int(m_str)
    s = int(s_str)
    if ms_str:
        if len(ms_str) == 2:
            frac = int(ms_str) / 100.0
        else:
            frac = int(ms_str[:3]) / 1000.0
    else:
        frac = 0.0
    return m * 60.0 + s + frac


def format_ass_time(sec: float) -> str:
    """Formats seconds into ASS timestamp format: h:mm:ss.cc (centiseconds)."""
    if sec < 0:
        sec = 0.0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cc = int(round((sec - int(sec)) * 100))
    if cc >= 100:
        cc = 0
        s += 1
        if s >= 60:
            s = 0
            m += 1
            if m >= 60:
                m = 0
                h += 1
    return f"{h}:{m:02d}:{s:02d}.{cc:02d}"


def format_srt_time(sec: float) -> str:
    """Formats seconds into SRT timestamp format: hh:mm:ss,mmm (milliseconds)."""
    if sec < 0:
        sec = 0.0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        ms = 0
        s += 1
        if s >= 60:
            s = 0
            m += 1
            if m >= 60:
                m = 0
                h += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def hex_to_ass_color(hex_str: str, alpha_hex: str = "00") -> str:
    """Converts #RRGGBB hex color to ASS &HAABBGGRR& format."""
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join([c * 2 for c in clean])
    if len(clean) != 6:
        clean = "00D7FF"  # Default gold/amber

    r = clean[0:2]
    g = clean[2:4]
    b = clean[4:6]
    return f"&H{alpha_hex.upper()}{b.upper()}{g.upper()}{r.upper()}&"


class LyricSyllable:
    def __init__(self, text: str, duration_cs: int):
        self.text = text
        self.duration_cs = max(1, duration_cs)


class LyricLine:
    def __init__(self, start_sec: float, end_sec: float, raw_text: str):
        self.start_sec = start_sec
        self.end_sec = end_sec
        self.raw_text = raw_text.strip()
        self.syllables: List[LyricSyllable] = []
        self.is_enhanced = False


def parse_lrc(content: str) -> Tuple[List[LyricLine], Dict[str, str]]:
    """Parses LRC or Enhanced LRC text into lines and metadata."""
    metadata = {}
    lines_raw = content.splitlines()
    raw_parsed_lines = []

    for line_idx, line in enumerate(lines_raw):
        line_clean = line.strip()
        if not line_clean:
            continue

        # Check for metadata tags: [ti: Title]
        meta_match = METADATA_REGEX.match(line_clean)
        if meta_match:
            metadata[meta_match.group(1).lower()] = meta_match.group(2).strip()
            continue

        # Check for timestamp tag: [mm:ss.xx]
        time_matches = list(TIME_TAG_REGEX.finditer(line_clean))
        if not time_matches:
            continue

        # Extract text after last header time tag
        last_match = time_matches[-1]
        text_content = line_clean[last_match.end():].strip()

        for m in time_matches:
            start_sec = parse_timestamp_to_seconds(m.group(1), m.group(2), m.group(3))
            raw_parsed_lines.append((start_sec, text_content))

    # Sort lines chronologically
    raw_parsed_lines.sort(key=lambda x: x[0])

    # Convert to LyricLine objects with calculated end times
    lyric_lines: List[LyricLine] = []
    for i in range(len(raw_parsed_lines)):
        start_sec, text_content = raw_parsed_lines[i]
        if i + 1 < len(raw_parsed_lines):
            next_start = raw_parsed_lines[i + 1][0]
            # Cap line duration to 8.0 seconds or until next line starts
            end_sec = min(start_sec + 8.0, next_start)
            if end_sec <= start_sec:
                end_sec = start_sec + 2.5
        else:
            end_sec = start_sec + 3.5

        ll = LyricLine(start_sec, end_sec, text_content)

        # Check if line contains enhanced syllable tags <mm:ss.xx>
        syl_matches = list(SYLLABLE_TAG_REGEX.finditer(text_content))
        if syl_matches:
            ll.is_enhanced = True
            prev_time = start_sec
            for s_idx, sm in enumerate(syl_matches):
                sm_time = parse_timestamp_to_seconds(sm.group(1), sm.group(2), sm.group(3))
                # Text following this syllable tag up to next tag
                start_txt = sm.end()
                end_txt = syl_matches[s_idx + 1].start() if (s_idx + 1 < len(syl_matches)) else len(text_content)
                syl_word = text_content[start_txt:end_txt]
                
                # If next syllable exists, use its time for duration; else use end_sec
                if s_idx + 1 < len(syl_matches):
                    next_syl_time = parse_timestamp_to_seconds(
                        syl_matches[s_idx + 1].group(1),
                        syl_matches[s_idx + 1].group(2),
                        syl_matches[s_idx + 1].group(3)
                    )
                    dur_cs = int(round(max(0.05, next_syl_time - sm_time) * 100))
                else:
                    dur_cs = int(round(max(0.1, end_sec - sm_time) * 100))

                ll.syllables.append(LyricSyllable(syl_word, dur_cs))
        else:
            # Generate estimated syllable timing from plain words
            words = text_content.split()
            if words:
                line_dur_cs = int(round((end_sec - start_sec) * 100))
                # Weight by word length
                total_chars = sum(len(w) for w in words)
                if total_chars == 0:
                    total_chars = len(words)
                
                for w in words:
                    weight = len(w) / total_chars
                    dur_cs = max(10, int(round(line_dur_cs * weight)))
                    ll.syllables.append(LyricSyllable(w + " ", dur_cs))

        lyric_lines.append(ll)

    return lyric_lines, metadata


def generate_ass_script(
    lines: List[LyricLine],
    metadata: Dict[str, str],
    style_preset: str = "karaoke",
    primary_color_hex: str = "#FFD700",
    secondary_color_hex: str = "#FFFFFF",
    font_name: str = "Trebuchet MS",
    font_size: int = 50,
    res_x: int = 1920,
    res_y: int = 1080
) -> str:
    """Generates complete ASS subtitle script content with style configurations."""
    title = metadata.get("ti", "Sonance Karaoke Subtitles")
    artist = metadata.get("ar", "Unknown Artist")

    ass_primary = hex_to_ass_color(primary_color_hex)
    ass_secondary = hex_to_ass_color(secondary_color_hex)
    ass_outline = "&H00000000&"
    ass_back = "&H80000000&"

    # Style definitions based on preset
    style_preset_key = style_preset.lower().strip()
    if style_preset_key == "minimal":
        font_size = 42
        outline_size = 1.5
        shadow_size = 0.5
        bold = 0
        alignment = 2  # Bottom-center
        margin_v = 45
    elif style_preset_key == "cinematic":
        font_name = "Georgia"
        font_size = 46
        outline_size = 2.0
        shadow_size = 2.0
        bold = 0
        alignment = 2
        margin_v = 70
    else:  # karaoke (default vibrant)
        outline_size = 2.8
        shadow_size = 2.0
        bold = -1
        alignment = 2
        margin_v = 60

    out = []
    # Header
    out.append("[Script Info]")
    out.append(f"; Script generated by Sonance Word-by-Word LRC to ASS Converter")
    out.append(f"Title: {title} - {artist}")
    out.append("ScriptType: v4.00+")
    out.append("WrapStyle: 0")
    out.append("ScaledBorderAndShadow: yes")
    out.append(f"PlayResX: {res_x}")
    out.append(f"PlayResY: {res_y}")
    out.append("")

    # Styles
    out.append("[V4+ Styles]")
    out.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
    style_line = (
        f"Style: Default,{font_name},{font_size},"
        f"{ass_primary},{ass_secondary},{ass_outline},{ass_back},"
        f"{bold},0,0,0,100,100,0,0,1,{outline_size},{shadow_size},{alignment},40,40,{margin_v},1"
    )
    out.append(style_line)
    out.append("")

    # Events
    out.append("[Events]")
    out.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for line in lines:
        start_str = format_ass_time(line.start_sec)
        end_str = format_ass_time(line.end_sec)

        # Build karaoke styled text: {\k<duration_cs>}Word
        k_text_parts = []
        for syl in line.syllables:
            # Clean any internal braces or tags
            clean_word = syl.text.replace("{", "").replace("}", "")
            k_text_parts.append(f"{{\\k{syl.duration_cs}}}{clean_word}")

        full_k_text = "".join(k_text_parts) if k_text_parts else line.raw_text
        event_line = f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{full_k_text}"
        out.append(event_line)

    return "\n".join(out)


def generate_srt_script(lines: List[LyricLine]) -> str:
    """Generates standard SubRip (.srt) subtitle script content."""
    out = []
    for idx, line in enumerate(lines, 1):
        start_str = format_srt_time(line.start_sec)
        end_str = format_srt_time(line.end_sec)
        # Strip all karaoke / syllable tags for clean SRT presentation
        clean_text = re.sub(r'<[^>]+>', '', line.raw_text).strip()
        clean_text = re.sub(r'\[[^\]]+\]', '', clean_text).strip()
        if not clean_text and line.syllables:
            clean_text = "".join(s.text for s in line.syllables).strip()

        out.append(str(idx))
        out.append(f"{start_str} --> {end_str}")
        out.append(clean_text)
        out.append("")

    return "\n".join(out)


def convert_lrc_to_subtitles(
    lrc_path: str,
    output_path: Optional[str] = None,
    style_preset: str = "karaoke",
    primary_color_hex: str = "#FFD700",
    secondary_color_hex: str = "#FFFFFF",
    font_name: str = "Trebuchet MS",
    export_srt: bool = False
) -> Dict[str, Any]:
    """
    Converts LRC or ELRC file to styled ASS (and optional SRT) subtitles.
    
    Args:
        lrc_path: Path to source .lrc file.
        output_path: Path to target output .ass file (auto-named if None).
        style_preset: One of 'karaoke', 'minimal', 'cinematic'.
        primary_color_hex: Highlight fill color (e.g. #FFD700).
        secondary_color_hex: Unsung base color (e.g. #FFFFFF).
        font_name: Font family name.
        export_srt: If True, also writes an accompanying .srt file.
        
    Returns:
        Dict with conversion statistics and output file paths.
    """
    if not os.path.exists(lrc_path):
        return {
            "success": False,
            "error": f"LRC file not found: {lrc_path}"
        }

    try:
        # Read LRC with robust encoding detection
        encodings = ["utf-8-sig", "utf-8", "cp1252", "shift_jis", "latin-1"]
        content = None
        for enc in encodings:
            try:
                with open(lrc_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            with open(lrc_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

        lines, metadata = parse_lrc(content)
        if not lines:
            return {
                "success": False,
                "error": "No valid timestamped lyrics lines found in LRC file"
            }

        enhanced_count = sum(1 for line in lines if line.is_enhanced)
        total_lines = len(lines)
        total_duration = lines[-1].end_sec if lines else 0.0

        # Determine output ASS path
        if not output_path:
            base, _ = os.path.splitext(lrc_path)
            output_path = base + ".ass"

        ass_content = generate_ass_script(
            lines=lines,
            metadata=metadata,
            style_preset=style_preset,
            primary_color_hex=primary_color_hex,
            secondary_color_hex=secondary_color_hex,
            font_name=font_name
        )

        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(ass_content)

        srt_path = None
        if export_srt:
            base, _ = os.path.splitext(output_path)
            srt_path = base + ".srt"
            srt_content = generate_srt_script(lines)
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

        return {
            "success": True,
            "output_ass_path": output_path,
            "output_srt_path": srt_path,
            "title": metadata.get("ti", os.path.basename(lrc_path)),
            "artist": metadata.get("ar", "Unknown Artist"),
            "total_lines": total_lines,
            "enhanced_lines": enhanced_count,
            "duration_sec": round(total_duration, 2),
            "style_preset": style_preset,
            "primary_color": primary_color_hex,
            "font_name": font_name
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def format_ass_card(res: Dict[str, Any]) -> str:
    """Renders formatted ASCII card summarizing the subtitle styling result."""
    if not res.get("success"):
        return f"[!] Error converting subtitles: {res.get('error', 'Unknown error')}"

    lines = []
    sep = "+" + "-" * 66 + "+"
    lines.append(sep)
    lines.append("| WORD-BY-WORD LRC TO KARAOKE ASS SUBTITLE CONVERTER              |")
    lines.append(sep)
    lines.append(f"| Track Title    : {res['title'][:48]:<48} |")
    lines.append(f"| Artist         : {res['artist'][:48]:<48} |")
    lines.append(f"| Subtitle Style : {res['style_preset'].capitalize():<20} | Font: {res['font_name']:<21} |")
    lines.append(f"| Highlight Color: {res['primary_color']:<20} | Mode: 1080p Broadcast ASS    |")
    lines.append(sep)
    lines.append(f"| Total Lines    : {res['total_lines']:<5} lines (Duration: {res['duration_sec']}s)               |")
    enhanced_label = f"{res['enhanced_lines']} lines (True Word Timing)" if res['enhanced_lines'] > 0 else "Synthesized Syllables"
    lines.append(f"| Syllable Sync  : {enhanced_label:<48} |")
    lines.append(sep)
    lines.append(f"| Output .ASS    : {res['output_ass_path'][:48]:<48} |")
    if res.get("output_srt_path"):
        lines.append(f"| Output .SRT    : {res['output_srt_path'][:48]:<48} |")
    lines.append(sep)

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sonance Word-by-Word LRC to ASS Karaoke Subtitle Converter")
    parser.add_argument("lrc_file", help="Path to input .lrc or .elrc file")
    parser.add_argument("output_ass", nargs="?", default=None, help="Target output .ass path")
    parser.add_argument("--style", choices=["karaoke", "minimal", "cinematic"], default="karaoke", help="Subtitle style preset")
    parser.add_argument("--color", default="#FFD700", help="Primary highlight hex color (e.g. #FFD700)")
    parser.add_argument("--font", default="Trebuchet MS", help="Font family name")
    parser.add_argument("--srt", action="store_true", help="Also export clean .srt subtitle file")

    args = parser.parse_args()

    result = convert_lrc_to_subtitles(
        lrc_path=args.lrc_file,
        output_path=args.output_ass,
        style_preset=args.style,
        primary_color_hex=args.color,
        font_name=args.font,
        export_srt=args.srt
    )
    print(format_ass_card(result))
