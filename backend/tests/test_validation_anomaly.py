import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.base import Base
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.schemas.extraction import ExtractedFieldCreate
from backend.app.schemas.validation import ValidationResultCreate
from backend.app.services.validation_service import validation_service
from backend.app.services.anomaly_service import anomaly_service
from backend.app.services.confidence_service import confidence_service


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_gstin_validation():
    # 1. Valid GSTIN
    f_valid = ExtractedFieldCreate(field_name="gstin", extracted_value="29ABCDE1234F1Z5")
    res = validation_service._validate_gstin(f_valid)
    assert res.status == "PASSED"

    # 2. Invalid length
    f_short = ExtractedFieldCreate(field_name="gstin", extracted_value="29ABCDE")
    res_short = validation_service._validate_gstin(f_short)
    assert res_short.status == "FAILED"

    # 3. Invalid state code
    f_bad_state = ExtractedFieldCreate(field_name="gstin", extracted_value="99ABCDE1234F1Z5")
    res_state = validation_service._validate_gstin(f_bad_state)
    assert res_state.status == "FAILED"


def test_date_validation():
    # 1. Standard valid past date
    f_date = ExtractedFieldCreate(field_name="invoice_date", extracted_value="15/01/2025")
    res = validation_service._validate_invoice_date(f_date)
    assert res.status == "PASSED"

    # 2. Far future date
    f_future = ExtractedFieldCreate(field_name="invoice_date", extracted_value="01/01/2035")
    res_future = validation_service._validate_invoice_date(f_future)
    assert res_future.status == "WARNING"

    # 3. Non-date gibberish
    f_garbage = ExtractedFieldCreate(field_name="invoice_date", extracted_value="not_a_date_xyz")
    res_garbage = validation_service._validate_invoice_date(f_garbage)
    assert res_garbage.status == "FAILED"


def test_math_consistency():
    sub = ExtractedFieldCreate(field_name="subtotal", extracted_value="1000.00")
    tax = ExtractedFieldCreate(field_name="tax_amount", extracted_value="180.00")
    tot_exact = ExtractedFieldCreate(field_name="total_amount", extracted_value="1180.00")
    tot_broken = ExtractedFieldCreate(field_name="total_amount", extracted_value="1500.00")

    # Exact match
    res_exact = validation_service._validate_math_consistency(sub, tax, tot_exact)
    assert res_exact.status == "PASSED"

    # Major discrepancy
    res_broken = validation_service._validate_math_consistency(sub, tax, tot_broken)
    assert res_broken.status == "FAILED"
    assert res_broken.details["discrepancy"] == 320.00


def test_duplicate_invoice_validation(db_session):
    # Insert existing invoice record into DB
    doc1 = Document(original_filename="doc1.pdf", storage_path="uploads/doc1.pdf", file_type="pdf")
    db_session.add(doc1)
    db_session.commit()

    field1 = ExtractedField(document_id=doc1.id, field_name="invoice_number", extracted_value="INV-2026-001")
    db_session.add(field1)
    db_session.commit()

    # Attempt to validate a new invoice with the identical invoice number
    f_inv_duplicate = ExtractedFieldCreate(field_name="invoice_number", extracted_value="INV-2026-001")
    f_vendor = ExtractedFieldCreate(field_name="vendor_name", extracted_value="Acme Corp")

    res_dup = validation_service._validate_duplicate_invoice(
        db=db_session,
        vendor_field=f_vendor,
        inv_num_field=f_inv_duplicate,
        current_document_id="new_doc_999"
    )
    assert res_dup.status == "FAILED"
    assert "already exists" in res_dup.message

    # Unique invoice number
    f_inv_unique = ExtractedFieldCreate(field_name="invoice_number", extracted_value="INV-2026-999")
    res_unique = validation_service._validate_duplicate_invoice(
        db=db_session,
        vendor_field=f_vendor,
        inv_num_field=f_inv_unique,
        current_document_id="new_doc_999"
    )
    assert res_unique.status == "PASSED"


def test_anomaly_detection_service():
    # 1. Normal invoice transaction
    normal_fields = [
        ExtractedFieldCreate(field_name="subtotal", extracted_value="5000.00"),
        ExtractedFieldCreate(field_name="tax_amount", extracted_value="900.00"),
        ExtractedFieldCreate(field_name="total_amount", extracted_value="5900.00"),
        ExtractedFieldCreate(field_name="vendor_name", extracted_value="Standard Supplier Ltd")
    ]
    res_normal = anomaly_service.analyze_document(normal_fields)
    assert res_normal.is_anomalous is False
    assert res_normal.anomaly_score >= -0.1

    # 2. Extreme anomalous invoice: abnormal tax (80% tax rate)
    anomalous_fields = [
        ExtractedFieldCreate(field_name="subtotal", extracted_value="2000.00"),
        ExtractedFieldCreate(field_name="tax_amount", extracted_value="1600.00"),  # 80% tax rate
        ExtractedFieldCreate(field_name="total_amount", extracted_value="3600.00"),
        ExtractedFieldCreate(field_name="vendor_name", extracted_value="Suspicious Vendor")
    ]
    res_anomalous = anomaly_service.analyze_document(anomalous_fields)
    assert res_anomalous.is_anomalous is True
    assert "Unusually high tax ratio" in res_anomalous.explanation or "Isolation Forest" in res_anomalous.explanation


