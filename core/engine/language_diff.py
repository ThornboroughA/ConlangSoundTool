from __future__ import annotations

from typing import Any, Dict, List, Tuple

from . import sound_change as sound_change_engine


def summarize_rule_effects(parent_inventory: Dict[str, Any], changeset: Dict[str, Any]) -> Dict[str, Any]:
    """Return a summary of rule impacts on inventory."""
    parent = parent_inventory if isinstance(parent_inventory, dict) else {}
    child = sound_change_engine.apply_changeset_to_inventory(parent, changeset)
    diff = sound_change_engine.diff_inventory(parent, child)
    enabled_rules = [
        rule for rule in changeset.get("rules", []) if isinstance(rule, dict) and rule.get("enabled", True)
    ]
    return {
        "rule_count": len(enabled_rules),
        "diff": diff,
    }


def sample_lexicon_diff(
    parent_language: Dict[str, Any],
    child_language: Dict[str, Any],
    n: int = 20,
) -> List[Dict[str, str]]:
    parent_lexicon = parent_language.get("lexicon", [])
    child_lexicon = child_language.get("lexicon", [])
    if not isinstance(parent_lexicon, list) or not isinstance(child_lexicon, list):
        return []

    parent_map = {
        str(entry.get("id", "")): str(entry.get("ipa", ""))
        for entry in parent_lexicon
        if isinstance(entry, dict)
    }
    rows: List[Dict[str, str]] = []
    for entry in child_lexicon:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", ""))
        if not entry_id:
            continue
        rows.append(
            {
                "id": entry_id,
                "parent_ipa": parent_map.get(entry_id, ""),
                "child_ipa": str(entry.get("ipa", "")),
                "meaning": str(entry.get("meaning", "")),
            }
        )
        if len(rows) >= n:
            break
    return rows
