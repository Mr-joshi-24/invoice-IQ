# Invoice IQ — Prioritized Implementation Plan (Phases 1–12)

**Official Product Name:** Invoice IQ  
**Official Tagline:** Extract. Validate. Understand.  
**Execution Standard:** Senior AI/ML Engineer, Software Architect, Security Engineer, QA Automation Engineer.

---

## Roadmap Overview

```
Phase 0: Complete Repository Audit (CURRENT)
  │
  ├──► Phase 1: Complete Rebranding to Invoice IQ
  │
  ├──► Phase 2: Fix Existing Critical Bugs (Security, Routing, Review, Frontend)
  │
  ├──► Phase 3: Machine Learning Improvements (Diversity, Leakage, Calibration, Anomaly)
  │
  ├──► Phase 4: Hybrid Document Extraction Pipeline (Modular Orchestration)
  │
  ├──► Phase 5: Comprehensive Invoice Validation (GSTIN, Math, Line Items, Vendors)
  │
  ├──► Phase 6: Backend Engineering (Alembic Migrations, Error Handling, Rate Limiting)
  │
  ├──► Phase 7: Security (JWT Authentication, Password Hashing, User Ownership & RBAC)
  │
  ├──► Phase 8: Frontend Improvements (Enterprise UI, Diff Viewer, Error Boundaries)
  │
  ├──► Phase 9: Automated Testing & Regressions (Unit, API, Frontend, E2E)
  │
  ├──► Phase 10: Production Deployment (PostgreSQL, Docker, GitHub Actions CI/CD)
  │
  ├──► Phase 11: Professional Documentation (Specs, Architecture, Security, Interview Guide)
  │
  └──► Phase 12: GitHub Quality & Portfolio Polish
```

---

## Phase-by-Phase Execution Details

### Phase 1: Complete Rebranding to Invoice IQ
- **Objective**: Establish unified enterprise brand identity ("Invoice IQ: Extract. Validate. Understand.").
- **Tasks**:
  1. Frontend Branding: Update `index.html` (title, meta, favicon SVG), `Sidebar.jsx`, `Navbar.jsx`, `Dashboard.jsx`, error pages, empty states, and about modals.
  2. Backend Branding: Update FastAPI title, OpenAPI metadata, Swagger tags, `settings.PROJECT_NAME = "Invoice IQ"`, logger names (`invoice_iq`), and health check payloads.
  3. Config & Docker Branding: Update `.env`, `.env.example`, `docker-compose.yml` service and container names (`invoice-iq-backend`, `invoice-iq-frontend`, `invoice-iq-db`).
  4. Documentation & GitHub: Update `README.md`, `package.json` (`"name": "invoice-iq-frontend"`).
  5. Create `docs/REBRANDING_MIGRATION.md` documenting all modified files and migration safety.
- **Exit Criteria**: `grep -rn "DocuMind"` returns 0 active user-facing instances.

---

### Phase 2: Fix Existing Critical Bugs
- **Objective**: Eliminate high-severity logic, workflow, and security vulnerabilities.
- **Tasks**:
  1. **Confidence Scoring Gate (`confidence_service.py`)**: Ensure missing mandatory fields (`invoice_number`, `total_amount`) immediately trigger `status = "NEEDS_REVIEW"` regardless of mathematical score.
  2. **Human Review Integrity (`ReviewCenter.jsx` & `review.py`)**: Track dirty state in the frontend; only submit genuinely changed fields; preserve original extracted values in the database; do not assign 100% confidence to untouched fields.
  3. **File Upload Security (`documents.py`)**: Enforce streaming upload size limit (max 15 MB chunk check), sanitize filenames via `Path(filename).name`, enforce max 25 PDF pages limit, and reject corrupted documents before storage.
  4. **Frontend Reliability (`ReviewCenter.jsx`, `Documents.jsx`)**: Add React Error Boundaries; fix null pointer crash on 404/not-found documents with optional chaining and friendly error states.
  5. **Dashboard Accuracy (`analytics.py`)**: Set `success_rate = 0.0` (or `None`) when `total_documents == 0`; show `"N/A"` in UI for insufficient data.
