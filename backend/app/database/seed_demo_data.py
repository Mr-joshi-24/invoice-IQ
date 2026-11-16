import shutil
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from backend.app.core.config import settings
from backend.app.database.session import SessionLocal
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.validation_result import ValidationResult
from backend.app.models.anomaly_result import AnomalyResult
from backend.app.models.review import Review
from backend.app.database.init_db import init_db
from backend.app.services.pipeline_service import pipeline_service


DEMO_INVOICES = [
    {
        "filename": "cloud_services_mar2026.pdf",
        "sample_source": "data/sample_invoices/01_clean_standard_invoice.pdf",
        "days_ago": 0,
        "vendor": "Nexus Digital Systems Inc",
        "inv_num": "INV-2026-4401",
        "date": "15/03/2026",
        "gstin": "27AABCN1234F1Z8",
        "subtotal": "10000.00",
        "tax": "1800.00",
        "total": "11800.00",
        "status": "PROCESSED",
        "conf": 0.96,
        "anomalous": False
    },
    {
        "filename": "industrial_pumps_feb2026.pdf",
        "sample_source": "data/sample_invoices/02_math_discrepancy_invoice.pdf",
        "days_ago": 1,
        "vendor": "Titan Industrial Equipment Ltd",
        "inv_num": "INV-2026-9022",
        "date": "10/02/2026",
        "gstin": "29ABCDE1234F1Z5",
        "subtotal": "8500.00",
        "tax": "1530.00",
        "total": "12000.00",
        "status": "NEEDS_REVIEW",
        "conf": 0.88,
        "anomalous": False,
        "val_failed": True,
        "val_msg": "Subtotal (8500.00) + Tax (1530.00) = 10030.00, but Total is 12000.00 (diff: 1970.00)"
    },
    {
        "filename": "asic_crypto_hardware.pdf",
        "sample_source": "data/sample_invoices/03_tax_anomaly_invoice.pdf",
        "days_ago": 2,
        "vendor": "Quantum Dynamics Infotech",
        "inv_num": "INV-2026-8104",
        "date": "05/01/2026",
        "gstin": "33AABCQ9999F1Z2",
        "subtotal": "4000.00",
        "tax": "2800.00",
        "total": "6800.00",
        "status": "NEEDS_REVIEW",
        "conf": 0.91,
        "anomalous": True,
        "anom_score": -0.18,
        "anom_msg": "Unusually high tax ratio of 70.0% detected by Isolation Forest."
    },
    {
        "filename": "office_supplies_q1.pdf",
        "sample_source": "data/sample_invoices/01_clean_standard_invoice.pdf",
        "days_ago": 3,
        "vendor": "Prime Wholesale Stationery Supplies",
        "inv_num": "INV-2026-1190",
        "date": "02/03/2026",
        "gstin": "29AABCP8888F1Z3",
        "subtotal": "2450.00",
        "tax": "294.00",
        "total": "2744.00",
        "status": "PROCESSED",
        "conf": 0.95,
        "anomalous": False
    },
    {
        "filename": "logistics_freight_mar2026.pdf",
        "sample_source": "data/sample_invoices/01_clean_standard_invoice.pdf",
        "days_ago": 4,
        "vendor": "TransGlobal Logistics Solutions",
        "inv_num": "INV-2026-7788",
        "date": "28/02/2026",
        "gstin": "27AABCT9922F1Z1",
        "subtotal": "18400.00",
        "tax": "3312.00",
        "total": "21712.00",
        "status": "PROCESSED",
        "conf": 0.94,
        "anomalous": False
    },
    {
        "filename": "software_seats_license.pdf",
        "sample_source": "data/sample_invoices/04_malformed_gstin_invoice.pdf",
        "days_ago": 5,
        "vendor": "Apex Cloud Solutions Pvt Ltd",
        "inv_num": "INV-2026-7219",
        "date": "20/02/2026",
        "gstin": "99XYZ1234F",
        "subtotal": "5000.00",
        "tax": "900.00",
        "total": "5900.00",
        "status": "NEEDS_REVIEW",
        "conf": 0.78,
        "anomalous": False,
        "gstin_failed": True
    },
    {
        "filename": "consulting_advisory_mar.pdf",
        "sample_source": "data/sample_invoices/01_clean_standard_invoice.pdf",
        "days_ago": 6,
        "vendor": "Starlight Corporate Consulting",
        "inv_num": "INV-2026-3392",
        "date": "18/02/2026",
        "gstin": "07AABCS5555F1Z4",
        "subtotal": "25000.00",
        "tax": "4500.00",
        "total": "29500.00",
        "status": "PROCESSED",
        "conf": 0.98,
        "anomalous": False,
        "has_review": True
    }
]


