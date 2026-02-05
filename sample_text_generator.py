"""Word and sentence sample generation utilities.

This module keeps semantics intentionally lightweight: concept tags help produce
more coherent forms and clauses without turning this project into a full
meaning generator.
"""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

STYLE_PRESETS: Dict[str, Dict[str, object]] = {
    "Balanced": {
        "description": "Neutral blend of short and medium words.",
        "syllable_shapes": [("V", 0.10), ("CV", 0.40), ("VC", 0.12), ("CVC", 0.23), ("CVV", 0.08), ("VCV", 0.07)],
    },
    "Clipped": {
        "description": "Short, punchy cadence with tighter consonant-heavy chunks.",
        "syllable_shapes": [("CV", 0.35), ("CVC", 0.38), ("VC", 0.15), ("V", 0.05), ("CVV", 0.04), ("VCV", 0.03)],
    },
    "Flowing": {
        "description": "Smoother rhythm with more open syllables and vowel sequences.",
        "syllable_shapes": [("V", 0.16), ("CV", 0.44), ("VC", 0.06), ("CVC", 0.10), ("CVV", 0.16), ("VCV", 0.08)],
    },
    "Dense": {
        "description": "Denser consonant clusters and heavier codas.",
        "syllable_shapes": [("CV", 0.24), ("CVC", 0.34), ("CCV", 0.12), ("CVCC", 0.14), ("VC", 0.10), ("V", 0.06)],
    },
}
DEFAULT_STYLE_PRESET = "Balanced"

LEIPZIG_JAKARTA_100: Tuple[str, ...] = (
    "fire",
    "nose",
    "to go",
    "water",
    "mouth",
    "tongue",
    "blood",
    "bone",
    "2nd-person singular pronoun (you)",
    "root",
    "to come",
    "breast",
    "name",
    "louse",
    "to drink",
    "bird",
    "to die",
    "ear",
    "to give",
    "to see",
    "to hear",
    "egg",
    "horn",
    "tail",
    "dog",
    "fish",
    "to know",
    "to bite",
    "because",
    "to have",
    "one",
    "who?",
    "what?",
    "this",
    "to swim",
    "to fly",
    "to walk",
    "to lie (as in a bed)",
    "to sit",
    "to stand",
    "to kill",
    "to sleep",
    "to hit / beat",
    "to say",
    "sun",
    "moon",
    "star",
    "wind",
    "stone / rock",
    "to pour",
    "to break",
    "to burn",
    "path / road",
    "mountain",
    "red",
    "green",
    "yellow",
    "white",
    "black",
    "night",
    "hot",
    "cold",
    "full",
    "new",
    "good",
    "round",
    "dry",
    "name",
    "to hear",
    "to know",
    "to die",
    "to kill",
    "water",
    "rain",
    "stone",
    "sun",
    "moon",
    "root",
    "bark",
    "skin",
    "louse",
    "leaf",
    "tree",
    "to walk",
    "to run",
    "to sit",
    "to stand",
    "to lie",
    "to sleep",
    "to dream",
    "to wake up",
    "to blow",
    "to suck",
    "to sew",
    "to spin",
    "to weave",
    "to tie",
    "to turn",
    "to count",
    "to ask",
)

CORE_STARTER_CONCEPTS: Tuple[Dict[str, str], ...] = (
    {"meaning": "person", "pos": "N"},
    {"meaning": "child", "pos": "N"},
    {"meaning": "water", "pos": "N"},
    {"meaning": "fire", "pos": "N"},
    {"meaning": "stone", "pos": "N"},
    {"meaning": "tree", "pos": "N"},
    {"meaning": "sun", "pos": "N"},
    {"meaning": "moon", "pos": "N"},
    {"meaning": "house", "pos": "N"},
    {"meaning": "path", "pos": "N"},
    {"meaning": "go", "pos": "V"},
    {"meaning": "come", "pos": "V"},
    {"meaning": "see", "pos": "V"},
    {"meaning": "hear", "pos": "V"},
    {"meaning": "eat", "pos": "V"},
    {"meaning": "drink", "pos": "V"},
    {"meaning": "give", "pos": "V"},
    {"meaning": "take", "pos": "V"},
    {"meaning": "sleep", "pos": "V"},
    {"meaning": "speak", "pos": "V"},
    {"meaning": "know", "pos": "V"},
    {"meaning": "make", "pos": "V"},
    {"meaning": "big", "pos": "ADJ"},
    {"meaning": "small", "pos": "ADJ"},
    {"meaning": "good", "pos": "ADJ"},
    {"meaning": "bad", "pos": "ADJ"},
    {"meaning": "new", "pos": "ADJ"},
    {"meaning": "old", "pos": "ADJ"},
)

CONCEPT_LIST_PRESETS: Dict[str, Dict[str, object]] = {
    "Leipzig-Jakarta 100": {
        "description": "Cross-linguistically stable 100-concept core list for root generation.",
        "entries": LEIPZIG_JAKARTA_100,
    },
    "Core Starter": {
        "description": "Smaller starter list for quicker iterations and debugging.",
        "entries": CORE_STARTER_CONCEPTS,
    },
}
DEFAULT_CONCEPT_LIST = "Leipzig-Jakarta 100"

