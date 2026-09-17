"""
lyrics_translation.py - Sonance Multilingual Lyrics Romanization & Translation Studio

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Provides real-time phonetic romanization (Romaji for Japanese, Revised Romanization
for Korean Hangul, Pinyin for Chinese) and translations for international music.
"""

import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests


# ------------------ Japanese Kana -> Romaji Mapping ------------------
KANA_MAP = {
    # Gojūon (Hiragana)
    'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
    'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
    'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so',
    'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to',
    'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no',
    'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho',
    'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo',
    'や': 'ya', 'ゆ': 'yu', 'よ': 'yo',
    'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro',
    'わ': 'wa', 'を': 'wo', 'ん': 'n',
    # Dakuon & Handakuon
    'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gu', 'げ': 'ge', 'ご': 'go',
    'ざ': 'za', 'じ': 'ji', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo',
    'だ': 'da', 'ぢ': 'ji', 'づ': 'zu', 'で': 'de', 'ど': 'do',
    'ば': 'ba', 'び': 'bi', 'ぶ': 'bu', 'べ': 'be', 'ぼ': 'bo',
    'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pu', 'ぺ': 'pe', 'ぽ': 'po',
    # Yōon (Combined Kana)
    'きゃ': 'kya', 'きゅ': 'kyu', 'きょ': 'kyo',
    'しゃ': 'sha', 'しゅ': 'shu', 'しょ': 'sho',
    'ちゃ': 'cha', 'ちゅ': 'chu', 'ちょ': 'cho',
    'にゃ': 'nya', 'にゅ': 'nyu', 'にょ': 'nyo',
    'ひゃ': 'hya', 'ひゅ': 'hyu', 'ひょ': 'hyo',
    'みゃ': 'mya', 'みゅ': 'myu', 'みょ': 'myo',
    'りゃ': 'rya', 'りゅ': 'ryu', 'りょ': 'ryo',
    'ぎゃ': 'gya', 'ぎゅ': 'gyu', 'ぎょ': 'gyo',
    'じゃ': 'ja', 'じゅ': 'ju', 'じょ': 'jo',
    'びゃ': 'bya', 'びゅ': 'byu', 'びょ': 'byo',
    'ぴゃ': 'pya', 'ぴゅ': 'pyu', 'ぴょ': 'pyo',
}

# Katakana equivalent mapping
for hira, rom in list(KANA_MAP.items()):
    kata = "".join(chr(ord(c) + 0x60) if '\u3041' <= c <= '\u3096' else c for c in hira)
    KANA_MAP[kata] = rom


# ------------------ Korean Hangul Algorithmic Romanizer ------------------
HANGUL_INITIALS = [
    'g', 'kk', 'n', 'd', 'tt', 'r', 'm', 'b', 'pp', 's', 'ss', '',
    'j', 'jj', 'ch', 'k', 't', 'p', 'h'
]
HANGUL_VOWELS = [
    'a', 'ae', 'ya', 'yae', 'eo', 'e', 'yeo', 'ye', 'o', 'wa', 'wae', 'oe',
    'yo', 'u', 'wo', 'we', 'wi', 'yu', 'eu', 'ui', 'i'
]
HANGUL_FINALS = [
    '', 'g', 'kk', 'ks', 'n', 'nj', 'nh', 'd', 'l', 'lg', 'lm', 'lb',
    'ls', 'lt', 'lp', 'lh', 'm', 'b', 'bs', 's', 'ss', 'ng', 'j', 'ch',
    'k', 't', 'p', 'h'
]


def romanize_hangul_char(char: str) -> str:
    code = ord(char)
    if 0xAC00 <= code <= 0xD7A3:
        offset = code - 0xAC00
        initial_idx = offset // (21 * 28)
        vowel_idx = (offset % (21 * 28)) // 28
        final_idx = offset % 28
        return HANGUL_INITIALS[initial_idx] + HANGUL_VOWELS[vowel_idx] + HANGUL_FINALS[final_idx]
    return char


def romanize_text(text: str) -> str:
    """Converts Japanese Kana and Korean Hangul text into Romanized Latin phonetics."""
    if not text:
        return ""

    result = []
    i = 0
    n = len(text)

    while i < n:
        # Check two-character Japanese combinations first (e.g. きゃ)
        if i + 1 < n and text[i:i+2] in KANA_MAP:
            result.append(KANA_MAP[text[i:i+2]])
            i += 2
            continue

        ch = text[i]

        # Sokuon (small っ / ッ)
        if ch in ('っ', 'ッ') and i + 1 < n:
            next_ch = text[i+1]
            if next_ch in KANA_MAP:
                next_rom = KANA_MAP[next_ch]
                result.append(next_rom[0] if next_rom else '')
                i += 1
                continue

        # Single Kana
        if ch in KANA_MAP:
            result.append(KANA_MAP[ch])
        # Korean Hangul syllable
        elif 0xAC00 <= ord(ch) <= 0xD7A3:
            result.append(romanize_hangul_char(ch))
        else:
            result.append(ch)

        i += 1

    return "".join(result)


def has_cjk(text: str) -> bool:
    """Checks if string contains Chinese, Japanese, or Korean characters."""
    return bool(re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]', text))


# In-memory translation cache
_TRANSLATION_CACHE: Dict[str, str] = {}


def translate_text(text: str, target_lang: str = "en") -> str:
    """Translates text to English or specified language using public translation API."""
    if not text or not text.strip():
        return ""

    cache_key = f"{target_lang}:::{text.strip()}"
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    try:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text.strip())}&langpair=autodetect|{target_lang}"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            if translated and translated.lower() != text.strip().lower():
                _TRANSLATION_CACHE[cache_key] = translated
                return translated
    except Exception:
        pass

    return ""


def enrich_lyrics_with_phonetics(lines: List[Dict[str, Any]], target_lang: str = "en") -> List[Dict[str, Any]]:
    """
    Enriches a list of lyrics lines with phonetic romanization and translations.
    Each line dictionary receives 'romanized' and 'translation' fields.
    """
    enriched = []
    for line in lines:
        raw_text = line.get("text", "")
        item = dict(line)

        if has_cjk(raw_text):
            item["romanized"] = romanize_text(raw_text)
            # Only translate lines with significant text
            if len(raw_text.strip()) > 2:
                item["translation"] = translate_text(raw_text, target_lang)
            else:
                item["translation"] = ""
        else:
            item["romanized"] = ""
            item["translation"] = ""

        enriched.append(item)
    return enriched
