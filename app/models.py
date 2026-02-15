"""
Pydantic Models for ArXivMind API

Centralized request/response models for all API endpoints.
"""
from pydantic import BaseModel
from typing import Optional, List


class QueryRequest(BaseModel):
    question: str
    n_results: Optional[int] = 5


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list
    num_sources: int


class AgentRequest(BaseModel):
    question: str
    agent_type: str
    n_results: Optional[int] = 10


class AgentResponse(BaseModel):
    question: str
    analysis: str
    sources: list
    agent_type: str


class EvalRequest(BaseModel):
    question: str
    n_results: Optional[int] = 5


class HealthResponse(BaseModel):
    status: str
    rag_initialized: bool
    collection_count: int
    ollama_connected: bool
    model_name: str


class PaperInfo(BaseModel):
    filename: str
    title: str
    page_count: int
    chunk_count: int
    sha256: str
    indexed_at: str


class PapersListResponse(BaseModel):
    papers: List[PaperInfo]
    total: int


class UploadResponse(BaseModel):
    status: str
    filename: str
    title: str
    page_count: int
    chunk_count: int
