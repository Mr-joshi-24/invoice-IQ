import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    extracted_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Method: RULE, ML, HYBRID, HUMAN_CORRECTED
    extraction_method: Mapped[str] = mapped_column(String(30), nullable=False, default="HYBRID")
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Normalized bounding box: {"x1": 0.12, "y1": 0.34, "x2": 0.45, "y2": 0.38}
    bounding_box: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="extracted_fields")

    def __repr__(self) -> str:
        return f"<ExtractedField doc_id={self.document_id} field={self.field_name} val='{self.extracted_value}' conf={self.confidence_score}>"

