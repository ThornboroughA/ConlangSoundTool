#!/usr/bin/env python3
"""Simple Streamlit UI for the Sound Inventory Generator."""

from __future__ import annotations

import csv
import io
import json
import random
import re
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import streamlit as st

import family_generator
import language_diff
import project_io
import sound_inventory_generator as generator
import sound_change_engine
from sample_text_generator import (
    CONCEPT_LIST_PRESETS,
    DEFAULT_PHONOTACTIC_PROFILE,
    DEFAULT_CONCEPT_LIST,
    DEFAULT_GRAMMAR_PROFILE,
    DEFAULT_STYLE_PRESET,
    GRAMMAR_PROFILES,
    POS_LABELS,
    STYLE_PRESETS,
    build_custom_entry,
    build_language_model,
    build_sample_sentences,
    build_sample_words,
    concept_gloss,
    generate_custom_word_form,
    is_custom_entry,
    language_model_summary,
    model_matches,
    rebuild_indices,
    reroll_lexicon_entry,
    validate_generation_config,
)

try:  # pragma: no cover - optional UI dependency
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover - optional UI dependency
    AGRAPH_AVAILABLE = False

IPA_TO_ROMAN_DIACRITICS: Dict[str, str] = {
    # Vowels
    "a": "a",
    "ɑ": "ā",
    "aː": "ā",
    "a˞": "ar",
    "a̟˞": "ar",
    "ɐ": "ă",
    "æ": "ae",
    "æː": "ǣ",
    "e": "e",
    "eɪ": "ei",
    "ɛ": "e",
    "ɛː": "ē",
    "eː": "ē",
    "e̞": "e",
    "ə": "ə",
    "ə˞": "er",
    "ə̃˞": "er",
    "ɜ": "er",
    "ɪ": "ĭ",
    "i": "i",
    "iː": "ī",
    "o": "o",
    "oʊ": "ou",
    "ɔ": "ô",
    "ɔː": "ô̄",
    "ɒ": "ŏ",
    "oː": "ō",
    "o̞": "o",
    "ʊ": "ŭ",
    "u": "u",
    "uː": "ū",
    "u˞": "ur",
    "ʌ": "ŭ",
    "y": "ü",
    "ø": "ö",
    "œ": "œ",
    "ɨ": "ɨ",
    "ʉ": "ǖ",
    "ɯ": "eu",
    "ɯː": "eū",
    "ɯ̃": "eũ",
    "ɤ": "eo",
    "ɤː": "eō",
    "ɤ˞": "eor",
    "ɤ̟": "eo",
    "ɵ̞": "ö",
    "ɑ̃˞": "ar",
    # Stops / affricates
    "p": "p",
    "pˀ": "p’",
    "p͈": "pp",
    "pː": "pp",
    "pʰ": "ph",
    "b": "b",
    "t": "t",
    "tˀ": "t’",
    "t͈": "tt",
    "tː": "tt",
    "tʰ": "th",
    "d": "d",
    "d̠ʒ": "j",
    "d̪": "d",
    "d̪ʲ": "dy",
    "ʈ": "ṭ",
    "ɖ": "ḍ",
    "k": "k",
    "kˀ": "k’",
    "k͈": "kk",
    "kː": "kk",
    "kʰ": "kh",
    "g": "g",
    "ɡ": "g",
    "q": "q",
    "ɢ": "ġ",
    "ʔ": "’",
    "c": "ky",
    "ɟ": "gy",
    "tʃ": "ch",
    "t̠ʃ": "ch",
    "t̠ʃʰ": "chh",
    "t̠ʃˀ": "ch’",
    "t̠ʃː": "chch",
    "dʒ": "j",
    "tɕ": "j",
    "tɕʰ": "ch",
    "ts": "ts",
    "tsʰ": "tsh",
    "tsː": "tsts",
    "t̪": "t",
    "t̪ʰ": "th",
    "t̪ʲ": "ty",
    "t̪s̪": "ts",
    "t̪s̪ʰ": "tsh",
    "ʈʂ": "ch",
    "ʈʂʰ": "chh",
    # Nasals
    "m": "m",
    "n": "n",
    "n̪": "n",
    "ŋ": "ng",
    "ɲ": "ñ",
    "ɳ": "ṇ",
    "ɴ": "ṅ",
    # Fricatives
    "f": "f",
    "v": "v",
    "ɸ": "ph",
    "β": "bh",
    "θ": "th",
    "ð": "dh",
    "s": "s",
    "sˀ": "s’",
    "s͈": "ss",
    "sː": "ss",
    "s̪": "s",
    "s̪ʲ": "sy",
    "z": "z",
    "ʃ": "sh",
    "ʃː": "shsh",
    "ʒ": "zh",
    "ʂ": "ṣ",
    "ʐ": "ẓ",
    "x": "kh",
    "χ": "qh",
    "ɣ": "gh",
    "h": "h",
    "h͈": "hh",
    "ç": "ç",
    "çː": "çç",
    "ʝ": "y",
    "ʁ": "ṛ",
    # Rhotics / laterals / approximants
    "r": "rr",
    "ɾ": "r",
    "ɽ": "ṛ",
    "ɻ": "r",
    "l": "l",
    "l̪": "l",
    "l̪ʲ": "ly",
    "l̪ˠ": "ł",
    "ɭ": "ḷ",
    "ʋ": "w",
    "w": "w",
    "w˞": "wr",
    "j": "y",
    "ɥ": "ü",
    "ɰ": "ğ",
    # Other
    "ʙ": "br",
    "cc": "cc",
    "ch": "ch",
    "cç": "ch",
    "cçʰ": "chh",
    "˥": "H",
    "˥˦": "HM",
    "˧˥": "MH",
    "˧˨˥": "MHM",
}

IPA_TO_ROMAN_ASCII: Dict[str, str] = {
    # Vowels
    "a": "a",
    "ɑ": "aa",
    "aː": "aa",
    "a˞": "ar",
    "a̟˞": "ar",
    "ɐ": "a",
    "æ": "ae",
    "æː": "aeae",
    "e": "e",
    "eɪ": "ei",
    "ɛ": "e",
    "ɛː": "ee",
    "eː": "ee",
    "e̞": "e",
    "ə": "e",
    "ə˞": "er",
    "ə̃˞": "er",
    "ɜ": "er",
    "ɪ": "i",
    "i": "i",
    "iː": "ii",
    "o": "o",
    "oʊ": "ou",
    "ɔ": "o",
    "ɔː": "oo",
    "ɒ": "o",
    "oː": "oo",
    "o̞": "o",
    "ʊ": "u",
    "u": "u",
    "uː": "uu",
    "u˞": "ur",
    "ʌ": "u",
    "y": "u",
    "ø": "oe",
    "œ": "oe",
    "ɨ": "y",
    "ʉ": "u",
    "ɯ": "eu",
    "ɯː": "eueu",
    "ɯ̃": "eu~",
    "ɤ": "eo",
    "ɤː": "eoeo",
    "ɤ˞": "eor",
    "ɤ̟": "eo",
    "ɵ̞": "oe",
    "ɑ̃˞": "ar",
    # Stops / affricates
    "p": "p",
    "pˀ": "p'",
    "p͈": "pp",
    "pː": "pp",
    "pʰ": "ph",
    "b": "b",
    "t": "t",
    "tˀ": "t'",
    "t͈": "tt",
    "tː": "tt",
    "tʰ": "th",
    "d": "d",
    "d̠ʒ": "j",
    "d̪": "d",
    "d̪ʲ": "dy",
    "ʈ": "t",
    "ɖ": "d",
    "k": "k",
    "kˀ": "k'",
    "k͈": "kk",
    "kː": "kk",
    "kʰ": "kh",
    "g": "g",
    "ɡ": "g",
    "q": "q",
    "ɢ": "g",
    "ʔ": "'",
    "c": "ky",
    "ɟ": "gy",
    "tʃ": "ch",
    "t̠ʃ": "ch",
    "t̠ʃʰ": "chh",
    "t̠ʃˀ": "ch'",
    "t̠ʃː": "chch",
    "dʒ": "j",
    "tɕ": "j",
    "tɕʰ": "ch",
    "ts": "ts",
    "tsʰ": "tsh",
    "tsː": "tsts",
    "t̪": "t",
    "t̪ʰ": "th",
    "t̪ʲ": "ty",
    "t̪s̪": "ts",
    "t̪s̪ʰ": "tsh",
    "ʈʂ": "ch",
    "ʈʂʰ": "chh",
    # Nasals
    "m": "m",
    "n": "n",
    "n̪": "n",
    "ŋ": "ng",
    "ɲ": "ny",
    "ɳ": "n",
    "ɴ": "ng",
    # Fricatives
    "f": "f",
    "v": "v",
    "ɸ": "ph",
    "β": "bh",
    "θ": "th",
    "ð": "dh",
    "s": "s",
    "sˀ": "s'",
    "s͈": "ss",
    "sː": "ss",
    "s̪": "s",
    "s̪ʲ": "sy",
    "z": "z",
    "ʃ": "sh",
    "ʃː": "shsh",
    "ʒ": "zh",
    "ʂ": "sh",
    "ʐ": "zh",
    "x": "kh",
    "χ": "qh",
    "ɣ": "gh",
    "h": "h",
    "h͈": "hh",
    "ç": "hy",
    "çː": "hyhy",
    "ʝ": "y",
    "ʁ": "r",
    # Rhotics / laterals / approximants
    "r": "rr",
    "ɾ": "r",
    "ɽ": "r",
    "ɻ": "r",
    "l": "l",
    "l̪": "l",
    "l̪ʲ": "ly",
    "l̪ˠ": "l",
    "ɭ": "l",
    "ʋ": "w",
    "w": "w",
    "w˞": "wr",
    "j": "y",
    "ɥ": "yu",
    "ɰ": "gh",
    # Other
    "ʙ": "br",
    "cc": "cc",
    "ch": "ch",
    "cç": "ch",
    "cçʰ": "chh",
    "˥": "H",
    "˥˦": "HM",
    "˧˥": "MH",
    "˧˨˥": "MHM",
}

ROMANIZATION_PROFILES: Dict[str, Dict[str, str]] = {
    "Diacritics (recommended)": IPA_TO_ROMAN_DIACRITICS,
    "ASCII": IPA_TO_ROMAN_ASCII,
}
DEFAULT_ROMANIZATION_PROFILE = "Diacritics (recommended)"
PHOIBLE_DEFAULT_URL = "https://raw.githubusercontent.com/phoible/dev/refs/heads/master/data/phoible.csv"
PHOIBLE_CORE_WEIGHT_DEFAULT = 1.0
PHOIBLE_MARGINAL_WEIGHT_DEFAULT = 0.35
PHOIBLE_MAX_RESULTS = 200
FAMILY_TIMESPAN_DEFAULT = 2000
SOUND_CHANGE_TEMPLATE_LABELS: Dict[str, str] = {
    "stop_voicing": "Stop voicing (p→b, t→d, k→g)",
    "stop_devoicing": "Stop devoicing (b→p, d→t, g→k)",
    "s_voicing": "S voicing (s→z)",
    "h_loss": "H loss (h→∅)",
    "approximant_shift": "Approximant shift (w↔v)",
    "r_shift": "R shift (r↔ɾ)",
    "liquid_shift": "Liquid shift (l↔r)",
    "fricative_voicing": "Fricative voicing (f→v, s→z, ʃ→ʒ)",
    "fricative_devoicing": "Fricative devoicing (v→f, z→s, ʒ→ʃ)",
    "stop_lenition": "Stop lenition (p→f, t→s, k→x)",
    "stop_fortition": "Stop fortition (f→p, s→t, x→k)",
    "vowel_raise_pair": "Vowel raise (e→i, o→u, etc.)",
    "vowel_lower_pair": "Vowel lower (i→e, u→o, etc.)",
    "vowel_centralization": "Vowel centralization (i→ɪ, e→ə, o→ə)",
    "vowel_fronting": "Vowel fronting (u→y, o→ø)",
    "vowel_backing": "Vowel backing (i→ɯ, e→ɤ)",
}
SOUND_CHANGE_TEMPLATE_DESCRIPTIONS: Dict[str, str] = {
    "stop_voicing": "Turns voiceless stops into voiced ones (like p→b).",
    "stop_devoicing": "Turns voiced stops into voiceless ones (like b→p).",
    "s_voicing": "Voices s to z in applicable contexts.",
    "h_loss": "Deletes h from words, a common historical change.",
    "approximant_shift": "Swaps w and v, modeling labial approximant/ fricative shifts.",
    "r_shift": "Alternates r with a tap ɾ, a frequent rhotic drift.",
    "liquid_shift": "Swaps l and r, a frequent liquid shift in many families.",
    "fricative_voicing": "Voices fricatives (f→v, s→z, etc.).",
    "fricative_devoicing": "Devoices fricatives (v→f, z→s, etc.).",
    "stop_lenition": "Softens stops into fricatives (p→f, t→s, k→x).",
    "stop_fortition": "Hardens fricatives into stops (f→p, s→t, x→k).",
    "vowel_raise_pair": "Raises a vowel (like e→i or o→u).",
    "vowel_lower_pair": "Lowers a vowel (like i→e or u→o).",
    "vowel_centralization": "Moves vowels toward the center (i→ɪ, e→ə, o→ə).",
    "vowel_fronting": "Fronts back vowels (u→y, o→ø).",
    "vowel_backing": "Backs front vowels (i→ɯ, e→ɤ).",
}
SOUND_CHANGE_VOWEL_TEMPLATES = {
    "vowel_raise_pair",
    "vowel_lower_pair",
    "vowel_centralization",
    "vowel_fronting",
    "vowel_backing",
}

ROMANIZATION_FALLBACK_VOWELS = set("aeiouyæœɨöü")
ROMANIZATION_FALLBACK_VOWELS |= set("āēīōūȳǣôŏăŭ")
ROMANIZATION_ASCII_VOWELS = set("aeiouy")
IPA_TIE_BARS = {"͡", "͜"}
IPA_MODIFIER_DIACRITICS = {
    "ʰ", "ʱ", "ʲ", "ʷ", "ˠ", "ˤ", "ˀ", "ʼ", "ː", "ˑ", "˞",
    "ˈ", "ˌ", "̥", "̬", "̃", "̩", "̯", "̪", "̺", "̻", "̹", "̜", "̟", "̠",
}

def romanization_map(profile_name: str) -> Dict[str, str]:
    """Return the chosen IPA->romanization map with safe fallback."""
    return ROMANIZATION_PROFILES.get(profile_name, ROMANIZATION_PROFILES[DEFAULT_ROMANIZATION_PROFILE])


def segment_keys(profile_name: str) -> List[str]:
    """Return sorted IPA keys (longest first) for robust tokenization."""
    return sorted(romanization_map(profile_name).keys(), key=len, reverse=True)


def hint_for_segment(segment: str, profile_name: str = DEFAULT_ROMANIZATION_PROFILE) -> Dict[str, str]:
    """Return romanization metadata for an IPA segment."""
    mapped = romanize_segment(segment, profile_name=profile_name)
    if mapped:
        return {"sound_like": mapped, "example": ""}
    return {"sound_like": segment, "example": ""}


def _apply_macron(text: str) -> str:
    macron_map = {
        "a": "ā",
        "e": "ē",
        "i": "ī",
        "o": "ō",
        "u": "ū",
        "y": "ȳ",
        "æ": "ǣ",
        "ö": "ȫ",
        "ü": "ǖ",
        "ô": "ô̄",
        "ŏ": "ō",
        "ă": "ā",
        "ŭ": "ū",
        "ɨ": "ɨ̄",
        "ə": "ə̄",
        "œ": "œ̄",
    }
    chars = list(text)
    for index in range(len(chars) - 1, -1, -1):
        char = chars[index]
        if char in macron_map:
            chars[index] = macron_map[char]
            return "".join(chars)
        if char in ROMANIZATION_FALLBACK_VOWELS:
            chars[index] = char + "̄"
            return "".join(chars)
    return text


def _apply_nasalization(text: str, profile_name: str) -> str:
    if profile_name == "ASCII":
        return f"{text}~"
    chars = list(text)
    for index in range(len(chars) - 1, -1, -1):
        char = chars[index]
        if char in ROMANIZATION_FALLBACK_VOWELS:
            chars[index] = char + "̃"
            return "".join(chars)
    return f"{text}̃"


def _apply_length(text: str, profile_name: str) -> str:
    if not text:
        return text
    if profile_name == "ASCII":
        return text + text
    if any(char in ROMANIZATION_FALLBACK_VOWELS for char in text):
        return _apply_macron(text)
    return text + text[-1]


def romanize_segment(segment: str, profile_name: str = DEFAULT_ROMANIZATION_PROFILE) -> str:
    mapping = romanization_map(profile_name)
    if segment in mapping:
        return mapping[segment]
    return romanize_ipa_fallback(segment, profile_name=profile_name, mapping=mapping)


def romanize_ipa_fallback(segment: str, profile_name: str, mapping: Dict[str, str]) -> str:
    raw = segment.strip()
    if not raw:
        return raw
    if "|" in raw:
        raw = raw.split("|", 1)[0].strip()
    if raw in mapping:
        return mapping[raw]

    raw = raw.replace("͡", "").replace("͜", "")
    length_flag = "ː" in raw or "ˑ" in raw or "͈" in raw
    aspiration_flag = "ʰ" in raw or "ʱ" in raw
    palatal_flag = "ʲ" in raw
    labial_flag = "ʷ" in raw
    rhotic_flag = "˞" in raw
    ejective_flag = "ˀ" in raw or "ʼ" in raw
    nasal_flag = "̃" in raw

    decomposed = unicodedata.normalize("NFD", raw)
    base_chars: List[str] = []
    for char in decomposed:
        if char in IPA_TIE_BARS:
            continue
        if unicodedata.combining(char):
            continue
        if char in IPA_MODIFIER_DIACRITICS:
            continue
        base_chars.append(char)

    base = "".join(base_chars)
    if not base:
        return raw

    if base in mapping:
        roman = mapping[base]
    else:
        roman_parts = []
        for char in base:
            roman_parts.append(mapping.get(char, char))
        roman = "".join(roman_parts)

    if nasal_flag:
        roman = _apply_nasalization(roman, profile_name=profile_name)
    if length_flag:
        roman = _apply_length(roman, profile_name=profile_name)
    if palatal_flag:
        roman += "y"
    if labial_flag:
        roman += "w"
    if rhotic_flag:
        roman += "r"
    if aspiration_flag:
        roman += "h"
    if ejective_flag:
        roman += "’" if profile_name != "ASCII" else "'"

    return roman


def _consume_fallback_segment(text: str, index: int) -> Tuple[Tuple[str, str], int]:
    base = text[index]
    if base.isspace():
        return ("literal", base), index + 1
    segment = base
    cursor = index + 1
    while cursor < len(text):
        char = text[cursor]
        if unicodedata.combining(char) or char in IPA_MODIFIER_DIACRITICS:
            segment += char
            cursor += 1
            continue
        break
    return ("segment", segment), cursor


def tokenize_ipa_text(text: str, profile_name: str = DEFAULT_ROMANIZATION_PROFILE) -> List[Tuple[str, str]]:
    """Split a text into known IPA segments and literal characters."""
    profile_segment_keys = segment_keys(profile_name)
    tokens: List[Tuple[str, str]] = []
    index = 0
    while index < len(text):
        match = None
        for segment in profile_segment_keys:
            if text.startswith(segment, index):
                match = segment
                break
        if match:
            tokens.append(("segment", match))
            index += len(match)
        else:
            token, index = _consume_fallback_segment(text, index)
            tokens.append(token)
    return tokens


def ipa_text_to_sound_like(
    text: str,
    use_segment_separators: bool = False,
    profile_name: str = DEFAULT_ROMANIZATION_PROFILE,
) -> str:
    """Render a rough sound-like guide from IPA text."""
    parts: List[str] = []
    previous_was_segment = False

    for token_type, value in tokenize_ipa_text(text, profile_name=profile_name):
        if token_type == "segment":
            mapped = hint_for_segment(value, profile_name=profile_name)["sound_like"]
            if profile_name == "ASCII":
                mapped = re.sub(r"[^A-Za-z]", "", mapped)
            if previous_was_segment and use_segment_separators:
                parts.append("-")
            parts.append(mapped)
            previous_was_segment = True
            continue

        parts.append(value)
        if value in {" ", "\t", "\n", ".", ",", ";", ":", "?", "!", "-", "(" , ")"}:
            previous_was_segment = False
        else:
            previous_was_segment = False

    return "".join(parts)


def build_segment_rows(
    segments: List[str],
    profile_name: str = DEFAULT_ROMANIZATION_PROFILE,
    representation_lookup: Optional[Dict[str, float]] = None,
) -> List[Dict[str, str]]:
    """Build table rows with IPA plus sound-like references."""
    rows: List[Dict[str, str]] = []
    for segment in segments:
        hint = hint_for_segment(segment, profile_name=profile_name)
        representation_text = ""
        if representation_lookup and segment in representation_lookup:
            representation_text = f"{representation_lookup[segment]:.3f}"
        rows.append(
            {
                "IPA": segment,
                "Representation": representation_text,
                "Sound-like": hint["sound_like"],
                "Example": hint["example"],
            }
        )
    return rows


def build_pronunciation_csv(
    vowels: List[str],
    consonants: List[str],
    profile_name: str = DEFAULT_ROMANIZATION_PROFILE,
) -> str:
    """Build a downloadable CSV pronunciation guide for the latest result."""
    output = io.StringIO()
    output.write("Type,IPA,Sound-alike,Example\n")
    for segment_type, segments in [("vowel", vowels), ("consonant", consonants)]:
        for segment in segments:
            hint = hint_for_segment(segment, profile_name=profile_name)
            output.write(f"{segment_type},{segment},{hint['sound_like']},{hint['example']}\n")
    return output.getvalue()


def mix_share(weight: float, total_weight: float) -> float:
    """Return a safe percentage share for a source weight."""
    if total_weight <= 0:
        return 0.0
    return (weight / total_weight) * 100.0


def load_preset_safe(name: str) -> Dict[str, Any]:
    """Load preset data, returning empty lists on load issues."""
    try:
        return generator.load_preset(name)
    except Exception as exc:  # pragma: no cover - UI safety net
        st.warning(f"Could not load preset '{name}': {exc}")
        return {"vowels": [], "consonants": [], "vowels_entries": [], "consonants_entries": []}


