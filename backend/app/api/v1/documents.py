import os
import re
import shutil
import uuid
import csv
import io
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import get_db
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.validation_result import ValidationResult
from backend.app.models.anomaly_result import AnomalyResult
from backend.app.schemas.document import (
    DocumentResponse,
    DocumentListItem,
    DocumentListResponse
)
from backend.app.utils.pdf_tools import validate_document_file
from backend.app.services.pipeline_service import pipeline_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=List[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts one or more invoice files (PDF, PNG, JPG), validates signatures and size limits,
    stores files securely, creates database records with status 'PENDING',
    and initiates asynchronous background processing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    created_docs = []
    max_upload_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    for upload_file in files:
        raw_filename = upload_file.filename or "uploaded_document"
        # Sanitize against path traversal and null bytes (SEC-02/SEC-03)
        safe_original_name = Path(raw_filename).name.replace("\x00", "").strip() or "uploaded_document"
        clean_stem = re.sub(r'[^a-zA-Z0-9_.-]', '_', safe_original_name)
        ext = safe_original_name.split(".")[-1].lower() if "." in safe_original_name else ""

        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '{ext}'. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )

        # Generate unique storage filename and verify directory containment
        doc_id = str(uuid.uuid4())
        stored_filename = f"{doc_id}_{clean_stem}"
        storage_path = (settings.UPLOAD_DIR / stored_filename).resolve()

        if not str(storage_path).startswith(str(settings.UPLOAD_DIR.resolve())):
            raise HTTPException(status_code=400, detail="Invalid file destination path.")

        # Stream uploaded file in chunks with strict size enforcement
        bytes_written = 0
        try:
            with open(storage_path, "wb") as buffer:
                while True:
                    chunk = upload_file.file.read(1024 * 1024)  # 1MB chunk
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_upload_bytes:
                        buffer.close()
                        storage_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail=f"File '{safe_original_name}' exceeds maximum allowable upload size of {settings.MAX_UPLOAD_SIZE_MB} MB."
                        )
                    buffer.write(chunk)
        except HTTPException:
            raise
        except Exception as e:
            storage_path.unlink(missing_ok=True)
            logger.error(f"Failed to save upload {safe_original_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file {safe_original_name}")
        finally:
            upload_file.file.close()

        # Validate file size and magic-byte signature
        val_info = validate_document_file(
            file_path=storage_path,
            max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
            allowed_types=settings.ALLOWED_EXTENSIONS
        )
        if not val_info["valid"]:
            # Delete invalid file
            storage_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=val_info["error"])

        # Create Document record
        doc = Document(
            id=doc_id,
            original_filename=safe_original_name,
            storage_path=str(storage_path.resolve()),
            file_type=val_info["file_type"],
            file_size_bytes=val_info["size_bytes"],
            page_count=val_info["page_count"],
            processing_status="PENDING"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        created_docs.append(doc)

        # Queue asynchronous background pipeline execution
        background_tasks.add_task(pipeline_service.process_document, doc_id)

    return created_docs


@router.get("", response_model=DocumentListResponse)
def list_documents(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (e.g., PROCESSED, NEEDS_REVIEW, FAILED)"),
    search: Optional[str] = Query(None, description="Search by filename or extracted fields"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Returns a paginated list of uploaded documents with summary fields for table display.
    Supports status filtering and search.
    """
    query = db.query(Document)

    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Document.processing_status == status_filter.upper())

    if search:
        search_pattern = f"%{search.strip()}%"
        # Match filename or search through extracted field values
        subquery = db.query(ExtractedField.document_id).filter(
            ExtractedField.extracted_value.ilike(search_pattern)
        ).scalar_subquery()
        query = query.filter(
            or_(
                Document.original_filename.ilike(search_pattern),
                Document.id.in_(subquery)
            )
        )

    total = query.count()
    pages_count = (total + limit - 1) // limit if total > 0 else 1

    docs = (
        query.order_by(desc(Document.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items: List[DocumentListItem] = []
    for doc in docs:
        field_map = {f.field_name: f.extracted_value for f in doc.extracted_fields}
        is_anom = doc.anomaly_result.is_anomalous if doc.anomaly_result else None

        items.append(DocumentListItem(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            page_count=doc.page_count,
            processing_status=doc.processing_status,
            overall_confidence=doc.overall_confidence,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            vendor_name=field_map.get("vendor_name"),
            invoice_number=field_map.get("invoice_number"),
            invoice_date=field_map.get("invoice_date"),
            total_amount=field_map.get("total_amount"),
            is_anomalous=is_anom
        ))

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages_count
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Returns complete details of a single document including extracted fields and validation outcomes."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")
    return doc


@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Triggers or forces reprocessing of an existing document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    doc.processing_status = "PENDING"
    doc.error_message = None
    db.commit()

    background_tasks.add_task(pipeline_service.process_document, document_id)
    return {"message": "Reprocessing triggered successfully", "document_id": document_id, "status": "PENDING"}


@router.get("/{document_id}/preview/{page_number}")
def get_document_page_preview(
    document_id: str,
    page_number: int = 1,
    db: Session = Depends(get_db)
):
    """
    Returns the rendered PNG image stream for a given page, enabling the
    frontend split-screen Review Center and Document Viewer.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    # 1. Look in processed pages directory
    page_img_path = settings.PROCESSED_PAGES_DIR / document_id / f"doc_{document_id}_{page_number}.png"
    if not page_img_path.exists():
        # Fallback to direct file if single image
        if doc.file_type.lower() in ["png", "jpg", "jpeg"]:
            page_img_path = Path(doc.storage_path)

    if not page_img_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Rendered image for document {document_id} page {page_number} is not ready or not found."
        )

    return FileResponse(
        str(page_img_path),
        media_type="image/png",
        filename=f"page_{page_number}.png"
    )


@router.get("/export/download")
def export_documents(
    format: str = Query("csv", pattern="^(csv|json)$"),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    """
    Exports extracted invoice information as a downloadable CSV or JSON file.
    """
    query = db.query(Document)
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Document.processing_status == status_filter.upper())

    docs = query.order_by(desc(Document.created_at)).all()

    records = []
    for doc in docs:
        f_map = {f.field_name: f.extracted_value for f in doc.extracted_fields}
        records.append({
            "Document ID": doc.id,
            "Original Filename": doc.original_filename,
            "Status": doc.processing_status,
            "Confidence": doc.overall_confidence or 0.0,
            "Vendor Name": f_map.get("vendor_name", ""),
            "Invoice Number": f_map.get("invoice_number", ""),
            "Invoice Date": f_map.get("invoice_date", ""),
            "GSTIN": f_map.get("gstin", ""),
            "Subtotal": f_map.get("subtotal", ""),
            "Tax Amount": f_map.get("tax_amount", ""),
            "Total Amount": f_map.get("total_amount", ""),
            "Uploaded At": doc.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    if format == "json":
        json_content = json.dumps(records, indent=2)
        return StreamingResponse(
            io.StringIO(json_content),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="invoice_iq_export.json"'}
        )
    else:
        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
        else:
            output.write("No documents found for export.\n")

        output.seek(0)
        return StreamingResponse(
            io.StringIO(output.getvalue()),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="invoice_iq_export.csv"'}
        )
