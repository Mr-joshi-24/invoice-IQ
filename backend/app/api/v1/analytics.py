import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.anomaly_result import AnomalyResult
from backend.app.models.extracted_field import ExtractedField

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    """
    Returns live KPIs, document volume metrics, processing success rates,
    and historical daily trends for the Dashboard and Analytics pages.
    """
    total_docs = db.query(Document).count()
    processed_count = db.query(Document).filter(Document.processing_status == "PROCESSED").count()
    needs_review_count = db.query(Document).filter(Document.processing_status == "NEEDS_REVIEW").count()
    failed_count = db.query(Document).filter(Document.processing_status == "FAILED").count()
    pending_count = db.query(Document).filter(Document.processing_status.in_(["PENDING", "PROCESSING"])).count()

    anomalies_count = db.query(AnomalyResult).filter(AnomalyResult.is_anomalous == True).count()

    success_rate = (
        round((processed_count / total_docs) * 100, 1)
        if total_docs > 0 else 0.0
    )

    avg_conf_query = db.query(func.avg(Document.overall_confidence)).filter(Document.overall_confidence.isnot(None)).scalar()
    avg_confidence = round(float(avg_conf_query), 2) if avg_conf_query else 0.0

    # Recent 7-day activity trend
    now = datetime.now(timezone.utc)
    recent_activity = []
    for day_offset in range(6, -1, -1):
        target_day = now - timedelta(days=day_offset)
        day_start = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = target_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        day_label = target_day.strftime("%b %d")

        p_cnt = db.query(Document).filter(
            Document.created_at >= day_start,
            Document.created_at <= day_end,
            Document.processing_status == "PROCESSED"
        ).count()
        r_cnt = db.query(Document).filter(
            Document.created_at >= day_start,
            Document.created_at <= day_end,
            Document.processing_status == "NEEDS_REVIEW"
        ).count()
        f_cnt = db.query(Document).filter(
            Document.created_at >= day_start,
            Document.created_at <= day_end,
            Document.processing_status == "FAILED"
        ).count()

        recent_activity.append({
            "date": day_label,
            "processed": p_cnt,
            "needs_review": r_cnt,
            "failed": f_cnt
        })

    # Status distribution for donut charts
    status_distribution = [
        {"name": "Processed", "value": processed_count, "color": "#10b981"},
        {"name": "Needs Review", "value": needs_review_count, "color": "#f59e0b"},
        {"name": "Failed", "value": failed_count, "color": "#ef4444"},
        {"name": "Pending", "value": pending_count, "color": "#6366f1"}
    ]

    # Recent Anomaly alerts
    recent_anomalies_records = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.is_anomalous == True)
        .order_by(AnomalyResult.created_at.desc())
        .limit(5)
        .all()
    )
    anomalies_list = []
    for a in recent_anomalies_records:
        doc = db.query(Document).filter(Document.id == a.document_id).first()
        vendor_field = db.query(ExtractedField.extracted_value).filter(
            ExtractedField.document_id == a.document_id,
            ExtractedField.field_name == "vendor_name"
        ).first()
        total_field = db.query(ExtractedField.extracted_value).filter(
            ExtractedField.document_id == a.document_id,
            ExtractedField.field_name == "total_amount"
        ).first()

        anomalies_list.append({
            "id": a.id,
            "document_id": a.document_id,
            "filename": doc.original_filename if doc else "unknown",
            "vendor": vendor_field[0] if vendor_field else "Unknown Vendor",
            "total_amount": total_field[0] if total_field else "N/A",
            "anomaly_score": a.anomaly_score,
            "explanation": a.explanation,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {
        "total_documents": total_docs,
        "processed": processed_count,
        "pending_review": needs_review_count,
        "failed": failed_count,
        "anomalies_detected": anomalies_count,
        "success_rate": success_rate,
        "average_confidence": avg_confidence,
        "recent_activity": recent_activity,
        "status_distribution": status_distribution,
        "recent_anomalies": anomalies_list
    }


@router.get("/model")
def get_model_evaluation_metrics():
    """
    Returns authentic training, validation, and test evaluation metrics
    from the serialized metrics_summary.json artifact.
    """
    metrics_path = settings.ML_ARTIFACTS_DIR / "metrics_summary.json"
    if not metrics_path.exists():
        return {
            "is_trained": False,
            "message": "Model has not been trained yet. Run ml/src/train_classifier.py to train."
        }

    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {
            "is_trained": False,
            "error": f"Failed to read model metrics artifact: {str(e)}"
        }
