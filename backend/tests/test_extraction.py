import pytest
from backend.app.services.ocr_service import OCRDocumentResult, OCRPageResult, OCRToken
from backend.app.services.extraction_service import extraction_service, HybridExtractionService
from ml.datasets.synthetic_generator import generate_synthetic_invoice_document, generate_dataset
from ml.src.features import extract_token_features, get_token_lexical_tags, get_spatial_bins


def test_synthetic_invoice_generator():
    doc = generate_synthetic_invoice_document("Alpha Omega Technologies Pvt Ltd", doc_index=42)
    assert doc["document_id"] == "synthetic_42"
    assert doc["vendor_name"] == "Alpha Omega Technologies Pvt Ltd"

    gt = doc["ground_truth"]
    assert "invoice_number" in gt
    assert "gstin" in gt
    assert "subtotal" in gt
    assert "tax_amount" in gt
    assert "total_amount" in gt

    tokens = doc["tokens"]
    assert len(tokens) >= 15
    for t in tokens:
        assert "text" in t
        assert "label" in t
        assert "bbox" in t
        assert 0.0 <= t["bbox"]["x1"] <= 1.0


def test_dataset_splits_and_vendor_isolation():
    dataset = generate_dataset(total_documents=40)
    assert len(dataset["train"]) > 0
    assert len(dataset["val"]) > 0
    assert len(dataset["test"]) > 0

    train_vendors = {d["vendor_name"] for d in dataset["train"]}
    test_vendors = {d["vendor_name"] for d in dataset["test"]}

    # Verify vendors in test set are disjoint from training set (prevent data leakage)
    assert train_vendors.isdisjoint(test_vendors)


def test_feature_engineering():
    tags = get_token_lexical_tags("27ABCDE1234F1Z5")
    assert "IS_UPPER" in tags
    assert "HAS_DIGIT" in tags

    amount_tags = get_token_lexical_tags("14,500.00")
    assert "IS_CURRENCY_AMOUNT" in amount_tags

    bins = get_spatial_bins({"x1": 0.15, "y1": 0.08, "x2": 0.35, "y2": 0.12})
    assert "Y_BAND_0" in bins
    assert "X_COL_0" in bins


def test_hybrid_field_extraction():
    # Build synthetic OCR document result
    syn_doc = generate_synthetic_invoice_document("Apex Cloud Solutions Pvt Ltd", doc_index=99)
    gt = syn_doc["ground_truth"]

    ocr_tokens = [
        OCRToken(
            text=t["text"],
            confidence=t.get("confidence", 0.95),
            page_number=t.get("page_number", 1),
            line_number=t.get("line_number", 0),
            block_number=0,
            bbox=t["bbox"]
        )
        for t in syn_doc["tokens"]
    ]

    ocr_result = OCRDocumentResult(
        document_id="doc_test_hybrid",
        total_pages=1,
        pages=[
            OCRPageResult(
                page_number=1,
                width=1000,
                height=1400,
                tokens=ocr_tokens,
                full_text=syn_doc["full_text"],
                mean_confidence=0.96
            )
        ],
        full_text=syn_doc["full_text"],
        mean_confidence=0.96
    )

    fields = extraction_service.extract_fields(ocr_result)
    field_map = {f.field_name: f for f in fields}

    assert "vendor_name" in field_map
    assert "invoice_number" in field_map
    assert "invoice_date" in field_map
    assert "gstin" in field_map
    assert "subtotal" in field_map
    assert "tax_amount" in field_map
    assert "total_amount" in field_map

    # Check GSTIN extraction
    assert field_map["gstin"].extracted_value == gt["gstin"]
    assert field_map["gstin"].confidence_score >= 0.85
    assert field_map["gstin"].extraction_method in ["RULE", "ML", "HYBRID"]

    # Check Total Amount extraction
    assert field_map["total_amount"].extracted_value is not None
    assert float(field_map["total_amount"].extracted_value) == float(gt["total_amount"])


def test_candidate_agreement_boost():
    service = HybridExtractionService()

    rule_c = {
        "value": "INV-2026-901",
        "confidence": 0.90,
        "ocr_confidence": 0.95,
        "bbox": {"x1": 0.6, "y1": 0.1, "x2": 0.8, "y2": 0.12},
        "page_number": 1
    }
    ml_c = {
        "value": "INV-2026-901",
        "confidence": 0.92,
        "ocr_confidence": 0.95,
        "bbox": {"x1": 0.6, "y1": 0.1, "x2": 0.8, "y2": 0.12},
        "page_number": 1
    }

    # When both agree on the exact same value
    aggregated = service._aggregate_candidates("invoice_number", rule_c, ml_c)
    assert aggregated is not None
    assert aggregated.extraction_method == "HYBRID"
    assert aggregated.extracted_value == "INV-2026-901"
    # Boosted confidence: max(0.90, 0.92) + 0.05 = 0.97
    assert aggregated.confidence_score == 0.97
