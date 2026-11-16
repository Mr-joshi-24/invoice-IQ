from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.review import Review
from backend.app.schemas.review import ReviewCreate, ReviewResponse
from backend.app.schemas.document import DocumentResponse
from backend.app.core.logging import logger

router = APIRouter(prefix="/documents", tags=["Review Center"])


@router.post("/{document_id}/review", response_model=DocumentResponse)
def submit_human_review(
    document_id: str,
    review_data: ReviewCreate,
    db: Session = Depends(get_db)
):
    """
    Submits human reviewer corrections and approval/rejection decision.
    Only updates fields that were genuinely modified (dirty checking), preserves original values,
    recalculates statuses, and records audit trail for continuous model learning.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    logger.info(f"Reviewer '{review_data.reviewer_id}' submitted action '{review_data.review_action}' for Document {document_id}")

    actually_modified = {}

    # 1. Update only modified field values (Dirty Checking)
    if review_data.corrected_fields:
        for field_name, new_val in review_data.corrected_fields.items():
            field_rec = db.query(ExtractedField).filter(
                ExtractedField.document_id == document_id,
                ExtractedField.field_name == field_name
            ).first()

            val_str = new_val.get("new", str(new_val)) if isinstance(new_val, dict) else str(new_val)
            val_str = val_str.strip() if val_str is not None else ""

            if field_rec:
                curr_val = (field_rec.extracted_value or "").strip()
                if curr_val != val_str:
                    # Genuinely modified by human reviewer
                    if getattr(field_rec, "original_value", None) is None:
                        field_rec.original_value = field_rec.extracted_value

                    actually_modified[field_name] = {
                        "old": field_rec.extracted_value,
                        "new": val_str
                    }
                    field_rec.extracted_value = val_str
                    field_rec.is_corrected = True
                    field_rec.extraction_method = "HUMAN_CORRECTED"
                    field_rec.confidence_score = 1.0  # Human verified is 100% confidence
            else:
                if val_str:
                    new_field = ExtractedField(
                        document_id=document_id,
                        field_name=field_name,
                        extracted_value=val_str,
                        original_value=None,
                        confidence_score=1.0,
                        extraction_method="HUMAN_CORRECTED",
                        is_corrected=True,
                        page_number=1
                    )
                    db.add(new_field)
                    actually_modified[field_name] = {"old": None, "new": val_str}

    # 2. Record Review Audit Entry
    review_entry = Review(
        document_id=document_id,
        reviewer_id=review_data.reviewer_id,
        review_action=review_data.review_action,
        corrected_fields=actually_modified if actually_modified else review_data.corrected_fields,
        reviewer_notes=review_data.reviewer_notes
    )
    db.add(review_entry)

    # 3. Update Document Processing Status
    if review_data.review_action == "APPROVED":
        doc.processing_status = "PROCESSED"
        doc.error_message = None
        # Boost overall confidence for human-approved records
        doc.overall_confidence = max(doc.overall_confidence or 0.0, 0.95)
    elif review_data.review_action == "REJECTED":
        doc.processing_status = "FAILED"
        doc.error_message = f"Rejected in human review: {review_data.reviewer_notes or 'No reason provided.'}"

    db.commit()
    db.refresh(doc)
    return doc
