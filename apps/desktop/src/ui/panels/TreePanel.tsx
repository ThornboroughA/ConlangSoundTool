import { useEffect, useMemo, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import { apiGet, getApiBase } from "../../services/apiClient";

type TreePanelProps = {
  selectedId: string | null;
  onSelect: (id: string) => void;
  onHelp: (topic: string) => void;
  projectId: string;
  onProjectChange: (id: string) => void;
  languages: Record<string, any>;
  loadingLanguages: boolean;
  onRefresh: () => void;
};

type ProjectListResponse = {
  projects: { id: string; path: string }[];
};

type HealthResponse = {
  status: string;
  project_root?: string;
  cwd?: string;
};

export default function TreePanel({
  selectedId,
  onSelect,
  onHelp,
  projectId,
  onProjectChange,
  languages,
  loadingLanguages,
  onRefresh,
}: TreePanelProps) {
  const [projects, setProjects] = useState<ProjectListResponse["projects"]>([]);
  const [apiBase, setApiBase] = useState<string>("");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    getApiBase().then(setApiBase).catch(() => setApiBase(""));
    apiGet<HealthResponse>("/health")
      .then((data) => setHealth(data))
      .catch(() => setHealth(null));

    apiGet<ProjectListResponse>("/projects")
      .then((data) => {
        setProjects(data.projects);
        if (data.projects.length && !projectId) {
          onProjectChange(data.projects[0].id);
        }
        setErrorMessage(null);
      })
      .catch(() => {
        setProjects([]);
        setErrorMessage("API not reachable. Start the API server first (see README).");
      });
  }, [onProjectChange, projectId]);

  const elements = useMemo(() => {
    const nodes = [];
    const edges = [];
    const lineage = new Set<string>();
    if (selectedId && languages[selectedId]) {
      let current = languages[selectedId];
      while (current) {
        const meta = current.meta || {};
        const currentId = String(meta.language_id || "");
        if (!currentId) break;
        lineage.add(currentId);
        const parentId = meta.parent_id ? String(meta.parent_id) : "";
        current = parentId ? languages[parentId] : null;
      }
    }

    Object.values(languages).forEach((language: any) => {
      const meta = language.meta || {};
      const id = String(meta.language_id || "");
      if (!id) return;
      const label = `${meta.name || id} (${meta.year ?? "?"})`;
      const classes = [
        id === selectedId ? "selected" : "",
        lineage.has(id) ? "lineage" : "",
      ]
        .filter(Boolean)
        .join(" ");
      nodes.push({ data: { id, label }, classes });

      const parentId = meta.parent_id ? String(meta.parent_id) : "";
      if (parentId) {
        const edgeId = `edge_${parentId}_${id}`;
        const edgeClasses = lineage.has(id) ? "lineage" : "";
        edges.push({ data: { id: edgeId, source: parentId, target: id }, classes: edgeClasses });
      }
    });

    return [...nodes, ...edges];
  }, [languages, selectedId]);

  return (
    <div className="panel">
      <div className="toolbar">
        <h2>Tree</h2>
        <button onClick={() => onHelp("tree")}>?</button>
      </div>
      {errorMessage && (
        <div className="warning">
          <div>{errorMessage}</div>
          {apiBase && <div>API base: {apiBase}</div>}
        </div>
      )}
      {!errorMessage && projects.length === 0 && (
        <div className="warning">
          <div>No projects found.</div>
          {health?.project_root && <div>Project root: {health.project_root}</div>}
          <div>
            If your projects are in `outputs/projects/`, set `CONLANG_PROJECT_ROOT` before starting the API.
          </div>
        </div>
      )}
      <div className="tree-controls">
        <select value={projectId} onChange={(event) => onProjectChange(event.target.value)}>
          <option value="">Select project</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.id}
            </option>
          ))}
        </select>
        <button onClick={onRefresh}>
          {loadingLanguages ? "Loading..." : "Refresh"}
        </button>
      </div>
      <CytoscapeComponent
        elements={elements}
        style={{ width: "100%", height: "100%" }}
        layout={{ name: "breadthfirst", directed: true }}
        stylesheet={[
          {
            selector: "node",
            style: {
              label: "data(label)",
              "text-valign": "center",
              "text-halign": "center",
              "background-color": "#5b8bd1",
              color: "#fff",
              "font-size": 10,
            },
          },
          { selector: "node.selected", style: { "background-color": "#d65b5b" } },
          { selector: "node.lineage", style: { "border-width": 2, "border-color": "#1f7a5a" } },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": "#b0bec5",
              "target-arrow-color": "#b0bec5",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
            },
          },
          {
            selector: "edge.lineage",
            style: {
              "line-color": "#1f7a5a",
              "target-arrow-color": "#1f7a5a",
              width: 3,
            },
          },
        ]}
        cy={(cy) => {
          cy.on("tap", "node", (evt) => {
            const id = evt.target.id();
            onSelect(id);
          });
        }}
      />
    </div>
  );
}
