export type HelpTopic = {
  title: string;
  body: string[];
};

const helpRegistry: Record<string, HelpTopic> = {
  tree: {
    title: "Language Tree",
    body: [
      "Select a node to focus the workspace.",
      "The tree highlights the lineage of the selected language.",
      "Use the search box to jump to a language by name or ID.",
    ],
  },
  parent_select: {
    title: "Parent Selection",
    body: [
      "Choose the parent language for the new daughter.",
      "Inherited settings are copied from the parent by default.",
      "You can override settings in the next steps.",
    ],
  },
  inventory_diff: {
    title: "Inventory Diff",
    body: [
      "Shows which segments were added or removed.",
      "This updates live as you edit sound-change rules.",
    ],
  },
  default: {
    title: "Help",
    body: [
      "Select any control to see focused guidance.",
      "This panel updates as you move through the workflow.",
    ],
  },
};

export default helpRegistry;
