"""
Section-Aware Smart Chunking for Research Papers

Detects academic paper sections (Abstract, Introduction, Methods, etc.)
and produces semantically meaningful chunks that respect both section
boundaries and sentence boundaries. Falls back to sentence-boundary
chunking when section headers are not detected.
"""
import re
from typing import List, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Section header patterns
# ---------------------------------------------------------------------------
# Each pattern is designed to match common academic formatting variants:
#   ABSTRACT / Abstract / 1. Introduction / II. Methods / 3 RESULTS AND DISCUSSION
# We capture the canonical section name from each match.

_SECTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Abstract — often standalone, no numbering
    (re.compile(
        r"^[\s]*(?:abstract)[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Abstract"),

    # Introduction
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?introduction[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Introduction"),

    # Background
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?background[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Background"),

    # Related Work
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?related[\s]+work[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Related Work"),

    # Methods / Methodology
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?(?:methods?|methodology)[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Methods"),

    # Results (including compound headers like "Results and Discussion")
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?results(?:\s+and\s+discussion)?[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Results"),

    # Discussion (standalone)
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?discussion[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Discussion"),

    # Conclusion(s)
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?conclusions?[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Conclusion"),

    # Limitations
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?limitations?[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "Limitations"),

    # References / Bibliography
    (re.compile(
        r"^[\s]*(?:[0-9]+[.\s]*|[IVX]+[.\s]+)?(?:references|bibliography)[\s]*$",
        re.IGNORECASE | re.MULTILINE,
    ), "References"),
]

# Sentence-ending punctuation followed by whitespace (space, newline, or end)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?:\s+)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> List[str]:
    """Split *text* into sentences using punctuation + whitespace boundaries.

    Keeps each sentence's trailing punctuation attached.  Empty fragments
    are discarded.
    """
    parts = _SENTENCE_BOUNDARY.split(text)
    return [s.strip() for s in parts if s.strip()]


# ---------------------------------------------------------------------------
# SectionChunker
# ---------------------------------------------------------------------------

class SectionChunker:
    """Section-aware chunker for academic research papers.

    Parameters
    ----------
    chunk_size : int
        Target maximum character length per chunk (default 500).
    overlap_ratio : float
        Fraction of *chunk_size* used as overlap between consecutive
        chunks within the same section (default 0.12 = 12 %).
    """

    SECTION_CHUNK_SIZES = {
        "Abstract": 2000,
        "Methods": 1000,
        "Methodology": 1000,
        "Results": 800,
    }
    DEFAULT_CHUNK_SIZE = 500

    def __init__(
        self,
        chunk_size: int = 500,
        overlap_ratio: float = 0.12,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap_ratio = overlap_ratio

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_sections(self, text: str) -> List[Dict]:
        """Detect academic sections in *text*.

        Returns a list of ``{"section": name, "text": content}`` dicts
        ordered by their appearance in the document.  If no sections are
        detected the entire text is returned under the section name
        ``"Full Text"``.
        """
        # Collect all matches with their positions
        matches: List[Tuple[int, int, str]] = []  # (start, end, section_name)
        for pattern, section_name in _SECTION_PATTERNS:
            for m in pattern.finditer(text):
                matches.append((m.start(), m.end(), section_name))

        if not matches:
            # Fallback — no recognisable sections
            return [{"section": "Full Text", "text": text}]

        # Sort by position in the document
        matches.sort(key=lambda t: t[0])

        sections: List[Dict] = []

        # Text before the first detected header (e.g. title / author block)
        pre_text = text[: matches[0][0]].strip()
        if pre_text:
            sections.append({"section": "Preamble", "text": pre_text})

        for idx, (start, end, name) in enumerate(matches):
            # Content runs from end of this header to start of the next
            if idx + 1 < len(matches):
                content = text[end: matches[idx + 1][0]]
            else:
                content = text[end:]

            content = content.strip()
            if content:
                sections.append({"section": name, "text": content})

        return sections

    def chunk_section(
        self,
        section_text: str,
        section_name: str,
        source: str,
        start_id: int = 0,
        effective_chunk_size: Optional[int] = None,
    ) -> List[Dict]:
        """Chunk a single section's text into overlapping pieces.

        Each chunk respects sentence boundaries so no word is cut in
        half.  Returns a list of dicts with keys
        ``text``, ``section``, ``source``, ``chunk_id``.

        Parameters
        ----------
        effective_chunk_size : int, optional
            Override ``self.chunk_size`` for this call. Used by
            ``chunk_paper`` to apply section-specific sizes.
        """
        chunk_size = effective_chunk_size if effective_chunk_size is not None else self.chunk_size

        sentences = _split_sentences(section_text)
        if not sentences:
            return []

        overlap_chars = int(chunk_size * self.overlap_ratio)
        chunks: List[Dict] = []
        chunk_id = start_id

        current_sentences: List[str] = []
        current_len = 0

        i = 0
        while i < len(sentences):
            sentence = sentences[i]

            # If adding this sentence still fits, accumulate
            projected = current_len + len(sentence) + (1 if current_sentences else 0)
            if projected <= chunk_size or not current_sentences:
                current_sentences.append(sentence)
                current_len = projected
                i += 1
            else:
                # Emit current chunk
                chunk_text = " ".join(current_sentences)
                chunks.append({
                    "text": chunk_text,
                    "section": section_name,
                    "source": source,
                    "chunk_id": chunk_id,
                })
                chunk_id += 1

                # Rewind for overlap — walk backwards through accumulated
                # sentences until we have at least *overlap_chars* worth.
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_sentences):
                    if overlap_len + len(s) + (1 if overlap_sentences else 0) > overlap_chars:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s) + (1 if len(overlap_sentences) > 1 else 0)

                current_sentences = list(overlap_sentences)
                current_len = sum(len(s) for s in current_sentences) + max(0, len(current_sentences) - 1)
                # Do NOT advance *i* — the sentence that didn't fit will
                # be reconsidered on the next iteration.

        # Flush remaining sentences
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append({
                "text": chunk_text,
                "section": section_name,
                "source": source,
                "chunk_id": chunk_id,
            })

        return chunks

    def chunk_paper(self, text: str, source: str) -> List[Dict]:
        """Main entry point: chunk an entire paper's text.

        1. Detect sections in *text*.
        2. For each section, produce sentence-boundary-respecting chunks
           with the configured overlap.
        3. Return a flat list of chunk dicts, each with a globally unique
           ``chunk_id``.
        """
        sections = self.detect_sections(text)

        all_chunks: List[Dict] = []
        running_id = 0

        for section in sections:
            section_name = section["section"]
            effective_size = self.SECTION_CHUNK_SIZES.get(section_name, self.chunk_size)
            new_chunks = self.chunk_section(
                section_text=section["text"],
                section_name=section_name,
                source=source,
                start_id=running_id,
                effective_chunk_size=effective_size,
            )
            all_chunks.extend(new_chunks)
            running_id += len(new_chunks)

        return all_chunks
