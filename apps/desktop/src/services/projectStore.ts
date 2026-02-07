export type ProjectState = {
  projectId: string | null;
  selectedLanguageId: string | null;
};

type Listener = (state: ProjectState) => void;

class ProjectStore {
  private state: ProjectState = {
    projectId: null,
    selectedLanguageId: null,
  };
  private listeners = new Set<Listener>();

  getState(): ProjectState {
    return this.state;
  }

  setState(next: Partial<ProjectState>): void {
    this.state = { ...this.state, ...next };
    this.listeners.forEach((listener) => listener(this.state));
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}

export const projectStore = new ProjectStore();
