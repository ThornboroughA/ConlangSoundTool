# Source Profile Authoring Guide

This guide explains how to create `*.profile.json` sidecars for presets.

## What a source profile does

A source profile is an optional sidecar file loaded automatically when its basename matches a preset.

- Preset: `presets/korean_1.json`
- Sidecar: `presets/korean_1.profile.json`

The sidecar influences sample generation with soft tendencies. It does not hard-ban forms.

## Quick start (manual)

1. Copy `presets/source_profile_template.profile.json`.
2. Rename it to match your preset basename, for example `presets/my_lang.profile.json`.
3. Edit only `provenance`, `segment_frequency`, and `template_weights_by_position` first.
4. Generate samples and tune gradually.

## Built-in starters in UI

The Build tab includes starter source-profile presets you can apply as fallback for sources
without sidecars:

- Balanced Global
- Open Syllable
- Coda Heavy
- Cluster Rich
- Harmony Leaning
- Sonorant Flow
- Stop Leaning
- Fricative Leaning
- Moraic Light
- Compact Mix

This fallback is only used when a selected source has no matching `*.profile.json`.
If a sidecar exists, it wins.

## Quick start (from a wordlist)

If you have IPA wordlist data, bootstrap a profile automatically:

```bash
python tools/build_source_profile_from_wordlist.py \
  --input data/my_language_wordlist.tsv \
  --ipa-column ipa \
  --delimiter auto \
  --output presets/my_lang.profile.json
```

Then hand-tune optional sections (`slot_class_weights`, `co_occurrence`, `soft_constraints`, `cluster`).

## Schema

```json
{
  "version": 1,
  "provenance": ["Source notes"],
  "segment_frequency": {
    "vowel_weights": {"a": 1.2, "i": 0.9},
    "consonant_weights": {"t": 1.1, "k": 0.8}
  },
  "template_weights_by_position": {
    "single": [["CV", 0.55], ["CVC", 0.45]],
    "initial": [["CV", 0.60], ["CCV", 0.40]],
    "medial": [["CV", 0.65], ["VC", 0.35]],
    "final": [["CVC", 0.65], ["VC", 0.35]]
  },
  "slot_class_weights": {
    "coda": {"nasal": 1.2, "stop": 0.8}
  },
  "co_occurrence": {"front_back_harmony_bonus": 1.1},
  "soft_constraints": {"hiatus_penalty": 0.3},
  "cluster": {"violation_penalty": 0.25}
}
```

## How values are interpreted

- `segment_frequency`:
  - Per-class maps are normalized to mean `1.0`.
  - Values above `1.0` increase relative selection, below `1.0` decrease it.
- `template_weights_by_position`:
  - Supported positions: `single`, `initial`, `medial`, `final`.
  - Each position is normalized to sum `1.0`.
  - Template labels must match `C`/`V` patterns like `CV`, `CVC`, `CCV`, `CVCC`.
- `slot_class_weights`:
  - Optional multipliers by slot role and consonant class.
  - Slot roles: `onset`, `word_initial_onset`, `medial`, `coda`, `word_final_coda`.
  - Classes: `stop`, `affricate`, `fricative`, `nasal`, `velar_nasal`, `liquid`, `glide`, `unknown`.
- `co_occurrence`:
  - Optional soft multipliers for segment interactions.
  - Common keys: `front_back_harmony_bonus`, `front_back_harmony_penalty`, `palatal_front_bonus`, `palatal_back_penalty`, `dorsal_back_bonus`, `dorsal_front_penalty`, `labial_rounded_bonus`, `harmony_penalty`.
- `soft_constraints`:
  - Optional penalties/bonuses in candidate scoring.
  - Common keys: `initial_velar_nasal_penalty`, `triple_repeat_penalty`, `identical_adjacent_penalty`, `cluster_violation_penalty`, `final_complex_coda_penalty`, `hiatus_penalty`, `onsetless_word_penalty`.
- `cluster`:
  - Optional cluster-generation behavior.
  - Common keys: `max_attempts`, `allow_identical_adjacent`, `rise_bonus`, `fall_bonus`, `medial_change_bonus`, `s_stop_bonus`, `violation_penalty`.

## Practical tuning ranges

Use these as a conservative starting point:

- Frequency/style multipliers: `0.7` to `1.4`
- Strong but still plausible pushes: `0.5` to `1.8`
- Penalties:
  - `hiatus_penalty`: `0.1` to `0.8`
  - `cluster_violation_penalty`: `0.6` to `1.8`
  - `initial_velar_nasal_penalty`: `2.0` to `6.0`

Extreme values are allowed but tend to make outputs feel artificial.

## Recommended workflow

1. Start with automatic bootstrap from a wordlist or the template.
2. Tune `template_weights_by_position` first for syllable feel.
3. Tune `segment_frequency` next for inventory flavor.
4. Tune `soft_constraints` and `co_occurrence` lightly for polish.
5. Keep a short `provenance` list so future edits are traceable.

## Troubleshooting

- Sidecar not applied:
  - Ensure basename match: `my_lang.json` and `my_lang.profile.json`.
  - Ensure valid JSON (no trailing commas).
- Profile appears ignored:
  - Invalid/non-positive entries are sanitized away.
  - Check the Samples tab caption for active source profile sections.
  - Open `Source profile mix debug` in Samples to confirm per-source shares and origins.
- Templates not taking effect:
  - Labels must be `C`/`V` strings only (for example `CV`, `CVC`, `CVCC`).