def test_confidence_scoring_and_routing():
    valid_fields = [
        ExtractedFieldCreate(field_name="vendor_name", extracted_value="Acme Corp", confidence_score=0.95),
        ExtractedFieldCreate(field_name="invoice_number", extracted_value="INV-100", confidence_score=0.92),
        ExtractedFieldCreate(field_name="invoice_date", extracted_value="01/02/2026", confidence_score=0.90),
        ExtractedFieldCreate(field_name="gstin", extracted_value="29ABCDE1234F1Z5", confidence_score=0.95),
        ExtractedFieldCreate(field_name="subtotal", extracted_value="1000.00", confidence_score=0.90),
        ExtractedFieldCreate(field_name="tax_amount", extracted_value="180.00", confidence_score=0.90),
        ExtractedFieldCreate(field_name="total_amount", extracted_value="1180.00", confidence_score=0.95)
    ]
    validations_pass = [
        ValidationResultCreate(rule_name="GSTIN_FORMAT", status="PASSED", message="Valid"),
        ValidationResultCreate(rule_name="MATH_CONSISTENCY", status="PASSED", message="Match")
    ]

    # Clean document -> PROCESSED
    score, status, reasons = confidence_service.evaluate_document_confidence(
        extracted_fields=valid_fields,
        validations=validations_pass,
        confidence_threshold=0.80
    )
    assert score >= 0.85
    assert status == "PROCESSED"
    assert len(reasons) == 0

    # With validation failure -> NEEDS_REVIEW
    validations_fail = [
        ValidationResultCreate(rule_name="MATH_CONSISTENCY", status="FAILED", message="Mismatch")
    ]
    score_f, status_f, reasons_f = confidence_service.evaluate_document_confidence(
        extracted_fields=valid_fields,
        validations=validations_fail,
        confidence_threshold=0.80
    )
    assert status_f == "NEEDS_REVIEW"
    assert any("Validation failure" in r for r in reasons_f)


def test_mandatory_fields_hard_routing():
    """
    Regression test for BUG-01: An invoice missing a mandatory field (e.g. invoice_number)
    must NEVER be marked PROCESSED, even if all other fields have 100% confidence.
    """
    fields_without_invoice_num = [
        ExtractedFieldCreate(field_name="vendor_name", extracted_value="Acme Corp", confidence_score=1.0),
        ExtractedFieldCreate(field_name="invoice_date", extracted_value="01/02/2026", confidence_score=1.0),
        ExtractedFieldCreate(field_name="gstin", extracted_value="29ABCDE1234F1Z5", confidence_score=1.0),
        ExtractedFieldCreate(field_name="subtotal", extracted_value="1000.00", confidence_score=1.0),
        ExtractedFieldCreate(field_name="tax_amount", extracted_value="180.00", confidence_score=1.0),
        ExtractedFieldCreate(field_name="total_amount", extracted_value="1180.00", confidence_score=1.0)
    ]
    validations_pass = [
        ValidationResultCreate(rule_name="GSTIN_FORMAT", status="PASSED", message="Valid")
    ]

    score, status, reasons = confidence_service.evaluate_document_confidence(
        extracted_fields=fields_without_invoice_num,
        validations=validations_pass,
        confidence_threshold=0.80
    )
    assert status == "NEEDS_REVIEW"
    assert any("invoice_number" in r for r in reasons)

    # Missing total_amount also hard-gates to NEEDS_REVIEW
    fields_without_total = [
        ExtractedFieldCreate(field_name="invoice_number", extracted_value="INV-100", confidence_score=1.0),
        ExtractedFieldCreate(field_name="vendor_name", extracted_value="Acme Corp", confidence_score=1.0),
        ExtractedFieldCreate(field_name="subtotal", extracted_value="1000.00", confidence_score=1.0)
    ]
    _, status_no_total, reasons_no_total = confidence_service.evaluate_document_confidence(
        extracted_fields=fields_without_total,
        validations=validations_pass,
        confidence_threshold=0.80
    )
    assert status_no_total == "NEEDS_REVIEW"
    assert any("total_amount" in r for r in reasons_no_total)


def test_tax_bracket_alignment():
    # 1. Standard 18% GST rate aligns
    sub_18 = ExtractedFieldCreate(field_name="subtotal", extracted_value="1000.00")
    tax_18 = ExtractedFieldCreate(field_name="tax_amount", extracted_value="180.00")
    res_18 = validation_service._validate_tax_brackets(sub_18, tax_18)
    assert res_18.status == "PASSED"
    assert "18%" in res_18.message

    # 2. Standard 5% GST rate aligns
    tax_5 = ExtractedFieldCreate(field_name="tax_amount", extracted_value="50.00")
    res_5 = validation_service._validate_tax_brackets(sub_18, tax_5)
    assert res_5.status == "PASSED"
    assert "5%" in res_5.message

    # 3. Abnormal tax rate (> 40%) fails
    tax_huge = ExtractedFieldCreate(field_name="tax_amount", extracted_value="650.00")  # 65%
    res_huge = validation_service._validate_tax_brackets(sub_18, tax_huge)
    assert res_huge.status == "FAILED"
    assert "exceeds statutory maximum GST ceiling" in res_huge.message


def test_gstin_luhn_mod36_checksum():
    from backend.app.services.validation_service import compute_luhn_mod36_checksum
    # Verify calculation
    check_char = compute_luhn_mod36_checksum("29ABCDE1234F1Z")
    assert check_char == "W"

    # Perfect matching GSTIN
    f_perfect = ExtractedFieldCreate(field_name="gstin", extracted_value="29ABCDE1234F1ZW")
    res_perfect = validation_service._validate_gstin(f_perfect)
    assert res_perfect.status == "PASSED"
    assert res_perfect.details["checksum_verified"] is True



