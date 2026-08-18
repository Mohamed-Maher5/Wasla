from typing import List
import io

import requests
import pypdf
import docx as docx_lib

from app.shared.config import settings

CHUNK_SIZE_CHARS = 1500   # roughly 300-400 Arabic tokens
CHUNK_OVERLAP_CHARS = 200

HF_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
EMBEDDING_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Day 1: text extraction
# ---------------------------------------------------------------------------

def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Dispatches based on file extension. Raises ValueError for unsupported
    types so the router can return a 400 instead of crashing.
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    elif lower.endswith(".docx"):
        return _extract_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename} — only PDF or DOCX allowed")


def _extract_pdf(file_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text)


def _extract_docx(file_bytes: bytes) -> str:
    doc = docx_lib.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Day 2: chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS,
                overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
    """
    Simple character-based chunking with overlap. Not linguistically
    optimal, but good enough for the MVP. The overlap matters so
    information at chunk boundaries doesn't get lost.
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_len:
            break
        start = end - overlap  # step back by the overlap amount

    return chunks


# ---------------------------------------------------------------------------
# Day 2: embeddings via Hugging Face Inference API
# ---------------------------------------------------------------------------

def _call_hf_api(texts: List[str]) -> List[List[float]]:
    """
    Sends texts to the HF feature-extraction pipeline and returns
    one pooled vector per input text.

    The API returns a 3-D tensor: (batch, tokens, 384).
    We mean-pool over the token axis to get one 384-d vector per text.
    """
    if not settings.huggingface_api_key:
        raise RuntimeError(
            "HUGGINGFACE_API_KEY is not set — cannot generate embeddings"
        )

    response = requests.post(
        HF_API_URL,
        headers={"Authorization": f"Bearer {settings.huggingface_api_key}"},
        json={"inputs": texts},
        timeout=EMBEDDING_TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"HF Inference API returned {response.status_code}: "
            f"{response.text[:300]}"
        )

    # The API may return:
    #   - List[List[float]]  — one vector per input text (already pooled)
    #   - List[List[List[float]]]  — one vector per token per text (needs pooling)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        raise RuntimeError(f"Unexpected HF API response shape: {type(data)}")

    # Determine shape: is data[0] a float (flat vector) or a list (nested)?
    if isinstance(data[0], list) and len(data[0]) > 0 and isinstance(data[0][0], (int, float)):
        # Already pooled — each element is a flat vector [384]
        vectors: List[List[float]] = [list(v) for v in data]
    elif isinstance(data[0], list) and len(data[0]) > 0 and isinstance(data[0][0], list):
        # 3D — mean-pool over tokens for each text
        vectors = []
        for token_embs in data:
            non_zero = [t for t in token_embs if any(v != 0.0 for v in t)]
            if not non_zero:
                raise RuntimeError("All token embeddings are zero — input may be empty")
            dim = len(non_zero[0])
            pooled = [sum(t[i] for t in non_zero) / len(non_zero) for i in range(dim)]
            vectors.append(pooled)
    else:
        raise RuntimeError(f"Unrecognized HF API response shape: {type(data[0])}")

    return vectors


def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """Converts all chunks to vectors in one batch call instead of looping."""
    if not chunks:
        return []
    return _call_hf_api(chunks)


def embed_query(question: str) -> List[float]:
    """Same model used at ingestion time, so the vector space matches."""
    vectors = _call_hf_api([question])
    return vectors[0]
