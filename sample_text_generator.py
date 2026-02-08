"""Word and sentence sample generation utilities.

This module keeps semantics intentionally lightweight: concept tags help produce
more coherent forms and clauses without turning this project into a full
meaning generator.
"""

from __future__ import annotations

from copy import deepcopy
import math
import random
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import concept_packs

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
        "phonotactics_overrides": {
            "soft_constraints": {
                "final_complex_coda_penalty": 0.85,
                "hiatus_penalty": 0.18,
            }
        },
    },
    "Dense": {
        "description": "Denser consonant clusters and heavier codas.",
        "syllable_shapes": [("CV", 0.24), ("CVC", 0.34), ("CCV", 0.12), ("CVCC", 0.14), ("VC", 0.10), ("V", 0.06)],
        "phonotactics_overrides": {
            "style_template_blend": 0.82,
            "cluster": {
                "violation_penalty": 0.30,
                "max_attempts": 16,
            },
            "soft_constraints": {
                "cluster_violation_penalty": 0.70,
                "final_complex_coda_penalty": 0.20,
            },
        },
    },
}
DEFAULT_STYLE_PRESET = "Balanced"

DEFAULT_PHONOTACTIC_PROFILE: Dict[str, object] = {
    "style_template_blend": 0.58,
    "template_weights_by_position": {
        "single": [("V", 0.10), ("CV", 0.44), ("VC", 0.11), ("CVC", 0.24), ("CVV", 0.07), ("CCV", 0.04)],
        "initial": [("V", 0.06), ("CV", 0.52), ("VC", 0.04), ("CVC", 0.20), ("CVV", 0.08), ("CCV", 0.10)],
        "medial": [("V", 0.09), ("CV", 0.40), ("VC", 0.08), ("CVC", 0.22), ("CVV", 0.10), ("VCV", 0.11)],
        "final": [("V", 0.07), ("CV", 0.28), ("VC", 0.20), ("CVC", 0.30), ("CVV", 0.05), ("CVCC", 0.10)],
    },
    "slot_class_weights": {
        "onset": {
            "stop": 1.00,
            "affricate": 0.95,
            "fricative": 0.95,
            "nasal": 0.82,
            "velar_nasal": 0.28,
            "liquid": 0.86,
            "glide": 0.72,
            "unknown": 1.00,
        },
        "word_initial_onset": {
            "stop": 1.00,
            "affricate": 0.95,
            "fricative": 0.92,
            "nasal": 0.48,
            "velar_nasal": 0.07,
            "liquid": 0.78,
            "glide": 0.66,
            "unknown": 0.95,
        },
        "medial": {
            "stop": 0.94,
            "affricate": 0.92,
            "fricative": 1.02,
            "nasal": 1.05,
            "velar_nasal": 0.72,
            "liquid": 1.08,
            "glide": 0.95,
            "unknown": 1.00,
        },
        "coda": {
            "stop": 0.78,
            "affricate": 0.72,
            "fricative": 0.97,
            "nasal": 1.24,
            "velar_nasal": 1.10,
            "liquid": 1.14,
            "glide": 0.58,
            "unknown": 0.96,
        },
        "word_final_coda": {
            "stop": 0.68,
            "affricate": 0.65,
            "fricative": 0.90,
            "nasal": 1.18,
            "velar_nasal": 1.08,
            "liquid": 1.04,
            "glide": 0.48,
            "unknown": 0.88,
        },
    },
    "segment_slot_weights": {
        "onset": {"ŋ": 0.30, "ʔ": 0.82},
        "word_initial_onset": {"ŋ": 0.04, "ɲ": 0.24, "ʔ": 0.74, "h": 0.90},
        "medial": {"ʔ": 0.72},
        "coda": {"h": 0.55},
        "word_final_coda": {"h": 0.40, "ʔ": 0.56},
    },
    "cluster": {
        "max_attempts": 12,
        "allow_identical_adjacent": False,
        "rise_bonus": 1.36,
        "fall_bonus": 1.36,
        "medial_change_bonus": 1.10,
        "s_stop_bonus": 1.24,
        "violation_penalty": 0.22,
    },
    "candidate_selection": {
        "candidates_per_word": 7,
        "temperature": 0.82,
    },
    "soft_constraints": {
        "initial_velar_nasal_penalty": 4.00,
        "triple_repeat_penalty": 2.50,
        "identical_adjacent_penalty": 0.65,
        "cluster_violation_penalty": 1.10,
        "final_complex_coda_penalty": 0.42,
        "hiatus_penalty": 0.35,
        "onsetless_word_penalty": 0.18,
    },
    "co_occurrence": {
        "enabled": True,
        "palatal_front_bonus": 1.30,
        "palatal_back_penalty": 0.76,
        "dorsal_back_bonus": 1.22,
        "dorsal_front_penalty": 0.84,
        "labial_rounded_bonus": 1.14,
        "front_back_harmony_bonus": 1.14,
        "front_back_harmony_penalty": 0.90,
        "harmony_penalty": 0.32,
    },
    "morphology": {
        "enabled": True,
        "prefix_rate_by_pos": {"N": 0.10, "V": 0.14, "ADJ": 0.08, "default": 0.06},
        "suffix_rate_by_pos": {"N": 0.28, "V": 0.38, "ADJ": 0.20, "default": 0.18},
        "prefix_pool_size": 5,
        "suffix_pool_size": 7,
        "prefix_syllables": [1, 1],
        "suffix_syllables": [1, 1],
    },
}

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

IPA_NASAL_CHARS: Set[str] = {"m", "n", "ɱ", "ŋ", "ɲ", "ɳ", "ɴ"}
IPA_VELAR_NASAL_CHARS: Set[str] = {"ŋ", "ɴ"}
IPA_LIQUID_CHARS: Set[str] = {"l", "ɫ", "ɬ", "ɮ", "ɭ", "r", "ɾ", "ɽ", "ɻ", "ʀ", "ʙ", "ɺ"}
IPA_GLIDE_CHARS: Set[str] = {"j", "w", "ɥ", "ʋ"}
IPA_STOP_CHARS: Set[str] = {"p", "b", "t", "d", "ʈ", "ɖ", "c", "ɟ", "k", "g", "q", "ɢ", "ʔ"}
IPA_FRICATIVE_CHARS: Set[str] = {
    "f",
    "v",
    "θ",
    "ð",
    "s",
    "z",
    "ʃ",
    "ʒ",
    "ʂ",
    "ʐ",
    "ɕ",
    "ʑ",
    "ç",
    "ʝ",
    "x",
    "ɣ",
    "χ",
    "ʁ",
    "ħ",
    "ʕ",
    "h",
    "ɦ",
    "ɸ",
    "β",
}
IPA_SIBILANTS: Set[str] = {"s", "z", "ʃ", "ʒ", "ʂ", "ʐ", "ɕ", "ʑ"}
AFFRICATE_PATTERNS: Tuple[str, ...] = ("ts", "dz", "tʃ", "dʒ", "tɕ", "dʑ", "ʈʂ", "ɖʐ", "pf")
FRONT_VOWEL_CHARS: Set[str] = {"i", "y", "e", "ø", "ɛ", "œ", "ɪ", "ʏ", "ɨ", "ʉ"}
BACK_VOWEL_CHARS: Set[str] = {"u", "o", "ɯ", "ɤ", "ɔ", "ɒ", "ɑ", "ʊ", "ʌ"}
ROUNDED_VOWEL_CHARS: Set[str] = {"u", "o", "y", "ø", "œ", "ɔ", "ɒ", "ʊ", "ʉ", "ʏ"}
PALATAL_CONSONANT_HINTS: Set[str] = {"c", "ɟ", "ɲ", "j", "ɕ", "ʑ", "ç", "ʝ", "ʃ", "ʒ"}
DORSAL_CONSONANT_HINTS: Set[str] = {"k", "g", "ŋ", "x", "ɣ", "q", "ɢ", "χ", "ʁ"}
LABIAL_CONSONANT_HINTS: Set[str] = {"p", "b", "m", "f", "v", "ɸ", "β", "w", "ʋ"}