PARTICLE_DEFINITIONS: Dict[str, str] = {
    "TOP": "topic",
    "ACC": "object",
    "DAT": "recipient",
    "LOC": "location",
    "GEN": "genitive",
    "TAM": "tense-aspect",
    "Q": "question",
}

GRAMMAR_PROFILES: Dict[str, Dict[str, object]] = {
    "Flexible Core": {
        "description": "Mixed SOV/SVO with optional particles and moderate adjuncts.",
        "clause_templates": [("SV", 0.26), ("SOV", 0.44), ("SVO", 0.30)],
        "sample_word_pos": [("N", 0.42), ("V", 0.30), ("ADJ", 0.18), ("PRON", 0.05), ("PART", 0.05)],
        "subject_pronoun_rate": 0.28,
        "object_pronoun_rate": 0.16,
        "subject_particle_rate": 0.30,
        "object_particle_rate": 0.62,
        "tam_particle_rate": 0.24,
        "adjunct_rate": 0.28,
        "modifier_rate": 0.30,
        "modifier_positions": [("pre", 0.65), ("post", 0.35)],
        "filler_pos": [("ADJ", 0.42), ("N", 0.28), ("V", 0.20), ("PART", 0.10)],
        "particle_inventory": ["TOP", "ACC", "DAT", "LOC", "GEN", "TAM", "Q"],
        "particle_syllables": (1, 1),
        "punctuation": [(".", 0.75), ("?", 0.15), ("!", 0.10)],
    },
    "SOV Marking": {
        "description": "Head-final bias with stronger case-like particle usage.",
        "clause_templates": [("SV", 0.16), ("SOV", 0.72), ("SVO", 0.12)],
        "sample_word_pos": [("N", 0.38), ("V", 0.28), ("ADJ", 0.15), ("PRON", 0.04), ("PART", 0.15)],
        "subject_pronoun_rate": 0.20,
        "object_pronoun_rate": 0.10,
        "subject_particle_rate": 0.54,
        "object_particle_rate": 0.90,
        "tam_particle_rate": 0.36,
        "adjunct_rate": 0.42,
        "modifier_rate": 0.38,
        "modifier_positions": [("pre", 0.74), ("post", 0.26)],
        "filler_pos": [("N", 0.36), ("PART", 0.26), ("ADJ", 0.22), ("V", 0.16)],
        "particle_inventory": ["TOP", "ACC", "DAT", "LOC", "GEN", "TAM", "Q"],
        "particle_syllables": (1, 2),
        "punctuation": [(".", 0.78), ("?", 0.14), ("!", 0.08)],
    },
    "Analytic SVO": {
        "description": "SVO bias with lighter particles and stricter word order.",
        "clause_templates": [("SV", 0.34), ("SOV", 0.12), ("SVO", 0.54)],
        "sample_word_pos": [("N", 0.40), ("V", 0.34), ("ADJ", 0.18), ("PRON", 0.06), ("PART", 0.02)],
        "subject_pronoun_rate": 0.36,
        "object_pronoun_rate": 0.26,
        "subject_particle_rate": 0.08,
        "object_particle_rate": 0.14,
        "tam_particle_rate": 0.10,
        "adjunct_rate": 0.18,
        "modifier_rate": 0.24,
        "modifier_positions": [("pre", 0.76), ("post", 0.24)],
        "filler_pos": [("ADJ", 0.45), ("N", 0.24), ("V", 0.24), ("PART", 0.07)],
        "particle_inventory": ["LOC", "GEN", "Q"],
        "particle_syllables": (1, 1),
        "punctuation": [(".", 0.70), ("?", 0.20), ("!", 0.10)],
    },
    "Topic-Prominent": {
        "description": "Frequent topic marking with SOV preference and high particle density.",
        "clause_templates": [("SV", 0.18), ("SOV", 0.62), ("SVO", 0.20)],
        "sample_word_pos": [("N", 0.34), ("V", 0.24), ("ADJ", 0.16), ("PRON", 0.04), ("PART", 0.22)],
        "subject_pronoun_rate": 0.22,
        "object_pronoun_rate": 0.08,
        "subject_particle_rate": 0.82,
        "object_particle_rate": 0.82,
        "tam_particle_rate": 0.46,
        "adjunct_rate": 0.46,
        "modifier_rate": 0.32,
        "modifier_positions": [("pre", 0.62), ("post", 0.38)],
        "filler_pos": [("PART", 0.32), ("N", 0.28), ("ADJ", 0.24), ("V", 0.16)],
        "particle_inventory": ["TOP", "ACC", "DAT", "LOC", "GEN", "TAM", "Q"],
        "particle_syllables": (1, 2),
        "punctuation": [(".", 0.72), ("?", 0.18), ("!", 0.10)],
    },
}
DEFAULT_GRAMMAR_PROFILE = "Flexible Core"

CLAUSE_SLOTS: Dict[str, Tuple[str, ...]] = {
    "SV": ("S", "V"),
    "SOV": ("S", "O", "V"),
    "SVO": ("S", "V", "O"),
}

