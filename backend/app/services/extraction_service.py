import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dateutil import parser as date_parser
import joblib
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.ocr_service import OCRDocumentResult, OCRToken
from backend.app.schemas.extraction import ExtractedFieldCreate
from ml.src.features import extract_token_features

# Regular expressions for deterministic field patterns
GSTIN_REGEX = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")
AMOUNT_REGEX = re.compile(r"\b(?:INR|Rs\.?|₹|\$|EUR|€)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2})\b")
DATE_REGEX_PATTERNS = [
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"),
    re.compile(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4}\b", re.IGNORECASE)
]
INV_NUM_REGEX = re.compile(
    r"(?:Invoice\s*(?:No|Num|Number|#)?|Bill\s*No|Inv\s*#|Doc\s*#)[:.\s]*([A-Z0-9\-\/]{3,30})",
    re.IGNORECASE
)


class HybridExtractionService:
    """
    Hybrid Document Field Extraction Engine.
    Combines:
    1. Deterministic rule-based extraction (regex, geometry, keyword anchors)
    2. ML token classification (TF-IDF + Logistic Regression)
    3. Candidate aggregation and disambiguation
    """

    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.artifacts_dir = artifacts_dir or settings.ML_ARTIFACTS_DIR
        self._clf = None
        self._vectorizer = None
        self._load_ml_models()

    def _load_ml_models(self):
        """Loads serialized ML artifacts if available."""
        clf_path = self.artifacts_dir / "field_classifier.joblib"
        vec_path = self.artifacts_dir / "tfidf_vectorizer.joblib"

        if clf_path.exists() and vec_path.exists():
            try:
                self._clf = joblib.load(clf_path)
                self._vectorizer = joblib.load(vec_path)
                logger.info(f"Loaded ML extraction models from {self.artifacts_dir}")
            except Exception as e:
                logger.warning(f"Failed to load ML artifacts: {e}. Falling back to rule-based engine.")
                self._clf = None
                self._vectorizer = None
        else:
            logger.info("ML model artifacts not found; engine will run in rule-based baseline mode.")

    def extract_fields(self, ocr_result: OCRDocumentResult) -> List[ExtractedFieldCreate]:
        """
        Executes hybrid extraction across all OCR tokens in the document.
        Returns a list of ExtractedFieldCreate records for the 7 core fields:
        - vendor_name
        - invoice_number
        - invoice_date
        - gstin
        - subtotal
        - tax_amount
        - total_amount
        """
        all_tokens = [tok for page in ocr_result.pages for tok in page.tokens]
        full_text = ocr_result.full_text

        # 1. Rule-Based Candidates
        rule_candidates = self._extract_rule_candidates(all_tokens, full_text)

        # 2. ML-Based Candidates
        ml_candidates = self._extract_ml_candidates(all_tokens)

        # 3. Candidate Aggregation
        extracted_fields: List[ExtractedFieldCreate] = []
        target_fields = [
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "gstin",
            "subtotal",
            "tax_amount",
            "total_amount"
        ]

        for field_name in target_fields:
            rule_c = rule_candidates.get(field_name)
            ml_c = ml_candidates.get(field_name)

            chosen = self._aggregate_candidates(field_name, rule_c, ml_c)
            if chosen:
                extracted_fields.append(chosen)
            else:
                # Add default empty record with 0 confidence
                extracted_fields.append(ExtractedFieldCreate(
                    field_name=field_name,
                    extracted_value=None,
                    confidence_score=0.0,
                    ocr_confidence=None,
                    extraction_method="HYBRID",
                    page_number=1,
                    bounding_box=None
                ))

        return extracted_fields

    def _extract_rule_candidates(
        self,
        tokens: List[OCRToken],
        full_text: str
    ) -> Dict[str, Dict[str, Any]]:
        """Extracts candidate values using regex and spatial keyword anchors."""
        candidates = {}

        # 1. GSTIN (Rule)
        for tok in tokens:
            match = GSTIN_REGEX.search(tok.text)
            if match:
                candidates["gstin"] = {
                    "value": match.group(0),
                    "confidence": 0.95,
                    "ocr_confidence": tok.confidence,
                    "bbox": tok.bbox,
                    "page_number": tok.page_number
                }
                break
        if "gstin" not in candidates:
            match = GSTIN_REGEX.search(full_text)
            if match:
                candidates["gstin"] = {
                    "value": match.group(0),
                    "confidence": 0.90,
                    "ocr_confidence": 0.90,
                    "bbox": {"x1": 0.1, "y1": 0.1, "x2": 0.4, "y2": 0.15},
                    "page_number": 1
                }

        # 2. Invoice Date (Rule)
        for tok in tokens:
            for pat in DATE_REGEX_PATTERNS:
                m = pat.search(tok.text)
                if m:
                    raw_date = m.group(0)
                    try:
                        # Verify parsable date
                        date_parser.parse(raw_date, fuzzy=False)
                        candidates["invoice_date"] = {
                            "value": raw_date,
                            "confidence": 0.92,
                            "ocr_confidence": tok.confidence,
                            "bbox": tok.bbox,
                            "page_number": tok.page_number
                        }
                        break
                    except Exception:
                        pass
            if "invoice_date" in candidates:
                break

        # 3. Invoice Number (Rule)
        inv_match = INV_NUM_REGEX.search(full_text)
        if inv_match:
            inv_val = inv_match.group(1).strip()
            # Find matching token for bbox
            found_tok = None
            for tok in tokens:
                if inv_val in tok.text or tok.text in inv_val:
                    found_tok = tok
                    break
            candidates["invoice_number"] = {
                "value": inv_val,
                "confidence": 0.90,
                "ocr_confidence": found_tok.confidence if found_tok else 0.90,
                "bbox": found_tok.bbox if found_tok else {"x1": 0.6, "y1": 0.08, "x2": 0.9, "y2": 0.12},
                "page_number": found_tok.page_number if found_tok else 1
            }

        # 4. Amounts: Subtotal, Tax, Total via Anchor Proximity
        amounts_found = self._extract_amounts_by_anchors(tokens)
        for k in ["subtotal", "tax_amount", "total_amount"]:
            if k in amounts_found:
                candidates[k] = amounts_found[k]

        # 5. Vendor Name (Top left heuristic)
        vendor_candidate = self._extract_vendor_by_layout(tokens)
        if vendor_candidate:
            candidates["vendor_name"] = vendor_candidate

        return candidates

    def _extract_amounts_by_anchors(self, tokens: List[OCRToken]) -> Dict[str, Dict[str, Any]]:
        """Finds numeric amount tokens situated near financial anchor words."""
        results = {}
        anchor_patterns = {
            "subtotal": ["subtotal", "sub total", "sub-total", "net amount"],
            "tax_amount": ["tax", "gst", "cgst", "sgst", "igst", "vat"],
            "total_amount": ["grand total", "net total", "amount payable", "total amount", "total"]
        }

        for field, keywords in anchor_patterns.items():
            best_amount = None
            for idx, tok in enumerate(tokens):
                tok_clean = tok.text.lower().replace(":", "").strip()
                # Ensure 'total' does not accidentally match 'subtotal'
                matches_kw = False
                for kw in keywords:
                    if kw == tok_clean:
                        matches_kw = True
                        break
                    elif kw in tok_clean:
                        if field == "total_amount" and "sub" in tok_clean:
                            continue
                        matches_kw = True
                        break

                if matches_kw:
                    anchor_bbox = tok.bbox
                    # Search subsequent tokens within same horizontal row or immediately following
                    for j in range(idx + 1, min(idx + 8, len(tokens))):
                        cand_tok = tokens[j]
                        clean_num = cand_tok.text.replace(",", "").replace("₹", "").replace("$", "").replace("INR", "").strip()
                        m = re.match(r"^\d+\.\d{2}$", clean_num)
                        if m:
                            # Verify geometric proximity
                            y_diff = abs(cand_tok.bbox["y1"] - anchor_bbox["y1"])
                            if y_diff < 0.06:  # within approximately same line
                                best_amount = {
                                    "value": clean_num,
                                    "confidence": 0.92,
                                    "ocr_confidence": cand_tok.confidence,
                                    "bbox": cand_tok.bbox,
                                    "page_number": cand_tok.page_number
                                }
                                break
                    if best_amount:
                        break
            if best_amount:
                results[field] = best_amount

        return results

    def _extract_vendor_by_layout(self, tokens: List[OCRToken]) -> Optional[Dict[str, Any]]:
        """Identifies vendor name tokens located in header banner region."""
        ignored_words = {"tax", "invoice", "bill", "to", "ship", "date", "gstin", "original", "for", "recipient"}
        header_tokens = [
            t for t in tokens
            if t.bbox["y1"] <= 0.16 and t.text.lower() not in ignored_words and len(t.text) > 1
        ]
        if not header_tokens:
            return None

        # Group tokens on top line
        top_y = min(t.bbox["y1"] for t in header_tokens)
        line_tokens = [t for t in header_tokens if abs(t.bbox["y1"] - top_y) < 0.03]
        line_tokens.sort(key=lambda t: t.bbox["x1"])

        if line_tokens:
            vendor_text = " ".join(t.text for t in line_tokens)
            mean_conf = sum(t.confidence for t in line_tokens) / len(line_tokens)
            # Combine bounding box
            x1 = min(t.bbox["x1"] for t in line_tokens)
            y1 = min(t.bbox["y1"] for t in line_tokens)
            x2 = max(t.bbox["x2"] for t in line_tokens)
            y2 = max(t.bbox["y2"] for t in line_tokens)
            return {
                "value": vendor_text,
                "confidence": 0.85,
                "ocr_confidence": round(mean_conf, 4),
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "page_number": line_tokens[0].page_number
            }
        return None

    def _extract_ml_candidates(self, tokens: List[OCRToken]) -> Dict[str, Dict[str, Any]]:
        """Uses trained Logistic Regression model to classify and score tokens."""
        if not self._clf or not self._vectorizer or not tokens:
            return {}

        token_dicts = [
            {
                "text": t.text,
                "bbox": t.bbox,
                "page_number": t.page_number,
                "line_number": t.line_number
            }
            for t in tokens
        ]
        feature_strings = extract_token_features(token_dicts)
        X_vec = self._vectorizer.transform(feature_strings)
        probs = self._clf.predict_proba(X_vec)
        classes = list(self._clf.classes_)

        class_to_field = {
            "VENDOR": "vendor_name",
            "INVOICE_NUM": "invoice_number",
            "DATE": "invoice_date",
            "GSTIN": "gstin",
            "SUBTOTAL": "subtotal",
            "TAX": "tax_amount",
            "TOTAL": "total_amount"
        }

        candidates = {}
        for ml_cls, field_name in class_to_field.items():
            if ml_cls not in classes:
                continue
            cls_idx = classes.index(ml_cls)
            best_idx = None
            best_prob = 0.0

            for i in range(len(tokens)):
                p = float(probs[i][cls_idx])
                if p > best_prob and p >= 0.35:
                    best_prob = p
                    best_idx = i

            if best_idx is not None:
                tok = tokens[best_idx]
                candidates[field_name] = {
                    "value": tok.text.strip(),
                    "confidence": round(best_prob, 4),
                    "ocr_confidence": tok.confidence,
                    "bbox": tok.bbox,
                    "page_number": tok.page_number
                }

        # Multi-word consolidation for vendor name
        if "vendor_name" in candidates and "VENDOR" in classes:
            v_idx = classes.index("VENDOR")
            v_tokens = [tokens[i] for i in range(len(tokens)) if probs[i][v_idx] >= 0.40]
            if len(v_tokens) > 1:
                v_tokens.sort(key=lambda t: (t.bbox["y1"], t.bbox["x1"]))
                candidates["vendor_name"]["value"] = " ".join(t.text for t in v_tokens)
                candidates["vendor_name"]["bbox"] = {
                    "x1": min(t.bbox["x1"] for t in v_tokens),
                    "y1": min(t.bbox["y1"] for t in v_tokens),
                    "x2": max(t.bbox["x2"] for t in v_tokens),
                    "y2": max(t.bbox["y2"] for t in v_tokens)
                }

        return candidates

    def _aggregate_candidates(
        self,
        field_name: str,
        rule_c: Optional[Dict[str, Any]],
        ml_c: Optional[Dict[str, Any]]
    ) -> Optional[ExtractedFieldCreate]:
        """
        Combines rule-based and ML-based candidates.
        Applies agreement boost when both engines agree on the candidate value.
        """
        if not rule_c and not ml_c:
            return None

        # If only rule exists
        if rule_c and not ml_c:
            return ExtractedFieldCreate(
                field_name=field_name,
                extracted_value=str(rule_c["value"]),
                confidence_score=rule_c["confidence"],
                ocr_confidence=rule_c.get("ocr_confidence"),
                extraction_method="RULE",
                page_number=rule_c.get("page_number", 1),
                bounding_box=rule_c.get("bbox")
            )

        # If only ML exists
        if ml_c and not rule_c:
            return ExtractedFieldCreate(
                field_name=field_name,
                extracted_value=str(ml_c["value"]),
                confidence_score=ml_c["confidence"],
                ocr_confidence=ml_c.get("ocr_confidence"),
                extraction_method="ML",
                page_number=ml_c.get("page_number", 1),
                bounding_box=ml_c.get("bbox")
            )

        # Both candidates exist: Compare values
        r_val = str(rule_c["value"]).strip()
        m_val = str(ml_c["value"]).strip()

        # Check agreement (exact or substring match)
        agreement = (r_val == m_val) or (r_val in m_val) or (m_val in r_val)
        if agreement:
            # Agreement boost: boost combined confidence
            boosted_conf = min(1.0, max(rule_c["confidence"], ml_c["confidence"]) + 0.05)
            # Prefer cleaner / rule-formatted value
            final_val = r_val if len(r_val) <= len(m_val) and len(r_val) > 0 else m_val
            return ExtractedFieldCreate(
                field_name=field_name,
                extracted_value=final_val,
                confidence_score=round(boosted_conf, 4),
                ocr_confidence=rule_c.get("ocr_confidence") or ml_c.get("ocr_confidence"),
                extraction_method="HYBRID",
                page_number=rule_c.get("page_number", 1),
                bounding_box=rule_c.get("bbox") or ml_c.get("bbox")
            )

        # Conflict resolution: Select candidate with higher confidence
        if rule_c["confidence"] >= ml_c["confidence"]:
            return ExtractedFieldCreate(
                field_name=field_name,
                extracted_value=r_val,
                confidence_score=rule_c["confidence"],
                ocr_confidence=rule_c.get("ocr_confidence"),
                extraction_method="RULE",
                page_number=rule_c.get("page_number", 1),
                bounding_box=rule_c.get("bbox")
            )
        else:
            return ExtractedFieldCreate(
                field_name=field_name,
                extracted_value=m_val,
                confidence_score=ml_c["confidence"],
                ocr_confidence=ml_c.get("ocr_confidence"),
                extraction_method="ML",
                page_number=ml_c.get("page_number", 1),
                bounding_box=ml_c.get("bbox")
            )


extraction_service = HybridExtractionService()

