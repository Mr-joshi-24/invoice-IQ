from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.extraction import ExtractedFieldResponse
from backend.app.schemas.validation import ValidationResultResponse
from backend.app.schemas.anomaly import AnomalyResultResponse
from backend.app.schemas.review import ReviewResponse


class DocumentBase(BaseModel):
    original_filename: str
    file_type: str
    file_size_bytes: int = 0
    page_count: int = 1


class DocumentCreate(DocumentBase):
    storage_path: str
    processing_status: str = "PENDING"


class DocumentUpdate(BaseModel):
    processing_status: Optional[str] = None
    error_message: Optional[str] = None
    overall_confidence: Optional[float] = None
    page_count: Optional[int] = None


class DocumentListItem(BaseModel):
    id: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    page_count: int
    processing_status: str
    overall_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    # Selected extracted summary fields for table view
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[str] = None
    is_anomalous: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(DocumentBase):
    id: str
    storage_path: str
    processing_status: str
    error_message: Optional[str] = None
    overall_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    extracted_fields: List[ExtractedFieldResponse] = []
    validation_results: List[ValidationResultResponse] = []
    anomaly_result: Optional[AnomalyResultResponse] = None
    reviews: List[ReviewResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: List[DocumentListItem]
    total: int
    page: int
    limit: int
    pages: int

