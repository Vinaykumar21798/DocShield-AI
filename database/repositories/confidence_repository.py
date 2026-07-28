from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.confidence import ConfidenceScore
from database.repositories.base_repository import BaseRepository


class ConfidenceRepository(BaseRepository[ConfidenceScore]):
    def __init__(self, db: Session):
        super().__init__(ConfidenceScore, db)

    def get_by_id(self, confidence_id: str) -> Optional[ConfidenceScore]:
        stmt = select(ConfidenceScore).where(
            ConfidenceScore.id == confidence_id
        )
        return self.db.scalar(stmt)

    def get_by_entity_id(self, entity_id: str) -> Optional[ConfidenceScore]:
        stmt = select(ConfidenceScore).where(
            ConfidenceScore.entity_id == entity_id
        )
        return self.db.scalar(stmt)

    def get_by_confidence_level(
        self,
        confidence_level: str
    ) -> List[ConfidenceScore]:
        stmt = select(ConfidenceScore).where(
            ConfidenceScore.confidence_level == confidence_level
        )
        return list(self.db.scalars(stmt).all())

    def get_below_threshold(
        self,
        threshold: float
    ) -> List[ConfidenceScore]:
        stmt = select(ConfidenceScore).where(
            ConfidenceScore.confidence_score < threshold
        )
        return list(self.db.scalars(stmt).all())