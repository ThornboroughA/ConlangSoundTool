import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../../services/apiClient";

type WorkspacePanelProps = {
  selectedId: string | null;
  workspace: "create" | "compare" | "details";
  onWorkspaceChange: (value: "create" | "compare" | "details") => void;
  onHelp: (topic: string) => void;
  projectId: string;
  languages: Record<string, any>;
  onSelect: (id: string) => void;
  onRefresh: () => void;
};

type PresetResponse = {
  style_presets: string[];
  concept_lists: string[];
  grammar_profiles: string[];
  defaults: {
    style_name: string;
    concept_list_name: string;
    grammar_profile_name: string;
  };
};

type TemplateResponse = {
  templates: string[];
};

type DiffResponse = {
  added_vowels: string[];
  removed_vowels: string[];
  added_consonants: string[];
  removed_consonants: string[];
};

type PreviewResponse = {
  language: any;
  diff: DiffResponse;
  summary?: { rule_count: number; diff: DiffResponse };
  lexicon_preview?: { id: string; parent_ipa: string; child_ipa: string; meaning: string }[];
};

type CompareResponse = {
  diff: DiffResponse;
  lexicon_preview: { id: string; parent_ipa: string; child_ipa: string; meaning: string }[];
};

type Rule = {
  from: string;
  to: string;
  enabled: boolean;
  notes: string;
};

const sanitizeId = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/^_+|_+$/g, "") || "language";

const suggestUniqueId = (base: string, existing: string[]) => {
  const normalized = sanitizeId(base);
  if (!existing.includes(normalized)) return normalized;
  let counter = 1;
  while (counter < 1000) {
    const candidate = `${normalized}_${String(counter).padStart(2, "0")}`;
    if (!existing.includes(candidate)) return candidate;
    counter += 1;
  }
  return `${normalized}_${Date.now()}`;
};

const cleanRules = (rules: Rule[]) => {
  const cleaned: Rule[] = [];
  const warnings: string[] = [];
  const seen = new Set<string>();
  rules.forEach((rule) => {
    const fromValue = rule.from.trim();
    if (!fromValue) {
      warnings.push("Missing 'from' value.");
      return;
    }
    if (seen.has(fromValue)) {
      warnings.push(`Duplicate rule for '${fromValue}'.`);
      return;
    }
    seen.add(fromValue);
    cleaned.push({
      from: fromValue,
      to: rule.to.trim(),
      enabled: rule.enabled,
      notes: rule.notes,
    });
  });
  return { cleaned, warnings: Array.from(new Set(warnings)) };
};

