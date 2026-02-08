#!/usr/bin/env python3
"""
Sound Inventory Generator

This script mixes phoneme inventories from language presets, optionally adds random phonemes
and applies sound‑change rules to produce a new inventory.  Presets and rules are stored
as JSON files in the `presets/` and `rules/` directories.  The script writes the generated
inventory both as a JSON file and in a minimal CLDF/PHOIBLE style CSV format so that
it can be re‑loaded or used in external tools.

Usage:
  python sound_inventory_generator.py --presets english korean --weights 0.5 0.5 \
      --random-weight 0.1 --rules demo_shift --output my_lang

Run with --help for full options.
"""

import argparse
import json
import os
import random
import csv
from typing import Dict, List, Any, Tuple

# Directory constants (relative to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESETS_DIR = os.path.join(SCRIPT_DIR, 'presets')
RULES_DIR = os.path.join(SCRIPT_DIR, 'rules')


def _normalize_segment_entries(raw_items: Any) -> List[Dict[str, Any]]:
    """Normalize segment entries to {'segment': str, 'representation': float}.

    Accepts either:
    - ["p", "t", ...] (legacy format), or
    - [{"segment": "p", "representation": 0.2}, ...] (weighted format).
    - {"p": 0.2, "t": 1.0, ...} (mapping shorthand).

    Duplicate segments are merged by summing representation values.
    """
    if isinstance(raw_items, dict):
        # Allow shorthand mappings like {"p": 0.7, "t": 1.2}
        iterable_items: List[Any] = [
            {"segment": str(segment), "representation": value}
            for segment, value in raw_items.items()
        ]
    elif isinstance(raw_items, list):
        iterable_items = raw_items
    else:
        iterable_items = []

    ordered_segments: List[str] = []
    merged: Dict[str, Dict[str, Any]] = {}

    for item in iterable_items:
        segment = ""
        representation = 1.0

        if isinstance(item, dict):
            segment = str(item.get("segment", "")).strip() or str(item.get("ipa", "")).strip()
            raw_representation = item.get("representation", item.get("weight", 1.0))
            try:
                representation = float(raw_representation)
            except (TypeError, ValueError):
                representation = 1.0
        else:
            # Fallback for plain strings and any scalar-like values.
            segment = str(item).strip()
            representation = 1.0

        if not segment:
            continue

        # Some sources include alternative phoneme spellings joined by "|".
        # Split them to keep inventories normalized.
        segments = [part.strip() for part in segment.split("|") if part.strip()]
        if not segments:
            continue

        representation = max(0.0, representation)
        for seg in segments:
            if seg not in merged:
                merged[seg] = {"segment": seg, "representation": representation}
                ordered_segments.append(seg)
            else:
                merged[seg]["representation"] += representation

    return [merged[segment] for segment in ordered_segments]


def load_preset(name: str) -> Dict[str, Any]:
    """Load a language preset by name from the presets directory.

    Args:
        name: Basename of the preset file without extension.

    Returns:
        A dictionary with keys:
        - 'name'
        - 'vowels' / 'consonants' (legacy string lists for UI compatibility)
        - 'vowels_entries' / 'consonants_entries' (weighted segment entries)

    Raises:
        FileNotFoundError: if the preset file cannot be found.
        json.JSONDecodeError: if the preset file is not valid JSON.
    """
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    vowels_entries = _normalize_segment_entries(data.get("vowels", []))
    consonants_entries = _normalize_segment_entries(data.get("consonants", []))

    data["vowels_entries"] = vowels_entries
    data["consonants_entries"] = consonants_entries
    data["vowels"] = [entry["segment"] for entry in vowels_entries]
    data["consonants"] = [entry["segment"] for entry in consonants_entries]
    return data


def load_rule_set(name: str) -> Dict[str, Any]:
    """Load a rule set by name from the rules directory.

    Args:
        name: Basename of the rule file without extension.

    Returns:
        A dictionary with keys 'name', 'description', and 'rules'.
    """
    path = os.path.join(RULES_DIR, f"{name}.json")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def weighted_average(lengths: List[int], weights: List[float]) -> float:
    """Compute the weighted average of counts.

    Args:
        lengths: list of integer counts (e.g., number of vowels per preset)
        weights: list of weights corresponding to each length

    Returns:
        Weighted average as float.  If the sum of weights is zero, returns zero.
    """
    total_w = sum(weights)
    if total_w <= 0:
        return 0.0
    return sum(length * w for length, w in zip(lengths, weights)) / total_w


def sample_from_entries(entries: List[Dict[str, Any]], n: int) -> List[str]:
    """Return n weighted samples from normalized segment entries.

    Args:
        entries: list of {'segment', 'representation'} items.
        n: number of items to sample.

    Returns:
        A new list of sampled items.  If n <= 0, returns an empty list.
    """
    if n <= 0 or not entries:
        return []

    segments = [entry["segment"] for entry in entries if entry.get("segment")]
    weights = [max(0.0, float(entry.get("representation", 1.0))) for entry in entries if entry.get("segment")]
    if not segments:
        return []

    if sum(weights) <= 0:
        return random.choices(segments, k=n)
    return random.choices(segments, weights=weights, k=n)


