import io
from pathlib import Path
import pytest
import fitz  # PyMuPDF
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import get_db, SessionLocal, engine
from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.services.pipeline_service import pipeline_service

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Keep db intact for other module tests if needed


def create_in_memory_invoice_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 60), "TAX INVOICE", fontsize=18)
    page.insert_text((50, 90), "Vendor: Global Dynamics Tech Solutions Pvt Ltd", fontsize=11)
    page.insert_text((50, 110), "GSTIN: 27AABCG1234F1Z8", fontsize=11)
    page.insert_text((380, 90), "Invoice No: INV-2026-7788", fontsize=11)
    page.insert_text((380, 110), "Date: 12/03/2026", fontsize=11)
    page.insert_text((50, 200), "Description: Enterprise Cloud Storage License", fontsize=11)
    page.insert_text((50, 260), "Subtotal: 5000.00", fontsize=12)
    page.insert_text((50, 280), "Tax Amount: 900.00", fontsize=12)
    page.insert_text((50, 300), "Total Amount: 5900.00", fontsize=14)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_upload_and_pipeline_lifecycle():
    pdf_bytes = create_in_memory_invoice_pdf()
    files = [("files", ("invoice_api_test.pdf", io.BytesIO(pdf_bytes), "application/pdf"))]

    # 1. Test Upload
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    doc_id = data[0]["id"]
    assert data[0]["original_filename"] == "invoice_api_test.pdf"
    assert data[0]["processing_status"] in ["PENDING", "PROCESSING", "PROCESSED", "NEEDS_REVIEW"]

    # 2. Run Pipeline Directly to guarantee synchronous completion in test
    pipe_res = pipeline_service.process_document(doc_id)
    assert pipe_res["success"] is True
    assert pipe_res["status"] in ["PROCESSED", "NEEDS_REVIEW"]
    assert "stage_timings_ms" in pipe_res
    assert "TOTAL_PIPELINE_MS" in pipe_res["stage_timings_ms"]

    # 3. Test Get Single Document
    res_get = client.get(f"/api/v1/documents/{doc_id}")
    assert res_get.status_code == 200
    doc_data = res_get.json()
    assert doc_data["id"] == doc_id
    assert len(doc_data["extracted_fields"]) >= 5
    assert len(doc_data["validation_results"]) >= 3
    assert doc_data["anomaly_result"] is not None

    # Check extracted values
    f_map = {f["field_name"]: f["extracted_value"] for f in doc_data["extracted_fields"]}
    assert "27AABCG1234F1Z8" in (f_map.get("gstin") or "")
    assert "5900" in (f_map.get("total_amount") or "")

    # 4. Test Page Preview Image Stream
    res_preview = client.get(f"/api/v1/documents/{doc_id}/preview/1")
    assert res_preview.status_code == 200
    assert res_preview.headers["content-type"] == "image/png"

    # 5. Test Human Review Submission
    review_payload = {
        "reviewer_id": "senior_auditor_alice",
        "review_action": "APPROVED",
        "corrected_fields": {
            "vendor_name": "Global Dynamics Tech Solutions Pvt Ltd"
        },
        "reviewer_notes": "Verified correct vendor entity"
    }
    res_review = client.post(f"/api/v1/documents/{doc_id}/review", json=review_payload)
    assert res_review.status_code == 200
    reviewed_doc = res_review.json()
    assert reviewed_doc["processing_status"] == "PROCESSED"
    assert len(reviewed_doc["reviews"]) >= 1
    assert reviewed_doc["reviews"][0]["reviewer_id"] == "senior_auditor_alice"


def test_list_documents_filtering_and_search():
    res_list = client.get("/api/v1/documents?page=1&limit=10")
    assert res_list.status_code == 200
    data = res_list.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1

    # Filter by status
    res_filtered = client.get("/api/v1/documents?status=PROCESSED")
    assert res_filtered.status_code == 200

    # Search filter
    res_search = client.get("/api/v1/documents?search=invoice")
    assert res_search.status_code == 200


