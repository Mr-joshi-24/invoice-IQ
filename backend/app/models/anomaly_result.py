import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnomalyResult(Base):
    __tablename__ = "anomaly_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_anomalous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    feature_vector: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="Normal pattern")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="anomaly_result")

    def __repr__(self) -> str:
        return f"<AnomalyResult doc_id={self.document_id} anomalous={self.is_anomalous} score={self.anomaly_score}>"

