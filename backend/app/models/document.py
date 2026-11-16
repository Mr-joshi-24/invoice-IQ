import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Ownership
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Status: PENDING, PROCESSING, PROCESSED, NEEDS_REVIEW, FAILED
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overall_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="documents")
    extracted_fields: Mapped[List["ExtractedField"]] = relationship(
        "ExtractedField",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ExtractedField.field_name"
    )
    validation_results: Mapped[List["ValidationResult"]] = relationship(
        "ValidationResult",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    anomaly_result: Mapped[Optional["AnomalyResult"]] = relationship(
        "AnomalyResult",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan"
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Review.reviewed_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} name='{self.original_filename}' status={self.processing_status}>"
