from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing common CRUD operations.
    """

    def __init__(self, model: Type[ModelType], db: Optional[Session] = None):
        self.model = model
        self.db = db

    def create(self, db_or_obj: Any, obj: Optional[ModelType] = None) -> ModelType:
        if obj is None:
            # HEAD style: create(self, obj)
            session = self.db
            actual_obj = db_or_obj
        else:
            # origin/main style: create(self, db, obj)
            session = db_or_obj
            actual_obj = obj
        
        session.add(actual_obj)
        session.commit()
        session.refresh(actual_obj)
        return actual_obj

    def get_by_id(self, db_or_id: Any, object_id: Optional[str] = None) -> Optional[ModelType]:
        if object_id is None:
            # HEAD style: get_by_id(self, obj_id)
            session = self.db
            actual_id = db_or_id
        else:
            # origin/main style: get_by_id(self, db, object_id)
            session = db_or_id
            actual_id = object_id
        return session.query(self.model).filter(self.model.id == actual_id).first()

    def get_all(
        self,
        db_or_none: Optional[Session] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        if db_or_none is not None and not isinstance(db_or_none, int):
            session = db_or_none
        else:
            session = self.db
        
        query = session.query(self.model)
        if db_or_none is None:
            # HEAD style: return all
            return query.all()
        else:
            # origin/main style: return paginated
            return query.offset(skip).limit(limit).all()

    def update(
        self,
        db_or_obj: Any,
        db_obj: Optional[ModelType] = None,
        updates: Optional[Dict[str, Any]] = None,
    ) -> ModelType:
        if db_obj is None:
            # HEAD style: update(self, obj)
            session = self.db
            actual_obj = db_or_obj
        else:
            # origin/main style: update(self, db, db_obj, updates)
            session = db_or_obj
            actual_obj = db_obj
            if updates:
                for field, value in updates.items():
                    setattr(actual_obj, field, value)

        session.commit()
        session.refresh(actual_obj)
        return actual_obj

    def delete(self, db_or_obj: Any, db_obj: Optional[ModelType] = None) -> None:
        if db_obj is None:
            # HEAD style: delete(self, obj)
            session = self.db
            actual_obj = db_or_obj
        else:
            # origin/main style: delete(self, db, db_obj)
            session = db_or_obj
            actual_obj = db_obj
        session.delete(actual_obj)
        session.commit()
