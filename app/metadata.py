"""
PDF Metadata Extraction for ArXivMind

Extracts paper titles from PDFs using a 3-strategy cascade:
1. PDF metadata title field (if meaningful)
2. First-page largest-font text via PyMuPDF
3. Cleaned filename fallback
"""
import re
from pathlib import Path
import fitz  # pymupdf


def _is_arxiv_id(text: str) -> bool:
    """Check if text looks like an arXiv ID (e.g., 2301.12345, 2301.12345v2)."""
    return bool(re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", text.strip()))


def _is_filename_like(title: str, pdf_path: Path) -> bool:
    """Check if the title is just the filename stem or empty."""
    stem = pdf_path.stem
    if not title or not title.strip():
        return True
    # Exact match with stem
    if title.strip() == stem:
        return True
    # Match with .pdf extension
    if title.strip() == pdf_path.name:
        return True
    return False


def _title_from_metadata(pdf_path: Path) -> str | None:
    """Strategy 1: Extract title from PDF metadata field."""
    try:
        doc = fitz.open(str(pdf_path))
        metadata = doc.metadata
        doc.close()
        if metadata and metadata.get("title"):
            title = metadata["title"].strip()
            if not title:
                return None
            if _is_filename_like(title, pdf_path):
                return None
            if _is_arxiv_id(title):
                return None
            return title
    except Exception:
        pass
    return None


def _title_from_largest_font(pdf_path: Path) -> str | None:
    """Strategy 2: Extract title from first-page largest-font text."""
    try:
        doc = fitz.open(str(pdf_path))
        if len(doc) == 0:
            doc.close()
            return None
        page = doc[0]
        text_dict = page.get_text("dict")
        doc.close()

        max_size = 0.0
        max_text = ""

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # type 0 = text block
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()
                    if text and size > max_size:
                        max_size = size
                        max_text = text

        if max_text:
            # Clean up and limit length
            title = max_text.strip()[:200].strip()
            if title and not _is_arxiv_id(title):
                return title
    except Exception:
        pass
    return None


def _title_from_filename(pdf_path: Path) -> str:
    """Strategy 3: Clean filename as fallback title."""
    name = pdf_path.stem
    # Strip arXiv ID patterns (e.g., 2301.12345v2, 2301.12345)
    name = re.sub(r"\d{4}\.\d{4,5}(?:v\d+)?", "", name)
    # Replace underscores and hyphens with spaces
    name = name.replace("_", " ").replace("-", " ")
    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name).strip()
    # Title-case
    if name:
        name = name.title()
    else:
        name = pdf_path.stem.title()
    return name


def extract_title(pdf_path: Path) -> str:
    """Extract paper title using a 3-strategy cascade.

    1. PDF metadata title field (reject if empty, filename-like, or arXiv ID)
    2. First-page largest-font text via PyMuPDF
    3. Cleaned filename fallback

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted title string.
    """
    # Strategy 1: PDF metadata
    title = _title_from_metadata(pdf_path)
    if title:
        return title

    # Strategy 2: Largest font on first page
    title = _title_from_largest_font(pdf_path)
    if title:
        return title

    # Strategy 3: Cleaned filename
    return _title_from_filename(pdf_path)
