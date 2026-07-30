from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional, Tuple

from database.models import Document


class OCREngine(str, Enum):
    NATIVE_PDF = "NATIVE_PDF"
    NATIVE_TEXT = "NATIVE_TEXT"
    PADDLEOCR = "PADDLEOCR"
    MIXED_PDF = "MIXED_PDF"


class OCRDecisionError(Exception):
    """
    Raised when the OCR engine cannot be selected for a document.
    """


@dataclass(frozen=True)
class PDFPageSearchability:
    page_number: int
    is_searchable: bool
    text_length: int


@dataclass(frozen=True)
class OCRDecision:
    engine: OCREngine
    is_searchable: bool
    reason: str
    page_searchability: Tuple[PDFPageSearchability, ...] = tuple()


class OCRDecisionEngine:
    """
    Determines the extraction engine for an uploaded document.
    """

    PDF_EXTENSIONS = {".pdf"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    TEXT_EXTENSIONS = {".txt"}
    WORD_EXTENSIONS = {".docx"}

    PDF_CONTENT_TYPES = {
        "application/pdf",
        "application/x-pdf",
    }
    IMAGE_CONTENT_TYPE_PREFIX = "image/"
    TEXT_CONTENT_TYPES = {
        "text/plain",
    }
    WORD_CONTENT_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    MIN_SEARCHABLE_TEXT_LENGTH = 10

    def decide(self, document: Document) -> OCRDecision:
        file_path = self._get_storage_path(document)
        extension = self._get_extension(document, file_path)
        content_type = self._normalize_content_type(document.file_type)

        if not file_path.exists():
            raise OCRDecisionError(
                f"Stored document file not found: {file_path}"
            )

        if self._is_pdf(extension, content_type):
            return self._decide_pdf(file_path)

        if self._is_image(extension, content_type):
            return OCRDecision(
                engine=OCREngine.PADDLEOCR,
                is_searchable=False,
                reason="Image document requires OCR.",
            )

        if self._is_native_text(extension, content_type):
            return OCRDecision(
                engine=OCREngine.NATIVE_TEXT,
                is_searchable=True,
                reason="Text-based document can be parsed natively.",
            )

        raise OCRDecisionError(
            "Unsupported document type for OCR decision: "
            f"extension={extension or 'unknown'}, "
            f"content_type={content_type or 'unknown'}"
        )

    def _decide_pdf(self, file_path: Path) -> OCRDecision:
        page_searchability = self._inspect_pdf_page_searchability(file_path)
        searchable_pages = [
            page
            for page in page_searchability
            if page.is_searchable
        ]

        if not page_searchability:
            return OCRDecision(
                engine=OCREngine.PADDLEOCR,
                is_searchable=False,
                reason="PDF has no pages to inspect.",
                page_searchability=page_searchability,
            )

        if len(searchable_pages) == len(page_searchability):
            return OCRDecision(
                engine=OCREngine.NATIVE_PDF,
                is_searchable=True,
                reason="All PDF pages contain searchable text.",
                page_searchability=page_searchability,
            )

        if not searchable_pages:
            return OCRDecision(
                engine=OCREngine.PADDLEOCR,
                is_searchable=False,
                reason="No PDF pages contain searchable text.",
                page_searchability=page_searchability,
            )

        scanned_pages = len(page_searchability) - len(searchable_pages)
        return OCRDecision(
            engine=OCREngine.MIXED_PDF,
            is_searchable=False,
            reason=(
                "PDF has mixed searchable and scanned pages: "
                f"searchable={len(searchable_pages)} scanned={scanned_pages}."
            ),
            page_searchability=page_searchability,
        )

    def _inspect_pdf_page_searchability(
        self,
        file_path: Path,
    ) -> Tuple[PDFPageSearchability, ...]:
        try:
            import fitz
        except ImportError as exc:
            raise OCRDecisionError(
                "PyMuPDF is required for PDF searchability detection."
            ) from exc

        try:
            with fitz.open(file_path) as pdf_document:
                return tuple(
                    self._inspect_pdf_page(pdf_document, page_number)
                    for page_number in range(pdf_document.page_count)
                )

        except Exception as exc:
            raise OCRDecisionError(
                f"Unable to inspect PDF page searchability: {file_path}"
            ) from exc

    def _inspect_pdf_page(
        self,
        pdf_document,
        page_index: int,
    ) -> PDFPageSearchability:
        page = pdf_document.load_page(page_index)
        page_text = page.get_text("text").strip()
        text_length = len(page_text)
        return PDFPageSearchability(
            page_number=page_index + 1,
            is_searchable=(text_length >= self.MIN_SEARCHABLE_TEXT_LENGTH),
            text_length=text_length,
        )

    def _get_storage_path(self, document: Document) -> Path:
        if not document.storage_path:
            raise OCRDecisionError(
                f"Document storage path is missing: {document.id}"
            )

        return Path(document.storage_path)

    def _get_extension(
        self,
        document: Document,
        file_path: Path,
    ) -> str:
        candidates = (
            file_path.suffix,
            Path(document.stored_filename or "").suffix,
            Path(document.filename or "").suffix,
        )

        for extension in candidates:
            normalized_extension = extension.lower().strip()
            if normalized_extension:
                return normalized_extension

        return ""

    @staticmethod
    def _normalize_content_type(content_type: Optional[str]) -> str:
        return (content_type or "").split(";")[0].strip().lower()

    def _is_pdf(
        self,
        extension: str,
        content_type: str,
    ) -> bool:
        return (
            extension in self.PDF_EXTENSIONS
            or content_type in self.PDF_CONTENT_TYPES
        )

    def _is_image(
        self,
        extension: str,
        content_type: str,
    ) -> bool:
        return (
            extension in self.IMAGE_EXTENSIONS
            or content_type.startswith(self.IMAGE_CONTENT_TYPE_PREFIX)
        )

    def _is_native_text(
        self,
        extension: str,
        content_type: str,
    ) -> bool:
        return (
            self._is_extension_match(
                extension,
                self.TEXT_EXTENSIONS | self.WORD_EXTENSIONS,
            )
            or content_type in self.TEXT_CONTENT_TYPES
            or content_type in self.WORD_CONTENT_TYPES
        )

    @staticmethod
    def _is_extension_match(
        extension: str,
        extensions: Iterable[str],
    ) -> bool:
        return extension in extensions
