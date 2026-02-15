# ArXivMind

Local RAG pipeline for research paper Q&A. Drop PDFs, index them, ask questions — answers come grounded in your papers with cited sources.

## Tech Stack

| Layer | Tech |
|-------|------|
| LLM | GLM-4 via Ollama (local, no API keys) |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) |
| Vector Store | ChromaDB (persistent) |
| Retrieval | Hybrid — BM25 + vector search + cross-encoder reranking (RRF fusion) |
| Chunking | Section-aware (detects Abstract, Methods, Results, etc.) |
| Backend | FastAPI + Python |
| Frontend | Next.js 16 + React 19 + Tailwind |
| Evaluation | RAGAS-inspired (faithfulness, relevancy, precision, recall) |

## How It Works

```
PDF Papers → Section-Aware Chunking → Embeddings → ChromaDB
                                                        ↓
User Question → BM25 + Vector Search → RRF Fusion → Cross-Encoder Rerank → GLM-4 → Answer
```

1. **Index** — Upload or drop PDFs into `papers/`. The pipeline extracts text, detects sections, chunks with overlap, embeds, and stores in ChromaDB. Already-indexed papers are skipped via manifest hashing.
2. **Query** — Your question hits both BM25 keyword search and vector similarity search. Results are fused with Reciprocal Rank Fusion, then reranked by a cross-encoder for precision.
3. **Answer** — Top chunks become context for GLM-4, which generates a grounded answer with source citations.

## Research Agents

Three specialized agents for deeper analysis:

- **Synthesize** — Cross-paper synthesis: common findings, contradictions, strongest evidence
- **Trends** — Research trend identification: emerging directions, methodology evolution
- **Gaps** — Gap analysis: under-explored areas, limitations, future work suggestions

## Quick Start

```bash
# Prerequisites: Ollama running with GLM-4
ollama pull glm-4.7-flash

# Start everything
make start

# Index your papers
make index

# Test a query
make test
```

**Endpoints:** `localhost:8000/docs` for full API docs, `localhost:3000` for the frontend.

## Roadmap

- [ ] Multi-model support (swap GLM-4 for any Ollama model)
- [ ] Citation graph visualization
- [ ] Batch evaluation pipeline with gold-standard Q&A
- [ ] Paper similarity clustering
- [ ] Export research summaries to markdown
