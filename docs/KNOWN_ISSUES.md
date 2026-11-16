# Invoice IQ — Known Issues & Bug Register

This document tracks all identified defects, security vulnerabilities, edge-case limitations, and architectural inconsistencies across the codebase, along with their resolution status.

---

## Issue Status Matrix

| Issue ID | Severity | Category | Title | Status | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ISSUE-001** | CRITICAL | Pipeline | Mandatory field missing did not trigger hard human review | **RESOLVED** | `test_mandatory_fields_hard_routing` (Passed) |
| **ISSUE-002** | HIGH | HITL Review | Review submission destroyed original values & set false 100% confidence | **RESOLVED** | `test_review_dirty_checking_and_original_value` (Passed) |
| **ISSUE-003** | HIGH | Frontend | ReviewCenter crash on null or 404 document | **RESOLVED** | 404 handling & optional chaining added |
| **ISSUE-004** | CRITICAL | Security | Unauthenticated API access & missing authorization | **RESOLVED** | JWT Auth & RBAC implemented in `test_auth.py` (Passed) |
| **ISSUE-005** | HIGH | Security | File upload disk exhaustion & path traversal vulnerability | **RESOLVED** | Streaming size check, safe stem naming & page limit (Passed) |
| **ISSUE-006** | MEDIUM | Analytics | Dashboard displays 100% success rate when zero documents exist | **RESOLVED** | Returns 0.0% / "N/A" on zero state (Passed) |
| **ISSUE-007** | MEDIUM | Validation | Duplicate invoice check was not vendor-aware | **RESOLVED** | Same-vendor vs cross-vendor duplicate handling (Passed) |
| **ISSUE-008** | HIGH | ML / Quality | Overly uniform synthetic dataset yielding artificial 100% accuracy | **RESOLVED** | 4-layout templates, spatial jitter & distractor tokens (Passed) |
| **ISSUE-009** | MEDIUM | DevOps | Missing Alembic versioned migration system | **RESOLVED** | Alembic initialized, tracking `001_initial_schema` (Passed) |
| **ISSUE-010** | HIGH | Product | Legacy "DocuMind AI" branding throughout codebase | **RESOLVED** | Full Phase 1 Rebranding to Invoice IQ (Passed) |

---

## 1. Resolved Issues Details

### ISSUE-001: Missing Mandatory Field Does Not Trigger Hard Human Review (RESOLVED)
- **Root Cause**: `confidence_service.py` evaluated a weighted average of available fields without gating on required fields. High confidence on optional fields masked the omission of critical fields like `invoice_number` or `total_amount`.
- **Resolution**: Implemented strict hard-gating for `MANDATORY_FIELDS = {"invoice_number", "total_amount"}`. If unextracted, empty, or confidence $< 0.40$, status is unconditionally set to `NEEDS_REVIEW`.
- **Verified In**: `backend/tests/test_validation_anomaly.py::test_mandatory_fields_hard_routing`.

### ISSUE-002: Review Submission Destroys Original Extracted Data (RESOLVED)
- **Root Cause**: Unconditional overwrite of all fields during review submission, destroying the machine-extracted value and falsely marking untouched fields as human-corrected.
- **Resolution**:
  1. Added `original_value` column to `ExtractedField` model and schema.
  2. Implemented dirty-checking on backend (`review.py`) and frontend (`ReviewCenter.jsx`).
  3. Original values are permanently preserved; only genuinely modified fields receive `is_corrected = True` and `HUMAN_CORRECTED`.
- **Verified In**: `backend/tests/test_api.py::test_review_dirty_checking_and_original_value`.

### ISSUE-003: ReviewCenter Frontend Crash on Null or 404 Document (RESOLVED)
- **Root Cause**: Direct property access (`document.original_filename`) without error state handling when document ID was invalid or deleted.
- **Resolution**: Added 404 error state screen with navigation back to documents list and optional chaining (`document?.original_filename`) across all UI bindings.
- **Verified In**: Frontend production build and browser error boundary testing.

### ISSUE-004: Unauthenticated API Access & Missing Authorization (RESOLVED)
- **Root Cause**: All API endpoints were open without authentication headers, user models, or role-based access control.
- **Resolution**:
  1. Implemented `User` model (`users` table) with `ADMIN`, `REVIEWER`, and `VIEWER` roles.
  2. Added secure `bcrypt` salted password hashing and JWT token generation (`/api/v1/auth/login`, `/register`, `/me`).
  3. Implemented `get_current_user` and `require_roles([UserRole.ADMIN, ...])` dependencies.
  4. Seeded default platform accounts (`admin@invoiceiq.com`, `auditor@invoiceiq.com`, `viewer@invoiceiq.com`).
- **Verified In**: `backend/tests/test_auth.py` (6 tests passing).

### ISSUE-005: File Upload Security, Streaming, and Path Traversal (RESOLVED)
- **Root Cause**: Direct `shutil.copyfileobj` to disk with raw client filenames and unbounded PDF page counts.
- **Resolution**:
  1. Filenames sanitized via `Path(upload_file.filename).name` and safe alphanumeric regex filtering.
  2. Uploads streamed in 1 MB chunks with immediate HTTP 413 abort if file size exceeds `MAX_UPLOAD_SIZE_MB`.
  3. Bounded maximum allowable PDF page limit to 25 pages in `validate_document_file` and `convert_pdf_to_images`.
- **Verified In**: `backend/tests/test_api.py::test_upload_security_filename_sanitization`.

### ISSUE-006: Dashboard 100% Success Rate When Zero Documents Exist (RESOLVED)
- **Root Cause**: Ternary returned 100.0% when `total_docs == 0`.
- **Resolution**: Corrected to return `0.0%` in `analytics.py` and display `'N/A'` in `Dashboard.jsx`.
- **Verified In**: `backend/app/api/v1/analytics.py` overview calculations.

### ISSUE-007: Duplicate Invoice Check Scoped by Invoice Number Only (RESOLVED)
- **Root Cause**: Queried solely by invoice number, flagging invoices from different vendors who legitimately use the same numbering sequence as duplicates.
- **Resolution**: Refined duplicate check to verify whether vendor matches: identical vendor + invoice number triggers `FAILED` (duplicate), while differing known vendors trigger `WARNING`.
- **Verified In**: `backend/tests/test_validation_anomaly.py::test_duplicate_invoice_validation`.

### ISSUE-008: Overly Uniform Synthetic Dataset (RESOLVED)
- **Resolution**: Built 4 distinct commercial invoice layout templates with random spatial coordinate jitter ($\pm 0.015 - 0.03$) and distractor background tokens (phone, PO, HSN, unit rates, quantities).
- **Verified In**: Multi-model benchmarks in `ml/artifacts/metrics_summary.json` and `docs/model_evaluation.md`.

### ISSUE-009: Missing Database Versioned Migrations (RESOLVED)
- **Resolution**: Initialized Alembic migration infrastructure (`alembic.ini`, `alembic/env.py`, `alembic/versions/001_initial_schema.py`) tracking `001_initial_schema (head)` with SQLite batch mode support.
- **Verified In**: `alembic current` -> `001_initial_schema (head)`.

### ISSUE-010: Complete Rebranding to Invoice IQ (RESOLVED)
- **Resolution**: Rebranded all frontend pages, favicon SVG, manifest, backend FastAPI title, OpenAPI metadata, root endpoints, logger names, Docker configurations, and documentation to **Invoice IQ** ("Extract. Validate. Understand.").
- **Verified In**: `backend/tests/test_main.py::test_root_endpoint`, `npm run build`, and clean build checks.
