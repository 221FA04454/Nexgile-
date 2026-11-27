"""Text extraction. OCR is an explicit future adapter and is not faked."""
from __future__ import annotations

from typing import Protocol


class TextExtractor(Protocol):
    def extract(self, data: bytes, content_type: str, filename: str = "") -> tuple[str, str]:
        """Return (text, extractor_name)."""


class OCRExtractor:
    """Placeholder so OCR can be added later without changing the ingest pipeline."""

    def extract(self, data: bytes, content_type: str, filename: str = "") -> tuple[str, str]:
        return "", "ocr_not_configured"


def extract_text(data: bytes, content_type: str, filename: str = "") -> tuple[str, str]:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if ctype.startswith("text/") or name.endswith(".txt"):
        return data.decode("utf-8", errors="replace"), "plaintext"
    if "pdf" in ctype or name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            from io import BytesIO

            reader = PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            return "\n".join(pages).strip(), "pypdf"
        except Exception:
            return "", "pypdf_failed"
    if "wordprocessingml" in ctype or name.endswith(".docx"):
        try:
            from docx import Document
            from io import BytesIO

            doc = Document(BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs).strip(), "python_docx"
        except Exception:
            return "", "docx_failed"
    return "", "unsupported"
