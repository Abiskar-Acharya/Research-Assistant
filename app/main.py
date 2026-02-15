"""
FastAPI Server for ArXivMind RAG Pipeline
Enhanced with research agents, RAGAS evaluation, and paper management.
"""
import os
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.rag import get_rag
from app.agents import ResearchAgents
from app.evaluation import RAGEvaluator
from app.models import (
    QueryRequest, QueryResponse, AgentRequest, AgentResponse,
    EvalRequest, HealthResponse, PaperInfo, PapersListResponse, UploadResponse,
)

# Initialize FastAPI app
app = FastAPI(
    title="ArXivMind API",
    description="Local RAG system for research paper Q&A with hybrid retrieval",
    version="2.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
rag_pipeline = None
research_agents = None
evaluator = None

# Indexing progress state
indexing_status = {
    "state": "idle",
    "current_paper": "",
    "papers_done": 0,
    "total_papers": 0,
    "total_chunks": 0,
    "error": None,
}

@app.on_event("startup")
async def startup_event():
    """Initialize RAG pipeline on server start"""
    global rag_pipeline, research_agents, evaluator
    model_name = os.environ.get("MODEL_NAME", "glm-4.7-flash")
    print("\n" + "="*50)
    print("Starting ArXivMind RAG Pipeline Server v2.0")
    print(f"Model: {model_name}")
    print("="*50)
    rag_pipeline = get_rag()
    research_agents = ResearchAgents(rag_pipeline)
    evaluator = RAGEvaluator()
    print("RAG Pipeline initialized")
    print("Research agents loaded (synthesize, trends, gaps)")
    print("RAGAS evaluator loaded")
    print(f"Server ready at http://localhost:8000")
    print(f"API docs at http://localhost:8000/docs")
    print("="*50 + "\n")

@app.get("/")
async def root():
    """Root endpoint - welcome message"""
    return {
        "message": "ArXivMind RAG Pipeline API v2.0",
        "endpoints": {
            "health": "/health",
            "index_papers": "/index",
            "query": "/query",
            "agent": "/agent",
            "evaluate": "/evaluate",
            "generate_qa": "/generate-qa",
            "upload": "/upload",
            "papers": "/papers",
            "stats": "/stats",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    import requests as req
    ollama_url = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
    model_name = os.environ.get("MODEL_NAME", "glm-4.7-flash")
    ollama_connected = False
    try:
        r = req.get(f"{ollama_url}/api/tags", timeout=3)
        ollama_connected = r.status_code == 200
    except Exception:
        pass
    return {
        "status": "healthy",
        "rag_initialized": rag_pipeline is not None,
        "collection_count": rag_pipeline.collection.count() if rag_pipeline else 0,
        "ollama_connected": ollama_connected,
        "model_name": model_name,
    }

def _run_indexing():
    """Background thread for paper indexing"""
    global indexing_status
    try:
        def on_progress(current_paper, papers_done, total_papers, total_chunks):
            indexing_status.update({
                "current_paper": current_paper,
                "papers_done": papers_done,
                "total_papers": total_papers,
                "total_chunks": total_chunks,
            })

        result = rag_pipeline.index_papers(progress_callback=on_progress)

        if "error" in result:
            indexing_status["state"] = "error"
            indexing_status["error"] = result["error"]
        else:
            indexing_status["state"] = "done"
            indexing_status["total_chunks"] = result["total_chunks"]
    except Exception as e:
        indexing_status["state"] = "error"
        indexing_status["error"] = str(e)


@app.post("/index")
async def index_papers():
    """Index all PDF papers in papers/ directory (runs in background)"""
    global indexing_status
    if not rag_pipeline:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")

    if indexing_status["state"] == "indexing":
        return {"status": "already_indexing", **indexing_status}

    indexing_status = {
        "state": "indexing",
        "current_paper": "",
        "papers_done": 0,
        "total_papers": 0,
        "total_chunks": 0,
        "error": None,
    }

    thread = threading.Thread(target=_run_indexing, daemon=True)
    thread.start()

    return {"status": "started", "message": "Indexing started in background. Poll GET /index/status for progress."}


@app.get("/index/status")
async def index_status():
    """Get current indexing progress"""
    return indexing_status

@app.post("/query", response_model=QueryResponse)
async def query_papers(request: QueryRequest):
    """Ask a question about indexed papers"""
    if not rag_pipeline:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")

    if rag_pipeline.collection.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No papers indexed yet. Please run /index first."
        )

    try:
        result = rag_pipeline.rag_query(request.question, request.n_results)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/agent", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """Run a research agent (synthesize, trends, gaps)"""
    if not rag_pipeline or not research_agents:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")

    if rag_pipeline.collection.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No papers indexed yet. Please run /index first."
        )

    try:
        result = research_agents.run_agent(
            request.agent_type, request.question, request.n_results
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")

@app.post("/evaluate")
async def evaluate_query(request: EvalRequest):
    """Evaluate a single RAG query using RAGAS metrics"""
    if not rag_pipeline or not evaluator:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")

    if rag_pipeline.collection.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No papers indexed yet. Please run /index first."
        )

    try:
        # Run the RAG query
        rag_result = rag_pipeline.rag_query(request.question, request.n_results)
        answer = rag_result.get("answer", "")
        contexts = [s.get("text", "") for s in rag_result.get("sources", [])]

        # Evaluate
        scores = evaluator.evaluate(request.question, answer, contexts)

        return {
            "question": request.question,
            "answer": answer,
            "scores": scores,
            "num_sources": len(contexts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.post("/generate-qa")
async def generate_qa_pairs():
    """Generate gold-standard Q&A pairs from indexed papers"""
    if not rag_pipeline or not evaluator:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")

    if rag_pipeline.collection.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No papers indexed yet. Please run /index first."
        )

    try:
        # Get a sample of documents to generate Q&A from
        all_data = rag_pipeline.collection.get(
            include=["documents", "metadatas"],
            limit=10
        )
        docs = all_data.get("documents", [])
        metadatas = all_data.get("metadatas", [])

        qa_pairs = []
        seen_sources = set()

        for i, doc in enumerate(docs):
            source = metadatas[i].get("source", "unknown") if i < len(metadatas) else "unknown"
            if source in seen_sources:
                continue
            seen_sources.add(source)

            pairs = evaluator.generate_qa_pairs(doc, source, n_pairs=2)
            qa_pairs.extend(pairs)

            if len(qa_pairs) >= 10:
                break

        return {"qa_pairs": qa_pairs[:10], "count": min(len(qa_pairs), 10)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A generation failed: {str(e)}")

@app.post("/upload", response_model=UploadResponse)
async def upload_paper(file: UploadFile = File(...)):
    """Upload and index a single PDF paper"""
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if not rag_pipeline:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")

    papers_dir = Path("/app/papers")
    papers_dir.mkdir(parents=True, exist_ok=True)
    save_path = papers_dir / file.filename

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    try:
        result = rag_pipeline.index_single_paper(save_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.get("/papers", response_model=PapersListResponse)
async def list_papers():
    """List all indexed papers"""
    if not rag_pipeline:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")
    papers = rag_pipeline.get_papers()
    return {"papers": papers, "total": len(papers)}


@app.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete an indexed paper and its chunks"""
    if not rag_pipeline:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")
    result = rag_pipeline.delete_paper(paper_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Paper not found")
    return result


@app.get("/stats")
async def get_stats():
    """Get statistics about indexed papers"""
    if not rag_pipeline:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")

    collection_count = rag_pipeline.collection.count()

    model_name = os.environ.get("MODEL_NAME", "glm-4.7-flash")
    return {
        "total_chunks": collection_count,
        "collection_name": "research_papers",
        "embedding_model": "all-MiniLM-L6-v2",
        "llm_model": model_name,
        "features": {
            "chunking": "section-aware",
            "retrieval": "hybrid (BM25 + vector + cross-encoder reranking)",
            "evaluation": "RAGAS-inspired (faithfulness, relevancy, precision, recall)",
            "agents": ["synthesize", "trends", "gaps"]
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
