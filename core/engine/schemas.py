from __future__ import annotations

from typing import Dict, List, Optional, TypedDict, Any


class LanguageMeta(TypedDict, total=False):
    language_id: str
    name: str
    year: int
    parent_id: Optional[str]
    changeset_id: Optional[str]
    created_at: str
    notes: str
    lexicon_overrides: Dict[str, str]


class Inventory(TypedDict, total=False):
    vowels: List[str]
    consonants: List[str]


class LexiconEntry(TypedDict, total=False):
    id: str
    ipa: str
    meaning: str
    gloss: str
    pos: str
    source: str


class LanguageSnapshot(TypedDict, total=False):
    schema_version: int
    meta: LanguageMeta
    style_name: str
    concept_list_name: str
    grammar_profile_name: str
    syllable_range: List[int]
    syllable_separator: str
    phonotactic_profile_overrides: Dict[str, Any]
    inventory: Inventory
    lexicon: List[LexiconEntry]


class ChangesetRule(TypedDict, total=False):
    from_: str
    to: str
    enabled: bool
    notes: str


class Changeset(TypedDict, total=False):
    schema_version: int
    changeset_id: str
    name: str
    description: str
    rules: List[Dict[str, Any]]


class ProjectPaths(TypedDict, total=False):
    languages_dir: str
    changesets_dir: str


class Project(TypedDict, total=False):
    schema_version: int
    project_name: str
    project_slug: str
    created_at: str
    last_modified_at: str
    seed: int
    time_span_years: int
    extant_year: int
    root_language_id: str
    next_language_counter: int
    paths: ProjectPaths
    family_config: Dict[str, Any]
    language_index: List[Dict[str, str]]
