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

## PHOIBLE import weighting model

When importing presets from PHOIBLE in the UI:

- PHOIBLE CSV does not provide within-language token frequency values.
- The importer uses a typological prior based on cross-inventory prevalence per `GlyphID`.
- Base score: `log1p(prevalence_count)`.
- Scores are normalized separately for vowels and consonants so each class has mean `1.0`.
- Core and marginal slider values act as multipliers on top of this normalized prior.

This keeps the preset JSON format unchanged while avoiding flat `1.0` representations for every segment.
