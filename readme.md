# Sound Inventory Generator

Generate plausible phoneme inventories by mixing language presets, adding optional random segments, and applying optional sound-change rules.

## What this project does

- Loads preset inventories from `presets/*.json`.
- Mixes selected presets with user-defined weights.
- Optionally adds random segments from a master preset (default: `random_master`).
- Optionally applies rule sets from `rules/*.json`.
- Exports:
  - a JSON inventory (`<name>.json`)
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
- generate and preview vowels/consonants,
- save outputs to an output folder,
- save the latest result as a reusable preset in `presets/`.
