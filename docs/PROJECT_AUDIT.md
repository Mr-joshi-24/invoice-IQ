# Invoice IQ (formerly DocuMind AI) — Comprehensive Project Audit
**Generated:** November 16, 2026  
**Auditor:** Senior AI/ML & Full-Stack Security Architect  
**Project Objective:** Transform into a production-grade, secure, verified AI/ML engineering platform ("Invoice IQ: Extract. Validate. Understand.").

---

## Executive Summary

The existing repository provides a solid architectural foundation with 29 passing unit/integration tests, clean modular Python backend code (FastAPI + SQLAlchemy + PyMuPDF), a Scikit-learn hybrid ML pipeline, and a modern React 18 / Tailwind frontend. 

However, a thorough audit reveals several critical vulnerabilities, security gaps, ML evaluation biases, and workflow limitations that must be remediated before the project can be considered resume- and production-ready.

---

## Detailed Audit by System Component (20 Areas)

### 1. Frontend Architecture
- **Current State**: React 18, Vite 5, Tailwind CSS, React Router v6, Lucide icons, Recharts.
- **Issues Found**:
  - `ReviewCenter.jsx`: Crashes with `TypeError: Cannot read properties of null (reading 'original_filename')` if `documentId` is invalid or API returns 404 because `document` is accessed without optional chaining.
  - No error boundary component wrapping routes; an uncaught rendering error in any component blanks out the entire application.
  - Zero automated unit/component tests in `frontend/` (missing Vitest / React Testing Library).
  - Review Center sends the entire form back to the backend rather than tracking dirty/modified fields.

### 2. Backend Architecture
- **Current State**: FastAPI async framework with APIRouter, Pydantic v2 schemas, SQLAlchemy 2.0 ORM, and dependency injection for sessions.
- **Issues Found**:
  - No database migration tool configured (missing Alembic; relies on `Base.metadata.create_all()`).
  - No rate limiting or request throttling middleware (vulnerable to DoS and brute-force uploads).
  - Global uncaught exception handlers are minimal; unexpected runtime exceptions can leak internal stack traces in HTTP 500 responses.

### 3. API Endpoints & Dependencies
- **Current State**: REST endpoints under `/api/v1/`: `/documents`, `/review`, `/analytics`, `/settings`.
- **Issues Found**:
  - Inconsistent HTTP status codes: Rejection and failure states sometimes return HTTP 200 with error strings inside payload rather than proper semantic status codes.
  - OpenAPI specification tags and descriptions still reference legacy branding ("DocuMind AI").
  - Lack of idempotency keys or transaction IDs on long-running document processing tasks.

### 4. Database Models & Relationships
- **Current State**: Relational entities (`Document`, `ExtractedField`, `ValidationResult`, `AnomalyResult`, `Review`) with cascade deletes.
- **Issues Found**:
  - **No `User` model**: The database lacks multi-tenancy, user ownership, and access controls. Every document is global and accessible to any client.
  - `ExtractedField`: Lacks separation between the original OCR extracted value and reviewer-corrected value (`extracted_value` is directly overwritten when corrected, permanently erasing ground truth).
  - Lacks database migration history (`alembic_version` table).

### 5. OCR Implementation
- **Current State**: PaddleOCR primary engine with PyMuPDF direct vector word extractor fallback.
- **Issues Found**:
  - PaddleOCR CPU package on Windows environments occasionally encounters MSVC runtime variations; PyMuPDF fallback operates cleanly, but OCR Character Error Rate (CER) and Word Error Rate (WER) are not actively benchmarked on real scanned noisy PDFs.
  - Line reconstruction relies on simple vertical delta thresholds, which can misalign multi-column invoices where lines are close vertically.

### 6. Image Preprocessing
- **Current State**: OpenCV deskewing (`minAreaRect`), CLAHE contrast equalization, Gaussian blur.
- **Issues Found**:
  - In environments where `cv2` is missing, preprocessing runs in pass-through mode without warning the user or adjusting OCR confidence.
  - No image resolution upscaling or DPI normalization for low-resolution smartphone uploads (e.g. 72 DPI photos).

