"""
headphone_autoeq.py - Headphone AutoEq & Harman Target Calibration Studio
Part of Sonance - The Ultimate Open-Source Music Workstation
Calibrates headphone frequency responses to the Harman 2020 Target curve with
built-in audiophile profiles and EqualizerAPO / Peace parametric profile import.

Author: Sandeep Khadka <sandeepkhadka9090@gmail.com>
License: GNU General Public License v3.0 with Commons Clause
"""

import re
from typing import Dict, List, Any, Optional

# Standard 10-Band Studio Hardware EQ Frequencies (Hz)
EQ_10_BANDS = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

# Built-in AutoEq database (calibrated toward Harman 2020 Target)
AUTOEQ_PROFILES: Dict[str, Dict[str, Any]] = {
    "sennheiser_hd600": {
        "name": "Sennheiser HD 600",
        "brand": "Sennheiser",
        "type": "Over-Ear Open",
        "preamp_db": -4.2,
        "gains": [5.5, 4.2, 1.5, -0.5, 0.0, 0.5, -1.0, 1.5, -2.0, -1.5],
        "description": "Compensates sub-bass roll-off and smooths upper-mid peak toward the Harman Target.",
    },
    "sennheiser_hd650": {
        "name": "Sennheiser HD 650 / HD 6XX",
        "brand": "Sennheiser",
        "type": "Over-Ear Open",
        "preamp_db": -4.8,
        "gains": [6.0, 4.5, 1.8, -0.8, -0.5, 0.2, -0.5, 2.0, -1.0, -0.5],
        "description": "Lifts sub-bass extension while opening up the veiled top-end presence.",
    },
    "sennheiser_hd800s": {
        "name": "Sennheiser HD 800 S",
        "brand": "Sennheiser",
        "type": "Over-Ear Open",
        "preamp_db": -5.5,
        "gains": [6.5, 4.0, 1.0, 0.0, 0.5, 1.0, -1.5, -3.5, 1.5, 0.0],
        "description": "Adds deep sub-bass body and tames the sharp 6 kHz resonance peak for fatigue-free staging.",
    },
    "sony_wh1000xm4": {
        "name": "Sony WH-1000XM4 (ANC)",
        "brand": "Sony",
        "type": "Wireless ANC",
        "preamp_db": -3.0,
        "gains": [-4.5, -3.0, -2.0, 0.5, 1.5, 2.5, 3.0, 2.0, -1.0, 1.5],
        "description": "Clears boomy mid-bass muddiness and elevates recessed female vocals and treble detail.",
    },
    "sony_wh1000xm5": {
        "name": "Sony WH-1000XM5 (ANC)",
        "brand": "Sony",
        "type": "Wireless ANC",
        "preamp_db": -2.8,
        "gains": [-3.5, -2.5, -1.5, 0.0, 1.2, 2.2, 2.8, 1.5, -0.5, 2.0],
        "description": "Tames excessive bass bloat while delivering crystal-clear vocal transparency.",
    },
    "apple_airpods_max": {
        "name": "Apple AirPods Max",
        "brand": "Apple",
        "type": "Wireless ANC",
        "preamp_db": -2.5,
        "gains": [1.0, -1.0, -0.5, 0.5, 1.0, 1.5, -1.0, 2.5, 1.0, -2.0],
        "description": "Enhances midrange presence and resolves upper-treble dip for studio balance.",
    },
    "apple_airpods_pro_2": {
        "name": "Apple AirPods Pro 2",
        "brand": "Apple",
        "type": "True Wireless IEM",
        "preamp_db": -2.0,
        "gains": [1.5, 0.5, -0.5, -0.5, 0.5, 1.0, -0.5, 1.5, 0.5, 1.0],
        "description": "Subtle tuning refining already-exceptional stock response into exact Harman alignment.",
    },
    "beyerdynamic_dt770_80": {
        "name": "Beyerdynamic DT 770 Pro (80Ω)",
        "brand": "Beyerdynamic",
        "type": "Over-Ear Closed",
        "preamp_db": -4.5,
        "gains": [1.5, 0.0, -2.5, -1.5, 0.5, 1.5, -1.0, -4.5, -3.0, -1.0],
        "description": "Softens the aggressive 6-9 kHz 'Beyer treble peak' and balances the V-shaped bass boost.",
    },
    "beyerdynamic_dt990_250": {
        "name": "Beyerdynamic DT 990 Pro (250Ω)",
        "brand": "Beyerdynamic",
        "type": "Over-Ear Open",
        "preamp_db": -5.0,
        "gains": [4.0, 2.0, -1.0, -1.0, 0.0, 1.0, -1.5, -5.5, -4.0, -1.5],
        "description": "Suppresses harsh treble sibilance and restores warm linear sub-bass.",
    },
    "audiotechnica_ath_m50x": {
        "name": "Audio-Technica ATH-M50x",
        "brand": "Audio-Technica",
        "type": "Over-Ear Closed",
        "preamp_db": -3.5,
        "gains": [-1.0, -2.5, -1.5, 0.5, 1.0, 0.5, -1.5, -2.0, 1.0, 2.5],
        "description": "Reduces mid-bass hump and smooths peaky lower-treble for accurate studio monitoring.",
    },
    "moondrop_blessing2": {
        "name": "Moondrop Blessing 2 / Dusk",
        "brand": "Moondrop",
        "type": "In-Ear Monitor",
        "preamp_db": -2.0,
        "gains": [2.5, 1.5, 0.0, -0.5, 0.0, 0.5, 0.0, -1.0, 1.0, 2.0],
        "description": "Adds satisfying tactile sub-bass rumble while maintaining class-leading midrange purity.",
    },
    "moondrop_aria": {
        "name": "Moondrop Aria",
        "brand": "Moondrop",
        "type": "In-Ear Monitor",
        "preamp_db": -2.2,
        "gains": [2.0, 1.0, 0.0, -0.5, 0.5, 0.5, -0.5, 1.0, 0.5, 1.5],
        "description": "Enhances dynamic slam and micro-detail resolution according to Harman IE target.",
    },
    "hifiman_sundara": {
        "name": "Hifiman Sundara (Planar)",
        "brand": "Hifiman",
        "type": "Planar Magnetic Open",
        "preamp_db": -4.0,
        "gains": [5.5, 3.5, 1.0, 0.0, -0.5, 0.0, 0.5, -1.0, 1.5, 0.0],
        "description": "Restores deep planar sub-bass extension to match the hyper-fast acoustic transients.",
    },
    "bose_qc35ii": {
        "name": "Bose QuietComfort 35 II / QC45",
        "brand": "Bose",
        "type": "Wireless ANC",
        "preamp_db": -2.5,
        "gains": [2.0, 0.5, -1.0, 0.0, 0.5, 1.5, 2.0, -1.0, 1.0, 2.0],
        "description": "Opens up the soundstage and clarifies muffled treble details.",
    },
    "shure_se215": {
        "name": "Shure SE215",
        "brand": "Shure",
        "type": "In-Ear Monitor",
        "preamp_db": -3.5,
        "gains": [-3.0, -2.5, -1.5, 0.5, 1.5, 2.5, 3.5, 2.5, 0.0, 3.0],
        "description": "Tames muddy 200 Hz warmth and rescues recessed upper-mids and treble harmonics.",
    },
    "harman_target_2020": {
        "name": "Harman 2020 Target Reference",
        "brand": "Harman / AKG",
        "type": "Target Curve",
        "preamp_db": -3.0,
        "gains": [4.0, 2.5, 1.0, 0.0, 0.0, 0.5, 1.0, 1.5, 0.5, 1.0],
        "description": "Industry-standard Harman consumer target curve with warm sub-bass and natural pinna gain.",
    },
    "diffuse_field_neutral": {
        "name": "Diffuse Field Reference (Studio Flat)",
        "brand": "Reference",
        "type": "Target Curve",
        "preamp_db": 0.0,
        "gains": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "description": "Pristine flat calibration curve for uncolored acoustic monitoring and mastering.",
    },
}


