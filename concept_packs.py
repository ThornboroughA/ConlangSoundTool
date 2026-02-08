from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

PACKS_DIR = Path(__file__).resolve().parent / "data" / "concept_packs"

PACK_CATEGORIES = {
    "world",
    "society",
    "belief",
    "values",
    "material",
    "aesthetic",
    "time",
    "power",
    "food",
    "kinship",
    "craft",
    "commerce",
}

DEFAULT_REGISTER_BIAS = {
    "neutral": 1.0,
    "formal": 0.85,
    "poetic": 0.8,
    "archaic": 0.7,
    "sacred": 0.75,
    "taboo": 0.4,
}

DEFAULT_TIER_LIMITS = {
    "core": 100,
    "context": 200,
    "optional": 100,
}

DEFAULT_PACK_SELECTION = [
    "world_landforms",
    "world_hydrology",
    "world_weather",
    "world_celestial",
    "flora_basic",
    "fauna_basic",
    "society_roles",
    "kinship_basic",
    "settlement_terms",
    "values_emotions",
    "material_culture",
    "food_agriculture",
    "time_counting",
]

DEFAULT_CONCEPT_PACK_CONFIG: Dict[str, Any] = {
    "enabled_packs": list(DEFAULT_PACK_SELECTION),
    "tier_limits": dict(DEFAULT_TIER_LIMITS),
    "biome_filters": ["temperate_forest"],
    "register_bias": dict(DEFAULT_REGISTER_BIAS),
    "random_seed": 42,
}


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip()).strip("_").lower()
    return cleaned or "concept"


def _normalize_tags(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def load_pack(path: Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Pack {path} must be a JSON object.")
    return payload


def load_packs(pack_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    directory = pack_dir or PACKS_DIR
    packs: Dict[str, Dict[str, Any]] = {}
    if not directory.exists():
        return packs
    for path in sorted(directory.glob("*.json")):
        payload = load_pack(path)
        pack_id = str(payload.get("pack_id") or _slug(path.stem))
        payload["pack_id"] = pack_id
        packs[pack_id] = payload
    return packs


def list_packs_by_category(packs: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {category: [] for category in sorted(PACK_CATEGORIES)}
    for pack in packs.values():
        category = str(pack.get("category") or "world")
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(pack)
    for category in grouped:
        grouped[category] = sorted(grouped[category], key=lambda item: str(item.get("pack_name", "")))
    return grouped


def _weighted_choice(entries: Sequence[Dict[str, Any]], weights: Sequence[float], rng: random.Random) -> Optional[Dict[str, Any]]:
    if not entries:
        return None
    total = sum(max(weight, 0.0) for weight in weights)
    if total <= 0:
        return rng.choice(list(entries))
    pick = rng.uniform(0, total)
    running = 0.0
    for entry, weight in zip(entries, weights):
        running += max(weight, 0.0)
        if running >= pick:
            return entry
    return entries[-1]


def _weighted_sample(entries: List[Dict[str, Any]], weights: List[float], k: int, rng: random.Random) -> List[Dict[str, Any]]:
    if k <= 0 or not entries:
        return []
    selected: List[Dict[str, Any]] = []
    pool = list(entries)
    pool_weights = list(weights)
    while pool and len(selected) < k:
        choice = _weighted_choice(pool, pool_weights, rng)
        if choice is None:
            break
        index = pool.index(choice)
        selected.append(choice)
        pool.pop(index)
        pool_weights.pop(index)
    return selected


def _entry_weight(entry: Dict[str, Any], register_bias: Dict[str, float]) -> float:
    base = float(entry.get("weight", 1.0))
    register = str(entry.get("register", "neutral"))
    bias = float(register_bias.get(register, 1.0))
    return max(0.0, base * bias)


def _entry_matches_biome(entry: Dict[str, Any], biome_filters: Sequence[str]) -> bool:
    if not biome_filters:
        return True
    entry_biomes = entry.get("biomes", [])
    if not entry_biomes:
        return True
    return any(biome in entry_biomes for biome in biome_filters)


def _expand_entry(entry: Dict[str, Any], pack: Dict[str, Any]) -> Dict[str, Any]:
    expanded = dict(entry)
    expanded.setdefault("concept_id", f"{pack.get('pack_id','pack')}.{_slug(entry.get('meaning','concept'))}")
    expanded.setdefault("gloss", str(expanded.get("meaning", "")).upper().replace(" ", "_"))
    expanded.setdefault("pos", "N")
    expanded["tags"] = sorted(set(_normalize_tags(pack.get("tags")) + _normalize_tags(expanded.get("tags"))))
    expanded["biomes"] = _normalize_tags(expanded.get("biomes"))
    expanded["register"] = str(expanded.get("register", "neutral"))
    expanded["weight"] = float(expanded.get("weight", 1.0))
    expanded["source_pack"] = str(pack.get("pack_id"))
    expanded["pack_category"] = str(pack.get("category", "world"))
    expanded["tier"] = str(expanded.get("tier") or pack.get("tier") or "context")
    return expanded


def select_pack_entries(
    concept_pack_config: Optional[Dict[str, Any]] = None,
    pack_dir: Optional[Path] = None,
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    packs = load_packs(pack_dir)
    if not packs:
        return []

    config = dict(DEFAULT_CONCEPT_PACK_CONFIG)
    if isinstance(concept_pack_config, dict):
        config.update({key: concept_pack_config.get(key, config.get(key)) for key in config.keys()})

    enabled = config.get("enabled_packs")
    if enabled is None or not isinstance(enabled, list):
        enabled = list(DEFAULT_PACK_SELECTION)

    enabled = [pack_id for pack_id in enabled if pack_id in packs]
    biome_filters = [str(item) for item in config.get("biome_filters", []) if str(item)]
    register_bias = config.get("register_bias")
    if not isinstance(register_bias, dict):
        register_bias = dict(DEFAULT_REGISTER_BIAS)

    tier_limits = config.get("tier_limits")
    if not isinstance(tier_limits, dict):
        tier_limits = dict(DEFAULT_TIER_LIMITS)

    if rng is None:
        seed = config.get("random_seed")
        rng = random.Random(int(seed) if seed is not None else None)

    tiered_entries: Dict[str, List[Dict[str, Any]]] = {"context": [], "optional": []}

    for pack_id in enabled:
        pack = packs.get(pack_id)
        if not pack:
            continue
        entries = pack.get("entries", [])
        if not isinstance(entries, list):
            continue
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                continue
            expanded = _expand_entry(raw_entry, pack)
            if not _entry_matches_biome(expanded, biome_filters):
                continue
            tier = str(expanded.get("tier", "context"))
            if tier not in tiered_entries:
                tiered_entries[tier] = []
            tiered_entries[tier].append(expanded)

    selected: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    for tier in ["context", "optional"]:
        entries = tiered_entries.get(tier, [])
        if not entries:
            continue
        weights = [_entry_weight(entry, register_bias) for entry in entries]
        limit = int(tier_limits.get(tier, len(entries))) if tier_limits else len(entries)
        sampled = _weighted_sample(entries, weights, min(limit, len(entries)), rng)
        for entry in sampled:
            concept_id = str(entry.get("concept_id", ""))
            if not concept_id or concept_id in seen_ids:
                continue
            seen_ids.add(concept_id)
            selected.append(entry)

    return selected


def pack_coverage(entries: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    coverage: Dict[str, int] = {}
    for entry in entries:
        category = str(entry.get("pack_category") or "world")
        coverage[category] = coverage.get(category, 0) + 1
    return coverage
