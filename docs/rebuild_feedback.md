# Rebuild Feedback: Conlang Sound Toolkit

Date: February 10, 2026

This note captures my feedback on the current project and how I would approach a ground-up rebuild. It’s intended as a planning reference, not a spec.

## Key Takeaways From This Build

- “Language” is effectively a surface snapshot (inventory + lexicon + config). There’s no clear separation between underlying representation, phonological processes, and surface realization. This makes iteration and propagation of edits hard.
- Sound change is mostly segment substitution without context. The current approach doesn’t model environment, ordering effects, assimilation, epenthesis, or mergers/splits, so daughter languages feel flat.
- Phonotactics and “feel” are driven by syllable templates and soft constraints. This is a good direction, but it still sits on top of a randomized generator, which makes outputs feel arbitrary.
- The lexicon is concept-list based with random wordforms. There’s limited morphology and no deep etymology tracking, so family resemblance is shallow.
- The UI owns too much logic. `app.py` is large, while `core/` is mostly unused, which makes a platform swap harder than it should be.

## What I Would Keep

- The romanization system. The IPA → romanization mapping and fallback logic are strong and should become a dedicated orthography layer.
- The source-profile idea (sidecars + soft phonotactic profiles). This is conceptually right and should be promoted to a first-class layer.
- A Swadesh-style seed lexicon is still a good anchor, especially if it becomes a root inventory supporting derivation and historical tracking.

## A Better Underlying Model (Language As Layers)

Think of “language” as a layered system with explicit interfaces rather than a single snapshot.

1. Phonological system
- Phoneme inventory as features, not just symbols.
- Allophony and processes as rules mapping underlying to surface forms.
- Prosody as first-class: stress, syllable weight, tone, position effects.

2. Phonotactics as a formal grammar
- Replace CV template + soft penalties with a formal grammar (weighted constraints or finite-state patterns).
- Let “style presets” drive parameterized rules rather than template weights alone.

3. Lexicon as roots + morphology + etymology
- Start with a root inventory tied to concepts, not just surface wordforms.
- Add affixation, compounding, derivation, and inflection.
- Track etymology for each lexeme so daughter languages inherit roots and transform them.

4. Language recipe vs. language snapshot
- Store a “recipe” (inputs + rules + timeline) and a “snapshot” (current surface state).
- Allow regenerating snapshots from a modified recipe without losing curated overrides.

## Sound Change Engine: What Needs Rethinking

- Use a rule language with context, feature classes, and ordering.
- Handle insertions and deletions explicitly, not just replacement.
- Track mergers and splits, and support chain shifts.
- Add optional lexical diffusion for irregularity.
- Update phonotactics as sound change proceeds so constraints don’t become obsolete.

## Family and Contact

- Model family relationships as a graph, not just a tree. Borrowings and contact effects should be normal, not hacks.
- A daughter language should inherit a parent’s lexicon and apply changes, then add contact-driven borrowings and lexical replacement.

## Why Outputs Feel Off Right Now

- Inventory mixing + template-driven wordform generation lacks the “middle layers” that shape real language systems.
- Sound change mostly alters symbols, not word structure or morphosystem, so family cohesion is weak.

## How I’d Start a Clean Rebuild

1. Define a minimal data model for Language Recipe vs Language Snapshot.
2. Choose a formalism for feature-aware, ordered sound-change rules.
3. Build a root lexicon with morphology hooks and etymology tracking.
4. Design the UI around the pipeline (design → evolve → compare → iterate), not the other way around.

## Optional Next Steps

- Draft a minimal language schema for phonology, phonotactics, lexicon, morphology, orthography, etymology.
- Sketch a sound-change DSL and a timeline representation.
- Outline a UI/UX flow that reflects the new pipeline (see `docs/uiux_family_first_flow.md`).
