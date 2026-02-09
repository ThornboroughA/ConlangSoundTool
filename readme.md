# Conlang Sound Toolkit

Build phonology-driven languages, generate lexicons with custom words, and evolve daughter languages via sound changes.

## What this project does

- Mix preset inventories to generate a phoneme inventory.
- Apply sound-change rule sets.
- Generate lexicon-backed word and sentence samples from concept lists, grammar profiles, and phonotactic styles.
- Add, edit, delete, and re-roll custom lexicon entries.
- Build language families, define sound-change templates, and compare parent/child lexica.
- Export presets, pronunciation guides, lexicon CSVs, and full snapshots.
- Import PHOIBLE inventories into presets.

## UI usage (Streamlit)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the UI:

```bash
streamlit run app.py
```

3. In the UI you can:

- configure inventories and rules,
- review vowels and consonants with sound-like hints,
- generate lexicon-backed word and sentence samples,
- create custom words and curate the full lexicon,
- export presets, lexicon CSVs, and snapshot JSONs,
- build and compare language families.

## CLI usage

```bash
python sound_inventory_generator.py \
  --presets english korean \
  --weights 0.4 0.6 \
  --random-weight 0.1 \
  --rules demo_shift \
  --name MyLang \
  --output outputs/mylang
```

## Preset format

Presets support weighted segment entries:

```json
{
  "name": "ExampleLang",
  "vowels": [
    {"segment": "i", "representation": 1.8},
    {"segment": "a", "representation": 1.0}
  ],
  "consonants": [
    {"segment": "t", "representation": 1.6},
    {"segment": "k", "representation": 0.7}
  ]
}
```

`representation` controls how likely a segment is to be sampled when mixing. Larger values make a segment more likely to appear in generated inventories. Values are relative and do not need to sum to 1.

Legacy list format (e.g. `"vowels": ["i", "a"]`) still works and is treated as `representation: 1.0` for each segment.

## Source profile sidecars (optional)

You can add an optional sidecar next to any preset:

- `presets/<preset_name>.profile.json`

Sidecars are non-breaking: if a sidecar is missing, generation falls back to current inventory-derived behavior.

Practical starting points:

- Authoring guide: `docs/source_profile_guide.md`
- Reusable template: `presets/source_profile_template.profile.json`
- Auto-bootstrap script: `tools/build_source_profile_from_wordlist.py`
- Build-tab starter presets (built in): pick one as fallback when selected sources have no sidecar.

Built-in starter profile options include:

- `Balanced Global`
- `Open Syllable`
- `Coda Heavy`
- `Cluster Rich`
- `Harmony Leaning`
- `Sonorant Flow`
- `Stop Leaning`
- `Fricative Leaning`
- `Moraic Light`
- `Compact Mix`

Quick workflow:

1. Copy `presets/source_profile_template.profile.json` to `presets/<preset_name>.profile.json`.
2. Replace the `provenance` text and tune `template_weights_by_position` first.
3. Tune `segment_frequency` second.
4. Optionally tune `co_occurrence`, `soft_constraints`, and `cluster`.
5. Generate samples and iterate.

When mixing presets, the Build tab can apply a chosen starter profile only to sources that lack
`<preset>.profile.json`. Existing sidecars still take priority.

Supported sidecar schema:

```json
{
  "version": 1,
  "provenance": ["Source citation"],
  "segment_frequency": {
    "vowel_weights": {"a": 1.2, "i": 0.9},
    "consonant_weights": {"t": 1.1, "k": 0.8}
  },
  "template_weights_by_position": {
    "single": [["CV", 0.55], ["CVC", 0.45]],
    "initial": [["CV", 0.6], ["CCV", 0.4]],
    "medial": [["CV", 0.7], ["VC", 0.3]],
    "final": [["CVC", 0.65], ["VC", 0.35]]
  },
  "slot_class_weights": {"coda": {"nasal": 1.2, "stop": 0.8}},
  "co_occurrence": {"front_back_harmony_bonus": 1.1},
  "soft_constraints": {"hiatus_penalty": 0.3},
  "cluster": {"violation_penalty": 0.25}
}
```

Notes:

- Segment maps are normalized to mean `1.0` per class.
- Template weights are normalized to sum `1.0` per position.
- Sidecar tendencies are soft/probabilistic; no hard allow/deny constraints are used.

## PHOIBLE import representation defaults

When importing presets from PHOIBLE in the UI:

- Imported core segments default to `representation: 1.0`.
- Imported marginal segments use the marginal multiplier.
- You can adjust both with the importer sliders, then manually edit `representation` values later in preset JSON files.

This keeps the preset JSON format unchanged and makes PHOIBLE import behavior deterministic and easy to tune.

## Build a sidecar from a wordlist

Use the helper script to derive a source profile from IPA wordlist data:

```bash
python tools/build_source_profile_from_wordlist.py \
  --input data/japanese_wordlist.tsv \
  --ipa-column ipa \
  --delimiter auto \
  --output presets/japanese_197.profile.json
```

The script estimates:

- segment frequency weights (vowels/consonants), and
- syllable template distributions by position (`single`, `initial`, `medial`, `final`).
