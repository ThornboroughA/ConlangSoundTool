from __future__ import annotations

import json
import hashlib
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from concept_packs import DEFAULT_REGISTER_BIAS

TEMPLATES_PATH = Path(__file__).resolve().parent / "data" / "name_templates.json"

DEFAULT_NAME_CONFIG: Dict[str, Any] = {
    "counts_by_type": {
        "personal": {"given": 50, "family": 20, "title": 10},
        "toponym": {"settlement": 30, "hydronym": 15, "terrain": 15},
    },
    "template_weights": {},
    "archaic_bias": {"self": 0.7, "parent": 0.2, "proto": 0.1},
    "register_bias": dict(DEFAULT_REGISTER_BIAS),
    "biome_filters": [],
    "random_seed": 42,
}


def _now_iso() -> str:
    return datetime.now().isoformat()


def _normalize_tags(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def load_templates(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    template_path = path or TEMPLATES_PATH
    if not template_path.exists():
        return []
    with template_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("Name templates must be a JSON list.")
    return [item for item in payload if isinstance(item, dict)]


def _entry_matches_tags(entry: Dict[str, Any], tags_any: Sequence[str]) -> bool:
    if not tags_any:
        return True
    entry_tags = set(_normalize_tags(entry.get("tags")))
    return any(tag in entry_tags for tag in tags_any)


def _entry_matches_biome(entry: Dict[str, Any], biome_filters: Sequence[str]) -> bool:
    if not biome_filters:
        return True
    entry_biomes = _normalize_tags(entry.get("biomes"))
    if not entry_biomes:
        return True
    return any(biome in entry_biomes for biome in biome_filters)


def _entry_register_weight(entry: Dict[str, Any], register_bias: Dict[str, float]) -> float:
    register = str(entry.get("register", "neutral"))
    return float(register_bias.get(register, 1.0))


def _collect_candidate_entries(
    sources: Sequence[Tuple[str, Dict[str, Any]]],
    tags_any: Sequence[str],
    pos_any: Sequence[str],
    biome_filters: Sequence[str],
) -> List[Tuple[Dict[str, Any], str]]:
    candidates: List[Tuple[Dict[str, Any], str]] = []
    for label, model in sources:
        lexicon = model.get("lexicon", []) if isinstance(model, dict) else []
        if not isinstance(lexicon, list):
            continue
        for entry in lexicon:
            if not isinstance(entry, dict):
                continue
            if pos_any:
                pos = str(entry.get("pos", ""))
                if pos not in pos_any:
                    continue
            if not _entry_matches_tags(entry, tags_any):
                continue
            if not _entry_matches_biome(entry, biome_filters):
                continue
            candidates.append((entry, label))
    return candidates


def _weighted_pick(
    candidates: Sequence[Tuple[Dict[str, Any], str]],
    source_bias: Dict[str, float],
    register_bias: Dict[str, float],
    rng: random.Random,
) -> Optional[Tuple[Dict[str, Any], str]]:
    if not candidates:
        return None
    weights: List[float] = []
    for entry, label in candidates:
        bias = float(source_bias.get(label, 1.0))
        weight = bias * _entry_register_weight(entry, register_bias)
        weights.append(max(weight, 0.0))

    total = sum(weights)
    if total <= 0:
        return rng.choice(list(candidates))
    pick = rng.uniform(0, total)
    running = 0.0
    for item, weight in zip(candidates, weights):
        running += weight
        if running >= pick:
            return item
    return candidates[-1]


def _normalize_config(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    config = dict(DEFAULT_NAME_CONFIG)
    if isinstance(value, dict):
        for key in config:
            if key in value:
                config[key] = value.get(key)
    return config


def _template_weight(template: Dict[str, Any], overrides: Dict[str, Any]) -> float:
    base = float(template.get("weight", 1.0))
    template_id = str(template.get("template_id", ""))
    override = overrides.get(template_id)
    if override is None:
        return base
    try:
        return float(override)
    except (TypeError, ValueError):
        return base


def _pick_template(
    templates: Sequence[Dict[str, Any]],
    name_type: str,
    subtype: str,
    overrides: Dict[str, Any],
    rng: random.Random,
) -> Optional[Dict[str, Any]]:
    filtered = [t for t in templates if t.get("name_type") == name_type and t.get("subtype") == subtype]
    if not filtered:
        return None
    weights = [_template_weight(t, overrides) for t in filtered]
    total = sum(max(w, 0.0) for w in weights)
    if total <= 0:
        return rng.choice(filtered)
    pick = rng.uniform(0, total)
    running = 0.0
    for template, weight in zip(filtered, weights):
        running += max(weight, 0.0)
        if running >= pick:
            return template
    return filtered[-1]


def _fallback_entry(sources: Sequence[Tuple[str, Dict[str, Any]]], rng: random.Random) -> Optional[Tuple[Dict[str, Any], str]]:
    for label, model in sources:
        lexicon = model.get("lexicon", []) if isinstance(model, dict) else []
        if isinstance(lexicon, list) and lexicon:
            return rng.choice(lexicon), label
    return None


def _generate_name_from_template(
    template: Dict[str, Any],
    sources: Sequence[Tuple[str, Dict[str, Any]]],
    source_bias: Dict[str, float],
    register_bias: Dict[str, float],
    biome_filters: Sequence[str],
    rng: random.Random,
) -> Optional[Dict[str, Any]]:
    parts = template.get("parts", []) if isinstance(template.get("parts", []), list) else []
    if not parts:
        return None

    selected_entries: List[Tuple[Dict[str, Any], str]] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        tags_any = _normalize_tags(part.get("tags_any"))
        pos_any = _normalize_tags(part.get("pos_any"))
        candidates = _collect_candidate_entries(sources, tags_any, pos_any, biome_filters)
        if not candidates:
            fallback = _fallback_entry(sources, rng)
            if not fallback:
                return None
            selected_entries.append(fallback)
            continue
        choice = _weighted_pick(candidates, source_bias, register_bias, rng)
        if not choice:
            return None
        selected_entries.append(choice)

    joiner = str(template.get("joiner", ""))
    form = joiner.join(str(entry.get("ipa", "")).strip() for entry, _ in selected_entries if str(entry.get("ipa", "")).strip())
    gloss = " ".join(str(entry.get("meaning", "")).strip() for entry, _ in selected_entries if str(entry.get("meaning", "")).strip())
    concepts = [str(entry.get("concept_id", "")) for entry, _ in selected_entries if str(entry.get("concept_id", ""))]

    return {
        "form_ipa": form.strip(),
        "gloss": gloss.strip(),
        "source_concepts": concepts,
    }


def generate_names(
    language_model: Dict[str, Any],
    name_config: Optional[Dict[str, Any]] = None,
    templates: Optional[Sequence[Dict[str, Any]]] = None,
    ancestors: Optional[Dict[str, Dict[str, Any]]] = None,
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    config = _normalize_config(name_config)
    counts_by_type = config.get("counts_by_type", {})
    template_overrides = config.get("template_weights", {})
    source_bias = config.get("archaic_bias", {})
    register_bias = config.get("register_bias", {})
    biome_filters = _normalize_tags(config.get("biome_filters"))

    if rng is None:
        seed = config.get("random_seed")
        rng = random.Random(int(seed) if seed is not None else None)

    template_list = list(templates) if templates is not None else load_templates()

    sources: List[Tuple[str, Dict[str, Any]]] = [("self", language_model)]
    if isinstance(ancestors, dict):
        if "parent" in ancestors and isinstance(ancestors["parent"], dict):
            sources.append(("parent", ancestors["parent"]))
        if "proto" in ancestors and isinstance(ancestors["proto"], dict):
            sources.append(("proto", ancestors["proto"]))

    names: List[Dict[str, Any]] = []
    used_forms: set[str] = set()
    language_id = str(language_model.get("meta", {}).get("language_id", ""))

    for name_type, subtypes in counts_by_type.items():
        if not isinstance(subtypes, dict):
            continue
        for subtype, count in subtypes.items():
            target = max(0, int(count))
            for index in range(1, target + 1):
                for _ in range(20):
                    template = _pick_template(template_list, name_type, subtype, template_overrides, rng)
                    if not template:
                        break
                    payload = _generate_name_from_template(
                        template=template,
                        sources=sources,
                        source_bias=source_bias,
                        register_bias=register_bias,
                        biome_filters=biome_filters,
                        rng=rng,
                    )
                    if not payload or not payload.get("form_ipa"):
                        continue
                    form = str(payload.get("form_ipa", ""))
                    if form in used_forms:
                        continue
                    used_forms.add(form)
                    names.append(
                        {
                            "name_id": f"NAME:{name_type}:{subtype}:{index:04d}",
                            "name_type": name_type,
                            "subtype": subtype,
                            "template_id": str(template.get("template_id", "")),
                            "form_ipa": form,
                            "romanized": form,
                            "gloss": str(payload.get("gloss", "")),
                            "source_language_id": language_id,
                            "source_concepts": payload.get("source_concepts", []),
                            "locked": False,
                        }
                    )
                    break
    return names


def merge_locked(existing: Sequence[Dict[str, Any]], generated: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    locked = [entry for entry in existing if isinstance(entry, dict) and entry.get("locked") is True]
    if not locked:
        return generated
    index_by_key: Dict[Tuple[str, str], int] = {}
    for idx, entry in enumerate(generated):
        key = (str(entry.get("name_type", "")), str(entry.get("subtype", "")))
        if key not in index_by_key:
            index_by_key[key] = idx

    for entry in locked:
        key = (str(entry.get("name_type", "")), str(entry.get("subtype", "")))
        if key in index_by_key:
            generated[index_by_key[key]] = entry
        else:
            generated.append(entry)
    return generated


def names_payload(language_id: str, names: Sequence[Dict[str, Any]], config_hash: str) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "language_id": language_id,
        "generated_at": _now_iso(),
        "config_hash": config_hash,
        "names": list(names),
    }


def config_hash(config: Dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def load_names(project_dir: Path, language_id: str) -> Optional[Dict[str, Any]]:
    path = Path(project_dir) / "names" / f"{language_id}.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return None
    return payload


def save_names(project_dir: Path, payload: Dict[str, Any]) -> None:
    names_dir = Path(project_dir) / "names"
    names_dir.mkdir(parents=True, exist_ok=True)
    language_id = str(payload.get("language_id", "language"))
    path = names_dir / f"{language_id}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def rebuild_names_subtree(
    project_dir: Path,
    root_language_id: str,
    languages: Dict[str, Dict[str, Any]],
    name_config: Dict[str, Any],
    templates: Optional[Sequence[Dict[str, Any]]] = None,
) -> None:
    if root_language_id not in languages:
        return
    parent_map: Dict[str, List[str]] = {}
    for lang_id, language in languages.items():
        meta = language.get("meta", {}) if isinstance(language, dict) else {}
        parent_id = meta.get("parent_id")
        if parent_id:
            parent_map.setdefault(str(parent_id), []).append(lang_id)

    def _walk(current_id: str) -> None:
        current_lang = languages.get(current_id)
        if not current_lang:
            return
        existing = load_names(project_dir, current_id)
        existing_names = existing.get("names", []) if isinstance(existing, dict) else []
        ancestors: Dict[str, Dict[str, Any]] = {}
        meta = current_lang.get("meta", {}) if isinstance(current_lang, dict) else {}
        parent_id = meta.get("parent_id")
        if parent_id and parent_id in languages:
            ancestors["parent"] = languages[parent_id]
        proto_id = meta.get("parent_id")
        while proto_id and proto_id in languages:
            parent_meta = languages[proto_id].get("meta", {})
            next_parent = parent_meta.get("parent_id") if isinstance(parent_meta, dict) else None
            if next_parent is None:
                ancestors["proto"] = languages[proto_id]
                break
            proto_id = next_parent

        rng = random.Random(int(name_config.get("random_seed", 42)))
        generated = generate_names(
            language_model=current_lang,
            name_config=name_config,
            templates=templates,
            ancestors=ancestors,
            rng=rng,
        )
        merged = merge_locked(existing_names, generated)
        payload = names_payload(str(meta.get("language_id", current_id)), merged, config_hash(name_config))
        save_names(project_dir, payload)

        for child_id in parent_map.get(current_id, []):
            _walk(child_id)

    _walk(root_language_id)