def mix_inventories(preset_names: List[str], weights: List[float], random_weight: float,
                    master_preset_name: str) -> Dict[str, Any]:
    """Mix multiple language inventories according to weights and add a random component.

    Args:
        preset_names: list of preset basenames (without extension) to mix.
        weights: list of weights corresponding to each preset.
        random_weight: weight assigned to random phonemes drawn from a master preset.
        master_preset_name: name of the master preset containing extra random phonemes.

    Returns:
        A dictionary with:
        - 'vowels' / 'consonants': unique generated segments
        - 'vowels_representation' / 'consonants_representation': sampled weight traces
    """
    if len(preset_names) != len(weights):
        raise ValueError("Number of preset names must equal number of weights.")
    # Load all presets
    presets = [load_preset(n) for n in preset_names]
    master = load_preset(master_preset_name)

    # Compute target counts based on weighted average of each preset's counts
    vowel_lengths = [len(p['vowels']) for p in presets]
    consonant_lengths = [len(p['consonants']) for p in presets]
    avg_vowels = weighted_average(vowel_lengths, weights)
    avg_consonants = weighted_average(consonant_lengths, weights)

    # Round to nearest integer
    target_vowels = max(1, round(avg_vowels))
    target_consonants = max(1, round(avg_consonants))

    # Determine counts per preset and random portion
    total_weight = sum(weights) + (random_weight if random_weight > 0 else 0.0)
    # Avoid division by zero
    if total_weight <= 0:
        total_weight = 1.0
    # Determine how many items to sample from each preset
    counts_vowels: List[int] = []
    counts_consonants: List[int] = []
    for w in weights:
        portion = w / total_weight
        counts_vowels.append(max(0, round(portion * target_vowels)))
        counts_consonants.append(max(0, round(portion * target_consonants)))
    # Random portion counts
    random_portion = (random_weight / total_weight) if total_weight > 0 else 0.0
    random_vowels = max(0, round(random_portion * target_vowels))
    random_consonants = max(0, round(random_portion * target_consonants))

    # Sample phonemes (weighted by representation where available)
    final_vowels: List[str] = []
    final_consonants: List[str] = []
    for p, n_v, n_c in zip(presets, counts_vowels, counts_consonants):
        final_vowels.extend(sample_from_entries(p.get('vowels_entries', []), n_v))
        final_consonants.extend(sample_from_entries(p.get('consonants_entries', []), n_c))
    # Random from master
    final_vowels.extend(sample_from_entries(master.get('vowels_entries', []), random_vowels))
    final_consonants.extend(sample_from_entries(master.get('consonants_entries', []), random_consonants))

    # Track sampled frequency traces before deduplication so generated presets can carry weights.
    vowel_representation: Dict[str, float] = {}
    consonant_representation: Dict[str, float] = {}
    for segment in final_vowels:
        vowel_representation[segment] = vowel_representation.get(segment, 0.0) + 1.0
    for segment in final_consonants:
        consonant_representation[segment] = consonant_representation.get(segment, 0.0) + 1.0

    # Consolidate into unique sets
    vowels_set = list(dict.fromkeys(final_vowels))
    consonants_set = list(dict.fromkeys(final_consonants))
    return {
        "vowels": vowels_set,
        "consonants": consonants_set,
        "vowels_representation": {segment: vowel_representation.get(segment, 1.0) for segment in vowels_set},
        "consonants_representation": {segment: consonant_representation.get(segment, 1.0) for segment in consonants_set},
    }