def _deep_merge_dict(base: Dict[str, object], overrides: Dict[str, object]) -> Dict[str, object]:
    merged: Dict[str, object] = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = merged.get(key, {})
            if not isinstance(nested, dict):
                nested = {}
            merged[key] = _deep_merge_dict(nested, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _clamp_float(value: object, fallback: float, minimum: float, maximum: float) -> float:
    number = _as_float(value)
    if number is None:
        return fallback
    return max(minimum, min(maximum, float(number)))


def _canonicalize_config(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _canonicalize_config(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize_config(item) for item in value]
    return value


def _normalize_weighted_pairs(
    value: object,
    fallback: Sequence[Tuple[str, float]],
    label_pattern: str = r".+",
) -> List[Tuple[str, float]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [(label, float(weight)) for label, weight in fallback if float(weight) > 0]

    cleaned: List[Tuple[str, float]] = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        label = str(item[0])
        weight = _as_float(item[1])
        if weight is None or weight <= 0:
            continue
        if not re.fullmatch(label_pattern, label):
            continue
        cleaned.append((label, float(weight)))
    if cleaned:
        return cleaned
    return [(label, float(weight)) for label, weight in fallback if float(weight) > 0]


def resolve_phonotactic_profile(
    style_name: str,
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    profile: Dict[str, object] = deepcopy(DEFAULT_PHONOTACTIC_PROFILE)

    style = style_profile(style_name)
    style_overrides = style.get("phonotactics_overrides")
    if isinstance(style_overrides, dict):
        profile = _deep_merge_dict(profile, style_overrides)
    if isinstance(phonotactic_profile_overrides, dict):
        profile = _deep_merge_dict(profile, phonotactic_profile_overrides)

    default_templates = DEFAULT_PHONOTACTIC_PROFILE.get("template_weights_by_position", {})
    raw_templates = profile.get("template_weights_by_position")
    if not isinstance(raw_templates, dict):
        raw_templates = default_templates
    if not isinstance(default_templates, dict):
        default_templates = {}

    normalized_templates: Dict[str, List[Tuple[str, float]]] = {}
    for position in ("single", "initial", "medial", "final"):
        fallback = default_templates.get(position, default_templates.get("single", [("CV", 1.0)]))
        source = raw_templates.get(position, raw_templates.get("single", fallback))
        normalized_templates[position] = _normalize_weighted_pairs(source, fallback, label_pattern=r"[CV]+")
    profile["template_weights_by_position"] = normalized_templates

    profile["style_template_blend"] = _clamp_float(
        profile.get("style_template_blend"),
        fallback=0.6,
        minimum=0.0,
        maximum=1.0,
    )

    candidate_cfg = profile.get("candidate_selection")
    if not isinstance(candidate_cfg, dict):
        candidate_cfg = {}
    candidate_cfg["candidates_per_word"] = max(1, int(_clamp_float(candidate_cfg.get("candidates_per_word"), 6.0, 1.0, 64.0)))
    candidate_cfg["temperature"] = _clamp_float(candidate_cfg.get("temperature"), 0.85, 0.05, 4.0)
    profile["candidate_selection"] = candidate_cfg

    co_occurrence_cfg = profile.get("co_occurrence")
    if not isinstance(co_occurrence_cfg, dict):
        co_occurrence_cfg = {}
    co_occurrence_cfg["enabled"] = bool(co_occurrence_cfg.get("enabled", True))
    for key, fallback in (
        ("palatal_front_bonus", 1.25),
        ("palatal_back_penalty", 0.8),
        ("dorsal_back_bonus", 1.2),
        ("dorsal_front_penalty", 0.85),
        ("labial_rounded_bonus", 1.1),
        ("front_back_harmony_bonus", 1.1),
        ("front_back_harmony_penalty", 0.9),
        ("harmony_penalty", 0.3),
    ):
        co_occurrence_cfg[key] = _clamp_float(co_occurrence_cfg.get(key), fallback, 0.0, 8.0)
    profile["co_occurrence"] = co_occurrence_cfg

    profile["morphology"] = _resolve_morphology_profile(profile)

    return profile


def _normalize_segment_for_classification(segment: str) -> str:
    normalized = str(segment).lower().strip()
    return re.sub(r"[\u0300-\u036fːˑˈˌʼʰʷʲ˞ˤˠˀˁ]", "", normalized)


def _vowel_features(segment: str) -> Set[str]:
    normalized = _normalize_segment_for_classification(segment)
    features: Set[str] = set()
    if any(char in normalized for char in FRONT_VOWEL_CHARS):
        features.add("front")
    if any(char in normalized for char in BACK_VOWEL_CHARS):
        features.add("back")
    if any(char in normalized for char in ROUNDED_VOWEL_CHARS):
        features.add("rounded")
    if not features:
        features.add("central")
    return features


def _consonant_features(segment: str) -> Set[str]:
    normalized = _normalize_segment_for_classification(segment)
    features: Set[str] = set()
    if any(char in normalized for char in PALATAL_CONSONANT_HINTS):
        features.add("palatal")
    if any(char in normalized for char in DORSAL_CONSONANT_HINTS):
        features.add("dorsal")
    if any(char in normalized for char in LABIAL_CONSONANT_HINTS):
        features.add("labial")
    return features


def _co_occurrence_vowel_weight(
    vowel: str,
    previous_consonant: str,
    previous_vowel: str,
    phonotactic_profile: Dict[str, object],
) -> float:
    co_occurrence_cfg = phonotactic_profile.get("co_occurrence", {})
    if not isinstance(co_occurrence_cfg, dict):
        return 1.0
    if not bool(co_occurrence_cfg.get("enabled", True)):
        return 1.0

    weight = 1.0
    vowel_features = _vowel_features(vowel)

    if previous_consonant:
        consonant_features = _consonant_features(previous_consonant)
        if "palatal" in consonant_features:
            if "front" in vowel_features:
                weight *= _clamp_float(co_occurrence_cfg.get("palatal_front_bonus"), 1.25, 0.0, 8.0)
            if "back" in vowel_features:
                weight *= _clamp_float(co_occurrence_cfg.get("palatal_back_penalty"), 0.8, 0.0, 8.0)
        if "dorsal" in consonant_features:
            if "back" in vowel_features:
                weight *= _clamp_float(co_occurrence_cfg.get("dorsal_back_bonus"), 1.2, 0.0, 8.0)
            if "front" in vowel_features:
                weight *= _clamp_float(co_occurrence_cfg.get("dorsal_front_penalty"), 0.85, 0.0, 8.0)
        if "labial" in consonant_features and "rounded" in vowel_features:
            weight *= _clamp_float(co_occurrence_cfg.get("labial_rounded_bonus"), 1.1, 0.0, 8.0)

    if previous_vowel:
        prior_features = _vowel_features(previous_vowel)
        if "front" in prior_features and "front" in vowel_features:
            weight *= _clamp_float(co_occurrence_cfg.get("front_back_harmony_bonus"), 1.1, 0.0, 8.0)
        elif "back" in prior_features and "back" in vowel_features:
            weight *= _clamp_float(co_occurrence_cfg.get("front_back_harmony_bonus"), 1.1, 0.0, 8.0)
        elif ("front" in prior_features and "back" in vowel_features) or (
            "back" in prior_features and "front" in vowel_features
        ):
            weight *= _clamp_float(co_occurrence_cfg.get("front_back_harmony_penalty"), 0.9, 0.0, 8.0)

    return max(0.0, float(weight))


def _lookup_pos_rate(rate_map: object, pos: str, default: float) -> float:
    if not isinstance(rate_map, dict):
        return default
    if pos in rate_map:
        return _clamp_float(rate_map.get(pos), default, 0.0, 1.0)
    return _clamp_float(rate_map.get("default"), default, 0.0, 1.0)


def _join_morphemes(parts: Sequence[str], separator: str) -> str:
    cleaned_parts = [str(part) for part in parts if str(part)]
    if not cleaned_parts:
        return ""
    if not separator:
        return "".join(cleaned_parts)

    tokens: List[str] = []
    for part in cleaned_parts:
        split_tokens = [token for token in part.split(separator) if token]
        if split_tokens:
            tokens.extend(split_tokens)
        else:
            tokens.append(part)
    return separator.join(tokens)


def _resolve_morphology_profile(phonotactic_profile: Dict[str, object]) -> Dict[str, object]:
    morphology_cfg = phonotactic_profile.get("morphology", {})
    if not isinstance(morphology_cfg, dict):
        morphology_cfg = {}

    prefix_pool_size = max(0, int(_clamp_float(morphology_cfg.get("prefix_pool_size"), 5.0, 0.0, 64.0)))
    suffix_pool_size = max(0, int(_clamp_float(morphology_cfg.get("suffix_pool_size"), 7.0, 0.0, 64.0)))
    prefix_range_raw = morphology_cfg.get("prefix_syllables", (1, 1))
    suffix_range_raw = morphology_cfg.get("suffix_syllables", (1, 1))
    if not isinstance(prefix_range_raw, (list, tuple)) or len(prefix_range_raw) != 2:
        prefix_range_raw = (1, 1)
    if not isinstance(suffix_range_raw, (list, tuple)) or len(suffix_range_raw) != 2:
        suffix_range_raw = (1, 1)
    prefix_min = int(_clamp_float(prefix_range_raw[0], 1.0, 1.0, 8.0))
    prefix_max = int(_clamp_float(prefix_range_raw[1], float(prefix_min), 1.0, 8.0))
    suffix_min = int(_clamp_float(suffix_range_raw[0], 1.0, 1.0, 8.0))
    suffix_max = int(_clamp_float(suffix_range_raw[1], float(suffix_min), 1.0, 8.0))

    return {
        "enabled": bool(morphology_cfg.get("enabled", True)),
        "prefix_rate_by_pos": morphology_cfg.get("prefix_rate_by_pos", {"default": 0.08}),
        "suffix_rate_by_pos": morphology_cfg.get("suffix_rate_by_pos", {"default": 0.2}),
        "prefix_pool_size": prefix_pool_size,
        "suffix_pool_size": suffix_pool_size,
        "prefix_syllables": normalize_range((prefix_min, prefix_max), minimum=1),
        "suffix_syllables": normalize_range((suffix_min, suffix_max), minimum=1),
    }


def _build_morphology_resources(
    vowels: Sequence[str],
    consonants: Sequence[str],
    style_name: str,
    syllable_separator: str,
    phonotactic_profile_overrides: Optional[Dict[str, object]],
    phonotactic_profile: Dict[str, object],
) -> Dict[str, object]:
    morphology_cfg = _resolve_morphology_profile(phonotactic_profile)
    if not bool(morphology_cfg.get("enabled", True)):
        return {"enabled": False, "prefixes": [], "suffixes": [], "config": morphology_cfg}

    affix_forms: Set[str] = set()
    prefixes: List[str] = []
    suffixes: List[str] = []

    prefix_pool_size = int(morphology_cfg.get("prefix_pool_size", 0))
    suffix_pool_size = int(morphology_cfg.get("suffix_pool_size", 0))
    prefix_syllables = tuple(morphology_cfg.get("prefix_syllables", (1, 1)))
    suffix_syllables = tuple(morphology_cfg.get("suffix_syllables", (1, 1)))

    for _ in range(prefix_pool_size):
        prefixes.append(
            _generate_unique_word(
                vowels=vowels,
                consonants=consonants,
                syllable_range=prefix_syllables,
                syllable_separator=syllable_separator,
                style_name=style_name,
                used_forms=affix_forms,
                phonotactic_profile_overrides=phonotactic_profile_overrides,
                apply_morphology=False,
            )
        )
    for _ in range(suffix_pool_size):
        suffixes.append(
            _generate_unique_word(
                vowels=vowels,
                consonants=consonants,
                syllable_range=suffix_syllables,
                syllable_separator=syllable_separator,
                style_name=style_name,
                used_forms=affix_forms,
                phonotactic_profile_overrides=phonotactic_profile_overrides,
                apply_morphology=False,
            )
        )

    return {
        "enabled": True,
        "prefixes": prefixes,
        "suffixes": suffixes,
        "config": morphology_cfg,
    }


def _apply_morphology_to_stem(
    stem: str,
    pos: str,
    morphology_resources: Optional[Dict[str, object]],
    syllable_separator: str,
) -> str:
    if not isinstance(morphology_resources, dict):
        return stem
    if not bool(morphology_resources.get("enabled", False)):
        return stem

    config = morphology_resources.get("config", {})
    if not isinstance(config, dict):
        config = {}

    prefix_rate = _lookup_pos_rate(config.get("prefix_rate_by_pos"), pos, default=0.08)
    suffix_rate = _lookup_pos_rate(config.get("suffix_rate_by_pos"), pos, default=0.20)

    prefixes = morphology_resources.get("prefixes", [])
    suffixes = morphology_resources.get("suffixes", [])
    if not isinstance(prefixes, list):
        prefixes = []
    if not isinstance(suffixes, list):
        suffixes = []

    prefix = random.choice(prefixes) if prefixes and random.random() < prefix_rate else ""
    suffix = random.choice(suffixes) if suffixes and random.random() < suffix_rate else ""

    if not prefix and not suffix:
        return stem
    return _join_morphemes([prefix, stem, suffix], separator=syllable_separator)

def _segment_classes(segment: str) -> Set[str]:
    normalized = _normalize_segment_for_classification(segment)
    classes: Set[str] = set()
    if any(char in normalized for char in IPA_VELAR_NASAL_CHARS):
        classes.add("velar_nasal")
        classes.add("nasal")
    elif any(char in normalized for char in IPA_NASAL_CHARS):
        classes.add("nasal")

    if "͡" in normalized or any(pattern in normalized for pattern in AFFRICATE_PATTERNS):
        classes.add("affricate")
    if any(char in normalized for char in IPA_STOP_CHARS):
        classes.add("stop")
    if any(char in normalized for char in IPA_FRICATIVE_CHARS):
        classes.add("fricative")
    if any(char in normalized for char in IPA_LIQUID_CHARS):
        classes.add("liquid")
    if any(char in normalized for char in IPA_GLIDE_CHARS):
        classes.add("glide")

    if not classes:
        classes.add("unknown")
    return classes


def _segment_sonority(segment: str) -> float:
    classes = _segment_classes(segment)
    if "glide" in classes:
        return 5.5
    if "liquid" in classes:
        return 4.5
    if "nasal" in classes:
        return 3.6
    if "fricative" in classes:
        return 2.6
    if "affricate" in classes:
        return 2.1
    if "stop" in classes:
        return 1.4
    return 3.0


def _is_sibilant(segment: str) -> bool:
    normalized = _normalize_segment_for_classification(segment)
    return any(char in normalized for char in IPA_SIBILANTS)


def _is_stop_like(segment: str) -> bool:
    classes = _segment_classes(segment)
    return "stop" in classes or "affricate" in classes


def _segment_weight_for_slot(
    segment: str,
    slot_role: str,
    phonotactic_profile: Dict[str, object],
) -> float:
    weight = 1.0

    class_weight_tables = phonotactic_profile.get("slot_class_weights", {})
    if isinstance(class_weight_tables, dict):
        class_weights = class_weight_tables.get(slot_role, {})
        if isinstance(class_weights, dict):
            segment_classes = _segment_classes(segment)
            for class_name in segment_classes:
                if class_name in class_weights:
                    class_weight = _as_float(class_weights.get(class_name))
                    if class_weight is not None:
                        weight *= max(0.0, class_weight)

    segment_weight_tables = phonotactic_profile.get("segment_slot_weights", {})
    if isinstance(segment_weight_tables, dict):
        segment_weights = segment_weight_tables.get(slot_role, {})
        if isinstance(segment_weights, dict):
            value = segment_weights.get(segment)
            explicit = _as_float(value)
            if explicit is not None:
                weight *= max(0.0, explicit)

    return max(0.0, float(weight))


def _weighted_segment_choice(segments: Sequence[str], raw_weights: Sequence[float]) -> str:
    if not segments:
        return ""
    sanitized_weights = [max(0.0, float(weight)) for weight in raw_weights]
    if len(sanitized_weights) != len(segments) or sum(sanitized_weights) <= 0:
        return random.choice(list(segments))
    return random.choices(list(segments), weights=sanitized_weights, k=1)[0]


def _cluster_transition_weight(
    previous_segment: str,
    next_segment: str,
    cluster_type: str,
    transition_index: int,
    phonotactic_profile: Dict[str, object],
) -> float:
    cluster_cfg = phonotactic_profile.get("cluster", {})
    if not isinstance(cluster_cfg, dict):
        cluster_cfg = {}

    rise_bonus = _clamp_float(cluster_cfg.get("rise_bonus"), 1.2, 0.0, 8.0)
    fall_bonus = _clamp_float(cluster_cfg.get("fall_bonus"), 1.2, 0.0, 8.0)
    s_stop_bonus = _clamp_float(cluster_cfg.get("s_stop_bonus"), 1.15, 0.0, 8.0)
    violation_penalty = _clamp_float(cluster_cfg.get("violation_penalty"), 0.2, 0.0, 8.0)
    medial_change_bonus = _clamp_float(cluster_cfg.get("medial_change_bonus"), 1.05, 0.0, 8.0)

    previous_sonority = _segment_sonority(previous_segment)
    next_sonority = _segment_sonority(next_segment)

    if cluster_type == "onset":
        if transition_index == 1 and _is_sibilant(previous_segment) and _is_stop_like(next_segment):
            return s_stop_bonus
        if next_sonority > previous_sonority:
            return rise_bonus
        return violation_penalty

    if cluster_type == "coda":
        if next_sonority < previous_sonority:
            return fall_bonus
        return violation_penalty

    if previous_sonority != next_sonority:
        return medial_change_bonus
    return violation_penalty


def _count_cluster_sonority_violations(cluster: Sequence[str], cluster_type: str) -> int:
    if len(cluster) < 2:
        return 0

    violations = 0
    for index in range(1, len(cluster)):
        previous_segment = cluster[index - 1]
        current_segment = cluster[index]
        previous_sonority = _segment_sonority(previous_segment)
        current_sonority = _segment_sonority(current_segment)

        if cluster_type == "onset":
            if _is_sibilant(previous_segment) and _is_stop_like(current_segment):
                continue
            if current_sonority <= previous_sonority:
                violations += 1
            continue

        if cluster_type == "coda":
            if current_sonority >= previous_sonority:
                violations += 1
            continue

        if current_sonority == previous_sonority:
            violations += 1

    return violations


def _syllable_position(index: int, syllable_count: int) -> str:
    if syllable_count <= 1:
        return "single"
    if index <= 0:
        return "initial"
    if index >= syllable_count - 1:
        return "final"
    return "medial"


def _word_consonant_slot(
    shape: str,
    start_index: int,
    end_index: int,
    syllable_position: str,
) -> Tuple[str, str]:
    has_vowel_before = "V" in shape[:start_index]
    has_vowel_after = "V" in shape[end_index:]

    if not has_vowel_before and has_vowel_after:
        if syllable_position in {"single", "initial"}:
            return "onset", "word_initial_onset"
        return "onset", "onset"
    if has_vowel_before and not has_vowel_after:
        if syllable_position in {"single", "final"}:
            return "coda", "word_final_coda"
        return "coda", "coda"
    if has_vowel_before and has_vowel_after:
        return "medial", "medial"
    if syllable_position in {"single", "initial"}:
        return "onset", "word_initial_onset"
    return "onset", "onset"


def _choose_template_for_position(
    style_name: str,
    syllable_position: str,
    phonotactic_profile: Dict[str, object],
) -> List[Tuple[str, float]]:
    style = style_profile(style_name)
    default_style_templates = STYLE_PRESETS[DEFAULT_STYLE_PRESET].get("syllable_shapes", [("CV", 1.0)])
    style_templates = _normalize_weighted_pairs(
        style.get("syllable_shapes"),
        default_style_templates if isinstance(default_style_templates, Sequence) else [("CV", 1.0)],
        label_pattern=r"[CV]+",
    )

    position_templates_map = phonotactic_profile.get("template_weights_by_position", {})
    if not isinstance(position_templates_map, dict):
        position_templates_map = {}
    position_templates = _normalize_weighted_pairs(
        position_templates_map.get(syllable_position),
        position_templates_map.get("single", style_templates),
        label_pattern=r"[CV]+",
    )

    blend = _clamp_float(phonotactic_profile.get("style_template_blend"), 0.6, 0.0, 1.0)
    combined: Dict[str, float] = {}
    for shape, weight in position_templates:
        combined[shape] = combined.get(shape, 0.0) + float(weight) * (1.0 - blend)
    for shape, weight in style_templates:
        combined[shape] = combined.get(shape, 0.0) + float(weight) * blend

    merged = [(shape, weight) for shape, weight in combined.items() if weight > 0]
    if merged:
        return merged
    return style_templates


def _filter_templates_for_inventory(
    templates: Sequence[Tuple[str, float]],
    has_vowels: bool,
    has_consonants: bool,
) -> List[Tuple[str, float]]:
    filtered: List[Tuple[str, float]] = []
    for shape, weight in templates:
        if not has_vowels and "V" in shape:
            continue
        if not has_consonants and "C" in shape:
            continue
        filtered.append((shape, float(weight)))
    return filtered


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
        overrides = profile.get("phonotactics_overrides")
        if overrides is not None and not isinstance(overrides, dict):
            report["errors"].append(f"{owner}.phonotactics_overrides must be a dict when provided.")
        elif isinstance(overrides, dict):
            template_overrides = overrides.get("template_weights_by_position")
            if isinstance(template_overrides, dict):
                for position_name, weights in template_overrides.items():
                    _validate_weighted_pairs(
                        report,
                        owner=owner,
                        field_name=f"phonotactics_overrides.template_weights_by_position[{position_name}]",
                        value=weights,
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
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source", ""))
        if source.startswith("concept-list:") or source.startswith("concept-pack:"):
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


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip()).strip("_").lower()
    return cleaned or "concept"


def _core_concept_entry(meaning: str, pos: str, gloss: str) -> Dict[str, Any]:
    concept_id = f"core.{_slugify(meaning)}"
    return {
        "concept_id": concept_id,
        "meaning": meaning,
        "pos": pos,
        "gloss": gloss,
        "tags": ["core"],
        "source_pack": "core",
        "register": "neutral",
        "biomes": [],
        "tier": "core",
    }


def resolve_concept_entries(
    concept_list_name: str,
    concept_pack_config: Optional[Dict[str, Any]] = None,
    include_packs: bool = True,
) -> List[Dict[str, Any]]:
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

    core_entries: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        meaning = str(entry.get("meaning", ""))
        pos = str(entry.get("pos", "N"))
        gloss = str(entry.get("gloss", "") or concept_gloss(meaning, pos))
        core_entries.append(_core_concept_entry(meaning, pos, gloss))

    if not core_entries and concept_list_name != DEFAULT_CONCEPT_LIST:
        core_entries = resolve_concept_entries(DEFAULT_CONCEPT_LIST, concept_pack_config=None, include_packs=False)

    pack_entries = concept_packs.select_pack_entries(concept_pack_config) if include_packs else []
    return core_entries + pack_entries


def _build_consonant_cluster(
    consonants: Sequence[str],
    cluster_length: int,
    cluster_type: str,
    slot_role: str,
    phonotactic_profile: Dict[str, object],
) -> List[str]:
    if cluster_length <= 0 or not consonants:
        return []

    cluster_cfg = phonotactic_profile.get("cluster", {})
    if not isinstance(cluster_cfg, dict):
        cluster_cfg = {}

    max_attempts = max(1, int(_clamp_float(cluster_cfg.get("max_attempts"), 10.0, 1.0, 128.0)))
    allow_identical = bool(cluster_cfg.get("allow_identical_adjacent", False))
    consonant_pool = list(consonants)

    best_cluster: List[str] = []
    best_violation_count = max_attempts + cluster_length

    for _ in range(max_attempts):
        candidate: List[str] = []
        for index in range(cluster_length):
            weights: List[float] = []
            for segment in consonant_pool:
                segment_weight = _segment_weight_for_slot(segment, slot_role, phonotactic_profile)
                if candidate:
                    previous = candidate[-1]
                    segment_weight *= _cluster_transition_weight(
                        previous_segment=previous,
                        next_segment=segment,
                        cluster_type=cluster_type,
                        transition_index=index,
                        phonotactic_profile=phonotactic_profile,
                    )
                    if not allow_identical and segment == previous:
                        segment_weight *= 0.02
                weights.append(segment_weight)

            chosen = _weighted_segment_choice(consonant_pool, weights)
            if not chosen:
                break
            candidate.append(chosen)

        if len(candidate) < cluster_length:
            filler = [choose_segment(consonant_pool) for _ in range(cluster_length - len(candidate))]
            candidate.extend([segment for segment in filler if segment])
        if len(candidate) != cluster_length:
            continue

        violation_count = _count_cluster_sonority_violations(candidate, cluster_type)
        if violation_count < best_violation_count:
            best_cluster = candidate
            best_violation_count = violation_count
        if violation_count == 0:
            return candidate

    if best_cluster:
        return best_cluster
    return [choose_segment(consonant_pool) for _ in range(cluster_length)]


def _generate_syllable_candidate(
    vowels: Sequence[str],
    consonants: Sequence[str],
    style_name: str,
    syllable_position: str,
    phonotactic_profile: Dict[str, object],
    previous_vowel: str = "",
) -> Dict[str, object]:
    vowels_list = list(vowels)
    consonants_list = list(consonants)

    template_weights = _choose_template_for_position(
        style_name=style_name,
        syllable_position=syllable_position,
        phonotactic_profile=phonotactic_profile,
    )
    template_weights = _filter_templates_for_inventory(
        template_weights,
        has_vowels=bool(vowels_list),
        has_consonants=bool(consonants_list),
    )
    if not template_weights:
        if vowels_list and consonants_list:
            template_weights = [("CV", 1.0)]
        elif vowels_list:
            template_weights = [("V", 0.75), ("VV", 0.25)]
        elif consonants_list:
            template_weights = [("C", 0.85), ("CC", 0.15)]
        else:
            template_weights = []

    template_fallback = template_weights[0][0] if template_weights else ""
    template = weighted_choice(template_weights, fallback=template_fallback) if template_weights else ""

    segments: List[str] = []
    slot_types: List[str] = []
    clusters: List[Dict[str, object]] = []
    active_previous_vowel = previous_vowel

    index = 0
    while index < len(template):
        slot = template[index]
        if slot == "V":
            previous_consonant = ""
            if segments and slot_types and slot_types[-1] == "C":
                previous_consonant = segments[-1]
            vowel_weights = [
                _co_occurrence_vowel_weight(
                    vowel=vowel_option,
                    previous_consonant=previous_consonant,
                    previous_vowel=active_previous_vowel,
                    phonotactic_profile=phonotactic_profile,
                )
                for vowel_option in vowels_list
            ]
            vowel = _weighted_segment_choice(vowels_list, vowel_weights)
            if vowel:
                segments.append(vowel)
                slot_types.append("V")
                active_previous_vowel = vowel
            index += 1
            continue

        start_index = index
        while index < len(template) and template[index] == "C":
            index += 1

        cluster_length = index - start_index
        cluster_type, slot_role = _word_consonant_slot(
            shape=template,
            start_index=start_index,
            end_index=index,
            syllable_position=syllable_position,
        )
        cluster_segments = _build_consonant_cluster(
            consonants=consonants_list,
            cluster_length=cluster_length,
            cluster_type=cluster_type,
            slot_role=slot_role,
            phonotactic_profile=phonotactic_profile,
        )
        if cluster_segments:
            segments.extend(cluster_segments)
            slot_types.extend(["C"] * len(cluster_segments))
            clusters.append(
                {
                    "type": cluster_type,
                    "slot_role": slot_role,
                    "segments": cluster_segments,
                }
            )

    return {
        "text": "".join(segments),
        "segments": segments,
        "slot_types": slot_types,
        "template": template,
        "position": syllable_position,
        "clusters": clusters,
        "starts_with_vowel": bool(slot_types and slot_types[0] == "V"),
        "ends_with_vowel": bool(slot_types and slot_types[-1] == "V"),
        "last_vowel": active_previous_vowel,
    }


def _generate_word_candidate(
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    phonotactic_profile: Dict[str, object],
) -> Dict[str, object]:
    min_syllables, max_syllables = normalize_range(syllable_range, minimum=1)
    syllable_count = random.randint(min_syllables, max_syllables)

    syllables: List[Dict[str, object]] = []
    last_vowel = ""
    for index in range(syllable_count):
        syllable = _generate_syllable_candidate(
            vowels=vowels,
            consonants=consonants,
            style_name=style_name,
            syllable_position=_syllable_position(index, syllable_count),
            phonotactic_profile=phonotactic_profile,
            previous_vowel=last_vowel,
        )
        if syllable.get("text"):
            syllables.append(syllable)
            last_vowel = str(syllable.get("last_vowel", last_vowel))

    if not syllables:
        fallback = choose_segment(vowels) or choose_segment(consonants) or "a"
        return {
            "form": fallback,
            "raw_form": fallback,
            "segments": [fallback],
            "syllables": [],
        }

    syllable_texts = [str(syllable.get("text", "")) for syllable in syllables]
    form = syllable_separator.join(syllable_texts)
    raw_form = "".join(syllable_texts)
    flat_segments: List[str] = []
    for syllable in syllables:
        for segment in syllable.get("segments", []):
            flat_segments.append(str(segment))
    flat_vowels: List[str] = []
    for syllable in syllables:
        syllable_segments = syllable.get("segments", [])
        syllable_slots = syllable.get("slot_types", [])
        if not isinstance(syllable_segments, list) or not isinstance(syllable_slots, list):
            continue
        for segment, slot_type in zip(syllable_segments, syllable_slots):
            if str(slot_type) == "V":
                flat_vowels.append(str(segment))

    return {
        "form": form,
        "raw_form": raw_form,
        "segments": flat_segments,
        "vowels": flat_vowels,
        "syllables": syllables,
    }


def _score_word_candidate(candidate: Dict[str, object], phonotactic_profile: Dict[str, object]) -> float:
    soft_cfg = phonotactic_profile.get("soft_constraints", {})
    if not isinstance(soft_cfg, dict):
        soft_cfg = {}
    co_occurrence_cfg = phonotactic_profile.get("co_occurrence", {})
    if not isinstance(co_occurrence_cfg, dict):
        co_occurrence_cfg = {}

    initial_velar_nasal_penalty = _clamp_float(soft_cfg.get("initial_velar_nasal_penalty"), 4.0, 0.0, 100.0)
    triple_repeat_penalty = _clamp_float(soft_cfg.get("triple_repeat_penalty"), 2.5, 0.0, 100.0)
    identical_adjacent_penalty = _clamp_float(soft_cfg.get("identical_adjacent_penalty"), 0.65, 0.0, 100.0)
    cluster_violation_penalty = _clamp_float(soft_cfg.get("cluster_violation_penalty"), 1.1, 0.0, 100.0)
    final_complex_coda_penalty = _clamp_float(soft_cfg.get("final_complex_coda_penalty"), 0.42, 0.0, 100.0)
    hiatus_penalty = _clamp_float(soft_cfg.get("hiatus_penalty"), 0.35, 0.0, 100.0)
    onsetless_word_penalty = _clamp_float(soft_cfg.get("onsetless_word_penalty"), 0.18, 0.0, 100.0)
    harmony_penalty = _clamp_float(co_occurrence_cfg.get("harmony_penalty"), 0.3, 0.0, 100.0)

    score = 0.0
    raw_form = str(candidate.get("raw_form", ""))
    if re.search(r"(.)\1\1", raw_form):
        score -= triple_repeat_penalty

    segments = [str(segment) for segment in candidate.get("segments", [])]
    for previous, current in zip(segments, segments[1:]):
        if previous == current:
            score -= identical_adjacent_penalty

    vowels = [str(vowel) for vowel in candidate.get("vowels", [])]
    if bool(co_occurrence_cfg.get("enabled", True)):
        for previous_vowel, current_vowel in zip(vowels, vowels[1:]):
            previous_features = _vowel_features(previous_vowel)
            current_features = _vowel_features(current_vowel)
            if ("front" in previous_features and "back" in current_features) or (
                "back" in previous_features and "front" in current_features
            ):
                score -= harmony_penalty

    syllables_raw = candidate.get("syllables", [])
    syllables: List[Dict[str, object]] = [syllable for syllable in syllables_raw if isinstance(syllable, dict)]

    if syllables and bool(syllables[0].get("starts_with_vowel", False)):
        score -= onsetless_word_penalty

    for left_syllable, right_syllable in zip(syllables, syllables[1:]):
        if bool(left_syllable.get("ends_with_vowel", False)) and bool(right_syllable.get("starts_with_vowel", False)):
            score -= hiatus_penalty

    seen_initial_cluster = False
    for syllable in syllables:
        clusters_raw = syllable.get("clusters", [])
        if not isinstance(clusters_raw, list):
            continue
        for cluster in clusters_raw:
            if not isinstance(cluster, dict):
                continue
            cluster_segments = [str(segment) for segment in cluster.get("segments", [])]
            cluster_type = str(cluster.get("type", ""))
            slot_role = str(cluster.get("slot_role", ""))
            if len(cluster_segments) > 1:
                violations = _count_cluster_sonority_violations(cluster_segments, cluster_type)
                score -= float(violations) * cluster_violation_penalty

            if slot_role == "word_final_coda" and len(cluster_segments) > 1:
                score -= float(len(cluster_segments) - 1) * final_complex_coda_penalty

            if not seen_initial_cluster and slot_role == "word_initial_onset" and cluster_segments:
                seen_initial_cluster = True
                if "velar_nasal" in _segment_classes(cluster_segments[0]):
                    score -= initial_velar_nasal_penalty

    return score


def _choose_scored_candidate(
    scored_candidates: Sequence[Dict[str, object]],
    phonotactic_profile: Dict[str, object],
) -> Optional[Dict[str, object]]:
    if not scored_candidates:
        return None

    candidate_cfg = phonotactic_profile.get("candidate_selection", {})
    if not isinstance(candidate_cfg, dict):
        candidate_cfg = {}
    temperature = _clamp_float(candidate_cfg.get("temperature"), 0.82, 0.05, 4.0)

    scores = [float(candidate.get("score", 0.0)) for candidate in scored_candidates]
    max_score = max(scores)
    weights = [math.exp((score - max_score) / temperature) for score in scores]
    return random.choices(list(scored_candidates), weights=weights, k=1)[0]


def generate_syllable(
    vowels: Sequence[str],
    consonants: Sequence[str],
    style_name: str,
    syllable_position: str = "single",
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
) -> str:
    phonotactic_profile = resolve_phonotactic_profile(
        style_name=style_name,
        phonotactic_profile_overrides=phonotactic_profile_overrides,
    )
    syllable = _generate_syllable_candidate(
        vowels=vowels,
        consonants=consonants,
        style_name=style_name,
        syllable_position=syllable_position,
        phonotactic_profile=phonotactic_profile,
    )
    return str(syllable.get("text", ""))


def generate_word(
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
) -> str:
    phonotactic_profile = resolve_phonotactic_profile(
        style_name=style_name,
        phonotactic_profile_overrides=phonotactic_profile_overrides,
    )
    candidate_cfg = phonotactic_profile.get("candidate_selection", {})
    if not isinstance(candidate_cfg, dict):
        candidate_cfg = {}
    candidate_count = max(1, int(_clamp_float(candidate_cfg.get("candidates_per_word"), 7.0, 1.0, 64.0)))

    scored_candidates: List[Dict[str, object]] = []
    for _ in range(candidate_count):
        candidate = _generate_word_candidate(
            vowels=vowels,
            consonants=consonants,
            syllable_range=syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
            phonotactic_profile=phonotactic_profile,
        )
        candidate["score"] = _score_word_candidate(candidate, phonotactic_profile)
        scored_candidates.append(candidate)

    selected = _choose_scored_candidate(scored_candidates, phonotactic_profile)
    if selected and selected.get("form"):
        return str(selected.get("form", ""))
    return choose_segment(vowels) or choose_segment(consonants) or "a"


def _looks_noisy(form: str) -> bool:
    if not form:
        return True
    compact_form = re.sub(r"[\s.]", "", form)
    return bool(re.search(r"(.)\1\1", compact_form))


def _generate_unique_word(
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    used_forms: Set[str],
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
    morphology_resources: Optional[Dict[str, object]] = None,
    pos: str = "N",
    apply_morphology: bool = False,
) -> str:
    for _ in range(40):
        candidate = generate_word(
            vowels=vowels,
            consonants=consonants,
            syllable_range=syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
            phonotactic_profile_overrides=phonotactic_profile_overrides,
        )
        if apply_morphology:
            candidate = _apply_morphology_to_stem(
                stem=candidate,
                pos=pos,
                morphology_resources=morphology_resources,
                syllable_separator=syllable_separator,
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
        phonotactic_profile_overrides=phonotactic_profile_overrides,
    )
    if apply_morphology:
        fallback = _apply_morphology_to_stem(
            stem=fallback,
            pos=pos,
            morphology_resources=morphology_resources,
            syllable_separator=syllable_separator,
        )
    if fallback in used_forms and (vowels or consonants):
        extra = choose_segment(consonants) or choose_segment(vowels) or "a"
        fallback = f"{fallback}{syllable_separator}{extra}" if syllable_separator else f"{fallback}{extra}"
    used_forms.add(fallback)
    return fallback


def _new_entry(
    entry_id: str,
    ipa: str,
    meaning: str,
    gloss: str,
    pos: str,
    source: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "id": entry_id,
        "ipa": ipa,
        "meaning": meaning,
        "gloss": gloss,
        "pos": pos,
        "source": source,
    }
    if isinstance(extra, dict):
        entry.update(extra)
    return entry


def build_language_model(
    vowels: Sequence[str],
    consonants: Sequence[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
    concept_list_name: str = DEFAULT_CONCEPT_LIST,
    grammar_profile_name: str = DEFAULT_GRAMMAR_PROFILE,
    concept_pack_config: Optional[Dict[str, Any]] = None,
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
) -> Dict[str, Any]:
    root_syllable_range = normalize_range(syllable_range, minimum=1)
    grammar = grammar_profile(grammar_profile_name)
    particle_syllables = normalize_range(tuple(grammar.get("particle_syllables", (1, 1))), minimum=1)
    phonotactic_profile = resolve_phonotactic_profile(
        style_name=style_name,
        phonotactic_profile_overrides=phonotactic_profile_overrides,
    )

    concept_entries = resolve_concept_entries(concept_list_name, concept_pack_config=concept_pack_config)
    used_forms: Set[str] = set()
    lexicon: List[Dict[str, str]] = []
    by_pos: Dict[str, List[Dict[str, str]]] = {}
    particles: Dict[str, Dict[str, str]] = {}
    morphology_resources = _build_morphology_resources(
        vowels=vowels,
        consonants=consonants,
        style_name=style_name,
        syllable_separator=syllable_separator,
        phonotactic_profile_overrides=phonotactic_profile_overrides,
        phonotactic_profile=phonotactic_profile,
    )

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
            phonotactic_profile_overrides=phonotactic_profile_overrides,
            morphology_resources=morphology_resources,
            pos=pos,
            apply_morphology=bool(morphology_resources.get("enabled", False)),
        )
        concept_id = str(concept.get("concept_id", f"core.{index:03d}"))
        source_pack = str(concept.get("source_pack", "core"))
        entry_id = f"ROOT:{concept_id}" if source_pack == "core" else f"PACK:{source_pack}:{concept_id}"
        entry = _new_entry(
            entry_id=entry_id,
            ipa=ipa,
            meaning=meaning,
            gloss=gloss,
            pos=pos,
            source=f"concept-pack:{source_pack}" if source_pack != "core" else f"concept-list:{concept_list_name}",
            extra={
                "concept_id": concept_id,
                "tags": list(concept.get("tags", [])),
                "source_pack": source_pack,
                "register": concept.get("register", "neutral"),
                "biomes": list(concept.get("biomes", [])),
                "tier": concept.get("tier", "core"),
            },
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
            phonotactic_profile_overrides=phonotactic_profile_overrides,
            apply_morphology=False,
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
        "concept_pack_config": _canonicalize_config(concept_pack_config or {}),
        "grammar_profile_name": grammar_profile_name,
        "syllable_range": [root_syllable_range[0], root_syllable_range[1]],
        "syllable_separator": syllable_separator,
        "phonotactic_profile_overrides": _canonicalize_config(phonotactic_profile_overrides or {}),
        "morphology_resources": _canonicalize_config(morphology_resources),
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
    concept_pack_config: Optional[Dict[str, Any]] = None,
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
) -> bool:
    if not isinstance(language_model, dict):
        return False
    expected_min, expected_max = normalize_range(syllable_range, minimum=1)
    inventory = language_model.get("inventory", {})
    if not isinstance(inventory, dict):
        return False
    expected_overrides = _canonicalize_config(phonotactic_profile_overrides or {})
    cached_overrides = language_model.get("phonotactic_profile_overrides")
    if cached_overrides is None:
        cached_overrides = language_model.get("phonotactics_overrides")

    expected_pack_config = _canonicalize_config(concept_pack_config or {})
    cached_pack_config = _canonicalize_config(language_model.get("concept_pack_config", {}))

    return (
        language_model.get("style_name") == style_name
        and language_model.get("concept_list_name") == concept_list_name
        and cached_pack_config == expected_pack_config
        and language_model.get("grammar_profile_name") == grammar_profile_name
        and language_model.get("syllable_separator") == syllable_separator
        and language_model.get("syllable_range") == [expected_min, expected_max]
        and _canonicalize_config(cached_overrides or {}) == expected_overrides
        and inventory.get("vowels") == list(vowels)
        and inventory.get("consonants") == list(consonants)
    )


def reroll_lexicon_entry(
    language_model: Dict[str, Any],
    entry_id: str,
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
) -> Optional[Dict[str, str]]:
    if not isinstance(language_model, dict):
        return None
    if not entry_id:
        return None

    lexicon = language_model.get("lexicon", [])
    if not isinstance(lexicon, list):
        return None

    target_entry: Optional[Dict[str, str]] = None
    for entry in lexicon:
        if isinstance(entry, dict) and str(entry.get("id", "")) == entry_id:
            target_entry = entry
            break
    if target_entry is None:
        return None

    inventory = language_model.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
    vowels = inventory.get("vowels", [])
    consonants = inventory.get("consonants", [])
    if not isinstance(vowels, list):
        vowels = []
    if not isinstance(consonants, list):
        consonants = []

    style_name = str(language_model.get("style_name", DEFAULT_STYLE_PRESET))
    syllable_separator = str(language_model.get("syllable_separator", ""))
    model_syllable_range = language_model.get("syllable_range", [1, 1])
    if not isinstance(model_syllable_range, (list, tuple)) or len(model_syllable_range) != 2:
        model_syllable_range = [1, 1]
    root_syllable_range = normalize_range((int(model_syllable_range[0]), int(model_syllable_range[1])), minimum=1)

    grammar_name = str(language_model.get("grammar_profile_name", DEFAULT_GRAMMAR_PROFILE))
    grammar = grammar_profile(grammar_name)
    particle_syllables = normalize_range(tuple(grammar.get("particle_syllables", (1, 1))), minimum=1)

    model_overrides = language_model.get("phonotactic_profile_overrides")
    if model_overrides is None:
        model_overrides = language_model.get("phonotactics_overrides")
    active_overrides = phonotactic_profile_overrides if phonotactic_profile_overrides is not None else model_overrides

    morphology_resources_raw = language_model.get("morphology_resources", {})
    morphology_resources: Optional[Dict[str, object]]
    if isinstance(morphology_resources_raw, dict):
        morphology_resources = morphology_resources_raw
    else:
        morphology_resources = None

    target_pos = str(target_entry.get("pos", "N"))
    source_label = str(target_entry.get("source", ""))
    is_root_word = source_label.startswith("concept-list:") or source_label.startswith("concept-pack:")
    reroll_range = root_syllable_range if is_root_word else particle_syllables

    used_forms = {
        str(entry.get("ipa", ""))
        for entry in lexicon
        if isinstance(entry, dict) and str(entry.get("id", "")) != entry_id and str(entry.get("ipa", ""))
    }

    new_ipa = _generate_unique_word(
        vowels=vowels,
        consonants=consonants,
        syllable_range=reroll_range,
        syllable_separator=syllable_separator,
        style_name=style_name,
        used_forms=used_forms,
        phonotactic_profile_overrides=active_overrides if isinstance(active_overrides, dict) else None,
        morphology_resources=morphology_resources,
        pos=target_pos,
        apply_morphology=is_root_word and bool(morphology_resources and morphology_resources.get("enabled", False)),
    )
    target_entry["ipa"] = new_ipa
    return target_entry


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
        "id": entry.get("id", ""),
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
    concept_pack_config: Optional[Dict[str, Any]] = None,
    language_model: Optional[Dict[str, Any]] = None,
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
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
            concept_pack_config=concept_pack_config,
            phonotactic_profile_overrides=phonotactic_profile_overrides,
        )

    lexicon = model.get("lexicon", [])
    if not isinstance(lexicon, list):
        lexicon = []

    concept_entries = [
        entry
        for entry in lexicon
        if isinstance(entry, dict) and (
            str(entry.get("source", "")).startswith("concept-list:") or str(entry.get("source", "")).startswith("concept-pack:")
        )
    ]
    concept_entries.sort(key=lambda entry: str(entry.get("id", "")))
    if concept_entries:
        return [_entry_to_word_sample(entry) for entry in concept_entries]

    count = max(1, int(sample_count))
    grammar = grammar_profile(grammar_profile_name)
    pos_weights = grammar.get("sample_word_pos", GRAMMAR_PROFILES[DEFAULT_GRAMMAR_PROFILE]["sample_word_pos"])
    return [
        _entry_to_word_sample(_pick_entry(model, weighted_choice(pos_weights, fallback="N"), fallback_pos=["N", "V", "ADJ", "PART", "PRON"]))
        for _ in range(count)
    ]


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
    concept_pack_config: Optional[Dict[str, Any]] = None,
    language_model: Optional[Dict[str, Any]] = None,
    phonotactic_profile_overrides: Optional[Dict[str, object]] = None,
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
            concept_pack_config=concept_pack_config,
            phonotactic_profile_overrides=phonotactic_profile_overrides,
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


def rebuild_indices(language_model: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild lightweight lookup tables for a persisted language model snapshot."""
    model = dict(language_model)
    lexicon = model.get("lexicon", [])
    if not isinstance(lexicon, list):
        lexicon = []
    model["lexicon"] = lexicon

    by_pos: Dict[str, List[Dict[str, str]]] = {}
    particles: Dict[str, Dict[str, str]] = {}
    for entry in lexicon:
        if not isinstance(entry, dict):
            continue
        pos = str(entry.get("pos", "")).strip()
        if pos:
            by_pos.setdefault(pos, []).append(entry)
        entry_id = str(entry.get("id", ""))
        if entry_id.startswith("PART:") or pos == "PART":
            gloss = str(entry.get("gloss", "") or entry_id.replace("PART:", "")).upper()
            particles[gloss] = entry

    model["by_pos"] = by_pos
    model["particles"] = particles
    return model
