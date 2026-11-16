# Invoice IQ
### Extract. Validate. Understand.
**Intelligent Invoice Processing, Extraction & Verification Platform**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.2-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Scikit--Learn](https://img.shields.io/badge/Scikit--Learn-1.4+-F7931E.svg?logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Invoice IQ is an intelligent document processing (IDP) and financial audit platform engineered to ingest, extract, validate, and analyze commercial invoices and receipts. Built as a self-contained AI/ML application, it delivers high-precision field extraction, calibrated confidence scoring, rule-based business validation, and unsupervised anomaly detection without relying on costly third-party LLM APIs.

---

## Key Capabilities

1. **Multi-Format Ingestion & Security**: Validates file magic-bytes and securely parses multi-page PDFs, PNGs, and JPGs with stream-level size gating and strict filename sanitization.
2. **Computer Vision & Image Preprocessing**: Deskews tilted scans ($\pm 45^\circ$) via Hough line transforms and applies CLAHE contrast enhancement for crisp character definition.
3. **High-Accuracy OCR**: Extracts word/line-level text tokens with normalized geometric bounding boxes $[0.0, 1.0]$.
4. **Hybrid Field Extraction Engine**:
   - **Rule-Based Engine**: Deterministic regex extractors for Indian GSTINs, dates, invoice numbers, and financial amounts based on spatial anchors.
   - **Machine Learning Engine**: TF-IDF vectorizer + Logistic Regression token classifier trained on lexical, contextual, and spatial features.
   - **Candidate Aggregation & Agreement Boost**: Combines Rule and ML candidates, boosting confidence when both agree.
5. **Multi-Factor Business Validation Engine**:
   - Indian GSTIN format and state code verification (01–38).
   - Date validity and temporal bounds check (rejects far-future dates).
   - Non-negative amounts constraint (Total $\ge$ Subtotal).
   - Mathematical consistency: $|\text{Subtotal} + \text{Tax} - \text{Total}| \le 0.05$.
   - Database cross-checks preventing duplicate invoice billing.
6. **Unsupervised Anomaly Detection**:
   - Scikit-learn **Isolation Forest** scoring financial transaction feature vectors.
   - Historical vendor transaction Z-score tracking to detect billing spikes.
   - Transparent, human-interpretable anomaly explanations.
7. **Calibrated Multi-Factor Confidence Scoring**:
   - Separates OCR character recognition confidence from field extraction confidence.
   - Calibrated formula: $0.50 \cdot c_{\text{ext}} + 0.30 \cdot c_{\text{ocr}} + 0.20 \cdot \mathbb{I}_{\text{valid}}$.
   - Strict gating: Missing critical fields (Invoice Number, Total Amount) forces human review regardless of average score.
8. **Human-in-the-Loop (HITL) Review Center**:
   - Split-screen interface: Interactive document canvas with hover-highlighted bounding boxes on the left; editable form, validation alerts, and Approve/Reject controls on the right.
   - Full audit trail capturing original extraction values alongside reviewer corrections.
9. **Executive Analytics & One-Click Exports**:
   - Real-time KPI dashboard and 7-day throughput activity charts.
   - One-click export of verified invoice records to **CSV** and **JSON**.

---

## Technology Stack

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons, Recharts, Axios, React Router.
- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0, Uvicorn.
- **Database**: Dual configuration (zero-config SQLite for local dev, PostgreSQL for production).
- **Computer Vision & OCR**: PyMuPDF (fitz), OpenCV, PaddleOCR.
- **Machine Learning**: Scikit-learn (Logistic Regression, TF-IDF Vectorizer, Isolation Forest), NumPy, Pandas, Joblib.
- **DevOps**: Docker, Docker Compose, Nginx.

---

## System Architecture

```
User Document ──► FastAPI Ingest ──► Async Pipeline Queue
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  ▼                                        ▼                                        ▼
PyMuPDF Rendering                  OpenCV Preprocessing                    PaddleOCR Tokens
(300 DPI Images)                  (Deskew & Contrast)                    (Normalized BBoxes)
  │                                        │                                        │
  └────────────────────────────────────────┼────────────────────────────────────────┘
                                           ▼
                           Hybrid Field Extraction Engine
                           ├── Rule-Based Anchor Engine
                           └── ML Token Classifier (TF-IDF + LogReg)
                                           ▼
                           Candidate Disambiguation & Boost
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  ▼                                        ▼                                        ▼
Validation Engine                   Isolation Forest                      Confidence Scoring
(GSTIN, Math, Duplicates)           (Financial Anomalies)                (Field & Document)
  │                                        │                                        │
  └────────────────────────────────────────┼────────────────────────────────────────┘
                                           ▼
                               Status Routing Decision
                               ├── Confidence >= 80% & Valid ──► PROCESSED
                               └── Uncertain / Anomaly / Error ──► NEEDS_REVIEW
                                                                      │
                                                           Human Review Center
                                                           (Interactive Canvas)
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ (with npm)

### 2. Backend Setup
```bash
# Clone and enter directory
cd "Invoice IQ"

# Copy environment variables
cp .env.example .env

# Install backend dependencies
pip install -r backend/requirements.txt

# Run database table initialization and startup
python -s -m uvicorn backend.app.main:app --reload --port 8000
```
FastAPI interactive documentation is available at: `http://localhost:8000/docs`.

### 3. ML Model Training & Benchmarking
```bash
# Train the TF-IDF + Logistic Regression field classifier
python -s -m ml.src.train_classifier

# Train the Isolation Forest anomaly detector
python -s -m ml.src.train_anomaly
```
Artifacts are automatically saved to `ml/artifacts/`.

### 4. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Running Automated Tests

Run the complete test suite:

```bash
python -s -m pytest backend/tests/
```

Test breakdown:
- `backend/tests/test_database.py`: Schema creation, cascades, ORM relationships.
- `backend/tests/test_main.py`: App factory, lifespan, health checks, Invoice IQ metadata.
- `backend/tests/test_preprocessing_ocr.py`: Magic bytes, PDF rasterization, OpenCV, OCR tokens.
- `backend/tests/test_extraction.py`: Synthetic generator, features, hybrid extraction, agreement boost.
- `backend/tests/test_validation_anomaly.py`: GSTIN, dates, math, duplicate checks, Isolation Forest, routing.
- `backend/tests/test_api.py`: Upload, pipeline, preview, review, analytics, export, settings.

---

## Docker Deployment

To launch the full production stack (FastAPI Backend, PostgreSQL, and React Nginx Frontend) with one command:

```bash
docker-compose up --build
```
- Frontend UI: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

---

## License
MIT License. Built for enterprise document automation and portfolio demonstration.
