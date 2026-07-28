from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.review import Review
from database.repositories.base_repository import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    def __init__(self, db: Session):
        super().__init__(Review, db)

    def get_by_id(self, review_id: str) -> Optional[Review]:
        stmt = select(Review).where(
            Review.id == review_id
        )
        return self.db.scalar(stmt)

    def get_by_entity_id(self, entity_id: str) -> Optional[Review]:
        stmt = select(Review).where(
            Review.entity_id == entity_id
        )
        return self.db.scalar(stmt)

    def get_by_reviewer(
        self,
        reviewer: str
    ) -> List[Review]:
        stmt = select(Review).where(
            Review.reviewer == reviewer
        )
        return list(self.db.scalars(stmt).all())

    def get_by_review_status(
        self,
        review_status: str
    ) -> List[Review]:
        stmt = select(Review).where(
            Review.review_status == review_status
        )
        return list(self.db.scalars(stmt).all())

    def get_pending_reviews(self) -> List[Review]:
        stmt = select(Review).where(
            Review.review_status == "PENDING"
        )
        return list(self.db.scalars(stmt).all())