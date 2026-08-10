from typing import List

from fastapi import APIRouter, HTTPException, status

from api.dependencies import DatabaseSession
from api.schemas.document_status import DocumentStatusResponse
from api.schemas.entity import EntityResponse
from api.schemas.extracted_text import ExtractedTextResponse
from database.models import Document, Entity
from modules.extraction.service import (
    DocumentNotFoundError,
    ExtractedTextNotFoundError,
    ExtractionService,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


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
        created_at=entity.created_at,
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
) -> DocumentStatusResponse:
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
    db: DatabaseSession = None,
) -> List[EntityResponse]:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    entities = (
        db.query(Entity)
        .filter(Entity.document_id == document_id)
        .all()
    )
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
) -> ExtractedTextResponse:
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