def get_available_profiles() -> List[Dict[str, Any]]:
    """Returns a list of all built-in AutoEq calibration profiles."""
    profiles = []
    for key, data in AUTOEQ_PROFILES.items():
        profiles.append({
            "key": key,
            "name": data["name"],
            "brand": data["brand"],
            "type": data["type"],
            "preamp_db": data["preamp_db"],
            "gains": data["gains"],
            "description": data["description"],
        })
    return profiles


def get_profile_by_key(key: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific profile by its identifier."""
    return AUTOEQ_PROFILES.get(key)


def parse_equalizer_apo_text(content: str) -> Dict[str, Any]:
    """
    Parses an EqualizerAPO / Peace configuration file into 10-band studio EQ gains.
    Supports GraphicEQ lines or parametric Filter lines.
    """
    gains = [0.0] * 10
    preamp = 0.0

    # Look for Preamp: Preamp: -4.5 dB
    preamp_match = re.search(r"Preamp:\s*([+-]?\d+(?:\.\d+)?)\s*dB", content, re.IGNORECASE)
    if preamp_match:
        preamp = float(preamp_match.group(1))

    # Check for GraphicEQ: 25 1.5; 40 2.0; ...
    graphic_match = re.search(r"GraphicEQ:\s*([^\r\n]+)", content)
    if graphic_match:
        pairs = graphic_match.group(1).split(";")
        freq_gain_map = {}
        for p in pairs:
            parts = p.strip().split()
            if len(parts) >= 2:
                try:
                    f = float(parts[0])
                    g = float(parts[1])
                    freq_gain_map[f] = g
                except ValueError:
                    pass

        # Interpolate closest frequencies to our 10 bands
        if freq_gain_map:
            for idx, target_f in enumerate(EQ_10_BANDS):
                closest_f = min(freq_gain_map.keys(), key=lambda f: abs(f - target_f))
                gains[idx] = round(freq_gain_map[closest_f], 1)

            return {
                "success": True,
                "name": "Custom EqualizerAPO GraphicEQ",
                "preamp_db": preamp,
                "gains": gains,
                "description": "Imported from EqualizerAPO GraphicEQ profile.",
            }

    # Parametric Filter lines: Filter 1: ON PK Fc 1000 Gain -2.5 Q 1.4
    param_matches = re.findall(r"Filter\s*\d*:\s*ON\s+PK\s+Fc\s+(\d+(?:\.\d+)?)\s+Gain\s+([+-]?\d+(?:\.\d+)?)", content, re.IGNORECASE)
    if param_matches:
        for fc_str, gain_str in param_matches:
            fc = float(fc_str)
            g = float(gain_str)
            # Find closest standard 10-band
            closest_idx = min(range(len(EQ_10_BANDS)), key=lambda i: abs(EQ_10_BANDS[i] - fc))
            gains[closest_idx] += g

        # Clamp gains to standard slider range [-12.0, +12.0]
        gains = [max(-12.0, min(12.0, round(v, 1))) for v in gains]
        return {
            "success": True,
            "name": "Custom Parametric EQ",
            "preamp_db": preamp,
            "gains": gains,
            "description": f"Imported {len(param_matches)} parametric filters.",
        }

    return {"success": False, "error": "No valid GraphicEQ or Parametric Filter lines found."}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2 or sys.argv[1] == "--list":
        print("Available Headphone AutoEq Profiles:")
        for p in get_available_profiles():
            print(f"  [{p['key']}] {p['name']} ({p['type']}) - Preamp: {p['preamp_db']} dB")
            print(f"    Gains: {p['gains']}")
            print(f"    Notes: {p['description']}")
    else:
        key = sys.argv[1]
        prof = get_profile_by_key(key)
        if prof:
            print(f"Profile: {prof['name']} [{prof['brand']}]")
            print(f"Preamp:  {prof['preamp_db']} dB")
            for f, g in zip(EQ_10_BANDS, prof['gains']):
                print(f"  {f:>5} Hz: {g:>+5.1f} dB")
            print(f"Summary: {prof['description']}")
        else:
            print(f"Profile '{key}' not found. Run with --list to view all available models.")
