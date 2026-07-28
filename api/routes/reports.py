import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import DatabaseSession
from api.routes.artifacts import resolve_artifact_path
from api.schemas.report import ReportDetailResponse, ReportResponse
from database.models import Report

router = APIRouter(tags=["Reports"])


def _serialize_report(
    report: Report,
    payload: Optional[Dict[str, Any]] = None,
) -> ReportDetailResponse:
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
        qwen_invoked=bool(report.qwen_invoked),
        total_pii=report.total_pii or 0,
        total_phi=report.total_phi or 0,
        review_completion=bool(report.review_completion),
        redaction_completion=bool(report.redaction_completion),
        created_at=report.created_at,
        payload=payload,
    )


def _load_report_payload(report: Report) -> Optional[Dict[str, Any]]:
    if not report.report_path:
        return None

    artifact_path = resolve_artifact_path(
        report.report_path,
        "storage/reports",
    )
    try:
        return json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report artifact is not valid JSON: {exc}",
        ) from exc


@router.get(
    "/documents/{document_id}/reports",
    response_model=List[ReportResponse],
    status_code=status.HTTP_200_OK,
    summary="List Document Reports",
)
def list_document_reports(
    document_id: str,
    db: DatabaseSession = None,
) -> List[ReportResponse]:
    reports = (
        db.query(Report)
        .filter(Report.document_id == document_id)
        .order_by(Report.created_at.desc())
        .all()
    )
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
) -> ReportDetailResponse:
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    payload = _load_report_payload(report) if include_payload else None
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
) -> FileResponse:
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    artifact_path = resolve_artifact_path(
        report.report_path,
        "storage/reports",
    )
    return FileResponse(
        path=artifact_path,
        media_type="application/json",
        filename=artifact_path.name,
    )