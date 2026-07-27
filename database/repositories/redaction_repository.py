from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.redaction import Redaction
from database.repositories.base_repository import BaseRepository


class RedactionRepository(BaseRepository[Redaction]):
    def __init__(self, db: Session):
        super().__init__(Redaction, db)

    def get_by_id(self, redaction_id: str) -> Optional[Redaction]:
        stmt = select(Redaction).where(
            Redaction.id == redaction_id
        )
        return self.db.scalar(stmt)

    def get_by_document_id(self, document_id: str) -> List[Redaction]:
        stmt = select(Redaction).where(
            Redaction.document_id == document_id
        )
        return list(self.db.scalars(stmt).all())

    def get_by_redaction_type(
        self,
        redaction_type: str
    ) -> List[Redaction]:
        stmt = select(Redaction).where(
            Redaction.redaction_type == redaction_type
        )
        return list(self.db.scalars(stmt).all())

    def get_by_processed_by(
        self,
        processed_by: str
    ) -> List[Redaction]:
        stmt = select(Redaction).where(
            Redaction.processed_by == processed_by
        )
        return list(self.db.scalars(stmt).all())

    def delete_by_document_id(self, document_id: str) -> int:
        redactions = self.get_by_document_id(document_id)

        for redaction in redactions:
            self.db.delete(redaction)

        self.db.commit()

        return len(redactions)