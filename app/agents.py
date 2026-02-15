"""
Research Analysis Agents: Higher-order analysis using the RAG pipeline.

Provides specialized agents for research synthesis, trend analysis,
and gap identification across indexed research papers.
"""
from typing import Dict, List


class ResearchAgents:
    """Research analysis agents that use the RAG pipeline for higher-order analysis."""

    AGENT_TYPES = ("synthesize", "trends", "gaps")

    def __init__(self, rag_pipeline):
        """Initialize with a RAG pipeline instance.

        Args:
            rag_pipeline: An object exposing search_similar(query, n) and
                          query_glm4(prompt) methods.
        """
        self.rag_pipeline = rag_pipeline

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _search_and_build_context(
        self, topic: str, n_results: int
    ) -> tuple:
        """Search for relevant chunks and build a formatted context string.

        Returns:
            A tuple of (context_str, sources_list).  If no chunks are found,
            context_str will be empty and sources_list will be an empty list.
        """
        chunks: List[Dict] = self.rag_pipeline.search_similar(topic, n_results)

        if not chunks:
            return "", []

        context = "\n\n".join(
            f"[From {chunk['source']}]\n{chunk['text']}"
            for chunk in chunks
        )

        sources = [
            {
                "source": chunk["source"],
                "text": chunk["text"],
                "distance": chunk["distance"],
            }
            for chunk in chunks
        ]

        return context, sources

    def _no_results_response(self, topic: str, agent_type: str) -> Dict:
        """Return a structured response when no relevant chunks are found."""
        return {
            "question": topic,
            "analysis": (
                f"No relevant information found in the indexed papers for "
                f"'{topic}'. Please ensure papers are indexed and try a "
                f"different query."
            ),
            "sources": [],
            "agent_type": agent_type,
        }

    # ------------------------------------------------------------------
    # Agent methods
    # ------------------------------------------------------------------

    def synthesize(self, topic: str, n_results: int = 10) -> Dict:
        """Synthesis agent -- synthesize findings across multiple papers.

        Searches for chunks related to *topic*, then asks GLM-4 to produce
        a comprehensive synthesis identifying common findings, contradictions,
        strongest evidence, and overarching conclusions.
        """
        context, sources = self._search_and_build_context(topic, n_results)

        if not context:
            return self._no_results_response(topic, "synthesize")

        prompt = (
            "You are a research synthesis expert. Given excerpts from "
            f"multiple research papers about {topic}, provide a "
            "comprehensive synthesis that: "
            "1) Identifies common findings, "
            "2) Notes contradictions or disagreements, "
            "3) Highlights the strongest evidence, "
            "4) Draws overarching conclusions."
            "\n\nResearch excerpts:\n"
            f"{context}"
            "\n\nSynthesis:"
        )

        analysis = self.rag_pipeline.query_glm4(prompt)

        return {
            "question": topic,
            "analysis": analysis,
            "sources": sources,
            "agent_type": "synthesize",
        }

    def analyze_trends(self, topic: str, n_results: int = 10) -> Dict:
        """Trend analysis agent -- identify research trends and directions.

        Searches for chunks related to *topic*, then asks GLM-4 to identify
        emerging trends, methodology evolution, shifts in focus, and
        predicted future directions.
        """
        context, sources = self._search_and_build_context(topic, n_results)

        if not context:
            return self._no_results_response(topic, "trends")

        prompt = (
            "You are a research trend analyst. Given excerpts from "
            f"research papers about {topic}, identify: "
            "1) Emerging trends and directions, "
            "2) Evolution of methodologies over time, "
            "3) Shifts in research focus, "
            "4) Predicted future directions based on current trajectory."
            "\n\nResearch excerpts:\n"
            f"{context}"
            "\n\nTrend Analysis:"
        )

        analysis = self.rag_pipeline.query_glm4(prompt)

        return {
            "question": topic,
            "analysis": analysis,
            "sources": sources,
            "agent_type": "trends",
        }

    def find_gaps(self, topic: str, n_results: int = 10) -> Dict:
        """Gap finding agent -- identify research gaps and opportunities.

        Searches for chunks related to *topic*, then asks GLM-4 to identify
        under-explored areas, methodological limitations, contradictions,
        missing perspectives, and suggested future work.
        """
        context, sources = self._search_and_build_context(topic, n_results)

        if not context:
            return self._no_results_response(topic, "gaps")

        prompt = (
            "You are a research gap analyst. Given excerpts from "
            f"research papers about {topic}, identify: "
            "1) Under-explored areas mentioned but not studied, "
            "2) Methodological limitations acknowledged by authors, "
            "3) Contradictions that need resolution, "
            "4) Missing perspectives or populations, "
            "5) Suggested future work by authors."
            "\n\nResearch excerpts:\n"
            f"{context}"
            "\n\nGap Analysis:"
        )

        analysis = self.rag_pipeline.query_glm4(prompt)

        return {
            "question": topic,
            "analysis": analysis,
            "sources": sources,
            "agent_type": "gaps",
        }

    def run_agent(
        self, agent_type: str, question: str, n_results: int = 10
    ) -> Dict:
        """Route to the appropriate agent method based on *agent_type*.

        Args:
            agent_type: One of "synthesize", "trends", or "gaps".
            question:   The research topic / question to analyze.
            n_results:  Number of chunks to retrieve from the vector store.

        Returns:
            The structured response dict from the chosen agent.

        Raises:
            ValueError: If *agent_type* is not recognized.
        """
        router = {
            "synthesize": self.synthesize,
            "trends": self.analyze_trends,
            "gaps": self.find_gaps,
        }

        agent_fn = router.get(agent_type)
        if agent_fn is None:
            raise ValueError(
                f"Unknown agent_type '{agent_type}'. "
                f"Must be one of: {', '.join(self.AGENT_TYPES)}"
            )

        return agent_fn(question, n_results)
