#!/usr/bin/env python3
"""Simple Streamlit UI for the Sound Inventory Generator."""

from __future__ import annotations

import io
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st

import sound_inventory_generator as generator

IPA_SOUND_ALIKES: Dict[str, Dict[str, str]] = {
    "a": {"sound_like": "ah", "example": "father"},
    "ɑ": {"sound_like": "ah", "example": "father"},
    "ɐ": {"sound_like": "uh/ah", "example": "about (stressed)"},
    "æ": {"sound_like": "a", "example": "cat"},
    "e": {"sound_like": "eh", "example": "French ete"},
    "eɪ": {"sound_like": "ay", "example": "say"},
    "ɛ": {"sound_like": "eh", "example": "bet"},
    "ə": {"sound_like": "uh", "example": "sofa"},
    "ɜ": {"sound_like": "er", "example": "bird"},
    "ɪ": {"sound_like": "ih", "example": "bit"},
    "i": {"sound_like": "ee", "example": "machine"},
    "o": {"sound_like": "oh", "example": "Italian sole"},
    "oʊ": {"sound_like": "oh", "example": "go"},
    "ɔ": {"sound_like": "aw", "example": "thought"},
    "ɒ": {"sound_like": "o", "example": "British lot"},
    "ʊ": {"sound_like": "oo", "example": "book"},
    "u": {"sound_like": "oo", "example": "flute"},
    "ʌ": {"sound_like": "uh", "example": "strut"},
    "y": {"sound_like": "ee with rounded lips", "example": "French tu"},
    "ø": {"sound_like": "ay with rounded lips", "example": "French deux"},
    "œ": {"sound_like": "eh with rounded lips", "example": "French soeur"},
    "ɨ": {"sound_like": "central ee", "example": "Russian y"},
    "ʉ": {"sound_like": "central oo", "example": "Swedish du"},
    "ɯ": {"sound_like": "unrounded oo", "example": "Korean eu"},
    "p": {"sound_like": "p", "example": "spin"},
    "pʰ": {"sound_like": "p (breathy)", "example": "pin"},
    "b": {"sound_like": "b", "example": "bat"},
    "t": {"sound_like": "t", "example": "stop"},
    "tʰ": {"sound_like": "t (breathy)", "example": "top"},
    "d": {"sound_like": "d", "example": "dog"},
    "ʈ": {"sound_like": "retroflex t", "example": "Indian-type t"},
    "ɖ": {"sound_like": "retroflex d", "example": "Indian-type d"},
    "k": {"sound_like": "k", "example": "skill"},
    "kʰ": {"sound_like": "k (breathy)", "example": "kill"},
    "g": {"sound_like": "g", "example": "go"},
    "q": {"sound_like": "deep k", "example": "uvular k"},
    "ɢ": {"sound_like": "deep g", "example": "uvular g"},
    "ʔ": {"sound_like": "glottal stop", "example": "uh-oh (middle)"},
    "c": {"sound_like": "ky", "example": "palatal k"},
    "ɟ": {"sound_like": "gy", "example": "palatal g"},
    "m": {"sound_like": "m", "example": "man"},
    "n": {"sound_like": "n", "example": "no"},
    "ŋ": {"sound_like": "ng", "example": "sing"},
    "ɲ": {"sound_like": "ny", "example": "canyon"},
    "ɳ": {"sound_like": "retroflex n", "example": "Indian-type n"},
    "f": {"sound_like": "f", "example": "fan"},
    "v": {"sound_like": "v", "example": "van"},
    "ɸ": {"sound_like": "soft f", "example": "Japanese fu"},
    "β": {"sound_like": "soft b/v", "example": "Spanish b between vowels"},
    "θ": {"sound_like": "th", "example": "thin"},
    "ð": {"sound_like": "th", "example": "this"},
    "s": {"sound_like": "s", "example": "see"},
    "z": {"sound_like": "z", "example": "zoo"},
    "ʃ": {"sound_like": "sh", "example": "ship"},
    "ʒ": {"sound_like": "zh", "example": "measure"},
    "ʂ": {"sound_like": "retroflex sh", "example": "Russian sh"},
    "ʐ": {"sound_like": "retroflex zh", "example": "Russian zh"},
    "x": {"sound_like": "kh", "example": "Bach"},
    "χ": {"sound_like": "deeper kh", "example": "uvular fricative"},
    "ɣ": {"sound_like": "soft g", "example": "Spanish g between vowels"},
    "h": {"sound_like": "h", "example": "hat"},
    "ʁ": {"sound_like": "French r", "example": "Paris r"},
    "r": {"sound_like": "trilled r", "example": "Spanish perro"},
    "ɾ": {"sound_like": "tap r", "example": "American t in water"},
    "ɽ": {"sound_like": "retroflex flap", "example": "Indian-type r"},
    "ɻ": {"sound_like": "retroflex r", "example": "American r-ish"},
    "l": {"sound_like": "l", "example": "leaf"},
    "ɭ": {"sound_like": "retroflex l", "example": "Indian-type l"},
    "ʋ": {"sound_like": "between v and w", "example": "Hindi v/w"},
    "w": {"sound_like": "w", "example": "we"},
    "j": {"sound_like": "y", "example": "yes"},
    "tʃ": {"sound_like": "ch", "example": "church"},
    "dʒ": {"sound_like": "j", "example": "judge"},
    "tɕ": {"sound_like": "soft ch", "example": "Korean j-ish"},
    "tɕʰ": {"sound_like": "soft ch (breathy)", "example": "Korean ch-ish"},
    "ʙ": {"sound_like": "bilabial trill", "example": "trilled lips"},
}


