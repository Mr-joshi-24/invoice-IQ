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


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reviewer_id: Mapped[str] = mapped_column(String(100), nullable=False, default="reviewer")
    # Action: APPROVED, REJECTED
    review_action: Mapped[str] = mapped_column(String(20), nullable=False, default="APPROVED")
    corrected_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, index=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<Review doc_id={self.document_id} action={self.review_action} at={self.reviewed_at}>"

