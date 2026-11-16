from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AnomalyResultBase(BaseModel):
    anomaly_score: float = Field(default=0.0, description="Isolation forest anomaly score (-1.0 to 1.0)")
    is_anomalous: bool = False
    feature_vector: Optional[Dict[str, Any]] = None
    explanation: str = "Normal pattern"


class AnomalyResultCreate(AnomalyResultBase):
    pass


class AnomalyResultResponse(AnomalyResultBase):
    id: str
    document_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

