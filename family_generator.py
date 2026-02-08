from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import random
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

import project_io
import sound_change_engine


@dataclass
class Node:
    node_id: str
    children: List["Node"] = field(default_factory=list)
    parent: Optional["Node"] = None
    year: Optional[int] = None
    height: int = 0

    def is_leaf(self) -> bool:
        return not self.children


def build_random_binary_topology(extant_leaf_count: int, rng: random.Random) -> Node:
    if extant_leaf_count < 1:
        raise ValueError("extant_leaf_count must be at least 1.")

    nodes = [Node(f"leaf_{index:03d}") for index in range(1, extant_leaf_count + 1)]
    counter = 1
    while len(nodes) > 1:
        left, right = rng.sample(nodes, 2)
        nodes.remove(left)
        nodes.remove(right)
        parent = Node(f"node_{counter:03d}", children=[left, right])
        left.parent = parent
        right.parent = parent
        nodes.append(parent)
        counter += 1
    return nodes[0]


def _compute_heights(node: Node) -> int:
    if node.is_leaf():
        node.height = 0
        return 0
    child_heights = [_compute_heights(child) for child in node.children]
    node.height = 1 + max(child_heights) if child_heights else 0
    return node.height


def assign_years(root: Node, extant_year: int, min_branch_years: int, rng: random.Random) -> None:
    _compute_heights(root)
    root.year = 0

    def _assign(node: Node) -> None:
        if node.year is None:
            node.year = 0
        for child in node.children:
            if child.is_leaf():
                child.year = extant_year
            else:
                min_year = node.year + min_branch_years
                max_year = extant_year - (child.height * min_branch_years)
                if max_year < min_year:
                    max_year = min_year
                child.year = rng.randint(min_year, max_year)
            _assign(child)

    _assign(root)


def _collect_nodes_preorder(node: Node) -> List[Node]:
    nodes = [node]
    for child in node.children:
        nodes.extend(_collect_nodes_preorder(child))
    return nodes