POS_LABELS: Dict[str, str] = {
    "N": "Noun",
    "V": "Verb",
    "ADJ": "Modifier",
    "PART": "Particle",
    "PRON": "Pronoun",
    "NUM": "Numeral",
    "DEM": "Demonstrative",
    "ADV": "Adverb",
    "ADP": "Adposition",
    "NEG": "Negator",
    "CONJ": "Conjunction",
    "INT": "Interrogative",
}

ADJECTIVE_CONCEPTS: Set[str] = {
    "far",
    "bitter",
    "big",
    "black",
    "new",
    "good",
    "heavy",
    "old",
    "thick",
    "long",
    "red",
    "sweet",
    "small",
    "wide",
    "hard",
    "green",
    "yellow",
    "white",
    "hot",
    "cold",
    "full",
    "round",
    "dry",
}

SPECIAL_CONCEPT_TAGS: Dict[str, Tuple[str, str]] = {
    "2nd-person singular pronoun (you)": ("PRON", "2SG"),
    "1st-person singular pronoun (I/me)": ("PRON", "1SG"),
    "3rd-person singular pronoun (he/she/it/him/her)": ("PRON", "3SG"),
    "who?": ("INT", "WHO"),
    "what?": ("INT", "WHAT"),
    "this": ("DEM", "THIS"),
    "one": ("NUM", "ONE"),
    "in": ("ADP", "IN"),
    "not": ("NEG", "NEG"),
    "because": ("CONJ", "BECAUSE"),
    "yesterday": ("ADV", "YESTERDAY"),
}


def weighted_choice(weighted_items: Sequence[Tuple[str, float]], fallback: str) -> str:
    valid = [(label, weight) for label, weight in weighted_items if float(weight) > 0]
    if not valid:
        return fallback
    labels = [label for label, _ in valid]
    weights = [weight for _, weight in valid]
    return random.choices(labels, weights=weights, k=1)[0]


def style_profile(style_name: str) -> Dict[str, object]:
    return STYLE_PRESETS.get(style_name, STYLE_PRESETS[DEFAULT_STYLE_PRESET])


def concept_list_profile(concept_list_name: str) -> Dict[str, object]:
    return CONCEPT_LIST_PRESETS.get(concept_list_name, CONCEPT_LIST_PRESETS[DEFAULT_CONCEPT_LIST])


def grammar_profile(grammar_profile_name: str) -> Dict[str, object]:
    return GRAMMAR_PROFILES.get(grammar_profile_name, GRAMMAR_PROFILES[DEFAULT_GRAMMAR_PROFILE])


def _as_float(value: object) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _validate_weighted_pairs(
    report: Dict[str, List[str]],
    owner: str,
    field_name: str,
    value: object,
    allowed_labels: Optional[Set[str]] = None,
    label_pattern: Optional[str] = None,
) -> None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        report["errors"].append(f"{owner}.{field_name} must be a weighted list of (label, weight) pairs.")
        return

    positive_weights = 0
    for index, item in enumerate(value):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            report["errors"].append(f"{owner}.{field_name}[{index}] must be a (label, weight) pair.")
            continue

        raw_label, raw_weight = item
        label = str(raw_label)
        weight = _as_float(raw_weight)
        if weight is None:
            report["errors"].append(f"{owner}.{field_name}[{index}] has a non-numeric weight.")
        elif weight < 0:
            report["errors"].append(f"{owner}.{field_name}[{index}] has a negative weight.")
        elif weight > 0:
            positive_weights += 1

        if allowed_labels is not None and label not in allowed_labels:
            report["errors"].append(
                f"{owner}.{field_name}[{index}] references unknown label '{label}'."
            )

        if label_pattern is not None and not re.fullmatch(label_pattern, label):
            report["errors"].append(
                f"{owner}.{field_name}[{index}] label '{label}' does not match expected pattern."
            )

    if positive_weights == 0:
        report["errors"].append(f"{owner}.{field_name} must include at least one positive weight.")


def _validate_probability_field(
    report: Dict[str, List[str]],
    owner: str,
    field_name: str,
    value: object,
) -> None:
    number = _as_float(value)
    if number is None:
        report["errors"].append(f"{owner}.{field_name} must be numeric.")
        return
    if number < 0 or number > 1:
        report["errors"].append(f"{owner}.{field_name} must be between 0 and 1.")


def _validate_range_field(
    report: Dict[str, List[str]],
    owner: str,
    field_name: str,
    value: object,
) -> None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        report["errors"].append(f"{owner}.{field_name} must be a (min, max) pair.")
        return
    low = _as_float(value[0])
    high = _as_float(value[1])
    if low is None or high is None:
        report["errors"].append(f"{owner}.{field_name} must contain numeric values.")
        return
    if low < 1 or high < 1:
        report["errors"].append(f"{owner}.{field_name} must be >= 1.")
        return
    if int(high) < int(low):
        report["errors"].append(f"{owner}.{field_name} max must be >= min.")


