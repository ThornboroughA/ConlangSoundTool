# Sound Inventory Generator

Generate plausible phoneme inventories by mixing language presets, adding optional random segments, and applying optional sound-change rules.

## What this project does

- Loads preset inventories from `presets/*.json`.
- Mixes selected presets with user-defined weights.
- Samples each preset's segments using per-segment `representation` weights (if present).
- Optionally adds random segments from a master preset (default: `random_master`).
- Optionally applies rule sets from `rules/*.json`.
- Exports:
  - a JSON inventory (`<name>.json`, including sampled representation traces)
  - minimal CLDF-style CSV files (`languages.csv`, `inventories.csv`, `values.csv`)

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

Presets now support weighted segment entries:

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

## Simple UI usage (Streamlit)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the UI:

```bash
streamlit run app.py
```

3. In the UI you can:

- choose presets and weights,
- set random weight and master preset,
- apply rule sets,
- view source-sound mixing guides and sound-like hints anywhere IPA is shown,
- generate and preview vowels/consonants,
- generate lexicon-backed sample words/sentences from the latest inventory (with phonotactic styles, concept lists, grammar profiles, POS tags, and gloss hints),
- get validation feedback for concept/grammar/style profile definitions while iterating,
- save outputs to an output folder,
- save the latest result as a reusable preset in `presets/`.