def _edge_seed(base_seed: int, parent_id: str, child_id: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{parent_id}->{child_id}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


VOWEL_RAISE_PAIRS: List[Tuple[str, str]] = [
    ("a", "e"),
    ("e", "i"),
    ("o", "u"),
    ("ɛ", "e"),
    ("ɔ", "o"),
    ("æ", "e"),
    ("ɪ", "i"),
    ("ʊ", "u"),
]

VOWEL_LOWER_PAIRS: List[Tuple[str, str]] = [
    ("i", "e"),
    ("u", "o"),
    ("e", "a"),
    ("o", "ɔ"),
    ("e", "ɛ"),
    ("e", "æ"),
    ("i", "ɪ"),
    ("u", "ʊ"),
]


def _pick_pair(pairs: Iterable[Tuple[str, str]], vowels: List[str], rng: random.Random) -> Optional[Tuple[str, str]]:
    candidates = [pair for pair in pairs if pair[0] in vowels]
    if not candidates:
        return None
    return rng.choice(candidates)


def _template_rule(template_id: str, vowels: List[str], consonants: List[str], rng: random.Random) -> Optional[Tuple[str, str]]:
    if template_id == "stop_voicing":
        candidates = [(frm, to) for frm, to in [("p", "b"), ("t", "d"), ("k", "g")] if frm in consonants]
        return rng.choice(candidates) if candidates else None
    if template_id == "stop_devoicing":
        candidates = [(frm, to) for frm, to in [("b", "p"), ("d", "t"), ("g", "k")] if frm in consonants]
        return rng.choice(candidates) if candidates else None
    if template_id == "s_voicing":
        return ("s", "z") if "s" in consonants else None
    if template_id == "h_loss":
        return ("h", "") if "h" in consonants else None
    if template_id == "approximant_shift":
        if "w" in consonants:
            return ("w", "v")
        if "v" in consonants:
            return ("v", "w")
        return None
    if template_id == "r_shift":
        if "r" in consonants:
            return ("r", "ɾ")
        if "ɾ" in consonants:
            return ("ɾ", "r")
        return None
    if template_id == "vowel_raise_pair":
        return _pick_pair(VOWEL_RAISE_PAIRS, vowels, rng)
    if template_id == "vowel_lower_pair":
        return _pick_pair(VOWEL_LOWER_PAIRS, vowels, rng)
    return None


def _event_count(expected_events: float, rng: random.Random) -> int:
    jitter = rng.uniform(-0.4, 0.4)
    return max(1, int(round(expected_events + jitter)))


def generate_changeset(
    parent_inventory: Dict[str, Any],
    enabled_templates: List[str],
    event_count: int,
    rng: random.Random,
    changeset_id: str,
    name: str,
    description: str = "",
) -> Dict[str, Any]:
    vowels = parent_inventory.get("vowels", [])
    consonants = parent_inventory.get("consonants", [])
    if not isinstance(vowels, list):
        vowels = []
    if not isinstance(consonants, list):
        consonants = []

    rules: List[Dict[str, Any]] = []
    used_from: Set[str] = set()
    attempts = 0
    max_attempts = max(20, event_count * 10)
    templates = [template for template in enabled_templates if isinstance(template, str)]
    if not templates:
        templates = []

    while len(rules) < event_count and attempts < max_attempts:
        attempts += 1
        if not templates:
            break
        template_id = rng.choice(templates)
        rule = _template_rule(template_id, vowels, consonants, rng)
        if not rule:
            continue
        frm, to = rule
        if frm in used_from:
            continue
        used_from.add(frm)
        rules.append({"from": frm, "to": to, "enabled": True, "notes": ""})

    return {
        "schema_version": 1,
        "changeset_id": changeset_id,
        "name": name,
        "description": description,
        "rules": rules,
    }


def apply_lexicon_overrides(language: Dict[str, Any], overrides: Dict[str, str]) -> Dict[str, Any]:
    if not overrides:
        return language
    lexicon = language.get("lexicon", [])
    if not isinstance(lexicon, list):
        return language
    for entry in lexicon:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", ""))
        if entry_id in overrides:
            entry["ipa"] = overrides[entry_id]
    return language


def _register_language(project: Dict[str, Any], language_id: str) -> None:
    index = project.get("language_index", [])
    if not isinstance(index, list):
        index = []
    exists = any(isinstance(item, dict) and item.get("language_id") == language_id for item in index)
    if not exists:
        index.append({"language_id": language_id, "filename": f"{language_id}.json"})
    project["language_index"] = index


def generate_family(
    project_dir: Path,
    proto_language_path: Path,
    family_config: Dict[str, Any],
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    project = project_io.load_project(project_dir)
    proto_language = project_io.load_language(proto_language_path)
    proto_language = project_io.normalize_language_snapshot(proto_language)

    meta = proto_language.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    root_language_id = str(meta.get("language_id") or "proto")
    meta.setdefault("language_id", root_language_id)
    meta.setdefault("name", root_language_id)
    meta.setdefault("year", 0)
    meta.setdefault("parent_id", None)
    meta.setdefault("changeset_id", None)
    meta.setdefault("created_at", datetime.now().isoformat())
    meta.setdefault("notes", "")
    meta.setdefault("lexicon_overrides", {})
    proto_language["meta"] = meta

    project["root_language_id"] = root_language_id
    project["family_config"] = {
        key: family_config[key]
        for key in [
            "extant_language_count",
            "min_branch_years",
            "events_per_1000_years",
            "sound_change_templates_enabled",
            "tree_type",
        ]
        if key in family_config
    }

    extant_language_count = int(family_config.get("extant_language_count", 50))
    min_branch_years = int(family_config.get("min_branch_years", 100))
    events_per_1000_years = float(family_config.get("events_per_1000_years", 6.0))
    enabled_templates = list(family_config.get("sound_change_templates_enabled", []))

    time_span_years = int(family_config.get("time_span_years", project.get("time_span_years", 2000)))
    extant_year = int(family_config.get("extant_year", project.get("extant_year", time_span_years)))
    if extant_year <= 0:
        extant_year = max(1, time_span_years)
    project["time_span_years"] = time_span_years
    project["extant_year"] = extant_year

    seed = int(family_config.get("seed", project.get("seed", 0)))
    rng = random.Random(seed)

    root = build_random_binary_topology(extant_language_count, rng)
    assign_years(root, extant_year=extant_year, min_branch_years=min_branch_years, rng=rng)

    nodes = _collect_nodes_preorder(root)
    root.node_id = root_language_id
    counter = 1
    for node in nodes[1:]:
        node.node_id = f"lang_{counter:03d}"
        counter += 1

    languages_dir = Path(project.get("_project_dir", project_dir)) / project.get("paths", {}).get("languages_dir", "languages")
    changesets_dir = Path(project.get("_project_dir", project_dir)) / project.get("paths", {}).get("changesets_dir", "changesets")
    languages_dir.mkdir(parents=True, exist_ok=True)
    changesets_dir.mkdir(parents=True, exist_ok=True)

    project_io.save_language(proto_language, languages_dir / f"{root_language_id}.json")
    _register_language(project, root_language_id)

    language_map: Dict[str, Dict[str, Any]] = {root_language_id: proto_language}

    total_nodes = len(nodes)
    processed = 1

    for node in nodes[1:]:
        parent = node.parent
        if parent is None:
            continue
        parent_language = language_map.get(parent.node_id)
        if parent_language is None:
            continue

        duration = max(1, (node.year or extant_year) - (parent.year or 0))
        expected_events = events_per_1000_years * (duration / 1000.0)
        edge_rng = random.Random(_edge_seed(seed, parent.node_id, node.node_id))
        event_count = _event_count(expected_events, edge_rng)

        changeset_id = f"chg_{parent.node_id}_{node.node_id}"
        changeset_name = f"{parent.node_id}→{node.node_id}"
        changeset = generate_changeset(
            parent_inventory=parent_language.get("inventory", {}),
            enabled_templates=enabled_templates,
            event_count=event_count,
            rng=edge_rng,
            changeset_id=changeset_id,
            name=changeset_name,
            description=f"{event_count} sound-change event(s)",
        )
        project_io.save_changeset(changeset, changesets_dir / f"{changeset_id}.json")

        child_language = sound_change_engine.apply_changeset_to_language(parent_language, changeset)
        child_meta = {
            "language_id": node.node_id,
            "name": node.node_id,
            "year": int(node.year or extant_year),
            "parent_id": parent.node_id,
            "changeset_id": changeset_id,
            "created_at": datetime.now().isoformat(),
            "notes": "",
            "lexicon_overrides": {},
        }
        child_language["meta"] = child_meta
        child_language = project_io.normalize_language_snapshot(child_language)

        project_io.save_language(child_language, languages_dir / f"{node.node_id}.json")
        _register_language(project, node.node_id)
        language_map[node.node_id] = child_language

        processed += 1
        if progress_callback:
            progress_callback(processed, total_nodes)

    project_io.save_project(project)
    return project


def build_child_map(languages: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    children: Dict[str, List[str]] = {}
    for language_id, language in languages.items():
        meta = language.get("meta", {})
        if not isinstance(meta, dict):
            continue
        parent_id = meta.get("parent_id")
        if parent_id:
            children.setdefault(str(parent_id), []).append(language_id)
    return children


def path_to_root(languages: Dict[str, Dict[str, Any]], language_id: str) -> List[str]:
    path: List[str] = []
    current = language_id
    visited: Set[str] = set()
    while current and current not in visited:
        visited.add(current)
        path.append(current)
        language = languages.get(current, {})
        meta = language.get("meta", {})
        if not isinstance(meta, dict):
            break
        current = meta.get("parent_id")
    return path


def rebuild_subtree(project_dir: Path, root_language_id: str) -> None:
    project = project_io.load_project(project_dir)
    languages_dir = Path(project.get("_project_dir", project_dir)) / project.get("paths", {}).get("languages_dir", "languages")
    changesets_dir = Path(project.get("_project_dir", project_dir)) / project.get("paths", {}).get("changesets_dir", "changesets")

    language_index = project.get("language_index", [])
    if not isinstance(language_index, list):
        return

    languages: Dict[str, Dict[str, Any]] = {}
    for entry in language_index:
        if not isinstance(entry, dict):
            continue
        language_id = entry.get("language_id")
        filename = entry.get("filename")
        if not language_id or not filename:
            continue
        path = languages_dir / filename
        if not path.exists():
            continue
        languages[str(language_id)] = project_io.load_language(path)

    children_map = build_child_map(languages)

    def _rebuild_node(parent_id: str) -> None:
        parent_language = languages.get(parent_id)
        if not parent_language:
            return
        for child_id in children_map.get(parent_id, []):
            existing_child = languages.get(child_id)
            if not existing_child:
                continue
            meta = existing_child.get("meta", {})
            if not isinstance(meta, dict):
                continue
            changeset_id = meta.get("changeset_id")
            if not changeset_id:
                continue
            changeset_path = changesets_dir / f"{changeset_id}.json"
            if not changeset_path.exists():
                continue
            changeset = project_io.load_changeset(changeset_path)
            rebuilt = sound_change_engine.apply_changeset_to_language(parent_language, changeset)

            for key in [
                "style_name",
                "concept_list_name",
                "concept_pack_config",
                "grammar_profile_name",
                "syllable_range",
                "syllable_separator",
                "phonotactic_profile_overrides",
            ]:
                if key in existing_child:
                    rebuilt[key] = existing_child.get(key)

            rebuilt["meta"] = meta
            overrides = meta.get("lexicon_overrides", {})
            if isinstance(overrides, dict):
                rebuilt = apply_lexicon_overrides(rebuilt, overrides)

            rebuilt = project_io.normalize_language_snapshot(rebuilt)
            project_io.save_language(rebuilt, languages_dir / f"{child_id}.json")
            languages[child_id] = rebuilt
            _rebuild_node(child_id)

    _rebuild_node(root_language_id)


def _sanitize_language_id(raw_value: str) -> str:
    return project_io.sanitize_slug(raw_value)


def _collect_language_ids(project: Dict[str, Any]) -> Set[str]:
    language_ids: Set[str] = set()
    index = project.get("language_index", [])
    if isinstance(index, list):
        for item in index:
            if isinstance(item, dict):
                language_id = item.get("language_id")
                if language_id:
                    language_ids.add(str(language_id))
    root_id = project.get("root_language_id")
    if root_id:
        language_ids.add(str(root_id))
    return language_ids


def _next_available_language_id(project: Dict[str, Any], base_id: str) -> str:
    base = _sanitize_language_id(base_id) or "language"
    existing = _collect_language_ids(project)
    if base not in existing:
        return base
    counter = int(project.get("next_language_counter", 1))
    while True:
        candidate = f"{base}_{counter:02d}"
        counter += 1
        if candidate not in existing:
            project["next_language_counter"] = counter
            return candidate


def _apply_overrides(child: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(overrides, dict):
        return child
    for key in [
        "style_name",
        "concept_list_name",
        "concept_pack_config",
        "grammar_profile_name",
        "syllable_range",
        "syllable_separator",
        "phonotactic_profile_overrides",
    ]:
        if key in overrides:
            child[key] = overrides.get(key)
    return child


def preview_child_language(
    project_dir: Path,
    parent_language_id: str,
    child_name: str,
    child_id: str,
    changeset: Dict[str, Any],
    override_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    project = project_io.load_project(project_dir)
    languages_dir = Path(project.get("_project_dir", project_dir)) / project.get("paths", {}).get("languages_dir", "languages")
    parent_path = languages_dir / f"{parent_language_id}.json"
    parent_language = project_io.load_language(parent_path)
    parent_language = project_io.normalize_language_snapshot(parent_language)

    child_language = sound_change_engine.apply_changeset_to_language(parent_language, changeset)
    child_language = _apply_overrides(child_language, override_settings or {})
    meta_overrides = override_settings or {}
    year_value = meta_overrides.get("year")
    if year_value is None:
        parent_year = parent_language.get("meta", {}).get("year", 0)
        year_value = int(parent_year) + int(meta_overrides.get("year_offset", 100))

    child_language["meta"] = {
        "language_id": child_id,
        "name": child_name,
        "year": int(year_value),
        "parent_id": parent_language_id,
        "changeset_id": changeset.get("changeset_id") or f"chg_{parent_language_id}_{child_id}",
        "created_at": datetime.now().isoformat(),
        "notes": str(meta_overrides.get("notes", "")),
        "lexicon_overrides": dict(meta_overrides.get("lexicon_overrides", {})) if isinstance(meta_overrides.get("lexicon_overrides", {}), dict) else {},
    }
    overrides = child_language["meta"].get("lexicon_overrides", {})
    if isinstance(overrides, dict):
        child_language = apply_lexicon_overrides(child_language, overrides)
    return project_io.normalize_language_snapshot(child_language)


def create_child_language(
    project_dir: Path,
    parent_language_id: str,
    child_name: str,
    child_id: str,
    changeset: Dict[str, Any],
    override_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    project = project_io.load_project(project_dir)
    child_id_final = _next_available_language_id(project, child_id)
    child_preview = preview_child_language(
        project_dir=project_dir,
        parent_language_id=parent_language_id,
        child_name=child_name,
        child_id=child_id_final,
        changeset=changeset,
        override_settings=override_settings,
    )

    changeset_id = changeset.get("changeset_id") or f"chg_{parent_language_id}_{child_id_final}"
    changeset["changeset_id"] = changeset_id
    changeset["name"] = changeset.get("name") or f"{parent_language_id}→{child_id_final}"

    languages_dir = Path(project.get("_project_dir", project_dir)) / project.get("paths", {}).get("languages_dir", "languages")
    changesets_dir = Path(project.get("_project_dir", project_dir)) / project.get("paths", {}).get("changesets_dir", "changesets")
    project_io.save_changeset(changeset, changesets_dir / f"{changeset_id}.json")
    project_io.save_language(child_preview, languages_dir / f"{child_id_final}.json")

    _register_language(project, child_id_final)
    project_io.save_project(project)
    return child_preview