### 7. Document Classification
- **Current State**: Pipeline currently assumes all uploaded files are invoices or receipts; no upstream document classifier to reject non-financial documents (e.g., resumes, legal contracts).
- **Recommended Fix**: Add a lightweight document-type classifier / heuristic filter to verify financial document structure before running heavy field extraction.

### 8. Information Extraction
- **Current State**: Hybrid extraction combining regex rules and token-level TF-IDF + Logistic Regression.
- **Issues Found**:
  - Anchors for `total_amount` must be carefully guarded against substring overlaps with `subtotal` (partially resolved, but needs explicit multi-line item table extraction).
  - Does not currently parse individual line-item tables (Item, Quantity, Rate, Amount) into structured arrays.

### 9. Confidence Scoring
- **Current State**: `confidence_service.py` computes field confidence and weighted document confidence.
- **Critical Bug**: When a mandatory field (e.g. `invoice_number` or `gstin`) is missing, it appends a message to `reasons`, but does **not** directly set `status = "NEEDS_REVIEW"`. If other extracted fields have high confidence, the weighted average can exceed the threshold ($\ge 0.80$), allowing an invoice with missing mandatory fields to be marked as `PROCESSED`!
- **Fix Required**: Immediate hard routing to `NEEDS_REVIEW` upon any missing mandatory field.

### 10. Validation Services
- **Current State**: GSTIN checksum/format, dates, non-negative amounts, math consistency ($|\text{Sub} + \text{Tax} - \text{Total}| \le 0.05$), duplicate check.
- **Issues Found**:
  - Duplicate check only queries by `invoice_number`, which can false-positive across different vendors who happen to use identical sequence numbers (e.g., `INV-001`). Must query compound key `(vendor_name, invoice_number)`.
  - Due date validation is missing.
  - Currency validation is missing.

### 11. Anomaly Detection
- **Current State**: Scikit-learn Isolation Forest on financial feature vectors + vendor historical Z-scores.
- **Issues Found**:
  - Feature vectors are not normalized before tree ingestion (`total_amount_log` is scale ~9, while `tax_ratio` is scale ~0.18, and `math_discrepancy` can be scale ~1000).
  - Missing values in subtotal are imputed with an assumed 18% tax (`total * 0.82`), which inadvertently masks anomalies.
  - Contamination hyperparameter is static (0.05) and cannot be dynamically adjusted per tenant.

### 12. ML Training and Inference Pipelines
- **Current State**: `train_classifier.py` and `train_anomaly.py` run independently.
- **Issues Found**:
  - Synthetic training data currently has 100% exact-match accuracy because layout geometry in the synthetic generator is overly uniform (fixed vertical bands). This will not generalize to real-world scanned invoices with varied layouts.
  - Model confidence is taken directly from raw `predict_proba()`, which is uncalibrated on sparse n-gram spaces.

### 13. Dataset Generation and Model Artifacts
- **Current State**: Synthetic generator in `ml/datasets/synthetic_generator.py`.
- **Issues Found**:
  - Relies solely on synthetic invoices; has not integrated or benchmarked against public benchmarks (e.g. SROIE, CORD, FUNSD).
  - Synthetic data metrics must be clearly segregated from real-world benchmarks to avoid claims of synthetic performance as production performance.

### 14. Authentication & Authorization (CRITICAL SECURITY GAP)
- **Current State**: **Completely Absent**.
- **Security Vulnerability**: No user model, no password hashing, no JWT auth, no session management. All API endpoints are public. Any user can view, edit, approve, or delete any invoice.
- **Fix Required**: Implement JWT-based authentication, Argon2/Bcrypt password hashing, Role-Based Access Control (`ADMIN`, `REVIEWER`, `VIEWER`), and tenant/user ownership on all `Document` entities.

### 15. Review Workflow
- **Current State**: `POST /documents/{id}/review` accepts reviewer actions.
- **Issues Found**:
  - Automatically marks **every** submitted field as `is_corrected = True` and sets `confidence_score = 1.0`, even for fields that were not modified by the reviewer.
  - Reviewer ID is spoofable (submitted directly in request payload without authentication check).
  - Overwrites `extracted_value` directly, losing the original OCR extraction record.