def apply_rules(inventory: Dict[str, Any], rule_sets: List[str]) -> Dict[str, Any]:
    """Apply one or more rule sets to an inventory.

    Each rule maps a 'from' string to a 'to' string.  If a phoneme exactly matches
    the 'from' string, it will be replaced with 'to'.  An empty 'to' string
    removes the phoneme from the inventory.  Rules are applied sequentially
    across the provided rule sets.

    Args:
        inventory: dictionary with keys 'vowels' and 'consonants'. Values are lists of phoneme strings.
            Optional keys 'vowels_representation' and 'consonants_representation' are preserved and transformed.
        rule_sets: list of rule set names to apply.

    Returns:
        A new inventory dictionary with rules applied.
    """
    vowels = inventory['vowels']
    consonants = inventory['consonants']
    vowels_representation: Dict[str, float] = {}
    for segment, value in inventory.get(
        'vowels_representation',
        {segment: 1.0 for segment in vowels},
    ).items():
        try:
            vowels_representation[segment] = float(value)
        except (TypeError, ValueError):
            vowels_representation[segment] = 1.0

    consonants_representation: Dict[str, float] = {}
    for segment, value in inventory.get(
        'consonants_representation',
        {segment: 1.0 for segment in consonants},
    ).items():
        try:
            consonants_representation[segment] = float(value)
        except (TypeError, ValueError):
            consonants_representation[segment] = 1.0
    # Make a copy to modify
    new_vowels = vowels[:]
    new_consonants = consonants[:]

    for rule_name in rule_sets:
        rules = load_rule_set(rule_name).get('rules', [])
        # Apply to vowels
        updated_vowels: List[str] = []
        updated_vowels_representation: Dict[str, float] = {}
        for ph in new_vowels:
            new_ph = ph
            for r in rules:
                frm = r.get('from')
                to = r.get('to')
                # Replace entire phoneme if it matches exactly
                if new_ph == frm:
                    new_ph = to
            if new_ph:
                updated_vowels.append(new_ph)
                updated_vowels_representation[new_ph] = updated_vowels_representation.get(new_ph, 0.0) + vowels_representation.get(ph, 1.0)
        new_vowels = updated_vowels
        vowels_representation = updated_vowels_representation
        # Apply to consonants
        updated_consonants: List[str] = []
        updated_consonants_representation: Dict[str, float] = {}
        for ph in new_consonants:
            new_ph = ph
            for r in rules:
                frm = r.get('from')
                to = r.get('to')
                if new_ph == frm:
                    new_ph = to
            if new_ph:
                updated_consonants.append(new_ph)
                updated_consonants_representation[new_ph] = updated_consonants_representation.get(new_ph, 0.0) + consonants_representation.get(ph, 1.0)
        new_consonants = updated_consonants
        consonants_representation = updated_consonants_representation

    # Deduplicate while preserving order
    dedup_vowels = list(dict.fromkeys(new_vowels))
    dedup_consonants = list(dict.fromkeys(new_consonants))
    return {
        "vowels": dedup_vowels,
        "consonants": dedup_consonants,
        "vowels_representation": {segment: vowels_representation.get(segment, 1.0) for segment in dedup_vowels},
        "consonants_representation": {segment: consonants_representation.get(segment, 1.0) for segment in dedup_consonants},
    }


def save_inventory_as_json(inventory: Dict[str, Any], path: str, name: str) -> None:
    """Save the generated inventory as a JSON file.

    Args:
        inventory: dictionary with 'vowels' and 'consonants' (plus optional metadata).
        path: directory where to save the file.
        name: name prefix for the file.
    """
    os.makedirs(path, exist_ok=True)
    filename = os.path.join(path, f"{name}.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)


def save_inventory_as_cldf(inventory: Dict[str, Any], path: str, language_name: str) -> None:
    """Save the generated inventory in a minimal CLDF/PHOIBLE style.

    This writes three CSV files: `languages.csv`, `inventories.csv`, and `values.csv`.

    Args:
        inventory: dictionary with 'vowels' and 'consonants'.
        path: directory where to write the CSV files.
        language_name: name of the generated language.
    """
    os.makedirs(path, exist_ok=True)
    # Define simple IDs
    lang_id = f"lang_{language_name.lower().replace(' ', '_')}"
    inv_id = f"inv_{language_name.lower().replace(' ', '_')}"
    # languages.csv
    with open(os.path.join(path, 'languages.csv'), 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Name'])
        writer.writeheader()
        writer.writerow({'ID': lang_id, 'Name': language_name})
    # inventories.csv
    with open(os.path.join(path, 'inventories.csv'), 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Language_ID', 'Name'])
        writer.writeheader()
        writer.writerow({'ID': inv_id, 'Language_ID': lang_id, 'Name': f"Inventory of {language_name}"})
    # values.csv
    with open(os.path.join(path, 'values.csv'), 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Inventory_ID', 'Segment'])
        writer.writeheader()
        for segment in inventory['vowels'] + inventory['consonants']:
            writer.writerow({'Inventory_ID': inv_id, 'Segment': segment})


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate a phoneme inventory by mixing language presets and applying sound changes.")
    parser.add_argument('--presets', nargs='+', required=True,
                        help='List of preset names (without .json) to mix')
    parser.add_argument('--weights', nargs='+', type=float, required=True,
                        help='List of weights corresponding to each preset')
    parser.add_argument('--random-weight', type=float, default=0.0,
                        help='Weight of random phonemes drawn from the master preset')
    parser.add_argument('--master-preset', type=str, default='random_master',
                        help='Name of the master preset file for random phonemes')
    parser.add_argument('--rules', nargs='*', default=[],
                        help='Optional list of rule set names to apply')
    parser.add_argument('--output', type=str, required=True,
                        help='Directory path where generated files should be written')
    parser.add_argument('--name', type=str, default='GeneratedLanguage',
                        help='Name of the generated language for CSV output')
    return parser.parse_args()


def main():
    args = parse_args()
    if len(args.presets) != len(args.weights):
        raise ValueError("--presets and --weights must have the same number of elements")

    # Generate inventory
    mixed = mix_inventories(args.presets, args.weights, args.random_weight, args.master_preset)
    # Apply rules if provided
    if args.rules:
        mixed = apply_rules(mixed, args.rules)

    # Save results
    save_inventory_as_json(mixed, args.output, args.name)
    save_inventory_as_cldf(mixed, args.output, args.name)
    print(f"Generated language '{args.name}' saved to {args.output}")


if __name__ == '__main__':
    main()