- **Exit Criteria**: All regression tests pass in `backend/tests/test_validation_anomaly.py` and `test_api.py`.

---

### Phase 3: Machine Learning Improvements
- **Objective**: Elevate AI/ML credibility for technical interviews and competitive AI/ML internship applications.
- **Tasks**:
  1. **Dataset Diversity (`synthetic_generator.py`)**: Add multi-template generators (boxed tables, column-based, minimalist, header-left, header-center) with coordinate jitter and diverse fonts.
  2. **Real-World Benchmarking (`docs/dataset.md`)**: Document layout features, compare with public SROIE/CORD benchmark standards, and maintain strict vendor-level leakage prevention.
  3. **Model Experimentation (`train_classifier.py`)**: Compare TF-IDF + Logistic Regression vs Linear SVM vs Random Forest; log hyperparameter grid search results on validation split.
  4. **Confidence Calibration**: Calculate Brier score and Expected Calibration Error (ECE); implement Platt scaling / isotonic calibration for output probabilities.
  5. **Anomaly Detection Enhancement (`anomaly_service.py` & `train_anomaly.py`)**: Apply StandardScaler/RobustScaler on Isolation Forest features; handle missing subtotal without artificial 18% assumption; refine multi-factor explanations.
- **Exit Criteria**: Updated model artifacts in `ml/artifacts/` with verified calibration curves and honest evaluation reports.

---

### Phase 4: Hybrid Document Extraction Pipeline
- **Objective**: Modularize the document processing pipeline with traceable stage states.
- **Tasks**:
  1. Pipeline Modularization: Define discrete stages (`INGESTION`, `PREPROCESSING`, `OCR`, `CLASSIFICATION`, `EXTRACTION`, `VALIDATION`, `ANOMALY_SCORING`, `CONFIDENCE_ROUTING`, `PERSISTENCE`).
  2. Execution Timing: Track per-stage execution latency (ms) and persist in document processing metadata.
  3. Retry Support: Allow retrying failed stages individually.
- **Exit Criteria**: Full pipeline executes with stage-level timing and granular error traces.

---

### Phase 5: Comprehensive Invoice Validation
- **Objective**: Implement robust, enterprise-grade business rules.
- **Tasks**:
  1. Compound Duplicate Check: Cross-check both `(vendor_name, invoice_number)` across database records.
  2. Currency Validation: Validate recognized currency symbols (INR, USD, EUR, GBP) and format consistency.
  3. Line-Item Table Arithmetic: Where line items exist, verify $\sum (\text{Qty} \times \text{Unit Price}) \approx \text{Subtotal}$.
  4. Due Date vs Invoice Date: Verify $\text{Due Date} \ge \text{Invoice Date}$.
- **Exit Criteria**: Validation test suite covering 10+ business integrity scenarios with 100% pass rate.

---

### Phase 6: Backend Engineering
- **Objective**: Solidify enterprise backend reliability and maintainability.
- **Tasks**:
  1. **Alembic Migrations**: Initialize Alembic, create initial baseline migration, and verify automated schema versioning.
  2. **Standardized API Error Format**: RFC 7807 problem details with consistent error envelopes.
  3. **Health Check Enhancement**: Deep health check verifying database read/write and disk storage availability (`/api/v1/health/deep`).
  4. **Structured Logging**: JSON logging with request IDs for distributed tracing.
- **Exit Criteria**: Alembic migrations run cleanly up and down; deep health check verifies DB connectivity.

---

