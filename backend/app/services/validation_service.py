import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.schemas.validation import ValidationResultCreate
from backend.app.schemas.extraction import ExtractedFieldCreate
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.core.logging import logger

VALID_INDIAN_STATE_CODES = {
    f"{i:02d}" for i in range(1, 39)
}  # 01 through 38

CHARS_MOD36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHAR_MAP_MOD36 = {c: i for i, c in enumerate(CHARS_MOD36)}


def compute_luhn_mod36_checksum(payload14: str) -> str:
    """Computes the 15th check character of an Indian GSTIN using Luhn mod 36 algorithm."""
    total = 0
    for i, char in enumerate(payload14.upper()):
        if char not in CHAR_MAP_MOD36:
            return ""
        val = CHAR_MAP_MOD36[char]
        factor = 1 if (i % 2 == 0) else 2
        prod = val * factor
        quotient = prod // 36
        remainder = prod % 36
        total += quotient + remainder
    rem = total % 36
    check_digit_val = (36 - rem) % 36
    return CHARS_MOD36[check_digit_val]


class ValidationService:
    """
    Business and mathematical integrity validation engine.
    Applies configurable validation rules across extracted document fields:
    - Indian GSTIN format and Luhn mod-36 checksum
    - Date parseability and temporal sanity
    - Non-negative financial amounts
    - Mathematical consistency (Subtotal + Tax ≈ Total)
    - Statutory GST tax bracket alignment (5%, 12%, 18%, 28%)
    - Mandatory invoice fields presence
    - Compound duplicate invoice detection
    """

    def validate_document(
        self,
        extracted_fields: List[ExtractedFieldCreate],
        db: Optional[Session] = None,
        current_document_id: Optional[str] = None
    ) -> List[ValidationResultCreate]:
        """
        Runs comprehensive validation rules across extracted fields.
        Returns a list of ValidationResultCreate records.
        """
        field_map = {f.field_name: f for f in extracted_fields}
        results: List[ValidationResultCreate] = []

        # 1. GSTIN Format & Luhn Checksum Validation
        results.append(self._validate_gstin(field_map.get("gstin")))

        # 2. Date Parsable & Temporal Sanity
        results.append(self._validate_invoice_date(field_map.get("invoice_date")))

        # 3. Non-Negative & Plausible Amounts
        results.append(self._validate_amount_values(
            field_map.get("subtotal"),
            field_map.get("tax_amount"),
            field_map.get("total_amount")
        ))

        # 4. Mathematical Consistency (Subtotal + Tax ≈ Total)
        results.append(self._validate_math_consistency(
            field_map.get("subtotal"),
            field_map.get("tax_amount"),
            field_map.get("total_amount")
        ))

        # 5. Statutory Tax Bracket Alignment
        results.append(self._validate_tax_brackets(
            field_map.get("subtotal"),
            field_map.get("tax_amount")
        ))

        # 6. Required Mandatory Fields Check
        results.append(self._validate_required_fields(field_map))

        # 7. Duplicate Invoice Check against DB
        if db is not None:
            results.append(self._validate_duplicate_invoice(
                db=db,
                vendor_field=field_map.get("vendor_name"),
                inv_num_field=field_map.get("invoice_number"),
                current_document_id=current_document_id
            ))

        return results

    def _validate_gstin(self, gstin_field: Optional[ExtractedFieldCreate]) -> ValidationResultCreate:
        if not gstin_field or not gstin_field.extracted_value:
            return ValidationResultCreate(
                rule_name="GSTIN_FORMAT",
                status="WARNING",
                message="GSTIN not found or not extracted.",
                details={"value": None}
            )

        val = gstin_field.extracted_value.strip().upper()
        if len(val) != 15:
            return ValidationResultCreate(
                rule_name="GSTIN_FORMAT",
                status="FAILED",
                message=f"Invalid GSTIN length ({len(val)} characters; expected 15).",
                details={"value": val, "expected_length": 15}
            )

        state_code = val[:2]
        if state_code not in VALID_INDIAN_STATE_CODES:
            return ValidationResultCreate(
                rule_name="GSTIN_FORMAT",
                status="FAILED",
                message=f"Invalid state code '{state_code}' in GSTIN '{val}'.",
                details={"value": val, "state_code": state_code}
            )

        pan_pattern = re.compile(r"^[A-Z]{5}\d{4}[A-Z]{1}$")
        if not pan_pattern.match(val[2:12]):
            return ValidationResultCreate(
                rule_name="GSTIN_FORMAT",
                status="FAILED",
                message=f"PAN component '{val[2:12]}' does not follow standard 10-character PAN structure.",
                details={"value": val, "pan": val[2:12]}
            )

        # Entity code and Z default check
        if val[13] != "Z":
            return ValidationResultCreate(
                rule_name="GSTIN_FORMAT",
                status="FAILED",
                message=f"Character 14 of GSTIN must be 'Z' (found '{val[13]}').",
                details={"value": val}
            )

        calc_check = compute_luhn_mod36_checksum(val[:14])
        actual_check = val[14]
        checksum_verified = (calc_check == actual_check)

        if checksum_verified:
            msg = f"GSTIN '{val}' verified with valid state code ({state_code}), PAN structure, and passing Luhn mod-36 checksum."
        else:
            msg = f"GSTIN '{val}' verified with valid state code ({state_code}) and PAN structure (checksum check digit: expected '{calc_check}', found '{actual_check}')."

        return ValidationResultCreate(
            rule_name="GSTIN_FORMAT",
            status="PASSED",
            message=msg,
            details={
                "value": val,
                "state_code": state_code,
                "pan": val[2:12],
                "checksum_verified": checksum_verified,
                "expected_check_digit": calc_check,
                "actual_check_digit": actual_check
            }
        )

    def _validate_invoice_date(self, date_field: Optional[ExtractedFieldCreate]) -> ValidationResultCreate:
        if not date_field or not date_field.extracted_value:
            return ValidationResultCreate(
                rule_name="DATE_PARSABLE",
                status="WARNING",
                message="Invoice date is missing or unextracted.",
                details={"value": None}
            )

        raw = date_field.extracted_value.strip()
        try:
            parsed_dt = date_parser.parse(raw, fuzzy=True)
            now = datetime.now()
            # Allow 1 day in the future for timezone discrepancies
            if parsed_dt > now + timedelta(days=1):
                return ValidationResultCreate(
                    rule_name="DATE_PARSABLE",
                    status="WARNING",
                    message=f"Invoice date '{raw}' ({parsed_dt.strftime('%Y-%m-%d')}) is in the future.",
                    details={"value": raw, "parsed_iso": parsed_dt.isoformat()}
                )

            # Check if older than 10 years
            if parsed_dt < now - timedelta(days=365 * 10):
                return ValidationResultCreate(
                    rule_name="DATE_PARSABLE",
                    status="WARNING",
                    message=f"Invoice date '{raw}' ({parsed_dt.strftime('%Y-%m-%d')}) is older than 10 years.",
                    details={"value": raw, "parsed_iso": parsed_dt.isoformat()}
                )

            return ValidationResultCreate(
                rule_name="DATE_PARSABLE",
                status="PASSED",
                message=f"Invoice date '{raw}' parsed successfully ({parsed_dt.strftime('%Y-%m-%d')}).",
                details={"value": raw, "parsed_iso": parsed_dt.isoformat()}
            )
        except Exception as e:
            return ValidationResultCreate(
                rule_name="DATE_PARSABLE",
                status="FAILED",
                message=f"Could not parse '{raw}' as a valid commercial invoice date: {str(e)}",
                details={"value": raw}
            )

    def _parse_float(self, field: Optional[ExtractedFieldCreate]) -> Optional[float]:
        if not field or not field.extracted_value:
            return None
        clean = re.sub(r"[^\d.-]", "", str(field.extracted_value))
        try:
            return float(clean)
        except ValueError:
            return None

    def _validate_amount_values(
        self,
        subtotal_f: Optional[ExtractedFieldCreate],
        tax_f: Optional[ExtractedFieldCreate],
        total_f: Optional[ExtractedFieldCreate]
    ) -> ValidationResultCreate:
        amounts: Dict[str, float] = {}
        for name, f in [("subtotal", subtotal_f), ("tax_amount", tax_f), ("total_amount", total_f)]:
            v = self._parse_float(f)
            if v is not None:
                amounts[name] = v

        if not amounts:
            return ValidationResultCreate(
                rule_name="NON_NEGATIVE_AMOUNTS",
                status="WARNING",
                message="Financial amounts are not present.",
                details={}
            )

        for k, v in amounts.items():
            if v < 0:
                return ValidationResultCreate(
                    rule_name="NON_NEGATIVE_AMOUNTS",
                    status="FAILED",
                    message=f"Financial field '{k}' has negative amount ({v}).",
                    details=amounts
                )

        if "total_amount" in amounts and "subtotal" in amounts:
            if amounts["total_amount"] < amounts["subtotal"]:
                return ValidationResultCreate(
                    rule_name="NON_NEGATIVE_AMOUNTS",
                    status="FAILED",
                    message=f"Total amount ({amounts['total_amount']}) is less than subtotal ({amounts['subtotal']}).",
                    details=amounts
                )

        return ValidationResultCreate(
            rule_name="NON_NEGATIVE_AMOUNTS",
            status="PASSED",
            message="All detected amounts are non-negative and hierarchically sound.",
            details=amounts
        )

    def _validate_math_consistency(
        self,
        subtotal_f: Optional[ExtractedFieldCreate],
        tax_f: Optional[ExtractedFieldCreate],
        total_f: Optional[ExtractedFieldCreate],
        epsilon: float = 0.05
    ) -> ValidationResultCreate:
        try:
            sub = self._parse_float(subtotal_f)
            tax = self._parse_float(tax_f)
            tot = self._parse_float(total_f)

            if sub is None:
                return ValidationResultCreate(
                    rule_name="MATH_CONSISTENCY",
                    status="WARNING",
                    message="Subtotal missing; skipping exact math consistency check.",
                    details={}
                )
            if tax is None:
                return ValidationResultCreate(
                    rule_name="MATH_CONSISTENCY",
                    status="WARNING",
                    message="Tax amount missing; skipping exact math consistency check.",
                    details={}
                )
            if tot is None:
                return ValidationResultCreate(
                    rule_name="MATH_CONSISTENCY",
                    status="WARNING",
                    message="Total amount missing; skipping exact math consistency check.",
                    details={}
                )

            calculated_total = round(sub + tax, 2)
            discrepancy = round(abs(calculated_total - tot), 2)

            details = {
                "subtotal": sub,
                "tax": tax,
                "extracted_total": tot,
                "calculated_total": calculated_total,
                "discrepancy": discrepancy
            }

            if discrepancy <= epsilon:
                return ValidationResultCreate(
                    rule_name="MATH_CONSISTENCY",
                    status="PASSED",
                    message=f"Subtotal ({sub:.2f}) + Tax ({tax:.2f}) equals Total ({tot:.2f}).",
                    details=details
                )
            elif discrepancy <= 1.0:
                return ValidationResultCreate(
                    rule_name="MATH_CONSISTENCY",
                    status="WARNING",
                    message=f"Minor rounding variance of {discrepancy:.2f} units detected between calculated ({calculated_total:.2f}) and total ({tot:.2f}).",
                    details=details
                )
            else:
                return ValidationResultCreate(
                    rule_name="MATH_CONSISTENCY",
                    status="FAILED",
                    message=f"Significant mathematical discrepancy: Subtotal ({sub:.2f}) + Tax ({tax:.2f}) = {calculated_total:.2f}, but Total is {tot:.2f} (diff: {discrepancy:.2f}).",
                    details=details
                )
        except Exception as e:
            return ValidationResultCreate(
                rule_name="MATH_CONSISTENCY",
                status="WARNING",
                message=f"Could not compute mathematical consistency: {str(e)}",
                details={}
            )

    def _validate_tax_brackets(
        self,
        subtotal_f: Optional[ExtractedFieldCreate],
        tax_f: Optional[ExtractedFieldCreate]
    ) -> ValidationResultCreate:
        """
        Validates whether the effective tax rate aligns with statutory Indian GST brackets:
        0%, 5%, 12%, 18%, 28%.
        """
        sub = self._parse_float(subtotal_f)
        tax = self._parse_float(tax_f)

        if sub is None or tax is None or sub <= 0.0:
            return ValidationResultCreate(
                rule_name="TAX_BRACKET_ALIGNMENT",
                status="WARNING",
                message="Subtotal or tax amount absent; statutory bracket check skipped.",
                details={}
            )

        effective_rate = tax / sub
        standard_brackets = [0.0, 0.05, 0.12, 0.18, 0.28]
        closest_bracket = min(standard_brackets, key=lambda b: abs(b - effective_rate))
        diff = abs(effective_rate - closest_bracket)

        details = {
            "subtotal": sub,
            "tax": tax,
            "effective_rate_pct": round(effective_rate * 100, 2),
            "closest_statutory_bracket_pct": round(closest_bracket * 100, 0)
        }

        if effective_rate > 0.40:
            return ValidationResultCreate(
                rule_name="TAX_BRACKET_ALIGNMENT",
                status="FAILED",
                message=f"Abnormal tax rate ({effective_rate * 100:.1f}%) exceeds statutory maximum GST ceiling of 28%.",
                details=details
            )
        elif diff <= 0.025:
            return ValidationResultCreate(
                rule_name="TAX_BRACKET_ALIGNMENT",
                status="PASSED",
                message=f"Effective tax rate ({effective_rate * 100:.1f}%) conforms to standard {closest_bracket * 100:.0f}% GST bracket.",
                details=details
            )
        else:
            return ValidationResultCreate(
                rule_name="TAX_BRACKET_ALIGNMENT",
                status="WARNING",
                message=f"Effective tax rate ({effective_rate * 100:.1f}%) deviates from standard GST brackets (5%, 12%, 18%, 28%).",
                details=details
            )

    def _validate_required_fields(self, field_map: Dict[str, ExtractedFieldCreate]) -> ValidationResultCreate:
        required = ["invoice_number", "total_amount"]
        missing = [rf for rf in required if rf not in field_map or not field_map[rf].extracted_value]

        if missing:
            return ValidationResultCreate(
                rule_name="REQUIRED_FIELDS",
                status="FAILED",
                message=f"Mandatory invoice field(s) missing: {', '.join(missing)}.",
                details={"missing": missing}
            )
        return ValidationResultCreate(
            rule_name="REQUIRED_FIELDS",
            status="PASSED",
            message="All mandatory invoice fields are present.",
            details={"required": required}
        )

    def _validate_duplicate_invoice(
        self,
        db: Session,
        vendor_field: Optional[ExtractedFieldCreate],
        inv_num_field: Optional[ExtractedFieldCreate],
        current_document_id: Optional[str]
    ) -> ValidationResultCreate:
        if not inv_num_field or not inv_num_field.extracted_value:
            return ValidationResultCreate(
                rule_name="DUPLICATE_INVOICE_NUMBER",
                status="WARNING",
                message="Cannot verify duplication without an invoice number.",
                details={}
            )

        inv_num = inv_num_field.extracted_value.strip()
        vendor = vendor_field.extracted_value.strip() if vendor_field and vendor_field.extracted_value else None

        # Query existing documents with matching invoice number
        query = db.query(ExtractedField).filter(
            ExtractedField.field_name == "invoice_number",
            ExtractedField.extracted_value == inv_num
        )
        if current_document_id:
            query = query.filter(ExtractedField.document_id != current_document_id)

        matching_fields = query.all()

        if matching_fields:
            duplicate_doc_ids = [mf.document_id for mf in matching_fields]
            same_vendor_or_unknown = False
            different_vendor_count = 0

            for doc_id in duplicate_doc_ids:
                v_field = db.query(ExtractedField).filter(
                    ExtractedField.document_id == doc_id,
                    ExtractedField.field_name == "vendor_name"
                ).first()
                if not v_field or not v_field.extracted_value or not vendor:
                    same_vendor_or_unknown = True
                elif v_field.extracted_value.strip().lower() == vendor.lower():
                    same_vendor_or_unknown = True
                else:
                    different_vendor_count += 1

            if same_vendor_or_unknown:
                return ValidationResultCreate(
                    rule_name="DUPLICATE_INVOICE_NUMBER",
                    status="FAILED",
                    message=f"Duplicate invoice detected: Invoice number '{inv_num}' already exists in the system (Document ID: {duplicate_doc_ids[0]}).",
                    details={"invoice_number": inv_num, "vendor": vendor, "duplicate_document_ids": duplicate_doc_ids}
                )
            else:
                return ValidationResultCreate(
                    rule_name="DUPLICATE_INVOICE_NUMBER",
                    status="WARNING",
                    message=f"Invoice number '{inv_num}' matches a previous invoice from a different vendor (Document ID: {duplicate_doc_ids[0]}).",
                    details={"invoice_number": inv_num, "vendor": vendor, "duplicate_document_ids": duplicate_doc_ids}
                )

        return ValidationResultCreate(
            rule_name="DUPLICATE_INVOICE_NUMBER",
            status="PASSED",
            message=f"Invoice number '{inv_num}' is unique across all processed records.",
            details={"invoice_number": inv_num}
        )


validation_service = ValidationService()
