from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.entity import Entity
from database.repositories.base_repository import BaseRepository


class EntityRepository(BaseRepository[Entity]):
    def __init__(self, db: Session):
        super().__init__(Entity, db)

    def create(self, obj: Entity) -> Entity:
        """
        Creates a new Entity record in the database with strict validation and diagnostic logging.
        """
        # Issue 6: Persistence Validation
        required_fields = ["id", "document_id", "entity_type", "entity_value"]
        for field in required_fields:
            val = getattr(obj, field, None)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise ValueError(f"Persistence Validation Failed: Missing required column '{field}' on Entity model.")

        # Issue 5: Database exception catching and rollback diagnostics
        try:
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as exc:
            self.db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            failed_sql = (
                "INSERT INTO entities (id, document_id, ocr_result_id, entity_type, entity_value, "
                "page_number, confidence_score, detector, start_char, end_char, privacy_category, "
                "entity_owner, canonical_type, processing_stage, is_review_required, is_redacted, "
                "final_confidence, created_at) VALUES (...)"
            )
            logger.error(
                "\n❌ DATABASE PERSISTENCE TRANSACTION FAILURE ❌\n"
                f"Entity ID: {getattr(obj, 'id', None)}\n"
                f"Detector: {getattr(obj, 'detector', None)}\n"
                f"Entity Type: {getattr(obj, 'entity_type', None)}\n"
                f"Privacy Category: {getattr(obj, 'privacy_category', None)}\n"
                f"Confidence: {getattr(obj, 'confidence_score', None)}\n"
                f"Failed SQL: {failed_sql}\n"
                f"Database Exception: {exc}\n"
                "Migration Hint: Check if columns like 'start_char', 'end_char', or 'privacy_category' "
                "exist in the database. Ensure Alembic migrations are up to date by running `alembic upgrade head`.\n"
            )
            raise RuntimeError(
                f"Database save failed for entity {getattr(obj, 'id', None)}. Details: {exc}"
            ) from None

    def get_by_document_id(self, document_id: str) -> List[Entity]:
        stmt = select(Entity).where(Entity.document_id == document_id)
        return list(self.db.scalars(stmt).all())

    def get_by_ocr_result_id(self, ocr_result_id: str) -> List[Entity]:
        stmt = select(Entity).where(Entity.ocr_result_id == ocr_result_id)
        return list(self.db.scalars(stmt).all())

    def get_by_entity_type(self, entity_type: str) -> List[Entity]:
        stmt = select(Entity).where(Entity.entity_type == entity_type)
        return list(self.db.scalars(stmt).all())

    def get_by_detector(self, detector: str) -> List[Entity]:
        stmt = select(Entity).where(Entity.detector == detector)
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, entity_id: str) -> Optional[Entity]:
        stmt = select(Entity).where(Entity.id == entity_id)
        return self.db.scalar(stmt)

    def delete_by_document_id(self, document_id: str) -> int:
        entities = self.get_by_document_id(document_id)

        for entity in entities:
            self.db.delete(entity)

        self.db.commit()

        return len(entities)