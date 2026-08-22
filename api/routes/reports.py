import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import (
    DatabaseSession,
    require_document_access,
    require_roles,
)
from api.routes.artifacts import resolve_artifact_path
from api.schemas.report import ReportDetailResponse, ReportResponse
from database.models import Document, Report, User
from database.repositories.report_repository import (
    empty_llm_candidate_audit,
    extract_llm_candidate_audit,
    load_llm_candidate_audit,
    normalize_llm_candidate_audit,
)
from modules.upload.storage import StorageService

router = APIRouter(tags=["Reports"])


def _serialize_report(
    report: Report,
    payload: Optional[Dict[str, Any]] = None,
) -> ReportDetailResponse:
    audit = (
        normalize_llm_candidate_audit(report.llm_candidate_audit)
        if report.llm_candidate_audit is not None
        else None
    )
    return ReportDetailResponse(
        report_id=report.id,
        document_id=report.document_id,
        report_type=report.report_type,
        total_entities=report.total_entities or 0,
        total_redactions=report.total_redactions or 0,
        report_path=report.report_path,
        generated_by=report.generated_by,
        processing_duration_ms=report.processing_duration_ms,
        detectors_used=report.detectors_used,
        gemma_invoked=bool(report.gemma_invoked),
        total_pii=report.total_pii or 0,
        total_phi=report.total_phi or 0,
        review_completion=bool(report.review_completion),
        redaction_completion=bool(report.redaction_completion),
        llm_candidate_audit=audit,
        llm_candidate_accepted_count=len(audit["accepted"]) if audit else 0,
        llm_candidate_rejected_count=len(audit["rejected"]) if audit else 0,
        created_at=report.created_at,
        payload=payload,
    )


def _load_report_payload(report: Report) -> Optional[Dict[str, Any]]:
    if not report.report_path:
        return None

    artifact_path = resolve_artifact_path(
        report.report_path,
        str(StorageService.STORAGE_DIR),
    )
    try:
        return json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report artifact is not valid JSON: {exc}",
        ) from exc


def _persist_report_audit(
    db,
    report: Report,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    if report.llm_candidate_audit is not None:
        return normalize_llm_candidate_audit(report.llm_candidate_audit)

    audit = (
        extract_llm_candidate_audit(payload, report.document_id)
        if payload is not None
        else load_llm_candidate_audit(report)
    )
    if audit is None:
        return None

    report.llm_candidate_audit = audit
    db.add(report)
    db.commit()
    return audit


@router.get(
    "/documents/{document_id}/reports",
    response_model=List[ReportResponse],
    status_code=status.HTTP_200_OK,
    summary="List Document Reports",
)
def list_document_reports(
    document_id: str,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("USER", "REVIEWER", "ADMIN")),
) -> List[ReportResponse]:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    require_document_access(db, current_user, document)

    reports = (
        db.query(Report)
        .filter(Report.document_id == document_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    for report in reports:
        _persist_report_audit(db, report)
    return [_serialize_report(report) for report in reports]


@router.get(
    "/reports/{report_id}",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Report Metadata And Payload",
)
def get_report(
    report_id: str,
    include_payload: bool = True,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("USER", "REVIEWER", "ADMIN")),
) -> ReportDetailResponse:
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    document = db.query(Document).filter(Document.id == report.document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {report.document_id}",
        )

    require_document_access(db, current_user, document)

    payload = _load_report_payload(report) if include_payload else None
    audit = _persist_report_audit(db, report, payload=payload)
    if payload is not None:
        payload["llm_candidate_audit"] = (
            audit if audit is not None else empty_llm_candidate_audit()
        )
    return _serialize_report(report, payload=payload)


@router.get(
    "/reports/{report_id}/file",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Download Report Artifact",
)
def download_report_file(
    report_id: str,
    db: DatabaseSession = None,
    current_user: User = Depends(require_roles("USER", "REVIEWER", "ADMIN")),
) -> FileResponse:
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    document = db.query(Document).filter(Document.id == report.document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {report.document_id}",
        )

    require_document_access(db, current_user, document)

    artifact_path = resolve_artifact_path(
        report.report_path,
        str(StorageService.STORAGE_DIR),
    )
    return FileResponse(
        path=artifact_path,
        media_type="application/json",
        filename=artifact_path.name,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
