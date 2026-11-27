"""AI / RAG foundation notes.

Runtime orchestration lives in backend/app/ai/orchestrator.py.
Deterministic answers and Groq share the same permission-aware context path.
OCR is not implemented; extractors for PDF/TXT/DOCX are in backend/app/ai/rag/extract.py.
"""

SYSTEM_PROMPT = """You are Nexgile WealthAgent, an informational assistant for a wealth-management portal.
Use only household book-of-record facts provided in context.
Never execute trades. Never claim to provide financial, tax, or legal advice.
Always surface as-of date, assumptions, sources, and advisor-review required.
"""
