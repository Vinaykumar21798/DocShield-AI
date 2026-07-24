from typing import List, Optional

from sqlalchemy.orm import Session

from database.models import OCRResult
from database.repositories.base_repository import BaseRepository


class OCRResultRepository(BaseRepository[OCRResult]):

    def __init__(self):
        super().__init__(OCRResult)

    def create_result(
        self,
        db: Session,
        result: OCRResult,
    ) -> OCRResult:
        return self.create(db, result)

    def get_result_by_id(
        self,
        db: Session,
        result_id: str,
    ) -> Optional[OCRResult]:
        return self.get_by_id(db, result_id)

    def get_by_document_id(
        self,
        db: Session,
        document_id: str,
    ) -> List[OCRResult]:
        return (
            db.query(OCRResult)
            .filter(OCRResult.document_id == document_id)
            .all()
        )

    def update_extracted_text(
        self,
        db: Session,
        result: OCRResult,
        extracted_text: str,
    ) -> OCRResult:
        return self.update(
            db,
            result,
            {
                "extracted_text": extracted_text,
            },
        )

    def update_text_path(
        self,
        db: Session,
        result: OCRResult,
        text_path: str,
    ) -> OCRResult:
        return self.update(
            db,
            result,
            {
                "extracted_text_path": text_path,
            },
        )

    def update_confidence(
        self,
        db: Session,
        result: OCRResult,
        confidence: float,
    ) -> OCRResult:
        return self.update(
            db,
            result,
            {
                "confidence_score": confidence,
            },
        )

    def update_processing_time(
        self,
        db: Session,
        result: OCRResult,
        processing_time: float,
    ) -> OCRResult:
        return self.update(
            db,
            result,
            {
                "processing_time": processing_time,
            },
        )

    def update_page_count(
        self,
        db: Session,
        result: OCRResult,
        page_count: int,
    ) -> OCRResult:
        return self.update(
            db,
            result,
            {
                "page_count": page_count,
            },
        )

    def update_extraction_method(
        self,
        db: Session,
        result: OCRResult,
        method: str,
    ) -> OCRResult:
        return self.update(
            db,
            result,
            {
                "extraction_method": method,
            },
        )

    def update_searchable_status(
        self,
        db: Session,
        result: OCRResult,
        is_searchable: bool,
    ) -> OCRResult:
        return self.update(
            db,
            result,
            {
                "is_searchable": is_searchable,
            },
        )

    def delete_result(
        self,
        db: Session,
        result: OCRResult,
    ) -> None:
        self.delete(db, result)


ocr_result_repository = OCRResultRepository()