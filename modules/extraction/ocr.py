from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional, Tuple, List
import fitz

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
    SUBSTANTIAL_TEXT_THRESHOLD = 500
    MAX_IMAGE_AREA_RATIO = 0.30

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
        
        # Heuristic to distinguish native PDFs from scanned PDFs with searchable footers/headers.
        # A page is considered searchable if it has substantial text, 
        # or if it has some text but isn't dominated by a large image (which usually indicates a scan).
        is_searchable = False
        
        if text_length >= self.SUBSTANTIAL_TEXT_THRESHOLD:
            # Page contains enough text to be considered a native document regardless of images.
            is_searchable = True
        elif text_length >= self.MIN_SEARCHABLE_TEXT_LENGTH:
            # Page has some text; check if it is dominated by a large image (typical for scanned docs with footers).
            images = page.get_images(full=True)
            if not images:
                is_searchable = True
            else:
                page_rect = page.rect
                page_area = page_rect.width * page_rect.height
                
                # Calculate the union area of all image rectangles to avoid double-counting overlapping images.
                all_rects = []
                for img in images:
                    try:
                        rects = page.get_image_rects(img[0])
                        for r in rects:
                            # Clip rectangle to page bounds
                            clipped = r & page_rect
                            if not clipped.is_empty:
                                all_rects.append(clipped)
                    except Exception:
                        continue
                
                union_area = self._calculate_union_area(all_rects)
                is_dominated_by_image = (union_area / page_area) > self.MAX_IMAGE_AREA_RATIO
                
                if not is_dominated_by_image:
                    is_searchable = True

        return PDFPageSearchability(
            page_number=page_index + 1,
            is_searchable=is_searchable,
            text_length=text_length,
        )

    @staticmethod
    def _calculate_union_area(rects: List[fitz.Rect]) -> float:
        """
        Calculates the area of the union of multiple rectangles.
        Uses a simple coordinate compression (sweep-line) approach.
        """
        if not rects:
            return 0.0
        
        # Extract all x-coordinates
        x_coords = sorted(set([r.x0 for r in rects] + [r.x1 for r in rects]))
        x_map = {x: i for i, x in enumerate(x_coords)}
        
        # Create a grid of y-intervals for each x-strip
        # strip_y_intervals[i] contains a list of (y0, y1) for rectangles covering the strip [x_coords[i], x_coords[i+1]]
        strip_y_intervals = [[] for _ in range(len(x_coords) - 1)]
        
        for r in rects:
            for i in range(x_map[r.x0], x_map[r.x1]):
                strip_y_intervals[i].append((r.y0, r.y1))
        
        total_area = 0.0
        for i in range(len(x_coords) - 1):
            width = x_coords[i+1] - x_coords[i]
            if width <= 0:
                continue
                
            # Calculate the length of the union of y-intervals in this strip
            intervals = sorted(strip_y_intervals[i])
            if not intervals:
                continue
                
            union_y_len = 0.0
            curr_y0, curr_y1 = intervals[0]
            
            for next_y0, next_y1 in intervals[1:]:
                if next_y0 < curr_y1:
                    curr_y1 = max(curr_y1, next_y1)
                else:
                    union_y_len += curr_y1 - curr_y0
                    curr_y0, curr_y1 = next_y0, next_y1
            
            union_y_len += curr_y1 - curr_y0
            total_area += width * union_y_len
            
        return total_area


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
