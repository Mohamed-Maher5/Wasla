from typing import List, Optional, TypedDict
import io

import requests
import pypdf
import docx as docx_lib
import fitz  # PyMuPDF — renders PDF pages to images for OCR fallback
import pytesseract
from PIL import Image

from app.shared.config import settings

CHUNK_SIZE_CHARS = 1500   # roughly 300-400 Arabic tokens
CHUNK_OVERLAP_CHARS = 200

HF_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/pipeline/feature-extraction"
EMBEDDING_TIMEOUT = 15  # seconds

# A page is treated as "no real text" (i.e. a scanned image, not real text)
# when pypdf extracts fewer than this many characters, and gets OCR'd
# instead. Small headers/footers on an otherwise-blank page can produce a
# handful of stray characters, so this is intentionally not just "== 0".
MIN_TEXT_CHARS_BEFORE_OCR = 20

# Tesseract language codes to run — Arabic + English covers Wasla's
# documents; "+" runs both together in one pass.
OCR_LANGUAGES = "ara+eng"

# Render resolution for OCR — higher = more accurate but slower. 200 DPI is
# a reasonable middle ground for scanned office documents.
OCR_RENDER_DPI = 200


class PageChunk(TypedDict):
    text: str
    page_number: Optional[int]  # 1-based; None when the source has no page concept (DOCX)


# ---------------------------------------------------------------------------
# Day 1: text extraction
# ---------------------------------------------------------------------------

def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Backward-compatible plain-text extraction (all pages joined).
    Kept for any caller that just wants the raw text without page info.
    """
    return "\n".join(page_text for _, page_text in extract_pages(file_bytes, filename))


def extract_pages(file_bytes: bytes, filename: str) -> List[tuple[Optional[int], str]]:
    """
    Dispatches based on file extension and returns a list of
    (page_number, text) tuples so page numbers survive into chunking.
    Raises ValueError for unsupported types so the router can return a
    400 instead of crashing.
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        return _extract_pdf_pages(file_bytes)
    elif lower.endswith(".docx"):
        return _extract_docx_pages(file_bytes)
    elif lower.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp")):
        return _extract_image_pages(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type: {filename} — only PDF, DOCX, or image "
            f"files (PNG/JPG/JPEG/BMP/TIFF/WEBP) are allowed"
        )


def _ocr_image(image: "Image.Image") -> str:
    """Runs Tesseract OCR (Arabic + English) on a single PIL image."""
    return pytesseract.image_to_string(image, lang=OCR_LANGUAGES) or ""


def _extract_pdf_pages(file_bytes: bytes) -> List[tuple[Optional[int], str]]:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages = []
    doc_for_ocr = None  # lazily opened only if a page actually needs OCR

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        # Scanned pages have no embedded text layer — pypdf returns almost
        # nothing for them. Fall back to rendering that page as an image
        # and running OCR on it, so scanned PDFs are readable too.
        if len(text.strip()) < MIN_TEXT_CHARS_BEFORE_OCR:
            if doc_for_ocr is None:
                doc_for_ocr = fitz.open(stream=file_bytes, filetype="pdf")
            try:
                pdf_page = doc_for_ocr.load_page(i)
                zoom = OCR_RENDER_DPI / 72  # PDF base unit is 72 DPI
                pix = pdf_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = _ocr_image(image)
                if ocr_text.strip():
                    print(f"[chatbot] Page {i+1}: no text layer — OCR recovered {len(ocr_text)} chars")
                    text = ocr_text
            except Exception as e:
                print(f"[chatbot] OCR failed for PDF page {i+1}: {e}")

        pages.append((i + 1, text))  # 1-based page numbers

    if doc_for_ocr is not None:
        doc_for_ocr.close()

    return pages


def _extract_docx_pages(file_bytes: bytes) -> List[tuple[Optional[int], str]]:
    # DOCX has no reliable page concept (pagination depends on the reader),
    # so the whole document is treated as one page-less block.
    doc = docx_lib.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return [(None, "\n".join(paragraphs))]


def _extract_image_pages(file_bytes: bytes) -> List[tuple[Optional[int], str]]:
    # A standalone image (screenshot, photo of a document, etc.) is
    # OCR'd directly and treated as one page-less block, same as DOCX.
    image = Image.open(io.BytesIO(file_bytes))
    text = _ocr_image(image)
    return [(None, text)]


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


def chunk_pages(pages: List[tuple[Optional[int], str]], chunk_size: int = CHUNK_SIZE_CHARS,
                 overlap: int = CHUNK_OVERLAP_CHARS) -> List[PageChunk]:
    """
    Chunks each page independently so every chunk keeps its correct
    page_number. A page's text is never merged with another page's text.
    """
    result: List[PageChunk] = []
    for page_number, page_text in pages:
        for piece in chunk_text(page_text, chunk_size=chunk_size, overlap=overlap):
            result.append({"text": piece, "page_number": page_number})
    return result


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