"""
Resume retrieval using FAISS.

Loads your resume (plain text), splits it into chunks, embeds them, and
retrieves the most relevant chunks for a given question. This keeps the
LLM grounded in YOUR actual experience instead of hallucinating.

Embeddings: uses a small local sentence-transformers model so you don't
need a second API key just to embed text.
"""
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

RESUME_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "resume.txt")
_model = None
_index = None
_chunks: list[str] = []


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """Naive word-based chunking — good enough for a single resume document."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return [c for c in chunks if c.strip()]


def build_index(force_rebuild: bool = False):
    """Build (or rebuild) the FAISS index from data/resume.txt.

    Call this once at startup, and again any time you update your resume file.
    """
    global _index, _chunks
    if _index is not None and not force_rebuild:
        return

    if not os.path.exists(RESUME_PATH):
        raise FileNotFoundError(
            f"No resume found at {RESUME_PATH}. "
            "Add a plain-text export of your resume there before using retrieval."
        )

    with open(RESUME_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    _chunks = _chunk_text(text)
    model = _get_model()
    embeddings = model.encode(_chunks, convert_to_numpy=True)
    dim = embeddings.shape[1]
    _index = faiss.IndexFlatL2(dim)
    _index.add(embeddings.astype(np.float32))


def retrieve(question: str, top_k: int = 3) -> list[str]:
    """Return the top_k most relevant resume chunks for a question."""
    if _index is None:
        build_index()
    model = _get_model()
    q_embedding = model.encode([question], convert_to_numpy=True).astype(np.float32)
    _, indices = _index.search(q_embedding, min(top_k, len(_chunks)))
    return [_chunks[i] for i in indices[0] if i < len(_chunks)]
