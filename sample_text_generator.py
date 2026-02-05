"""Word and sentence sample generation utilities."""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

STYLE_PRESETS: Dict[str, Dict[str, object]] = {
    "Balanced": {
        "description": "Neutral blend of short and medium words.",
        "syllable_shapes": [("V", 0.10), ("CV", 0.40), ("VC", 0.12), ("CVC", 0.23), ("CVV", 0.08), ("VCV", 0.07)],
        "punctuation": [(".", 0.75), ("?", 0.15), ("!", 0.10)],
        "particle_rate": 0.08,
        "particle_syllables": (1, 1),
    },
    "Clipped": {
        "description": "Short, punchy cadence with tighter consonant-heavy chunks.",
        "syllable_shapes": [("CV", 0.35), ("CVC", 0.38), ("VC", 0.15), ("V", 0.05), ("CVV", 0.04), ("VCV", 0.03)],
        "punctuation": [(".", 0.70), ("!", 0.20), ("?", 0.10)],
        "particle_rate": 0.03,
        "particle_syllables": (1, 1),
    },
    "Flowing": {
        "description": "Smoother rhythm with more open syllables and vowel sequences.",
        "syllable_shapes": [("V", 0.16), ("CV", 0.44), ("VC", 0.06), ("CVC", 0.10), ("CVV", 0.16), ("VCV", 0.08)],
        "punctuation": [(".", 0.80), ("?", 0.12), ("!", 0.08)],
        "particle_rate": 0.06,
        "particle_syllables": (1, 2),
    },
    "Particle-rich": {
        "description": "Adds frequent short particles for a more grammaticalized surface feel.",
        "syllable_shapes": [("V", 0.10), ("CV", 0.36), ("VC", 0.10), ("CVC", 0.20), ("CVV", 0.12), ("VCV", 0.12)],
        "punctuation": [(".", 0.72), ("?", 0.18), ("!", 0.10)],
        "particle_rate": 0.45,
        "particle_syllables": (1, 1),
    },
}


def weighted_choice(weighted_items: List[Tuple[str, float]], fallback: str) -> str:
    """Choose one label from weighted items, with fallback if invalid."""
    valid = [(label, weight) for label, weight in weighted_items if weight > 0]
    if not valid:
        return fallback
    labels = [label for label, _ in valid]
    weights = [weight for _, weight in valid]
    return random.choices(labels, weights=weights, k=1)[0]


def style_profile(style_name: str) -> Dict[str, object]:
    """Return style config with balanced fallback."""
    return STYLE_PRESETS.get(style_name, STYLE_PRESETS["Balanced"])


def choose_segment(segments: List[str]) -> str:
    """Return a random segment, or empty string if unavailable."""
    if not segments:
        return ""
    return random.choice(segments)


def generate_syllable(vowels: List[str], consonants: List[str], style_name: str) -> str:
    """Generate a syllable-like chunk from the current inventory."""
    if not vowels and not consonants:
        return ""

    if not consonants:
        shape_weights = [("V", 0.75), ("VV", 0.25)]
        shape = weighted_choice(shape_weights, fallback="V")
    elif not vowels:
        shape_weights = [("C", 0.85), ("CC", 0.15)]
        shape = weighted_choice(shape_weights, fallback="C")
    else:
        profile = style_profile(style_name)
        shape_weights = profile.get("syllable_shapes", STYLE_PRESETS["Balanced"]["syllable_shapes"])
        shape = weighted_choice(shape_weights, fallback="CV")

    parts: List[str] = []
    for slot in shape:
        segment = choose_segment(consonants) if slot == "C" else choose_segment(vowels)
        if segment:
            parts.append(segment)
    return "".join(parts)


def generate_word(
    vowels: List[str],
    consonants: List[str],
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
) -> str:
    """Generate a placeholder word made from inventory segments."""
    min_syllables, max_syllables = syllable_range
    min_syllables = max(1, int(min_syllables))
    max_syllables = max(min_syllables, int(max_syllables))

    syllable_count = random.randint(min_syllables, max_syllables)
    syllables = [generate_syllable(vowels, consonants, style_name=style_name) for _ in range(syllable_count)]
    syllables = [syllable for syllable in syllables if syllable]

    if not syllables:
        return choose_segment(vowels) or choose_segment(consonants) or "a"
    return syllable_separator.join(syllables)


def generate_sentence(
    vowels: List[str],
    consonants: List[str],
    syllable_range: Tuple[int, int],
    words_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
) -> str:
    """Generate a placeholder sentence from inventory-derived words."""
    min_words, max_words = words_range
    min_words = max(1, int(min_words))
    max_words = max(min_words, int(max_words))

    word_count = random.randint(min_words, max_words)
    words = [
        generate_word(
            vowels,
            consonants,
            syllable_range=syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
        )
        for _ in range(word_count)
    ]

    profile = style_profile(style_name)
    particle_rate = float(profile.get("particle_rate", 0.0))
    particle_syllables = profile.get("particle_syllables", (1, 1))
    if random.random() < particle_rate:
        words.append(
            generate_word(
                vowels,
                consonants,
                syllable_range=particle_syllables,
                syllable_separator=syllable_separator,
                style_name=style_name,
            )
        )

    punctuation_weights = profile.get("punctuation", STYLE_PRESETS["Balanced"]["punctuation"])
    punctuation = weighted_choice(punctuation_weights, fallback=".")
    return f"{' '.join(words)}{punctuation}"


def build_sample_words(
    vowels: List[str],
    consonants: List[str],
    sample_count: int,
    syllable_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
) -> List[str]:
    """Return a list of generated placeholder words."""
    count = max(1, int(sample_count))
    return [
        generate_word(
            vowels,
            consonants,
            syllable_range=syllable_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
        )
        for _ in range(count)
    ]


def build_sample_sentences(
    vowels: List[str],
    consonants: List[str],
    sample_count: int,
    syllable_range: Tuple[int, int],
    words_range: Tuple[int, int],
    syllable_separator: str,
    style_name: str,
) -> List[str]:
    """Return a list of generated placeholder sentences."""
    count = max(1, int(sample_count))
    return [
        generate_sentence(
            vowels,
            consonants,
            syllable_range=syllable_range,
            words_range=words_range,
            syllable_separator=syllable_separator,
            style_name=style_name,
        )
        for _ in range(count)
    ]
