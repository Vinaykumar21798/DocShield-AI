from typing import List, Optional

from sqlalchemy.orm import Session

from database.models import Document
from database.repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository[Document]):

    def __init__(self):
        super().__init__(Document)

    def create_document(
        self,
        db: Session,
        document: Document,
    ) -> Document:
        return self.create(db, document)

    def get_document_by_id(
        self,
        db: Session,
        document_id: str,
    ) -> Optional[Document]:
        return self.get_by_id(db, document_id)

    def get_document_by_filename(
        self,
        db: Session,
        filename: str,
    ) -> Optional[Document]:
        return (
            db.query(Document)
            .filter(Document.filename == filename)
            .first()
        )

    def get_document_by_stored_filename(
        self,
        db: Session,
        stored_filename: str,
    ) -> Optional[Document]:
        return (
            db.query(Document)
            .filter(Document.stored_filename == stored_filename)
            .first()
        )

    def get_documents(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        return self.get_all(db, skip, limit)

    def get_documents_by_status(
        self,
        db: Session,
        status: str,
    ) -> List[Document]:
        return (
            db.query(Document)
            .filter(Document.status == status)
            .all()
        )

    def update_status(
        self,
        db: Session,
        document: Document,
        status: str,
    ) -> Document:
        return self.update(
            db,
            document,
            {"status": status},
        )

    def update_document_type(
        self,
        db: Session,
        document: Document,
        document_type: str,
    ) -> Document:
        return self.update(
            db,
            document,
            {"document_type": document_type},
        )

    def delete_document(
        self,
        db: Session,
        document: Document,
    ) -> None:
        self.delete(db, document)


document_repository = DocumentRepository()