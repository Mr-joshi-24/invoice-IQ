import os
from pathlib import Path
import pytest
import fitz  # PyMuPDF
from backend.app.utils.pdf_tools import (
    validate_document_file,
    convert_pdf_to_images,
    extract_pdf_native_spans,
    get_pdf_page_count
)
from backend.app.services.preprocessing_service import preprocessing_service
from backend.app.services.ocr_service import ocr_service, OCRDocumentResult


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    """Generates a realistic single-page vector invoice PDF using PyMuPDF."""
    temp_dir = tmp_path_factory.mktemp("pdf_test")
    pdf_path = temp_dir / "sample_invoice.pdf"

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # Standard A4 at 72 DPI

    # Insert text lines imitating a standard invoice
    page.insert_text((50, 60), "TAX INVOICE", fontsize=18)
    page.insert_text((50, 100), "Vendor: Acme Industrial Supplies Ltd", fontsize=11)
    page.insert_text((50, 120), "GSTIN: 29ABCDE1234F1Z5", fontsize=11)
    page.insert_text((400, 100), "Invoice No: INV-2026-8802", fontsize=11)
    page.insert_text((400, 120), "Date: 15/03/2026", fontsize=11)
    page.insert_text((50, 200), "Item: Heavy Duty Server Rack x 2", fontsize=11)
    page.insert_text((50, 280), "Subtotal: INR 10,000.00", fontsize=12)
    page.insert_text((50, 300), "Tax Amount: INR 1,800.00", fontsize=12)
    page.insert_text((50, 320), "Total Amount: INR 11,800.00", fontsize=14)

    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


def test_validate_document_file(sample_pdf, tmp_path):
    # 1. Valid PDF
    res = validate_document_file(sample_pdf)
    assert res["valid"] is True
    assert res["file_type"] == "pdf"
    assert res["page_count"] == 1
    assert res["size_bytes"] > 0

    # 2. Non-existent file
    res_fake = validate_document_file("non_existent_file.pdf")
    assert res_fake["valid"] is False
    assert "File does not exist" in res_fake["error"]

    # 3. Invalid magic bytes file
    bad_file = tmp_path / "corrupted.pdf"
    bad_file.write_text("This is not a real PDF file header.")
    res_bad = validate_document_file(bad_file)
    assert res_bad["valid"] is False
    assert "Unsupported or corrupted" in res_bad["error"]


def test_get_pdf_page_count(sample_pdf):
    count = get_pdf_page_count(sample_pdf)
    assert count == 1


def test_convert_pdf_to_images(sample_pdf, tmp_path):
    out_dir = tmp_path / "rendered_pages"
    results = convert_pdf_to_images(sample_pdf, out_dir, dpi=150, prefix="test_page")

    assert len(results) == 1
    page_info = results[0]
    assert page_info["page_number"] == 1
    assert page_info["dpi"] == 150
    assert os.path.exists(page_info["image_path"])
    assert page_info["width"] > 0
    assert page_info["height"] > 0


def test_extract_pdf_native_spans(sample_pdf):
    tokens = extract_pdf_native_spans(sample_pdf)
    assert len(tokens) >= 15

    # Check normalization of bounding boxes
    for t in tokens:
        bbox = t["bbox"]
        assert 0.0 <= bbox["x1"] <= 1.0
        assert 0.0 <= bbox["y1"] <= 1.0
        assert 0.0 <= bbox["x2"] <= 1.0
        assert 0.0 <= bbox["y2"] <= 1.0
        assert bbox["x1"] <= bbox["x2"]
        assert bbox["y1"] <= bbox["y2"]
        assert t["confidence"] == 1.0

    texts = [t["text"] for t in tokens]
    assert "INVOICE" in texts
    assert "GSTIN:" in texts
    assert "29ABCDE1234F1Z5" in texts
    assert "11,800.00" in texts


def test_preprocessing_service(sample_pdf, tmp_path):
    # Render page to image first
    out_dir = tmp_path / "prep_pages"
    results = convert_pdf_to_images(sample_pdf, out_dir, dpi=150, prefix="prep_test")
    img_path = results[0]["image_path"]

    # Run preprocessing
    prep_res = preprocessing_service.preprocess_image(
        img_path,
        apply_deskew=True,
        apply_enhancement=True
    )
    assert prep_res["success"] is True
    assert os.path.exists(prep_res["preprocessed_path"])


def test_ocr_service_pipeline(sample_pdf, tmp_path):
    out_dir = tmp_path / "ocr_pages"
    rendered = convert_pdf_to_images(sample_pdf, out_dir, dpi=150, prefix="ocr_test")

    doc_result = ocr_service.process_document(
        document_id="doc_test_123",
        file_path=sample_pdf,
        rendered_pages=rendered
    )

    assert isinstance(doc_result, OCRDocumentResult)
    assert doc_result.document_id == "doc_test_123"
    assert doc_result.total_pages == 1
    assert len(doc_result.pages) == 1
    assert doc_result.mean_confidence > 0.8

    page = doc_result.pages[0]
    assert len(page.tokens) > 0
    assert "INVOICE" in page.full_text
    assert "11,800.00" in page.full_text

