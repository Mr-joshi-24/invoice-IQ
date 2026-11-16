import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Rule names: GSTIN_FORMAT, DATE_PARSABLE, MATH_CONSISTENCY, NON_NEGATIVE_AMOUNTS, DUPLICATE_INVOICE_NUMBER, REQUIRED_FIELDS
    rule_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    # Status: PASSED, WARNING, FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PASSED")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="validation_results")

    def __repr__(self) -> str:
        return f"<ValidationResult doc_id={self.document_id} rule={self.rule_name} status={self.status}>"

