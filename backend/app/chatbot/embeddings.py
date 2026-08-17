from typing import List
import io
 
import pypdf
import docx as docx_lib
from sentence_transformers import SentenceTransformer
 
CHUNK_SIZE_CHARS = 1500   # roughly 300-400 Arabic tokens
CHUNK_OVERLAP_CHARS = 200
 
# Free local model — loaded once when the server starts
_local_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
 
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
# Day 2: embeddings (temporary local version instead of OpenAI)
# ---------------------------------------------------------------------------
 
def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """Converts all chunks to vectors in one batch call instead of looping."""
    if not chunks:
        return []
 
    vectors = _local_model.encode(chunks, convert_to_numpy=True)
    return vectors.tolist()
 
 
def embed_query(question: str) -> List[float]:
    """Same model used at ingestion time, so the vector space matches."""
    vector = _local_model.encode([question], convert_to_numpy=True)[0]
    return vector.tolist()
 