def hint_for_segment(segment: str) -> Dict[str, str]:
    """Return a user-friendly pronunciation hint for an IPA segment."""
    hint = IPA_SOUND_ALIKES.get(segment)
    if hint:
        return hint
    return {"sound_like": "(no hint yet)", "example": "keep IPA as source of truth"}


def build_segment_rows(segments: List[str], include_hints: bool) -> List[Dict[str, str]]:
    """Build table rows for segment display."""
    rows: List[Dict[str, str]] = []
    for segment in segments:
        if include_hints:
            hint = hint_for_segment(segment)
            rows.append(
                {
                    "IPA": segment,
                    "Sound-alike": hint["sound_like"],
                    "Example": hint["example"],
                }
            )
        else:
            rows.append({"IPA": segment})
    return rows


def build_pronunciation_csv(vowels: List[str], consonants: List[str]) -> str:
    """Build a downloadable CSV pronunciation guide for the latest result."""
    output = io.StringIO()
    output.write("Type,IPA,Sound-alike,Example\n")
    for segment_type, segments in [("vowel", vowels), ("consonant", consonants)]:
        for segment in segments:
            hint = hint_for_segment(segment)
            output.write(f"{segment_type},{segment},{hint['sound_like']},{hint['example']}\n")
    return output.getvalue()


def choose_segment(segments: List[str]) -> str:
    """Return a random segment, or empty string if unavailable."""
    if not segments:
        return ""
    return random.choice(segments)


def generate_syllable(vowels: List[str], consonants: List[str]) -> str:
    """Generate a syllable-like chunk from the current inventory."""
    if not vowels and not consonants:
        return ""

    if not consonants:
        shape = random.choices(["V", "VV"], weights=[0.75, 0.25], k=1)[0]
    elif not vowels:
        shape = random.choices(["C", "CC"], weights=[0.85, 0.15], k=1)[0]
    else:
        shape = random.choices(
            ["V", "CV", "VC", "CVC", "CVV", "VCV"],
            weights=[0.10, 0.40, 0.12, 0.23, 0.08, 0.07],
            k=1,
        )[0]

    parts: List[str] = []
    for slot in shape:
        segment = choose_segment(consonants) if slot == "C" else choose_segment(vowels)
        if segment:
            parts.append(segment)
    return "".join(parts)


