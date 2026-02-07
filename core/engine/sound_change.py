from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional


def _enabled_rules(changeset: Dict[str, Any]) -> List[Dict[str, Any]]:
    rules = changeset.get("rules", [])
    if not isinstance(rules, list):
        return []
    enabled: List[Dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if rule.get("enabled", True) is False:
            continue
        enabled.append(rule)
    return enabled


def _apply_rules_to_segments(segments: Iterable[str], rules: List[Dict[str, Any]]) -> List[str]:
    updated: List[str] = []
    for segment in segments:
        new_segment = segment
        for rule in rules:
            frm = str(rule.get("from", ""))
            to = "" if rule.get("to") is None else str(rule.get("to", ""))
            if new_segment == frm:
                new_segment = to
        if new_segment:
            updated.append(new_segment)
    deduped = list(dict.fromkeys(updated))
    return deduped


def apply_changeset_to_inventory(inventory: Dict[str, Any], changeset: Dict[str, Any]) -> Dict[str, Any]:
    rules = _enabled_rules(changeset)
    vowels = inventory.get("vowels", [])
    consonants = inventory.get("consonants", [])
    if not isinstance(vowels, list):
        vowels = []
    if not isinstance(consonants, list):
        consonants = []
    new_inventory = dict(inventory)
    new_inventory["vowels"] = _apply_rules_to_segments(vowels, rules)
    new_inventory["consonants"] = _apply_rules_to_segments(consonants, rules)
    return new_inventory


def tokenize_form(form: str, segments: List[str], syllable_separator: str) -> List[str]:
    if not form:
        return []
    tokens: List[str] = []
    ordered_segments = sorted(set(segments), key=len, reverse=True)
    index = 0
    sep = syllable_separator or ""
    while index < len(form):
        if sep and form.startswith(sep, index):
            tokens.append(sep)
            index += len(sep)
            continue

        matched = False
        for segment in ordered_segments:
            if segment and form.startswith(segment, index):
                tokens.append(segment)
                index += len(segment)
                matched = True
                break
        if not matched:
            tokens.append(form[index])
            index += 1
    return tokens


def _apply_rules_to_tokens(tokens: List[str], rules: List[Dict[str, Any]], syllable_separator: str) -> List[str]:
    sep = syllable_separator or ""
    updated: List[str] = []
    for token in tokens:
        if sep and token == sep:
            updated.append(token)
            continue
        new_token = token
        for rule in rules:
            frm = str(rule.get("from", ""))
            to = "" if rule.get("to") is None else str(rule.get("to", ""))
            if new_token == frm:
                new_token = to
        if new_token:
            updated.append(new_token)
    return updated


def _cleanup_separators(tokens: List[str], syllable_separator: str) -> List[str]:
    sep = syllable_separator or ""
    if not sep:
        return tokens
    cleaned: List[str] = []
    for token in tokens:
        if token == sep:
            if not cleaned or cleaned[-1] == sep:
                continue
        cleaned.append(token)
    if cleaned and cleaned[-1] == sep:
        cleaned.pop()
    if cleaned and cleaned[0] == sep:
        cleaned = cleaned[1:]
    return cleaned


def apply_changeset_to_form(
    form: str,
    inventory: Dict[str, Any],
    changeset: Dict[str, Any],
    syllable_separator: str,
) -> str:
    vowels = inventory.get("vowels", [])
    consonants = inventory.get("consonants", [])
    if not isinstance(vowels, list):
        vowels = []
    if not isinstance(consonants, list):
        consonants = []
    segments = list(dict.fromkeys([str(seg) for seg in vowels + consonants if str(seg)]))
    tokens = tokenize_form(str(form), segments, syllable_separator)
    rules = _enabled_rules(changeset)
    updated_tokens = _apply_rules_to_tokens(tokens, rules, syllable_separator)
    cleaned_tokens = _cleanup_separators(updated_tokens, syllable_separator)
    return "".join(cleaned_tokens)


def apply_changeset_to_language(language: Dict[str, Any], changeset: Dict[str, Any]) -> Dict[str, Any]:
    new_language = deepcopy(language)
    inventory = language.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
    new_inventory = apply_changeset_to_inventory(inventory, changeset)
    new_language["inventory"] = new_inventory

    lexicon = new_language.get("lexicon", [])
    if not isinstance(lexicon, list):
        return new_language

    syllable_separator = str(new_language.get("syllable_separator", ""))
    for entry in lexicon:
        if not isinstance(entry, dict):
            continue
        ipa = entry.get("ipa", "")
        entry["ipa"] = apply_changeset_to_form(str(ipa), inventory, changeset, syllable_separator)
    return new_language


def report_lexicon_collisions(language: Dict[str, Any]) -> Dict[str, List[str]]:
    lexicon = language.get("lexicon", [])
    if not isinstance(lexicon, list):
        return {}
    collisions: Dict[str, List[str]] = {}
    for entry in lexicon:
        if not isinstance(entry, dict):
            continue
        ipa = str(entry.get("ipa", "")).strip()
        entry_id = str(entry.get("id", "")).strip()
        if not ipa or not entry_id:
            continue
        collisions.setdefault(ipa, []).append(entry_id)
    return {ipa: ids for ipa, ids in collisions.items() if len(ids) > 1}


def diff_inventory(parent: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, List[str]]:
    parent_vowels = parent.get("vowels", []) if isinstance(parent, dict) else []
    parent_consonants = parent.get("consonants", []) if isinstance(parent, dict) else []
    child_vowels = child.get("vowels", []) if isinstance(child, dict) else []
    child_consonants = child.get("consonants", []) if isinstance(child, dict) else []

    parent_vowels_set = set(parent_vowels) if isinstance(parent_vowels, list) else set()
    parent_consonants_set = set(parent_consonants) if isinstance(parent_consonants, list) else set()
    child_vowels_set = set(child_vowels) if isinstance(child_vowels, list) else set()
    child_consonants_set = set(child_consonants) if isinstance(child_consonants, list) else set()

    return {
        "added_vowels": sorted(child_vowels_set - parent_vowels_set),
        "removed_vowels": sorted(parent_vowels_set - child_vowels_set),
        "added_consonants": sorted(child_consonants_set - parent_consonants_set),
        "removed_consonants": sorted(parent_consonants_set - child_consonants_set),
    }
