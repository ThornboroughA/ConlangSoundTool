#!/usr/bin/env python3
"""Simple Streamlit UI for the Sound Inventory Generator."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Dict, List

import streamlit as st

import sound_inventory_generator as generator


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


def display_segment_table(title: str, segments: List[str]) -> None:
    """Render a segment list in a compact table."""
    st.markdown(f"**{title} ({len(segments)})**")
    rows = [{"Segment": seg} for seg in segments]
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

                st.success(f"Generated '{language_name}' and saved files to {output_dir}")
            except Exception as exc:  # pragma: no cover - UI safety net
                st.exception(exc)

    latest_inventory = st.session_state.get("last_inventory")
    latest_language_name = st.session_state.get("last_language_name", "GeneratedLanguage")

    if latest_inventory:
        st.subheader("Latest Result")
        col_a, col_b = st.columns(2)
        with col_a:
            display_segment_table("Vowels", latest_inventory.get("vowels", []))
        with col_b:
            display_segment_table("Consonants", latest_inventory.get("consonants", []))

        output_dir_label = st.session_state.get("last_output_dir", "(unknown)")
        st.caption(f"Latest files were written to: {output_dir_label}")

        preset_payload = inventory_as_preset_payload(latest_inventory, latest_language_name)
        st.download_button(
            label="Download preset JSON",
            data=json.dumps(preset_payload, ensure_ascii=False, indent=2),
            file_name=f"{sanitize_name(latest_language_name)}.json",
            mime="application/json",
        )

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
