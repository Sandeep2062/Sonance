"""
lyrics_translator.py - Dual-Language Synchronized Lyrics Translator
Part of Sonance - The Ultimate Open-Source Music Workstation
Translates synchronized lyrics lines into 50+ languages while preserving exact
millisecond timestamps, generating bilingual karaoke LRC files ([mm:ss.xx] original \n [mm:ss.xx] translated).

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import os
import sys
import re
import json
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

# Supported ISO language code mapping
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "it": "Italian (Italiano)",
    "pt": "Portuguese (Português)",
    "ru": "Russian (Русский)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "zh-CN": "Chinese Simplified (简体中文)",
    "zh-TW": "Chinese Traditional (繁體中文)",
    "hi": "Hindi (हिन्दी)",
    "ar": "Arabic (العربية)",
    "id": "Indonesian (Bahasa Indonesia)",
    "tr": "Turkish (Türkçe)",
    "vi": "Vietnamese (Tiếng Việt)",
    "th": "Thai (ไทย)",
    "nl": "Dutch (Nederlands)",
    "pl": "Polish (Polski)",
    "sv": "Swedish (Svenska)",
    "el": "Greek (Ελληνικά)",
    "ne": "Nepali (नेपाली)",
}


def _translate_text_batch(texts: List[str], target_lang: str, source_lang: str = "auto") -> List[str]:
    """
    Translates a batch of lyric text lines in chunks using free Google Translate endpoint.
    Batches lines joined by newlines to minimize HTTP roundtrips.
    """
    if not texts:
        return []

    # Clean lines and join with separator
    delimiter = "\n\n"
    combined_query = delimiter.join(texts)

    url = (
        f"https://translate.googleapis.com/translate_a/single?"
        f"client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q="
        + urllib.parse.quote(combined_query)
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # In Google Translate single endpoint, translated sentences are in data[0]
        # each element is [translated_chunk, original_chunk, ...]
        full_translated = "".join(part[0] for part in data[0] if part and part[0])

        translated_lines = full_translated.split(delimiter)

        # Pad or trim to match input length exactly
        if len(translated_lines) < len(texts):
            translated_lines.extend([""] * (len(texts) - len(translated_lines)))
        elif len(translated_lines) > len(texts):
            translated_lines = translated_lines[: len(texts)]

        return [l.strip() for l in translated_lines]
    except Exception:
        # Fallback to individual line translation or return originals if network fails
        translated = []
        for t in texts:
            if not t.strip():
                translated.append("")
                continue
            try:
                line_url = (
                    f"https://translate.googleapis.com/translate_a/single?"
                    f"client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q="
                    + urllib.parse.quote(t)
                )
                l_req = urllib.request.Request(line_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(l_req, timeout=5) as l_resp:
                    l_data = json.loads(l_resp.read().decode("utf-8"))
                    res_t = "".join(part[0] for part in l_data[0] if part and part[0])
                    translated.append(res_t.strip())
            except Exception:
                translated.append(t)
        return translated


def translate_lyrics(
    lrc_content: str,
    target_lang: str = "es",
    dual_format: bool = True,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Translates synced LRC lyrics preserving timestamps.
    Produces either bilingual dual-line format or translated-only lyrics.
    """
    if not lrc_content or not lrc_content.strip():
        return {"success": False, "error": "Empty lyrics content."}

    lines = lrc_content.splitlines()
    timestamp_regex = re.compile(r"^(\[\d{2}:\d{2}(?:\.\d{2,3})?\])(.*)$")

    parsed_entries: List[Tuple[str, str, str]] = []  # (tag_type, timestamp, text)
    texts_to_translate: List[str] = []

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            parsed_entries.append(("empty", "", ""))
            continue

        match = timestamp_regex.match(line_clean)
        if match:
            ts = match.group(1)
            txt = match.group(2).strip()
            parsed_entries.append(("lyric", ts, txt))
            if txt:
                texts_to_translate.append(txt)
            else:
                texts_to_translate.append("")
        elif line_clean.startswith("[") and "]" in line_clean:
            # Metadata tag (e.g. [ar: Queen], [ti: ...])
            parsed_entries.append(("meta", "", line_clean))
        else:
            # Plain un-timed line
            parsed_entries.append(("plain", "", line_clean))
            texts_to_translate.append(line_clean)

    # Perform batch translation
    translated_texts = _translate_text_batch(texts_to_translate, target_lang=target_lang)

    output_lines: List[str] = []
    t_idx = 0

    # Add metadata header noting translation
    lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
    output_lines.append(f"[re:Sonance Dual-Language Subtitle Studio]")
    output_lines.append(f"[translation:{lang_name}]")

    for entry_type, ts, orig_txt in parsed_entries:
        if entry_type == "empty":
            output_lines.append("")
        elif entry_type == "meta":
            output_lines.append(orig_txt)
        elif entry_type == "lyric":
            trans_txt = translated_texts[t_idx] if t_idx < len(translated_texts) else ""
            t_idx += 1

            if dual_format:
                # Bilingual output
                if orig_txt:
                    output_lines.append(f"{ts} {orig_txt}")
                if trans_txt:
                    output_lines.append(f"{ts} ({trans_txt})")
            else:
                # Translated-only output
                output_lines.append(f"{ts} {trans_txt if trans_txt else orig_txt}")
        elif entry_type == "plain":
            trans_txt = translated_texts[t_idx] if t_idx < len(translated_texts) else ""
            t_idx += 1

            if dual_format:
                output_lines.append(orig_txt)
                if trans_txt:
                    output_lines.append(f"({trans_txt})")
            else:
                output_lines.append(trans_txt if trans_txt else orig_txt)

    translated_lrc = "\n".join(output_lines)

    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(translated_lrc)
        except Exception as e:
            return {"success": False, "error": f"Failed to save translated LRC: {e}"}

    return {
        "success": True,
        "target_language": target_lang,
        "language_name": lang_name,
        "dual_format": dual_format,
        "total_lines_translated": len(texts_to_translate),
        "translated_lyrics": translated_lrc,
        "output_file": output_path,
    }


def get_supported_languages() -> Dict[str, str]:
    """Returns supported target languages for lyrics translation."""
    return SUPPORTED_LANGUAGES


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python lyrics_translator.py <lrc_file_or_text> <target_lang> [output_lrc] [--translated-only]")
        print("Supported languages:")
        for code, name in SUPPORTED_LANGUAGES.items():
            print(f"  {code:<6} {name}")
        sys.exit(1)

    inp = sys.argv[1]
    tgt = sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None
    dual = "--translated-only" not in sys.argv

    content = inp
    if os.path.isfile(inp):
        with open(inp, "r", encoding="utf-8") as f:
            content = f.read()

    res = translate_lyrics(content, target_lang=tgt, dual_format=dual, output_path=out)
    if res.get("success"):
        print(f"[+] Lyrics Translated to {res['language_name']} ({res['total_lines_translated']} lines):")
        print("--- Preview ---")
        for l in res["translated_lyrics"].splitlines()[:8]:
            print(f"  {l}")
        if res.get("output_file"):
            print(f"[+] Saved to: {res['output_file']}")
    else:
        print(f"[-] Translation Failed: {res.get('error')}")
