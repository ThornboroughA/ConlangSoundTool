import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../services/apiClient";
import TreePanel from "./panels/TreePanel";
import WorkspacePanel from "./panels/WorkspacePanel";
import HelpPanel from "./panels/HelpPanel";

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [helpTopic, setHelpTopic] = useState<string>("tree");
  const [workspace, setWorkspace] = useState<"create" | "compare" | "details">("create");
  const [projectId, setProjectId] = useState<string>("");
  const [languages, setLanguages] = useState<Record<string, any>>({});
  const [loadingLanguages, setLoadingLanguages] = useState(false);

  const refreshLanguages = useCallback(() => {
    if (!projectId) {
      setLanguages({});
      return;
    }
    setLoadingLanguages(true);
    apiGet<{ languages: Record<string, any> }>(`/project/${projectId}/tree`)
      .then((data) => {
        setLanguages(data.languages || {});
      })
      .finally(() => setLoadingLanguages(false));
  }, [projectId]);

  useEffect(() => {
    refreshLanguages();
  }, [refreshLanguages]);

  useEffect(() => {
    if (!selectedId && Object.keys(languages).length) {
      setSelectedId(Object.keys(languages)[0]);
    }
  }, [languages, selectedId]);

  return (
    <div className="app-shell">
      <TreePanel
        selectedId={selectedId}
        onSelect={setSelectedId}
        onHelp={setHelpTopic}
        projectId={projectId}
        onProjectChange={setProjectId}
        languages={languages}
        loadingLanguages={loadingLanguages}
        onRefresh={refreshLanguages}
      />
      <WorkspacePanel
        selectedId={selectedId}
        workspace={workspace}
        onWorkspaceChange={setWorkspace}
        onHelp={setHelpTopic}
        projectId={projectId}
        languages={languages}
        onSelect={setSelectedId}
        onRefresh={refreshLanguages}
      />
      <HelpPanel topicKey={helpTopic} />
    </div>
  );
}