def validate_generation_config() -> Dict[str, List[str]]:
    """Validate configurable concept/style/grammar presets used by sample generation."""
    report: Dict[str, List[str]] = {"errors": [], "warnings": []}

    if DEFAULT_STYLE_PRESET not in STYLE_PRESETS:
        report["errors"].append(f"DEFAULT_STYLE_PRESET '{DEFAULT_STYLE_PRESET}' is missing.")
    if DEFAULT_CONCEPT_LIST not in CONCEPT_LIST_PRESETS:
        report["errors"].append(f"DEFAULT_CONCEPT_LIST '{DEFAULT_CONCEPT_LIST}' is missing.")
    if DEFAULT_GRAMMAR_PROFILE not in GRAMMAR_PROFILES:
        report["errors"].append(f"DEFAULT_GRAMMAR_PROFILE '{DEFAULT_GRAMMAR_PROFILE}' is missing.")

    if not STYLE_PRESETS:
        report["errors"].append("STYLE_PRESETS is empty.")
    for name, profile in STYLE_PRESETS.items():
        owner = f"STYLE_PRESETS[{name}]"
        if not isinstance(profile.get("description"), str) or not str(profile.get("description", "")).strip():
            report["errors"].append(f"{owner}.description must be a non-empty string.")
        _validate_weighted_pairs(
            report,
            owner=owner,
            field_name="syllable_shapes",
            value=profile.get("syllable_shapes"),
            label_pattern=r"[CV]+",
        )

    if not CONCEPT_LIST_PRESETS:
        report["errors"].append("CONCEPT_LIST_PRESETS is empty.")
    for name, profile in CONCEPT_LIST_PRESETS.items():
        owner = f"CONCEPT_LIST_PRESETS[{name}]"
        if not isinstance(profile.get("description"), str) or not str(profile.get("description", "")).strip():
            report["errors"].append(f"{owner}.description must be a non-empty string.")

        entries = profile.get("entries")
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
            report["errors"].append(f"{owner}.entries must be a sequence.")
            continue
        if len(entries) == 0:
            report["errors"].append(f"{owner}.entries must not be empty.")
            continue

        seen_meanings: Set[str] = set()
        duplicate_meanings: Set[str] = set()
        for idx, entry in enumerate(entries):
            if isinstance(entry, str):
                meaning = _normalize_meaning(entry)
                if not meaning:
                    report["errors"].append(f"{owner}.entries[{idx}] is blank.")
                    continue
                normalized_meaning = meaning.lower()
                if normalized_meaning in seen_meanings:
                    duplicate_meanings.add(meaning)
                seen_meanings.add(normalized_meaning)
                continue

            if not isinstance(entry, dict):
                report["errors"].append(
                    f"{owner}.entries[{idx}] must be either a string meaning or a dict definition."
                )
                continue

            meaning = _normalize_meaning(str(entry.get("meaning", "")))
            if not meaning:
                report["errors"].append(f"{owner}.entries[{idx}].meaning is required.")
                continue

            pos = _normalize_meaning(str(entry.get("pos", "")).upper())
            if pos and pos not in POS_LABELS:
                report["errors"].append(
                    f"{owner}.entries[{idx}].pos '{pos}' is not in POS_LABELS."
                )

            normalized_meaning = meaning.lower()
            if normalized_meaning in seen_meanings:
                duplicate_meanings.add(meaning)
            seen_meanings.add(normalized_meaning)

        if duplicate_meanings and name != "Leipzig-Jakarta 100":
            duplicate_preview = ", ".join(sorted(duplicate_meanings)[:5])
            report["warnings"].append(
                f"{owner}.entries contains duplicate meanings (showing up to 5): {duplicate_preview}"
            )

    lj_profile = CONCEPT_LIST_PRESETS.get("Leipzig-Jakarta 100", {})
    lj_entries = lj_profile.get("entries", ())
    if isinstance(lj_entries, Sequence) and not isinstance(lj_entries, (str, bytes)):
        if len(lj_entries) != 100:
            report["warnings"].append(
                "CONCEPT_LIST_PRESETS['Leipzig-Jakarta 100'] does not currently contain exactly 100 entries."
            )

    if not GRAMMAR_PROFILES:
        report["errors"].append("GRAMMAR_PROFILES is empty.")
    for name, profile in GRAMMAR_PROFILES.items():
        owner = f"GRAMMAR_PROFILES[{name}]"
        if not isinstance(profile.get("description"), str) or not str(profile.get("description", "")).strip():
            report["errors"].append(f"{owner}.description must be a non-empty string.")

        _validate_weighted_pairs(
            report,
            owner=owner,
            field_name="clause_templates",
            value=profile.get("clause_templates"),
            allowed_labels=set(CLAUSE_SLOTS.keys()),
        )
        _validate_weighted_pairs(
            report,
            owner=owner,
            field_name="sample_word_pos",
            value=profile.get("sample_word_pos"),
            allowed_labels=set(POS_LABELS.keys()),
        )
        _validate_weighted_pairs(
            report,
            owner=owner,
            field_name="filler_pos",
            value=profile.get("filler_pos"),
            allowed_labels=set(POS_LABELS.keys()),
        )
        _validate_weighted_pairs(
            report,
            owner=owner,
            field_name="modifier_positions",
            value=profile.get("modifier_positions"),
            allowed_labels={"pre", "post"},
        )
        _validate_weighted_pairs(
            report,
            owner=owner,
            field_name="punctuation",
            value=profile.get("punctuation"),
        )

        for rate_key in (
            "subject_pronoun_rate",
            "object_pronoun_rate",
            "subject_particle_rate",
            "object_particle_rate",
            "tam_particle_rate",
            "adjunct_rate",
            "modifier_rate",
        ):
            _validate_probability_field(
                report,
                owner=owner,
                field_name=rate_key,
                value=profile.get(rate_key),
            )

        _validate_range_field(
            report,
            owner=owner,
            field_name="particle_syllables",
            value=profile.get("particle_syllables"),
        )

        particle_inventory = profile.get("particle_inventory")
        if not isinstance(particle_inventory, Sequence) or isinstance(particle_inventory, (str, bytes)):
            report["errors"].append(f"{owner}.particle_inventory must be a sequence.")
        else:
            for idx, particle in enumerate(particle_inventory):
                particle_name = str(particle).upper()
                if particle_name not in PARTICLE_DEFINITIONS:
                    report["errors"].append(
                        f"{owner}.particle_inventory[{idx}] references unknown particle '{particle_name}'."
                    )

    return report


