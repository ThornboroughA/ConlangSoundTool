#!/usr/bin/env python3
"""Simple Streamlit UI for the Sound Inventory Generator."""

from __future__ import annotations

import io
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

import sound_inventory_generator as generator
from sample_text_generator import (
    CONCEPT_LIST_PRESETS,
    GRAMMAR_PROFILES,
    STYLE_PRESETS,
    build_language_model,
    build_sample_sentences,
    build_sample_words,
    model_matches,
)

IPA_TO_ROMAN_DIACRITICS: Dict[str, str] = {
    # Vowels
    "a": "a",
    "ɑ": "ā",
    "ɐ": "ă",
    "æ": "ae",
    "e": "e",
    "eɪ": "ei",
    "ɛ": "e",
    "ə": "ə",
    "ɜ": "er",
    "ɪ": "ĭ",
    "i": "i",
    "o": "o",
    "oʊ": "ou",
    "ɔ": "ô",
    "ɒ": "ŏ",
    "ʊ": "ŭ",
    "u": "u",
    "ʌ": "ŭ",
    "y": "ü",
    "ø": "ö",
    "œ": "œ",
    "ɨ": "ɨ",
    "ʉ": "ǖ",
    "ɯ": "eu",
    # Stops / affricates
    "p": "p",
    "pʰ": "ph",
    "b": "b",
    "t": "t",
    "tʰ": "th",
    "d": "d",
    "ʈ": "ṭ",
    "ɖ": "ḍ",
    "k": "k",
    "kʰ": "kh",
    "g": "g",
    "q": "q",
    "ɢ": "ġ",
    "ʔ": "’",
    "c": "ky",
    "ɟ": "gy",
    "tʃ": "ch",
    "dʒ": "j",
    "tɕ": "j",
    "tɕʰ": "ch",
    # Nasals
    "m": "m",
    "n": "n",
    "ŋ": "ng",
    "ɲ": "ñ",
    "ɳ": "ṇ",
    # Fricatives
    "f": "f",
    "v": "v",
    "ɸ": "ph",
    "β": "bh",
    "θ": "th",
    "ð": "dh",
    "s": "s",
    "z": "z",
    "ʃ": "sh",
    "ʒ": "zh",
    "ʂ": "ṣ",
    "ʐ": "ẓ",
    "x": "kh",
    "χ": "qh",
    "ɣ": "gh",
    "h": "h",
    "ʁ": "ṛ",
    # Rhotics / laterals / approximants
    "r": "rr",
    "ɾ": "r",
    "ɽ": "ṛ",
    "ɻ": "r",
    "l": "l",
    "ɭ": "ḷ",
    "ʋ": "w",
    "w": "w",
    "j": "y",
    # Other
    "ʙ": "br",
}

IPA_TO_ROMAN_ASCII: Dict[str, str] = {
    # Vowels
    "a": "a",
    "ɑ": "aa",
    "ɐ": "a",
    "æ": "ae",
    "e": "e",
    "eɪ": "ei",
    "ɛ": "e",
    "ə": "e",
    "ɜ": "er",
    "ɪ": "i",
    "i": "i",
    "o": "o",
    "oʊ": "ou",
    "ɔ": "o",
    "ɒ": "o",
    "ʊ": "u",
    "u": "u",
    "ʌ": "u",
    "y": "u",
    "ø": "oe",
    "œ": "oe",
    "ɨ": "y",
    "ʉ": "u",
    "ɯ": "eu",
    # Stops / affricates
    "p": "p",
    "pʰ": "ph",
    "b": "b",
    "t": "t",
    "tʰ": "th",
    "d": "d",
    "ʈ": "t",
    "ɖ": "d",
    "k": "k",
    "kʰ": "kh",
    "g": "g",
    "q": "q",
    "ɢ": "g",
    "ʔ": "'",
    "c": "ky",
    "ɟ": "gy",
    "tʃ": "ch",
    "dʒ": "j",
    "tɕ": "j",
    "tɕʰ": "ch",
    # Nasals
    "m": "m",
    "n": "n",
    "ŋ": "ng",
    "ɲ": "ny",
    "ɳ": "n",
    # Fricatives
    "f": "f",
    "v": "v",
    "ɸ": "ph",
    "β": "bh",
    "θ": "th",
    "ð": "dh",
    "s": "s",
    "z": "z",
    "ʃ": "sh",
    "ʒ": "zh",
    "ʂ": "sh",
    "ʐ": "zh",
    "x": "kh",
    "χ": "qh",
    "ɣ": "gh",
    "h": "h",
    "ʁ": "r",
    # Rhotics / laterals / approximants
    "r": "rr",
    "ɾ": "r",
    "ɽ": "r",
    "ɻ": "r",
    "l": "l",
    "ɭ": "l",
    "ʋ": "w",
    "w": "w",
    "j": "y",
    # Other
    "ʙ": "br",
}