def generate_word(
    vowels: List[str],
    consonants: List[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
) -> str:
    """Generate a placeholder word made from inventory segments."""
    min_syllables, max_syllables = syllable_range
    min_syllables = max(1, int(min_syllables))
    max_syllables = max(min_syllables, int(max_syllables))

    syllable_count = random.randint(min_syllables, max_syllables)
    syllables = [generate_syllable(vowels, consonants) for _ in range(syllable_count)]
    syllables = [syllable for syllable in syllables if syllable]

    if not syllables:
        return choose_segment(vowels) or choose_segment(consonants) or "a"
    return syllable_separator.join(syllables)


def generate_sentence(
    vowels: List[str],
    consonants: List[str],
    syllable_range: Tuple[int, int],
    words_range: Tuple[int, int],
    syllable_separator: str,
) -> str:
    """Generate a placeholder sentence from inventory-derived words."""
    min_words, max_words = words_range
    min_words = max(1, int(min_words))
    max_words = max(min_words, int(max_words))

    word_count = random.randint(min_words, max_words)
    words = [
        generate_word(vowels, consonants, syllable_range, syllable_separator)
        for _ in range(word_count)
    ]
    punctuation = random.choices([".", "?", "!"], weights=[0.75, 0.15, 0.10], k=1)[0]
    return f"{' '.join(words)}{punctuation}"


def build_sample_words(
    vowels: List[str],
    consonants: List[str],
    sample_count: int,
    syllable_range: Tuple[int, int],
    syllable_separator: str,
) -> List[str]:
    """Return a list of generated placeholder words."""
    count = max(1, int(sample_count))
    return [
        generate_word(vowels, consonants, syllable_range, syllable_separator)
        for _ in range(count)
    ]


def build_sample_sentences(
    vowels: List[str],
    consonants: List[str],
    sample_count: int,
    syllable_range: Tuple[int, int],
    words_range: Tuple[int, int],
    syllable_separator: str,
) -> List[str]:
    """Return a list of generated placeholder sentences."""
    count = max(1, int(sample_count))
    return [
        generate_sentence(
            vowels,
            consonants,
            syllable_range=syllable_range,
            words_range=words_range,
            syllable_separator=syllable_separator,
        )
        for _ in range(count)
    ]


def mix_share(weight: float, total_weight: float) -> float:
    """Return a safe percentage share for a source weight."""
    if total_weight <= 0:
        return 0.0
    return (weight / total_weight) * 100.0


def load_preset_safe(name: str) -> Dict[str, List[str]]:
    """Load preset data, returning empty lists on load issues."""
    try:
        return generator.load_preset(name)
    except Exception as exc:  # pragma: no cover - UI safety net
        st.warning(f"Could not load preset '{name}': {exc}")
        return {"vowels": [], "consonants": []}


def render_mix_reference_panel(
    selected_presets: List[str],
    weights: List[float],
    random_weight: float,
    master_preset: str,
    include_hints: bool,
) -> None:
    """Render a dynamic guide to help users understand active mix sources."""
    st.caption("Weights are relative proportions: 0.2 + 0.4 behaves the same as 1 + 2.")

    if not selected_presets:
        st.info("Select presets to preview their sounds and contribution to the mix.")
        return

    total_weight = sum(weights) + (random_weight if random_weight > 0 else 0.0)
    summary_rows: List[Dict[str, str]] = []
    loaded_presets: Dict[str, Dict[str, List[str]]] = {}

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
                display_segment_table("Vowels", preset_data.get("vowels", []), include_hints=include_hints)
            with col_right:
                display_segment_table("Consonants", preset_data.get("consonants", []), include_hints=include_hints)

    if random_weight > 0:
        random_key = f"random::{master_preset}"
        share_label = mix_share(random_weight, total_weight)
        with st.expander(f"random pool ({master_preset}) - {share_label:.1f}% of current mix"):
            master_data = loaded_presets[random_key]
            col_left, col_right = st.columns(2)
            with col_left:
                display_segment_table("Vowels", master_data.get("vowels", []), include_hints=include_hints)
            with col_right:
                display_segment_table("Consonants", master_data.get("consonants", []), include_hints=include_hints)


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


def inventory_as_preset_payload(inventory: Dict[str, List[str]], language_name: str) -> Dict[str, List[str]]:
    """Return generated inventory in preset-compatible JSON format."""
    return {
        "name": language_name,
        "vowels": inventory.get("vowels", []),
        "consonants": inventory.get("consonants", []),
    }


def display_segment_table(title: str, segments: List[str], include_hints: bool) -> None:
    """Render a segment list in a compact table."""
    st.markdown(f"**{title} ({len(segments)})**")
    rows = build_segment_rows(segments, include_hints=include_hints)
    st.dataframe(rows, hide_index=True, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Sound Inventory Generator", layout="wide")
    st.title("Sound Inventory Generator")
    st.caption("Mix language presets, apply optional sound-change rules, and export reusable inventories.")

    preset_names = list_json_names(generator.PRESETS_DIR)
    rule_names = list_json_names(generator.RULES_DIR)

    if not preset_names:
        st.error("No preset files found. Add JSON files to presets/ and reload.")
        st.stop()

    st.subheader("Generator Controls")
    selected_presets = st.multiselect(
        "Presets to mix",
        options=preset_names,
        default=default_preset_selection(preset_names),
        help="Pick one or more source inventories.",
    )

    weights: List[float] = []
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
    show_sound_alikes = st.checkbox(
        "Show sound-alike hints",
        value=True,
        help="Keeps IPA exact, but adds rough English-leaning pronunciation hints in result tables.",
    )

    with st.expander("Mixing guide: source sounds and weights", expanded=True):
        render_mix_reference_panel(
            selected_presets=selected_presets,
            weights=weights,
            random_weight=random_weight,
            master_preset=master_preset,
            include_hints=show_sound_alikes,
        )

    language_name = st.text_input("Generated language name", value="GeneratedLanguage")
    output_dir_value = st.text_input("Output folder", value="outputs/ui_run")

    use_seed = st.checkbox("Use fixed random seed", value=False)
    seed_value = st.number_input(
        "Seed value",
        min_value=0,
        max_value=2_147_483_647,
        value=42,
        step=1,
        disabled=not use_seed,
    )

    generate = st.button("Generate Inventory", type="primary")

    if generate:
        if not selected_presets:
            st.error("Pick at least one preset before generating.")
        elif (sum(weights) + random_weight) <= 0:
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
                st.session_state.pop("sample_words", None)
                st.session_state.pop("sample_sentences", None)

                st.success(f"Generated '{language_name}' and saved files to {output_dir}")
            except Exception as exc:  # pragma: no cover - UI safety net
                st.exception(exc)

    latest_inventory = st.session_state.get("last_inventory")
    latest_language_name = st.session_state.get("last_language_name", "GeneratedLanguage")

    if latest_inventory:
        st.subheader("Latest Result")
        col_a, col_b = st.columns(2)
        with col_a:
            display_segment_table("Vowels", latest_inventory.get("vowels", []), include_hints=show_sound_alikes)
        with col_b:
            display_segment_table(
                "Consonants",
                latest_inventory.get("consonants", []),
                include_hints=show_sound_alikes,
            )

        output_dir_label = st.session_state.get("last_output_dir", "(unknown)")
        st.caption(f"Latest files were written to: {output_dir_label}")
        st.caption("Sound-alikes are approximation helpers; IPA stays the canonical data.")

        preset_payload = inventory_as_preset_payload(latest_inventory, latest_language_name)
        st.download_button(
            label="Download preset JSON",
            data=json.dumps(preset_payload, ensure_ascii=False, indent=2),
            file_name=f"{sanitize_name(latest_language_name)}.json",
            mime="application/json",
        )
        guide_csv = build_pronunciation_csv(
            latest_inventory.get("vowels", []),
            latest_inventory.get("consonants", []),
        )
        st.download_button(
            label="Download pronunciation guide CSV",
            data=guide_csv,
            file_name=f"{sanitize_name(latest_language_name)}_pronunciation_guide.csv",
            mime="text/csv",
        )

        st.subheader("Sample Text Playground (Not Saved)")
        st.caption(
            "Step 2: generate placeholder words and sentences from this inventory. Regenerate as much as you want."
        )

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
        syllable_separator = "." if show_syllable_breaks else ""

        samples_button_col_1, samples_button_col_2, samples_button_col_3 = st.columns(3)
        with samples_button_col_1:
            generate_word_samples = st.button("Generate Word Samples", key="generate_word_samples")
        with samples_button_col_2:
            generate_sentence_samples = st.button(
                "Generate Sentence Samples",
                key="generate_sentence_samples",
            )
        with samples_button_col_3:
            generate_both_samples = st.button("Generate Both", key="generate_both_samples")

        latest_vowels = latest_inventory.get("vowels", [])
        latest_consonants = latest_inventory.get("consonants", [])

        if generate_word_samples or generate_both_samples:
            st.session_state["sample_words"] = build_sample_words(
                latest_vowels,
                latest_consonants,
                sample_count=int(sample_word_count),
                syllable_range=sample_syllable_range,
                syllable_separator=syllable_separator,
            )

        if generate_sentence_samples or generate_both_samples:
            st.session_state["sample_sentences"] = build_sample_sentences(
                latest_vowels,
                latest_consonants,
                sample_count=int(sample_sentence_count),
                syllable_range=sample_syllable_range,
                words_range=sample_words_range,
                syllable_separator=syllable_separator,
            )

        sample_words = st.session_state.get("sample_words", [])
        sample_sentences = st.session_state.get("sample_sentences", [])

        if sample_words:
            st.markdown("**Word samples**")
            st.dataframe(
                [{"Word": word} for word in sample_words],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No word samples yet. Click 'Generate Word Samples' or 'Generate Both'.")

        if sample_sentences:
            st.markdown("**Sentence samples**")
            for sentence in sample_sentences:
                st.write(f"- {sentence}")
        else:
            st.info("No sentence samples yet. Click 'Generate Sentence Samples' or 'Generate Both'.")

        st.subheader("Save Latest Result as Preset")
        preset_filename = st.text_input(
            "Preset filename (without .json)",
            value=sanitize_name(latest_language_name),
            key="preset_filename",
        )
        overwrite_existing = st.checkbox("Overwrite existing preset file", value=False)
        save_preset = st.button("Save to presets/")

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