def seed_database():
    print("Initializing database tables...")
    init_db()
    db = SessionLocal()

    # Seed Default Platform Users
    from backend.app.models.user import User, UserRole
    from backend.app.core.security import hash_password

    print("Seeding default platform user accounts...")
    demo_users = [
        {"email": "admin@invoiceiq.com", "password": "Admin@123", "full_name": "System Administrator", "role": UserRole.ADMIN},
        {"email": "auditor@invoiceiq.com", "password": "Auditor@123", "full_name": "Lead Financial Auditor", "role": UserRole.REVIEWER},
        {"email": "viewer@invoiceiq.com", "password": "Viewer@123", "full_name": "Audit Observer", "role": UserRole.VIEWER}
    ]
    for u in demo_users:
        if not db.query(User).filter(User.email == u["email"]).first():
            db.add(User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                is_active=True
            ))
    db.commit()

    # Clear previous seed records if any
    print("Seeding demo invoice documents...")
    now = datetime.now(timezone.utc)

    for item in DEMO_INVOICES:
        doc_id = str(uuid.uuid4())
        src = Path(item["sample_source"])
        if not src.exists():
            continue

        stored_name = f"{doc_id}_{item['filename']}"
        dest_path = settings.UPLOAD_DIR / stored_name
        shutil.copyfile(src, dest_path)

        created_at = now - timedelta(days=item["days_ago"], hours=item.get("hours", 2))

        doc = Document(
            id=doc_id,
            original_filename=item["filename"],
            storage_path=str(dest_path.resolve()),
            file_type="pdf",
            file_size_bytes=dest_path.stat().st_size,
            page_count=1,
            processing_status=item["status"],
            overall_confidence=item["conf"],
            created_at=created_at,
            updated_at=created_at
        )
        db.add(doc)

        # Extracted fields
        fields_data = [
            ("vendor_name", item["vendor"], 0.95, {"x1": 0.08, "y1": 0.12, "x2": 0.45, "y2": 0.15}),
            ("invoice_number", item["inv_num"], 0.92, {"x1": 0.60, "y1": 0.12, "x2": 0.85, "y2": 0.15}),
            ("invoice_date", item["date"], 0.90, {"x1": 0.60, "y1": 0.15, "x2": 0.80, "y2": 0.18}),
            ("gstin", item["gstin"], 0.94 if not item.get("gstin_failed") else 0.60, {"x1": 0.08, "y1": 0.15, "x2": 0.35, "y2": 0.18}),
            ("subtotal", item["subtotal"], 0.92, {"x1": 0.70, "y1": 0.65, "x2": 0.88, "y2": 0.68}),
            ("tax_amount", item["tax"], 0.90, {"x1": 0.70, "y1": 0.70, "x2": 0.88, "y2": 0.73}),
            ("total_amount", item["total"], 0.95, {"x1": 0.70, "y1": 0.75, "x2": 0.90, "y2": 0.78})
        ]

        for fname, fval, fconf, bbox in fields_data:
            f = ExtractedField(
                document_id=doc_id,
                field_name=fname,
                extracted_value=fval,
                confidence_score=fconf,
                ocr_confidence=0.96,
                extraction_method="HYBRID",
                page_number=1,
                bounding_box=bbox,
                is_corrected=item.get("has_review", False) and fname == "vendor_name"
            )
            db.add(f)

        # Validations
        if item.get("val_failed"):
            db.add(ValidationResult(
                document_id=doc_id,
                rule_name="MATH_CONSISTENCY",
                status="FAILED",
                message=item["val_msg"],
                details={"discrepancy": 1970.0}
            ))
        else:
            db.add(ValidationResult(
                document_id=doc_id,
                rule_name="MATH_CONSISTENCY",
                status="PASSED",
                message=f"Subtotal ({item['subtotal']}) + Tax ({item['tax']}) equals Total ({item['total']})."
            ))

        if item.get("gstin_failed"):
            db.add(ValidationResult(
                document_id=doc_id,
                rule_name="GSTIN_FORMAT",
                status="FAILED",
                message=f"Invalid GSTIN length ({len(item['gstin'])} chars; expected 15)."
            ))
        else:
            db.add(ValidationResult(
                document_id=doc_id,
                rule_name="GSTIN_FORMAT",
                status="PASSED",
                message=f"GSTIN '{item['gstin']}' verified with valid state code and PAN structure."
            ))

        # Anomaly
        if item.get("anomalous"):
            db.add(AnomalyResult(
                document_id=doc_id,
                anomaly_score=item.get("anom_score", -0.15),
                is_anomalous=True,
                feature_vector={"total": float(item["total"]), "tax_ratio": 0.70},
                explanation=item["anom_msg"]
            ))
        else:
            db.add(AnomalyResult(
                document_id=doc_id,
                anomaly_score=0.22,
                is_anomalous=False,
                feature_vector={"total": float(item["total"]), "tax_ratio": 0.18},
                explanation="Normal transaction parameters within standard vendor and tax distributions."
            ))

        # Human Review History if present
        if item.get("has_review"):
            db.add(Review(
                document_id=doc_id,
                reviewer_id="lead_auditor",
                review_action="APPROVED",
                corrected_fields={"vendor_name": "Starlight Corporate Consulting"},
                reviewer_notes="Verified vendor registration with MCA."
            ))

    db.commit()
    db.close()
    print("Database demo seeding complete! Invoices populated across all statuses.")


if __name__ == "__main__":
    seed_database()