### 16. Frontend/Backend Integration
- **Current State**: Axios client with Vite proxy to `/api/v1`.
- **Issues Found**:
  - Polling for document processing status is manual; long-running OCR tasks can leave the user looking at a stale `PENDING` status.
  - Multi-file upload progress bar measures payload upload, but does not display per-file extraction progress.

### 17. Automated Tests
- **Current State**: 29 passing pytest tests in `backend/tests/`.
- **Issues Found**:
  - Zero frontend tests (no Vitest or Cypress/Playwright).
  - No security tests (no auth, no path traversal tests, no role permission tests).
  - No regression tests for the confidence routing or duplicate vendor checks.

### 18. Docker & Deployment Configuration
- **Current State**: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`.
- **Issues Found**:
  - `docker-compose.yml` hardcodes secrets (`documind_secret_password`).
  - Container and service names still use legacy `documind` identifiers.
  - Missing production health checks on frontend container.
  - Missing GitHub Actions CI/CD pipeline for automated test execution on push/PR.

### 19. Environment Variables
- **Current State**: `.env`, `.env.example`.
- **Issues Found**:
  - `PROJECT_NAME="DocuMind AI"` needs rebranding to `Invoice IQ`.
  - Missing JWT secret key (`JWT_SECRET_KEY`), access token expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`), and database connection pooling settings.

### 20. Documentation
- **Current State**: `README.md`, `docs/architecture.md`, `docs/dataset.md`, `docs/model_evaluation.md`.
- **Issues Found**:
  - All documentation uses legacy branding (`DocuMind AI`).
  - Lacks dedicated security documentation (`docs/SECURITY.md`), API reference (`docs/API_DOCUMENTATION.md`), and interview prep guide (`docs/INTERVIEW_PREPARATION.md`).

---

## Prioritized Issue Matrix

| Issue ID | Category | Severity | Description | Target Phase |
| :--- | :--- | :---: | :--- | :---: |
| **SEC-01** | Security | **CRITICAL** | Zero authentication & authorization; all document endpoints are unauthenticated and public. | Phase 7 |
| **SEC-02** | Security | **HIGH** | Unchecked upload file writes before size validation; potential disk exhaustion DoS. | Phase 2 |
| **SEC-03** | Security | **MEDIUM** | Filename path traversal vulnerability on uploaded file storage. | Phase 2 |
| **BUG-01** | ML/Logic | **CRITICAL** | Missing mandatory field does not force `NEEDS_REVIEW` if average confidence exceeds threshold. | Phase 2 |
| **BUG-02** | Workflow | **HIGH** | Review Center marks all submitted fields as `is_corrected=True` and overwrites original values. | Phase 2 |
| **BUG-03** | Frontend | **HIGH** | `ReviewCenter.jsx` crashes on null/404 document access without optional chaining. | Phase 2 |
| **BUG-04** | Analytics | **MEDIUM** | Dashboard displays 100% success rate when total documents is 0. | Phase 2 |
| **BUG-05** | Validation | **MEDIUM** | Duplicate invoice check matches invoice number alone without scoping to vendor. | Phase 5 |
| **ML-01** | Machine Learning | **HIGH** | Synthetic dataset generator uses fixed vertical bands; 100% test accuracy indicates layout memorization. | Phase 3 |
| **ML-02** | Machine Learning | **MEDIUM** | Logistic regression token probabilities are uncalibrated; lacks Brier score and reliability diagrams. | Phase 3 |
| **ML-03** | Anomaly | **MEDIUM** | Isolation Forest feature vector scales are unnormalized; missing subtotal is artificially imputed. | Phase 3 |
| **OPS-01** | DevOps | **MEDIUM** | Missing Alembic database migration environment. | Phase 6 |
| **OPS-02** | DevOps | **MEDIUM** | Missing automated GitHub Actions CI/CD workflow. | Phase 10 |
| **QA-01** | Testing | **MEDIUM** | Zero frontend automated test coverage. | Phase 9 |
| **BRAND-01**| Rebranding | **HIGH** | Legacy branding ("DocuMind AI") throughout codebase, UI, configs, and documentation. | Phase 1 |

