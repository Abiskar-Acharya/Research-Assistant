"""
RAGAS-Inspired Evaluation Framework for GLM-4 RAG Pipeline

Uses GLM-4 via Ollama as the judge model to evaluate RAG quality
across four dimensions: faithfulness, answer relevancy,
context precision, and context recall.
"""
import os
import requests
import json
import re
from typing import List, Dict


# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL_NAME = os.environ.get("MODEL_NAME", "glm-4.7-flash")


class RAGEvaluator:
    """
    RAGAS-inspired evaluation framework that uses GLM-4 as a judge model
    to score RAG pipeline outputs across four key metrics.
    """

    def __init__(self, ollama_url: str = OLLAMA_URL, model_name: str = MODEL_NAME):
        """
        Initialize the evaluator with Ollama configuration.

        Args:
            ollama_url: Base URL for the Ollama API server.
            model_name: Name of the model to use for evaluation judgments.
        """
        self.ollama_url = ollama_url
        self.model_name = model_name

    def query_llm(self, prompt: str) -> str:
        """
        Call the Ollama API to generate a response from the judge model.

        Args:
            prompt: The prompt to send to the model.

        Returns:
            The model's text response, or an error message string.
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "No response from model")
        except requests.exceptions.Timeout:
            return "Error: LLM request timed out after 120 seconds"
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to Ollama server"
        except Exception as e:
            return f"Error calling LLM: {str(e)}"

    def _parse_score(self, response: str) -> float:
        """
        Robustly parse a numeric score from an LLM response.

        Handles formats like: "7", "7/10", "7 out of 10", "Score: 7",
        "I would rate this a 7.5", etc.

        Args:
            response: The raw text response from the judge model.

        Returns:
            A float normalized to 0.0-1.0 range. Defaults to 0.5 on parse failure.
        """
        if not response or response.startswith("Error"):
            return 0.5

        # Try to find a decimal or integer number in the response.
        # Prioritize patterns like "X/10" or "X out of 10" first.
        pattern_fraction = re.search(r"(\d+(?:\.\d+)?)\s*(?:/|out of)\s*10", response)
        if pattern_fraction:
            score = float(pattern_fraction.group(1))
            return max(0.0, min(1.0, score / 10.0))

        # Look for any number (first occurrence) in the response.
        pattern_number = re.search(r"(\d+(?:\.\d+)?)", response)
        if pattern_number:
            score = float(pattern_number.group(1))
            # If the number is in 0-10 range, normalize to 0-1.
            if 0.0 <= score <= 10.0:
                return score / 10.0
            # If somehow larger than 10, clamp.
            if score > 10.0:
                return 1.0
            return 0.0

        # If no number found at all, return neutral default.
        return 0.5

    def score_faithfulness(self, answer: str, context: str) -> float:
        """
        Judge whether every claim in the answer is grounded in the context.

        A faithful answer makes no claims that cannot be traced back to
        the provided context.

        Args:
            answer: The generated answer to evaluate.
            context: The retrieved context that the answer should be grounded in.

        Returns:
            A float from 0.0 (completely unfaithful) to 1.0 (fully faithful).
        """
        prompt = (
            "You are an impartial judge evaluating the faithfulness of an AI-generated answer.\n\n"
            "Faithfulness measures whether every claim in the answer is supported by the given context. "
            "An answer is faithful if it makes no claims that go beyond what the context states.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"ANSWER:\n{answer}\n\n"
            "Given the context, is every claim in the answer supported? "
            "Rate the faithfulness on a scale of 0 to 10, where:\n"
            "  0 = The answer is entirely fabricated with no basis in the context\n"
            "  5 = Some claims are supported, but others are not\n"
            "  10 = Every single claim in the answer is directly supported by the context\n\n"
            "Respond with ONLY a single number from 0 to 10."
        )
        response = self.query_llm(prompt)
        return self._parse_score(response)

    def score_answer_relevancy(self, question: str, answer: str) -> float:
        """
        Judge whether the answer directly and completely addresses the question.

        A relevant answer focuses on what was asked without going off-topic
        or providing irrelevant information.

        Args:
            question: The original question that was asked.
            answer: The generated answer to evaluate.

        Returns:
            A float from 0.0 (completely irrelevant) to 1.0 (perfectly relevant).
        """
        prompt = (
            "You are an impartial judge evaluating the relevancy of an AI-generated answer to a question.\n\n"
            "Answer relevancy measures whether the answer directly addresses the question asked. "
            "A relevant answer is focused, on-topic, and provides the information the question seeks.\n\n"
            f"QUESTION:\n{question}\n\n"
            f"ANSWER:\n{answer}\n\n"
            "Does the answer directly and completely address the question? "
            "Rate the answer relevancy on a scale of 0 to 10, where:\n"
            "  0 = The answer is completely irrelevant to the question\n"
            "  5 = The answer partially addresses the question but misses key aspects\n"
            "  10 = The answer perfectly and completely addresses exactly what was asked\n\n"
            "Respond with ONLY a single number from 0 to 10."
        )
        response = self.query_llm(prompt)
        return self._parse_score(response)

    def score_context_precision(self, question: str, contexts: List[str]) -> float:
        """
        Judge whether the retrieved contexts are relevant to the question.

        Context precision measures the signal-to-noise ratio of retrieved chunks.
        High precision means most retrieved contexts are actually useful.

        Args:
            question: The original question.
            contexts: List of retrieved context strings.

        Returns:
            A float from 0.0 (no relevant contexts) to 1.0 (all contexts relevant).
        """
        if not contexts:
            return 0.0

        scores = []
        for i, context in enumerate(contexts):
            prompt = (
                "You are an impartial judge evaluating whether a retrieved context passage "
                "is relevant to answering a question.\n\n"
                "Context precision measures whether the retrieved passage contains information "
                "that would be useful for answering the question.\n\n"
                f"QUESTION:\n{question}\n\n"
                f"RETRIEVED CONTEXT (passage {i + 1}):\n{context}\n\n"
                "Is this context passage relevant and useful for answering the question? "
                "Rate the relevance on a scale of 0 to 10, where:\n"
                "  0 = The passage is completely irrelevant to the question\n"
                "  5 = The passage has some tangential relevance but is mostly unhelpful\n"
                "  10 = The passage is highly relevant and directly useful for answering\n\n"
                "Respond with ONLY a single number from 0 to 10."
            )
            response = self.query_llm(prompt)
            scores.append(self._parse_score(response))

        return sum(scores) / len(scores)

    def score_context_recall(self, answer: str, contexts: List[str]) -> float:
        """
        Judge whether the contexts contain enough information to produce the answer.

        Context recall measures if the retrieval step found all the information
        needed to generate a complete answer.

        Args:
            answer: The generated answer.
            contexts: List of retrieved context strings.

        Returns:
            A float from 0.0 (contexts lack needed info) to 1.0 (contexts fully sufficient).
        """
        if not contexts:
            return 0.0

        combined_context = "\n\n---\n\n".join(
            f"[Context {i + 1}]: {ctx}" for i, ctx in enumerate(contexts)
        )

        prompt = (
            "You are an impartial judge evaluating context recall for a RAG system.\n\n"
            "Context recall measures whether the retrieved context passages collectively contain "
            "enough information to produce the given answer. High recall means no important "
            "information is missing from the retrieved contexts.\n\n"
            f"RETRIEVED CONTEXTS:\n{combined_context}\n\n"
            f"ANSWER THAT WAS GENERATED:\n{answer}\n\n"
            "Do the retrieved contexts contain sufficient information to support generating "
            "this answer? Rate the context recall on a scale of 0 to 10, where:\n"
            "  0 = The contexts contain none of the information needed for the answer\n"
            "  5 = The contexts contain some information but key details are missing\n"
            "  10 = The contexts contain all the information needed to fully produce the answer\n\n"
            "Respond with ONLY a single number from 0 to 10."
        )
        response = self.query_llm(prompt)
        return self._parse_score(response)

    def evaluate(self, question: str, answer: str, contexts: List[str]) -> Dict:
        """
        Run all four evaluation metrics on a single RAG result.

        Args:
            question: The original question.
            answer: The generated answer.
            contexts: List of retrieved context strings used to generate the answer.

        Returns:
            Dictionary with individual metric scores and an overall average score.
            Keys: faithfulness, answer_relevancy, context_precision, context_recall, overall.
        """
        combined_context = "\n\n".join(contexts) if contexts else ""

        faithfulness = self.score_faithfulness(answer, combined_context)
        answer_relevancy = self.score_answer_relevancy(question, answer)
        context_precision = self.score_context_precision(question, contexts)
        context_recall = self.score_context_recall(answer, contexts)

        overall = (faithfulness + answer_relevancy + context_precision + context_recall) / 4.0

        return {
            "faithfulness": round(faithfulness, 4),
            "answer_relevancy": round(answer_relevancy, 4),
            "context_precision": round(context_precision, 4),
            "context_recall": round(context_recall, 4),
            "overall": round(overall, 4),
        }

    def generate_qa_pairs(
        self, text: str, source: str, n_pairs: int = 3
    ) -> List[Dict]:
        """
        Use the judge model to generate gold-standard Q&A pairs from paper text.

        These pairs can be used as ground truth for evaluating the RAG pipeline.

        Args:
            text: The source text (e.g., from a research paper).
            source: Identifier for the source document (e.g., filename).
            n_pairs: Number of Q&A pairs to generate.

        Returns:
            List of dicts, each with keys: question, answer, source.
        """
        prompt = (
            "You are a research assistant creating evaluation data for a question-answering system.\n\n"
            f"Given the following text from a research paper, generate exactly {n_pairs} "
            "factual question-answer pairs. Each question should be answerable ONLY from "
            "the provided text. Each answer should be concise and directly supported by the text.\n\n"
            f"SOURCE TEXT:\n{text[:3000]}\n\n"
            f"Generate exactly {n_pairs} Q&A pairs in the following JSON format:\n"
            "[\n"
            '  {"question": "Your question here?", "answer": "Your answer here."},\n'
            '  {"question": "Your question here?", "answer": "Your answer here."}\n'
            "]\n\n"
            "Respond with ONLY the JSON array, no other text."
        )

        response = self.query_llm(prompt)

        # Try to parse the JSON response.
        qa_pairs = []
        try:
            # Find JSON array in the response (the model may add extra text).
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "question" in item and "answer" in item:
                            qa_pairs.append(
                                {
                                    "question": str(item["question"]),
                                    "answer": str(item["answer"]),
                                    "source": source,
                                }
                            )
        except (json.JSONDecodeError, AttributeError):
            pass

        # If JSON parsing failed or returned too few pairs, try line-by-line extraction.
        if len(qa_pairs) < n_pairs:
            lines = response.strip().split("\n")
            current_q = None
            for line in lines:
                line = line.strip()
                q_match = re.match(r"(?:Q\d*[:.]|Question\s*\d*[:.])?\s*(.+\?)", line, re.IGNORECASE)
                a_match = re.match(r"(?:A\d*[:.]|Answer\s*\d*[:.])?\s*(.+)", line, re.IGNORECASE)

                if q_match and line.endswith("?"):
                    current_q = q_match.group(1).strip()
                elif a_match and current_q and not line.endswith("?"):
                    qa_pairs.append(
                        {
                            "question": current_q,
                            "answer": a_match.group(1).strip(),
                            "source": source,
                        }
                    )
                    current_q = None

                if len(qa_pairs) >= n_pairs:
                    break

        return qa_pairs[:n_pairs]

    def run_evaluation_suite(
        self, rag_pipeline, qa_pairs: List[Dict]
    ) -> Dict:
        """
        Run a full evaluation suite over a list of Q&A pairs using the RAG pipeline.

        For each Q&A pair, queries the pipeline, evaluates the result, and
        computes aggregate scores across all pairs.

        Args:
            rag_pipeline: An object with a `rag_query(question)` method that returns
                          a dict with keys: answer, sources (list of dicts with 'text').
            qa_pairs: List of dicts with keys: question, answer, source.

        Returns:
            Dictionary with per-pair results and aggregate metric averages.
        """
        results = []
        aggregate = {
            "faithfulness": [],
            "answer_relevancy": [],
            "context_precision": [],
            "context_recall": [],
            "overall": [],
        }

        for i, qa_pair in enumerate(qa_pairs):
            question = qa_pair["question"]
            expected_answer = qa_pair.get("answer", "")

            # Run the RAG pipeline to get an answer.
            try:
                pipeline_result = rag_pipeline.rag_query(question)
                generated_answer = pipeline_result.get("answer", "")
                sources = pipeline_result.get("sources", [])
                contexts = [s.get("text", "") for s in sources if isinstance(s, dict)]
            except Exception as e:
                generated_answer = f"Pipeline error: {str(e)}"
                contexts = []

            # Evaluate the result.
            scores = self.evaluate(question, generated_answer, contexts)

            result_entry = {
                "pair_index": i,
                "question": question,
                "expected_answer": expected_answer,
                "generated_answer": generated_answer,
                "num_contexts": len(contexts),
                "scores": scores,
            }
            results.append(result_entry)

            # Accumulate for aggregation.
            for metric in aggregate:
                aggregate[metric].append(scores[metric])

        # Compute aggregate averages.
        num_pairs = len(qa_pairs) if qa_pairs else 1
        aggregate_scores = {
            metric: round(sum(values) / max(len(values), 1), 4)
            for metric, values in aggregate.items()
        }

        return {
            "num_pairs_evaluated": len(results),
            "aggregate_scores": aggregate_scores,
            "per_pair_results": results,
        }
