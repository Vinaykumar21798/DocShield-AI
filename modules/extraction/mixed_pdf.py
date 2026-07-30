from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Sequence

from database.models import Document
from modules.extraction.native import TextExtractionResult
from modules.extraction.paddle import (
    OCRPageText,
    PaddleOCRExtractionService,
)


class MixedPDFExtractionError(Exception):
    """
    Raised when mixed native/OCR PDF extraction fails.
    """


@dataclass(frozen=True)
class MixedPDFPageResult:
    page_number: int
    text: str
    is_searchable: bool
    extraction_source: str
    confidence_scores: Sequence[float]
    structured_output: Dict[str, Any]


class MixedPDFExtractionService:
    """
    Extracts searchable PDF pages natively and OCRs only scanned pages.
    """

    MIN_SEARCHABLE_TEXT_LENGTH = 10
    NATIVE_CONFIDENCE = 1.0
    STRUCTURED_OUTPUT_VERSION = "mixed_pdf_extraction_v1"

    def __init__(
        self,
        paddle_ocr_extractor: Optional[PaddleOCRExtractionService] = None,
        min_searchable_text_length: int = MIN_SEARCHABLE_TEXT_LENGTH,
    ):
        self.paddle_ocr_extractor = (
            paddle_ocr_extractor or PaddleOCRExtractionService()
        )
        self.min_searchable_text_length = min_searchable_text_length

    def extract(self, document: Document) -> TextExtractionResult:
        file_path = self._get_file_path(document)
        start_time = perf_counter()

        try:
            import fitz
        except ImportError as exc:
            raise MixedPDFExtractionError(
                "PyMuPDF is required for mixed PDF extraction."
            ) from exc

        try:
            with fitz.open(file_path) as pdf_document:
                page_count = pdf_document.page_count
                page_results = self._extract_native_pages(pdf_document)
        except Exception as exc:
            raise MixedPDFExtractionError(
                f"Failed to inspect mixed PDF pages: {file_path}"
            ) from exc

        scanned_page_numbers = [
            page.page_number
            for page in page_results
            if not page.is_searchable
        ]
        if scanned_page_numbers:
            ocr_results = self.paddle_ocr_extractor.extract_pdf_pages(
                file_path,
                scanned_page_numbers,
            )
            page_results = self._merge_ocr_pages(
                page_results,
                ocr_results,
            )

        page_results.sort(key=lambda page: page.page_number)
        processing_time = perf_counter() - start_time
        extracted_text = self._merge_page_text(page_results)

        return TextExtractionResult(
            extracted_text=extracted_text,
            page_count=page_count,
            confidence_score=self._average_confidence(page_results),
            processing_time=processing_time,
            structured_output=self._build_document_output(page_results),
        )

    def _extract_native_pages(self, pdf_document) -> List[MixedPDFPageResult]:
        page_results = []

        for page_index in range(pdf_document.page_count):
            page = pdf_document.load_page(page_index)
            page_text = page.get_text("text").strip()
            is_searchable = (
                len(page_text) >= self.min_searchable_text_length
            )
            page_results.append(
                MixedPDFPageResult(
                    page_number=page_index + 1,
                    text=page_text if is_searchable else "",
                    is_searchable=is_searchable,
                    extraction_source=(
                        "native_pdf" if is_searchable else "paddleocr"
                    ),
                    confidence_scores=(
                        (self.NATIVE_CONFIDENCE,) if is_searchable else tuple()
                    ),
                    structured_output=self._build_native_page_output(
                        page_number=page_index + 1,
                        text=page_text if is_searchable else "",
                        is_searchable=is_searchable,
                    ),
                )
            )

        return page_results

    def _merge_ocr_pages(
        self,
        page_results: List[MixedPDFPageResult],
        ocr_results: List[OCRPageText],
    ) -> List[MixedPDFPageResult]:
        ocr_by_page = {
            page.structured_output.get("page_number"): page
            for page in ocr_results
        }
        merged_pages = []

        for page in page_results:
            if page.is_searchable:
                merged_pages.append(page)
                continue

            ocr_page = ocr_by_page.get(page.page_number)
            if ocr_page is None:
                merged_pages.append(page)
                continue

            page_output = dict(ocr_page.structured_output)
            page_output["page_number"] = page.page_number
            page_output["is_searchable"] = False
            page_output["extraction_source"] = "paddleocr"
            merged_pages.append(
                MixedPDFPageResult(
                    page_number=page.page_number,
                    text=ocr_page.text,
                    is_searchable=False,
                    extraction_source="paddleocr",
                    confidence_scores=ocr_page.confidence_scores,
                    structured_output=page_output,
                )
            )

        return merged_pages

    def _build_native_page_output(
        self,
        page_number: int,
        text: str,
        is_searchable: bool,
    ) -> Dict[str, Any]:
        blocks = []
        if text:
            blocks.append(
                {
                    "block_type": "text",
                    "bbox": None,
                    "text": text,
                    "source": "pymupdf_text",
                }
            )

        return {
            "page_number": page_number,
            "is_searchable": is_searchable,
            "extraction_source": (
                "native_pdf" if is_searchable else "paddleocr"
            ),
            "layout_source": "native_text" if is_searchable else "pending_ocr",
            "layout_analysis_used": False,
            "text": text,
            "blocks": blocks,
            "lines": [],
        }

    def _build_document_output(
        self,
        page_results: List[MixedPDFPageResult],
    ) -> Dict[str, Any]:
        searchable_pages = [
            page.page_number
            for page in page_results
            if page.is_searchable
        ]
        ocr_pages = [
            page.page_number
            for page in page_results
            if not page.is_searchable
        ]
        layout_sources = sorted({
            str(page.structured_output.get("layout_source"))
            for page in page_results
            if page.structured_output.get("layout_source")
        })

        return {
            "schema_version": self.STRUCTURED_OUTPUT_VERSION,
            "engine": "MIXED_PDF",
            "page_count": len(page_results),
            "searchable_pages": searchable_pages,
            "ocr_pages": ocr_pages,
            "layout_analysis_used": any(
                page.structured_output.get("layout_analysis_used")
                for page in page_results
            ),
            "layout_sources": layout_sources,
            "pages": [
                page.structured_output
                for page in page_results
            ],
        }

    @staticmethod
    def _merge_page_text(page_results: List[MixedPDFPageResult]) -> str:
        return PaddleOCRExtractionService.PAGE_BREAK.join(
            page.text
            for page in page_results
            if page.text
        ).strip()

    @staticmethod
    def _average_confidence(page_results: List[MixedPDFPageResult]) -> float:
        confidence_scores = [
            score
            for page in page_results
            for score in page.confidence_scores
        ]

        if not confidence_scores:
            return 0.0

        return sum(confidence_scores) / len(confidence_scores)

    def _get_file_path(self, document: Document) -> Path:
        if not document.storage_path:
            raise MixedPDFExtractionError(
                f"Document storage path is missing: {document.id}"
            )

        file_path = Path(document.storage_path)

        if not file_path.exists():
            raise MixedPDFExtractionError(
                f"Stored document file not found: {file_path}"
            )

        return file_path
