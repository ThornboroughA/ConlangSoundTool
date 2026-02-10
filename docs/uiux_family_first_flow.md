# Family-First UI/UX Flow (Pipeline-Oriented)

Date: February 10, 2026

This document sketches a UI/UX flow that matches the *pipeline* we actually want: building coherent language families over time, with reversible iteration and strong lineage context.

## Frame Of Thought (How To Think While Designing The UI)

- A “project” is a **family simulator + editor**, not a single-language generator.
- The user’s job is closer to **historical linguist / worldbuilder** than “randomizer operator.”
- Always separate **Recipe** (what should happen) from **Snapshot** (what it currently produced).
- Everything happens on a **timeline**; if time isn’t visible, coherence will feel accidental.
- The UX should reward adding constraints and structure.
- The UX should reward inspecting consequences.
- The UX should reward iterating with confidence.
- The UX should reward provenance (why this is the way it is).

## Core Objects (What The UI Is Really Editing)

- **Family Graph**: nodes = languages; edges = descent or contact.
- **Language Recipe**: phonology + phonotactics + morphology + lexicon strategy + orthography rules + timeline events.
- **Language Snapshot**: realized inventory, realized lexicon, samples, stats; “rendered” at a specific time.
- **Timeline Event**: sound changes, contact/borrowing, lexical replacement, phonotactic shifts, morphological reanalysis.
- **Lexeme**: meaning + POS + underlying form(s) + surface forms per language/time + etymology.

UX implication: the UI should make it hard to confuse “I edited the snapshot” with “I edited the recipe.”

## Navigation Model (Top-Level)

One clean mental model is a left sidebar with these primary spaces:

- `Family`: graph, timeline, health checks, global constraints.
- `Proto`: define proto recipe, generate proto snapshot.
- `Evolve`: apply events over time, branch generation, contact events.
- `Compare`: correspondences, innovations, lexicon diffs, collision/merger reports.
- `Lexicon`: meanings, roots, derivations, borrowing ledger, semantic drift.
- `Orthography`: romanization/orthographies, per-language, per-era.
- `Export`: packs for writing (names lists, dictionaries, atlas pages).

## Pipeline Flow (Family-First)

### 1) Create Family Project

Goal: set global constraints so everything downstream feels like it belongs together.

UI flow:

1. `Family → New Project`
2. Choose: time depth (years); branching style (tree vs mostly-tree with contact); realism knobs (innovation rate, borrowing rate, irregularity).
3. Define global “family identity” constraints: allowable phonation/places (feature bounds); prosody defaults (stress/tone presence); phonotactic complexity bounds (max onset/coda complexity).
4. Result: an empty family graph with a proto placeholder and a visible time axis.

Key UX elements:

- A **timeline bar** is always visible.
- A **family coherence scorecard** exists early (even if naive) to orient the user.

### 2) Build The Proto (Recipe First, Then Snapshot)

Goal: create a proto that has *structure* (roots + system), not just surface words.

UI flow:

1. `Proto → Phonology`: pick feature bounds (or seed from sources), choose phonemes, optionally add allophony.
2. `Proto → Phonotactics`: choose a syllable grammar preset, edit it, confirm position-sensitive word-shape distributions.
3. `Proto → Lexicon Strategy`: choose seed concept list, choose root policy (roots + derivation vs unanalyzed words), choose morphology starter (affix pools, compounding rate).
4. `Proto → Generate Snapshot`: generate lexicon + samples, then run health checks (collisions, ugly clusters, overuse of segments, homophony rate).
5. `Proto → Curate`: accept/reject rerolls at the **root/lexeme** level, tag notes, lock items that must remain stable.

Key UX element:

- A clear distinction between `Regenerate Snapshot` (safe, repeatable) and `Edit Recipe` (structural).

### 3) Plan The Family Before Generating Daughters

Goal: avoid “50 random daughters.” Generate a plan that encodes intended coherence.

UI flow:

