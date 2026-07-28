from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.report import Report
from database.repositories.base_repository import BaseRepository


class ReportRepository(BaseRepository[Report]):
    def __init__(self, db: Session):
        super().__init__(Report, db)

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