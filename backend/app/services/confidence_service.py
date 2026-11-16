from typing import List, Dict, Any, Tuple, Optional
from backend.app.schemas.extraction import ExtractedFieldCreate
from backend.app.schemas.validation import ValidationResultCreate
from backend.app.schemas.anomaly import AnomalyResultCreate
from backend.app.core.config import settings

FIELD_WEIGHTS = {
    "total_amount": 0.25,
    "invoice_number": 0.20,
    "vendor_name": 0.15,
    "invoice_date": 0.15,
    "gstin": 0.10,
    "subtotal": 0.10,
    "tax_amount": 0.05
}

MANDATORY_FIELDS = {"invoice_number", "total_amount"}


class ConfidenceService:
    """
    Computes calibrated, transparent confidence scores for individual fields
    and aggregates overall document confidence for human-review routing.
    """

    def compute_field_confidence(
        self,
        field: ExtractedFieldCreate,
        validation_passed: bool = True
    ) -> float:
        """
        Calculates composite field confidence:
        c_final = 0.50 * c_extraction + 0.30 * c_ocr + 0.20 * is_valid
        """
        c_ext = field.confidence_score
        c_ocr = field.ocr_confidence if field.ocr_confidence is not None else c_ext
        v_score = 1.0 if validation_passed else 0.0

        composite = (0.50 * c_ext) + (0.30 * c_ocr) + (0.20 * v_score)
        return round(min(1.0, max(0.0, composite)), 4)

    def evaluate_document_confidence(
        self,
        extracted_fields: List[ExtractedFieldCreate],
        validations: List[ValidationResultCreate],
        anomaly: Optional[AnomalyResultCreate] = None,
        confidence_threshold: Optional[float] = None
    ) -> Tuple[float, str, List[str]]:
        """
        Aggregates field confidence and determines document routing status:
        - PROCESSED: confidence >= threshold, no validation failures, not anomalous, all mandatory fields present
        - NEEDS_REVIEW: confidence < threshold, validation failure, anomalous, or missing mandatory fields

        Returns:
            (overall_confidence: float, status: str, reasons: List[str])
        """
        threshold = confidence_threshold or settings.CONFIDENCE_THRESHOLD
        reasons: List[str] = []

        # Map field name to field
        field_map = {f.field_name: f for f in extracted_fields}

        # Check validation failures
        has_failed_validations = False
        for v in validations:
            if v.status == "FAILED":
                has_failed_validations = True
                reasons.append(f"Validation failure in rule '{v.rule_name}': {v.message}")

        # Track mandatory field integrity (BUG-01 fix)
        missing_mandatory_fields = []
        for mf in MANDATORY_FIELDS:
            f = field_map.get(mf)
            if not f or not f.extracted_value or str(f.extracted_value).strip() == "":
                missing_mandatory_fields.append(mf)
                reasons.append(f"Mandatory field '{mf}' is missing or unextracted.")
            elif f.confidence_score < 0.40:
                missing_mandatory_fields.append(mf)
                reasons.append(f"Mandatory field '{mf}' has unacceptably low confidence ({f.confidence_score:.2f}).")

        # Compute weighted average score
        weighted_sum = 0.0
        total_weight = 0.0

        for field_name, weight in FIELD_WEIGHTS.items():
            field = field_map.get(field_name)
            if field and field.extracted_value and str(field.extracted_value).strip() != "":
                c = field.confidence_score
                weighted_sum += c * weight
            else:
                if field_name not in MANDATORY_FIELDS:
                    reasons.append(f"Optional field '{field_name}' not extracted.")
            total_weight += weight

        overall_confidence = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

        # Check anomaly flag
        is_anomalous = anomaly.is_anomalous if anomaly else False
        if is_anomalous:
            reasons.append(f"Financial anomaly flagged: {anomaly.explanation}")

        # Determine Routing Status with hard-gating on mandatory fields
        if has_failed_validations:
            status = "NEEDS_REVIEW"
        elif is_anomalous:
            status = "NEEDS_REVIEW"
        elif missing_mandatory_fields:
            status = "NEEDS_REVIEW"
            reasons.append("Document routed to Human Review: Missing or uncertain mandatory field(s).")
        elif overall_confidence < threshold:
            status = "NEEDS_REVIEW"
            reasons.append(f"Overall confidence ({overall_confidence:.2f}) below threshold ({threshold:.2f})")
        else:
            status = "PROCESSED"

        return overall_confidence, status, reasons


confidence_service = ConfidenceService()
