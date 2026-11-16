import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import SessionLocal
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.validation_result import ValidationResult
from backend.app.models.anomaly_result import AnomalyResult
from backend.app.utils.pdf_tools import convert_pdf_to_images, get_pdf_page_count
from backend.app.services.preprocessing_service import preprocessing_service
from backend.app.services.ocr_service import ocr_service
from backend.app.services.extraction_service import extraction_service
from backend.app.services.validation_service import validation_service
from backend.app.services.anomaly_service import anomaly_service
from backend.app.services.confidence_service import confidence_service


class PipelineStage:
    INITIALIZE = "INITIALIZE"
    RENDER = "PAGE_RENDER"
    PREPROCESS = "CV_PREPROCESSING"
    OCR = "OCR_EXTRACTION"
    FIELD_EXTRACTION = "HYBRID_FIELD_EXTRACTION"
    VALIDATION = "INTEGRITY_VALIDATION"
    ANOMALY = "ANOMALY_DETECTION"
    CONFIDENCE_ROUTING = "CONFIDENCE_ROUTING"
    PERSISTENCE = "DATABASE_PERSISTENCE"


class PipelineService:
    """
    Modular, Observable End-to-End Orchestrator for Invoice Processing:
    - Stage-level execution timing & profiling
    - Precise stage-level fault isolation and graceful error routing
    - Hybrid field extraction combining deterministic anchors & ML classifiers
    - Multi-factor business rule validation & unsupervised anomaly detection
    - Automated confidence scoring and Human Review Center routing
    """

    def process_document(self, document_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Executes the synchronous document processing pipeline for a given document ID.
        Records step-level latency metrics and handles transactional rollback upon failure.
        """
        session_created = False
        if db is None:
            db = SessionLocal()
            session_created = True

        current_stage = PipelineStage.INITIALIZE
        stage_timings_ms: Dict[str, float] = {}
        t_start_total = time.perf_counter()

        try:
            # Stage 0: Initialization
            t0 = time.perf_counter()
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error(f"[Pipeline] Document {document_id} not found in database.")
                return {"success": False, "error": f"Document {document_id} not found"}

            logger.info(f"[Pipeline] Starting processing for Document {document_id} ({doc.original_filename})...")
            doc.processing_status = "PROCESSING"
            doc.error_message = None
            db.commit()

            file_path = Path(doc.storage_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Stored document file not found on disk: {file_path}")

            is_pdf = doc.file_type.lower() == "pdf"
            stage_timings_ms[PipelineStage.INITIALIZE] = round((time.perf_counter() - t0) * 1000, 2)

            # Stage 1: Page Rendering & Computer Vision Preprocessing
            current_stage = PipelineStage.RENDER
            t0 = time.perf_counter()
            rendered_pages = self._render_and_preprocess(doc, file_path, is_pdf)
            stage_timings_ms[PipelineStage.RENDER] = round((time.perf_counter() - t0) * 1000, 2)

            # Stage 2: OCR Token & Geometric Extraction
            current_stage = PipelineStage.OCR
            t0 = time.perf_counter()
            logger.info(f"[Pipeline:OCR] Extracting tokens for Document {document_id} ({len(rendered_pages)} pages)...")
            ocr_result = ocr_service.process_document(
                document_id=document_id,
                file_path=file_path,
                rendered_pages=rendered_pages
            )
            stage_timings_ms[PipelineStage.OCR] = round((time.perf_counter() - t0) * 1000, 2)

            # Stage 3: Hybrid Field Extraction (Rules + ML Classifier)
            current_stage = PipelineStage.FIELD_EXTRACTION
            t0 = time.perf_counter()
            logger.info(f"[Pipeline:Extraction] Running hybrid anchor & ML extraction for Document {document_id}...")
            extracted_fields = extraction_service.extract_fields(ocr_result)
            stage_timings_ms[PipelineStage.FIELD_EXTRACTION] = round((time.perf_counter() - t0) * 1000, 2)

            # Stage 4: Multi-Factor Business Validation Engine
            current_stage = PipelineStage.VALIDATION
            t0 = time.perf_counter()
            logger.info(f"[Pipeline:Validation] Executing business and mathematical rules for Document {document_id}...")
            validations = validation_service.validate_document(
                extracted_fields=extracted_fields,
                db=db,
                current_document_id=document_id
            )
            stage_timings_ms[PipelineStage.VALIDATION] = round((time.perf_counter() - t0) * 1000, 2)

            # Stage 5: Unsupervised Financial Anomaly Detection
            current_stage = PipelineStage.ANOMALY
            t0 = time.perf_counter()
            logger.info(f"[Pipeline:Anomaly] Evaluating Isolation Forest transaction score for Document {document_id}...")
            anomaly = anomaly_service.analyze_document(
                extracted_fields=extracted_fields,
                db=db,
                current_document_id=document_id
            )
            stage_timings_ms[PipelineStage.ANOMALY] = round((time.perf_counter() - t0) * 1000, 2)

            # Stage 6: Confidence Scoring & Human Review Routing
            current_stage = PipelineStage.CONFIDENCE_ROUTING
            t0 = time.perf_counter()
            overall_confidence, routing_status, reasons = confidence_service.evaluate_document_confidence(
                extracted_fields=extracted_fields,
                validations=validations,
                anomaly=anomaly
            )
            stage_timings_ms[PipelineStage.CONFIDENCE_ROUTING] = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(f"[Pipeline:Routing] Document {document_id} routed to '{routing_status}' (Confidence: {overall_confidence:.2f})")

            # Stage 7: Database Persistence & Atomic Commit
            current_stage = PipelineStage.PERSISTENCE
            t0 = time.perf_counter()
            self._persist_results(
                db=db,
                doc=doc,
                extracted_fields=extracted_fields,
                validations=validations,
                anomaly=anomaly,
                routing_status=routing_status,
                overall_confidence=overall_confidence,
                reasons=reasons
            )
            stage_timings_ms[PipelineStage.PERSISTENCE] = round((time.perf_counter() - t0) * 1000, 2)

            total_duration_ms = round((time.perf_counter() - t_start_total) * 1000, 2)
            stage_timings_ms["TOTAL_PIPELINE_MS"] = total_duration_ms

            logger.info(f"[Pipeline] Completed processing for Document {document_id} in {total_duration_ms}ms")

            return {
                "success": True,
                "document_id": document_id,
                "status": routing_status,
                "confidence": overall_confidence,
                "fields_extracted": len(extracted_fields),
                "validations_count": len(validations),
                "is_anomalous": anomaly.is_anomalous,
                "stage_timings_ms": stage_timings_ms
            }

        except Exception as e:
            error_msg = f"[Stage: {current_stage}] {str(e)}"
            logger.exception(f"[Pipeline] Processing failed for Document {document_id}: {error_msg}")
            if db:
                db.rollback()
                try:
                    doc = db.query(Document).filter(Document.id == document_id).first()
                    if doc:
                        doc.processing_status = "FAILED"
                        doc.error_message = error_msg
                        db.commit()
                except Exception as rollback_err:
                    logger.error(f"[Pipeline] Failed to record error state for {document_id}: {rollback_err}")
            return {
                "success": False,
                "document_id": document_id,
                "failed_stage": current_stage,
                "error": error_msg,
                "stage_timings_ms": stage_timings_ms
            }

        finally:
            if session_created:
                db.close()

    def _render_and_preprocess(self, doc: Document, file_path: Path, is_pdf: bool) -> List[Dict[str, Any]]:
        """Handles PDF page rasterization and computer vision preprocessing (deskewing, contrast)."""
        rendered_pages: List[Dict[str, Any]] = []

        if is_pdf:
            doc.page_count = get_pdf_page_count(file_path)
            page_out_dir = settings.PROCESSED_PAGES_DIR / doc.id
            raw_rendered = convert_pdf_to_images(
                pdf_path=file_path,
                output_dir=page_out_dir,
                dpi=200,
                prefix=f"doc_{doc.id}"
            )
            for p in raw_rendered:
                prep = preprocessing_service.preprocess_image(
                    image_path=p["image_path"],
                    apply_deskew=True,
                    apply_enhancement=True
                )
                rendered_pages.append({
                    "page_number": p["page_number"],
                    "image_path": prep["preprocessed_path"],
                    "width": prep["width"] or p["width"],
                    "height": prep["height"] or p["height"]
                })
        else:
            prep = preprocessing_service.preprocess_image(
                image_path=file_path,
                apply_deskew=True,
                apply_enhancement=True
            )
            rendered_pages.append({
                "page_number": 1,
                "image_path": prep["preprocessed_path"],
                "width": prep["width"],
                "height": prep["height"]
            })
            doc.page_count = 1

        return rendered_pages

    def _persist_results(
        self,
        db: Session,
        doc: Document,
        extracted_fields: List[Any],
        validations: List[Any],
        anomaly: Any,
        routing_status: str,
        overall_confidence: float,
        reasons: List[str]
    ) -> None:
        """Atomically persists extracted fields, validation results, and anomaly flags."""
        document_id = doc.id

        # Clean existing records if reprocessing
        db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()
        db.query(ValidationResult).filter(ValidationResult.document_id == document_id).delete()
        db.query(AnomalyResult).filter(AnomalyResult.document_id == document_id).delete()

        # Insert extracted fields
        for f in extracted_fields:
            db_field = ExtractedField(
                document_id=document_id,
                field_name=f.field_name,
                extracted_value=f.extracted_value,
                original_value=None,
                confidence_score=f.confidence_score,
                ocr_confidence=f.ocr_confidence,
                extraction_method=f.extraction_method,
                page_number=f.page_number,
                bounding_box=f.bounding_box,
                is_corrected=False
            )
            db.add(db_field)

        # Insert validation records
        for v in validations:
            db_val = ValidationResult(
                document_id=document_id,
                rule_name=v.rule_name,
                status=v.status,
                message=v.message,
                details=v.details
            )
            db.add(db_val)

        # Insert anomaly record
        db_anomaly = AnomalyResult(
            document_id=document_id,
            anomaly_score=anomaly.anomaly_score,
            is_anomalous=anomaly.is_anomalous,
            feature_vector=anomaly.feature_vector,
            explanation=anomaly.explanation
        )
        db.add(db_anomaly)

        # Update document record
        doc.processing_status = routing_status
        doc.overall_confidence = overall_confidence
        doc.error_message = "; ".join(reasons) if reasons else None
        db.commit()


pipeline_service = PipelineService()
