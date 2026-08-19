from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import (
    DatabaseSession,
    require_document_access,
    require_roles,
)
from api.routes.artifacts import resolve_artifact_path
from api.schemas.redaction import RedactionResponse
from database.models import Document, Redaction, User
from modules.upload.storage import StorageService

router = APIRouter(tags=["Redactions"])


def _serialize_redaction(redaction: Redaction) -> RedactionResponse:
    return RedactionResponse(
        redaction_id=redaction.id,
        document_id=redaction.document_id,
        redaction_type=redaction.redaction_type,
        redacted_file_path=redaction.redacted_file_path,
        redaction_summary=redaction.redaction_summary,
        processed_by=redaction.processed_by,
        created_at=redaction.created_at,
    )


@router.get(
    "/documents/{document_id}/redactions",
    response_model=List[RedactionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Document Redactions",
)
def list_document_redactions(
    document_id: str,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("USER", "REVIEWER", "ADMIN")),
) -> List[RedactionResponse]:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    require_document_access(db, current_user, document)

    redactions = (
        db.query(Redaction)
        .filter(Redaction.document_id == document_id)
        .order_by(Redaction.created_at.desc())
        .all()
    )
    return [_serialize_redaction(redaction) for redaction in redactions]


@router.get(
    "/redactions/{redaction_id}/file",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Download Redacted Text Artifact",
)
def download_redacted_file(
    redaction_id: str,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("USER", "REVIEWER", "ADMIN")),
) -> FileResponse:
    redaction = (
        db.query(Redaction)
        .filter(Redaction.id == redaction_id)
        .first()
    )
    if redaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Redaction not found: {redaction_id}",
        )

    document = db.query(Document).filter(Document.id == redaction.document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {redaction.document_id}",
        )

    require_document_access(db, current_user, document)

    artifact_path = resolve_artifact_path(
        redaction.redacted_file_path,
        str(StorageService.STORAGE_DIR),
    )
    return FileResponse(
        path=artifact_path,
        media_type="text/plain",
        filename=artifact_path.name,
    )