from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.app.core.config import settings

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    confidence_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    anomaly_contamination: Optional[float] = Field(None, gt=0.0, lt=0.5)
    max_upload_size_mb: Optional[int] = Field(None, ge=1, le=50)


@router.get("")
def get_system_settings():
    """Returns current active engine and platform settings."""
    return {
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "anomaly_contamination": settings.ANOMALY_CONTAMINATION,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "allowed_extensions": settings.ALLOWED_EXTENSIONS,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "project_name": settings.PROJECT_NAME
    }


@router.put("")
def update_system_settings(updates: SettingsUpdate):
    """Updates runtime platform thresholds."""
    if updates.confidence_threshold is not None:
        settings.CONFIDENCE_THRESHOLD = updates.confidence_threshold
    if updates.anomaly_contamination is not None:
        settings.ANOMALY_CONTAMINATION = updates.anomaly_contamination
    if updates.max_upload_size_mb is not None:
        settings.MAX_UPLOAD_SIZE_MB = updates.max_upload_size_mb

    return {
        "message": "Settings updated successfully",
        "settings": {
            "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
            "anomaly_contamination": settings.ANOMALY_CONTAMINATION,
            "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB
        }
    }