### Phase 7: Security (Authentication & Authorization)
- **Objective**: Secure the entire platform with enterprise multi-tenancy and RBAC.
- **Tasks**:
  1. **User Model & Passwords**: Create `User` table (id, email, hashed_password, role, created_at) using Passlib/Bcrypt.
  2. **JWT Authentication**: Endpoints `/api/v1/auth/register`, `/api/v1/auth/login`, and `/api/v1/auth/me`.
  3. **Role-Based Access Control (RBAC)**: Roles `ADMIN`, `REVIEWER`, `VIEWER`.
  4. **Document Ownership**: Add `owner_id` to `Document`; enforce tenancy so users only access their own invoices (or auditors access assigned queues).
  5. **Rate Limiting**: Protect upload and auth endpoints against brute-force attacks via SlowAPI.
- **Exit Criteria**: Unauthorized requests return 401/403; security tests verify tenant isolation.

---

### Phase 8: Frontend Improvements
- **Objective**: Polish the user interface into an enterprise-grade SaaS platform.
- **Tasks**:
  1. Authentication UI: Login and registration views with JWT token storage in `localStorage`/`httpOnly` cookie.
  2. Review Center Diff Viewer: Visual comparison showing original OCR extracted value vs reviewer corrected value.
  3. Real-Time Status Feedback: Dynamic polling or WebSocket updates for long-running OCR tasks.
  4. Accessible & Responsive: Full keyboard navigation and mobile-responsive layouts.
- **Exit Criteria**: Frontend build succeeds without warnings; all pages render with professional visual hierarchy.

---

### Phase 9: Automated Testing & Regressions
- **Objective**: Build a robust multi-layer test pyramid.
- **Tasks**:
  1. Backend Unit & Regression Tests (targeting 40+ tests).
  2. API Security & Tenancy Tests (testing unauthorized access, invalid tokens, tenant leakage).
  3. Frontend Unit Tests (testing components, form diffing, and error boundaries with Vitest).
  4. End-to-End Integration Flow: Automated upload $\to$ pipeline $\to$ review $\to$ export workflow test.
- **Exit Criteria**: All automated test suites pass with zero failures.

---

### Phase 10: Production Deployment
- **Objective**: Containerized, reproducible production deployment.
- **Tasks**:
  1. Docker Compose Optimization: Multi-stage builds, non-root users, volume persistence.
  2. GitHub Actions CI/CD: Automated workflow on push/PR running linting, backend tests, and frontend build.
  3. Production Environment Checklist: Database connection pool configuration, CORS lockdown.
- **Exit Criteria**: `docker-compose up --build` launches from a clean clone with healthy status checks.

---

### Phase 11: Professional Documentation
- **Objective**: Provide comprehensive engineering documentation for recruiters and technical interviewers.
- **Tasks**:
  - `docs/ARCHITECTURE.md`: High-level system design, data flow, component decoupling.
  - `docs/ML_METHODOLOGY.md`: Feature engineering, model selection, calibration, anomaly detection math.
  - `docs/DATASET_DOCUMENTATION.md`: Synthetic generation, Indian GSTIN specs, leakage prevention.
  - `docs/MODEL_EVALUATION.md`: Honest evaluation benchmarks, metrics, confusion matrix, limitations.
  - `docs/API_DOCUMENTATION.md`: Full OpenAPI/REST endpoint contract.
  - `docs/SECURITY.md`: Authentication, RBAC, tenant isolation, file security.
  - `docs/TESTING.md`: Test strategy, coverage report, running tests.
  - `docs/DEPLOYMENT.md`: Docker, PostgreSQL, environment variables, production deployment.
  - `docs/INTERVIEW_PREPARATION.md`: 25 anticipated technical interview questions and deep-dive answers.
- **Exit Criteria**: Documentation is complete, accurate, and reflects the exact working codebase.

---

### Phase 12: GitHub Quality & Portfolio Polish
- **Objective**: Transform repository into a distinctive open-source portfolio showcase.
- **Tasks**:
  1. Professional `README.md` with badges, architecture diagrams, screenshots, and quickstart.
  2. Issue templates and Pull Request template (`.github/`).
  3. Clean repository hygiene: verify `.gitignore` excludes temporary, build, and private artifacts.
- **Exit Criteria**: Repository is clean, polished, and ready for recruitment review.