export default function WorkspacePanel({
  selectedId,
  workspace,
  onWorkspaceChange,
  onHelp,
  projectId,
  languages,
  onSelect,
  onRefresh,
}: WorkspacePanelProps) {
  const languageIds = useMemo(() => Object.keys(languages).sort(), [languages]);
  const activeId = selectedId && languages[selectedId] ? selectedId : languageIds[0] ?? null;
  const activeLanguage = activeId ? languages[activeId] : null;

  const [presetData, setPresetData] = useState<PresetResponse | null>(null);
  const [templateOptions, setTemplateOptions] = useState<string[]>([]);

  useEffect(() => {
    apiGet<PresetResponse>("/meta/presets").then(setPresetData).catch(() => setPresetData(null));
    apiGet<TemplateResponse>("/meta/templates")
      .then((data) => setTemplateOptions(data.templates ?? []))
      .catch(() => setTemplateOptions([]));
  }, []);

  // Create Daughter state
  const [parentId, setParentId] = useState<string>("");
  const [childName, setChildName] = useState<string>("");
  const [childId, setChildId] = useState<string>("");
  const [childYear, setChildYear] = useState<number>(100);
  const [childNotes, setChildNotes] = useState<string>("");
  const [manualName, setManualName] = useState(false);
  const [manualId, setManualId] = useState(false);

  const [overrideStyle, setOverrideStyle] = useState(false);
  const [overrideConcept, setOverrideConcept] = useState(false);
  const [overrideGrammar, setOverrideGrammar] = useState(false);
  const [overrideSyllables, setOverrideSyllables] = useState(false);
  const [overrideSeparator, setOverrideSeparator] = useState(false);
  const [overridePhonotactics, setOverridePhonotactics] = useState(false);

  const [styleName, setStyleName] = useState("");
  const [conceptList, setConceptList] = useState("");
  const [grammarProfile, setGrammarProfile] = useState("");
  const [syllableMin, setSyllableMin] = useState(1);
  const [syllableMax, setSyllableMax] = useState(2);
  const [syllableSeparator, setSyllableSeparator] = useState("");
  const [phonotacticJson, setPhonotacticJson] = useState("{}");
  const [phonotacticError, setPhonotacticError] = useState<string | null>(null);

  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [eventCount, setEventCount] = useState<number>(1);
  const [rules, setRules] = useState<Rule[]>([]);
  const [ruleWarnings, setRuleWarnings] = useState<string[]>([]);

  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    if (!parentId) return;
    const parent = languages[parentId];
    if (!parent) return;
    const parentMeta = parent.meta || {};
    const parentYear = Number(parentMeta.year ?? 0);
    setChildYear(parentYear + 100);

    if (!manualName) {
      setChildName(`${parentId}_child`);
    }
    if (!manualId) {
      setChildId(suggestUniqueId(`${parentId}_child`, languageIds));
    }

    setStyleName(String(parent.style_name ?? presetData?.defaults?.style_name ?? "default"));
    setConceptList(String(parent.concept_list_name ?? presetData?.defaults?.concept_list_name ?? "basic"));
    setGrammarProfile(
      String(parent.grammar_profile_name ?? presetData?.defaults?.grammar_profile_name ?? "default")
    );
    const syllableRange = Array.isArray(parent.syllable_range) ? parent.syllable_range : [1, 1];
    setSyllableMin(Number(syllableRange[0] ?? 1));
    setSyllableMax(Number(syllableRange[1] ?? 1));
    setSyllableSeparator(String(parent.syllable_separator ?? ""));
  }, [parentId, languages, manualId, manualName, languageIds, presetData]);

  useEffect(() => {
    if (!parentId && languageIds.length) {
      setParentId(activeId ?? languageIds[0]);
    }
  }, [activeId, languageIds, parentId]);

  const handleTemplateToggle = (template: string) => {
    setSelectedTemplates((current) =>
      current.includes(template) ? current.filter((id) => id !== template) : [...current, template]
    );
  };

  const handleGenerateRules = async () => {
    if (!projectId || !parentId) return;
    if (!selectedTemplates.length) {
      setRules([]);
      return;
    }
    const changesetId = `chg_${parentId}_${childId || "child"}`;
    const payload = {
      parent_language_id: parentId,
      template_ids: selectedTemplates,
      event_count: Math.max(1, eventCount),
      changeset_id: changesetId,
      name: `${parentId}→${childId || "child"}`,
    };
    const response = await apiPost<{ changeset: { rules: Rule[] } }>(
      `/project/${projectId}/changeset/generate`,
      payload
    );
    setRules(
      (response.changeset?.rules || []).map((rule) => ({
        from: String(rule.from ?? ""),
        to: String(rule.to ?? ""),
        enabled: Boolean(rule.enabled ?? true),
        notes: String(rule.notes ?? ""),
      }))
    );
  };

  const handleRuleChange = (index: number, field: keyof Rule, value: string | boolean) => {
    setRules((current) =>
      current.map((rule, idx) => (idx === index ? { ...rule, [field]: value } : rule))
    );
  };

  const handleAddRule = () => {
    setRules((current) => [...current, { from: "", to: "", enabled: true, notes: "" }]);
  };

  const handleRemoveRule = (index: number) => {
    setRules((current) => current.filter((_, idx) => idx !== index));
  };

  const buildOverrideSettings = () => {
    const overrides: Record<string, any> = {
      year: Number(childYear),
      notes: childNotes,
    };
    if (overrideStyle) overrides.style_name = styleName;
    if (overrideConcept) overrides.concept_list_name = conceptList;
    if (overrideGrammar) overrides.grammar_profile_name = grammarProfile;
    if (overrideSyllables) overrides.syllable_range = [Number(syllableMin), Number(syllableMax)];
    if (overrideSeparator) overrides.syllable_separator = syllableSeparator;
    if (overridePhonotactics) {
      try {
        const parsed = JSON.parse(phonotacticJson || "{}");
        overrides.phonotactic_profile_overrides = parsed;
        setPhonotacticError(null);
      } catch (err) {
        setPhonotacticError("Invalid JSON for phonotactic overrides.");
      }
    }
    return overrides;
  };

  const handlePreview = async () => {
    if (!projectId || !parentId) return;
    const { cleaned, warnings } = cleanRules(rules);
    setRuleWarnings(warnings);
    const changeset = {
      schema_version: 1,
      changeset_id: `chg_${parentId}_${childId || "child"}`,
      name: `${parentId}→${childId || "child"}`,
      description: `${cleaned.length} sound-change rule(s)`,
      rules: cleaned,
    };
    const payload = {
      parent_language_id: parentId,
      child_name: childName || childId,
      child_id: childId || suggestUniqueId(childName || "child", languageIds),
      changeset,
      override_settings: buildOverrideSettings(),
    };
    setPreviewLoading(true);
    try {
      const response = await apiPost<PreviewResponse>(`/project/${projectId}/preview-child`, payload);
      setPreviewData(response);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!projectId || !parentId) return;
    const { cleaned, warnings } = cleanRules(rules);
    setRuleWarnings(warnings);
    const changeset = {
      schema_version: 1,
      changeset_id: `chg_${parentId}_${childId || "child"}`,
      name: `${parentId}→${childId || "child"}`,
      description: `${cleaned.length} sound-change rule(s)`,
      rules: cleaned,
    };
    const payload = {
      parent_language_id: parentId,
      child_name: childName || childId,
      child_id: childId || suggestUniqueId(childName || "child", languageIds),
      changeset,
      override_settings: buildOverrideSettings(),
    };
    const response = await apiPost<{ language: any }>(`/project/${projectId}/create-child`, payload);
    const newId = response.language?.meta?.language_id;
    if (newId) {
      onSelect(newId);
    }
    onRefresh();
  };

  // Compare state
  const [compareChildId, setCompareChildId] = useState<string>("");
  const [compareParentId, setCompareParentId] = useState<string>("");
  const [compareData, setCompareData] = useState<CompareResponse | null>(null);

  useEffect(() => {
    if (!languageIds.length) return;
    const defaultChild = activeId ?? languageIds[0];
    setCompareChildId(defaultChild);
    const parent = languages[defaultChild]?.meta?.parent_id ?? languageIds[0];
    setCompareParentId(parent);
  }, [activeId, languageIds, languages]);

  const handleCompare = async () => {
    if (!projectId || !compareChildId || !compareParentId) return;
    const response = await apiGet<CompareResponse>(
      `/project/${projectId}/compare?parent_id=${compareParentId}&child_id=${compareChildId}&sample_count=20`
    );
    setCompareData(response);
  };

  // Details state
  const [sampleCount, setSampleCount] = useState(5);
  const [wordsMin, setWordsMin] = useState(3);
  const [wordsMax, setWordsMax] = useState(7);
  const [samples, setSamples] = useState<{ ipa: string; gloss: string }[]>([]);
  const [rerollEntry, setRerollEntry] = useState<string>("");

  useEffect(() => {
    if (!activeLanguage) return;
    const lexicon = activeLanguage.lexicon || [];
    const firstId = lexicon.length ? String(lexicon[0].id ?? "") : "";
    setRerollEntry(firstId);
  }, [activeLanguage]);

  const handleSample = async () => {
    if (!projectId || !activeId) return;
    const response = await apiPost<{ samples: { ipa: string; gloss: string }[] }>(
      `/project/${projectId}/language/${activeId}/samples`,
      {
        sample_count: sampleCount,
        words_range: [wordsMin, wordsMax],
      }
    );
    setSamples(response.samples || []);
  };

  const handleReroll = async () => {
    if (!projectId || !activeId || !rerollEntry) return;
    await apiPost(`/project/${projectId}/language/${activeId}/reroll`, { entry_id: rerollEntry });
    onRefresh();
  };

  if (!projectId) {
    return (
      <div className="panel">
        <h2>Workspace</h2>
        <p>Select a project to begin.</p>
      </div>
    );
  }

  if (!languageIds.length) {
    return (
      <div className="panel">
        <h2>Workspace</h2>
        <p>No languages found. Save a proto language first.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="workspace-tabs">
        <button
          className={workspace === "create" ? "active" : ""}
          onClick={() => onWorkspaceChange("create")}
        >
          Create Daughter
        </button>
        <button
          className={workspace === "compare" ? "active" : ""}
          onClick={() => onWorkspaceChange("compare")}
        >
          Compare
        </button>
        <button
          className={workspace === "details" ? "active" : ""}
          onClick={() => onWorkspaceChange("details")}
        >
          Details
        </button>
      </div>

      {workspace === "create" && (
        <div className="workspace-section">
          <h2>Create Daughter</h2>
          <div className="form-row">
            <label>Step 1: Select parent</label>
            <select value={parentId} onChange={(event) => setParentId(event.target.value)}>
              {languageIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
            <button onClick={() => onHelp("parent_select")}>?</button>
          </div>

          <div className="form-row">
            <label>Child language name</label>
            <input
              value={childName}
              onChange={(event) => {
                setManualName(true);
                setChildName(event.target.value);
              }}
            />
          </div>
          <div className="form-row">
            <label>Child language ID</label>
            <input
              value={childId}
              onChange={(event) => {
                setManualId(true);
                setChildId(event.target.value);
              }}
            />
            <button onClick={() => setChildId(suggestUniqueId(childName || childId, languageIds))}>
              Suggest ID
            </button>
          </div>
          <div className="form-row">
            <label>Year</label>
            <input
              type="number"
              value={childYear}
              onChange={(event) => setChildYear(Number(event.target.value))}
            />
          </div>
          <div className="form-row">
            <label>Notes</label>
            <textarea value={childNotes} onChange={(event) => setChildNotes(event.target.value)} />
          </div>

          <div className="form-row">
            <label>Override inherited settings</label>
          </div>
          <div className="override-grid">
            <label>
              <input
                type="checkbox"
                checked={overrideStyle}
                onChange={(event) => setOverrideStyle(event.target.checked)}
              />
              Style preset
            </label>
            <select disabled={!overrideStyle} value={styleName} onChange={(e) => setStyleName(e.target.value)}>
              {(presetData?.style_presets ?? []).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>

            <label>
              <input
                type="checkbox"
                checked={overrideConcept}
                onChange={(event) => setOverrideConcept(event.target.checked)}
              />
              Concept list
            </label>
            <select
              disabled={!overrideConcept}
              value={conceptList}
              onChange={(e) => setConceptList(e.target.value)}
            >
              {(presetData?.concept_lists ?? []).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>

            <label>
              <input
                type="checkbox"
                checked={overrideGrammar}
                onChange={(event) => setOverrideGrammar(event.target.checked)}
              />
              Grammar profile
            </label>
            <select
              disabled={!overrideGrammar}
              value={grammarProfile}
              onChange={(e) => setGrammarProfile(e.target.value)}
            >
              {(presetData?.grammar_profiles ?? []).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>

            <label>
              <input
                type="checkbox"
                checked={overrideSyllables}
                onChange={(event) => setOverrideSyllables(event.target.checked)}
              />
              Syllable range
            </label>
            <div className="inline-inputs">
              <input
                type="number"
                disabled={!overrideSyllables}
                value={syllableMin}
                onChange={(event) => setSyllableMin(Number(event.target.value))}
              />
              <input
                type="number"
                disabled={!overrideSyllables}
                value={syllableMax}
                onChange={(event) => setSyllableMax(Number(event.target.value))}
              />
            </div>

            <label>
              <input
                type="checkbox"
                checked={overrideSeparator}
                onChange={(event) => setOverrideSeparator(event.target.checked)}
              />
              Syllable separator
            </label>
            <select
              disabled={!overrideSeparator}
              value={syllableSeparator}
              onChange={(event) => setSyllableSeparator(event.target.value)}
            >
              <option value="">(none)</option>
              <option value=".">.</option>
            </select>

            <label>
              <input
                type="checkbox"
                checked={overridePhonotactics}
                onChange={(event) => setOverridePhonotactics(event.target.checked)}
              />
              Phonotactic overrides (JSON)
            </label>
            <textarea
              disabled={!overridePhonotactics}
              value={phonotacticJson}
              onChange={(event) => setPhonotacticJson(event.target.value)}
            />
          </div>
          {phonotacticError && <p className="warning">{phonotacticError}</p>}

          <h3>Step 3: Sound changes</h3>
          <div className="template-list">
            {templateOptions.map((template) => (
              <label key={template}>
                <input
                  type="checkbox"
                  checked={selectedTemplates.includes(template)}
                  onChange={() => handleTemplateToggle(template)}
                />
                {template}
              </label>
            ))}
          </div>
          <div className="form-row">
            <label>Event count</label>
            <input
              type="number"
              value={eventCount}
              min={1}
              onChange={(event) => setEventCount(Number(event.target.value))}
            />
            <button onClick={handleGenerateRules}>Generate rules</button>
          </div>

          <div className="rule-table">
            <div className="rule-row header">
              <span>From</span>
              <span>To</span>
              <span>Enabled</span>
              <span>Notes</span>
              <span />
            </div>
            {rules.map((rule, index) => (
              <div className="rule-row" key={`${rule.from}-${index}`}>
                <input
                  value={rule.from}
                  onChange={(event) => handleRuleChange(index, "from", event.target.value)}
                />
                <input
                  value={rule.to}
                  onChange={(event) => handleRuleChange(index, "to", event.target.value)}
                />
                <input
                  type="checkbox"
                  checked={rule.enabled}
                  onChange={(event) => handleRuleChange(index, "enabled", event.target.checked)}
                />
                <input
                  value={rule.notes}
                  onChange={(event) => handleRuleChange(index, "notes", event.target.value)}
                />
                <button onClick={() => handleRemoveRule(index)}>Remove</button>
              </div>
            ))}
            <button onClick={handleAddRule}>Add rule</button>
          </div>
          {ruleWarnings.length > 0 && (
            <p className="warning">Rule warnings: {ruleWarnings.join(" ")}</p>
          )}

          <h3>Step 4: Preview</h3>
          <div className="form-row">
            <button onClick={handlePreview}>{previewLoading ? "Previewing..." : "Update Preview"}</button>
            <button onClick={handleCreate}>Create Daughter</button>
          </div>

          {previewData?.diff && (
            <div className="diff-grid">
              <div>
                <strong>Added vowels:</strong> {previewData.diff.added_vowels.join(", ") || "—"}
              </div>
              <div>
                <strong>Removed vowels:</strong> {previewData.diff.removed_vowels.join(", ") || "—"}
              </div>
              <div>
                <strong>Added consonants:</strong> {previewData.diff.added_consonants.join(", ") || "—"}
              </div>
              <div>
                <strong>Removed consonants:</strong> {previewData.diff.removed_consonants.join(", ") || "—"}
              </div>
            </div>
          )}
          {previewData?.lexicon_preview && (
            <div className="table four-col">
              <div className="table-row header">
                <span>ID</span>
                <span>Parent</span>
                <span>Child</span>
                <span>Meaning</span>
              </div>
              {previewData.lexicon_preview.map((row) => (
                <div key={row.id} className="table-row">
                  <span>{row.id}</span>
                  <span>{row.parent_ipa}</span>
                  <span>{row.child_ipa}</span>
                  <span>{row.meaning}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {workspace === "compare" && (
        <div className="workspace-section">
          <h2>Compare</h2>
          <div className="form-row">
            <label>Child language</label>
            <select value={compareChildId} onChange={(event) => setCompareChildId(event.target.value)}>
              {languageIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
            <label>Parent language</label>
            <select value={compareParentId} onChange={(event) => setCompareParentId(event.target.value)}>
              {languageIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
            <button onClick={handleCompare}>Compare</button>
          </div>
          {compareData && (
            <>
              <div className="diff-grid">
                <div>
                  <strong>Added vowels:</strong> {compareData.diff.added_vowels.join(", ") || "—"}
                </div>
                <div>
                  <strong>Removed vowels:</strong> {compareData.diff.removed_vowels.join(", ") || "—"}
                </div>
                <div>
                  <strong>Added consonants:</strong> {compareData.diff.added_consonants.join(", ") || "—"}
                </div>
                <div>
                  <strong>Removed consonants:</strong> {compareData.diff.removed_consonants.join(", ") || "—"}
                </div>
              </div>
              <div className="table four-col">
                <div className="table-row header">
                  <span>ID</span>
                  <span>Parent</span>
                  <span>Child</span>
                  <span>Meaning</span>
                </div>
                {compareData.lexicon_preview.map((row) => (
                  <div key={row.id} className="table-row">
                    <span>{row.id}</span>
                    <span>{row.parent_ipa}</span>
                    <span>{row.child_ipa}</span>
                    <span>{row.meaning}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {workspace === "details" && activeLanguage && (
        <div className="workspace-section">
          <h2>Language Details</h2>
          <div className="meta-grid">
            <div>
              <strong>Name:</strong> {activeLanguage.meta?.name ?? activeId}
            </div>
            <div>
              <strong>Year:</strong> {activeLanguage.meta?.year ?? "?"}
            </div>
            <div>
              <strong>Parent:</strong> {activeLanguage.meta?.parent_id ?? "—"}
            </div>
            <div>
              <strong>Lexicon size:</strong> {(activeLanguage.lexicon || []).length}
            </div>
          </div>

          <div className="inventory-grid">
            <div>
              <h3>Vowels</h3>
              <p>{(activeLanguage.inventory?.vowels || []).join(", ") || "—"}</p>
            </div>
            <div>
              <h3>Consonants</h3>
              <p>{(activeLanguage.inventory?.consonants || []).join(", ") || "—"}</p>
            </div>
          </div>

          <h3>Sample sentences</h3>
          <div className="form-row">
            <label>Count</label>
            <input
              type="number"
              value={sampleCount}
              min={1}
              onChange={(event) => setSampleCount(Number(event.target.value))}
            />
            <label>Words range</label>
            <input
              type="number"
              value={wordsMin}
              min={1}
              onChange={(event) => setWordsMin(Number(event.target.value))}
            />
            <input
              type="number"
              value={wordsMax}
              min={1}
              onChange={(event) => setWordsMax(Number(event.target.value))}
            />
            <button onClick={handleSample}>Generate</button>
          </div>
          {samples.length > 0 && (
            <div className="table two-col">
              <div className="table-row header">
                <span>IPA</span>
                <span>Gloss</span>
              </div>
              {samples.map((sample, index) => (
                <div key={`${sample.ipa}-${index}`} className="table-row">
                  <span>{sample.ipa}</span>
                  <span>{sample.gloss}</span>
                </div>
              ))}
            </div>
          )}

          <h3>Reroll lexicon entry</h3>
          <div className="form-row">
            <select value={rerollEntry} onChange={(event) => setRerollEntry(event.target.value)}>
              {(activeLanguage.lexicon || []).map((entry: any) => (
                <option key={entry.id} value={entry.id}>
                  {entry.id} — {entry.meaning}
                </option>
              ))}
            </select>
            <button onClick={handleReroll}>Reroll</button>
          </div>

          <h3>Lexicon preview</h3>
          <div className="table three-col">
            <div className="table-row header">
              <span>ID</span>
              <span>IPA</span>
              <span>Meaning</span>
            </div>
            {(activeLanguage.lexicon || []).slice(0, 30).map((entry: any) => (
              <div key={entry.id} className="table-row">
                <span>{entry.id}</span>
                <span>{entry.ipa}</span>
                <span>{entry.meaning}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