1. `Family → Plan`: choose number of branches/regions; optionally place languages into “areas” (geography or social network).
2. Define shared innovations and areal pressures as first-class plans (examples: “Branch A develops vowel harmony”; “Coastal sprachbund prefers open syllables + loan phonemes”).
3. Result: a graph with labeled clades/areas and empty timelines.

Key UX element:

- Branch planning is editable without forcing immediate generation.

### 4) Evolve (Timeline Events, Not Just Sound Changes)

Goal: daughters are coherent because they inherit roots and then undergo *events*.

UI flow:

1. `Evolve → Select Edge/Branch`
2. Add events along the edge timeline: sound change stages; phonotactic shifts; borrowing/contact injections; lexical replacement waves; morphological reanalysis events.
3. For each event, preview impact on inventory, correspondences, lexicon samples, and collision/merger risk.
4. When satisfied, `Commit Event` (updates the recipe timeline) and `Render Snapshot` (produces the snapshot at that time).

Key UX element:

- Events are visible “cards” on a timeline, reorderable, toggleable, and inspectable.

### 5) Compare (Make Coherence Visible)

Goal: coherence should be something you can see and measure, not a vibe.

UI flow:

1. `Compare → Proto vs Selected`: correspondence table (by segment class) plus example cognate sets.
2. `Compare → Clade View`: shared innovations plus per-branch signature changes.
3. `Compare → Etymology Lens`: pick a meaning and see the lineage of forms across time.
4. `Compare → Alerts`: suspicious homophony clusters, excessive irregularity, too-similar siblings.

Key UX element:

- A “family atlas” view that feels like linguistics output: isogloss-like overlays, innovation badges, cognate-set drill-down.

### 6) Lexicon Workshop (Roots, Derivation, Borrowing)

Goal: family-level realism comes from how words relate, not just how they sound.

UI flow:

- `Lexicon → Meaning Table`: stable concept list expanded over time; per-language lexical replacement tracking.
- `Lexicon → Root Inventory`: manage roots and derivations; attach derivational patterns that are inheritable and evolvable.
- `Lexicon → Borrowing Ledger`: add borrowings as explicit events; control adaptation rules (loan phonology).

Key UX element:

- Borrowing is an event with provenance, not a manual edit hidden in a lexicon cell.

### 7) Orthography + Presentation

Goal: support writing use-cases (names, places, glossed samples) without corrupting the linguistic core.

UI flow:

- `Orthography → Profiles`: per-language and per-era romanization/orthography; preview “sound-like” output.
- `Export → Writing Packs`: name lists by semantic category; mini-dictionaries; family tree pages with example correspondences.

## Interaction Patterns That Preserve Sanity

- **Dirty/Derived indicators**: show when a snapshot is out-of-date relative to its recipe timeline.
- **Regenerate scopes**: regenerate a wordform, regenerate a lexicon, regenerate a language snapshot, regenerate a subtree.
- **Locks**: lock a root, a lexeme, a rule, or an event so regeneration can’t erase authorial decisions.
- **Provenance everywhere**: every event, borrowing, and override has a note and timestamp.

## Coherence Levers (Family-First Knobs Worth Surfacing)

- Shared-innovation templates per clade (phonology, phonotactics, morphology).
- Contact zones that bias loan rates.
- Contact zones that bias phonotactic convergence.
- Contact zones that bias specific feature pressures (for example: harmony, coda loss).
- Lexical replacement as waves (domain-targeted, not uniform randomness).
- Irregularity budget (controlled drift rather than chaotic noise).

## Anti-Patterns To Avoid

- Treating daughters as re-generated independent languages; they must inherit and transform.
- Letting the UI encourage randomization before structure.
- Hiding time; if time isn’t visible, “deep-time plausibility” becomes unattainable.
- Making manual edits that don’t get recorded as events or overrides.

## A Practical Design North Star

At any point, the user should be able to answer:

- “Where did this form come from?”
- “What events caused this difference?”
- “If I change this earlier rule, what downstream changes, and what stays locked?”
- “What makes this clade feel like a clade?”