ROMANIZATION_PROFILES: Dict[str, Dict[str, str]] = {
    "Diacritics (recommended)": IPA_TO_ROMAN_DIACRITICS,
    "ASCII": IPA_TO_ROMAN_ASCII,
}
DEFAULT_ROMANIZATION_PROFILE = "Diacritics (recommended)"

def romanization_map(profile_name: str) -> Dict[str, str]:
    """Return the chosen IPA->romanization map with safe fallback."""
    return ROMANIZATION_PROFILES.get(profile_name, ROMANIZATION_PROFILES[DEFAULT_ROMANIZATION_PROFILE])


def segment_keys(profile_name: str) -> List[str]:
    """Return sorted IPA keys (longest first) for robust tokenization."""
    return sorted(romanization_map(profile_name).keys(), key=len, reverse=True)


def hint_for_segment(segment: str, profile_name: str = DEFAULT_ROMANIZATION_PROFILE) -> Dict[str, str]:
    """Return romanization metadata for an IPA segment."""
    mapped = romanization_map(profile_name).get(segment)
    if mapped:
        return {"sound_like": mapped, "example": ""}
    return {"sound_like": "(no romanization yet)", "example": ""}


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
            tokens.append(("literal", text[index]))
            index += 1
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


def sanitize_name(value: str) -> str:
    """Convert free text to a safe lowercase filename."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_").lower()
    return cleaned or "generated_preset"


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


def inject_custom_css() -> None:
    """Apply visual polish while keeping Streamlit-native layout behavior."""
    st.markdown(
        """
        <style>
        :root {
            --bg-start: #f2f7f4;
            --bg-end: #e6f0ea;
            --panel: rgba(255, 255, 255, 0.84);
            --ink-strong: #1a2b23;
            --ink-muted: #4a6257;
            --line: #d2e0d7;
            --accent: #1f7a5a;
            --accent-soft: #2f9f76;
            --accent-warm: #a06c2f;
        }

        .stApp {
            background:
                radial-gradient(1200px 500px at 12% -18%, #dceadf 0%, transparent 60%),
                radial-gradient(900px 400px at 110% 0%, #e6ece2 0%, transparent 65%),
                linear-gradient(180deg, var(--bg-start), var(--bg-end));
        }

        .main .block-container {
            max-width: 1160px;
            padding-top: 1.1rem;
            padding-bottom: 2rem;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"] {
            color: var(--ink-strong);
            font-family: "Segoe UI Variable", "Trebuchet MS", "Verdana", sans-serif;
        }

        .material-symbols-rounded {
            font-family: "Material Symbols Rounded" !important;
        }

        h1, h2, h3, [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 {
            font-family: "Palatino Linotype", "Book Antiqua", "Georgia", serif;
            letter-spacing: 0.01em;
        }

        .hero-shell {
            border: 1px solid var(--line);
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.88), rgba(242, 249, 245, 0.86));
            border-radius: 16px;
            padding: 1.1rem 1.2rem 1.15rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 24px rgba(40, 70, 55, 0.06);
        }

        .hero-eyebrow {
            display: inline-block;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            font-size: 0.74rem;
            color: var(--accent);
            background: rgba(31, 122, 90, 0.12);
            border: 1px solid rgba(31, 122, 90, 0.28);
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            margin-bottom: 0.45rem;
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
            background: linear-gradient(180deg, rgba(246, 251, 248, 0.98), rgba(236, 245, 239, 0.98));
            border-right: 1px solid var(--line);
        }

        [data-testid="stMetric"] {
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 12px;
            padding: 0.55rem 0.7rem;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.75);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 12px;
            overflow: hidden;
        }

        .stButton > button, .stDownloadButton > button {
            border-radius: 10px;
            border: 1px solid rgba(31, 122, 90, 0.45);
            background: linear-gradient(180deg, #ffffff, #eef7f1);
        }

        .stButton > button[kind="primary"] {
            border: none;
            background: linear-gradient(145deg, var(--accent), var(--accent-soft));
            color: white;
            box-shadow: 0 8px 18px rgba(31, 122, 90, 0.24);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 9px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.74);
        }

        .stTabs [aria-selected="true"] {
            border-color: rgba(31, 122, 90, 0.42);
            background: rgba(238, 248, 242, 0.96);
        }

        .section-kicker {
            color: var(--accent-warm);
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-size: 0.73rem;
            margin-bottom: 0.1rem;
            font-weight: 600;
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
            <h1 class="hero-title">Build stable naming constraints without full conlang overhead.</h1>
            <p class="hero-copy">
                Blend real-language inventories, tune the flavor, and save reusable presets.
                Keep your names coherent now, then evolve into deeper linguistics later.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_mix_metrics(selected_presets: List[str], selected_rules: List[str], random_weight: float, total_weight: float) -> None:
    """Show at-a-glance settings metrics for current controls."""
    metric_cols = st.columns(4)
    metric_cols[0].metric("Sources", f"{len(selected_presets)}")
    metric_cols[1].metric("Rules", f"{len(selected_rules)}")
    metric_cols[2].metric("Random Share", f"{mix_share(random_weight, total_weight):.1f}%")
    metric_cols[3].metric("Total Weight", f"{total_weight:.2f}")


def render_inventory_metrics(inventory: Dict[str, List[str]], applied_rule_count: int) -> None:
    """Show concise stats for the latest generated inventory."""
    vowels_count = len(inventory.get("vowels", []))
    consonants_count = len(inventory.get("consonants", []))
    total_count = vowels_count + consonants_count
    metric_cols = st.columns(4)
    metric_cols[0].metric("Vowels", f"{vowels_count}")
    metric_cols[1].metric("Consonants", f"{consonants_count}")
    metric_cols[2].metric("Total Segments", f"{total_count}")
    metric_cols[3].metric("Rules Applied", f"{applied_rule_count}")


def main() -> None:
    st.set_page_config(page_title="Sound Inventory Generator", page_icon="🔤", layout="wide")
    inject_custom_css()
    render_hero()

    preset_names = list_json_names(generator.PRESETS_DIR)
    rule_names = list_json_names(generator.RULES_DIR)

    if not preset_names:
        st.error("No preset files found. Add JSON files to presets/ and reload.")
        st.stop()

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
                )
                weights.append(weight)

        random_weight = st.slider(
            "Random weight (master pool)",
            min_value=0.0,
            max_value=1.0,
            value=0.10,
            step=0.05,
        )

        master_default = preset_names.index("random_master") if "random_master" in preset_names else 0
        master_preset = st.selectbox(
            "Master preset for random picks",
            options=preset_names,
            index=master_default,
        )

        selected_rules = st.multiselect(
            "Sound-change rules (optional)",
            options=rule_names,
            help="Rules are applied in order, from top to bottom.",
        )

    with run_col:
        st.markdown("**Output settings**")
        language_name = st.text_input("Generated language name", value="GeneratedLanguage")
        output_dir_value = st.text_input("Output folder", value="outputs/ui_run")
        romanization_profile = st.selectbox(
            "Romanization profile",
            options=list(ROMANIZATION_PROFILES.keys()),
            index=0,
            help="Affects Sound-like rendering in tables, samples, and pronunciation CSV.",
        )
        use_seed = st.checkbox("Use fixed random seed", value=False)
        seed_value = st.number_input(
            "Seed value",
            min_value=0,
            max_value=2_147_483_647,
            value=42,
            step=1,
            disabled=not use_seed,
        )
        generate = st.button("Generate Inventory", type="primary", use_container_width=True)

        st.caption(
            "Tip: keep a fixed seed while exploring, then save successful inventories as presets."
        )

    total_weight = sum(weights) + (random_weight if random_weight > 0 else 0.0)
    render_mix_metrics(
        selected_presets=selected_presets,
        selected_rules=selected_rules,
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

                if selected_rules:
                    mixed_inventory = generator.apply_rules(mixed_inventory, selected_rules)

                output_dir = resolve_output_dir(output_dir_value)
                generator.save_inventory_as_json(mixed_inventory, str(output_dir), language_name)
                generator.save_inventory_as_cldf(mixed_inventory, str(output_dir), language_name)

                st.session_state["last_inventory"] = mixed_inventory
                st.session_state["last_language_name"] = language_name
                st.session_state["last_output_dir"] = str(output_dir)
                st.session_state["last_rule_sets"] = selected_rules[:]
                st.session_state["last_generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.pop("sample_words", None)
                st.session_state.pop("sample_sentences", None)
                st.session_state.pop("sample_language_model", None)

                st.success(f"Generated '{language_name}' and saved files to {output_dir}")
            except Exception as exc:  # pragma: no cover - UI safety net
                st.exception(exc)

    latest_inventory = st.session_state.get("last_inventory")
    latest_language_name = st.session_state.get("last_language_name", "GeneratedLanguage")
    latest_rule_sets = st.session_state.get("last_rule_sets", [])
    latest_generated_at = st.session_state.get("last_generated_at")

    if latest_inventory:
        st.divider()
        st.markdown('<div class="section-kicker">Step 2</div>', unsafe_allow_html=True)
        st.subheader("Review Latest Result")
        render_inventory_metrics(latest_inventory, applied_rule_count=len(latest_rule_sets))

        output_dir_label = st.session_state.get("last_output_dir", "(unknown)")
        generated_time_label = f" at {latest_generated_at}" if latest_generated_at else ""
        st.caption(f"Latest files were written to: {output_dir_label}{generated_time_label}")

        preset_payload = inventory_as_preset_payload(latest_inventory, latest_language_name)
        selected_result_view = st.radio(
            "Result view",
            options=["Inventory", "Sample Text", "Export and Reuse"],
            horizontal=True,
            key="result_view_selector",
            label_visibility="collapsed",
        )

        if selected_result_view == "Inventory":
            st.caption(
                f"Sound-like notes are approximation helpers; IPA remains canonical. "
                f"Profile: {romanization_profile}."
            )
            st.caption("Example column is intentionally blank for now (ready for your later notes).")
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

        elif selected_result_view == "Sample Text":
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
            st.caption("Word rows include meaning tags + part-of-speech labels from the shared lexicon.")

            sample_controls_left, sample_controls_right = st.columns(2)
            with sample_controls_left:
                sample_word_count = st.number_input(
                    "Word samples per run",
                    min_value=1,
                    max_value=50,
                    value=15,
                    step=1,
                    key="sample_word_count",
                )
                sample_syllable_range = st.slider(
                    "Syllables per generated word",
                    min_value=1,
                    max_value=5,
                    value=(1, 3),
                    key="sample_syllable_range",
                )
            with sample_controls_right:
                sample_sentence_count = st.number_input(
                    "Sentence samples per run",
                    min_value=1,
                    max_value=30,
                    value=6,
                    step=1,
                    key="sample_sentence_count",
                )
                sample_words_range = st.slider(
                    "Words per generated sentence",
                    min_value=2,
                    max_value=14,
                    value=(4, 8),
                    key="sample_sentence_words_range",
                )

            show_syllable_breaks = st.checkbox(
                "Show syllable separators (.)",
                value=False,
                key="sample_show_syllable_breaks",
            )
            show_segment_separators = st.checkbox(
                "Show segment separators (-) in sound-like text",
                value=False,
                key="sample_show_segment_separators",
            )
            syllable_separator = "." if show_syllable_breaks else ""

            samples_button_col_1, samples_button_col_2, samples_button_col_3 = st.columns(3)
            with samples_button_col_1:
                generate_word_samples = st.button("Generate Word Samples", key="generate_word_samples")
            with samples_button_col_2:
                generate_sentence_samples = st.button("Generate Sentence Samples", key="generate_sentence_samples")
            with samples_button_col_3:
                generate_both_samples = st.button("Generate Both", key="generate_both_samples")

            latest_vowels = latest_inventory.get("vowels", [])
            latest_consonants = latest_inventory.get("consonants", [])

            generate_any_samples = generate_word_samples or generate_sentence_samples or generate_both_samples
            if generate_any_samples:
                cached_model = st.session_state.get("sample_language_model")
                if not model_matches(
                    cached_model,
                    vowels=latest_vowels,
                    consonants=latest_consonants,
                    syllable_range=sample_syllable_range,
                    syllable_separator=syllable_separator,
                    style_name=selected_style,
                    concept_list_name=selected_concept_list,
                    grammar_profile_name=selected_grammar_profile,
                ):
                    cached_model = build_language_model(
                        vowels=latest_vowels,
                        consonants=latest_consonants,
                        syllable_range=sample_syllable_range,
                        syllable_separator=syllable_separator,
                        style_name=selected_style,
                        concept_list_name=selected_concept_list,
                        grammar_profile_name=selected_grammar_profile,
                    )
                    st.session_state["sample_language_model"] = cached_model

            if generate_word_samples or generate_both_samples:
                st.session_state["sample_words"] = build_sample_words(
                    latest_vowels,
                    latest_consonants,
                    sample_count=int(sample_word_count),
                    syllable_range=sample_syllable_range,
                    syllable_separator=syllable_separator,
                    style_name=selected_style,
                    concept_list_name=selected_concept_list,
                    grammar_profile_name=selected_grammar_profile,
                    language_model=st.session_state.get("sample_language_model"),
                )

            if generate_sentence_samples or generate_both_samples:
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
                    language_model=st.session_state.get("sample_language_model"),
                )

            sample_words = st.session_state.get("sample_words", [])
            sample_sentences = st.session_state.get("sample_sentences", [])

            if sample_words:
                st.markdown("**Word samples**")
                st.dataframe(
                    [
                        {
                            "IPA": str(word.get("ipa", "")) if isinstance(word, dict) else str(word),
                            "Part of speech": str(word.get("part_of_speech", "")) if isinstance(word, dict) else "",
                            "Meaning tag": str(word.get("meaning", "")) if isinstance(word, dict) else "",
                            "Gloss": str(word.get("gloss", "")) if isinstance(word, dict) else "",
                            "Sound-like": ipa_text_to_sound_like(
                                str(word.get("ipa", "")) if isinstance(word, dict) else str(word),
                                use_segment_separators=show_segment_separators,
                                profile_name=romanization_profile,
                            ),
                        }
                        for word in sample_words
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
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

        else:
            st.caption("Download ready-to-reuse files or save this result as a preset for future sessions.")

            download_col_1, download_col_2 = st.columns(2)
            with download_col_1:
                st.download_button(
                    label="Download preset JSON",
                    data=json.dumps(preset_payload, ensure_ascii=False, indent=2),
                    file_name=f"{sanitize_name(latest_language_name)}.json",
                    mime="application/json",
                    use_container_width=True,
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
                )

            st.markdown("**Save latest result as preset**")
            preset_filename = st.text_input(
                "Preset filename (without .json)",
                value=sanitize_name(latest_language_name),
                key="preset_filename",
            )
            overwrite_existing = st.checkbox("Overwrite existing preset file", value=False)
            save_preset = st.button("Save to presets/", use_container_width=True)

            if save_preset:
                safe_name = sanitize_name(preset_filename)
                preset_path = Path(generator.PRESETS_DIR) / f"{safe_name}.json"

                if preset_path.exists() and not overwrite_existing:
                    st.error(f"`{preset_path.name}` already exists. Enable overwrite to replace it.")
                else:
                    with preset_path.open("w", encoding="utf-8") as file:
                        json.dump(preset_payload, file, ensure_ascii=False, indent=2)
                    st.success(f"Saved preset: {preset_path}")


if __name__ == "__main__":
    main()
