"""Utilities for PHOIBLE prevalence-based representation weighting."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Sequence, Tuple

PHOIBLE_REPRESENTATION_MODEL = "phoible_prevalence_log1p_mean1_v1"
PHOIBLE_REPRESENTATION_SCOPE = (
    "cross-inventory segment prevalence (typological prior; "
    "not within-language token frequency)"
)


def clean_phoible_value(value: Any) -> str:
    text = str(value).strip()
    return "" if text.upper() == "NA" else text


def build_glyph_inventory_counts(rows: Iterable[Dict[str, Any]]) -> Tuple[Dict[str, int], int]:
    """Return GlyphID -> distinct inventory count and total distinct inventory count."""
    glyph_inventory_ids: Dict[str, set[str]] = defaultdict(set)
    inventory_ids: set[str] = set()

    for row in rows:
        inventory_id = clean_phoible_value(row.get("InventoryID", ""))
        if not inventory_id:
            continue
        inventory_ids.add(inventory_id)

        glyph_id = clean_phoible_value(row.get("GlyphID", ""))
        if glyph_id:
            glyph_inventory_ids[glyph_id].add(inventory_id)

    glyph_inventory_counts = {
        glyph_id: len(inventory_set)
        for glyph_id, inventory_set in glyph_inventory_ids.items()
    }
    return glyph_inventory_counts, len(inventory_ids)


def _safe_prevalence_count(glyph_id: str, glyph_inventory_counts: Dict[str, Any]) -> int:
    if not glyph_id:
        return 0
    raw_count = glyph_inventory_counts.get(glyph_id, 0)
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        return 0
    return count if count > 0 else 0


def _bucket_for_segment_class(segment_class: str, include_tones: bool) -> str:
    if segment_class == "vowel":
        return "vowel"
    if segment_class == "consonant":
        return "consonant"
    if segment_class == "tone" and include_tones:
        return "consonant"
    return ""


def build_prevalence_weighted_entries(
    rows: Sequence[Dict[str, Any]],
    include_marginal: bool,
    include_tones: bool,
    glyph_inventory_counts: Dict[str, Any],
    core_multiplier: float,
    marginal_multiplier: float,
) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
    """Build raw weighted vowel/consonant entry lists from PHOIBLE rows."""
    weighted_rows: List[Dict[str, Any]] = []
    bucket_scores: Dict[str, List[float]] = {"vowel": [], "consonant": []}

    for row in rows:
        segment = clean_phoible_value(row.get("Phoneme", ""))
        if not segment:
            continue

        segment_class = clean_phoible_value(row.get("SegmentClass", "")).lower()
        bucket = _bucket_for_segment_class(segment_class, include_tones=include_tones)
        if not bucket:
            continue

        is_marginal = clean_phoible_value(row.get("Marginal", "")).upper() == "TRUE"
        if is_marginal and not include_marginal:
            continue

        glyph_id = clean_phoible_value(row.get("GlyphID", ""))
        prevalence_count = _safe_prevalence_count(glyph_id, glyph_inventory_counts)
        # Fallback to neutral base score if prevalence cannot be resolved.
        base_score = math.log1p(float(prevalence_count)) if prevalence_count > 0 else 1.0

        bucket_scores[bucket].append(base_score)
        weighted_rows.append(
            {
                "bucket": bucket,
                "segment": segment,
                "is_marginal": is_marginal,
                "base_score": base_score,
            }
        )

    bucket_means: Dict[str, float] = {}
    for bucket_name in ("vowel", "consonant"):
        scores = bucket_scores[bucket_name]
        if scores:
            bucket_means[bucket_name] = sum(scores) / float(len(scores))
        else:
            bucket_means[bucket_name] = 1.0

    vowels_raw: List[Dict[str, float]] = []
    consonants_raw: List[Dict[str, float]] = []
    for entry in weighted_rows:
        bucket = str(entry.get("bucket", ""))
        segment = str(entry.get("segment", ""))
        base_score = float(entry.get("base_score", 1.0))
        is_marginal = bool(entry.get("is_marginal", False))
        mean_score = bucket_means.get(bucket, 1.0)
        normalized_score = (base_score / mean_score) if mean_score > 0 else 1.0
        multiplier = float(marginal_multiplier if is_marginal else core_multiplier)
        representation = float(normalized_score * multiplier)
        output_entry = {"segment": segment, "representation": representation}
        if bucket == "vowel":
            vowels_raw.append(output_entry)
        else:
            consonants_raw.append(output_entry)

    return vowels_raw, consonants_raw


def build_representation_meta(
    total_inventory_count: int,
    core_multiplier: float,
    marginal_multiplier: float,
) -> Dict[str, Any]:
    return {
        "representation_model": PHOIBLE_REPRESENTATION_MODEL,
        "representation_scope": PHOIBLE_REPRESENTATION_SCOPE,
        "representation_inventory_count": int(total_inventory_count),
        "core_multiplier": float(core_multiplier),
        "marginal_multiplier": float(marginal_multiplier),
    }
