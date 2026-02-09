#!/usr/bin/env python3
"""Build a source profile sidecar from an IPA wordlist CSV/TSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

VOWEL_HINTS = set("aeiouyæøœɨʉɯɤɔɒʌəɜɪʊɑ")
IPA_SEPARATORS = {".", "-", " ", "/", "|"}
IPA_MODIFIERS = {
    "ʰ", "ʱ", "ʲ", "ʷ", "ˠ", "ˤ", "ˀ", "ʼ", "ː", "ˑ", "˞",
    "ˈ", "ˌ", "̥", "̬", "̃", "̩", "̯", "̪", "̺", "̻", "̹", "̜", "̟", "̠",
}
IPA_TIE_BARS = {"͡", "͜"}
TEMPLATE_POSITIONS: Tuple[str, ...] = ("single", "initial", "medial", "final")


def _normalize_weight_map(counts: Dict[str, float]) -> Dict[str, float]:
    cleaned = {segment: float(count) for segment, count in counts.items() if float(count) > 0}
    if not cleaned:
        return {}
    mean = sum(cleaned.values()) / float(len(cleaned))
    if mean <= 0:
        return {}
    return {segment: float(value / mean) for segment, value in cleaned.items()}


def _normalize_template_counts(counts: Counter[str]) -> List[Tuple[str, float]]:
    filtered = {shape: float(value) for shape, value in counts.items() if value > 0 and re.fullmatch(r"[CV]+", shape)}
    total = sum(filtered.values())
    if total <= 0:
        return []
    return [(shape, float(value / total)) for shape, value in filtered.items()]


def _segment_tokens(text: str) -> List[str]:
    tokens: List[str] = []
    current = ""
    for char in text:
        if char in IPA_SEPARATORS:
            if current:
                tokens.append(current)
                current = ""
            tokens.append(char)
            continue
        if not current:
            current = char
            continue
        if unicodedata.combining(char) or char in IPA_MODIFIERS or char in IPA_TIE_BARS:
            current += char
            continue
        tokens.append(current)
        current = char
    if current:
        tokens.append(current)
    return tokens


def _is_vowel(segment: str) -> bool:
    normalized = "".join(
        char
        for char in segment
        if not unicodedata.combining(char) and char not in IPA_MODIFIERS and char not in IPA_TIE_BARS
    )
    return any(char in VOWEL_HINTS for char in normalized)


def _syllable_patterns(tokens: Sequence[str]) -> List[str]:
    syllables: List[List[str]] = [[]]
    for token in tokens:
        if token in {".", "-"}:
            if syllables[-1]:
                syllables.append([])
            continue
        if token in {" ", "/", "|"}:
            continue
        syllables[-1].append(token)
    cleaned = [syllable for syllable in syllables if syllable]
    patterns: List[str] = []
    for syllable in cleaned:
        shape = "".join("V" if _is_vowel(segment) else "C" for segment in syllable)
        if shape:
            patterns.append(shape)
    return patterns


def _iter_ipa_forms(path: Path, ipa_column: str, delimiter: str) -> Iterable[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        if delimiter == "auto":
            csv_delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        elif delimiter == "tab":
            csv_delimiter = "\t"
        else:
            csv_delimiter = ","
        reader = csv.DictReader(handle, delimiter=csv_delimiter)
        if reader.fieldnames is None:
            return
        fieldnames = [str(name).strip() for name in reader.fieldnames]
        source_column = ipa_column if ipa_column in fieldnames else (fieldnames[0] if fieldnames else "")
        if not source_column:
            return
        for row in reader:
            value = str(row.get(source_column, "")).strip()
            if value:
                yield value


def build_profile_from_wordlist(path: Path, ipa_column: str, delimiter: str) -> Dict[str, object]:
    vowel_counts: Counter[str] = Counter()
    consonant_counts: Counter[str] = Counter()
    template_counts: Dict[str, Counter[str]] = {position: Counter() for position in TEMPLATE_POSITIONS}

    for ipa in _iter_ipa_forms(path, ipa_column=ipa_column, delimiter=delimiter):
        tokens = _segment_tokens(ipa)
        segments = [token for token in tokens if token not in IPA_SEPARATORS]
        for segment in segments:
            if _is_vowel(segment):
                vowel_counts[segment] += 1
            else:
                consonant_counts[segment] += 1

        patterns = _syllable_patterns(tokens)
        if not patterns:
            continue
        if len(patterns) == 1:
            template_counts["single"][patterns[0]] += 1
            continue
        template_counts["initial"][patterns[0]] += 1
        template_counts["final"][patterns[-1]] += 1
        for pattern in patterns[1:-1]:
            template_counts["medial"][pattern] += 1

    profile: Dict[str, object] = {
        "version": 1,
        "provenance": [f"Derived from wordlist: {path.name}"],
        "segment_frequency": {
            "vowel_weights": _normalize_weight_map(dict(vowel_counts)),
            "consonant_weights": _normalize_weight_map(dict(consonant_counts)),
        },
        "template_weights_by_position": {
            position: _normalize_template_counts(counter)
            for position, counter in template_counts.items()
            if counter
        },
    }
    return profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a source profile sidecar from IPA wordlist data.")
    parser.add_argument("--input", required=True, help="Path to CSV/TSV wordlist with IPA column.")
    parser.add_argument("--output", required=True, help="Path to output .profile.json file.")
    parser.add_argument(
        "--ipa-column",
        default="ipa",
        help="Column name containing IPA forms (defaults to 'ipa'; falls back to first column).",
    )
    parser.add_argument(
        "--delimiter",
        choices=["auto", "comma", "tab"],
        default="auto",
        help="Input delimiter selection.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    profile = build_profile_from_wordlist(
        path=input_path,
        ipa_column=str(args.ipa_column),
        delimiter=str(args.delimiter),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(profile, handle, ensure_ascii=False, indent=2)
    print(f"Wrote source profile: {output_path}")


if __name__ == "__main__":
    main()
