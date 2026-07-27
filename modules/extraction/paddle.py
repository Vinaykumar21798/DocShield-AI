import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any, List, Optional, Tuple

from database.models import Document
from modules.extraction.native import TextExtractionResult


class PaddleOCRExtractionError(Exception):
    """
    Raised when PaddleOCR extraction fails.
    """


@dataclass(frozen=True)
class OCRPageText:
    text: str
    confidence_scores: Tuple[float, ...]


class PaddleOCRExtractionService:
    """
    Extracts text from scanned PDFs and image documents using PaddleOCR.
    """

    PDF_EXTENSIONS = {".pdf"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    DEFAULT_LANGUAGE = "en"
    PDF_RENDER_SCALE = 2.0

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        render_scale: float = PDF_RENDER_SCALE,
    ):
        self.language = language
        self.render_scale = render_scale
        self._ocr_client = None

    def extract(self, document: Document) -> TextExtractionResult:
        file_path = self._get_file_path(document)
        extension = self._get_extension(document, file_path)
        start_time = perf_counter()

        if extension in self.PDF_EXTENSIONS:
            page_results = self._extract_pdf(file_path)
            page_count = len(page_results)

        elif extension in self.IMAGE_EXTENSIONS:
            page_results = [self._extract_image(file_path)]
            page_count = 1

        else:
            raise PaddleOCRExtractionError(
                f"Unsupported file type for PaddleOCR: {extension}"
            )

        processing_time = perf_counter() - start_time
        extracted_text = self._merge_page_text(page_results)
        confidence_score = self._average_confidence(page_results)

        return TextExtractionResult(
            extracted_text=extracted_text,
            page_count=page_count,
            confidence_score=confidence_score,
            processing_time=processing_time,
        )

    def _extract_pdf(self, file_path: Path) -> List[OCRPageText]:
        try:
            import fitz
        except ImportError as exc:
            raise PaddleOCRExtractionError(
                "PyMuPDF is required to render scanned PDFs for PaddleOCR."
            ) from exc

        page_results = []

        try:
            with fitz.open(file_path) as pdf_document:
                with TemporaryDirectory(
                    prefix="paddleocr_pages_",
                    dir=str(file_path.parent),
                ) as temp_dir:
                    temp_path = Path(temp_dir)

                    for page_number in range(pdf_document.page_count):
                        page = pdf_document.load_page(page_number)
                        image_path = self._render_pdf_page(
                            page,
                            temp_path,
                            page_number,
                        )
                        page_results.append(
                            self._extract_image(image_path)
                        )

        except Exception as exc:
            raise PaddleOCRExtractionError(
                f"Failed to extract scanned PDF text: {file_path}"
            ) from exc

        return page_results

    def _render_pdf_page(
        self,
        page,
        temp_path: Path,
        page_number: int,
    ) -> Path:
        import fitz

        matrix = fitz.Matrix(self.render_scale, self.render_scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image_path = temp_path / f"page_{page_number + 1}.png"
        pixmap.save(str(image_path))
        return image_path

    def _extract_image(self, file_path: Path) -> OCRPageText:
        raw_result = self._run_paddle_ocr(file_path)
        lines = self._extract_text_lines(raw_result)
        text = "\n".join(line for line, _ in lines).strip()
        confidence_scores = tuple(score for _, score in lines)

        return OCRPageText(
            text=text,
            confidence_scores=confidence_scores,
        )

    def _run_paddle_ocr(self, file_path: Path) -> Any:
        ocr_client = self._get_ocr_client()

        if hasattr(ocr_client, "predict"):
            return ocr_client.predict(str(file_path))

        if hasattr(ocr_client, "ocr"):
            try:
                return ocr_client.ocr(str(file_path), cls=True)
            except TypeError:
                return ocr_client.ocr(str(file_path))

        raise PaddleOCRExtractionError(
            "PaddleOCR client does not expose ocr or predict methods."
        )

    def _get_ocr_client(self):
        if self._ocr_client is not None:
            return self._ocr_client

        self._configure_paddle_runtime()

        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise PaddleOCRExtractionError(
                "paddleocr is required for scanned document OCR."
            ) from exc

        self._ocr_client = self._build_ocr_client(PaddleOCR)
        return self._ocr_client

    @staticmethod
    def _configure_paddle_runtime() -> None:
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        os.environ.setdefault("FLAGS_enable_pir_api", "0")

    def _build_ocr_client(self, paddle_ocr_class):
        constructor_options = (
            {
                "lang": self.language,
                "device": "cpu",
                "enable_mkldnn": False,
                "cpu_threads": 4,
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "use_textline_orientation": False,
            },
            {
                "lang": self.language,
                "device": "cpu",
                "enable_mkldnn": False,
                "cpu_threads": 4,
            },
            {
                "lang": self.language,
            },
            {
                "use_angle_cls": True,
                "lang": self.language,
            },
        )

        last_error = None

        for options in constructor_options:
            try:
                return paddle_ocr_class(**options)
            except (TypeError, ValueError) as exc:
                last_error = exc

        raise PaddleOCRExtractionError(
            "Failed to initialize PaddleOCR client."
        ) from last_error

    def _extract_text_lines(self, raw_result: Any) -> List[Tuple[str, float]]:
        lines: List[Tuple[str, float]] = []
        self._collect_text_lines(raw_result, lines)
        return lines

    def _collect_text_lines(
        self,
        value: Any,
        lines: List[Tuple[str, float]],
    ) -> None:
        if value is None:
            return

        if isinstance(value, dict):
            self._collect_dict_text_lines(value, lines)
            return

        if self._is_legacy_text_line(value):
            text, score = value[1][0], value[1][1]
            lines.append((text, self._normalize_score(score)))
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                self._collect_text_lines(item, lines)

    def _collect_dict_text_lines(
        self,
        value: dict,
        lines: List[Tuple[str, float]],
    ) -> None:
        rec_texts = value.get("rec_texts")
        rec_scores = value.get("rec_scores") or []

        if isinstance(rec_texts, list):
            for index, text in enumerate(rec_texts):
                score = 0.0

                if index < len(rec_scores):
                    score = self._normalize_score(rec_scores[index])

                if isinstance(text, str) and text.strip():
                    lines.append((text.strip(), score))

            return

        for item in value.values():
            self._collect_text_lines(item, lines)

    @staticmethod
    def _is_legacy_text_line(value: Any) -> bool:
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            return False

        candidate = value[1]

        return (
            isinstance(candidate, (list, tuple))
            and len(candidate) >= 2
            and isinstance(candidate[0], str)
        )

    @staticmethod
    def _normalize_score(score: Any) -> float:
        try:
            return float(score)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _merge_page_text(page_results: List[OCRPageText]) -> str:
        return "\n\n".join(
            page_result.text
            for page_result in page_results
            if page_result.text
        ).strip()

    @staticmethod
    def _average_confidence(page_results: List[OCRPageText]) -> float:
        confidence_scores = [
            score
            for page_result in page_results
            for score in page_result.confidence_scores
        ]

        if not confidence_scores:
            return 0.0

        return sum(confidence_scores) / len(confidence_scores)

    def _get_file_path(self, document: Document) -> Path:
        if not document.storage_path:
            raise PaddleOCRExtractionError(
                f"Document storage path is missing: {document.id}"
            )

        file_path = Path(document.storage_path)

        if not file_path.exists():
            raise PaddleOCRExtractionError(
                f"Stored document file not found: {file_path}"
            )

        return file_path

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
