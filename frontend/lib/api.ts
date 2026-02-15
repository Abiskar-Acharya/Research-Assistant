import {
  QueryResponse,
  AgentResponse,
  HealthResponse,
  StatsResponse,
  IndexStatus,
  PapersListResponse,
  UploadResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function queryRAG(
  question: string,
  nResults = 5
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, n_results: nResults }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

export async function queryAgent(
  question: string,
  agentType: string,
  nResults = 10
): Promise<AgentResponse> {
  const res = await fetch(`${API_BASE}/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      agent_type: agentType,
      n_results: nResults,
    }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

export async function indexPapers(): Promise<{ status: string; papers_indexed: number; total_chunks: number }> {
  const res = await fetch(`${API_BASE}/index`, { method: "POST" });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Indexing failed" }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function checkIndexStatus(): Promise<IndexStatus> {
  const res = await fetch(`${API_BASE}/index/status`);
  return res.json();
}

export async function getStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/stats`);
  return res.json();
}

export async function getPapers(): Promise<PapersListResponse> {
  const res = await fetch(`${API_BASE}/papers`);
  if (!res.ok) throw new Error("Failed to fetch papers");
  return res.json();
}

export async function uploadPaper(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || `Upload error: ${res.status}`);
  }
  return res.json();
}

export async function deletePaper(paperId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/papers/${encodeURIComponent(paperId)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Delete failed" }));
    throw new Error(error.detail || `Delete error: ${res.status}`);
  }
}
