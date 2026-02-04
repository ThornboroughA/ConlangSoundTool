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


def load_preset(name: str) -> Dict[str, Any]:
    """Load a language preset by name from the presets directory.

    Args:
        name: Basename of the preset file without extension.

    Returns:
        A dictionary with keys 'name', 'vowels', and 'consonants'.

    Raises:
        FileNotFoundError: if the preset file cannot be found.
        json.JSONDecodeError: if the preset file is not valid JSON.
    """
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Ensure sets for uniqueness
    data['vowels'] = list(dict.fromkeys(data.get('vowels', [])))
    data['consonants'] = list(dict.fromkeys(data.get('consonants', [])))
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


def sample_from_set(items: List[str], n: int) -> List[str]:
    """Return a list of n items sampled with replacement from a list.

    Args:
        items: list of elements to sample from.
        n: number of items to sample.

    Returns:
        A new list of sampled items.  If n <= 0, returns an empty list.
    """
    if n <= 0:
        return []
    return random.choices(items, k=n)


def mix_inventories(preset_names: List[str], weights: List[float], random_weight: float,
                    master_preset_name: str) -> Dict[str, List[str]]:
    """Mix multiple language inventories according to weights and add a random component.

    Args:
        preset_names: list of preset basenames (without extension) to mix.
        weights: list of weights corresponding to each preset.
        random_weight: weight assigned to random phonemes drawn from a master preset.
        master_preset_name: name of the master preset containing extra random phonemes.

    Returns:
        A dictionary with keys 'vowels' and 'consonants' containing sets of phonemes.
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

    # Sample phonemes
    final_vowels: List[str] = []
    final_consonants: List[str] = []
    for p, n_v, n_c in zip(presets, counts_vowels, counts_consonants):
        final_vowels.extend(sample_from_set(p['vowels'], n_v))
        final_consonants.extend(sample_from_set(p['consonants'], n_c))
    # Random from master
    final_vowels.extend(sample_from_set(master['vowels'], random_vowels))
    final_consonants.extend(sample_from_set(master['consonants'], random_consonants))

    # Consolidate into unique sets
    vowels_set = list(dict.fromkeys(final_vowels))
    consonants_set = list(dict.fromkeys(final_consonants))
    return {"vowels": vowels_set, "consonants": consonants_set}


def apply_rules(inventory: Dict[str, List[str]], rule_sets: List[str]) -> Dict[str, List[str]]:
    """Apply one or more rule sets to an inventory.

    Each rule maps a 'from' string to a 'to' string.  If a phoneme exactly matches
    the 'from' string, it will be replaced with 'to'.  An empty 'to' string
    removes the phoneme from the inventory.  Rules are applied sequentially
    across the provided rule sets.

    Args:
        inventory: dictionary with keys 'vowels' and 'consonants'.  Values are lists of phoneme strings.
        rule_sets: list of rule set names to apply.

    Returns:
        A new inventory dictionary with rules applied.
    """
    vowels = inventory['vowels']
    consonants = inventory['consonants']
    # Make a copy to modify
    new_vowels = vowels[:]
    new_consonants = consonants[:]

    for rule_name in rule_sets:
        rules = load_rule_set(rule_name).get('rules', [])
        # Apply to vowels
        updated_vowels: List[str] = []
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
        new_vowels = updated_vowels
        # Apply to consonants
        updated_consonants: List[str] = []
        for ph in new_consonants:
            new_ph = ph
            for r in rules:
                frm = r.get('from')
                to = r.get('to')
                if new_ph == frm:
                    new_ph = to
            if new_ph:
                updated_consonants.append(new_ph)
        new_consonants = updated_consonants

    # Deduplicate while preserving order
    dedup_vowels = list(dict.fromkeys(new_vowels))
    dedup_consonants = list(dict.fromkeys(new_consonants))
    return {"vowels": dedup_vowels, "consonants": dedup_consonants}


def save_inventory_as_json(inventory: Dict[str, List[str]], path: str, name: str) -> None:
    """Save the generated inventory as a JSON file.

    Args:
        inventory: dictionary with 'vowels' and 'consonants'.
        path: directory where to save the file.
        name: name prefix for the file.
    """
    os.makedirs(path, exist_ok=True)
    filename = os.path.join(path, f"{name}.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)


def save_inventory_as_cldf(inventory: Dict[str, List[str]], path: str, language_name: str) -> None:
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
