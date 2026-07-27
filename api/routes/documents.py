from fastapi import APIRouter, HTTPException, status

from api.dependencies import DatabaseSession
from api.schemas.document_status import DocumentStatusResponse
from api.schemas.extracted_text import ExtractedTextResponse
from modules.extraction.service import (
    DocumentNotFoundError,
    ExtractedTextNotFoundError,
    ExtractionService,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
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
