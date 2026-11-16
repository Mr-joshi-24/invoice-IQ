import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import joblib
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.anomaly import AnomalyResultCreate
from backend.app.schemas.extraction import ExtractedFieldCreate
from backend.app.models.extracted_field import ExtractedField


class AnomalyDetectionService:
    """
    Unsupervised financial anomaly detection service using Isolation Forest
    and vendor-level transaction distribution analysis.
    """

    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.artifacts_dir = artifacts_dir or settings.ML_ARTIFACTS_DIR
        self._model = None
        self._scaler = None
        self._load_model()

    def _load_model(self):
        model_path = self.artifacts_dir / "anomaly_model.joblib"
        scaler_path = self.artifacts_dir / "anomaly_scaler.joblib"

        if model_path.exists():
            try:
                self._model = joblib.load(model_path)
                logger.info(f"Loaded Isolation Forest anomaly model from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load anomaly model: {e}")
                self._model = None
        else:
            logger.info("Anomaly detection model not yet trained; using heuristic fallback.")

        if scaler_path.exists():
            try:
                self._scaler = joblib.load(scaler_path)
                logger.info(f"Loaded feature RobustScaler from {scaler_path}")
            except Exception as e:
                logger.warning(f"Failed to load anomaly scaler: {e}")
                self._scaler = None

    def analyze_document(
        self,
        extracted_fields: List[ExtractedFieldCreate],
        db: Optional[Session] = None,
        current_document_id: Optional[str] = None
    ) -> AnomalyResultCreate:
        """
        Extracts numerical financial indicators and scores the invoice against
        the Isolation Forest model and vendor transaction history.
        """
        field_map = {f.field_name: f for f in extracted_fields}

        subtotal = self._parse_amount(field_map.get("subtotal"))
        tax = self._parse_amount(field_map.get("tax_amount"))
        total = self._parse_amount(field_map.get("total_amount"))
        vendor_name = (
            field_map["vendor_name"].extracted_value.strip()
            if field_map.get("vendor_name") and field_map["vendor_name"].extracted_value
            else None
        )

        # Fallback if financial amounts are absent
        if total is None:
            return AnomalyResultCreate(
                anomaly_score=0.0,
                is_anomalous=False,
                feature_vector={"total": None},
                explanation="Financial amounts absent; anomaly assessment skipped."
            )

        if subtotal is None and tax is not None:
            subtotal = max(0.0, total - tax)
        elif subtotal is None:
            subtotal = total

        if tax is None:
            tax = max(0.0, total - subtotal)

        # Construct feature vector
        tot_log = float(np.log1p(total))
        tax_ratio = float(tax / max(1.0, subtotal))
        st_ratio = float(subtotal / max(1.0, total))
        discrepancy = float(abs(subtotal + tax - total))

        feature_vector = {
            "total_amount": round(total, 2),
            "subtotal": round(subtotal, 2),
            "tax_amount": round(tax, 2),
            "total_amount_log": round(tot_log, 3),
            "tax_ratio": round(tax_ratio, 4),
            "subtotal_to_total_ratio": round(st_ratio, 4),
            "math_discrepancy": round(discrepancy, 2)
        }

        # 1. Isolation Forest Evaluation
        is_anomalous = False
        anomaly_score = 0.2  # positive = normal, negative = anomaly in scikit-learn
        model_flagged = False

        if self._model is not None:
            X = np.array([[tot_log, tax_ratio, st_ratio, discrepancy]], dtype=np.float64)
            X_eval = self._scaler.transform(X) if self._scaler is not None else X
            raw_score = float(self._model.decision_function(X_eval)[0])
            pred = int(self._model.predict(X_eval)[0])  # -1 = anomaly, 1 = normal
            anomaly_score = round(raw_score, 4)
            if pred == -1:
                model_flagged = True

        # 2. Vendor Historical Comparison (if DB available)
        vendor_flagged = False
        vendor_zscore = 0.0
        if db is not None and vendor_name:
            vendor_zscore, v_mean, v_count = self._compute_vendor_zscore(
                db=db,
                vendor_name=vendor_name,
                current_total=total,
                exclude_doc_id=current_document_id
            )
            feature_vector["vendor_historical_mean"] = round(v_mean, 2)
            feature_vector["vendor_transactions_count"] = v_count
            feature_vector["vendor_amount_zscore"] = round(vendor_zscore, 2)

            if abs(vendor_zscore) >= 3.5 and v_count >= 3:
                vendor_flagged = True

        is_anomalous = model_flagged or vendor_flagged

        # 3. Generate Human-Readable Explanation
        explanations = []
        if vendor_flagged:
            explanations.append(
                f"Amount of {total:,.2f} deviates significantly ({vendor_zscore:+.1f} std devs) "
                f"from vendor historical mean ({feature_vector['vendor_historical_mean']:,.2f})."
            )
        if model_flagged:
            if tax_ratio > 0.35:
                explanations.append(f"Unusually high tax ratio of {tax_ratio * 100:.1f}%.")
            elif discrepancy > 1.0:
                explanations.append(f"Subtotal and tax do not reconcile with total (diff: {discrepancy:.2f}).")
            elif total > 100000.0:
                explanations.append(f"High-value transaction amount ({total:,.2f}) detected.")
            else:
                explanations.append("Multi-factor Isolation Forest flagged unusual pattern.")

        final_explanation = (
            "; ".join(explanations)
            if explanations
            else "Normal transaction parameters within standard vendor and tax distributions."
        )

        return AnomalyResultCreate(
            anomaly_score=anomaly_score,
            is_anomalous=is_anomalous,
            feature_vector=feature_vector,
            explanation=final_explanation
        )

    def _parse_amount(self, field: Optional[ExtractedFieldCreate]) -> Optional[float]:
        if not field or not field.extracted_value:
            return None
        try:
            clean = re.sub(r"[^\d.]", "", str(field.extracted_value))
            return float(clean)
        except ValueError:
            return None

    def _compute_vendor_zscore(
        self,
        db: Session,
        vendor_name: str,
        current_total: float,
        exclude_doc_id: Optional[str]
    ) -> (float, float, int):
        """Calculates Z-score of current total relative to historical transactions from the same vendor."""
        # Find all documents with this vendor name
        vendor_docs = db.query(ExtractedField.document_id).filter(
            ExtractedField.field_name == "vendor_name",
            ExtractedField.extracted_value == vendor_name
        )
        if exclude_doc_id:
            vendor_docs = vendor_docs.filter(ExtractedField.document_id != exclude_doc_id)

        doc_ids = [r[0] for r in vendor_docs.all()]
        if len(doc_ids) < 3:
            return 0.0, current_total, len(doc_ids)

        # Get total amounts for these documents
        totals_records = db.query(ExtractedField.extracted_value).filter(
            ExtractedField.document_id.in_(doc_ids),
            ExtractedField.field_name == "total_amount"
        ).all()

        historical_totals = []
        for (rec_val,) in totals_records:
            if rec_val:
                try:
                    c = float(re.sub(r"[^\d.]", "", rec_val))
                    historical_totals.append(c)
                except ValueError:
                    pass

        if len(historical_totals) < 3:
            return 0.0, current_total, len(historical_totals)

        arr = np.array(historical_totals, dtype=np.float64)
        mean = float(np.mean(arr))
        std = float(np.std(arr))

        if std < 1.0:
            return 0.0, mean, len(historical_totals)

        zscore = float((current_total - mean) / std)
        return zscore, mean, len(historical_totals)


anomaly_service = AnomalyDetectionService()

