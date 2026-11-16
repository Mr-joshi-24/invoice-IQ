from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    x1: float = Field(..., ge=0.0, le=1.0, description="Normalized top-left X coordinate")
    y1: float = Field(..., ge=0.0, le=1.0, description="Normalized top-left Y coordinate")
    x2: float = Field(..., ge=0.0, le=1.0, description="Normalized bottom-right X coordinate")
    y2: float = Field(..., ge=0.0, le=1.0, description="Normalized bottom-right Y coordinate")


class ExtractedFieldBase(BaseModel):
    field_name: str
    extracted_value: Optional[str] = None
    original_value: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ocr_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    extraction_method: str = "HYBRID"
    page_number: int = Field(default=1, ge=1)
    bounding_box: Optional[Dict[str, Any]] = None
    is_corrected: bool = False


class ExtractedFieldCreate(ExtractedFieldBase):
    pass


class ExtractedFieldUpdate(BaseModel):
    extracted_value: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_corrected: bool = True
    extraction_method: str = "HUMAN_CORRECTED"


class ExtractedFieldResponse(ExtractedFieldBase):
    id: str
    document_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

