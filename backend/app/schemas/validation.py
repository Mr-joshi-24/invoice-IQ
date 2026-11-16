from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict


class ValidationResultBase(BaseModel):
    rule_name: str
    status: Literal["PASSED", "WARNING", "FAILED"] = "PASSED"
    message: str
    details: Optional[Dict[str, Any]] = None


class ValidationResultCreate(ValidationResultBase):
    pass


class ValidationResultResponse(ValidationResultBase):
    id: str
    document_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

