import os
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import fitz  # PyMuPDF
from backend.app.core.logging import logger

# Magic numbers for file format validation
FILE_SIGNATURES = {
    b"%PDF-": "pdf",
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg"  # covers both jpg and jpeg
}


def validate_document_file(
    file_path: Union[str, Path],
    max_size_mb: int = 15,
    allowed_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Validates document existence, size constraints, and file signatures (magic bytes)
    to prevent file upload spoofing.
    """
    path = Path(file_path)
    if not path.is_file():
        return {
            "valid": False,
            "error": f"File does not exist: {file_path}",
            "file_type": None,
            "size_bytes": 0,
            "page_count": 0
        }

    size_bytes = path.stat().st_size
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        return {
            "valid": False,
            "error": f"File size ({size_bytes / (1024*1024):.2f} MB) exceeds maximum allowed {max_size_mb} MB",
            "file_type": None,
            "size_bytes": size_bytes,
            "page_count": 0
        }

    # Inspect magic bytes
    file_type = None
    with open(path, "rb") as f:
        header = f.read(16)
        for sig, ext in FILE_SIGNATURES.items():
            if header.startswith(sig):
                file_type = ext
                break

    if not file_type:
        # Fallback inspection for jpeg variants
        if header.startswith(b"\xff\xd8"):
            file_type = "jpg"

    if not file_type:
        return {
            "valid": False,
            "error": "Unsupported or corrupted file format. Expected PDF, PNG, or JPG/JPEG.",
            "file_type": None,
            "size_bytes": size_bytes,
            "page_count": 0
        }

    allowed = allowed_types or ["pdf", "png", "jpg", "jpeg"]
    if file_type not in allowed and (file_type == "jpg" and "jpeg" not in allowed and "jpg" not in allowed):
        return {
            "valid": False,
            "error": f"File type '{file_type}' is not in allowed extensions: {allowed}",
            "file_type": file_type,
            "size_bytes": size_bytes,
            "page_count": 0
        }

    page_count = 1
    if file_type == "pdf":
        try:
            with fitz.open(str(path)) as doc:
                page_count = len(doc)
                if page_count == 0:
                    return {
                        "valid": False,
                        "error": "PDF document contains 0 pages.",
                        "file_type": file_type,
                        "size_bytes": size_bytes,
                        "page_count": 0
                    }
                if page_count > 25:
                    return {
                        "valid": False,
                        "error": f"PDF document contains {page_count} pages, which exceeds the maximum allowable limit of 25 pages.",
                        "file_type": file_type,
                        "size_bytes": size_bytes,
                        "page_count": page_count
                    }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to parse PDF structure: {str(e)}",
                "file_type": file_type,
                "size_bytes": size_bytes,
                "page_count": 0
            }

    return {
        "valid": True,
        "error": None,
        "file_type": file_type,
        "size_bytes": size_bytes,
        "page_count": page_count
    }


def get_pdf_page_count(pdf_path: Union[str, Path]) -> int:
    """Returns the total number of pages in a PDF file."""
    with fitz.open(str(pdf_path)) as doc:
        return len(doc)


def convert_pdf_to_images(
    pdf_path: Union[str, Path],
    output_dir: Union[str, Path],
    dpi: int = 300,
    prefix: str = "page"
) -> List[Dict[str, Any]]:
    """
    Renders every page of a PDF document to a high-resolution PNG image (default 300 DPI)
    for visual preview and OCR ingestion.

    Returns:
        List of dicts: [
            {
                "page_number": 1,
                "image_path": "/path/to/page_1.png",
                "width": 2480,
                "height": 3508,
                "dpi": 300
            },
            ...
        ]
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    # PyMuPDF standard zoom: 72 DPI is matrix 1.0. 300 DPI is zoom = 300 / 72 ≈ 4.166667
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    logger.info(f"Rendering PDF {pdf_path} to images at {dpi} DPI...")
    with fitz.open(str(pdf_path)) as doc:
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc.load_page(page_idx)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            filename = f"{prefix}_{page_num}.png"
            image_path = out_dir / filename
            pix.save(str(image_path))

            results.append({
                "page_number": page_num,
                "image_path": str(image_path.resolve()),
                "width": pix.width,
                "height": pix.height,
                "dpi": dpi
            })

    logger.info(f"Successfully converted {len(results)} pages to PNG images.")
    return results


def extract_pdf_native_spans(pdf_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Extracts text tokens and normalized bounding boxes directly from digital/searchable PDFs.
    
    Returns:
        List of token dicts with normalized coordinates [0.0, 1.0]:
        [
            {
                "text": "INVOICE",
                "page_number": 1,
                "line_number": 0,
                "bbox": {"x1": 0.1, "y1": 0.05, "x2": 0.25, "y2": 0.08},
                "confidence": 1.0
            },
            ...
        ]
    """
    tokens: List[Dict[str, Any]] = []

    with fitz.open(str(pdf_path)) as doc:
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc.load_page(page_idx)
            page_rect = page.rect
            page_w = page_rect.width
            page_h = page_rect.height

            # 'words' returns list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            words = page.get_text("words")
            for w in words:
                x0, y0, x1, y1, word_text, block_no, line_no, word_no = w
                clean_text = word_text.strip()
                if not clean_text:
                    continue

                # Normalized coordinates
                norm_x1 = max(0.0, min(1.0, x0 / page_w))
                norm_y1 = max(0.0, min(1.0, y0 / page_h))
                norm_x2 = max(0.0, min(1.0, x1 / page_w))
                norm_y2 = max(0.0, min(1.0, y1 / page_h))

                tokens.append({
                    "text": clean_text,
                    "page_number": page_num,
                    "line_number": int(line_no),
                    "block_number": int(block_no),
                    "bbox": {
                        "x1": round(norm_x1, 4),
                        "y1": round(norm_y1, 4),
                        "x2": round(norm_x2, 4),
                        "y2": round(norm_y2, 4)
                    },
                    "confidence": 1.0  # Native vector text is 100% OCR confidence
                })

    return tokens

