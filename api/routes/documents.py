from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_

from api.dependencies import (
    DatabaseSession,
    is_document_accessible,
    require_roles,
    require_document_access,
)
from api.schemas.document_status import DocumentStatusResponse
from api.schemas.entity import EntityResponse
from api.schemas.extracted_text import ExtractedTextResponse
from api.schemas.run import RunResponse, RunProgress
from database.models import Document, Entity, Run, User
from database.repositories.run_repository import RunRepository
from modules.extraction.service import (
    DocumentNotFoundError,
    ExtractedTextNotFoundError,
    ExtractionService,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def _get_document_or_404(db, document_id: str) -> Document:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
    return document


def _serialize_entity(entity: Entity) -> EntityResponse:

    return EntityResponse(
        entity_id=entity.id,
        document_id=entity.document_id,
        ocr_result_id=entity.ocr_result_id,
        entity_type=entity.entity_type,
        entity_value=entity.entity_value,
        privacy_category=entity.privacy_category,
        confidence_score=entity.confidence_score,
        final_confidence=entity.final_confidence,
        detector=entity.detector,
        page_number=entity.page_number,
        start_char=entity.start_char,
        end_char=entity.end_char,
        is_review_required=bool(entity.is_review_required),
        is_redacted=bool(entity.is_redacted),
        ai_decision=getattr(entity, "ai_decision", None),
        ai_reasoning=getattr(entity, "ai_reasoning", None),
        is_accepted_by_ai=getattr(entity, "is_accepted_by_ai", True),
        created_at=entity.created_at,
    )


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Progress",
    description="Return Run information and document-level progress.",
)
def get_run_progress(
    run_id: str,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("USER", "REVIEWER", "ADMIN")),
) -> RunResponse:
    run_repo = RunRepository(db)
    run = run_repo.get_by_run_id(run_id)
    
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    documents = db.query(Document).filter(Document.run_id == run.id).all()

    if current_user.role == "USER":
        documents = [
            doc
            for doc in documents
            if is_document_accessible(db, current_user, doc)
        ]

    return RunResponse(
        run_id=run.run_id,
        status=run.status,
        total_files=run.total_files,
        completed_files=run.completed_files,
        failed_files=run.failed_files,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        documents=[
            RunProgress(
                document_id=doc.id,
                filename=doc.filename,
                status=doc.status,
                document_type=doc.document_type,
            )
            for doc in documents
        ],
    )


@router.get(
    "/{document_id}/status",

    response_model=DocumentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Document Processing Status",
    description="Return document processing state and OCR availability.",
)
def get_document_status(
    document_id: str,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("USER", "REVIEWER", "ADMIN")),
) -> DocumentStatusResponse:
    document = _get_document_or_404(db, document_id)
    require_document_access(db, current_user, document)

    extraction_service = ExtractionService(db)

    try:
        return extraction_service.get_processing_status(document_id)

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{document_id}/entities",
    response_model=List[EntityResponse],
    status_code=status.HTTP_200_OK,
    summary="List Document Entities",
    description="Return all detected entities for a document with keys and values.",
)
def list_document_entities(
    document_id: str,
    include_rejected: bool = False,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("REVIEWER", "ADMIN")),
) -> List[EntityResponse]:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    require_document_access(db, current_user, document)

    query = db.query(Entity).filter(Entity.document_id == document_id)
    if not include_rejected:
        query = query.filter(
            or_(
                Entity.is_accepted_by_ai.is_(True),
                Entity.is_accepted_by_ai.is_(None),
            ),
            or_(
                Entity.processing_stage.is_(None),
                Entity.processing_stage != "REJECTED_BY_AI",
            ),
        )
    entities = query.all()
    entities.sort(
        key=lambda entity: (
            int(entity.page_number)
            if str(entity.page_number or "").isdigit()
            else 10**9,
            entity.start_char if entity.start_char is not None else 10**9,
            entity.end_char if entity.end_char is not None else 10**9,
            entity.created_at,
        )
    )
    return [_serialize_entity(entity) for entity in entities]


@router.get(
    "/{document_id}/text",
    response_model=ExtractedTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Extracted Document Text",
    description="Return the latest extracted text and OCR metadata.",
)
def get_extracted_text(
    document_id: str,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("USER", "REVIEWER", "ADMIN")),
) -> ExtractedTextResponse:
    document = _get_document_or_404(db, document_id)
    require_document_access(db, current_user, document)

    extraction_service = ExtractionService(db)

    try:
        return extraction_service.get_extracted_text(document_id)

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ExtractedTextNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