def test_analytics_endpoints():
    # 1. Overview KPIs
    res_overview = client.get("/api/v1/analytics/overview")
    assert res_overview.status_code == 200
    kpis = res_overview.json()
    assert "total_documents" in kpis
    assert "processed" in kpis
    assert "success_rate" in kpis
    assert "recent_activity" in kpis
    assert len(kpis["recent_activity"]) == 7
    assert "status_distribution" in kpis

    # 2. Model Evaluation Report
    res_model = client.get("/api/v1/analytics/model")
    assert res_model.status_code == 200
    model_data = res_model.json()
    assert model_data.get("is_trained") is True
    assert "exact_match_accuracy" in model_data
    assert "classification_report" in model_data


def test_export_endpoints():
    # 1. CSV Export
    res_csv = client.get("/api/v1/documents/export/download?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Document ID" in res_csv.text

    # 2. JSON Export
    res_json = client.get("/api/v1/documents/export/download?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]


def test_settings_endpoints():
    # 1. Get settings
    res_get = client.get("/api/v1/settings")
    assert res_get.status_code == 200
    data = res_get.json()
    assert "confidence_threshold" in data
    assert "allowed_extensions" in data

    # 2. Update settings
    res_put = client.put("/api/v1/settings", json={"confidence_threshold": 0.85})
    assert res_put.status_code == 200
    put_data = res_put.json()
    assert put_data["settings"]["confidence_threshold"] == 0.85


def test_upload_security_filename_sanitization():
    """Regression test for SEC-02/03: Path traversal attempt is sanitized."""
    pdf_bytes = create_in_memory_invoice_pdf()
    traversal_filename = "../../../traversal_invoice.pdf"
    files = [("files", (traversal_filename, io.BytesIO(pdf_bytes), "application/pdf"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code in (200, 201)
    data = response.json()
    assert len(data) == 1
    # Check that original_filename is clean and has no directory traversal slashes
    assert "/" not in data[0]["original_filename"]
    assert "\\" not in data[0]["original_filename"]
    assert data[0]["original_filename"] == "traversal_invoice.pdf"


def test_review_dirty_checking_and_original_value():
    """Regression test for BUG-02: Human review preserves machine extracted value in original_value."""
    pdf_bytes = create_in_memory_invoice_pdf()
    files = [("files", ("invoice_audit_test.pdf", io.BytesIO(pdf_bytes), "application/pdf"))]
    res_up = client.post("/api/v1/documents/upload", files=files)
    doc_id = res_up.json()[0]["id"]

    # Run pipeline to populate fields
    pipeline_service.process_document(doc_id)

    # Fetch document before review
    res_before = client.get(f"/api/v1/documents/{doc_id}")
    fields_before = {f["field_name"]: f for f in res_before.json()["extracted_fields"]}

    orig_vendor = fields_before["vendor_name"]["extracted_value"]
    orig_total = fields_before["total_amount"]["extracted_value"]

    # Reviewer modifies ONLY total_amount, leaves vendor_name identical
    new_total = "9999.99"
    review_payload = {
        "reviewer_id": "auditor_bob",
        "review_action": "APPROVED",
        "corrected_fields": {
            "vendor_name": orig_vendor,  # Unchanged
            "total_amount": new_total    # Changed
        },
        "reviewer_notes": "Corrected total"
    }
    res_rev = client.post(f"/api/v1/documents/{doc_id}/review", json=review_payload)
    assert res_rev.status_code == 200

    res_after = client.get(f"/api/v1/documents/{doc_id}")
    fields_after = {f["field_name"]: f for f in res_after.json()["extracted_fields"]}

    # Unchanged field vendor_name should NOT have is_corrected=True
    assert fields_after["vendor_name"]["is_corrected"] is False
    assert fields_after["vendor_name"]["extracted_value"] == orig_vendor

    # Changed field total_amount SHOULD have is_corrected=True and original_value preserved
    assert fields_after["total_amount"]["is_corrected"] is True
    assert fields_after["total_amount"]["extracted_value"] == new_total
    assert fields_after["total_amount"]["original_value"] == orig_total