def language_model_summary(language_model: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """Return compact counts used for UI status display."""
    if not isinstance(language_model, dict):
        return {"total_entries": 0, "root_entries": 0, "particle_entries": 0}

    lexicon = language_model.get("lexicon", [])
    if not isinstance(lexicon, list):
        lexicon = []
    particles = language_model.get("particles", {})
    if not isinstance(particles, dict):
        particles = {}

    root_entries = 0
    for entry in lexicon:
        if isinstance(entry, dict) and str(entry.get("source", "")).startswith("concept-list:"):
            root_entries += 1

    return {
        "total_entries": len(lexicon),
        "root_entries": root_entries,
        "particle_entries": len(particles),
    }


def normalize_range(values: Tuple[int, int], minimum: int = 1) -> Tuple[int, int]:
    min_value, max_value = values
    min_value = max(minimum, int(min_value))
    max_value = max(min_value, int(max_value))
    return min_value, max_value


def choose_segment(segments: Sequence[str]) -> str:
    if not segments:
        return ""
    return random.choice(list(segments))


def _normalize_meaning(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def infer_pos_for_concept(meaning: str) -> str:
    normalized = _normalize_meaning(meaning)
    if normalized in SPECIAL_CONCEPT_TAGS:
        return SPECIAL_CONCEPT_TAGS[normalized][0]
    if normalized.lower().startswith("to "):
        return "V"
    if normalized.lower() in ADJECTIVE_CONCEPTS:
        return "ADJ"
    return "N"


def concept_gloss(meaning: str, pos: str) -> str:
    normalized = _normalize_meaning(meaning)
    special = SPECIAL_CONCEPT_TAGS.get(normalized)
    if special and special[1]:
        return special[1]

    base = re.sub(r"\s*\([^)]*\)", "", normalized)
    base = base.replace("?", "")
    tokens = re.findall(r"[a-z0-9]+", base.lower())
    if pos == "V" and tokens and tokens[0] == "to":
        tokens = tokens[1:]
    if not tokens:
        return "ITEM"
    return "_".join(tokens[:3]).upper()


def resolve_concept_entries(concept_list_name: str) -> List[Dict[str, str]]:
    profile = concept_list_profile(concept_list_name)
    raw_entries = profile.get("entries", ())
    entries: List[Dict[str, str]] = []

    if not isinstance(raw_entries, Sequence):
        raw_entries = ()

    for raw_entry in raw_entries:
        if isinstance(raw_entry, str):
            meaning = _normalize_meaning(raw_entry)
            if not meaning:
                continue
            pos = infer_pos_for_concept(meaning)
            entries.append({"meaning": meaning, "pos": pos, "gloss": concept_gloss(meaning, pos)})
            continue

        if isinstance(raw_entry, dict):
            meaning = _normalize_meaning(str(raw_entry.get("meaning", "")))
            if not meaning:
                continue
            pos = _normalize_meaning(str(raw_entry.get("pos", "")).upper()) or infer_pos_for_concept(meaning)
            gloss = _normalize_meaning(str(raw_entry.get("gloss", "")).upper()) or concept_gloss(meaning, pos)
            entries.append({"meaning": meaning, "pos": pos, "gloss": gloss})

    if entries:
        return entries
    if concept_list_name == DEFAULT_CONCEPT_LIST:
        return []
    return resolve_concept_entries(DEFAULT_CONCEPT_LIST)


def generate_syllable(vowels: Sequence[str], consonants: Sequence[str], style_name: str) -> str:
    vowels_list = list(vowels)
    consonants_list = list(consonants)

    if not vowels_list and not consonants_list:
        return ""

    if not consonants_list:
        shape = weighted_choice([("V", 0.75), ("VV", 0.25)], fallback="V")
    elif not vowels_list:
        shape = weighted_choice([("C", 0.85), ("CC", 0.15)], fallback="C")
    else:
        profile = style_profile(style_name)
        shape_weights = profile.get("syllable_shapes", STYLE_PRESETS[DEFAULT_STYLE_PRESET]["syllable_shapes"])
        shape = weighted_choice(shape_weights, fallback="CV")

    parts: List[str] = []
    for slot in shape:
        segment = choose_segment(consonants_list) if slot == "C" else choose_segment(vowels_list)
        if segment:
            parts.append(segment)
    return "".join(parts)


def generate_word(
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
) -> str:
    min_syllables, max_syllables = normalize_range(syllable_range, minimum=1)
    syllable_count = random.randint(min_syllables, max_syllables)
    syllables = [generate_syllable(vowels, consonants, style_name=style_name) for _ in range(syllable_count)]
    syllables = [syllable for syllable in syllables if syllable]

    if not syllables:
        return choose_segment(vowels) or choose_segment(consonants) or "a"
    return syllable_separator.join(syllables)


def _looks_noisy(form: str) -> bool:
    if not form:
        return True
    return bool(re.search(r"(.)\1\1", form))


def _generate_unique_word(
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    used_forms: Set[str],
) -> str:
    for _ in range(40):
        candidate = generate_word(
            vowels=vowels,
            consonants=consonants,
            syllable_range=syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
        )
        if candidate in used_forms or _looks_noisy(candidate):
            continue
        used_forms.add(candidate)
        return candidate

    fallback = generate_word(
        vowels=vowels,
        consonants=consonants,
        syllable_range=syllable_range,
        syllable_separator=syllable_separator,
        style_name=style_name,
    )
    if fallback in used_forms and (vowels or consonants):
        extra = choose_segment(consonants) or choose_segment(vowels) or "a"
        fallback = f"{fallback}{syllable_separator}{extra}" if syllable_separator else f"{fallback}{extra}"
    used_forms.add(fallback)
    return fallback


def _new_entry(entry_id: str, ipa: str, meaning: str, gloss: str, pos: str, source: str) -> Dict[str, str]:
    return {
        "id": entry_id,
        "ipa": ipa,
        "meaning": meaning,
        "gloss": gloss,
        "pos": pos,
        "source": source,
    }


def build_language_model(
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    concept_list_name: str = DEFAULT_CONCEPT_LIST,
    grammar_profile_name: str = DEFAULT_GRAMMAR_PROFILE,
) -> Dict[str, Any]:
    root_syllable_range = normalize_range(syllable_range, minimum=1)
    grammar = grammar_profile(grammar_profile_name)
    particle_syllables = normalize_range(tuple(grammar.get("particle_syllables", (1, 1))), minimum=1)

    concept_entries = resolve_concept_entries(concept_list_name)
    used_forms: Set[str] = set()
    lexicon: List[Dict[str, str]] = []
    by_pos: Dict[str, List[Dict[str, str]]] = {}
    particles: Dict[str, Dict[str, str]] = {}

    for index, concept in enumerate(concept_entries, start=1):
        meaning = concept["meaning"]
        pos = concept["pos"]
        gloss = concept["gloss"]
        ipa = _generate_unique_word(
            vowels=vowels,
            consonants=consonants,
            syllable_range=root_syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
            used_forms=used_forms,
        )
        entry = _new_entry(
            entry_id=f"ROOT:{index:03d}",
            ipa=ipa,
            meaning=meaning,
            gloss=gloss,
            pos=pos,
            source=f"concept-list:{concept_list_name}",
        )
        lexicon.append(entry)
        by_pos.setdefault(pos, []).append(entry)

    particle_inventory = [str(name).upper() for name in grammar.get("particle_inventory", [])]
    for particle_name in particle_inventory:
        ipa = _generate_unique_word(
            vowels=vowels,
            consonants=consonants,
            syllable_range=particle_syllables,
            syllable_separator=syllable_separator,
            style_name=style_name,
            used_forms=used_forms,
        )
        meaning = PARTICLE_DEFINITIONS.get(particle_name, particle_name.lower())
        entry = _new_entry(
            entry_id=f"PART:{particle_name}",
            ipa=ipa,
            meaning=meaning,
            gloss=particle_name,
            pos="PART",
            source=f"grammar:{grammar_profile_name}",
        )
        lexicon.append(entry)
        by_pos.setdefault("PART", []).append(entry)
        particles[particle_name] = entry

    return {
        "style_name": style_name,
        "concept_list_name": concept_list_name,
        "grammar_profile_name": grammar_profile_name,
        "syllable_range": [root_syllable_range[0], root_syllable_range[1]],
        "syllable_separator": syllable_separator,
        "inventory": {
            "vowels": list(vowels),
            "consonants": list(consonants),
        },
        "lexicon": lexicon,
        "by_pos": by_pos,
        "particles": particles,
    }


def model_matches(
    language_model: Optional[Dict[str, Any]],
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    concept_list_name: str = DEFAULT_CONCEPT_LIST,
    grammar_profile_name: str = DEFAULT_GRAMMAR_PROFILE,
) -> bool:
    if not isinstance(language_model, dict):
        return False
    expected_min, expected_max = normalize_range(syllable_range, minimum=1)
    inventory = language_model.get("inventory", {})
    if not isinstance(inventory, dict):
        return False

    return (
        language_model.get("style_name") == style_name
        and language_model.get("concept_list_name") == concept_list_name
        and language_model.get("grammar_profile_name") == grammar_profile_name
        and language_model.get("syllable_separator") == syllable_separator
        and language_model.get("syllable_range") == [expected_min, expected_max]
        and inventory.get("vowels") == list(vowels)
        and inventory.get("consonants") == list(consonants)
    )


def _pick_entry(
    language_model: Dict[str, Any],
    pos: str,
    blocked_ids: Optional[Set[str]] = None,
    fallback_pos: Optional[Sequence[str]] = None,
) -> Dict[str, str]:
    by_pos = language_model.get("by_pos", {})
    entries = by_pos.get(pos, [])

    if not entries and fallback_pos:
        for alt in fallback_pos:
            alt_entries = by_pos.get(alt, [])
            if alt_entries:
                entries = alt_entries
                break

    if not entries:
        entries = language_model.get("lexicon", [])

    if blocked_ids:
        filtered = [entry for entry in entries if entry.get("id") not in blocked_ids]
        if filtered:
            entries = filtered

    if not entries:
        return _new_entry("fallback", "a", "sound", "SOUND", pos, "fallback")
    return random.choice(entries)


def _entry_to_word_sample(entry: Dict[str, str]) -> Dict[str, str]:
    return {
        "ipa": entry.get("ipa", ""),
        "meaning": entry.get("meaning", ""),
        "gloss": entry.get("gloss", ""),
        "part_of_speech": POS_LABELS.get(entry.get("pos", ""), entry.get("pos", "")),
        "source": entry.get("source", ""),
    }


def _pick_argument_entry(
    language_model: Dict[str, Any],
    grammar: Dict[str, object],
    role: str,
    blocked_ids: Set[str],
) -> Dict[str, str]:
    pron_key = "subject_pronoun_rate" if role == "S" else "object_pronoun_rate"
    pron_rate = float(grammar.get(pron_key, 0.0))
    if random.random() < pron_rate:
        return _pick_entry(language_model, "PRON", blocked_ids=blocked_ids, fallback_pos=["N"])
    return _pick_entry(language_model, "N", blocked_ids=blocked_ids, fallback_pos=["PRON"])


def _build_clause(language_model: Dict[str, Any], grammar_profile_name: str) -> Tuple[List[str], List[str], str]:
    grammar = grammar_profile(grammar_profile_name)
    template_weights = grammar.get("clause_templates", GRAMMAR_PROFILES[DEFAULT_GRAMMAR_PROFILE]["clause_templates"])
    template = weighted_choice(template_weights, fallback="SOV")
    slots = CLAUSE_SLOTS.get(template, CLAUSE_SLOTS["SOV"])

    particles = language_model.get("particles", {})
    used_ids: Set[str] = set()
    tokens: List[str] = []
    glosses: List[str] = []

    for slot in slots:
        if slot == "S":
            subject = _pick_argument_entry(language_model, grammar, role="S", blocked_ids=used_ids)
            used_ids.add(subject["id"])
            tokens.append(subject["ipa"])
            glosses.append(subject["gloss"])
            if random.random() < float(grammar.get("subject_particle_rate", 0.0)):
                top = particles.get("TOP")
                if top:
                    tokens.append(top["ipa"])
                    glosses.append(top["gloss"])
            continue

        if slot == "O":
            obj = _pick_argument_entry(language_model, grammar, role="O", blocked_ids=used_ids)
            used_ids.add(obj["id"])
            tokens.append(obj["ipa"])
            glosses.append(obj["gloss"])
            if random.random() < float(grammar.get("object_particle_rate", 0.0)):
                acc = particles.get("ACC")
                if acc:
                    tokens.append(acc["ipa"])
                    glosses.append(acc["gloss"])
            continue

        verb = _pick_entry(language_model, "V", blocked_ids=used_ids, fallback_pos=["N"])
        used_ids.add(verb["id"])
        tokens.append(verb["ipa"])
        glosses.append(verb["gloss"])
        if random.random() < float(grammar.get("tam_particle_rate", 0.0)):
            tam = particles.get("TAM")
            if tam:
                tokens.append(tam["ipa"])
                glosses.append(tam["gloss"])

    return tokens, glosses, template


def _append_modifier_phrase(
    tokens: List[str],
    glosses: List[str],
    language_model: Dict[str, Any],
    grammar: Dict[str, object],
) -> None:
    modifier = _pick_entry(language_model, "ADJ", fallback_pos=["N"])
    head = _pick_entry(language_model, "N", fallback_pos=["PRON", "ADJ"])
    modifier_position_weights = grammar.get("modifier_positions", [("pre", 1.0)])
    modifier_position = weighted_choice(modifier_position_weights, fallback="pre")

    if modifier_position == "post":
        tokens.extend([head["ipa"], modifier["ipa"]])
        glosses.extend([head["gloss"], modifier["gloss"]])
        return

    tokens.extend([modifier["ipa"], head["ipa"]])
    glosses.extend([modifier["gloss"], head["gloss"]])


def _expand_clause(
    tokens: List[str],
    glosses: List[str],
    language_model: Dict[str, Any],
    target_word_count: int,
    grammar_profile_name: str,
) -> None:
    grammar = grammar_profile(grammar_profile_name)
    particles = language_model.get("particles", {})

    while len(tokens) < target_word_count:
        remaining = target_word_count - len(tokens)

        if remaining >= 2 and random.random() < float(grammar.get("modifier_rate", 0.0)):
            _append_modifier_phrase(tokens, glosses, language_model, grammar)
            continue

        if remaining >= 2 and random.random() < float(grammar.get("adjunct_rate", 0.0)):
            noun = _pick_entry(language_model, "N", fallback_pos=["PRON", "ADJ"])
            tokens.append(noun["ipa"])
            glosses.append(noun["gloss"])
            if len(tokens) < target_word_count:
                loc = particles.get("LOC")
                if loc:
                    tokens.append(loc["ipa"])
                    glosses.append(loc["gloss"])
                else:
                    filler = _pick_entry(language_model, "ADJ", fallback_pos=["N"])
                    tokens.append(filler["ipa"])
                    glosses.append(filler["gloss"])
            continue

        filler_weights = grammar.get("filler_pos", [("ADJ", 0.4), ("N", 0.3), ("V", 0.2), ("PART", 0.1)])
        filler_pos = weighted_choice(filler_weights, fallback="N")
        fallback_lookup = {
            "ADJ": ["N", "PART"],
            "N": ["PRON", "ADJ"],
            "V": ["N", "ADJ"],
            "PART": ["ADJ", "N"],
        }
        filler = _pick_entry(language_model, filler_pos, fallback_pos=fallback_lookup.get(filler_pos, ["N"]))
        tokens.append(filler["ipa"])
        glosses.append(filler["gloss"])


def _generate_sentence_sample(
    language_model: Dict[str, Any],
    words_range: Tuple[int, int],
    grammar_profile_name: str,
) -> Dict[str, str]:
    min_words, max_words = normalize_range(words_range, minimum=2)
    target_word_count = random.randint(min_words, max_words)

    tokens, glosses, template = _build_clause(language_model, grammar_profile_name=grammar_profile_name)
    _expand_clause(tokens, glosses, language_model, target_word_count=target_word_count, grammar_profile_name=grammar_profile_name)

    grammar = grammar_profile(grammar_profile_name)
    punctuation_weights = grammar.get("punctuation", GRAMMAR_PROFILES[DEFAULT_GRAMMAR_PROFILE]["punctuation"])
    punctuation = weighted_choice(punctuation_weights, fallback=".")

    question_particle = language_model.get("particles", {}).get("Q")
    if punctuation == "?" and question_particle and len(tokens) < max_words:
        tokens.append(question_particle["ipa"])
        glosses.append(question_particle["gloss"])

    return {
        "ipa": f"{' '.join(tokens)}{punctuation}",
        "gloss": f"{' '.join(glosses)}{punctuation}",
        "template": template,
    }


def build_sample_words(
    vowels: Sequence[str],
    consonants: Sequence[str],
    sample_count: int,
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    concept_list_name: str = DEFAULT_CONCEPT_LIST,
    grammar_profile_name: str = DEFAULT_GRAMMAR_PROFILE,
    language_model: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    model = language_model
    if model is None:
        model = build_language_model(
            vowels=vowels,
            consonants=consonants,
            syllable_range=syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
            concept_list_name=concept_list_name,
            grammar_profile_name=grammar_profile_name,
        )

    count = max(1, int(sample_count))
    grammar = grammar_profile(grammar_profile_name)
    pos_weights = grammar.get("sample_word_pos", GRAMMAR_PROFILES[DEFAULT_GRAMMAR_PROFILE]["sample_word_pos"])

    samples: List[Dict[str, str]] = []
    for _ in range(count):
        pos = weighted_choice(pos_weights, fallback="N")
        entry = _pick_entry(model, pos, fallback_pos=["N", "V", "ADJ", "PART", "PRON"])
        samples.append(_entry_to_word_sample(entry))
    return samples


def build_sample_sentences(
    vowels: Sequence[str],
    consonants: Sequence[str],
    sample_count: int,
    syllable_range: Tuple[int, int],
    words_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    concept_list_name: str = DEFAULT_CONCEPT_LIST,
    grammar_profile_name: str = DEFAULT_GRAMMAR_PROFILE,
    language_model: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    model = language_model
    if model is None:
        model = build_language_model(
            vowels=vowels,
            consonants=consonants,
            syllable_range=syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
            concept_list_name=concept_list_name,
            grammar_profile_name=grammar_profile_name,
        )

    count = max(1, int(sample_count))
    return [
        _generate_sentence_sample(
            language_model=model,
            words_range=words_range,
            grammar_profile_name=grammar_profile_name,
        )
        for _ in range(count)
    ]
