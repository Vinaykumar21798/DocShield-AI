from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing common CRUD operations.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, obj: ModelType) -> ModelType:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get_by_id(self, db: Session, object_id: str) -> Optional[ModelType]:
        return (
            db.query(self.model)
            .filter(self.model.id == object_id)
            .first()
        )

    def get_all(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        return (
            db.query(self.model)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(
        self,
        db: Session,
        db_obj: ModelType,
        updates: Dict[str, Any],
    ) -> ModelType:

        for field, value in updates.items():
            setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)

        return db_obj

    def delete(
        self,
        db: Session,
        db_obj: ModelType,
    ) -> None:

        db.delete(db_obj)
        db.commit()