def representation_lookup(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Build a map of segment -> representation for table display."""
    lookup: Dict[str, float] = {}
    for entry in entries:
        segment = str(entry.get("segment", "")).strip()
        if not segment:
            continue
        raw_value = entry.get("representation", 1.0)
        try:
            lookup[segment] = float(raw_value)
        except (TypeError, ValueError):
            lookup[segment] = 1.0
    return lookup


def render_mix_reference_panel(
    selected_presets: List[str],
    weights: List[float],
    random_weight: float,
    master_preset: str,
    profile_name: str,
) -> None:
    """Render a dynamic guide to help users understand active mix sources."""
    st.caption("Weights are relative proportions: 0.2 + 0.4 behaves the same as 1 + 2.")

    if not selected_presets:
        st.info("Select presets to preview their sounds and contribution to the mix.")
        return

    total_weight = sum(weights) + (random_weight if random_weight > 0 else 0.0)
    summary_rows: List[Dict[str, str]] = []
    loaded_presets: Dict[str, Dict[str, Any]] = {}

    for preset_name, weight in zip(selected_presets, weights):
        preset_data = load_preset_safe(preset_name)
        loaded_presets[preset_name] = preset_data
        summary_rows.append(
            {
                "Source": preset_name,
                "Weight": f"{weight:.2f}",
                "Mix share": f"{mix_share(weight, total_weight):.1f}%",
                "Vowels": str(len(preset_data.get("vowels", []))),
                "Consonants": str(len(preset_data.get("consonants", []))),
            }
        )

    if random_weight > 0:
        master_data = load_preset_safe(master_preset)
        loaded_presets[f"random::{master_preset}"] = master_data
        summary_rows.append(
            {
                "Source": f"random ({master_preset})",
                "Weight": f"{random_weight:.2f}",
                "Mix share": f"{mix_share(random_weight, total_weight):.1f}%",
                "Vowels": str(len(master_data.get("vowels", []))),
                "Consonants": str(len(master_data.get("consonants", []))),
            }
        )

    st.markdown("**Current weight breakdown**")
    st.dataframe(summary_rows, hide_index=True, use_container_width=True)

    st.markdown("**Source sound inventories**")
    for preset_name, weight in zip(selected_presets, weights):
        share_label = mix_share(weight, total_weight)
        with st.expander(f"{preset_name} - {share_label:.1f}% of current mix"):
            preset_data = loaded_presets[preset_name]
            col_left, col_right = st.columns(2)
            with col_left:
                display_segment_table(
                    "Vowels",
                    preset_data.get("vowels", []),
                    profile_name=profile_name,
                    representation_values=representation_lookup(preset_data.get("vowels_entries", [])),
                )
            with col_right:
                display_segment_table(
                    "Consonants",
                    preset_data.get("consonants", []),
                    profile_name=profile_name,
                    representation_values=representation_lookup(preset_data.get("consonants_entries", [])),
                )

    if random_weight > 0:
        random_key = f"random::{master_preset}"
        share_label = mix_share(random_weight, total_weight)
        with st.expander(f"random pool ({master_preset}) - {share_label:.1f}% of current mix"):
            master_data = loaded_presets[random_key]
            col_left, col_right = st.columns(2)
            with col_left:
                display_segment_table(
                    "Vowels",
                    master_data.get("vowels", []),
                    profile_name=profile_name,
                    representation_values=representation_lookup(master_data.get("vowels_entries", [])),
                )
            with col_right:
                display_segment_table(
                    "Consonants",
                    master_data.get("consonants", []),
                    profile_name=profile_name,
                    representation_values=representation_lookup(master_data.get("consonants_entries", [])),
                )


def list_json_names(directory: str) -> List[str]:
    """Return sorted JSON basenames in a directory."""
    path = Path(directory)
    if not path.exists():
        return []
    return sorted(file.stem for file in path.glob("*.json") if file.is_file())


def default_preset_selection(presets: List[str]) -> List[str]:
    """Choose a friendly default preset selection."""
    preferred = ["english", "korean"]
    selected = [name for name in preferred if name in presets]
    if selected:
        return selected
    return presets[: min(2, len(presets))]


def _clean_phoible_value(value: Any) -> str:
    text = str(value).strip()
    return "" if text.upper() == "NA" else text


@st.cache_data(show_spinner=True)
def load_phoible_index(url: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, str]]]]:
    inventories: Dict[str, Dict[str, Any]] = {}
    rows_by_inventory: Dict[str, List[Dict[str, str]]] = {}

    with urllib.request.urlopen(url) as response:  # nosec - user controlled URL in UI
        reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8"))
        for row in reader:
            inventory_id = _clean_phoible_value(row.get("InventoryID", ""))
            if not inventory_id:
                continue
            rows_by_inventory.setdefault(inventory_id, []).append(row)
            entry = inventories.get(inventory_id)
            if entry is None:
                language_name = _clean_phoible_value(row.get("LanguageName", "(unknown)")) or "(unknown)"
                specific_dialect = _clean_phoible_value(row.get("SpecificDialect", ""))
                entry = {
                    "inventory_id": inventory_id,
                    "language_name": language_name,
                    "specific_dialect": specific_dialect,
                    "glottocode": _clean_phoible_value(row.get("Glottocode", "")),
                    "iso": _clean_phoible_value(row.get("ISO6393", "")),
                    "source": _clean_phoible_value(row.get("Source", "")),
                    "vowel_count": 0,
                    "consonant_count": 0,
                    "tone_count": 0,
                    "segment_count": 0,
                }
                inventories[inventory_id] = entry

            segment_class = _clean_phoible_value(row.get("SegmentClass", "")).lower()
            if segment_class == "vowel":
                entry["vowel_count"] += 1
            elif segment_class == "consonant":
                entry["consonant_count"] += 1
            elif segment_class == "tone":
                entry["tone_count"] += 1
            entry["segment_count"] += 1

    inventory_list = sorted(
        inventories.values(),
        key=lambda item: (item.get("language_name", "").lower(), item.get("inventory_id", "")),
    )
    return inventory_list, rows_by_inventory


def filter_phoible_inventories(inventories: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    cleaned = query.strip().lower()
    if not cleaned:
        return inventories[:PHOIBLE_MAX_RESULTS]

    def _matches(entry: Dict[str, Any]) -> bool:
        return any(
            cleaned in str(entry.get(key, "")).lower()
            for key in ["language_name", "specific_dialect", "inventory_id", "glottocode", "iso", "source"]
        )

    return [entry for entry in inventories if _matches(entry)]


def build_phoible_preset(
    rows: List[Dict[str, str]],
    name: str,
    include_marginal: bool,
    include_tones: bool,
    core_weight: float,
    marginal_weight: float,
    meta: Dict[str, Any],
) -> Dict[str, Any]:
    vowels_raw: List[Dict[str, Any]] = []
    consonants_raw: List[Dict[str, Any]] = []

    for row in rows:
        segment = _clean_phoible_value(row.get("Phoneme", ""))
        if not segment:
            continue
        segment_class = _clean_phoible_value(row.get("SegmentClass", "")).lower()
        if segment_class == "vowel":
            target = vowels_raw
        elif segment_class == "consonant":
            target = consonants_raw
        elif segment_class == "tone":
            if not include_tones:
                continue
            target = consonants_raw
        else:
            continue

        is_marginal = _clean_phoible_value(row.get("Marginal", "")).upper() == "TRUE"
        if is_marginal and not include_marginal:
            continue
        weight = float(marginal_weight if is_marginal else core_weight)
        target.append({"segment": segment, "representation": weight})

    vowels_entries = generator._normalize_segment_entries(vowels_raw)
    consonants_entries = generator._normalize_segment_entries(consonants_raw)

    return {
        "name": name,
        "vowels": vowels_entries,
        "consonants": consonants_entries,
        "phoible": meta,
    }


def render_phoible_importer() -> None:
    with st.expander("Import preset from PHOIBLE", expanded=False):
        st.caption(
            "Pull inventories directly from PHOIBLE. PHOIBLE does not provide per-language frequency weights, "
            "so representation values are derived from the marginal flag (configurable below)."
        )
        enable_phoible = st.checkbox(
            "Enable PHOIBLE search",
            value=False,
            key="phoible_enable",
            help="Toggle to load the PHOIBLE database for preset imports.",
        )
        if not enable_phoible:
            return

        url = st.text_input(
            "PHOIBLE CSV URL",
            value=st.session_state.get("phoible_url", PHOIBLE_DEFAULT_URL),
            key="phoible_url",
            help="Advanced: override the default PHOIBLE CSV source.",
        )

        try:
            inventories, rows_by_inventory = load_phoible_index(url)
        except Exception as exc:  # pragma: no cover - network safety net
            st.error(f"Could not load PHOIBLE data: {exc}")
            return

        query = st.text_input(
            "Search (language, dialect, ISO, Glottocode, or inventory ID)",
            value=st.session_state.get("phoible_query", ""),
            key="phoible_query",
            help="Filter inventories by name, ID, ISO, or Glottocode.",
        )
        matches = filter_phoible_inventories(inventories, query)
        if not query:
            st.info(f"Showing the first {min(len(matches), PHOIBLE_MAX_RESULTS)} inventories. Type to filter.")
        st.caption(f"Matches: {len(matches)}")

        if not matches:
            st.warning("No matches found. Try a different search term.")
            return

        labels: Dict[str, Dict[str, Any]] = {}
        for entry in matches[:PHOIBLE_MAX_RESULTS]:
            dialect = f" — {entry['specific_dialect']}" if entry.get("specific_dialect") else ""
            label = (
                f"{entry['language_name']}{dialect} "
                f"({entry.get('iso') or '—'}, {entry.get('glottocode') or '—'}) "
                f"· Inv {entry['inventory_id']} · "
                f"{entry['vowel_count']}V/{entry['consonant_count']}C"
            )
            labels[label] = entry

        selected_label = st.selectbox(
            "Matching inventories",
            options=list(labels.keys()),
            key="phoible_selected_label",
            help="Pick the inventory to import.",
        )
        selected_entry = labels[selected_label]
        inventory_id = selected_entry["inventory_id"]
        rows = rows_by_inventory.get(inventory_id, [])
        st.caption(
            f"Inventory {inventory_id} includes {selected_entry['segment_count']} segments "
            f"({selected_entry['vowel_count']} vowels, {selected_entry['consonant_count']} consonants, "
            f"{selected_entry['tone_count']} tones)."
        )

        include_marginal = st.checkbox(
            "Include marginal segments",
            value=True,
            key="phoible_include_marginal",
            help="Keep segments marked as marginal in PHOIBLE.",
        )
        include_tones = st.checkbox(
            "Include tone segments (stored as consonants)",
            value=False,
            key="phoible_include_tones",
            help="Include tone markers in the consonant list.",
        )
        core_weight = st.slider(
            "Core segment representation weight",
            min_value=0.2,
            max_value=2.0,
            value=PHOIBLE_CORE_WEIGHT_DEFAULT,
            step=0.05,
            key="phoible_core_weight",
            help="Relative weight for non-marginal segments.",
        )
        marginal_weight = st.slider(
            "Marginal segment representation weight",
            min_value=0.05,
            max_value=1.0,
            value=PHOIBLE_MARGINAL_WEIGHT_DEFAULT,
            step=0.05,
            key="phoible_marginal_weight",
            help="Relative weight for marginal segments.",
        )

        default_display_name = selected_entry["language_name"]
        if selected_entry.get("specific_dialect"):
            default_display_name = f"{default_display_name} {selected_entry['specific_dialect']}"
        default_display_name = f"{default_display_name} ({inventory_id})"
        suggested_filename = sanitize_name(f"{selected_entry['language_name']}_{inventory_id}")

        selected_key = f"{selected_entry.get('language_name','')}-{inventory_id}"
        last_key = st.session_state.get("phoible_last_selected")
        if selected_key != last_key:
            st.session_state["phoible_last_selected"] = selected_key
            st.session_state["phoible_preset_name"] = default_display_name
            st.session_state["phoible_preset_filename"] = suggested_filename

        preset_display_name = st.text_input(
            "Preset display name",
            value=st.session_state.get("phoible_preset_name", default_display_name),
            key="phoible_preset_name",
            help="Human-readable name stored inside the preset JSON.",
        )
        preset_filename = st.text_input(
            "Preset filename (without .json)",
            value=st.session_state.get("phoible_preset_filename", suggested_filename),
            key="phoible_preset_filename",
            help="Filename used when saving into presets/.",
        )
        overwrite_existing = st.checkbox(
            "Overwrite existing preset file",
            value=False,
            key="phoible_overwrite",
            help="Allow replacing a preset with the same filename.",
        )

        if st.button(
            "Create preset from PHOIBLE",
            type="primary",
            use_container_width=True,
            help="Save this inventory into presets/ for mixing later.",
        ):
            safe_name = sanitize_name(preset_filename)
            if not safe_name:
                st.error("Provide a valid preset filename.")
                return
            preset_path = Path(generator.PRESETS_DIR) / f"{safe_name}.json"
            if preset_path.exists() and not overwrite_existing:
                st.error(f"`{preset_path.name}` already exists. Enable overwrite to replace it.")
                return

            meta = {
                "inventory_id": inventory_id,
                "language_name": selected_entry.get("language_name"),
                "specific_dialect": selected_entry.get("specific_dialect"),
                "glottocode": selected_entry.get("glottocode"),
                "iso": selected_entry.get("iso"),
                "source": selected_entry.get("source"),
                "source_url": url,
            }
            preset_payload = build_phoible_preset(
                rows=rows,
                name=preset_display_name,
                include_marginal=include_marginal,
                include_tones=include_tones,
                core_weight=core_weight,
                marginal_weight=marginal_weight,
                meta=meta,
            )

            if not preset_payload["vowels"] or not preset_payload["consonants"]:
                st.error("Preset must include at least one vowel and one consonant.")
                return

            with preset_path.open("w", encoding="utf-8") as file:
                json.dump(preset_payload, file, ensure_ascii=False, indent=2)

            st.session_state["preset_notice"] = f"PHOIBLE preset saved: {preset_path.name}"
            st.rerun()


def sanitize_name(value: str) -> str:
    """Convert free text to a safe lowercase filename."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_").lower()
    return cleaned or "generated_preset"


def nested_value(mapping: Dict[str, Any], path: Sequence[str], fallback: Any) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return fallback
        current = current[key]
    return current


