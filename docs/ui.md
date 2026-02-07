# Desktop UI

## Layout

The desktop app uses a three-panel workspace:

- **Left panel:** Tree navigation and language search.
- **Center panel:** Create, Compare, and Details workflows.
- **Right panel:** Contextual help and inspector content.

## Tree

The tree is rendered with Cytoscape.js and supports:

- Click to select a language.
- Highlighted lineage from root to selection.
- Zoom and pan for larger families.

## Live previews

Changes to sound rules update inventory diffs and lexicon samples immediately. Saving is explicit so users can explore without committing.

## Help system

Every control can publish a help topic key. The right panel renders the matching help text from a registry file so guidance stays consistent across the app.
