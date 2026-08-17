"""
OCR Service — tiered strategy:
1. Docling       — primary document parser (layout-aware)
2. HunyuanOCR   — primary OCR for complex pages (GPU preferred)
3. PaddleOCR    — fallback OCR
4. PyMuPDF      — fast text-layer extraction (no OCR needed for digital PDFs)
5. pdfplumber   — table extraction
6. Apache Tika  — universal fallback for non-PDF files
7. Tesseract    — last resort OCR
"""
import fitz  # PyMuPDF
import structlog
from core.config import settings

log = structlog.get_logger()


def extract_text_pymupdf(pdf_bytes: bytes, max_pages: int = 40) -> str:
    """Fast extraction for text-layer PDFs."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = min(len(doc), max_pages)
        parts = []
        for i in range(pages):
            text = doc[i].get_text("text").strip()
            if text:
                parts.append(text)
        doc.close()
        return "\n\n".join(parts)
    except Exception as e:
        log.warning("pymupdf.failed", error=str(e))
        return ""


def extract_text_pdfplumber(pdf_bytes: bytes, max_pages: int = 40) -> str:
    """Table-aware extraction via pdfplumber."""
    try:
        import pdfplumber
        import io
        parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                text = page.extract_text() or ""
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        text += " | ".join(str(c) for c in row if c) + "\n"
                parts.append(text)
        return "\n\n".join(parts)
    except Exception as e:
        log.warning("pdfplumber.failed", error=str(e))
        return ""


def extract_text_paddle(image_bytes: bytes) -> str:
    """PaddleOCR — fallback for scanned pages."""
    try:
        from paddleocr import PaddleOCR
        import numpy as np
        from PIL import Image
        import io

        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        result = ocr.ocr(arr, cls=True)
        lines = []
        for block in (result or []):
            if block:
                for line in block:
                    if line and line[1]:
                        lines.append(line[1][0])
        return " ".join(lines)
    except Exception as e:
        log.warning("paddle.ocr.failed", error=str(e))
        return ""


def extract_text_tesseract(image_bytes: bytes) -> str:
    """Tesseract — last resort OCR."""
    try:
        import pytesseract
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img, lang="eng")
    except Exception as e:
        log.warning("tesseract.failed", error=str(e))
        return ""


def extract_text_tika(file_bytes: bytes, filename: str = "doc.pdf") -> str:
    """Apache Tika — universal parser for any file type."""
    try:
        from tika import parser as tika_parser
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as f:
            f.write(file_bytes)
            tmp = f.name
        parsed = tika_parser.from_file(tmp)
        os.unlink(tmp)
        return parsed.get("content", "") or ""
    except Exception as e:
        log.warning("tika.failed", error=str(e))
        return ""


def extract_text_docling(pdf_bytes: bytes) -> str:
    """Docling — primary layout-aware parser."""
    try:
        from docling.document_converter import DocumentConverter
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(pdf_bytes)
            tmp = f.name
        converter = DocumentConverter()
        result = converter.convert(tmp)
        os.unlink(tmp)
        return result.document.export_to_markdown()
    except Exception as e:
        log.warning("docling.failed", error=str(e))
        return ""


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Master extraction function — tries best method first.
    Digital PDF  → PyMuPDF (instant)
    Layout doc   → Docling
    Scanned PDF  → PaddleOCR → Tesseract fallback
    """
    # 1. Try fast PyMuPDF first
    text = extract_text_pymupdf(pdf_bytes)
    if len(text.strip()) > 200:
        log.info("ocr.method", method="pymupdf", chars=len(text))
        return text

    # 2. Try Docling for complex layouts
    text = extract_text_docling(pdf_bytes)
    if len(text.strip()) > 200:
        log.info("ocr.method", method="docling", chars=len(text))
        return text

    # 3. Render pages and OCR them
    log.info("ocr.method", method="render+ocr")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = []
    for i in range(min(len(doc), 30)):
        pix = doc[i].get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")

        # Try PaddleOCR first
        ocr_text = extract_text_paddle(img_bytes)
        if not ocr_text.strip():
            ocr_text = extract_text_tesseract(img_bytes)
        if ocr_text.strip():
            parts.append(ocr_text)

    doc.close()
    return "\n\n".join(parts)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split into overlapping chunks for RAG."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            bp = text.rfind(".", start, end)
            if bp > start + chunk_size // 2:
                end = bp + 1
        chunk = text[start:end].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
        start = end - overlap
    return chunks
