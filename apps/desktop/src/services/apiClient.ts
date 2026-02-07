let cachedBase: string | null = null;

async function resolveApiBase(): Promise<string> {
  if (cachedBase) {
    return cachedBase;
  }

  const globalBase = (window as { __CONLANG_API_BASE__?: string }).__CONLANG_API_BASE__;
  if (globalBase) {
    cachedBase = globalBase;
    return cachedBase;
  }

  try {
    const { invoke } = await import("@tauri-apps/api/tauri");
    const port = await invoke<number>("api_port");
    cachedBase = `http://127.0.0.1:${port}`;
    return cachedBase;
  } catch {
    cachedBase = "http://127.0.0.1:8000";
    return cachedBase;
  }
}

export async function getApiBase(): Promise<string> {
  return resolveApiBase();
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const base = await resolveApiBase();
  const response = await fetch(`${base}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

export async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
