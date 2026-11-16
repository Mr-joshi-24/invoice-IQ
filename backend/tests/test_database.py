import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.validation_result import ValidationResult
from backend.app.models.anomaly_result import AnomalyResult
from backend.app.models.review import Review
from backend.app.schemas.document import DocumentResponse
from backend.app.schemas.extraction import ExtractedFieldResponse


@pytest.fixture(scope="function")
def db_session():
    """Creates an in-memory SQLite database session isolated per test."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def test_create_document_and_fields(db_session):
    # 1. Create document
    doc = Document(
        original_filename="invoice_1001.pdf",
        storage_path="uploads/mock_uuid.pdf",
        file_type="pdf",
        file_size_bytes=102400,
        page_count=1,
        processing_status="PENDING"
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.id is not None
    assert doc.processing_status == "PENDING"
    assert doc.created_at is not None

    # 2. Add extracted fields
    field1 = ExtractedField(
        document_id=doc.id,
        field_name="vendor_name",
        extracted_value="Acme Corp Pvt Ltd",
        confidence_score=0.95,
        ocr_confidence=0.98,
        extraction_method="HYBRID",
        page_number=1,
        bounding_box={"x1": 0.1, "y1": 0.1, "x2": 0.4, "y2": 0.15}
    )
    field2 = ExtractedField(
        document_id=doc.id,
        field_name="total_amount",
        extracted_value="15420.50",
        confidence_score=0.88,
        ocr_confidence=0.92,
        extraction_method="RULE",
        page_number=1,
        bounding_box={"x1": 0.6, "y1": 0.8, "x2": 0.9, "y2": 0.85}
    )
    db_session.add_all([field1, field2])
    db_session.commit()
    db_session.refresh(doc)

    assert len(doc.extracted_fields) == 2
    assert doc.extracted_fields[0].field_name in ["total_amount", "vendor_name"]


def test_validation_and_anomaly_relationships(db_session):
    doc = Document(
        original_filename="tax_invoice_2026.pdf",
        storage_path="uploads/tax_inv.pdf",
        file_type="pdf",
        file_size_bytes=51200,
        page_count=1,
        processing_status="PROCESSING"
    )
    db_session.add(doc)
    db_session.commit()

    # Add Validation Result
    val = ValidationResult(
        document_id=doc.id,
        rule_name="MATH_CONSISTENCY",
        status="PASSED",
        message="Subtotal (100.00) + Tax (18.00) equals Total (118.00)",
        details={"subtotal": 100.0, "tax": 18.0, "total": 118.0, "discrepancy": 0.0}
    )
    db_session.add(val)

    # Add Anomaly Result
    anomaly = AnomalyResult(
        document_id=doc.id,
        anomaly_score=0.15,
        is_anomalous=False,
        feature_vector={"total_amount_log": 4.77, "tax_ratio": 0.18},
        explanation="Amounts align with vendor baseline"
    )
    db_session.add(anomaly)
    db_session.commit()
    db_session.refresh(doc)

    assert len(doc.validation_results) == 1
    assert doc.validation_results[0].rule_name == "MATH_CONSISTENCY"
    assert doc.anomaly_result is not None
    assert doc.anomaly_result.is_anomalous is False
    assert doc.anomaly_result.anomaly_score == 0.15


def test_review_and_feedback(db_session):
    doc = Document(
        original_filename="review_sample.png",
        storage_path="uploads/review.png",
        file_type="png",
        file_size_bytes=20480,
        page_count=1,
        processing_status="NEEDS_REVIEW"
    )
    db_session.add(doc)
    db_session.commit()

    rev = Review(
        document_id=doc.id,
        reviewer_id="lead_auditor",
        review_action="APPROVED",
        corrected_fields={"total_amount": {"original": "1500.00", "corrected": "15000.00"}},
        reviewer_notes="OCR missed trailing zero due to smudge"
    )
    db_session.add(rev)
    db_session.commit()
    db_session.refresh(doc)

    assert len(doc.reviews) == 1
    assert doc.reviews[0].review_action == "APPROVED"
    assert doc.reviews[0].reviewer_id == "lead_auditor"
    assert doc.reviews[0].corrected_fields["total_amount"]["corrected"] == "15000.00"


def test_cascade_deletion(db_session):
    doc = Document(
        original_filename="delete_me.pdf",
        storage_path="uploads/temp.pdf",
        file_type="pdf",
        file_size_bytes=1000,
        page_count=1
    )
    db_session.add(doc)
    db_session.commit()
    doc_id = doc.id

    field = ExtractedField(document_id=doc_id, field_name="gstin", extracted_value="29ABCDE1234F1Z5")
    val = ValidationResult(document_id=doc_id, rule_name="GSTIN_FORMAT", status="PASSED", message="Valid")
    anomaly = AnomalyResult(document_id=doc_id, anomaly_score=0.2, is_anomalous=False)
    rev = Review(document_id=doc_id, reviewer_id="qa", review_action="APPROVED")

    db_session.add_all([field, val, anomaly, rev])
    db_session.commit()

    # Verify rows exist
    assert db_session.query(ExtractedField).filter_by(document_id=doc_id).count() == 1
    assert db_session.query(ValidationResult).filter_by(document_id=doc_id).count() == 1
    assert db_session.query(AnomalyResult).filter_by(document_id=doc_id).count() == 1
    assert db_session.query(Review).filter_by(document_id=doc_id).count() == 1

    # Delete Document and verify cascade delete
    db_session.delete(doc)
    db_session.commit()

    assert db_session.query(ExtractedField).filter_by(document_id=doc_id).count() == 0
    assert db_session.query(ValidationResult).filter_by(document_id=doc_id).count() == 0
    assert db_session.query(AnomalyResult).filter_by(document_id=doc_id).count() == 0
    assert db_session.query(Review).filter_by(document_id=doc_id).count() == 0


def test_pydantic_schema_serialization(db_session):
    doc = Document(
        original_filename="pydantic_test.pdf",
        storage_path="uploads/pyd.pdf",
        file_type="pdf",
        file_size_bytes=8192,
        page_count=1,
        processing_status="PROCESSED",
        overall_confidence=0.92
    )
    db_session.add(doc)
    db_session.commit()

    field = ExtractedField(
        document_id=doc.id,
        field_name="invoice_number",
        extracted_value="INV-2026-981",
        confidence_score=0.95,
        ocr_confidence=0.97,
        extraction_method="RULE",
        page_number=1,
        bounding_box={"x1": 0.5, "y1": 0.2, "x2": 0.8, "y2": 0.25}
    )
    db_session.add(field)
    db_session.commit()
    db_session.refresh(doc)

    # Convert to Pydantic Response Schema
    doc_response = DocumentResponse.model_validate(doc)
    assert doc_response.id == doc.id
    assert doc_response.processing_status == "PROCESSED"
    assert doc_response.overall_confidence == 0.92
    assert len(doc_response.extracted_fields) == 1
    assert doc_response.extracted_fields[0].field_name == "invoice_number"
    assert doc_response.extracted_fields[0].extracted_value == "INV-2026-981"

