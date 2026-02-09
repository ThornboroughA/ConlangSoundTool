"""Source profile utilities for language-driven phonotactic tendencies."""

from __future__ import annotations

import csv
import json
import os
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESETS_DIR = os.path.join(SCRIPT_DIR, "presets")
SOURCE_PROFILE_VERSION = 1
TEMPLATE_POSITIONS: Tuple[str, ...] = ("single", "initial", "medial", "final")


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_float(value: Any) -> Optional[float]:
    number = _as_float(value)
    if number is None or number <= 0:
        return None
    return float(number)


def _normalize_weight_map(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        return {}
    cleaned: Dict[str, float] = {}
    for key, raw in value.items():
        weight = _positive_float(raw)
        if weight is None:
            continue
        cleaned[str(key)] = weight
    if not cleaned:
        return {}
    mean = sum(cleaned.values()) / float(len(cleaned))
    if mean <= 0:
        return {}
    return {key: float(weight / mean) for key, weight in cleaned.items()}


def _normalize_weighted_pairs(
    value: Any,
    label_pattern: str = r"[CV]+",
) -> List[Tuple[str, float]]:
    if isinstance(value, dict):
        sequence: Sequence[Any] = [(label, weight) for label, weight in value.items()]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        sequence = value
    else:
        return []

    cleaned: List[Tuple[str, float]] = []
    for item in sequence:
        label: str = ""
        weight: Optional[float] = None
        if isinstance(item, (list, tuple)) and len(item) == 2:
            label = str(item[0]).strip()
            weight = _positive_float(item[1])
        elif isinstance(item, dict):
            label = str(item.get("label", "")).strip()
            weight = _positive_float(item.get("weight"))
        else:
            continue
        if not label or weight is None:
            continue
        if not re.fullmatch(label_pattern, label):
            continue
        cleaned.append((label, weight))

    if not cleaned:
        return []
    totals: Dict[str, float] = {}
    for label, weight in cleaned:
        totals[label] = totals.get(label, 0.0) + float(weight)
    total = sum(totals.values())
    if total <= 0:
        return []
    return [(label, float(weight / total)) for label, weight in totals.items() if weight > 0]


def _normalize_nested_map(value: Any) -> Dict[str, Dict[str, float]]:
    if not isinstance(value, dict):
        return {}
    cleaned: Dict[str, Dict[str, float]] = {}
    for outer_key, outer_value in value.items():
        if not isinstance(outer_value, dict):
            continue
        inner_cleaned: Dict[str, float] = {}
        for inner_key, raw in outer_value.items():
            number = _positive_float(raw)
            if number is None:
                continue
            inner_cleaned[str(inner_key)] = number
        if inner_cleaned:
            cleaned[str(outer_key)] = inner_cleaned
    return cleaned


def _normalize_scalar_map(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        return {}
    cleaned: Dict[str, float] = {}
    for key, raw in value.items():
        number = _as_float(raw)
        if number is None:
            continue
        cleaned[str(key)] = float(number)
    return cleaned


def _mean_one_blend(base: float, target: float, influence: float) -> float:
    return base + ((target - base) * influence)


def _deep_get(mapping: Dict[str, Any], path: Sequence[str], fallback: Any) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return fallback
        current = current[key]
    return current


def deep_merge_dict(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = merged.get(key, {})
            if not isinstance(nested, dict):
                nested = {}
            merged[key] = deep_merge_dict(nested, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _default_phonotactic_profile() -> Dict[str, Any]:
    try:
        from sample_text_generator import DEFAULT_PHONOTACTIC_PROFILE  # local import keeps module lightweight
    except Exception:
        return {}
    if not isinstance(DEFAULT_PHONOTACTIC_PROFILE, dict):
        return {}
    return deepcopy(DEFAULT_PHONOTACTIC_PROFILE)


def _merge_template_pairs(
    source_pairs: List[Tuple[str, float]],
    default_pairs: List[Tuple[str, float]],
    influence: float,
) -> List[Tuple[str, float]]:
    source_map = {label: weight for label, weight in source_pairs}
    default_map = {label: weight for label, weight in default_pairs}
    labels = set(source_map.keys()) | set(default_map.keys())
    merged: Dict[str, float] = {}
    for label in labels:
        default_weight = float(default_map.get(label, 0.0))
        source_weight = float(source_map.get(label, 0.0))
        blended = _mean_one_blend(default_weight, source_weight, influence)
        if blended > 0:
            merged[label] = blended
    total = sum(merged.values())
    if total <= 0:
        return []
    return [(label, float(weight / total)) for label, weight in merged.items()]


def _weighted_average_maps(
    maps: List[Dict[str, float]],
    shares: List[float],
    neutral: float = 1.0,
) -> Dict[str, float]:
    if not maps or not shares:
        return {}
    keys = set()
    for mapping in maps:
        keys.update(mapping.keys())
    if not keys:
        return {}
    total_share = sum(shares)
    if total_share <= 0:
        return {}
    result: Dict[str, float] = {}
    for key in keys:
        weighted_total = 0.0
        for mapping, share in zip(maps, shares):
            weighted_total += float(mapping.get(key, neutral)) * share
        result[key] = float(weighted_total / total_share)
    return result


def _weighted_average_nested_maps(
    maps: List[Dict[str, Dict[str, float]]],
    shares: List[float],
    neutral: float = 1.0,
) -> Dict[str, Dict[str, float]]:
    if not maps or not shares:
        return {}
    outer_keys = set()
    for mapping in maps:
        outer_keys.update(mapping.keys())
    result: Dict[str, Dict[str, float]] = {}
    for outer_key in outer_keys:
        inner_maps = [mapping.get(outer_key, {}) for mapping in maps]
        mixed_inner = _weighted_average_maps(inner_maps, shares, neutral=neutral)
        if mixed_inner:
            result[outer_key] = mixed_inner
    return result


def _weighted_average_template_positions(
    templates: List[Dict[str, List[Tuple[str, float]]]],
    shares: List[float],
) -> Dict[str, List[Tuple[str, float]]]:
    if not templates or not shares:
        return {}
    total_share = sum(shares)
    if total_share <= 0:
        return {}
    mixed: Dict[str, List[Tuple[str, float]]] = {}
    for position in TEMPLATE_POSITIONS:
        accumulator: Dict[str, float] = {}
        for template_map, share in zip(templates, shares):
            pairs = template_map.get(position, [])
            for label, weight in pairs:
                accumulator[label] = accumulator.get(label, 0.0) + (float(weight) * float(share))
        total = sum(accumulator.values())
        if total <= 0:
            continue
        mixed[position] = [
            (label, float(weight / total))
            for label, weight in accumulator.items()
            if weight > 0
        ]
    return mixed


def _normalize_provenance(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    cleaned: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def load_source_profile(preset_name: str) -> Dict[str, Any]:
    """Load and normalize optional sidecar source profile for a preset."""
    path = os.path.join(PRESETS_DIR, f"{preset_name}.profile.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw_profile = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw_profile, dict):
        return {}
    return normalize_source_profile(raw_profile)


def normalize_source_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize source profile payload to a safe schema subset."""
    if not isinstance(profile, dict):
        return {}

    normalized: Dict[str, Any] = {}
    provenance = _normalize_provenance(profile.get("provenance", []))
    if provenance:
        normalized["provenance"] = provenance

    segment_frequency_raw = profile.get("segment_frequency", {})
    if isinstance(segment_frequency_raw, dict):
        vowel_weights = _normalize_weight_map(segment_frequency_raw.get("vowel_weights", {}))
        consonant_weights = _normalize_weight_map(segment_frequency_raw.get("consonant_weights", {}))
        if vowel_weights or consonant_weights:
            normalized["segment_frequency"] = {
                "vowel_weights": vowel_weights,
                "consonant_weights": consonant_weights,
            }

    templates_raw = profile.get("template_weights_by_position", {})
    if isinstance(templates_raw, dict):
        template_weights_by_position: Dict[str, List[Tuple[str, float]]] = {}
        for position in TEMPLATE_POSITIONS:
            pairs = _normalize_weighted_pairs(templates_raw.get(position, []), label_pattern=r"[CV]+")
            if pairs:
                template_weights_by_position[position] = pairs
        if template_weights_by_position:
            normalized["template_weights_by_position"] = template_weights_by_position

    slot_class_weights = _normalize_nested_map(profile.get("slot_class_weights", {}))
    if slot_class_weights:
        normalized["slot_class_weights"] = slot_class_weights

    co_occurrence = _normalize_scalar_map(profile.get("co_occurrence", {}))
    if co_occurrence:
        normalized["co_occurrence"] = co_occurrence

    soft_constraints = _normalize_scalar_map(profile.get("soft_constraints", {}))
    if soft_constraints:
        normalized["soft_constraints"] = soft_constraints

    cluster = _normalize_scalar_map(profile.get("cluster", {}))
    if cluster:
        normalized["cluster"] = cluster

    if not normalized:
        return {}
    normalized["version"] = SOURCE_PROFILE_VERSION
    return normalized


def mix_source_profiles(profiles: List[Dict[str, Any]], shares: List[float]) -> Dict[str, Any]:
    """Mix source profiles using preset contribution shares."""
    if not profiles or not shares:
        return {}

    aligned_profiles: List[Dict[str, Any]] = []
    aligned_shares: List[float] = []
    for profile, share in zip(profiles, shares):
        safe_share = _as_float(share)
        if safe_share is None or safe_share <= 0:
            continue
        normalized_profile = normalize_source_profile(profile if isinstance(profile, dict) else {})
        if not normalized_profile:
            continue
        aligned_profiles.append(normalized_profile)
        aligned_shares.append(float(safe_share))

    if not aligned_profiles or sum(aligned_shares) <= 0:
        return {}

    result: Dict[str, Any] = {"version": SOURCE_PROFILE_VERSION}
    provenance_seen: set[str] = set()
    provenance_merged: List[str] = []
    for profile in aligned_profiles:
        for item in profile.get("provenance", []):
            text = str(item).strip()
            if not text or text in provenance_seen:
                continue
            provenance_seen.add(text)
            provenance_merged.append(text)
    if provenance_merged:
        result["provenance"] = provenance_merged

    segment_profiles = [profile.get("segment_frequency", {}) for profile in aligned_profiles]
    vowel_maps = [segment.get("vowel_weights", {}) for segment in segment_profiles if isinstance(segment, dict)]
    consonant_maps = [segment.get("consonant_weights", {}) for segment in segment_profiles if isinstance(segment, dict)]
    mixed_vowels = _normalize_weight_map(_weighted_average_maps(vowel_maps, aligned_shares, neutral=1.0))
    mixed_consonants = _normalize_weight_map(_weighted_average_maps(consonant_maps, aligned_shares, neutral=1.0))
    if mixed_vowels or mixed_consonants:
        result["segment_frequency"] = {
            "vowel_weights": mixed_vowels,
            "consonant_weights": mixed_consonants,
        }

    template_profiles = [
        profile.get("template_weights_by_position", {})
        for profile in aligned_profiles
        if isinstance(profile.get("template_weights_by_position", {}), dict)
    ]
    mixed_templates = _weighted_average_template_positions(template_profiles, aligned_shares)
    if mixed_templates:
        result["template_weights_by_position"] = mixed_templates

    slot_maps = [
        profile.get("slot_class_weights", {})
        for profile in aligned_profiles
        if isinstance(profile.get("slot_class_weights", {}), dict)
    ]
    mixed_slot_weights = _weighted_average_nested_maps(slot_maps, aligned_shares, neutral=1.0)
    if mixed_slot_weights:
        result["slot_class_weights"] = mixed_slot_weights

    for section_name in ("co_occurrence", "soft_constraints", "cluster"):
        section_maps = [
            profile.get(section_name, {})
            for profile in aligned_profiles
            if isinstance(profile.get(section_name, {}), dict)
        ]
        mixed_section = _weighted_average_maps(section_maps, aligned_shares, neutral=1.0)
        if mixed_section:
            result[section_name] = mixed_section

    return normalize_source_profile(result)


def build_phonotactic_overrides_from_source_profile(profile: Dict[str, Any], influence: float) -> Dict[str, Any]:
    """Build phonotactic overrides from a normalized source profile."""
    normalized = normalize_source_profile(profile)
    level = _as_float(influence)
    if not normalized or level is None or level <= 0:
        return {}
    level = float(level)

    default_profile = _default_phonotactic_profile()
    overrides: Dict[str, Any] = {}

    segment_frequency = normalized.get("segment_frequency", {})
    if isinstance(segment_frequency, dict):
        vowel_weights = segment_frequency.get("vowel_weights", {})
        consonant_weights = segment_frequency.get("consonant_weights", {})
        if isinstance(vowel_weights, dict) or isinstance(consonant_weights, dict):
            adjusted_vowels = {
                segment: max(0.0, _mean_one_blend(1.0, float(weight), level))
                for segment, weight in (vowel_weights.items() if isinstance(vowel_weights, dict) else [])
            }
            adjusted_consonants = {
                segment: max(0.0, _mean_one_blend(1.0, float(weight), level))
                for segment, weight in (consonant_weights.items() if isinstance(consonant_weights, dict) else [])
            }
            overrides["segment_frequency"] = {
                "enabled": True,
                "strength": float(level),
                "vowel_weights": adjusted_vowels,
                "consonant_weights": adjusted_consonants,
            }

    source_templates = normalized.get("template_weights_by_position", {})
    default_templates = _deep_get(default_profile, ["template_weights_by_position"], {})
    if isinstance(source_templates, dict):
        merged_templates: Dict[str, List[Tuple[str, float]]] = {}
        for position in TEMPLATE_POSITIONS:
            source_pairs = _normalize_weighted_pairs(source_templates.get(position, []), label_pattern=r"[CV]+")
            if not source_pairs:
                continue
            default_pairs = _normalize_weighted_pairs(
                default_templates.get(position, default_templates.get("single", [])),
                label_pattern=r"[CV]+",
            ) if isinstance(default_templates, dict) else []
            merged_pairs = _merge_template_pairs(source_pairs, default_pairs, level)
            if merged_pairs:
                merged_templates[position] = merged_pairs
        if merged_templates:
            overrides["template_weights_by_position"] = merged_templates

    for nested_section in ("slot_class_weights",):
        source_section = normalized.get(nested_section, {})
        if not isinstance(source_section, dict):
            continue
        default_section = _deep_get(default_profile, [nested_section], {})
        merged_section: Dict[str, Dict[str, float]] = {}
        for slot_name, slot_values in source_section.items():
            if not isinstance(slot_values, dict):
                continue
            default_slot = default_section.get(slot_name, {}) if isinstance(default_section, dict) else {}
            merged_slot: Dict[str, float] = {}
            labels = set(slot_values.keys()) | set(default_slot.keys()) if isinstance(default_slot, dict) else set(slot_values.keys())
            for label in labels:
                source_value = _as_float(slot_values.get(label))
                if source_value is None:
                    continue
                default_value = _as_float(default_slot.get(label)) if isinstance(default_slot, dict) else 1.0
                if default_value is None:
                    default_value = 1.0
                blended = _mean_one_blend(float(default_value), float(source_value), level)
                if blended > 0:
                    merged_slot[label] = float(blended)
            if merged_slot:
                merged_section[slot_name] = merged_slot
        if merged_section:
            overrides[nested_section] = merged_section

    for scalar_section in ("co_occurrence", "soft_constraints", "cluster"):
        source_values = normalized.get(scalar_section, {})
        if not isinstance(source_values, dict):
            continue
        default_values = _deep_get(default_profile, [scalar_section], {})
        merged_values: Dict[str, float] = {}
        keys = set(source_values.keys())
        for key in keys:
            source_value = _as_float(source_values.get(key))
            if source_value is None:
                continue
            default_value = _as_float(default_values.get(key)) if isinstance(default_values, dict) else None
            if default_value is None:
                default_value = 1.0
            merged_values[key] = float(_mean_one_blend(float(default_value), float(source_value), level))
        if merged_values:
            overrides[scalar_section] = merged_values

    return overrides


def merge_generation_overrides(
    sound_template_overrides: Dict[str, Any],
    source_profile_overrides: Dict[str, Any],
    fallback_segment_frequency_overrides: Dict[str, Any],
    ui_tuning_overrides: Dict[str, Any],
    advanced_override_dict: Dict[str, Any],
    use_source_segment_frequency: bool = True,
) -> Dict[str, Any]:
    merged = deep_merge_dict(
        sound_template_overrides if isinstance(sound_template_overrides, dict) else {},
        source_profile_overrides if isinstance(source_profile_overrides, dict) else {},
    )
    if (
        use_source_segment_frequency
        and isinstance(fallback_segment_frequency_overrides, dict)
        and "segment_frequency" not in merged
    ):
        merged = deep_merge_dict(merged, fallback_segment_frequency_overrides)
    merged = deep_merge_dict(merged, ui_tuning_overrides if isinstance(ui_tuning_overrides, dict) else {})
    if isinstance(advanced_override_dict, dict):
        merged = deep_merge_dict(merged, advanced_override_dict)
    return merged
