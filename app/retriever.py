"""
Hybrid Retriever: BM25 + Vector Search with Cross-Encoder Reranking

Combines keyword-based BM25 search with ChromaDB vector similarity search,
merges results via Reciprocal Rank Fusion (RRF), and reranks the top
candidates using a cross-encoder model for maximum relevance.
"""

from typing import List, Dict
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder


class HybridRetriever:
    """
    Hybrid retrieval pipeline that fuses BM25 keyword search with dense
    vector search and applies cross-encoder reranking for precision.

    Usage:
        retriever = HybridRetriever(collection, embedder)
        retriever.build_bm25_index()
        results = retriever.search("What is attention mechanism?")
    """

    def __init__(self, collection, embedder):
        """
        Initialize the hybrid retriever.

        Args:
            collection: ChromaDB collection containing indexed documents.
            embedder: SentenceTransformer model used for query embedding.
        """
        self.collection = collection
        self.embedder = embedder
        self.bm25_index = None
        self.bm25_docs = []
        self.bm25_metadatas = []
        self.bm25_ids = []
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def build_bm25_index(self):
        """
        Fetch all documents from the ChromaDB collection and build a BM25
        index over their tokenized content.

        Tokenization uses simple lowercased word splitting to keep the
        keyword matching straightforward and fast.
        """
        all_data = self.collection.get(include=["documents", "metadatas"])

        self.bm25_docs = all_data.get("documents", []) or []
        self.bm25_metadatas = all_data.get("metadatas", []) or []
        self.bm25_ids = all_data.get("ids", []) or []

        if not self.bm25_docs:
            self.bm25_index = None
            return

        tokenized_corpus = [doc.lower().split() for doc in self.bm25_docs]
        self.bm25_index = BM25Okapi(tokenized_corpus)

    def bm25_search(self, query: str, n_results: int = 20) -> List[Dict]:
        """
        Perform BM25 keyword search over the indexed corpus.

        Args:
            query: The search query string.
            n_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: text, source, score, id.
            Returns empty list if the BM25 index has not been built or
            contains no documents.
        """
        if self.bm25_index is None or not self.bm25_docs:
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25_index.get_scores(tokenized_query)

        scored_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:n_results]

        results = []
        for idx in scored_indices:
            if scores[idx] <= 0:
                continue
            metadata = self.bm25_metadatas[idx] if idx < len(self.bm25_metadatas) else {}
            results.append({
                "text": self.bm25_docs[idx],
                "source": metadata.get("source", "unknown"),
                "score": float(scores[idx]),
                "id": self.bm25_ids[idx] if idx < len(self.bm25_ids) else "",
            })

        return results

    def vector_search(self, query: str, n_results: int = 20) -> List[Dict]:
        """
        Perform dense vector similarity search via ChromaDB.

        Args:
            query: The search query string.
            n_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: text, source, score, id.
            Score is derived from ChromaDB distance (lower distance = higher score).
        """
        query_embedding = self.embedder.encode([query]).tolist()

        raw = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        results = []
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        ids = raw.get("ids", [[]])[0]

        for i, doc in enumerate(documents):
            results.append({
                "text": doc,
                "source": metadatas[i].get("source", "unknown") if i < len(metadatas) else "unknown",
                "score": 1.0 / (1.0 + distances[i]) if i < len(distances) else 0.0,
                "id": ids[i] if i < len(ids) else "",
            })

        return results

    def reciprocal_rank_fusion(
        self, results_list: List[List[Dict]], k: int = 60
    ) -> List[Dict]:
        """
        Merge multiple ranked result lists using Reciprocal Rank Fusion.

        RRF assigns each document a score of 1/(k + rank) for each list
        it appears in, then sums scores across all lists. This balances
        contributions from different retrieval methods without requiring
        score normalization.

        Args:
            results_list: List of ranked result lists to fuse.
            k: Smoothing constant (default 60, per the original RRF paper).

        Returns:
            Merged list of dicts sorted by fused score descending.
            Each dict contains: text, source, score, id.
        """
        fused_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict] = {}

        for results in results_list:
            for rank, result in enumerate(results, start=1):
                doc_id = result.get("id") or result.get("text", "")[:100]
                fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
                if doc_id not in doc_map:
                    doc_map[doc_id] = result

        sorted_ids = sorted(fused_scores, key=lambda d: fused_scores[d], reverse=True)

        merged = []
        for doc_id in sorted_ids:
            entry = doc_map[doc_id].copy()
            entry["score"] = fused_scores[doc_id]
            merged.append(entry)

        return merged

    def rerank(self, query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Rerank candidate documents using a cross-encoder model for
        fine-grained relevance estimation.

        The cross-encoder scores each (query, document) pair jointly,
        producing more accurate relevance judgments than bi-encoder
        similarity alone.

        Args:
            query: The original search query.
            candidates: List of candidate result dicts (must contain "text").
            top_k: Number of top results to return after reranking.

        Returns:
            Top-k results sorted by cross-encoder score descending.
            Each dict has an updated "score" reflecting the rerank score.
        """
        if not candidates:
            return []

        pairs = [[query, c["text"]] for c in candidates]
        ce_scores = self.cross_encoder.predict(pairs)

        for i, candidate in enumerate(candidates):
            candidate["score"] = float(ce_scores[i])

        reranked = sorted(candidates, key=lambda c: c["score"], reverse=True)
        return reranked[:top_k]

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Execute the full hybrid retrieval pipeline:

        1. Run BM25 keyword search and vector similarity search in parallel.
        2. Fuse both result lists with Reciprocal Rank Fusion.
        3. Rerank the fused candidates with a cross-encoder.
        4. Return the top-k results in the standard output format.

        Falls back to vector-only retrieval if the BM25 index is empty
        (e.g., before any documents have been indexed into BM25).

        Args:
            query: The search query string.
            n_results: Number of final results to return.

        Returns:
            List of dicts with keys: text, source, distance, section,
            retrieval_method. The distance field is 1 - normalized_score
            so that lower values indicate higher relevance (compatible
            with the existing frontend).
        """
        bm25_results = self.bm25_search(query, n_results=20)
        vector_results = self.vector_search(query, n_results=20)

        # Fuse or fall back to vector-only when BM25 has no results
        if bm25_results:
            fused = self.reciprocal_rank_fusion([bm25_results, vector_results])
            retrieval_method = "hybrid"
        else:
            fused = vector_results
            retrieval_method = "vector_only"

        # Rerank the fused candidates
        reranked = self.rerank(query, fused, top_k=n_results)

        # Normalize cross-encoder scores to [0, 1] for distance conversion
        if reranked:
            raw_scores = [r["score"] for r in reranked]
            min_score = min(raw_scores)
            max_score = max(raw_scores)
            score_range = max_score - min_score

            if score_range > 0:
                normalized = [(s - min_score) / score_range for s in raw_scores]
            else:
                # All scores identical -- treat them as equally relevant
                normalized = [1.0] * len(raw_scores)
        else:
            normalized = []

        # Build the final output format
        output = []
        for i, result in enumerate(reranked):
            output.append({
                "text": result["text"],
                "source": result.get("source", "unknown"),
                "distance": 1.0 - normalized[i],
                "section": result.get("section", ""),
                "retrieval_method": retrieval_method,
            })

        return output
