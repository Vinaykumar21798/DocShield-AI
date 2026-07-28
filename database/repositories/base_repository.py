from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing common CRUD operations.

    Supports both repository styles currently used in the merged codebase:
    session-bound repositories and explicit-session repositories.
    """

    def __init__(self, model: Type[ModelType], db: Optional[Session] = None):
        self.model = model
        self.db = db

    @staticmethod
    def _require_session(session: Optional[Session]) -> Session:
        if session is None:
            raise RuntimeError("Repository operation requires a database session")
        return session

    def create(
        self,
        db_or_obj: Any,
        obj: Optional[ModelType] = None,
    ) -> ModelType:
        if obj is None:
            session = self._require_session(self.db)
            actual_obj = db_or_obj
        else:
            session = self._require_session(db_or_obj)
            actual_obj = obj

        session.add(actual_obj)
        session.commit()
        session.refresh(actual_obj)
        return actual_obj

    def get_by_id(
        self,
        db_or_id: Any,
        object_id: Optional[str] = None,
    ) -> Optional[ModelType]:
        if object_id is None:
            session = self._require_session(self.db)
            actual_id = db_or_id
        else:
            session = self._require_session(db_or_id)
            actual_id = object_id

        return (
            session.query(self.model)
            .filter(self.model.id == actual_id)
            .first()
        )

    def get_all(
        self,
        db_or_none: Optional[Session] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        session = self._require_session(db_or_none or self.db)
        query = session.query(self.model)

        if db_or_none is None:
            return query.all()

        return query.offset(skip).limit(limit).all()

    def update(
        self,
        db_or_obj: Any,
        db_obj: Optional[ModelType] = None,
        updates: Optional[Dict[str, Any]] = None,
    ) -> ModelType:
        if db_obj is None:
            session = self._require_session(self.db)
            actual_obj = db_or_obj
        else:
            session = self._require_session(db_or_obj)
            actual_obj = db_obj
            if updates:
                for field, value in updates.items():
                    setattr(actual_obj, field, value)

        session.commit()
        session.refresh(actual_obj)
        return actual_obj

    def delete(
        self,
        db_or_obj: Any,
        db_obj: Optional[ModelType] = None,
    ) -> None:
        if db_obj is None:
            session = self._require_session(self.db)
            actual_obj = db_or_obj
        else:
            session = self._require_session(db_or_obj)
            actual_obj = db_obj

        session.delete(actual_obj)
        session.commit()