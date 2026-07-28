from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

from database.models import Document


class OCREngine(str, Enum):
    NATIVE_PDF = "NATIVE_PDF"
    NATIVE_TEXT = "NATIVE_TEXT"
    PADDLEOCR = "PADDLEOCR"


class OCRDecisionError(Exception):
    """
    Raised when the OCR engine cannot be selected for a document.
    """


@dataclass(frozen=True)
class OCRDecision:
    engine: OCREngine
    is_searchable: bool
    reason: str


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

    MAX_PDF_PAGES_TO_PROBE = 3
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
        if self._pdf_has_searchable_text(file_path):
            return OCRDecision(
                engine=OCREngine.NATIVE_PDF,
                is_searchable=True,
                reason="PDF contains searchable text.",
            )

        return OCRDecision(
            engine=OCREngine.PADDLEOCR,
            is_searchable=False,
            reason="PDF does not contain searchable text in probed pages.",
        )

    def _pdf_has_searchable_text(self, file_path: Path) -> bool:
        try:
            import fitz
        except ImportError as exc:
            raise OCRDecisionError(
                "PyMuPDF is required for PDF searchability detection."
            ) from exc

        try:
            with fitz.open(file_path) as pdf_document:
                pages_to_probe = min(
                    pdf_document.page_count,
                    self.MAX_PDF_PAGES_TO_PROBE,
                )

                return self._has_text_in_pages(
                    pdf_document,
                    pages_to_probe,
                )

        except Exception as exc:
            raise OCRDecisionError(
                f"Unable to inspect PDF searchability: {file_path}"
            ) from exc

    def _has_text_in_pages(
        self,
        pdf_document,
        pages_to_probe: int,
    ) -> bool:
        total_text_length = 0

        for page_number in range(pages_to_probe):
            page = pdf_document.load_page(page_number)
            page_text = page.get_text("text").strip()
            total_text_length += len(page_text)

            if total_text_length >= self.MIN_SEARCHABLE_TEXT_LENGTH:
                return True

        return False

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