def deep_merge_dict(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(dict(merged.get(key, {})), value)
        else:
            merged[key] = value
    return merged


def parse_override_json(raw_text: str) -> Tuple[Dict[str, Any], Optional[str]]:
    cleaned = raw_text.strip()
    if not cleaned:
        return {}, None
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return {}, f"Invalid override JSON: {exc}"
    if not isinstance(parsed, dict):
        return {}, "Override JSON must be an object at the top level."
    return parsed, None


def resolve_output_dir(raw_value: str) -> Path:
    """Resolve output directory. Relative paths are rooted at project dir."""
    path = Path(raw_value).expanduser()
    if path.is_absolute():
        return path
    return Path(generator.SCRIPT_DIR) / path


def inventory_as_preset_payload(inventory: Dict[str, Any], language_name: str) -> Dict[str, Any]:
    """Return generated inventory in preset-compatible JSON format."""
    vowels_representation = inventory.get("vowels_representation", {})
    consonants_representation = inventory.get("consonants_representation", {})
    return {
        "name": language_name,
        "vowels": [
            {"segment": segment, "representation": float(vowels_representation.get(segment, 1.0))}
            for segment in inventory.get("vowels", [])
        ],
        "consonants": [
            {"segment": segment, "representation": float(consonants_representation.get(segment, 1.0))}
            for segment in inventory.get("consonants", [])
        ],
    }


def build_language_snapshot(
    language_name: str,
    inventory: Dict[str, Any],
    language_model: Optional[Dict[str, Any]] = None,
    language_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a v1 language snapshot payload from the current model/inventory."""
    base: Dict[str, Any] = {}
    if isinstance(language_model, dict):
        base.update(language_model)
    base["inventory"] = {
        "vowels": list(inventory.get("vowels", [])) if isinstance(inventory.get("vowels", []), list) else [],
        "consonants": list(inventory.get("consonants", [])) if isinstance(inventory.get("consonants", []), list) else [],
    }
    base.setdefault("style_name", DEFAULT_STYLE_PRESET)
    base.setdefault("concept_list_name", DEFAULT_CONCEPT_LIST)
    base.setdefault("grammar_profile_name", DEFAULT_GRAMMAR_PROFILE)
    base.setdefault("syllable_range", [1, 1])
    base.setdefault("syllable_separator", "")
    base.setdefault("phonotactic_profile_overrides", {})
    base["lexicon"] = list(base.get("lexicon", [])) if isinstance(base.get("lexicon", []), list) else []

    snapshot = project_io.normalize_language_snapshot(base)
    notes_value = ""
    meta_base = base.get("meta")
    if isinstance(meta_base, dict):
        notes_value = str(meta_base.get("notes", ""))
    if notes is not None:
        notes_value = str(notes)
    safe_id = language_id or sanitize_name(language_name)
    snapshot["meta"] = {
        "language_id": safe_id,
        "name": language_name,
        "year": 0,
        "parent_id": None,
        "changeset_id": None,
        "created_at": datetime.now().isoformat(),
        "notes": notes_value,
        "lexicon_overrides": {},
    }
    return snapshot


def snapshot_summary(snapshot: Dict[str, Any]) -> str:
    inventory = snapshot.get("inventory", {})
    vowels = inventory.get("vowels", []) if isinstance(inventory, dict) else []
    consonants = inventory.get("consonants", []) if isinstance(inventory, dict) else []
    lexicon = snapshot.get("lexicon", [])
    return f"{len(vowels)} vowels, {len(consonants)} consonants, {len(lexicon) if isinstance(lexicon, list) else 0} lexicon entries"


def discover_project_dirs(root_dir: Path) -> List[Path]:
    root_dir = Path(root_dir)
    if not root_dir.exists():
        return []
    return sorted([path for path in root_dir.iterdir() if path.is_dir() and (path / "project.json").exists()])


def load_languages_from_project(project: Dict[str, Any], project_dir: Path) -> Dict[str, Dict[str, Any]]:
    languages: Dict[str, Dict[str, Any]] = {}
    language_index = project.get("language_index", [])
    if not isinstance(language_index, list):
        return languages
    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
    for entry in language_index:
        if not isinstance(entry, dict):
            continue
        language_id = entry.get("language_id")
        filename = entry.get("filename")
        if not language_id or not filename:
            continue
        path = languages_dir / filename
        if not path.exists():
            continue
        languages[str(language_id)] = project_io.load_language(path)
    return languages


def find_entry_ipa(language: Dict[str, Any], entry_id: str) -> str:
    lexicon = language.get("lexicon", [])
    if not isinstance(lexicon, list):
        return ""
    for entry in lexicon:
        if isinstance(entry, dict) and str(entry.get("id", "")) == entry_id:
            return str(entry.get("ipa", ""))
    return ""


def extract_custom_entries(language_model: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(language_model, dict):
        return []
    lexicon = language_model.get("lexicon", [])
    if not isinstance(lexicon, list):
        return []
    return [entry for entry in lexicon if isinstance(entry, dict) and is_custom_entry(entry)]


def merge_custom_entries(language_model: Dict[str, Any], custom_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(language_model, dict):
        return language_model
    lexicon = language_model.get("lexicon", [])
    if not isinstance(lexicon, list):
        lexicon = []
    base_entries = [entry for entry in lexicon if isinstance(entry, dict) and not is_custom_entry(entry)]
    merged: List[Dict[str, Any]] = list(base_entries)
    seen_ids = {str(entry.get("id", "")).strip() for entry in base_entries if isinstance(entry, dict)}
    for entry in custom_entries or []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", "")).strip()
        if not entry_id or entry_id in seen_ids:
            continue
        merged.append(entry)
        seen_ids.add(entry_id)
    language_model["lexicon"] = merged
    return rebuild_indices(language_model)


def ensure_language_model(
    cached_model: Optional[Dict[str, Any]],
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    concept_list_name: str,
    grammar_profile_name: str,
    phonotactic_profile_overrides: Optional[Dict[str, Any]],
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    custom_entries = extract_custom_entries(cached_model)

    if force_rebuild or not isinstance(cached_model, dict):
        model = build_language_model(
            vowels=vowels,
            consonants=consonants,
            syllable_range=syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
            concept_list_name=concept_list_name,
            grammar_profile_name=grammar_profile_name,
            phonotactic_profile_overrides=phonotactic_profile_overrides,
        )
        if custom_entries:
            model = merge_custom_entries(model, custom_entries)
        return rebuild_indices(model)

    if model_matches(
        cached_model,
        vowels=vowels,
        consonants=consonants,
        syllable_range=syllable_range,
        syllable_separator=syllable_separator,
        style_name=style_name,
        concept_list_name=concept_list_name,
        grammar_profile_name=grammar_profile_name,
        phonotactic_profile_overrides=phonotactic_profile_overrides,
    ):
        return rebuild_indices(cached_model)

    return rebuild_indices(cached_model)


def display_segment_table(
    title: str,
    segments: List[str],
    profile_name: str = DEFAULT_ROMANIZATION_PROFILE,
    representation_values: Optional[Dict[str, float]] = None,
) -> None:
    """Render a segment list in a compact table."""
    st.markdown(f"**{title} ({len(segments)})**")
    rows = build_segment_rows(
        segments,
        profile_name=profile_name,
        representation_lookup=representation_values,
    )
    st.dataframe(rows, hide_index=True, use_container_width=True)


def build_lexicon_csv(rows: Sequence[Dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "ipa", "sound_like", "meaning", "gloss", "pos", "source"])
    for row in rows:
        writer.writerow(
            [
                row.get("id", ""),
                row.get("ipa", ""),
                row.get("sound_like", ""),
                row.get("meaning", ""),
                row.get("gloss", ""),
                row.get("pos", ""),
                row.get("source", ""),
            ]
        )
    return output.getvalue()


def suggest_language_name(language_model: Optional[Dict[str, Any]], profile_name: str) -> str:
    if not isinstance(language_model, dict):
        return ""
    lexicon = language_model.get("lexicon", [])
    if not isinstance(lexicon, list) or not lexicon:
        return ""
    candidates: List[Dict[str, Any]] = []
    for entry in lexicon:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", "")).strip()
        pos = str(entry.get("pos", "")).strip()
        source = str(entry.get("source", "")).strip()
        if entry_id.startswith("PART:") or pos == "PART" or source.startswith("grammar:"):
            continue
        if not str(entry.get("ipa", "")).strip():
            continue
        candidates.append(entry)
    if not candidates:
        return ""
    noun_candidates = [entry for entry in candidates if str(entry.get("pos", "")).strip() == "N"]
    pool = noun_candidates if noun_candidates else candidates
    chosen = random.choice(pool)
    ipa_value = str(chosen.get("ipa", "")).strip()
    if not ipa_value:
        return ""
    name = ipa_text_to_sound_like(ipa_value, use_segment_separators=False, profile_name=profile_name)
    name = re.sub(r"[\\s\\.-]+", "", name)
    if not name:
        return ""
    return name[0].upper() + name[1:]


def inject_custom_css() -> None:
    """Apply visual polish while keeping Streamlit-native layout behavior."""
    st.markdown(
        """
        <style>
        @import url("https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Sora:wght@300;400;500;600;700&display=swap");

        :root {
            --bg-start: #f4efe7;
            --bg-end: #e6f0ee;
            --panel: rgba(255, 255, 255, 0.92);
            --ink-strong: #172224;
            --ink-muted: #516463;
            --line: rgba(23, 34, 36, 0.12);
            --accent: #0f766e;
            --accent-soft: #14b8a6;
            --accent-warm: #d97706;
            --accent-cool: #2563eb;
        }

        .stApp {
            background:
                radial-gradient(1200px 520px at 4% -18%, rgba(245, 214, 164, 0.55) 0%, transparent 60%),
                radial-gradient(980px 560px at 100% 0%, rgba(175, 220, 214, 0.55) 0%, transparent 65%),
                linear-gradient(180deg, var(--bg-start), var(--bg-end));
        }

        .main .block-container {
            max-width: 1180px;
            padding-top: 1.1rem;
            padding-bottom: 2.2rem;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"] {
            color: var(--ink-strong);
            font-family: "Sora", "Segoe UI", "Trebuchet MS", sans-serif;
        }

        .material-symbols-rounded {
            font-family: "Material Symbols Rounded" !important;
        }

        h1, h2, h3, [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 {
            font-family: "DM Serif Display", "Palatino Linotype", "Book Antiqua", serif;
            letter-spacing: 0.01em;
        }

        @keyframes riseIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .hero-shell {
            border: 1px solid var(--line);
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(241, 248, 246, 0.92));
            border-radius: 18px;
            padding: 1.15rem 1.3rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 18px 36px rgba(17, 24, 24, 0.09);
            animation: riseIn 0.6s ease-out;
        }

        .hero-eyebrow {
            display: inline-block;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.7rem;
            color: var(--accent);
            background: rgba(15, 118, 110, 0.12);
            border: 1px solid rgba(15, 118, 110, 0.3);
            border-radius: 999px;
            padding: 0.18rem 0.6rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }

        .hero-title {
            font-size: clamp(1.55rem, 2.8vw, 2.15rem);
            line-height: 1.15;
            margin: 0;
        }

        .hero-copy {
            margin: 0.45rem 0 0;
            color: var(--ink-muted);
            max-width: 70ch;
            line-height: 1.45;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(248, 252, 251, 0.98), rgba(236, 246, 244, 0.98));
            border-right: 1px solid var(--line);
        }

        [data-testid="stMetric"] {
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 14px;
            padding: 0.6rem 0.75rem;
            box-shadow: 0 12px 24px rgba(15, 118, 110, 0.06);
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.82);
            box-shadow: 0 10px 18px rgba(17, 24, 24, 0.06);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(17, 24, 24, 0.05);
        }

        .stButton > button, .stDownloadButton > button {
            border-radius: 12px;
            border: 1px solid rgba(15, 118, 110, 0.28);
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(236, 246, 244, 0.96));
            box-shadow: 0 10px 20px rgba(15, 118, 110, 0.08);
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        }

        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 26px rgba(15, 118, 110, 0.12);
            border-color: rgba(15, 118, 110, 0.45);
        }

        .stButton > button[kind="primary"] {
            border: none;
            background: linear-gradient(135deg, var(--accent), var(--accent-soft));
            color: white;
            box-shadow: 0 12px 26px rgba(15, 118, 110, 0.24);
        }

        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 16px 32px rgba(15, 118, 110, 0.28);
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input {
            border-radius: 10px;
            border: 1px solid rgba(23, 34, 36, 0.15);
            background: rgba(255, 255, 255, 0.95);
        }

        [data-testid="stSelectbox"] [data-baseweb="select"] {
            border-radius: 10px;
            border: 1px solid rgba(23, 34, 36, 0.15);
            background: rgba(255, 255, 255, 0.95);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.84);
        }

        .stTabs [aria-selected="true"] {
            border-color: rgba(15, 118, 110, 0.45);
            background: rgba(232, 246, 244, 0.96);
        }

        .section-kicker {
            color: var(--accent-warm);
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-size: 0.73rem;
            margin-bottom: 0.1rem;
            font-weight: 600;
            animation: riseIn 0.5s ease-out;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    """Render branded header copy."""
    st.markdown(
        """
        <section class="hero-shell">
            <div class="hero-eyebrow">Conlang Sound Toolkit</div>
            <h1 class="hero-title">Design phonology-driven languages and evolving families.</h1>
            <p class="hero-copy">
                Mix inventories, build lexicons with custom words, and evolve daughter languages with sound changes.
                Save snapshots, curate entries, and keep every language ready for reuse.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_mix_metrics(selected_presets: List[str], random_weight: float, total_weight: float) -> None:
    """Show at-a-glance settings metrics for current controls."""
    metric_cols = st.columns(3)
    metric_cols[0].metric("Sources", f"{len(selected_presets)}")
    metric_cols[1].metric("Random Share", f"{mix_share(random_weight, total_weight):.1f}%")
    metric_cols[2].metric("Total Weight", f"{total_weight:.2f}")


def render_inventory_metrics(inventory: Dict[str, List[str]], lexicon_count: Optional[int] = None) -> None:
    """Show concise stats for the latest generated inventory."""
    vowels_count = len(inventory.get("vowels", []))
    consonants_count = len(inventory.get("consonants", []))
    total_count = vowels_count + consonants_count
    metric_cols = st.columns(4)
    metric_cols[0].metric("Vowels", f"{vowels_count}")
    metric_cols[1].metric("Consonants", f"{consonants_count}")
    metric_cols[2].metric("Total Segments", f"{total_count}")
    if lexicon_count is None:
        metric_cols[3].metric("Lexicon Entries", "—")
    else:
        metric_cols[3].metric("Lexicon Entries", f"{lexicon_count}")


def render_single_language_ui() -> None:
    romanization_profile = st.session_state.get("romanization_profile", DEFAULT_ROMANIZATION_PROFILE)
    if romanization_profile not in ROMANIZATION_PROFILES:
        romanization_profile = DEFAULT_ROMANIZATION_PROFILE

    preset_names = list_json_names(generator.PRESETS_DIR)

    if not preset_names:
        st.error("No preset files found. Add JSON files to presets/ and reload.")
        st.stop()

    preset_notice = st.session_state.pop("preset_notice", None)
    if preset_notice:
        st.success(preset_notice)

    latest_inventory = st.session_state.get("last_inventory")
    latest_language_name = st.session_state.get("last_language_name", "GeneratedLanguage")
    latest_generated_at = st.session_state.get("last_generated_at")
    output_dir_label = st.session_state.get("last_output_dir", "(unknown)")
    generated_time_label = f" at {latest_generated_at}" if latest_generated_at else ""

    status_col, display_col = st.columns([2.2, 1.0], gap="large")
    with status_col:
        st.markdown("### Session Status")
        if latest_inventory:
            vowels = latest_inventory.get("vowels", []) if isinstance(latest_inventory, dict) else []
            consonants = latest_inventory.get("consonants", []) if isinstance(latest_inventory, dict) else []
            st.caption(f"Active language: {latest_language_name}")
            st.caption(f"{len(vowels)} vowels, {len(consonants)} consonants.")
            st.caption(f"Latest files written to: {output_dir_label}{generated_time_label}")
        else:
            st.info("No language generated yet. Use the Build tab to start.")

    with display_col:
        st.markdown("### Display")
        romanization_profile = st.selectbox(
            "Romanization profile",
            options=list(ROMANIZATION_PROFILES.keys()),
            index=list(ROMANIZATION_PROFILES.keys()).index(romanization_profile)
            if romanization_profile in ROMANIZATION_PROFILES
            else 0,
            key="romanization_profile",
            help="Display-only: how IPA renders to sound-like text.",
        )

    tab_build, tab_review, tab_samples, tab_lexicon, tab_export = st.tabs(
        ["1. Build", "2. Review", "3. Samples", "4. Lexicon", "5. Export"]
    )

    with tab_build:
        st.markdown('<div class="section-kicker">Step 1</div>', unsafe_allow_html=True)
        st.subheader("Configure and Generate")

        controls_col, run_col = st.columns([1.8, 1.2], gap="large")
        weights: List[float] = []
        with controls_col:
            selected_presets = st.multiselect(
                "Presets to mix",
                options=preset_names,
                default=default_preset_selection(preset_names),
                help="Pick one or more source inventories.",
            )

            if selected_presets:
                st.markdown("**Preset weights**")
                default_weight = round(1.0 / len(selected_presets), 2)
                for preset_name in selected_presets:
                    weight = st.slider(
                        f"{preset_name} weight",
                        min_value=0.0,
                        max_value=1.0,
                        value=default_weight,
                        step=0.05,
                        key=f"weight_{preset_name}",
                        help="Relative influence of this preset in the mix.",
                    )
                    weights.append(weight)

            random_weight = st.slider(
                "Random weight (master pool)",
                min_value=0.0,
                max_value=1.0,
                value=0.15,
                step=0.05,
                help="Extra randomness sampled from the master preset.",
            )

            master_default = preset_names.index("random_master") if "random_master" in preset_names else 0
            master_preset = st.selectbox(
                "Master preset for random picks",
                options=preset_names,
                index=master_default,
                help="Source inventory used when random weight is above zero.",
            )

            st.caption("Sound-change rules are handled in the Language Family workflow.")

        with run_col:
            st.markdown("**Output settings**")
            language_name = st.text_input(
                "Generated language name",
                value="ProtoLanguage",
                help="Used for export filenames and display.",
            )
            output_dir_value = st.text_input(
                "Output folder",
                value="outputs/ui_run",
                help="Where JSON + CSV exports are written.",
            )
            use_seed = st.checkbox(
                "Use fixed random seed",
                value=False,
                help="Keep results reproducible between runs.",
            )
            seed_value = st.number_input(
                "Seed value",
                min_value=0,
                max_value=2_147_483_647,
                value=42,
                step=1,
                disabled=not use_seed,
                help="Only used when fixed seed is enabled.",
            )
            generate = st.button(
                "Generate Inventory",
                type="primary",
                use_container_width=True,
                help="Mix presets and create a new inventory snapshot.",
            )

            st.caption(
                "Tip: keep a fixed seed while exploring, then save successful inventories as presets."
            )

        total_weight = sum(weights) + (random_weight if random_weight > 0 else 0.0)
        render_mix_metrics(
            selected_presets=selected_presets,
            random_weight=random_weight,
            total_weight=total_weight,
        )

        with st.expander("Source inventory reference", expanded=False):
            render_mix_reference_panel(
                selected_presets=selected_presets,
                weights=weights,
                random_weight=random_weight,
                master_preset=master_preset,
                profile_name=romanization_profile,
            )

        st.divider()
        render_phoible_importer()

        if generate:
            if not selected_presets:
                st.error("Pick at least one preset before generating.")
            elif total_weight <= 0:
                st.error("At least one preset/random weight must be greater than zero.")
            else:
                try:
                    if use_seed:
                        random.seed(int(seed_value))

                    mixed_inventory = generator.mix_inventories(
                        preset_names=selected_presets,
                        weights=weights,
                        random_weight=random_weight,
                        master_preset_name=master_preset,
                    )

                    output_dir = resolve_output_dir(output_dir_value)
                    generator.save_inventory_as_json(mixed_inventory, str(output_dir), language_name)
                    generator.save_inventory_as_cldf(mixed_inventory, str(output_dir), language_name)

                    st.session_state["last_inventory"] = mixed_inventory
                    st.session_state["last_language_name"] = language_name
                    st.session_state["last_output_dir"] = str(output_dir)
                    st.session_state["last_rule_sets"] = []
                    st.session_state["last_generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.pop("sample_words", None)
                    st.session_state.pop("sample_sentences", None)
                    st.session_state.pop("sample_language_model", None)

                    st.success(f"Generated '{language_name}' and saved files to {output_dir}")
                except Exception as exc:  # pragma: no cover - UI safety net
                    st.exception(exc)

    latest_inventory = st.session_state.get("last_inventory")
    latest_language_name = st.session_state.get("last_language_name", "GeneratedLanguage")
    latest_generated_at = st.session_state.get("last_generated_at")

    with tab_review:
        st.markdown('<div class="section-kicker">Step 2</div>', unsafe_allow_html=True)
        st.subheader("Review Latest Result")
        if not latest_inventory:
            st.info("Generate a language first to review its inventory.")
        else:
            model = st.session_state.get("sample_language_model")
            lexicon_count: Optional[int] = None
            if isinstance(model, dict):
                lexicon = model.get("lexicon", [])
                if isinstance(lexicon, list):
                    lexicon_count = len(lexicon)
            render_inventory_metrics(latest_inventory, lexicon_count=lexicon_count)
            output_dir_label = st.session_state.get("last_output_dir", "(unknown)")
            generated_time_label = f" at {latest_generated_at}" if latest_generated_at else ""
            st.caption(f"Latest files were written to: {output_dir_label}{generated_time_label}")
            st.caption(
                f"Sound-like notes are approximation helpers; IPA remains canonical. "
                f"Profile: {romanization_profile}."
            )
            st.caption("Example column is intentionally blank for now (ready for your later notes).")
            def _auto_name_single() -> None:
                suggested = suggest_language_name(model, romanization_profile)
                if suggested:
                    st.session_state["single_language_name"] = suggested
                    st.session_state["last_language_name"] = suggested
                    st.session_state["single_language_name_notice"] = f"Generated name: {suggested}"
                else:
                    st.session_state["single_language_name_notice"] = (
                        "Generate a lexicon first (Samples tab) to auto-name this language."
                    )

            name_cols = st.columns([3, 1, 1])
            with name_cols[0]:
                rename_value = st.text_input(
                    "Language name",
                    value=latest_language_name,
                    key="single_language_name",
                    help="Rename this language for exports and displays.",
                )
            with name_cols[1]:
                if st.button(
                    "Save name",
                    key="single_language_name_save",
                    help="Update the display name for this session.",
                ):
                    if rename_value.strip():
                        st.session_state["last_language_name"] = rename_value.strip()
                        st.success("Language name updated.")
                        st.rerun()
            with name_cols[2]:
                st.button(
                    "Auto-name",
                    key="single_language_name_auto",
                    help="Generate a language name from the lexicon.",
                    on_click=_auto_name_single,
                )
            notice = st.session_state.pop("single_language_name_notice", None)
            if notice:
                st.info(notice)
            col_a, col_b = st.columns(2)
            with col_a:
                display_segment_table(
                    "Vowels",
                    latest_inventory.get("vowels", []),
                    profile_name=romanization_profile,
                    representation_values={
                        segment: float(value)
                        for segment, value in latest_inventory.get("vowels_representation", {}).items()
                    },
                )
            with col_b:
                display_segment_table(
                    "Consonants",
                    latest_inventory.get("consonants", []),
                    profile_name=romanization_profile,
                    representation_values={
                        segment: float(value)
                        for segment, value in latest_inventory.get("consonants_representation", {}).items()
                    },
                )
            st.markdown("**Language notes**")
            st.text_area(
                "Description / reminders",
                value=st.session_state.get("language_notes", ""),
                key="language_notes",
                height=140,
                placeholder="Add any notes you want to remember about this language.",
                help="Private notes saved into snapshots.",
            )

    with tab_samples:
        st.markdown('<div class="section-kicker">Step 3</div>', unsafe_allow_html=True)
        st.subheader("Generate Samples")
        if not latest_inventory:
            st.info("Generate a language first to build lexicon samples.")
        else:
            st.caption(
                "Generate lexicon-backed word and sentence samples from this inventory. "
                "The same generated lexicon powers both views."
            )

            style_names = list(STYLE_PRESETS.keys())
            concept_list_names = list(CONCEPT_LIST_PRESETS.keys())
            grammar_profile_names = list(GRAMMAR_PROFILES.keys())

            profile_col_1, profile_col_2, profile_col_3 = st.columns(3)
            with profile_col_1:
                selected_style = st.selectbox(
                    "Phonotactic style",
                    options=style_names,
                    index=0,
                    key="sample_style_preset",
                    help="Controls syllable-shape tendencies for generated forms.",
                )
            with profile_col_2:
                selected_concept_list = st.selectbox(
                    "Concept list",
                    options=concept_list_names,
                    index=0,
                    key="sample_concept_list",
                    help="Controls which core meanings receive generated roots.",
                )
            with profile_col_3:
                selected_grammar_profile = st.selectbox(
                    "Grammar profile",
                    options=grammar_profile_names,
                    index=0,
                    key="sample_grammar_profile",
                    help="Controls clause order and particle behavior in sentences.",
                )

            st.caption(f"Style guide: {STYLE_PRESETS[selected_style]['description']}")
            st.caption(f"Concept list: {CONCEPT_LIST_PRESETS[selected_concept_list]['description']}")
            st.caption(f"Grammar profile: {GRAMMAR_PROFILES[selected_grammar_profile]['description']}")
            st.caption("Word rows include every concept-list root with meaning tags + part-of-speech labels.")
            concept_entries_raw = CONCEPT_LIST_PRESETS[selected_concept_list].get("entries", [])
            concept_entry_count = len(concept_entries_raw) if isinstance(concept_entries_raw, (list, tuple)) else 0
            grammar_particles_raw = GRAMMAR_PROFILES[selected_grammar_profile].get("particle_inventory", [])
            grammar_particle_count = (
                len(grammar_particles_raw) if isinstance(grammar_particles_raw, (list, tuple)) else 0
            )
            st.caption(
                f"Current setup: {concept_entry_count} concept entries, "
                f"{grammar_particle_count} particle slots."
            )

            with st.expander("Phonotactics tuning (beginner-friendly controls)", expanded=False):
                default_initial_ng_penalty = float(
                    nested_value(DEFAULT_PHONOTACTIC_PROFILE, ["soft_constraints", "initial_velar_nasal_penalty"], 4.0)
                )
                default_candidate_count = int(
                    nested_value(DEFAULT_PHONOTACTIC_PROFILE, ["candidate_selection", "candidates_per_word"], 7)
                )
                default_temperature = float(
                    nested_value(DEFAULT_PHONOTACTIC_PROFILE, ["candidate_selection", "temperature"], 0.82)
                )
                default_harmony_penalty = float(
                    nested_value(DEFAULT_PHONOTACTIC_PROFILE, ["co_occurrence", "harmony_penalty"], 0.32)
                )
                default_morph_enabled = bool(
                    nested_value(DEFAULT_PHONOTACTIC_PROFILE, ["morphology", "enabled"], True)
                )
                default_noun_suffix_rate = float(
                    nested_value(DEFAULT_PHONOTACTIC_PROFILE, ["morphology", "suffix_rate_by_pos", "N"], 0.28)
                )
                default_verb_suffix_rate = float(
                    nested_value(DEFAULT_PHONOTACTIC_PROFILE, ["morphology", "suffix_rate_by_pos", "V"], 0.38)
                )
                default_prefix_rate = float(
                    nested_value(DEFAULT_PHONOTACTIC_PROFILE, ["morphology", "prefix_rate_by_pos", "default"], 0.06)
                )

                tuning_col_1, tuning_col_2 = st.columns(2)
                with tuning_col_1:
                    ui_initial_ng_penalty = st.slider(
                        "Initial velar nasal penalty",
                        min_value=0.0,
                        max_value=8.0,
                        value=default_initial_ng_penalty,
                        step=0.1,
                        key="phon_ui_initial_ng_penalty",
                        help="Controls how often words start with ŋ (ng). Higher = rarer; 0 = allow freely.",
                    )
                    ui_candidate_count = st.slider(
                        "Candidates per word",
                        min_value=1,
                        max_value=24,
                        value=default_candidate_count,
                        step=1,
                        key="phon_ui_candidates_per_word",
                        help="Generate several options and pick the best. Higher = smoother words but slower.",
                    )
                    ui_temperature = st.slider(
                        "Candidate selection temperature",
                        min_value=0.1,
                        max_value=2.5,
                        value=default_temperature,
                        step=0.01,
                        key="phon_ui_temperature",
                        help="Lower = stricter/cleaner picks. Higher = more variety.",
                    )
                    ui_harmony_penalty = st.slider(
                        "Vowel disharmony penalty",
                        min_value=0.0,
                        max_value=2.0,
                        value=default_harmony_penalty,
                        step=0.05,
                        key="phon_ui_harmony_penalty",
                        help="Higher values discourage mixing front/back vowels within a word.",
                    )
                with tuning_col_2:
                    ui_morph_enabled = st.checkbox(
                        "Enable morphology-lite affixes",
                        value=default_morph_enabled,
                        key="phon_ui_morph_enabled",
                        help="Adds small prefixes/suffixes so related roots feel like a family.",
                    )
                    ui_prefix_rate = st.slider(
                        "General prefix rate",
                        min_value=0.0,
                        max_value=0.8,
                        value=default_prefix_rate,
                        step=0.01,
                        key="phon_ui_prefix_rate",
                        help="Chance that a word gets a short prefix.",
                    )
                    ui_noun_suffix_rate = st.slider(
                        "Noun suffix rate",
                        min_value=0.0,
                        max_value=0.95,
                        value=default_noun_suffix_rate,
                        step=0.01,
                        key="phon_ui_noun_suffix_rate",
                        help="Chance that nouns get a short suffix.",
                    )
                    ui_verb_suffix_rate = st.slider(
                        "Verb suffix rate",
                        min_value=0.0,
                        max_value=0.95,
                        value=default_verb_suffix_rate,
                        step=0.01,
                        key="phon_ui_verb_suffix_rate",
                        help="Chance that verbs get a short suffix.",
                    )

                advanced_override_text = st.text_area(
                    "Advanced override JSON (optional)",
                    value=st.session_state.get("phon_ui_advanced_override_json", ""),
                    key="phon_ui_advanced_override_json",
                    height=140,
                    help="Paste an override object; it merges on top of the sliders.",
                )
                st.caption("Use this only if you want to go beyond the sliders.")
                st.code(
                    '{"segment_slot_weights": {"word_initial_onset": {"ŋ": 0.02}}, "cluster": {"max_attempts": 18}}',
                    language="json",
                )

            phonotactic_overrides: Dict[str, Any] = {
                "candidate_selection": {
                    "candidates_per_word": int(ui_candidate_count),
                    "temperature": float(ui_temperature),
                },
                "soft_constraints": {
                    "initial_velar_nasal_penalty": float(ui_initial_ng_penalty),
                },
                "co_occurrence": {
                    "enabled": True,
                    "harmony_penalty": float(ui_harmony_penalty),
                },
                "morphology": {
                    "enabled": bool(ui_morph_enabled),
                    "prefix_rate_by_pos": {
                        "N": float(ui_prefix_rate),
                        "V": float(ui_prefix_rate),
                        "ADJ": float(ui_prefix_rate),
                        "default": float(ui_prefix_rate),
                    },
                    "suffix_rate_by_pos": {
                        "N": float(ui_noun_suffix_rate),
                        "V": float(ui_verb_suffix_rate),
                        "ADJ": float((ui_noun_suffix_rate + ui_verb_suffix_rate) / 2.0),
                        "default": float((ui_noun_suffix_rate + ui_verb_suffix_rate) / 2.0),
                    },
                },
            }
            advanced_override_dict, advanced_override_error = parse_override_json(advanced_override_text)
            if advanced_override_error:
                st.error(advanced_override_error)
            else:
                phonotactic_overrides = deep_merge_dict(phonotactic_overrides, advanced_override_dict)
            st.session_state["phonotactic_overrides"] = phonotactic_overrides

            validation_report = validate_generation_config()
            validation_errors = validation_report.get("errors", [])
            validation_warnings = validation_report.get("warnings", [])
            sample_generation_disabled = bool(validation_errors or advanced_override_error)
            if validation_errors:
                st.error(
                    "Sample generation configuration has validation errors. "
                    "Fix profile definitions before generating."
                )
                with st.expander("Show generation-config errors", expanded=False):
                    for issue in validation_errors:
                        st.write(f"- {issue}")
            elif validation_warnings:
                with st.expander("Generation-config warnings", expanded=False):
                    for issue in validation_warnings:
                        st.write(f"- {issue}")

            sample_controls_left, sample_controls_right = st.columns(2)
            with sample_controls_left:
                sample_syllable_range = st.slider(
                    "Syllables per generated word",
                    min_value=1,
                    max_value=5,
                    value=(1, 3),
                    key="sample_syllable_range",
                    help="Range of syllables per root in the generated lexicon.",
                )
                st.caption(f"Generate Word Samples now returns all {concept_entry_count} concept entries.")
            with sample_controls_right:
                sample_sentence_count = st.number_input(
                    "Sentence samples per run",
                    min_value=1,
                    max_value=30,
                    value=6,
                    step=1,
                    key="sample_sentence_count",
                    help="How many sentences to generate per click.",
                )
                sample_words_range = st.slider(
                    "Words per generated sentence",
                    min_value=2,
                    max_value=14,
                    value=(4, 8),
                    key="sample_sentence_words_range",
                    help="Range of word counts per sentence.",
                )

            show_syllable_breaks = st.checkbox(
                "Show syllable separators (.)",
                value=False,
                key="sample_show_syllable_breaks",
                help="Insert dots between syllables in IPA output.",
            )
            show_segment_separators = st.checkbox(
                "Show segment separators (-) in sound-like text",
                value=False,
                key="sample_show_segment_separators",
                help="Insert hyphens between segments in the sound-like column.",
            )
            syllable_separator = "." if show_syllable_breaks else ""

            samples_button_col_1, samples_button_col_2, samples_button_col_3 = st.columns(3)
            with samples_button_col_1:
                generate_word_samples = st.button(
                    "Generate Word Samples",
                    key="generate_word_samples",
                    disabled=sample_generation_disabled,
                    help="Build or rebuild the lexicon and show word entries.",
                )
            with samples_button_col_2:
                generate_sentence_samples = st.button(
                    "Generate Sentence Samples",
                    key="generate_sentence_samples",
                    disabled=sample_generation_disabled,
                    help="Generate new sentence samples from the current lexicon.",
                )
            with samples_button_col_3:
                generate_both_samples = st.button(
                    "Generate Both",
                    key="generate_both_samples",
                    disabled=sample_generation_disabled,
                    help="Generate word + sentence samples together.",
                )

            latest_vowels = latest_inventory.get("vowels", [])
            latest_consonants = latest_inventory.get("consonants", [])
            cached_model = st.session_state.get("sample_language_model")
            model_is_current = model_matches(
                cached_model,
                vowels=latest_vowels,
                consonants=latest_consonants,
                syllable_range=sample_syllable_range,
                syllable_separator=syllable_separator,
                style_name=selected_style,
                concept_list_name=selected_concept_list,
                grammar_profile_name=selected_grammar_profile,
                phonotactic_profile_overrides=phonotactic_overrides,
            )

            if model_is_current:
                model_stats = language_model_summary(cached_model)
                st.caption(
                    f"Current lexicon model: {model_stats['root_entries']} roots + "
                    f"{model_stats['particle_entries']} particles "
                    f"({model_stats['total_entries']} total entries)."
                )
            elif cached_model:
                st.info(
                    "Sample settings changed since the last generation. "
                    "Generate again to rebuild the shared lexicon model."
                )

            generate_any_samples = generate_word_samples or generate_sentence_samples or generate_both_samples
            if generate_any_samples and not sample_generation_disabled:
                force_rebuild = generate_word_samples or generate_both_samples or not model_is_current
                cached_model = ensure_language_model(
                    cached_model=cached_model,
                    vowels=latest_vowels,
                    consonants=latest_consonants,
                    syllable_range=sample_syllable_range,
                    syllable_separator=syllable_separator,
                    style_name=selected_style,
                    concept_list_name=selected_concept_list,
                    grammar_profile_name=selected_grammar_profile,
                    phonotactic_profile_overrides=phonotactic_overrides,
                    force_rebuild=force_rebuild,
                )
                st.session_state["sample_language_model"] = cached_model

            if (generate_word_samples or generate_both_samples) and not sample_generation_disabled:
                st.session_state["sample_words"] = build_sample_words(
                    latest_vowels,
                    latest_consonants,
                    sample_count=max(1, int(concept_entry_count)),
                    syllable_range=sample_syllable_range,
                    syllable_separator=syllable_separator,
                    style_name=selected_style,
                    concept_list_name=selected_concept_list,
                    grammar_profile_name=selected_grammar_profile,
                    language_model=cached_model,
                    phonotactic_profile_overrides=phonotactic_overrides,
                )
                if not generate_both_samples:
                    st.session_state.pop("sample_sentences", None)

            if (generate_sentence_samples or generate_both_samples) and not sample_generation_disabled:
                st.session_state["sample_sentences"] = build_sample_sentences(
                    latest_vowels,
                    latest_consonants,
                    sample_count=int(sample_sentence_count),
                    syllable_range=sample_syllable_range,
                    words_range=sample_words_range,
                    syllable_separator=syllable_separator,
                    style_name=selected_style,
                    concept_list_name=selected_concept_list,
                    grammar_profile_name=selected_grammar_profile,
                    language_model=cached_model,
                    phonotactic_profile_overrides=phonotactic_overrides,
                )

            sample_words = st.session_state.get("sample_words", [])
            sample_sentences = st.session_state.get("sample_sentences", [])

            if sample_words:
                st.markdown("**Word samples**")
                word_rows = [
                    {
                        "Entry": str(word.get("id", "")) if isinstance(word, dict) else "",
                        "IPA": str(word.get("ipa", "")) if isinstance(word, dict) else str(word),
                        "Sound-like": ipa_text_to_sound_like(
                            str(word.get("ipa", "")) if isinstance(word, dict) else str(word),
                            use_segment_separators=show_segment_separators,
                            profile_name=romanization_profile,
                        ),
                        "Gloss": str(word.get("gloss", "")) if isinstance(word, dict) else "",
                        "Meaning tag": str(word.get("meaning", "")) if isinstance(word, dict) else "",
                        "Part of speech": str(word.get("part_of_speech", "")) if isinstance(word, dict) else "",
                        "Source": str(word.get("source", "")) if isinstance(word, dict) else "",
                        "Re-roll": False,
                    }
                    for word in sample_words
                ]
                edited_word_rows = st.data_editor(
                    word_rows,
                    hide_index=True,
                    use_container_width=True,
                    key="sample_word_table",
                    column_config={
                        "Re-roll": st.column_config.CheckboxColumn(
                            "Re-roll",
                            help="Select one or more words to re-generate.",
                            default=False,
                        ),
                        "Entry": st.column_config.TextColumn("Entry", disabled=True, help="Stable entry ID."),
                        "IPA": st.column_config.TextColumn("IPA", disabled=True, help="Canonical IPA form."),
                        "Sound-like": st.column_config.TextColumn(
                            "Sound-like", disabled=True, help="Approximate romanization."
                        ),
                        "Gloss": st.column_config.TextColumn("Gloss", disabled=True, help="Gloss text."),
                        "Meaning tag": st.column_config.TextColumn(
                            "Meaning tag", disabled=True, help="Semantic label."
                        ),
                        "Part of speech": st.column_config.TextColumn(
                            "Part of speech", disabled=True, help="Grammatical category."
                        ),
                        "Source": st.column_config.TextColumn("Source", disabled=True, help="Entry origin."),
                    },
                )

                if hasattr(edited_word_rows, "to_dict"):
                    edited_word_rows = edited_word_rows.to_dict(orient="records")
                if not isinstance(edited_word_rows, list):
                    edited_word_rows = []

                selected_rerolls = [
                    str(row.get("Entry", "")).strip()
                    for row in edited_word_rows
                    if isinstance(row, dict) and row.get("Re-roll") is True
                ]
                reroll_button = st.button(
                    f"Re-roll {len(selected_rerolls)} selected word(s)",
                    disabled=sample_generation_disabled or not selected_rerolls,
                    help="Regenerate IPA forms for the selected word entries.",
                )
                if reroll_button:
                    model = st.session_state.get("sample_language_model")
                    if not isinstance(model, dict):
                        st.error("No active lexicon model found. Generate samples first.")
                    else:
                        for entry_id in selected_rerolls:
                            reroll_lexicon_entry(
                                model,
                                entry_id=entry_id,
                                phonotactic_profile_overrides=phonotactic_overrides,
                            )

                        st.session_state["sample_language_model"] = model
                        st.session_state["sample_words"] = build_sample_words(
                            latest_vowels,
                            latest_consonants,
                            sample_count=max(1, int(concept_entry_count)),
                            syllable_range=sample_syllable_range,
                            syllable_separator=syllable_separator,
                            style_name=selected_style,
                            concept_list_name=selected_concept_list,
                            grammar_profile_name=selected_grammar_profile,
                            language_model=model,
                            phonotactic_profile_overrides=phonotactic_overrides,
                        )
                        st.session_state.pop("sample_sentences", None)
                        st.rerun()
            else:
                st.info("No word samples yet. Click 'Generate Word Samples' or 'Generate Both'.")

            if sample_sentences:
                st.markdown("**Sentence samples**")
                st.dataframe(
                    [
                        {
                            "IPA": str(sentence.get("ipa", "")) if isinstance(sentence, dict) else str(sentence),
                            "Gloss": str(sentence.get("gloss", "")) if isinstance(sentence, dict) else "",
                            "Template": str(sentence.get("template", "")) if isinstance(sentence, dict) else "",
                            "Sound-like": ipa_text_to_sound_like(
                                str(sentence.get("ipa", "")) if isinstance(sentence, dict) else str(sentence),
                                use_segment_separators=show_segment_separators,
                                profile_name=romanization_profile,
                            ),
                        }
                        for sentence in sample_sentences
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("No sentence samples yet. Click 'Generate Sentence Samples' or 'Generate Both'.")

            st.divider()
            st.caption("Lexicon curation lives in the Lexicon tab for a focused workflow.")

    with tab_lexicon:
        st.markdown('<div class="section-kicker">Step 4</div>', unsafe_allow_html=True)
        st.subheader("Lexicon Builder and Overview")
        if not latest_inventory:
            st.info("Generate a language first to build its lexicon.")
        else:
            st.caption(
                "Create custom words and curate the full lexicon. "
                "Custom entries persist across sample runs."
            )
            selected_style = st.session_state.get("sample_style_preset", DEFAULT_STYLE_PRESET)
            selected_concept_list = st.session_state.get("sample_concept_list", DEFAULT_CONCEPT_LIST)
            selected_grammar_profile = st.session_state.get("sample_grammar_profile", DEFAULT_GRAMMAR_PROFILE)
            sample_syllable_range = st.session_state.get("sample_syllable_range", (1, 3))
            if isinstance(sample_syllable_range, list):
                sample_syllable_range = tuple(sample_syllable_range)
            show_syllable_breaks = bool(st.session_state.get("sample_show_syllable_breaks", False))
            show_segment_separators = bool(st.session_state.get("sample_show_segment_separators", False))
            syllable_separator = "." if show_syllable_breaks else ""
            phonotactic_overrides = st.session_state.get("phonotactic_overrides", {})

            advanced_override_text = st.session_state.get("phon_ui_advanced_override_json", "")
            _, advanced_override_error = parse_override_json(advanced_override_text)
            validation_report = validate_generation_config()
            validation_errors = validation_report.get("errors", [])
            sample_generation_disabled = bool(validation_errors or advanced_override_error)
            if validation_errors:
                st.error("Fix generation profile errors before creating lexicon entries.")
            if advanced_override_error:
                st.error(advanced_override_error)

            latest_vowels = latest_inventory.get("vowels", [])
            latest_consonants = latest_inventory.get("consonants", [])
            cached_model = st.session_state.get("sample_language_model")
            model_is_current = model_matches(
                cached_model,
                vowels=latest_vowels,
                consonants=latest_consonants,
                syllable_range=sample_syllable_range,
                syllable_separator=syllable_separator,
                style_name=selected_style,
                concept_list_name=selected_concept_list,
                grammar_profile_name=selected_grammar_profile,
                phonotactic_profile_overrides=phonotactic_overrides,
            )
            if cached_model:
                model_stats = language_model_summary(cached_model)
                st.caption(
                    f"Current lexicon model: {model_stats['root_entries']} roots + "
                    f"{model_stats['particle_entries']} particles "
                    f"({model_stats['total_entries']} total entries)."
                )
            if cached_model and not model_is_current:
                st.info("Sample settings changed. Rebuild the lexicon model if you want fresh roots.")

            if st.button(
                "Rebuild lexicon model",
                key="lexicon_rebuild_model",
                disabled=sample_generation_disabled,
                help="Re-roll roots/particles using current sample settings (custom entries are preserved).",
            ):
                cached_model = ensure_language_model(
                    cached_model=cached_model,
                    vowels=latest_vowels,
                    consonants=latest_consonants,
                    syllable_range=sample_syllable_range,
                    syllable_separator=syllable_separator,
                    style_name=selected_style,
                    concept_list_name=selected_concept_list,
                    grammar_profile_name=selected_grammar_profile,
                    phonotactic_profile_overrides=phonotactic_overrides,
                    force_rebuild=True,
                )
                st.session_state["sample_language_model"] = cached_model
                st.session_state.pop("sample_words", None)
                st.session_state.pop("sample_sentences", None)
                st.success("Lexicon model rebuilt.")
                st.rerun()

            lexicon_model = cached_model
            if not isinstance(lexicon_model, dict):
                lexicon_model = ensure_language_model(
                    cached_model=None,
                    vowels=latest_vowels,
                    consonants=latest_consonants,
                    syllable_range=sample_syllable_range,
                    syllable_separator=syllable_separator,
                    style_name=selected_style,
                    concept_list_name=selected_concept_list,
                    grammar_profile_name=selected_grammar_profile,
                    phonotactic_profile_overrides=phonotactic_overrides,
                    force_rebuild=True,
                )
                st.session_state["sample_language_model"] = lexicon_model

            pos_order = ["N", "V", "ADJ", "ADV", "PRON", "NUM", "DEM", "ADP", "NEG", "CONJ", "INT", "PART"]
            pos_options = [pos for pos in pos_order if pos in POS_LABELS]
            pos_options.extend([pos for pos in POS_LABELS.keys() if pos not in pos_options])

            def format_pos_label(value: str) -> str:
                label = POS_LABELS.get(value, value)
                return f"{label} ({value})" if value and label != value else label

            st.divider()
            st.markdown("**Custom word builder**")
            builder_col_1, builder_col_2 = st.columns(2)
            with builder_col_1:
                meaning_tag = st.text_input(
                    "Meaning tag",
                    key="custom_word_meaning",
                    help="Short semantic label used for search and glossing.",
                )
                selected_pos = st.selectbox(
                    "Part of speech",
                    options=pos_options,
                    format_func=format_pos_label,
                    key="custom_word_pos",
                    help="Grammatical category for the new word.",
                )
                auto_gloss = st.checkbox(
                    "Auto gloss",
                    value=True,
                    key="custom_word_auto_gloss",
                    help="Automatically generate a gloss from the meaning tag.",
                )
                gloss_input = st.text_input(
                    "Gloss",
                    key="custom_word_gloss",
                    disabled=auto_gloss,
                    help="Short gloss used in sentence samples (manual override).",
                )
                gloss_value = ""
                if auto_gloss and meaning_tag.strip():
                    gloss_value = concept_gloss(meaning_tag.strip(), selected_pos)
                    st.caption(f"Gloss: {gloss_value}")
                elif gloss_input.strip():
                    gloss_value = gloss_input.strip()

            with builder_col_2:
                mode_label = st.radio(
                    "Build mode",
                    options=["Random", "Use existing root"],
                    horizontal=True,
                    key="custom_word_mode",
                    help="Random builds from phonotactics; rooted derives from an existing entry.",
                )
                custom_meta: Dict[str, Any] = {}
                root_ids: List[str] = []
                root_label_map: Dict[str, str] = {}
                if mode_label == "Random":
                    custom_range = st.slider(
                        "Syllables per word",
                        min_value=1,
                        max_value=5,
                        value=sample_syllable_range,
                        key="custom_word_random_range",
                        help="Total syllable range for the new word.",
                    )
                    custom_meta = {"mode": "random", "syllable_range": [int(custom_range[0]), int(custom_range[1])]}
                else:
                    lexicon_entries = lexicon_model.get("lexicon", []) if isinstance(lexicon_model, dict) else []
                    for entry in lexicon_entries:
                        if not isinstance(entry, dict):
                            continue
                        entry_id = str(entry.get("id", "")).strip()
                        pos = str(entry.get("pos", "")).strip()
                        if not entry_id or entry_id.startswith("PART:") or pos == "PART":
                            continue
                        meaning = str(entry.get("meaning", "")).strip()
                        label = f"{entry_id} · {meaning}" if meaning else entry_id
                        root_ids.append(entry_id)
                        root_label_map[entry_id] = label
                    selected_root = st.selectbox(
                        "Root to derive from",
                        options=root_ids if root_ids else ["(none)"],
                        format_func=lambda value: root_label_map.get(value, value),
                        key="custom_word_root_id",
                        disabled=not root_ids,
                        help="Pick an existing root to attach affixes to.",
                    )
                    if not root_ids:
                        st.warning("No eligible roots found to derive from.")
                        selected_root = ""

                    affix_mode_label = st.selectbox(
                        "Affix mode",
                        options=["Auto", "Prefix", "Suffix", "Both"],
                        key="custom_word_affix_mode",
                        help="Where the generated affix should attach.",
                    )
                    affix_range = st.slider(
                        "Affix syllables",
                        min_value=1,
                        max_value=4,
                        value=(1, 1),
                        key="custom_word_affix_range",
                        help="Syllable range for the affix portion.",
                    )
                    custom_meta = {
                        "mode": "rooted",
                        "root_id": selected_root,
                        "affix_mode": affix_mode_label.lower(),
                        "affix_syllable_range": [int(affix_range[0]), int(affix_range[1])],
                    }

            preview_state = st.session_state.get("custom_word_preview")
            can_generate = bool(meaning_tag.strip()) and not sample_generation_disabled
            if mode_label == "Use existing root":
                can_generate = can_generate and bool(custom_meta.get("root_id"))

            generate_candidate = st.button(
                "Generate candidate",
                key="custom_word_generate",
                disabled=not can_generate,
                help="Generate a new candidate form using the current settings.",
            )
            if generate_candidate:
                ipa = generate_custom_word_form(
                    language_model=lexicon_model,
                    custom_meta=custom_meta,
                    phonotactic_profile_overrides=phonotactic_overrides,
                )
                if not ipa:
                    st.error("Could not generate a candidate. Try adjusting the settings.")
                else:
                    st.session_state["custom_word_preview"] = {
                        "ipa": ipa,
                        "custom_meta": custom_meta,
                        "meaning": meaning_tag.strip(),
                        "pos": selected_pos,
                        "gloss": gloss_value,
                    }
                    preview_state = st.session_state["custom_word_preview"]

            if isinstance(preview_state, dict) and preview_state.get("ipa"):
                preview_ipa = str(preview_state.get("ipa", ""))
                preview_col_1, preview_col_2 = st.columns(2)
                with preview_col_1:
                    st.markdown(f"**IPA**: `{preview_ipa}`")
                with preview_col_2:
                    st.markdown(
                        f"**Sound-like**: `{ipa_text_to_sound_like(preview_ipa, use_segment_separators=False, profile_name=romanization_profile)}`"
                    )

            add_disabled = not (isinstance(preview_state, dict) and preview_state.get("ipa")) or not meaning_tag.strip()
            if st.button(
                "Add to lexicon",
                key="custom_word_add",
                disabled=add_disabled,
                help="Persist the previewed word into the lexicon.",
            ):
                entry = build_custom_entry(
                    language_model=lexicon_model,
                    meaning=meaning_tag.strip(),
                    pos=selected_pos,
                    gloss=gloss_value,
                    custom_meta=preview_state.get("custom_meta") if isinstance(preview_state, dict) else None,
                    ipa_override=preview_state.get("ipa") if isinstance(preview_state, dict) else None,
                    phonotactic_profile_overrides=phonotactic_overrides,
                )
                lexicon = lexicon_model.get("lexicon", [])
                if not isinstance(lexicon, list):
                    lexicon = []
                lexicon.append(entry)
                lexicon_model["lexicon"] = lexicon
                lexicon_model = rebuild_indices(lexicon_model)
                st.session_state["sample_language_model"] = lexicon_model
                st.session_state["custom_word_preview"] = None
                st.session_state.pop("sample_sentences", None)
                st.success("Custom entry added to the lexicon.")
                st.rerun()

            st.divider()
            st.markdown("**Lexicon overview**")

            lexicon_entries = lexicon_model.get("lexicon", []) if isinstance(lexicon_model, dict) else []
            if not isinstance(lexicon_entries, list):
                lexicon_entries = []

            search_term = st.text_input(
                "Search lexicon",
                key="lexicon_overview_search",
                help="Filter by ID, meaning, gloss, or IPA.",
            )

            def entry_source_label(entry: Dict[str, Any]) -> str:
                if is_custom_entry(entry):
                    return "Custom"
                entry_id = str(entry.get("id", ""))
                source = str(entry.get("source", ""))
                pos = str(entry.get("pos", ""))
                if source.startswith("concept-list:"):
                    return "Concept roots"
                if source.startswith("grammar:") or entry_id.startswith("PART:") or pos == "PART":
                    return "Particles"
                return "Other"

            source_order = ["Concept roots", "Custom", "Particles", "Other"]
            available_sources = sorted({entry_source_label(entry) for entry in lexicon_entries if isinstance(entry, dict)})
            source_options = [label for label in source_order if label in available_sources]
            selected_sources = st.multiselect(
                "Source filter",
                options=source_options if source_options else source_order,
                default=source_options,
                key="lexicon_overview_sources",
                help="Filter by entry origin.",
            )

            pos_codes = sorted(
                {
                    str(entry.get("pos", "")).strip()
                    for entry in lexicon_entries
                    if isinstance(entry, dict) and str(entry.get("pos", "")).strip()
                }
            )
            selected_pos_codes = st.multiselect(
                "Part of speech filter",
                options=pos_codes,
                default=pos_codes,
                format_func=format_pos_label,
                key="lexicon_overview_pos",
                help="Filter by grammatical category.",
            )

            def matches_search(entry: Dict[str, Any], needle: str) -> bool:
                if not needle:
                    return True
                hay = " ".join(
                    [
                        str(entry.get("id", "")),
                        str(entry.get("meaning", "")),
                        str(entry.get("gloss", "")),
                        str(entry.get("ipa", "")),
                    ]
                ).lower()
                return needle in hay

            filtered_entries: List[Dict[str, Any]] = []
            needle = search_term.strip().lower()
            for entry in lexicon_entries:
                if not isinstance(entry, dict):
                    continue
                if selected_sources and entry_source_label(entry) not in selected_sources:
                    continue
                entry_pos = str(entry.get("pos", "")).strip()
                if selected_pos_codes and entry_pos not in selected_pos_codes:
                    continue
                if not matches_search(entry, needle):
                    continue
                filtered_entries.append(entry)

            st.caption("Edits and deletions apply to all entries in this lexicon.")
            st.caption(f"Showing {len(filtered_entries)} of {len(lexicon_entries)} entries.")
            overview_rows = [
                {
                    "Entry": str(entry.get("id", "")),
                    "IPA": str(entry.get("ipa", "")),
                    "Sound-like": ipa_text_to_sound_like(
                        str(entry.get("ipa", "")),
                        use_segment_separators=show_segment_separators,
                        profile_name=romanization_profile,
                    ),
                    "Gloss": str(entry.get("gloss", "")),
                    "Meaning tag": str(entry.get("meaning", "")),
                    "POS": str(entry.get("pos", "")),
                    "Source": entry_source_label(entry),
                    "Custom": "Yes" if is_custom_entry(entry) else "No",
                    "Delete": False,
                    "Re-roll": False,
                }
                for entry in filtered_entries
            ]
            edited_overview_rows = st.data_editor(
                overview_rows,
                hide_index=True,
                use_container_width=True,
                height=520,
                key="lexicon_overview_table",
                column_config={
                    "Re-roll": st.column_config.CheckboxColumn(
                        "Re-roll",
                        default=False,
                        help="Regenerate this entry's IPA form.",
                    ),
                    "Delete": st.column_config.CheckboxColumn(
                        "Delete",
                        default=False,
                        help="Remove this entry from the lexicon.",
                    ),
                    "Entry": st.column_config.TextColumn("Entry", disabled=True, help="Stable entry ID."),
                    "IPA": st.column_config.TextColumn("IPA", disabled=True, help="Canonical IPA form."),
                    "Sound-like": st.column_config.TextColumn(
                        "Sound-like", disabled=True, help="Approximate romanization display."
                    ),
                    "Gloss": st.column_config.TextColumn("Gloss", help="Edit the gloss field."),
                    "Meaning tag": st.column_config.TextColumn("Meaning tag", help="Edit the meaning tag."),
                    "POS": st.column_config.SelectboxColumn("POS", options=pos_options, help="Edit part of speech."),
                    "Source": st.column_config.TextColumn("Source", disabled=True, help="Entry origin."),
                    "Custom": st.column_config.TextColumn("Custom", disabled=True, help="Custom entry flag."),
                },
            )

            if hasattr(edited_overview_rows, "to_dict"):
                edited_overview_rows = edited_overview_rows.to_dict(orient="records")
            if not isinstance(edited_overview_rows, list):
                edited_overview_rows = []

            entry_map = {
                str(entry.get("id", "")).strip(): entry
                for entry in lexicon_entries
                if isinstance(entry, dict)
            }
            pending_changes = False
            for row in edited_overview_rows:
                if not isinstance(row, dict):
                    continue
                row_id = str(row.get("Entry", "")).strip()
                entry = entry_map.get(row_id)
                if not entry:
                    continue
                if row.get("Delete") is True:
                    pending_changes = True
                    break
                row_meaning = str(row.get("Meaning tag", "")).strip()
                row_gloss = str(row.get("Gloss", "")).strip()
                row_pos = str(row.get("POS", "")).strip()
                if (
                    row_meaning != str(entry.get("meaning", "")).strip()
                    or row_gloss != str(entry.get("gloss", "")).strip()
                    or row_pos != str(entry.get("pos", "")).strip()
                ):
                    pending_changes = True
                    break

            apply_changes = st.button(
                "Apply edits / deletions",
                key="lexicon_overview_apply",
                disabled=sample_generation_disabled or not pending_changes,
                help="Commit edits and deletions to the lexicon.",
            )
            if apply_changes:
                delete_ids: List[str] = []
                edit_count = 0
                for row in edited_overview_rows:
                    if not isinstance(row, dict):
                        continue
                    row_id = str(row.get("Entry", "")).strip()
                    entry = entry_map.get(row_id)
                    if not entry:
                        continue
                    wants_delete = row.get("Delete") is True
                    if wants_delete:
                        delete_ids.append(row_id)
                        continue
                    row_meaning = str(row.get("Meaning tag", "")).strip()
                    row_gloss = str(row.get("Gloss", "")).strip()
                    row_pos = str(row.get("POS", "")).strip()
                    changed = False
                    if row_meaning and row_meaning != str(entry.get("meaning", "")).strip():
                        entry["meaning"] = row_meaning
                        changed = True
                    if row_gloss and row_gloss != str(entry.get("gloss", "")).strip():
                        entry["gloss"] = row_gloss
                        changed = True
                    if row_pos and row_pos in pos_options and row_pos != str(entry.get("pos", "")).strip():
                        entry["pos"] = row_pos
                        changed = True
                    if changed:
                        edit_count += 1

                if delete_ids:
                    lexicon_model["lexicon"] = [
                        entry for entry in lexicon_entries if str(entry.get("id", "")).strip() not in set(delete_ids)
                    ]
                lexicon_model = rebuild_indices(lexicon_model)
                st.session_state["sample_language_model"] = lexicon_model
                if st.session_state.get("sample_words"):
                    concept_entries_raw = CONCEPT_LIST_PRESETS[selected_concept_list].get("entries", [])
                    concept_entry_count = len(concept_entries_raw) if isinstance(concept_entries_raw, (list, tuple)) else 0
                    st.session_state["sample_words"] = build_sample_words(
                        latest_vowels,
                        latest_consonants,
                        sample_count=max(1, int(concept_entry_count)),
                        syllable_range=sample_syllable_range,
                        syllable_separator=syllable_separator,
                        style_name=selected_style,
                        concept_list_name=selected_concept_list,
                        grammar_profile_name=selected_grammar_profile,
                        language_model=lexicon_model,
                        phonotactic_profile_overrides=phonotactic_overrides,
                    )
                st.session_state.pop("sample_sentences", None)
                if edit_count or delete_ids:
                    st.success("Lexicon updates applied.")
                st.rerun()

            overview_rerolls = [
                str(row.get("Entry", "")).strip()
                for row in edited_overview_rows
                if isinstance(row, dict) and row.get("Re-roll") is True
            ]
            csv_rows = [
                {
                    "id": str(entry.get("id", "")),
                    "ipa": str(entry.get("ipa", "")),
                    "sound_like": ipa_text_to_sound_like(
                        str(entry.get("ipa", "")),
                        use_segment_separators=show_segment_separators,
                        profile_name=romanization_profile,
                    ),
                    "meaning": str(entry.get("meaning", "")),
                    "gloss": str(entry.get("gloss", "")),
                    "pos": str(entry.get("pos", "")),
                    "source": entry_source_label(entry),
                }
                for entry in filtered_entries
                if isinstance(entry, dict)
            ]
            lexicon_csv = build_lexicon_csv(csv_rows)
            st.download_button(
                label="Download lexicon CSV",
                data=lexicon_csv,
                file_name=f"{sanitize_name(latest_language_name)}_lexicon.csv",
                mime="text/csv",
                use_container_width=True,
                help="Download the filtered lexicon as CSV.",
            )
            reroll_overview_button = st.button(
                f"Re-roll {len(overview_rerolls)} selected entries",
                key="lexicon_overview_reroll",
                disabled=not overview_rerolls or sample_generation_disabled,
                help="Regenerate IPA forms for the selected entries.",
            )
            if reroll_overview_button:
                for entry_id in overview_rerolls:
                    reroll_lexicon_entry(
                        lexicon_model,
                        entry_id=entry_id,
                        phonotactic_profile_overrides=phonotactic_overrides,
                    )
                lexicon_model = rebuild_indices(lexicon_model)
                st.session_state["sample_language_model"] = lexicon_model
                if st.session_state.get("sample_words"):
                    concept_entries_raw = CONCEPT_LIST_PRESETS[selected_concept_list].get("entries", [])
                    concept_entry_count = len(concept_entries_raw) if isinstance(concept_entries_raw, (list, tuple)) else 0
                    st.session_state["sample_words"] = build_sample_words(
                        latest_vowels,
                        latest_consonants,
                        sample_count=max(1, int(concept_entry_count)),
                        syllable_range=sample_syllable_range,
                        syllable_separator=syllable_separator,
                        style_name=selected_style,
                        concept_list_name=selected_concept_list,
                        grammar_profile_name=selected_grammar_profile,
                        language_model=lexicon_model,
                        phonotactic_profile_overrides=phonotactic_overrides,
                    )
                st.session_state.pop("sample_sentences", None)
                st.success("Selected entries re-rolled.")
                st.rerun()

    with tab_export:
        st.markdown('<div class="section-kicker">Step 5</div>', unsafe_allow_html=True)
        st.subheader("Export and Reuse")
        if not latest_inventory:
            st.info("Generate a language first to export snapshots and presets.")
        else:
            st.caption("Download ready-to-reuse files or save this result as a preset for future sessions.")
            preset_payload = inventory_as_preset_payload(latest_inventory, latest_language_name)

            download_col_1, download_col_2 = st.columns(2)
            with download_col_1:
                st.download_button(
                    label="Download preset JSON",
                    data=json.dumps(preset_payload, ensure_ascii=False, indent=2),
                    file_name=f"{sanitize_name(latest_language_name)}.json",
                    mime="application/json",
                    use_container_width=True,
                    help="Save the current inventory as a preset.",
                )
            guide_csv = build_pronunciation_csv(
                latest_inventory.get("vowels", []),
                latest_inventory.get("consonants", []),
                profile_name=romanization_profile,
            )
            with download_col_2:
                st.download_button(
                    label="Download pronunciation guide CSV",
                    data=guide_csv,
                    file_name=f"{sanitize_name(latest_language_name)}_pronunciation_guide.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Export a segment + sound-like reference table.",
                )

            snapshot_payload = build_language_snapshot(
                language_name=latest_language_name,
                inventory=latest_inventory,
                language_model=st.session_state.get("sample_language_model"),
                notes=st.session_state.get("language_notes", ""),
            )
            snapshot_json = json.dumps(snapshot_payload, ensure_ascii=False, indent=2)
            st.download_button(
                label="Download language snapshot JSON",
                data=snapshot_json,
                file_name=f"{sanitize_name(latest_language_name)}_snapshot.json",
                mime="application/json",
                use_container_width=True,
                help="Export a full snapshot including lexicon and notes.",
            )
            uploaded_snapshot = st.file_uploader(
                "Load language snapshot JSON",
                type="json",
                key="language_snapshot_upload",
                help="Load a previously exported snapshot.",
            )
            if uploaded_snapshot:
                try:
                    snapshot = json.load(uploaded_snapshot)
                    if not isinstance(snapshot, dict):
                        raise ValueError("Snapshot must be a JSON object.")
                    inventory = snapshot.get("inventory", {})
                    if not isinstance(inventory, dict):
                        raise ValueError("Snapshot inventory is invalid.")
                    if "vowels" not in inventory or "consonants" not in inventory:
                        raise ValueError("Snapshot inventory must include vowels and consonants.")

                    hydrated = project_io.hydrate_language_model(snapshot)
                    meta = snapshot.get("meta", {})
                    if not isinstance(meta, dict):
                        meta = {}

                    st.session_state["last_inventory"] = inventory
                    st.session_state["last_language_name"] = meta.get("name", latest_language_name)
                    st.session_state["sample_language_model"] = hydrated
                    st.session_state["sample_style_preset"] = hydrated.get("style_name", DEFAULT_STYLE_PRESET)
                    st.session_state["sample_concept_list"] = hydrated.get("concept_list_name", DEFAULT_CONCEPT_LIST)
                    st.session_state["sample_grammar_profile"] = hydrated.get("grammar_profile_name", DEFAULT_GRAMMAR_PROFILE)
                    st.session_state["language_notes"] = str(meta.get("notes", ""))
                    syllable_range = hydrated.get("syllable_range", [1, 1])
                    if isinstance(syllable_range, (list, tuple)) and len(syllable_range) == 2:
                        st.session_state["sample_syllable_range"] = (int(syllable_range[0]), int(syllable_range[1]))
                    st.session_state["sample_show_syllable_breaks"] = hydrated.get("syllable_separator", "") == "."
                    st.session_state.pop("sample_words", None)
                    st.session_state.pop("sample_sentences", None)
                    st.session_state["last_generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    st.success("Language snapshot loaded.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not load snapshot: {exc}")

            st.markdown("**Save latest result as preset**")
            preset_filename = st.text_input(
                "Preset filename (without .json)",
                value=sanitize_name(latest_language_name),
                key="preset_filename",
                help="Saved into presets/ for reuse.",
            )
            overwrite_existing = st.checkbox(
                "Overwrite existing preset file",
                value=False,
                help="Allow replacing a preset with the same filename.",
            )
            save_preset = st.button(
                "Save to presets/",
                use_container_width=True,
                help="Write the preset JSON into presets/.",
            )

            if save_preset:
                safe_name = sanitize_name(preset_filename)
                preset_path = Path(generator.PRESETS_DIR) / f"{safe_name}.json"

                if preset_path.exists() and not overwrite_existing:
                    st.error(f"`{preset_path.name}` already exists. Enable overwrite to replace it.")
                else:
                    with preset_path.open("w", encoding="utf-8") as file:
                        json.dump(preset_payload, file, ensure_ascii=False, indent=2)
                    st.success(f"Saved preset: {preset_path}")

            st.markdown("**Next step**")
            if st.button(
                "Open Language Family Builder",
                use_container_width=True,
                help="Switch to multi-language family workflows.",
            ):
                st.session_state["app_mode"] = "Language Family"
                st.rerun()


def render_language_family_ui() -> None:
    st.subheader("Language Family Generator")
    romanization_profile = st.session_state.get("romanization_profile", DEFAULT_ROMANIZATION_PROFILE)
    if romanization_profile not in ROMANIZATION_PROFILES:
        romanization_profile = DEFAULT_ROMANIZATION_PROFILE

    display_col, _ = st.columns([1.1, 2.9])
    with display_col:
        romanization_profile = st.selectbox(
            "Romanization profile",
            options=list(ROMANIZATION_PROFILES.keys()),
            index=list(ROMANIZATION_PROFILES.keys()).index(romanization_profile)
            if romanization_profile in ROMANIZATION_PROFILES
            else 0,
            key="romanization_profile",
            help="Display-only: how IPA renders to sound-like text.",
        )

    notice = st.session_state.pop("family_notice", None)
    if notice:
        st.success(notice)

    def _set_project_state(project: Dict[str, Any], project_dir: Path) -> None:
        st.session_state["family_project"] = project
        st.session_state["family_project_dir"] = str(project_dir)
        st.session_state["family_languages_cache"] = None

    help_topics = {
        "project_root": {
            "title": "Project root",
            "body": "Where family projects are stored. Each project is a folder containing project.json.",
        },
        "proto_source": {
            "title": "Proto source",
            "body": "Choose whether to seed the family from the current single-language state or a saved snapshot.",
        },
        "parent_select": {
            "title": "Parent language",
            "body": "Pick the language your new daughter will descend from.",
        },
        "child_id": {
            "title": "Child ID",
            "body": "Unique identifier used for filenames and links in the tree. Auto-suggested, editable.",
        },
        "sound_changes": {
            "title": "Sound changes",
            "body": "Rules are applied in order to transform the parent inventory and lexicon into the daughter. "
            "Use templates to auto-fill common historical shifts; see the template explanations below.",
        },
        "override_settings": {
            "title": "Overrides",
            "body": "By default the daughter inherits style/grammar/phonotactics. Use overrides only if needed.",
        },
        "inventory_diff": {
            "title": "Inventory diff",
            "body": "Shows which vowels/consonants were added or removed by the changeset.",
        },
        "lexicon_diff": {
            "title": "Lexicon diff",
            "body": "Sample of cognate changes (parent vs child IPA).",
        },
        "tree": {
            "title": "Tree",
            "body": "Click a node to select it. Highlight shows lineage from root to selection.",
        },
    }

    def help_button(topic_key: str, suffix: str = "") -> None:
        key = f"help_{topic_key}_{suffix}" if suffix else f"help_{topic_key}"
        if st.button("?", key=key, help="Show an explanation for this section."):
            st.session_state["help_topic"] = topic_key

    def pick_random_sound_templates(
        options: List[str],
        parent_inventory: Dict[str, Any],
        duration_years: int,
    ) -> List[str]:
        if not options:
            return []
        rng = random.Random()
        weights = family_generator.template_weights_for_inventory(
            options,
            parent_inventory.get("vowels", []) if isinstance(parent_inventory, dict) else [],
            parent_inventory.get("consonants", []) if isinstance(parent_inventory, dict) else [],
        )
        weighted_options = [template for template in options if weights.get(template, 0.0) > 0]
        if not weighted_options:
            weighted_options = list(options)
        max_count = min(8, len(weighted_options))
        min_count = min(3, len(weighted_options))
        baseline = max(3, min_count)
        span = min(5, max_count - baseline)
        target_count = baseline + max(0, min(span, duration_years // 350))
        target_count = min(max_count, max(min_count, target_count))

        chosen: List[str] = []
        opposing_pairs = {
            ("stop_voicing", "stop_devoicing"),
            ("vowel_raise_pair", "vowel_lower_pair"),
        }

        def _pick_weighted() -> Optional[str]:
            total = sum(weights.get(template, 0.0) for template in weighted_options if template not in chosen)
            if total <= 0:
                remaining = [template for template in weighted_options if template not in chosen]
                return rng.choice(remaining) if remaining else None
            pick = rng.uniform(0, total)
            cumulative = 0.0
            for template in weighted_options:
                if template in chosen:
                    continue
                cumulative += weights.get(template, 0.0)
                if pick <= cumulative:
                    return template
            return None

        while len(chosen) < target_count:
            template_id = _pick_weighted()
            if not template_id:
                break
            conflicting = False
            for left, right in opposing_pairs:
                if template_id == left and right in chosen:
                    conflicting = True
                if template_id == right and left in chosen:
                    conflicting = True
            if conflicting:
                chosen.append(template_id)
                continue
            chosen.append(template_id)
        return [template for template in options if template in set(chosen)]

    setup_tab, workspace_tab = st.tabs(["Project Setup", "Family Workspace"])

    with setup_tab:
        setup_col_1, setup_col_2 = st.columns([1.4, 1.0], gap="large")

        with setup_col_1:
            st.markdown("### Project")
            project_root = st.text_input(
                "Project root folder",
                value=st.session_state.get("family_project_root", "outputs/projects"),
                key="family_project_root",
                help="Folder where family projects are stored.",
            )
            help_button("project_root")
            project_root_path = Path(project_root)
            project_dirs = discover_project_dirs(project_root_path)
            project_labels = [path.name for path in project_dirs]

            create_col, load_col = st.columns(2)
            with create_col:
                new_project_name = st.text_input(
                    "Project name",
                    value="MyLanguageFamily",
                    key="family_new_project_name",
                    help="Human-readable project name.",
                )
                new_project_seed = st.number_input(
                    "Seed",
                    min_value=0,
                    max_value=2_147_483_647,
                    value=42,
                    step=1,
                    key="family_new_project_seed",
                    help="Random seed for family generation.",
                )
                st.caption("Timeline span is fixed for now; you can edit years per language as needed.")
                if st.button(
                    "Create Project",
                    use_container_width=True,
                    help="Create a new family project folder.",
                ):
                    try:
                        project = project_io.create_project(
                            root_dir=project_root_path,
                            project_name=new_project_name,
                            seed=int(new_project_seed),
                            time_span_years=FAMILY_TIMESPAN_DEFAULT,
                        )
                        _set_project_state(project, project_root_path / project["project_slug"])
                        st.success("Project created and loaded.")
                    except FileExistsError as exc:
                        st.error(str(exc))

            with load_col:
                selected_project = st.selectbox(
                    "Projects",
                    options=project_labels if project_labels else ["(none)"],
                    index=0,
                    disabled=not project_labels,
                    help="Pick a saved project to load.",
                )
                if st.button(
                    "Load Project",
                    use_container_width=True,
                    disabled=not project_labels,
                    help="Load the selected project into the workspace.",
                ):
                    project_dir = project_root_path / selected_project
                    try:
                        project = project_io.load_project(project_dir)
                        _set_project_state(project, project_dir)
                        st.success(f"Loaded project: {selected_project}")
                    except Exception as exc:  # pragma: no cover - UI safety net
                        st.error(f"Could not load project: {exc}")

            project = st.session_state.get("family_project")
            project_dir_value = st.session_state.get("family_project_dir")
            project_dir = Path(project_dir_value) if project_dir_value else None
            if isinstance(project, dict):
                st.caption(f"Active: {project.get('project_name', '(unknown)')}")
                if st.button(
                    "Save Project",
                    use_container_width=True,
                    help="Persist any changes to project.json.",
                ):
                    try:
                        project_io.save_project(project)
                        st.success("Project saved.")
                    except Exception as exc:  # pragma: no cover - UI safety net
                        st.error(f"Could not save project: {exc}")

        project = st.session_state.get("family_project")
        project_dir_value = st.session_state.get("family_project_dir")
        project_dir = Path(project_dir_value) if project_dir_value else None

        with setup_col_2:
            st.markdown("### Proto")
            proto_source = st.radio(
                "Proto source",
                options=["Use current single-language state", "Upload snapshot JSON"],
                horizontal=True,
                key="family_proto_source",
                help="Choose where the proto language snapshot comes from.",
            )
            help_button("proto_source")
            proto_snapshot: Optional[Dict[str, Any]] = None

            if proto_source == "Use current single-language state":
                latest_inventory = st.session_state.get("last_inventory")
                if isinstance(latest_inventory, dict):
                    model = st.session_state.get("sample_language_model")
                    proto_snapshot = build_language_snapshot(
                        language_name=st.session_state.get("last_language_name", "ProtoLanguage"),
                        inventory=latest_inventory,
                        language_model=model if isinstance(model, dict) else None,
                        language_id="proto",
                        notes=st.session_state.get("language_notes", ""),
                    )
                    st.caption(f"Proto ready: {snapshot_summary(proto_snapshot)}")
                else:
                    st.info("Generate a single language inventory first.")
            else:
                uploaded_proto = st.file_uploader(
                    "Upload snapshot JSON",
                    type="json",
                    key="family_proto_upload",
                    help="Upload a snapshot exported from the single-language UI.",
                )
                if uploaded_proto:
                    try:
                        proto_snapshot = json.load(uploaded_proto)
                        if not isinstance(proto_snapshot, dict):
                            raise ValueError("Snapshot must be a JSON object.")
                        if "inventory" not in proto_snapshot:
                            raise ValueError("Snapshot missing inventory field.")
                        st.caption(f"Proto loaded: {snapshot_summary(proto_snapshot)}")
                    except Exception as exc:
                        st.error(f"Could not load snapshot: {exc}")

            if proto_snapshot and isinstance(project, dict) and project_dir:
                overwrite_proto = st.checkbox(
                    "Overwrite existing proto",
                    value=False,
                    help="Replace the proto file if it already exists.",
                )
                if st.button(
                    "Save Proto",
                    use_container_width=True,
                    help="Store the proto language into the family project.",
                ):
                    meta = proto_snapshot.get("meta", {})
                    if not isinstance(meta, dict):
                        meta = {}
                    language_id = sanitize_name(str(meta.get("language_id") or "proto")) or "proto"
                    language_name = str(meta.get("name") or proto_snapshot.get("name") or language_id)
                    meta.update(
                        {
                            "language_id": language_id,
                            "name": language_name,
                            "year": 0,
                            "parent_id": None,
                            "changeset_id": None,
                            "created_at": meta.get("created_at") or datetime.now().isoformat(),
                            "notes": meta.get("notes", ""),
                            "lexicon_overrides": meta.get("lexicon_overrides", {}),
                        }
                    )

                    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
                    target_path = languages_dir / f"{language_id}.json"
                    if target_path.exists() and not overwrite_proto:
                        st.error("Proto file already exists. Enable overwrite to replace it.")
                    else:
                        normalized = project_io.normalize_language_snapshot(proto_snapshot)
                        normalized["meta"] = meta
                        project_io.save_language(normalized, target_path)
                        project["root_language_id"] = language_id
                        language_index = project.get("language_index", [])
                        if not isinstance(language_index, list):
                            language_index = []
                        if not any(
                            isinstance(item, dict) and item.get("language_id") == language_id for item in language_index
                        ):
                            language_index.append({"language_id": language_id, "filename": f"{language_id}.json"})
                        project["language_index"] = language_index
                        project_io.save_project(project)
                        _set_project_state(project, project_dir)
                        st.session_state["family_notice"] = f"Saved proto language: {language_id}"
                        st.rerun()

    with workspace_tab:
        project = st.session_state.get("family_project")
        project_dir_value = st.session_state.get("family_project_dir")
        project_dir = Path(project_dir_value) if project_dir_value else None


        def _load_languages(force: bool = False) -> Dict[str, Dict[str, Any]]:
            if not isinstance(project, dict) or not project_dir:
                return {}
            cache = st.session_state.get("family_languages_cache")
            if force or not isinstance(cache, dict) or not cache:
                st.session_state["family_languages_cache"] = load_languages_from_project(project, project_dir)
            return st.session_state.get("family_languages_cache", {})

        def _label_for(language_id: str, languages: Dict[str, Dict[str, Any]]) -> str:
            meta = languages.get(language_id, {}).get("meta", {})
            name = meta.get("name", language_id)
            year = meta.get("year", "?")
            return f"{name} ({language_id}, {year})"

        def _suggest_unique_id(base: str, existing_ids: List[str]) -> str:
            base_id = sanitize_name(base) or "language"
            if base_id not in existing_ids:
                return base_id
            counter = 1
            while True:
                candidate = f"{base_id}_{counter:02d}"
                if candidate not in existing_ids:
                    return candidate
                counter += 1

        def _propagate_descendants(language_id: str, notice: str) -> None:
            if not isinstance(project, dict) or not project_dir:
                return
            family_generator.rebuild_subtree(project_dir, language_id)
            st.session_state["family_languages_cache"] = load_languages_from_project(project, project_dir)
            if notice:
                st.session_state["family_notice"] = notice

        left_col, main_col, help_col = st.columns([1.3, 2.2, 1.1], gap="large")

        with left_col:
            st.markdown("### Tree")
            help_button("tree")
            if not isinstance(project, dict) or not project_dir:
                st.info("Load or create a project first.")
            else:
                if st.button(
                    "Reload languages",
                    key="family_reload_languages",
                    help="Re-read language files from disk.",
                ):
                    _load_languages(force=True)
                languages = _load_languages()
                if not languages:
                    st.info("No languages found in this project yet.")
                else:
                    child_map = family_generator.build_child_map(languages)
                    root_id = project.get("root_language_id")
                    selected_id = st.session_state.get("family_selected_id") or root_id
                    if selected_id not in languages:
                        selected_id = root_id if root_id in languages else list(languages.keys())[0]

                    path_ids = family_generator.path_to_root(languages, selected_id)
                    path_set = set(path_ids)

                    if AGRAPH_AVAILABLE:
                        nodes = []
                        edges = []
                        for language_id, language in languages.items():
                            meta = language.get("meta", {})
                            label = f"{meta.get('name', language_id)}\n{meta.get('year', '?')}"
                            size = 26 if language_id == root_id else 18
                            color = "#1f7a5a" if language_id == root_id else "#5b8bd1"
                            if language_id == selected_id:
                                color = "#d65b5b"
                            elif language_id in path_set:
                                color = "#f0a202"
                            nodes.append(Node(id=language_id, label=label, size=size, color=color))
                        for parent_id, children in child_map.items():
                            for child_id in children:
                                edge_color = "#f0a202" if parent_id in path_set and child_id in path_set else "#a7b6bd"
                                edges.append(Edge(source=parent_id, target=child_id, color=edge_color))
                        config = Config(
                            width="100%",
                            height=520,
                            directed=True,
                            physics=True,
                            hierarchical=False,
                            nodeHighlightBehavior=True,
                        )
                        selected = agraph(nodes=nodes, edges=edges, config=config)
                        if selected:
                            if isinstance(selected, str):
                                selected_id = selected
                            elif isinstance(selected, dict) and "id" in selected:
                                selected_id = str(selected["id"])
                    else:
                        st.info("Install streamlit-agraph for interactive tree. Showing static graph instead.")
                        dot_lines = ["digraph G {", "rankdir=LR;"]
                        for language_id, language in languages.items():
                            meta = language.get("meta", {})
                            label = f"{meta.get('name', language_id)} ({meta.get('year', '?')})".replace('"', "'")
                            dot_lines.append(f'"{language_id}" [label="{label}"];')
                        for parent_id, children in child_map.items():
                            for child_id in children:
                                dot_lines.append(f'"{parent_id}" -> "{child_id}";')
                        dot_lines.append("}")
                        st.graphviz_chart("\n".join(dot_lines))

                    available_ids = list(languages.keys())
                    available_ids.sort(key=lambda lang_id: str(languages[lang_id].get("meta", {}).get("year", "")))
                    labels = {_label_for(lang_id, languages): lang_id for lang_id in available_ids}
                    selected_label = st.selectbox(
                        "Selected language",
                        options=list(labels.keys()),
                        index=list(labels.values()).index(selected_id) if selected_id in labels.values() else 0,
                        help="Choose the language to inspect or edit.",
                    )
                    selected_id = labels[selected_label]
                    st.session_state["family_selected_id"] = selected_id

                    selected_meta = languages.get(selected_id, {}).get("meta", {})
                    parent_id = selected_meta.get("parent_id")
                    path_ids = list(reversed(family_generator.path_to_root(languages, selected_id)))
                    if path_ids:
                        st.caption("Path: " + " → ".join(path_ids))

                    nav_cols = st.columns(2)
                    with nav_cols[0]:
                        if parent_id and st.button(
                            "Go to parent",
                            key="family_go_parent",
                            help="Jump to the immediate ancestor language.",
                        ):
                            st.session_state["family_selected_id"] = parent_id
                            st.rerun()
                    with nav_cols[1]:
                        root_id = project.get("root_language_id")
                        if root_id and st.button(
                            "Go to root",
                            key="family_go_root",
                            help="Jump to the proto/root language.",
                        ):
                            st.session_state["family_selected_id"] = root_id
                            st.rerun()

        with main_col:
            if not isinstance(project, dict) or not project_dir:
                st.info("Load or create a project first.")
            else:
                languages = _load_languages()
                if not languages:
                    st.info("Save a proto language first in the setup panel above.")
                else:
                    selected_id = st.session_state.get("family_selected_id") or project.get("root_language_id")
                    if selected_id not in languages:
                        selected_id = list(languages.keys())[0]
                    selected_meta = languages.get(selected_id, {}).get("meta", {})
                    selected_label = f"{selected_meta.get('name', selected_id)} ({selected_id})"
                    summary_cols = st.columns(3)
                    summary_cols[0].metric("Languages", str(len(languages)))
                    summary_cols[1].metric("Selected", selected_label)
                    summary_cols[2].metric("Root", str(project.get("root_language_id") or "—"))
                    view = st.radio(
                        "Workspace",
                        options=["Create Daughter", "Compare", "Language Details"],
                        horizontal=True,
                        help="Choose a workflow: create, compare, or curate a language.",
                    )

                    if view == "Create Daughter":
                        existing_ids = sorted(list(languages.keys()))
                        selected_parent_default = st.session_state.get("family_selected_id") or project.get("root_language_id")
                        if selected_parent_default not in existing_ids:
                            selected_parent_default = existing_ids[0]

                        selected_parent = selected_parent_default
                        child_name = f"{selected_parent}_child"
                        child_id_input = ""
                        override_settings: Dict[str, Any] = {}
                        cleaned_rules: List[Dict[str, Any]] = []

                        step_parent, step_identity, step_changes, step_preview = st.tabs(
                            ["1. Parent", "2. Identity", "3. Changes", "4. Preview"]
                        )

                        with step_parent:
                            parent_col, parent_help_col = st.columns([4, 1])
                            with parent_col:
                                selected_parent = st.selectbox(
                                    "Select parent language",
                                    options=existing_ids,
                                    index=existing_ids.index(selected_parent_default)
                                    if selected_parent_default in existing_ids
                                    else 0,
                                    help="Parent language that the daughter will derive from.",
                                )
                            with parent_help_col:
                                help_button("parent_select")
                            parent_language = languages[selected_parent]
                            parent_meta = parent_language.get("meta", {})
                            st.caption(
                                f"Parent: {parent_meta.get('name', selected_parent)} "
                                f"({selected_parent}, year {parent_meta.get('year', '?')})"
                            )

                        with step_identity:
                            parent_language = languages[selected_parent]
                            st.markdown("**Name + ID**")
                            child_name = st.text_input(
                                "Child language name",
                                value=f"{selected_parent}_child",
                                help="Display name for the new daughter language.",
                            )
                            suggested_id = _suggest_unique_id(child_name, existing_ids)
                            child_id_input = st.text_input(
                                "Child language ID",
                                value=suggested_id,
                                help="Stable identifier used in filenames and comparisons.",
                            )
                            help_button("child_id")
                            if child_id_input in existing_ids:
                                st.error("This ID is already used. Choose a different one.")
                            year_default = int(parent_language.get("meta", {}).get("year", 0)) + 100
                            child_year = st.number_input(
                                "Year (relative to proto timeline)",
                                value=year_default,
                                step=10,
                                key=f"family_child_year_{selected_parent}",
                                help="Approximate year for the daughter relative to the proto timeline.",
                            )
                            notes = st.text_area(
                                "Notes (optional)",
                                value="",
                                help="Optional notes stored with the language.",
                            )

                            override_settings = {"year": int(child_year), "notes": notes}
                            with st.expander("Override inherited settings", expanded=False):
                                help_button("override_settings")
                                parent_style = str(parent_language.get("style_name", DEFAULT_STYLE_PRESET))
                                parent_concept = str(parent_language.get("concept_list_name", DEFAULT_CONCEPT_LIST))
                                parent_grammar = str(parent_language.get("grammar_profile_name", DEFAULT_GRAMMAR_PROFILE))
                                parent_syllable_range = parent_language.get("syllable_range", [1, 1])
                                if not isinstance(parent_syllable_range, (list, tuple)) or len(parent_syllable_range) != 2:
                                    parent_syllable_range = [1, 1]
                                parent_separator = str(parent_language.get("syllable_separator", ""))

                                if st.checkbox(
                                    "Override style preset",
                                    value=False,
                                    key="family_override_style",
                                    help="Use a different phonotactic style than the parent.",
                                ):
                                    override_settings["style_name"] = st.selectbox(
                                        "Style preset",
                                        options=list(STYLE_PRESETS.keys()),
                                        index=list(STYLE_PRESETS.keys()).index(parent_style)
                                        if parent_style in STYLE_PRESETS
                                        else 0,
                                        help="Phonotactic style to use for the daughter.",
                                    )

                                if st.checkbox(
                                    "Override concept list",
                                    value=False,
                                    key="family_override_concept",
                                    help="Use a different concept list than the parent.",
                                ):
                                    override_settings["concept_list_name"] = st.selectbox(
                                        "Concept list",
                                        options=list(CONCEPT_LIST_PRESETS.keys()),
                                        index=list(CONCEPT_LIST_PRESETS.keys()).index(parent_concept)
                                        if parent_concept in CONCEPT_LIST_PRESETS
                                        else 0,
                                        help="Concept list for root meanings.",
                                    )

                                if st.checkbox(
                                    "Override grammar profile",
                                    value=False,
                                    key="family_override_grammar",
                                    help="Use a different grammar profile than the parent.",
                                ):
                                    override_settings["grammar_profile_name"] = st.selectbox(
                                        "Grammar profile",
                                        options=list(GRAMMAR_PROFILES.keys()),
                                        index=list(GRAMMAR_PROFILES.keys()).index(parent_grammar)
                                        if parent_grammar in GRAMMAR_PROFILES
                                        else 0,
                                        help="Grammar template for sentence generation.",
                                    )

                                if st.checkbox(
                                    "Override syllable range",
                                    value=False,
                                    key="family_override_syllables",
                                    help="Use a different syllable length range.",
                                ):
                                    override_settings["syllable_range"] = list(
                                        st.slider(
                                            "Syllables per word",
                                            min_value=1,
                                            max_value=5,
                                            value=(int(parent_syllable_range[0]), int(parent_syllable_range[1])),
                                            help="Min/max syllables for new roots.",
                                        )
                                    )

                                if st.checkbox(
                                    "Override syllable separator",
                                    value=False,
                                    key="family_override_sep",
                                    help="Show syllable separators in IPA output.",
                                ):
                                    override_settings["syllable_separator"] = st.selectbox(
                                        "Separator",
                                        options=["", "."],
                                        index=0 if parent_separator == "" else 1,
                                        help="Choose '.' to insert syllable breaks.",
                                    )

                                if st.checkbox(
                                    "Override phonotactic profile (JSON)",
                                    value=False,
                                    key="family_override_phonotactics",
                                    help="Advanced: paste a phonotactic override object.",
                                ):
                                    raw_override = st.text_area(
                                        "Phonotactic overrides JSON",
                                        value="{}",
                                        height=120,
                                        help="JSON overrides for phonotactic controls.",
                                    )
                                    override_dict, override_error = parse_override_json(raw_override)
                                    if override_error:
                                        st.error(override_error)
                                    else:
                                        override_settings["phonotactic_profile_overrides"] = override_dict

                        with step_changes:
                            parent_language = languages[selected_parent]
                            parent_inventory = parent_language.get("inventory", {})
                            parent_year = int(parent_language.get("meta", {}).get("year", 0))
                            duration_years = max(1, int(child_year) - parent_year)
                            events_per_1000_years = float(
                                project.get("family_config", {}).get("events_per_1000_years", 6.0)
                                if isinstance(project, dict)
                                else 6.0
                            )
                            seed_base = int(project.get("seed", 0))
                            seed_value = abs(hash(f"{seed_base}:{selected_parent}:{child_id_input}")) % (2**32)
                            plan_rng = random.Random(seed_value)
                            estimated_events, estimated_stages = family_generator.estimate_time_based_plan(
                                duration_years, events_per_1000_years, plan_rng
                            )
                            st.markdown("**Sound changes**")
                            help_button("sound_changes")
                            st.caption(
                                f"Time span: {duration_years} years → ~{estimated_events} change(s) across "
                                f"{estimated_stages} stage(s)."
                            )
                            template_options = list(project_io.DEFAULT_FAMILY_CONFIG["sound_change_templates_enabled"])
                            template_key = f"family_template_select_{selected_parent}_{child_id_input}"
                            rule_editor_key = f"family_rules_{selected_parent}_{child_id_input}"
                            randomize_flag = f"{rule_editor_key}_randomize_flag"
                            auto_sig_key = f"{rule_editor_key}_auto_sig"
                            auto_toggle_key = f"{rule_editor_key}_auto_toggle"

                            if template_key not in st.session_state:
                                st.session_state[template_key] = list(template_options)
                            if rule_editor_key not in st.session_state:
                                st.session_state[rule_editor_key] = []

                            def _apply_template_rules(templates: List[str], seed_salt: str = "") -> None:
                                if templates:
                                    seed_value = abs(
                                        hash(f"{seed_base}:{selected_parent}:{child_id_input}:{seed_salt}")
                                    ) % (2**32)
                                    rng = random.Random(seed_value)
                                    changeset_preview = family_generator.generate_time_based_changeset(
                                        parent_inventory=parent_inventory,
                                        enabled_templates=templates,
                                        duration_years=duration_years,
                                        events_per_1000_years=events_per_1000_years,
                                        rng=rng,
                                        changeset_id=f"chg_{selected_parent}_{child_id_input}",
                                        name=f"{selected_parent}→{child_id_input}",
                                    )
                                    st.session_state[rule_editor_key] = [
                                        {
                                            "from": rule.get("from", ""),
                                            "to": rule.get("to", ""),
                                            "enabled": rule.get("enabled", True),
                                            "notes": rule.get("notes", ""),
                                        }
                                        for rule in changeset_preview.get("rules", [])
                                        if isinstance(rule, dict)
                                    ]
                                else:
                                    st.session_state[rule_editor_key] = []

                            if st.session_state.pop(randomize_flag, False):
                                randomized = pick_random_sound_templates(
                                    template_options,
                                    parent_inventory,
                                    duration_years,
                                )
                                st.session_state[template_key] = randomized
                                _apply_template_rules(randomized, seed_salt=str(random.random()))

                            selected_templates = st.multiselect(
                                "Templates",
                                options=template_options,
                                default=st.session_state.get(template_key, []),
                                key=template_key,
                                format_func=lambda value: SOUND_CHANGE_TEMPLATE_LABELS.get(value, value),
                                help="Pick change templates; they become the auto-generated rules below.",
                            )

                            auto_rules = st.checkbox(
                                "Auto-generate rules by time span",
                                value=True,
                                key=auto_toggle_key,
                                help="When enabled, changes re-roll automatically when the time span changes.",
                            )
                            current_sig = f"{selected_parent}:{child_id_input}:{duration_years}:{','.join(sorted(selected_templates))}"
                            if auto_rules and st.session_state.get(auto_sig_key) != current_sig:
                                _apply_template_rules(selected_templates, seed_salt="auto")
                                st.session_state[auto_sig_key] = current_sig

                            template_action_cols = st.columns([1.2, 1.6, 2.2])
                            with template_action_cols[0]:
                                if st.button(
                                    "Randomize templates",
                                    key=f"{rule_editor_key}_randomize",
                                    help="Pick a balanced mix of vowel + consonant changes, then auto-generate rules.",
                                ):
                                    st.session_state[randomize_flag] = True
                                    st.rerun()
                            with template_action_cols[1]:
                                generate_rules_button = st.button(
                                    "Re-roll rules (time-based)",
                                    key=f"{rule_editor_key}_generate",
                                    help="Auto-generate a time-based set of sound-change rules.",
                                )
                            with template_action_cols[2]:
                                st.caption("Templates control which kinds of changes are eligible.")

                            if generate_rules_button:
                                _apply_template_rules(selected_templates)

                            with st.expander("Template explanations", expanded=False):
                                for template_id in template_options:
                                    label = SOUND_CHANGE_TEMPLATE_LABELS.get(template_id, template_id)
                                    description = SOUND_CHANGE_TEMPLATE_DESCRIPTIONS.get(template_id, "")
                                    st.markdown(f"- **{label}**: {description}")

                            edited_rules = st.data_editor(
                                st.session_state[rule_editor_key],
                                hide_index=True,
                                use_container_width=True,
                                num_rows="dynamic",
                                key=f"{rule_editor_key}_editor",
                                column_config={
                                    "from": st.column_config.TextColumn(
                                        "From",
                                        help="Segment to replace (IPA).",
                                    ),
                                    "to": st.column_config.TextColumn(
                                        "To",
                                        help="Replacement segment (IPA). Leave blank to delete.",
                                    ),
                                    "enabled": st.column_config.CheckboxColumn(
                                        "Enabled",
                                        help="Toggle to include/exclude this change.",
                                    ),
                                    "notes": st.column_config.TextColumn(
                                        "Notes",
                                        help="Optional reminder about why this rule exists.",
                                    ),
                                },
                            )
                            if hasattr(edited_rules, "to_dict"):
                                edited_rules = edited_rules.to_dict(orient="records")

                            cleaned_rules = []
                            seen_from: set[str] = set()
                            invalid_rules: List[str] = []
                            for rule in edited_rules:
                                if not isinstance(rule, dict):
                                    continue
                                frm = str(rule.get("from", "")).strip()
                                to = str(rule.get("to", "")).strip()
                                enabled = bool(rule.get("enabled", True))
                                if not frm:
                                    invalid_rules.append("Missing 'from' value.")
                                    continue
                                if frm in seen_from:
                                    invalid_rules.append(f"Duplicate rule for '{frm}'.")
                                    continue
                                seen_from.add(frm)
                                cleaned_rules.append(
                                    {
                                        "from": frm,
                                        "to": to,
                                        "enabled": enabled,
                                        "notes": str(rule.get("notes", "")),
                                    }
                                )
                            if invalid_rules:
                                st.warning("Rule validation warnings: " + "; ".join(sorted(set(invalid_rules))))
                            if not cleaned_rules:
                                st.info("No valid rules yet; you can still create a daughter with an empty changeset.")

                        with step_preview:
                            parent_language = languages[selected_parent]
                            parent_inventory = parent_language.get("inventory", {})
                            st.markdown("**Preview**")
                            st.caption(f"Parent {selected_parent} → Child {child_id_input or '(auto)'}")

                            changeset = {
                                "schema_version": 1,
                                "changeset_id": f"chg_{selected_parent}_{child_id_input}",
                                "name": f"{selected_parent}→{child_id_input}",
                                "description": f"{len(cleaned_rules)} sound-change rule(s)",
                                "rules": cleaned_rules,
                            }
                            preview_language = family_generator.preview_child_language(
                                project_dir=project_dir,
                                parent_language_id=selected_parent,
                                child_name=child_name,
                                child_id=child_id_input,
                                changeset=changeset,
                                override_settings=override_settings,
                            )
                            diff = sound_change_engine.diff_inventory(parent_inventory, preview_language.get("inventory", {}))
                            help_button("inventory_diff", "create")
                            diff_cols = st.columns(2)
                            with diff_cols[0]:
                                st.metric("Added vowels", str(len(diff["added_vowels"])))
                                st.metric("Removed vowels", str(len(diff["removed_vowels"])))
                            with diff_cols[1]:
                                st.metric("Added consonants", str(len(diff["added_consonants"])))
                                st.metric("Removed consonants", str(len(diff["removed_consonants"])))

                            if diff["added_vowels"] or diff["removed_vowels"] or diff["added_consonants"] or diff["removed_consonants"]:
                                st.dataframe(
                                    [
                                        {"Type": "Vowel+", "Segments": ", ".join(diff["added_vowels"])},
                                        {"Type": "Vowel-", "Segments": ", ".join(diff["removed_vowels"])},
                                        {"Type": "Consonant+", "Segments": ", ".join(diff["added_consonants"])},
                                        {"Type": "Consonant-", "Segments": ", ".join(diff["removed_consonants"])},
                                    ],
                                    hide_index=True,
                                    use_container_width=True,
                                )
                            summary = language_diff.summarize_rule_effects(parent_inventory, changeset)
                            st.caption(f"Rules enabled: {summary['rule_count']}")

                            lexicon_preview = language_diff.sample_lexicon_diff(parent_language, preview_language, n=12)
                            if lexicon_preview:
                                help_button("lexicon_diff", "create")
                                preview_rows = []
                                for row in lexicon_preview:
                                    parent_ipa = str(row.get("parent_ipa", ""))
                                    child_ipa = str(row.get("child_ipa", ""))
                                    preview_rows.append(
                                        {
                                            "id": row.get("id", ""),
                                            "meaning": row.get("meaning", ""),
                                            "parent_ipa": parent_ipa,
                                            "parent_sound_like": ipa_text_to_sound_like(
                                                parent_ipa,
                                                use_segment_separators=False,
                                                profile_name=romanization_profile,
                                            ),
                                            "child_ipa": child_ipa,
                                            "child_sound_like": ipa_text_to_sound_like(
                                                child_ipa,
                                                use_segment_separators=False,
                                                profile_name=romanization_profile,
                                            ),
                                        }
                                    )
                                st.dataframe(preview_rows, hide_index=True, use_container_width=True)

                            if st.button(
                                "Create Daughter",
                                type="primary",
                                use_container_width=True,
                                help="Save the daughter language into the project.",
                            ):
                                if child_id_input in existing_ids:
                                    st.error("Please pick a unique child ID.")
                                else:
                                    created = family_generator.create_child_language(
                                        project_dir=project_dir,
                                        parent_language_id=selected_parent,
                                        child_name=child_name,
                                        child_id=child_id_input,
                                        changeset=changeset,
                                        override_settings=override_settings,
                                    )
                                    project = project_io.load_project(project_dir)
                                    st.session_state["family_project"] = project
                                    st.session_state["family_languages_cache"] = load_languages_from_project(project, project_dir)
                                    st.session_state["family_selected_id"] = created.get("meta", {}).get("language_id")
                                    st.session_state["family_notice"] = (
                                        f"Created daughter language: {created.get('meta', {}).get('name')}"
                                    )
                                    st.rerun()

                    elif view == "Compare":
                        ids = sorted(list(languages.keys()))
                        default_child = st.session_state.get("family_selected_id") or ids[0]
                        child_id = st.selectbox(
                            "Child language",
                            options=ids,
                            index=ids.index(default_child) if default_child in ids else 0,
                            help="Language being compared (descendant).",
                        )
                        child_language = languages[child_id]
                        parent_id = child_language.get("meta", {}).get("parent_id") or ids[0]
                        parent_id = st.selectbox(
                            "Parent language",
                            options=ids,
                            index=ids.index(parent_id) if parent_id in ids else 0,
                            help="Language to compare against (ancestor or peer).",
                        )
                        parent_language = languages[parent_id]

                        diff = sound_change_engine.diff_inventory(
                            parent_language.get("inventory", {}),
                            child_language.get("inventory", {}),
                        )
                        st.markdown("**Inventory diff**")
                        help_button("inventory_diff", "compare")
                        st.dataframe(
                            [
                                {"Type": "Vowel+", "Segments": ", ".join(diff["added_vowels"])},
                                {"Type": "Vowel-", "Segments": ", ".join(diff["removed_vowels"])},
                                {"Type": "Consonant+", "Segments": ", ".join(diff["added_consonants"])},
                                {"Type": "Consonant-", "Segments": ", ".join(diff["removed_consonants"])},
                            ],
                            hide_index=True,
                            use_container_width=True,
                        )

                        st.markdown("**Lexicon sample diff**")
                        help_button("lexicon_diff", "compare")
                        rows = language_diff.sample_lexicon_diff(parent_language, child_language, n=20)
                        compare_rows = []
                        for row in rows:
                            parent_ipa = str(row.get("parent_ipa", ""))
                            child_ipa = str(row.get("child_ipa", ""))
                            compare_rows.append(
                                {
                                    "id": row.get("id", ""),
                                    "meaning": row.get("meaning", ""),
                                    "parent_ipa": parent_ipa,
                                    "parent_sound_like": ipa_text_to_sound_like(
                                        parent_ipa,
                                        use_segment_separators=False,
                                        profile_name=romanization_profile,
                                    ),
                                    "child_ipa": child_ipa,
                                    "child_sound_like": ipa_text_to_sound_like(
                                        child_ipa,
                                        use_segment_separators=False,
                                        profile_name=romanization_profile,
                                    ),
                                }
                            )
                        st.dataframe(compare_rows, hide_index=True, use_container_width=True)

                    else:
                        selected_language = languages[selected_id]
                        meta = selected_language.get("meta", {})
                        st.markdown(f"**{meta.get('name', selected_id)}**")
                        meta_cols = st.columns(4)
                        meta_cols[0].metric("Year", str(meta.get("year", "?")))
                        meta_cols[1].metric("Parent", str(meta.get("parent_id", "—")))
                        meta_cols[2].metric("Changeset", str(meta.get("changeset_id", "—")))
                        meta_cols[3].metric("Lexicon", str(len(selected_language.get("lexicon", []))))

                        model = project_io.hydrate_language_model(selected_language)
                        detail_tabs = st.tabs(["Overview", "Lexicon", "Samples"])

                        pos_order = ["N", "V", "ADJ", "ADV", "PRON", "NUM", "DEM", "ADP", "NEG", "CONJ", "INT", "PART"]
                        pos_options = [pos for pos in pos_order if pos in POS_LABELS]
                        pos_options.extend([pos for pos in POS_LABELS.keys() if pos not in pos_options])

                        def format_pos_label(value: str) -> str:
                            label = POS_LABELS.get(value, value)
                            return f"{label} ({value})" if value and label != value else label

                        def save_family_language(updated_language: Dict[str, Any], updated_meta: Dict[str, Any]) -> None:
                            updated_language["meta"] = updated_meta
                            normalized = project_io.normalize_language_snapshot(updated_language)
                            normalized["meta"] = updated_meta
                            languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
                            project_io.save_language(normalized, languages_dir / f"{selected_id}.json")
                            st.session_state["family_languages_cache"] = load_languages_from_project(project, project_dir)

                        with detail_tabs[0]:
                            inventory = selected_language.get("inventory", {})
                            st.markdown("**Language name**")
                            def _auto_name_family() -> None:
                                suggested = suggest_language_name(model, romanization_profile)
                                if suggested:
                                    meta["name"] = suggested
                                    st.session_state[f"family_name_{selected_id}"] = suggested
                                    save_family_language(selected_language, meta)
                                    st.session_state["family_notice"] = f"Generated name: {suggested}"
                                else:
                                    st.session_state["family_notice"] = (
                                        "Generate a lexicon first to auto-name this language."
                                    )

                            name_cols = st.columns([3, 1, 1])
                            with name_cols[0]:
                                name_value = st.text_input(
                                    "Display name",
                                    value=str(meta.get("name", selected_id)),
                                    key=f"family_name_{selected_id}",
                                    help="Rename this language for display and exports.",
                                )
                            with name_cols[1]:
                                if st.button(
                                    "Save name",
                                    key=f"family_name_save_{selected_id}",
                                    help="Persist the new name to disk.",
                                ):
                                    if name_value.strip():
                                        meta["name"] = name_value.strip()
                                        save_family_language(selected_language, meta)
                                        st.success("Language name updated.")
                                        st.rerun()
                            with name_cols[2]:
                                st.button(
                                    "Auto-name",
                                    key=f"family_name_auto_{selected_id}",
                                    help="Generate a language name from the lexicon.",
                                    on_click=_auto_name_family,
                                )
                            display_col_1, display_col_2 = st.columns(2)
                            with display_col_1:
                                display_segment_table(
                                    "Vowels",
                                    inventory.get("vowels", []) if isinstance(inventory, dict) else [],
                                    profile_name=romanization_profile,
                                )
                            with display_col_2:
                                display_segment_table(
                                    "Consonants",
                                    inventory.get("consonants", []) if isinstance(inventory, dict) else [],
                                    profile_name=romanization_profile,
                                )
                            st.markdown("**Language notes**")
                            notes_key = f"family_notes_{selected_id}"
                            notes_value = st.text_area(
                                "Description / reminders",
                                value=str(meta.get("notes", "")),
                                key=notes_key,
                                height=140,
                                placeholder="Add notes about this language.",
                                help="Private notes saved with this language.",
                            )
                            if st.button(
                                "Save notes",
                                key=f"family_notes_save_{selected_id}",
                                help="Persist notes to disk.",
                            ):
                                meta["notes"] = notes_value
                                save_family_language(selected_language, meta)
                                st.success("Notes saved.")
                                st.rerun()

                            st.divider()
                            st.markdown("**Quick compare**")
                            def entry_source_label(entry: Dict[str, Any]) -> str:
                                if is_custom_entry(entry):
                                    return "Custom"
                                entry_id = str(entry.get("id", ""))
                                source = str(entry.get("source", ""))
                                pos = str(entry.get("pos", ""))
                                if source.startswith("concept-list:"):
                                    return "Concept roots"
                                if source.startswith("grammar:") or entry_id.startswith("PART:") or pos == "PART":
                                    return "Particles"
                                return "Other"

                            compare_options = [
                                {"label": "(none)", "id": ""},
                            ]
                            for lang_id in languages.keys():
                                if lang_id == selected_id:
                                    continue
                                meta_other = languages.get(lang_id, {}).get("meta", {})
                                label = f"{meta_other.get('name', lang_id)} ({lang_id})"
                                compare_options.append({"label": label, "id": lang_id})

                            parent_id = meta.get("parent_id")
                            default_compare_id = parent_id if parent_id in languages else (project.get("root_language_id") or "")
                            default_index = 0
                            for idx, option in enumerate(compare_options):
                                if option["id"] == default_compare_id:
                                    default_index = idx
                                    break

                            compare_label = st.selectbox(
                                "Compare against",
                                options=[option["label"] for option in compare_options],
                                index=default_index,
                                key=f"family_compare_target_{selected_id}",
                                help="Pick another language to compare word-by-word.",
                            )
                            compare_id = ""
                            for option in compare_options:
                                if option["label"] == compare_label:
                                    compare_id = option["id"]
                                    break

                            compare_search = st.text_input(
                                "Search entries",
                                key=f"family_compare_search_{selected_id}",
                                placeholder="Filter by id or meaning",
                                help="Filter by entry ID or meaning tag.",
                            )
                            current_lexicon = model.get("lexicon", [])
                            if not isinstance(current_lexicon, list):
                                current_lexicon = []
                            compare_filter_cols = st.columns(3)
                            with compare_filter_cols[0]:
                                compare_count = st.slider(
                                    "Rows to show",
                                    min_value=10,
                                    max_value=200,
                                    value=40,
                                    step=10,
                                    key=f"family_compare_count_{selected_id}",
                                    help="Limit the number of rows shown.",
                                )
                            with compare_filter_cols[1]:
                                compare_sources = sorted(
                                    {entry_source_label(entry) for entry in current_lexicon if isinstance(entry, dict)}
                                )
                                selected_sources = st.multiselect(
                                    "Source filter",
                                    options=compare_sources,
                                    default=compare_sources,
                                    key=f"family_compare_sources_{selected_id}",
                                    help="Filter by entry origin.",
                                )
                            with compare_filter_cols[2]:
                                compare_pos_codes = sorted(
                                    {
                                        str(entry.get("pos", "")).strip()
                                        for entry in current_lexicon
                                        if isinstance(entry, dict) and str(entry.get("pos", "")).strip()
                                    }
                                )
                                selected_compare_pos = st.multiselect(
                                    "Part of speech filter",
                                    options=compare_pos_codes,
                                    default=compare_pos_codes,
                                    format_func=format_pos_label,
                                    key=f"family_compare_pos_{selected_id}",
                                    help="Filter by grammatical category.",
                                )

                            compare_lexicon = []
                            if compare_id and compare_id in languages:
                                compare_language = project_io.hydrate_language_model(languages[compare_id])
                                compare_lexicon = compare_language.get("lexicon", [])
                                if not isinstance(compare_lexicon, list):
                                    compare_lexicon = []
                            compare_map = {
                                str(entry.get("id", "")).strip(): entry
                                for entry in compare_lexicon
                                if isinstance(entry, dict)
                            }
                            needle = compare_search.strip().lower()
                            compare_rows = []
                            for entry in current_lexicon:
                                if not isinstance(entry, dict):
                                    continue
                                if selected_sources and entry_source_label(entry) not in selected_sources:
                                    continue
                                entry_id = str(entry.get("id", "")).strip()
                                meaning = str(entry.get("meaning", "")).strip()
                                if needle and needle not in f"{entry_id} {meaning}".lower():
                                    continue
                                entry_pos = str(entry.get("pos", "")).strip()
                                if selected_compare_pos and entry_pos not in selected_compare_pos:
                                    continue
                                entry_ipa = str(entry.get("ipa", "")).strip()
                                other_entry = compare_map.get(entry_id, {})
                                other_ipa = str(other_entry.get("ipa", "")).strip()
                                compare_rows.append(
                                    {
                                        "Entry": entry_id,
                                        "Meaning": meaning,
                                        "IPA": entry_ipa,
                                        "Sound-like": ipa_text_to_sound_like(
                                            entry_ipa,
                                            use_segment_separators=False,
                                            profile_name=romanization_profile,
                                        ),
                                        "Compare IPA": other_ipa,
                                        "Compare Sound-like": ipa_text_to_sound_like(
                                            other_ipa,
                                            use_segment_separators=False,
                                            profile_name=romanization_profile,
                                        )
                                        if other_ipa
                                        else "",
                                    }
                                )
                                if len(compare_rows) >= compare_count:
                                    break

                            st.dataframe(compare_rows, hide_index=True, use_container_width=True)

                            st.divider()
                            st.markdown("**Danger zone**")
                            root_language_id = project.get("root_language_id") if isinstance(project, dict) else None
                            if selected_id == root_language_id:
                                st.info("Root languages cannot be deleted from a family project.")
                            else:
                                confirm_delete = st.checkbox(
                                    "I understand this will permanently delete the language file.",
                                    key=f"family_delete_confirm_{selected_id}",
                                    help="Required confirmation before deletion.",
                                )
                                if st.button(
                                    "Delete language",
                                    key=f"family_delete_{selected_id}",
                                    disabled=not confirm_delete,
                                    help="Delete this language from the project.",
                                ):
                                    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
                                    target_path = languages_dir / f"{selected_id}.json"
                                    if target_path.exists():
                                        target_path.unlink()
                                    language_index = project.get("language_index", [])
                                    if not isinstance(language_index, list):
                                        language_index = []
                                    language_index = [
                                        item
                                        for item in language_index
                                        if not (isinstance(item, dict) and item.get("language_id") == selected_id)
                                    ]
                                    project["language_index"] = language_index
                                    project_io.save_project(project)
                                    st.session_state["family_selected_id"] = parent_id or project.get("root_language_id")
                                    st.session_state["family_languages_cache"] = load_languages_from_project(project, project_dir)
                                    st.success("Language deleted.")
                                    st.rerun()

                        with detail_tabs[1]:
                            st.markdown("**Custom word builder**")
                            lexicon_model = model
                            root_ids: List[str] = []
                            root_label_map: Dict[str, str] = {}
                            builder_col_1, builder_col_2 = st.columns(2)
                            with builder_col_1:
                                meaning_tag = st.text_input(
                                    "Meaning tag",
                                    key=f"family_custom_word_meaning_{selected_id}",
                                    help="Short semantic label used for search and glossing.",
                                )
                                selected_pos = st.selectbox(
                                    "Part of speech",
                                    options=pos_options,
                                    format_func=format_pos_label,
                                    key=f"family_custom_word_pos_{selected_id}",
                                    help="Grammatical category for the new word.",
                                )
                                auto_gloss = st.checkbox(
                                    "Auto gloss",
                                    value=True,
                                    key=f"family_custom_word_auto_gloss_{selected_id}",
                                    help="Automatically generate a gloss from the meaning tag.",
                                )
                                gloss_input = st.text_input(
                                    "Gloss",
                                    key=f"family_custom_word_gloss_{selected_id}",
                                    disabled=auto_gloss,
                                    help="Short gloss used in sentence samples (manual override).",
                                )
                                gloss_value = ""
                                if auto_gloss and meaning_tag.strip():
                                    gloss_value = concept_gloss(meaning_tag.strip(), selected_pos)
                                    st.caption(f"Gloss: {gloss_value}")
                                elif gloss_input.strip():
                                    gloss_value = gloss_input.strip()

                            with builder_col_2:
                                mode_label = st.radio(
                                    "Build mode",
                                    options=["Random", "Use existing root"],
                                    horizontal=True,
                                    key=f"family_custom_word_mode_{selected_id}",
                                    help="Random builds from phonotactics; rooted derives from an existing entry.",
                                )
                                custom_meta: Dict[str, Any] = {}
                                if mode_label == "Random":
                                    custom_range = st.slider(
                                        "Syllables per word",
                                        min_value=1,
                                        max_value=5,
                                        value=tuple(model.get("syllable_range", [1, 2])),
                                        key=f"family_custom_word_random_range_{selected_id}",
                                        help="Total syllable range for the new word.",
                                    )
                                    custom_meta = {
                                        "mode": "random",
                                        "syllable_range": [int(custom_range[0]), int(custom_range[1])],
                                    }
                                else:
                                    lexicon_entries = lexicon_model.get("lexicon", []) if isinstance(lexicon_model, dict) else []
                                    for entry in lexicon_entries:
                                        if not isinstance(entry, dict):
                                            continue
                                        entry_id = str(entry.get("id", "")).strip()
                                        pos = str(entry.get("pos", "")).strip()
                                        if not entry_id or entry_id.startswith("PART:") or pos == "PART":
                                            continue
                                        meaning = str(entry.get("meaning", "")).strip()
                                        label = f"{entry_id} · {meaning}" if meaning else entry_id
                                        root_ids.append(entry_id)
                                        root_label_map[entry_id] = label
                                    selected_root = st.selectbox(
                                        "Root to derive from",
                                        options=root_ids if root_ids else ["(none)"],
                                        format_func=lambda value: root_label_map.get(value, value),
                                        key=f"family_custom_word_root_{selected_id}",
                                        disabled=not root_ids,
                                        help="Pick an existing root to attach affixes to.",
                                    )
                                    if not root_ids:
                                        st.warning("No eligible roots found to derive from.")
                                        selected_root = ""

                                    affix_mode_label = st.selectbox(
                                        "Affix mode",
                                        options=["Auto", "Prefix", "Suffix", "Both"],
                                        key=f"family_custom_word_affix_mode_{selected_id}",
                                        help="Where the generated affix should attach.",
                                    )
                                    affix_range = st.slider(
                                        "Affix syllables",
                                        min_value=1,
                                        max_value=4,
                                        value=(1, 1),
                                        key=f"family_custom_word_affix_range_{selected_id}",
                                        help="Syllable range for the affix portion.",
                                    )
                                    custom_meta = {
                                        "mode": "rooted",
                                        "root_id": selected_root,
                                        "affix_mode": affix_mode_label.lower(),
                                        "affix_syllable_range": [int(affix_range[0]), int(affix_range[1])],
                                    }

                            preview_key = f"family_custom_word_preview_{selected_id}"
                            preview_state = st.session_state.get(preview_key)
                            can_generate = bool(meaning_tag.strip())
                            if mode_label == "Use existing root":
                                can_generate = can_generate and bool(custom_meta.get("root_id"))

                            if st.button(
                                "Generate candidate",
                                key=f"family_custom_word_generate_{selected_id}",
                                disabled=not can_generate,
                                help="Generate a new candidate form using the current settings.",
                            ):
                                ipa = generate_custom_word_form(
                                    language_model=lexicon_model,
                                    custom_meta=custom_meta,
                                    phonotactic_profile_overrides=lexicon_model.get("phonotactic_profile_overrides"),
                                )
                                if not ipa:
                                    st.error("Could not generate a candidate. Try adjusting the settings.")
                                else:
                                    st.session_state[preview_key] = {
                                        "ipa": ipa,
                                        "custom_meta": custom_meta,
                                        "meaning": meaning_tag.strip(),
                                        "pos": selected_pos,
                                        "gloss": gloss_value,
                                    }
                                    preview_state = st.session_state[preview_key]

                            if isinstance(preview_state, dict) and preview_state.get("ipa"):
                                preview_ipa = str(preview_state.get("ipa", ""))
                                preview_col_1, preview_col_2 = st.columns(2)
                                with preview_col_1:
                                    st.markdown(f"**IPA**: `{preview_ipa}`")
                                with preview_col_2:
                                    st.markdown(
                                        f"**Sound-like**: `{ipa_text_to_sound_like(preview_ipa, use_segment_separators=False, profile_name=romanization_profile)}`"
                                    )

                            add_disabled = not (isinstance(preview_state, dict) and preview_state.get("ipa")) or not meaning_tag.strip()
                            if st.button(
                                "Add to lexicon",
                                key=f"family_custom_word_add_{selected_id}",
                                disabled=add_disabled,
                                help="Persist the previewed word into the lexicon.",
                            ):
                                entry = build_custom_entry(
                                    language_model=lexicon_model,
                                    meaning=meaning_tag.strip(),
                                    pos=selected_pos,
                                    gloss=gloss_value,
                                    custom_meta=preview_state.get("custom_meta") if isinstance(preview_state, dict) else None,
                                    ipa_override=preview_state.get("ipa") if isinstance(preview_state, dict) else None,
                                    phonotactic_profile_overrides=lexicon_model.get("phonotactic_profile_overrides"),
                                )
                                lexicon = lexicon_model.get("lexicon", [])
                                if not isinstance(lexicon, list):
                                    lexicon = []
                                lexicon.append(entry)
                                lexicon_model["lexicon"] = lexicon
                            lexicon_model = rebuild_indices(lexicon_model)
                            selected_language["lexicon"] = lexicon_model.get("lexicon", [])
                            save_family_language(selected_language, meta)
                            _propagate_descendants(
                                selected_id,
                                "Custom entry added and propagated to descendants.",
                            )
                            st.session_state[preview_key] = None
                            st.success("Custom entry added to the lexicon.")
                            st.rerun()

                            st.divider()
                            st.markdown("**Lexicon overview**")

                            lexicon_entries = lexicon_model.get("lexicon", []) if isinstance(lexicon_model, dict) else []
                            if not isinstance(lexicon_entries, list):
                                lexicon_entries = []

                            search_term = st.text_input(
                                "Search lexicon",
                                key=f"family_lexicon_search_{selected_id}",
                                help="Filter by ID, meaning, gloss, or IPA.",
                            )

                            def entry_source_label(entry: Dict[str, Any]) -> str:
                                if is_custom_entry(entry):
                                    return "Custom"
                                entry_id = str(entry.get("id", ""))
                                source = str(entry.get("source", ""))
                                pos = str(entry.get("pos", ""))
                                if source.startswith("concept-list:"):
                                    return "Concept roots"
                                if source.startswith("grammar:") or entry_id.startswith("PART:") or pos == "PART":
                                    return "Particles"
                                return "Other"

                            source_order = ["Concept roots", "Custom", "Particles", "Other"]
                            available_sources = sorted(
                                {entry_source_label(entry) for entry in lexicon_entries if isinstance(entry, dict)}
                            )
                            source_options = [label for label in source_order if label in available_sources]
                            selected_sources = st.multiselect(
                                "Source filter",
                                options=source_options if source_options else source_order,
                                default=source_options,
                                key=f"family_lexicon_sources_{selected_id}",
                                help="Filter by entry origin.",
                            )

                            pos_codes = sorted(
                                {
                                    str(entry.get("pos", "")).strip()
                                    for entry in lexicon_entries
                                    if isinstance(entry, dict) and str(entry.get("pos", "")).strip()
                                }
                            )
                            selected_pos_codes = st.multiselect(
                                "Part of speech filter",
                                options=pos_codes,
                                default=pos_codes,
                                format_func=format_pos_label,
                                key=f"family_lexicon_pos_{selected_id}",
                                help="Filter by grammatical category.",
                            )

                            def matches_search(entry: Dict[str, Any], needle: str) -> bool:
                                if not needle:
                                    return True
                                hay = " ".join(
                                    [
                                        str(entry.get("id", "")),
                                        str(entry.get("meaning", "")),
                                        str(entry.get("gloss", "")),
                                        str(entry.get("ipa", "")),
                                    ]
                                ).lower()
                                return needle in hay

                            filtered_entries: List[Dict[str, Any]] = []
                            needle = search_term.strip().lower()
                            for entry in lexicon_entries:
                                if not isinstance(entry, dict):
                                    continue
                                if selected_sources and entry_source_label(entry) not in selected_sources:
                                    continue
                                entry_pos = str(entry.get("pos", "")).strip()
                                if selected_pos_codes and entry_pos not in selected_pos_codes:
                                    continue
                                if not matches_search(entry, needle):
                                    continue
                                filtered_entries.append(entry)

                            st.caption("Edits and deletions apply to all entries in this lexicon.")
                            st.caption(f"Showing {len(filtered_entries)} of {len(lexicon_entries)} entries.")
                            overview_rows = [
                                {
                                    "Entry": str(entry.get("id", "")),
                                    "IPA": str(entry.get("ipa", "")),
                                    "Sound-like": ipa_text_to_sound_like(
                                        str(entry.get("ipa", "")),
                                        use_segment_separators=False,
                                        profile_name=romanization_profile,
                                    ),
                                    "Gloss": str(entry.get("gloss", "")),
                                    "Meaning tag": str(entry.get("meaning", "")),
                                    "POS": str(entry.get("pos", "")),
                                    "Source": entry_source_label(entry),
                                    "Custom": "Yes" if is_custom_entry(entry) else "No",
                                    "Delete": False,
                                    "Re-roll": False,
                                }
                                for entry in filtered_entries
                            ]
                            edited_rows = st.data_editor(
                                overview_rows,
                                hide_index=True,
                                use_container_width=True,
                                height=520,
                                key=f"family_lexicon_table_{selected_id}",
                                column_config={
                                    "Re-roll": st.column_config.CheckboxColumn(
                                        "Re-roll",
                                        default=False,
                                        help="Regenerate this entry's IPA form.",
                                    ),
                                    "Delete": st.column_config.CheckboxColumn(
                                        "Delete",
                                        default=False,
                                        help="Remove this entry from the lexicon.",
                                    ),
                                    "Entry": st.column_config.TextColumn("Entry", disabled=True, help="Stable entry ID."),
                                    "IPA": st.column_config.TextColumn("IPA", disabled=True, help="Canonical IPA form."),
                                    "Sound-like": st.column_config.TextColumn(
                                        "Sound-like", disabled=True, help="Approximate romanization display."
                                    ),
                                    "Gloss": st.column_config.TextColumn("Gloss", help="Edit the gloss field."),
                                    "Meaning tag": st.column_config.TextColumn("Meaning tag", help="Edit the meaning tag."),
                                    "POS": st.column_config.SelectboxColumn(
                                        "POS", options=pos_options, help="Edit part of speech."
                                    ),
                                    "Source": st.column_config.TextColumn("Source", disabled=True, help="Entry origin."),
                                    "Custom": st.column_config.TextColumn("Custom", disabled=True, help="Custom entry flag."),
                                },
                            )
                            if hasattr(edited_rows, "to_dict"):
                                edited_rows = edited_rows.to_dict(orient="records")
                            if not isinstance(edited_rows, list):
                                edited_rows = []

                            entry_map = {
                                str(entry.get("id", "")).strip(): entry
                                for entry in lexicon_entries
                                if isinstance(entry, dict)
                            }
                            pending_changes = False
                            for row in edited_rows:
                                if not isinstance(row, dict):
                                    continue
                                row_id = str(row.get("Entry", "")).strip()
                                entry = entry_map.get(row_id)
                                if not entry:
                                    continue
                                if row.get("Delete") is True:
                                    pending_changes = True
                                    break
                                row_meaning = str(row.get("Meaning tag", "")).strip()
                                row_gloss = str(row.get("Gloss", "")).strip()
                                row_pos = str(row.get("POS", "")).strip()
                                if (
                                    row_meaning != str(entry.get("meaning", "")).strip()
                                    or row_gloss != str(entry.get("gloss", "")).strip()
                                    or row_pos != str(entry.get("pos", "")).strip()
                                ):
                                    pending_changes = True
                                    break

                            if st.button(
                                "Apply edits / deletions",
                                key=f"family_lexicon_apply_{selected_id}",
                                disabled=not pending_changes,
                                help="Commit edits and deletions to the lexicon.",
                            ):
                                delete_ids: List[str] = []
                                edit_count = 0
                                overrides = meta.get("lexicon_overrides", {})
                                if not isinstance(overrides, dict):
                                    overrides = {}
                                for row in edited_rows:
                                    if not isinstance(row, dict):
                                        continue
                                    row_id = str(row.get("Entry", "")).strip()
                                    entry = entry_map.get(row_id)
                                    if not entry:
                                        continue
                                    wants_delete = row.get("Delete") is True
                                    if wants_delete:
                                        delete_ids.append(row_id)
                                        overrides.pop(row_id, None)
                                        continue
                                    row_meaning = str(row.get("Meaning tag", "")).strip()
                                    row_gloss = str(row.get("Gloss", "")).strip()
                                    row_pos = str(row.get("POS", "")).strip()
                                    changed = False
                                    if row_meaning and row_meaning != str(entry.get("meaning", "")).strip():
                                        entry["meaning"] = row_meaning
                                        changed = True
                                    if row_gloss and row_gloss != str(entry.get("gloss", "")).strip():
                                        entry["gloss"] = row_gloss
                                        changed = True
                                    if row_pos and row_pos in pos_options and row_pos != str(entry.get("pos", "")).strip():
                                        entry["pos"] = row_pos
                                        changed = True
                                    if changed:
                                        edit_count += 1

                                if delete_ids:
                                    lexicon_model["lexicon"] = [
                                        entry
                                        for entry in lexicon_entries
                                        if str(entry.get("id", "")).strip() not in set(delete_ids)
                                    ]
                            meta["lexicon_overrides"] = overrides
                            lexicon_model = rebuild_indices(lexicon_model)
                            selected_language["meta"] = meta
                            selected_language["lexicon"] = lexicon_model.get("lexicon", [])
                            save_family_language(selected_language, meta)
                            _propagate_descendants(
                                selected_id,
                                "Lexicon updates propagated to descendants.",
                            )
                            if edit_count or delete_ids:
                                st.success("Lexicon updates applied.")
                            st.rerun()

                            overview_rerolls = [
                                str(row.get("Entry", "")).strip()
                                for row in edited_rows
                                if isinstance(row, dict) and row.get("Re-roll") is True
                            ]

                            csv_rows = [
                                {
                                    "id": str(entry.get("id", "")),
                                    "ipa": str(entry.get("ipa", "")),
                                    "sound_like": ipa_text_to_sound_like(
                                        str(entry.get("ipa", "")),
                                        use_segment_separators=False,
                                        profile_name=romanization_profile,
                                    ),
                                    "meaning": str(entry.get("meaning", "")),
                                    "gloss": str(entry.get("gloss", "")),
                                    "pos": str(entry.get("pos", "")),
                                    "source": entry_source_label(entry),
                                }
                                for entry in filtered_entries
                                if isinstance(entry, dict)
                            ]
                            lexicon_csv = build_lexicon_csv(csv_rows)
                            st.download_button(
                                label="Download lexicon CSV",
                                data=lexicon_csv,
                                file_name=f"{sanitize_name(meta.get('name', selected_id))}_lexicon.csv",
                                mime="text/csv",
                                use_container_width=True,
                                help="Download the filtered lexicon as CSV.",
                            )
                            if st.button(
                                f"Re-roll {len(overview_rerolls)} selected",
                                key=f"family_reroll_{selected_id}",
                                disabled=not overview_rerolls,
                                help="Regenerate IPA forms for the selected entries.",
                            ):
                                overrides = meta.get("lexicon_overrides", {})
                                if not isinstance(overrides, dict):
                                    overrides = {}
                                for entry_id in overview_rerolls:
                                    reroll_lexicon_entry(
                                        lexicon_model,
                                        entry_id=entry_id,
                                        phonotactic_profile_overrides=lexicon_model.get("phonotactic_profile_overrides"),
                                    )
                                    overrides[entry_id] = find_entry_ipa(lexicon_model, entry_id)
                            meta["lexicon_overrides"] = overrides
                            selected_language["meta"] = meta
                            selected_language["lexicon"] = lexicon_model.get("lexicon", [])
                            save_family_language(selected_language, meta)
                            _propagate_descendants(
                                selected_id,
                                "Re-rolled entries propagated to descendants.",
                            )
                            st.success("Re-rolled entries saved.")
                            st.rerun()

                        with detail_tabs[2]:
                            st.markdown("**Word preview**")
                            lexicon_entries = model.get("lexicon", [])
                            if not isinstance(lexicon_entries, list):
                                lexicon_entries = []

                            def entry_source_label(entry: Dict[str, Any]) -> str:
                                if is_custom_entry(entry):
                                    return "Custom"
                                entry_id = str(entry.get("id", ""))
                                source = str(entry.get("source", ""))
                                pos = str(entry.get("pos", ""))
                                if source.startswith("concept-list:"):
                                    return "Concept roots"
                                if source.startswith("grammar:") or entry_id.startswith("PART:") or pos == "PART":
                                    return "Particles"
                                return "Other"

                            preview_search = st.text_input(
                                "Search words",
                                key=f"family_word_preview_search_{selected_id}",
                                placeholder="Filter by id, meaning, or gloss",
                                help="Filter by ID, meaning, gloss, or IPA.",
                            )
                            preview_filters = st.columns(3)
                            with preview_filters[0]:
                                preview_limit = st.slider(
                                    "Rows to show",
                                    min_value=20,
                                    max_value=300,
                                    value=80,
                                    step=20,
                                    key=f"family_word_preview_limit_{selected_id}",
                                    help="Limit the number of rows shown.",
                                )
                            with preview_filters[1]:
                                preview_sources = sorted(
                                    {entry_source_label(entry) for entry in lexicon_entries if isinstance(entry, dict)}
                                )
                                selected_preview_sources = st.multiselect(
                                    "Source filter",
                                    options=preview_sources,
                                    default=preview_sources,
                                    key=f"family_word_preview_sources_{selected_id}",
                                    help="Filter by entry origin.",
                                )
                            with preview_filters[2]:
                                preview_pos_codes = sorted(
                                    {
                                        str(entry.get("pos", "")).strip()
                                        for entry in lexicon_entries
                                        if isinstance(entry, dict) and str(entry.get("pos", "")).strip()
                                    }
                                )
                                selected_preview_pos = st.multiselect(
                                    "Part of speech filter",
                                    options=preview_pos_codes,
                                    default=preview_pos_codes,
                                    format_func=format_pos_label,
                                    key=f"family_word_preview_pos_{selected_id}",
                                    help="Filter by grammatical category.",
                                )

                            needle = preview_search.strip().lower()
                            preview_rows = []
                            for entry in lexicon_entries:
                                if not isinstance(entry, dict):
                                    continue
                                if selected_preview_sources and entry_source_label(entry) not in selected_preview_sources:
                                    continue
                                entry_pos = str(entry.get("pos", "")).strip()
                                if selected_preview_pos and entry_pos not in selected_preview_pos:
                                    continue
                                entry_id = str(entry.get("id", "")).strip()
                                meaning = str(entry.get("meaning", "")).strip()
                                gloss = str(entry.get("gloss", "")).strip()
                                if needle and needle not in f"{entry_id} {meaning} {gloss}".lower():
                                    continue
                                ipa_value = str(entry.get("ipa", "")).strip()
                                preview_rows.append(
                                    {
                                        "Entry": entry_id,
                                        "IPA": ipa_value,
                                        "Sound-like": ipa_text_to_sound_like(
                                            ipa_value,
                                            use_segment_separators=False,
                                            profile_name=romanization_profile,
                                        ),
                                        "Gloss": gloss,
                                        "Meaning tag": meaning,
                                        "POS": format_pos_label(entry_pos),
                                        "Source": entry_source_label(entry),
                                    }
                                )
                                if len(preview_rows) >= preview_limit:
                                    break

                            st.caption(f"Showing {len(preview_rows)} of {len(lexicon_entries)} entries.")
                            st.dataframe(preview_rows, hide_index=True, use_container_width=True)

                            st.divider()
                            st.markdown("**Sample sentences**")
                            sample_sentence_count = st.number_input(
                                "Sentence samples",
                                min_value=1,
                                max_value=20,
                                value=5,
                                step=1,
                                key=f"family_sentence_count_{selected_id}",
                                help="How many sentences to generate per click.",
                            )
                            words_range = st.slider(
                                "Words per sentence",
                                min_value=2,
                                max_value=12,
                                value=(4, 8),
                                key=f"family_words_range_{selected_id}",
                                help="Range of word counts per sentence.",
                            )
                            if st.button(
                                "Generate sentences",
                                key=f"family_generate_sentences_{selected_id}",
                                help="Generate sample sentences for this language.",
                            ):
                                sentences = build_sample_sentences(
                                    vowels=model.get("inventory", {}).get("vowels", []),
                                    consonants=model.get("inventory", {}).get("consonants", []),
                                    sample_count=int(sample_sentence_count),
                                    syllable_range=tuple(model.get("syllable_range", [1, 2])),
                                    words_range=tuple(words_range),
                                    syllable_separator=str(model.get("syllable_separator", "")),
                                    style_name=str(model.get("style_name", DEFAULT_STYLE_PRESET)),
                                    concept_list_name=str(model.get("concept_list_name", DEFAULT_CONCEPT_LIST)),
                                    grammar_profile_name=str(model.get("grammar_profile_name", DEFAULT_GRAMMAR_PROFILE)),
                                    language_model=model,
                                    phonotactic_profile_overrides=model.get("phonotactic_profile_overrides"),
                                )
                                st.session_state[f"family_sentences_{selected_id}"] = sentences
                            sentences = st.session_state.get(f"family_sentences_{selected_id}", [])
                            if sentences:
                                st.dataframe(
                                    [
                                        {
                                            "IPA": s.get("ipa", ""),
                                            "Gloss": s.get("gloss", ""),
                                            "Template": s.get("template", ""),
                                            "Sound-like": ipa_text_to_sound_like(
                                                str(s.get("ipa", "")),
                                                use_segment_separators=False,
                                                profile_name=romanization_profile,
                                            ),
                                        }
                                        for s in sentences
                                    ],
                                    hide_index=True,
                                    use_container_width=True,
                                )
                            else:
                                st.info("No sentences generated yet.")

        with help_col:
            st.markdown("### Help")
            topic_key = st.session_state.get("help_topic")
            if topic_key and topic_key in help_topics:
                topic = help_topics[topic_key]
                st.markdown(f"**{topic['title']}**")
                st.write(topic["body"])
            else:
                st.write("Click a ? icon to learn about a control.")


def main() -> None:
    st.set_page_config(page_title="Conlang Sound Toolkit", page_icon="🔤", layout="wide")
    inject_custom_css()
    render_hero()

    mode = st.sidebar.radio(
        "Mode",
        options=["Single Language", "Language Family"],
        index=0,
        key="app_mode",
        help="Switch between single-language and family workflows.",
    )
    if mode == "Language Family":
        render_language_family_ui()
    else:
        render_single_language_ui()


if __name__ == "__main__":
    main()
