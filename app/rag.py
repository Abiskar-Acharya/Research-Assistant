"""
RAG Pipeline: PDF Processing, Vector Search, and GLM-4 Integration
Enhanced with section-aware chunking and hybrid retrieval.
"""
import os
import time
from pathlib import Path
from typing import List, Dict
import fitz  # pymupdf
import chromadb
from sentence_transformers import SentenceTransformer
import requests
import json

from app.chunker import SectionChunker
from app.retriever import HybridRetriever
from app.manifest import ManifestManager
from app.metadata import extract_title

# Configuration
PAPERS_DIR = Path("/app/papers")
CHROMA_DIR = Path(os.environ.get("CHROMA_PERSIST_DIR", "/app/data"))
MODEL_NAME = os.environ.get("MODEL_NAME", "glm-4.7-flash")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality embeddings
CHUNK_SIZE = 500  # Characters per chunk
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")

class RAGPipeline:
    def __init__(self):
        """Initialize RAG components"""
        # Initialize embedding model
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

        # Initialize ChromaDB
        print(f"Connecting to ChromaDB at: {CHROMA_DIR}")
        self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = self.chroma_client.get_or_create_collection(
            name="research_papers",
            metadata={"description": "Research paper embeddings"}
        )

        # Initialize manifest manager
        self.manifest = ManifestManager()

        # Initialize section-aware chunker
        self.chunker = SectionChunker(chunk_size=CHUNK_SIZE)

        # Initialize hybrid retriever
        print("Initializing hybrid retriever (BM25 + vector + reranking)...")
        self.retriever = HybridRetriever(self.collection, self.embedder)

        # Build BM25 index if documents exist
        if self.collection.count() > 0:
            print("Building BM25 index from existing documents...")
            self.retriever.build_bm25_index()
            print(f"BM25 index built with {self.collection.count()} documents")

    def extract_text_from_pdf(self, pdf_path: Path) -> tuple:
        """Extract text from a single PDF file. Returns (text, page_count)."""
        text = ""
        page_count = 0
        try:
            doc = fitz.open(str(pdf_path))
            page_count = len(doc)
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            print(f"  Extracted {len(text)} chars ({page_count} pages) from {pdf_path.name}")
        except Exception as e:
            print(f"  Error reading {pdf_path.name}: {e}")
        return text, page_count

    def index_papers(self, progress_callback=None) -> Dict:
        """Process all PDFs in papers/ directory and store in ChromaDB"""
        if not PAPERS_DIR.exists():
            return {"error": "Papers directory not found"}

        pdf_files = list(PAPERS_DIR.glob("*.pdf"))
        if not pdf_files:
            return {"error": "No PDF files found in papers/"}

        print(f"\nIndexing {len(pdf_files)} PDF files with section-aware chunking...")
        total_chunks = 0
        papers_indexed = 0

        for paper_idx, pdf_file in enumerate(pdf_files):
            if progress_callback:
                progress_callback(
                    current_paper=pdf_file.name,
                    papers_done=paper_idx,
                    total_papers=len(pdf_files),
                    total_chunks=total_chunks,
                )

            # Check manifest — skip already-indexed papers
            sha256 = ManifestManager.compute_hash(pdf_file)
            if self.manifest.is_indexed(pdf_file.name, sha256):
                print(f"  Skipping {pdf_file.name} (already indexed, hash unchanged)")
                continue

            # Extract title
            title = extract_title(pdf_file)
            print(f"  Title: {title}")

            # Extract text
            text, page_count = self.extract_text_from_pdf(pdf_file)
            if not text.strip():
                continue

            # Section-aware chunking
            chunks = self.chunker.chunk_paper(text, pdf_file.name)
            print(f"  Created {len(chunks)} section-aware chunks from {pdf_file.name}")

            # Batched embedding with progress logging
            chunk_texts = [c["text"] for c in chunks]
            BATCH_SIZE = 64
            all_embeddings = []
            for batch_start in range(0, len(chunk_texts), BATCH_SIZE):
                batch = chunk_texts[batch_start:batch_start + BATCH_SIZE]
                batch_embeddings = self.embedder.encode(batch, show_progress_bar=False)
                all_embeddings.extend(batch_embeddings.tolist())
                print(f"  Embedded {min(batch_start + BATCH_SIZE, len(chunk_texts))}/{len(chunk_texts)} chunks")
            embeddings = all_embeddings

            # Store in ChromaDB with section metadata (including title)
            ids = [f"{pdf_file.stem}_chunk_{c['chunk_id']}" for c in chunks]
            metadatas = [
                {
                    "source": c["source"],
                    "chunk_id": c["chunk_id"],
                    "section": c.get("section", ""),
                    "title": title,
                }
                for c in chunks
            ]

            self.collection.add(
                embeddings=embeddings,
                documents=chunk_texts,
                ids=ids,
                metadatas=metadatas
            )

            chunk_count = len(chunks)
            total_chunks += chunk_count
            papers_indexed += 1

            # Record in manifest
            self.manifest.add_paper(pdf_file.name, title, page_count, chunk_count, sha256)

        if progress_callback:
            progress_callback(
                current_paper="",
                papers_done=len(pdf_files),
                total_papers=len(pdf_files),
                total_chunks=total_chunks,
            )

        # Rebuild BM25 index after indexing
        print("Rebuilding BM25 index...")
        self.retriever.build_bm25_index()

        return {
            "status": "success",
            "papers_indexed": papers_indexed,
            "total_chunks": total_chunks,
            "collection_size": self.collection.count()
        }

    def search_similar(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search using hybrid retrieval (BM25 + vector + reranking)"""
        return self.retriever.search(query, n_results)

    def query_glm4(self, prompt: str) -> str:
        """Send prompt to GLM-4 via Ollama with retry logic."""
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
                    timeout=60
                )
                response.raise_for_status()
                return response.json().get("response", "No response from model")
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return f"Error calling GLM-4: {str(e)}"

    def index_single_paper(self, pdf_path: Path) -> Dict:
        """Index a single PDF paper into the RAG pipeline.

        Extracts text, chunks, embeds, stores in ChromaDB,
        updates manifest, and rebuilds BM25 index.

        Returns:
            Dict with status, filename, title, page_count, chunk_count.
        """
        sha256 = ManifestManager.compute_hash(pdf_path)
        title = extract_title(pdf_path)
        text, page_count = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            raise ValueError(f"No text could be extracted from {pdf_path.name}")

        # Section-aware chunking
        chunks = self.chunker.chunk_paper(text, pdf_path.name)
        print(f"  Created {len(chunks)} section-aware chunks from {pdf_path.name}")

        # Embed
        chunk_texts = [c["text"] for c in chunks]
        BATCH_SIZE = 64
        all_embeddings = []
        for batch_start in range(0, len(chunk_texts), BATCH_SIZE):
            batch = chunk_texts[batch_start:batch_start + BATCH_SIZE]
            batch_embeddings = self.embedder.encode(batch, show_progress_bar=False)
            all_embeddings.extend(batch_embeddings.tolist())

        # Store in ChromaDB
        ids = [f"{pdf_path.stem}_chunk_{c['chunk_id']}" for c in chunks]
        metadatas = [
            {
                "source": c["source"],
                "chunk_id": c["chunk_id"],
                "section": c.get("section", ""),
                "title": title,
            }
            for c in chunks
        ]

        self.collection.add(
            embeddings=all_embeddings,
            documents=chunk_texts,
            ids=ids,
            metadatas=metadatas
        )

        chunk_count = len(chunks)

        # Update manifest
        self.manifest.add_paper(pdf_path.name, title, page_count, chunk_count, sha256)

        # Rebuild BM25 index
        print("Rebuilding BM25 index...")
        self.retriever.build_bm25_index()

        return {
            "status": "success",
            "filename": pdf_path.name,
            "title": title,
            "page_count": page_count,
            "chunk_count": chunk_count,
        }

    def delete_paper(self, filename: str) -> Dict:
        """Delete a paper and its chunks from the pipeline.

        Removes chunks from ChromaDB, removes from manifest,
        and rebuilds the BM25 index.

        Returns:
            Dict with status information.
        """
        # Check if paper exists in manifest
        paper = self.manifest.get_paper(filename)
        if not paper:
            return {"status": "not_found", "filename": filename}

        # Get chunk IDs matching this paper from ChromaDB
        stem = Path(filename).stem
        prefix = f"{stem}_chunk_"
        chunks_removed = 0

        # Retrieve all IDs from the collection and filter
        try:
            all_data = self.collection.get(include=[])
            matching_ids = [id_ for id_ in all_data["ids"] if id_.startswith(prefix)]

            if matching_ids:
                self.collection.delete(ids=matching_ids)
                chunks_removed = len(matching_ids)
                print(f"  Deleted {chunks_removed} chunks for {filename}")
        except Exception as e:
            print(f"  Error deleting chunks for {filename}: {e}")

        # Remove from manifest
        self.manifest.remove_paper(filename)

        # Rebuild BM25 index
        print("Rebuilding BM25 index...")
        self.retriever.build_bm25_index()

        return {
            "status": "deleted",
            "filename": filename,
            "chunks_removed": chunks_removed,
        }

    def get_papers(self) -> List[Dict]:
        """Return list of all indexed papers from manifest."""
        return self.manifest.get_papers()

    def rag_query(self, question: str, n_results: int = 5) -> Dict:
        """Full RAG pipeline: hybrid search -> retrieve -> generate"""
        # Step 1: Hybrid search for relevant chunks
        print(f"\n[RAG] Searching for: {question}")
        relevant_chunks = self.search_similar(question, n_results)

        if not relevant_chunks:
            return {
                "answer": "No relevant information found in the indexed papers.",
                "sources": []
            }

        # Step 2: Build context from retrieved chunks
        context = "\n\n".join([
            f"[From {chunk['source']}" + (f" - {chunk.get('section', '')}]" if chunk.get('section') else "]") + f"\n{chunk['text']}"
            for chunk in relevant_chunks
        ])

        # Step 3: Build prompt for GLM-4
        prompt = f"""You are a research assistant. Answer the question based ONLY on the provided context from research papers.

Context from papers:
{context}

Question: {question}

Answer (cite sources when possible):"""

        # Step 4: Generate answer with GLM-4
        print("[RAG] Generating answer with GLM-4...")
        answer = self.query_glm4(prompt)

        # Step 5: Return structured response
        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "source": chunk['source'],
                    "text": chunk['text'],
                    "distance": chunk['distance'],
                    "section": chunk.get('section', ''),
                }
                for chunk in relevant_chunks
            ],
            "num_sources": len(relevant_chunks)
        }

# Global instance
rag = None

def get_rag() -> RAGPipeline:
    """Get or create RAG pipeline instance"""
    global rag
    if rag is None:
        rag = RAGPipeline()
    return rag
