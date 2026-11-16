from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict


class ReviewCreate(BaseModel):
    reviewer_id: str = "reviewer_default"
    review_action: Literal["APPROVED", "REJECTED"] = "APPROVED"
    corrected_fields: Optional[Dict[str, Any]] = None
    reviewer_notes: Optional[str] = None


class ReviewResponse(BaseModel):
    id: str
    document_id: str
    reviewer_id: str
    review_action: str
    corrected_fields: Optional[Dict[str, Any]] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)

