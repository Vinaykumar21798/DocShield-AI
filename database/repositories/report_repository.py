import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.report import Report
from database.repositories.base_repository import BaseRepository


class ReportRepository(BaseRepository[Report]):
    def __init__(self, db: Session):
        super().__init__(Report, db)

    def create(
        self,
        db_or_obj: Any,
        obj: Optional[Report] = None,
    ) -> Report:
        report = db_or_obj if obj is None else obj
        if report.llm_candidate_audit is None:
            report.llm_candidate_audit = load_llm_candidate_audit(report)
        return super().create(db_or_obj, obj)

    def get_by_id(self, report_id: str) -> Optional[Report]:
        stmt = select(Report).where(
            Report.id == report_id
        )
        return self.db.scalar(stmt)

    def get_by_document_id(self, document_id: str) -> List[Report]:
        stmt = select(Report).where(
            Report.document_id == document_id
        )
        return list(self.db.scalars(stmt).all())

    def get_by_report_type(
        self,
        report_type: str
    ) -> List[Report]:
        stmt = select(Report).where(
            Report.report_type == report_type
        )
        return list(self.db.scalars(stmt).all())

    def get_by_generated_by(
        self,
        generated_by: str
    ) -> List[Report]:
        stmt = select(Report).where(
            Report.generated_by == generated_by
        )
        return list(self.db.scalars(stmt).all())

    def get_latest_by_document(
        self,
        document_id: str
    ) -> Optional[Report]:
        stmt = (
            select(Report)
            .where(Report.document_id == document_id)
            .order_by(Report.created_at.desc())
        )
        return self.db.scalar(stmt)


def empty_llm_candidate_audit() -> Dict[str, List[Dict[str, Any]]]:
    return {"accepted": [], "rejected": []}


def normalize_llm_candidate_audit(
    audit: Any,
) -> Dict[str, List[Dict[str, Any]]]:
    if not isinstance(audit, dict):
        return empty_llm_candidate_audit()

    normalized = empty_llm_candidate_audit()
    for decision in ("accepted", "rejected"):
        candidates = audit.get(decision)
        if not isinstance(candidates, list):
            continue
        normalized[decision] = [
            dict(candidate)
            for candidate in candidates
            if isinstance(candidate, dict)
        ]
    return normalized


def extract_llm_candidate_audit(
    payload: Any,
    document_id: str,
) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    if not isinstance(payload, dict):
        return None

    payload_document_id = payload.get("document_id")
    if str(payload_document_id or "") != str(document_id):
        return None

    return normalize_llm_candidate_audit(
        payload.get("llm_candidate_audit")
    )


def load_llm_candidate_audit(
    report: Report,
) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    if not report.report_path:
        return None

    report_path = Path(report.report_path)
    if not report_path.is_absolute():
        report_path = Path.cwd() / report_path

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return extract_llm_candidate_audit(payload, report.document_id)
