# UI/UX Bible

This document defines the intended user flow and layout for the family-first conlang builder. It is the reference for future UI work to keep the experience consistent and extensible.

## Core Flow

1. **Start**  
   Create a proto language quickly with minimal required inputs. Advanced controls live in a collapsible panel.

2. **Enrich**  
   Add cultural meaning via concept packs and expand the proto lexicon. This is where all future meaning systems should live.

3. **Family**  
   Explore the tree, create daughter languages, and inspect language details.

Administrative tasks are separated into **Manage** and **Export** tabs so they never interrupt the creative flow.

## Design Principles

- **Start must be effortless.** A new user should generate a proto in under a minute.
- **Advanced is always collapsible.** Power exists, but never blocks the first success.
- **Admin is separate.** Project management and export/import do not belong in the core creation steps.
- **Families are the default.** No single-language mode is exposed to the user.

## Extensibility Model

All future \"meaning\" expansions belong in the **Enrich** tab as new sections. Do not bolt them onto Start or Family. This keeps the flow stable while the cultural layer grows.

## Visual Rules

- Clearly mark **Required** vs **Advanced** areas.
- Use coverage meters and warnings to guide concept-pack completeness.
- Always show a light preview after proto generation.

## Tab Responsibilities

- **Start:** phonology setup, proto generation, light preview.
- **Enrich:** concept packs, culture notes, lexicon expansion.
- **Family:** tree navigation, daughter creation, language details.
- **Manage:** create/load/save/clear projects.
- **Export:** project and language exports, ZIP import.
