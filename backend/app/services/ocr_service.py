from typing import List, Dict, Any, Union, Optional
from pathlib import Path
from pydantic import BaseModel, Field
import fitz  # PyMuPDF
from backend.app.core.logging import logger

# Lazy load PaddleOCR if available
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logger.info("PaddleOCR not installed in current environment; using PyMuPDF OCR engine.")


class OCRToken(BaseModel):
    text: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    page_number: int = 1
    line_number: int = 0
    block_number: int = 0
    bbox: Dict[str, float] = Field(
        ...,
        description="Normalized coordinates: {'x1': float, 'y1': float, 'x2': float, 'y2': float} in [0, 1]"
    )


class OCRPageResult(BaseModel):
    page_number: int
    width: int
    height: int
    tokens: List[OCRToken] = []
    full_text: str = ""
    mean_confidence: float = 1.0


class OCRDocumentResult(BaseModel):
    document_id: str
    total_pages: int
    pages: List[OCRPageResult] = []
    full_text: str = ""
    mean_confidence: float = 1.0


class OCRService:
    """
    Robust OCR engine providing document text extraction, word/line-level bounding boxes,
    and confidence scores. Supports PaddleOCR when available and PyMuPDF engine as
    a rock-solid fallback.
    """

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._paddle_ocr = None

    def _get_paddle_ocr(self):
        if not PADDLE_AVAILABLE:
            return None
        if self._paddle_ocr is None:
            logger.info("Initializing PaddleOCR engine...")
            try:
                self._paddle_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False
                )
                logger.info("PaddleOCR engine initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize PaddleOCR: {e}. Falling back to PyMuPDF.")
                self._paddle_ocr = False
        return self._paddle_ocr if self._paddle_ocr is not False else None

    def process_document(
        self,
        document_id: str,
        file_path: Union[str, Path],
        rendered_pages: Optional[List[Dict[str, Any]]] = None
    ) -> OCRDocumentResult:
        """
        Extracts all text tokens, bounding boxes, and lines across all pages of a document.
        """
        path = Path(file_path)
        is_pdf = path.suffix.lower() == ".pdf"
        pages_result: List[OCRPageResult] = []

        # 1. Try PyMuPDF native vector text first for digital PDFs (fastest, 100% accurate)
        if is_pdf:
            native_pages = self._extract_native_pdf_pages(str(path))
            # If native extraction yields substantial text (> 5 words per page), use it
            total_words = sum(len(p.tokens) for p in native_pages)
            if total_words >= 5:
                logger.info(f"Extracted {total_words} native vector tokens from PDF {path.name}.")
                pages_result = native_pages

        # 2. If scanned PDF or image, run OCR on rendered page images
        if not pages_result:
            paddle = self._get_paddle_ocr()
            if rendered_pages:
                for p_info in rendered_pages:
                    img_path = p_info["image_path"]
                    p_num = p_info.get("page_number", 1)
                    w = p_info.get("width", 1000)
                    h = p_info.get("height", 1400)

                    if paddle:
                        page_res = self._ocr_image_paddle(paddle, img_path, p_num, w, h)
                    else:
                        page_res = self._fallback_ocr_image(img_path, p_num, w, h)
                    pages_result.append(page_res)
            elif not is_pdf:
                # Standalone image (PNG, JPG)
                import fitz
                pix = fitz.Pixmap(str(path))
                w, h = pix.width, pix.height
                pix = None
                if paddle:
                    page_res = self._ocr_image_paddle(paddle, str(path), 1, w, h)
                else:
                    page_res = self._fallback_ocr_image(str(path), 1, w, h)
                pages_result.append(page_res)

        # 3. Aggregate document-level metrics
        all_tokens = [tok for p in pages_result for tok in p.tokens]
        doc_text = "\n\n".join(p.full_text for p in pages_result if p.full_text)
        overall_mean_conf = (
            sum(tok.confidence for tok in all_tokens) / len(all_tokens)
            if all_tokens else 0.0
        )

        return OCRDocumentResult(
            document_id=document_id,
            total_pages=len(pages_result),
            pages=pages_result,
            full_text=doc_text,
            mean_confidence=round(overall_mean_conf, 4)
        )

    def _extract_native_pdf_pages(self, pdf_path: str) -> List[OCRPageResult]:
        """Extracts structured word tokens and lines from digital PDFs."""
        pages: List[OCRPageResult] = []
        with fitz.open(pdf_path) as doc:
            for page_idx in range(len(doc)):
                page = doc.load_page(page_idx)
                rect = page.rect
                pw = max(1.0, rect.width)
                ph = max(1.0, rect.height)

                words = page.get_text("words")
                tokens: List[OCRToken] = []
                for w in words:
                    x0, y0, x1, y1, word_text, block_no, line_no, word_no = w
                    word_clean = word_text.strip()
                    if not word_clean:
                        continue
                    tokens.append(OCRToken(
                        text=word_clean,
                        confidence=1.0,
                        page_number=page_idx + 1,
                        line_number=int(line_no),
                        block_number=int(block_no),
                        bbox={
                            "x1": round(max(0.0, min(1.0, x0 / pw)), 4),
                            "y1": round(max(0.0, min(1.0, y0 / ph)), 4),
                            "x2": round(max(0.0, min(1.0, x1 / pw)), 4),
                            "y2": round(max(0.0, min(1.0, y1 / ph)), 4)
                        }
                    ))

                # Reconstruct full text ordered by position
                tokens.sort(key=lambda t: (t.bbox["y1"], t.bbox["x1"]))
                full_text = " ".join(t.text for t in tokens)
                mean_conf = sum(t.confidence for t in tokens) / len(tokens) if tokens else 1.0

                pages.append(OCRPageResult(
                    page_number=page_idx + 1,
                    width=int(pw),
                    height=int(ph),
                    tokens=tokens,
                    full_text=full_text,
                    mean_confidence=round(mean_conf, 4)
                ))
        return pages

    def _ocr_image_paddle(
        self,
        paddle,
        img_path: str,
        page_num: int,
        width: int,
        height: int
    ) -> OCRPageResult:
        """Processes an image using PaddleOCR and formats tokens with normalized bboxes."""
        try:
            results = paddle.ocr(img_path, cls=True)
        except Exception as e:
            logger.error(f"PaddleOCR error on {img_path}: {e}")
            return self._fallback_ocr_image(img_path, page_num, width, height)

        tokens: List[OCRToken] = []
        if results and results[0]:
            for idx, line in enumerate(results[0]):
                box, (text, conf) = line
                clean_text = text.strip()
                if not clean_text:
                    continue

                # box is [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)

                # Tokenize words inside the recognized text box
                words = clean_text.split()
                if len(words) <= 1:
                    tokens.append(OCRToken(
                        text=clean_text,
                        confidence=round(float(conf), 4),
                        page_number=page_num,
                        line_number=idx,
                        block_number=0,
                        bbox={
                            "x1": round(max(0.0, min(1.0, min_x / width)), 4),
                            "y1": round(max(0.0, min(1.0, min_y / height)), 4),
                            "x2": round(max(0.0, min(1.0, max_x / width)), 4),
                            "y2": round(max(0.0, min(1.0, max_y / height)), 4)
                        }
                    ))
                else:
                    # Distribute bounding box proportionally across words
                    total_chars = max(1, sum(len(w) for w in words))
                    curr_x = min_x
                    box_w = max_x - min_x
                    for w in words:
                        w_fraction = len(w) / total_chars
                        w_width = box_w * w_fraction
                        w_end = curr_x + w_width
                        tokens.append(OCRToken(
                            text=w,
                            confidence=round(float(conf), 4),
                            page_number=page_num,
                            line_number=idx,
                            block_number=0,
                            bbox={
                                "x1": round(max(0.0, min(1.0, curr_x / width)), 4),
                                "y1": round(max(0.0, min(1.0, min_y / height)), 4),
                                "x2": round(max(0.0, min(1.0, w_end / width)), 4),
                                "y2": round(max(0.0, min(1.0, max_y / height)), 4)
                            }
                        ))
                        curr_x = w_end

        tokens.sort(key=lambda t: (t.bbox["y1"], t.bbox["x1"]))
        full_text = " ".join(t.text for t in tokens)
        mean_conf = sum(t.confidence for t in tokens) / len(tokens) if tokens else 0.0

        return OCRPageResult(
            page_number=page_num,
            width=width,
            height=height,
            tokens=tokens,
            full_text=full_text,
            mean_confidence=round(mean_conf, 4)
        )

    def _fallback_ocr_image(
        self,
        img_path: str,
        page_num: int,
        width: int,
        height: int
    ) -> OCRPageResult:
        """
        Fallback OCR engine using PyMuPDF to extract text from image documents
        when external deep learning OCR engines are not available.
        """
        try:
            doc = fitz.open(img_path)
            page = doc.load_page(0)
            words = page.get_text("words")
            doc.close()
            tokens: List[OCRToken] = []
            for w in words:
                x0, y0, x1, y1, word_text, block_no, line_no, word_no = w
                clean = word_text.strip()
                if not clean:
                    continue
                tokens.append(OCRToken(
                    text=clean,
                    confidence=0.90,
                    page_number=page_num,
                    line_number=int(line_no),
                    block_number=int(block_no),
                    bbox={
                        "x1": round(max(0.0, min(1.0, x0 / width)), 4),
                        "y1": round(max(0.0, min(1.0, y0 / height)), 4),
                        "x2": round(max(0.0, min(1.0, x1 / width)), 4),
                        "y2": round(max(0.0, min(1.0, y1 / height)), 4)
                    }
                ))
            tokens.sort(key=lambda t: (t.bbox["y1"], t.bbox["x1"]))
            full_text = " ".join(t.text for t in tokens)
            return OCRPageResult(
                page_number=page_num,
                width=width,
                height=height,
                tokens=tokens,
                full_text=full_text,
                mean_confidence=0.90 if tokens else 0.0
            )
        except Exception as e:
            logger.warning(f"Fallback OCR could not read image: {e}")
            return OCRPageResult(
                page_number=page_num,
                width=width,
                height=height,
                tokens=[],
                full_text="",
                mean_confidence=0.0
            )


ocr_service = OCRService()

