from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import DatabaseSession
from api.routes.artifacts import resolve_artifact_path
from api.schemas.redaction import RedactionResponse
from database.models import Redaction

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
) -> List[RedactionResponse]:
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

    artifact_path = resolve_artifact_path(
        redaction.redacted_file_path,
        "storage/redacted",
    )
    return FileResponse(
        path=artifact_path,
        media_type="text/plain",
        filename=artifact_path.name,
    )