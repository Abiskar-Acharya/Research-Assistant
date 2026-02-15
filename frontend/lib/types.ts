export interface Source {
  source: string;
  text: string;
  distance: number;
  section?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  timestamp: number;
  agentMode?: string;
}

export interface Chat {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  sources: Source[];
  num_sources: number;
}

export interface AgentResponse {
  question: string;
  analysis: string;
  sources: Source[];
  agent_type: string;
}

export interface EvalResult {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  context_recall: number;
  overall: number;
}

export interface HealthResponse {
  status: string;
  rag_initialized: boolean;
  collection_count: number;
  ollama_connected: boolean;
  model_name: string;
}

export interface StatsResponse {
  total_chunks: number;
  collection_name: string;
  embedding_model: string;
  llm_model: string;
}

export interface IndexStatus {
  state: "idle" | "indexing" | "done" | "error";
  current_paper: string;
  papers_done: number;
  total_papers: number;
  total_chunks: number;
  error: string | null;
}

export interface Paper {
  filename: string;
  title: string;
  page_count: number;
  chunk_count: number;
  indexed_at: string;
  sha256: string;
}

export interface PapersListResponse {
  papers: Paper[];
  total: number;
}

export interface UploadResponse {
  status: string;
  filename: string;
  title: string;
  page_count: number;
  chunk_count: number;
}
