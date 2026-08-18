import os
import re
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

from database.models import Document
from modules.extraction.native import TextExtractionResult


BoundingBox = Tuple[float, float, float, float]


class PaddleOCRExtractionError(Exception):
    """
    Raised when PaddleOCR extraction fails.
    """


@dataclass(frozen=True)
class OCRTextLine:
    text: str
    confidence_score: float
    bbox: Optional[BoundingBox] = None

    @property
    def left(self) -> float:
        return self.bbox[0] if self.bbox else 0.0

    @property
    def top(self) -> float:
        return self.bbox[1] if self.bbox else 0.0

    @property
    def right(self) -> float:
        return self.bbox[2] if self.bbox else 0.0

    @property
    def bottom(self) -> float:
        return self.bbox[3] if self.bbox else 0.0

    @property
    def center_y(self) -> float:
        if not self.bbox:
            return 0.0
        return (self.top + self.bottom) / 2

    @property
    def height(self) -> float:
        if not self.bbox:
            return 0.0
        return max(self.bottom - self.top, 0.0)


@dataclass(frozen=True)
class OCRPageText:
    text: str
    confidence_scores: Tuple[float, ...]
    structured_output: Dict[str, Any]


class _HTMLTableParser(HTMLParser):
    """
    Minimal HTML table parser for PP-Structure table output.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: List[List[str]] = []
        self._current_row: Optional[List[str]] = None
        self._current_cell: Optional[List[str]] = None

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "tr":
            self._current_row = []
            return
        if (
            normalized_tag in {"td", "th"}
            and self._current_row is not None
        ):
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"td", "th"}:
            if self._current_cell is None or self._current_row is None:
                return
            cell_text = " ".join(
                " ".join(self._current_cell).split()
            )
            self._current_row.append(cell_text)
            self._current_cell = None
            return
        if normalized_tag == "tr" and self._current_row is not None:
            if any(cell.strip() for cell in self._current_row):
                self.rows.append(self._current_row)
            self._current_row = None


class PaddleOCRExtractionService:
    """
    Extracts text from scanned PDFs and image documents using PaddleOCR.
    """

    PDF_EXTENSIONS = {".pdf"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    DEFAULT_LANGUAGE = "en"
    PDF_RENDER_SCALE = 2.0
    STRUCTURED_OUTPUT_VERSION = "layout_ocr_v1"
    PAGE_BREAK = "\n\n\f\n\n"
    ROW_TOLERANCE_MULTIPLIER = 0.60
    BLOCK_GAP_MULTIPLIER = 1.75

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        render_scale: float = PDF_RENDER_SCALE,
        use_layout_analysis: bool = True,
    ):
        self.language = language
        self.render_scale = render_scale
        self.use_layout_analysis = use_layout_analysis
        self._ocr_client = None
        self._structure_client = None
        self._structure_client_unavailable = False

    def extract(self, document: Document) -> TextExtractionResult:
        file_path = self._get_file_path(document)
        extension = self._get_extension(document, file_path)
        start_time = perf_counter()

        if extension in self.PDF_EXTENSIONS:
            page_results = self._extract_pdf(file_path)
            page_count = len(page_results)
        elif extension in self.IMAGE_EXTENSIONS:
            page_results = [self._extract_image(file_path, page_number=1)]
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
            structured_output=self._build_document_output(
                extension,
                page_results,
            ),
        )

    def _extract_pdf(self, file_path: Path) -> List[OCRPageText]:
        return self.extract_pdf_pages(file_path)

    def extract_pdf_pages(
        self,
        file_path: Path,
        page_numbers: Optional[Sequence[int]] = None,
    ) -> List[OCRPageText]:
        try:
            import fitz
        except ImportError as exc:
            raise PaddleOCRExtractionError(
                "PyMuPDF is required to render scanned PDFs for PaddleOCR."
            ) from exc

        page_results = []

        try:
            with fitz.open(file_path) as pdf_document:
                target_page_numbers = self._normalize_pdf_page_numbers(
                    page_numbers,
                    pdf_document.page_count,
                )
                with TemporaryDirectory(
                    prefix="paddleocr_pages_",
                    dir=str(file_path.parent),
                ) as temp_dir:
                    temp_path = Path(temp_dir)

                    for page_number in target_page_numbers:
                        page_index = page_number - 1
                        page = pdf_document.load_page(page_index)
                        image_path = self._render_pdf_page(
                            page,
                            temp_path,
                            page_index,
                        )
                        page_results.append(
                            self._extract_image(
                                image_path,
                                page_number=page_number,
                            )
                        )

        except Exception as exc:
            raise PaddleOCRExtractionError(
                f"Failed to extract scanned PDF text: {file_path}"
            ) from exc

        return page_results

    @staticmethod
    def _normalize_pdf_page_numbers(
        page_numbers: Optional[Sequence[int]],
        page_count: int,
    ) -> Tuple[int, ...]:
        if page_numbers is None:
            return tuple(range(1, page_count + 1))

        normalized = sorted({int(page_number) for page_number in page_numbers})
        return tuple(
            page_number
            for page_number in normalized
            if 1 <= page_number <= page_count
        )

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

    def _extract_image(
        self,
        file_path: Path,
        page_number: int,
    ) -> OCRPageText:
        raw_result = self._run_paddle_ocr(file_path)
        lines = self._extract_ocr_lines(raw_result)
        layout_result = self._run_layout_analysis(file_path)
        page_size = self._get_image_size(file_path)
        page_output = self._build_page_output(
            page_number=page_number,
            file_path=file_path,
            lines=lines,
            layout_result=layout_result,
            page_size=page_size,
        )
        confidence_scores = tuple(
            line.confidence_score
            for line in lines
        )

        return OCRPageText(
            text=str(page_output.get("text") or "").strip(),
            confidence_scores=confidence_scores,
            structured_output=page_output,
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

    def _run_layout_analysis(self, file_path: Path) -> Any:
        structure_client = self._get_structure_client()
        if structure_client is None:
            return None

        try:
            if hasattr(structure_client, "predict"):
                return structure_client.predict(str(file_path))
            if callable(structure_client):
                return structure_client(str(file_path))
            if hasattr(structure_client, "structure"):
                return structure_client.structure(str(file_path))
        except Exception:
            self._structure_client_unavailable = True
            return None

        return None

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

    def _get_structure_client(self):
        if not self.use_layout_analysis:
            return None
        if self._structure_client is not None:
            return self._structure_client
        if self._structure_client_unavailable:
            return None

        self._configure_paddle_runtime()

        try:
            import paddleocr
        except ImportError:
            self._structure_client_unavailable = True
            return None

        for class_name in ("PPStructure", "PPStructureV3"):
            structure_class = getattr(paddleocr, class_name, None)
            if structure_class is None:
                continue

            structure_client = self._build_structure_client(
                structure_class,
            )
            if structure_client is not None:
                self._structure_client = structure_client
                return self._structure_client

        self._structure_client_unavailable = True
        return None

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

    def _build_structure_client(self, structure_class):
        constructor_options = (
            {
                "lang": self.language,
                "device": "cpu",
                "enable_mkldnn": False,
                "show_log": False,
                "table": True,
                "ocr": True,
            },
            {
                "lang": self.language,
                "show_log": False,
                "table": True,
                "ocr": True,
            },
            {
                "lang": self.language,
                "show_log": False,
            },
            {
                "lang": self.language,
            },
            {},
        )

        for options in constructor_options:
            try:
                return structure_class(**options)
            except Exception:
                continue

        return None

    def _extract_text_lines(self, raw_result: Any) -> List[Tuple[str, float]]:
        return [
            (line.text, line.confidence_score)
            for line in self._extract_ocr_lines(raw_result)
        ]

    def _collect_text_lines(
        self,
        value: Any,
        lines: List[Tuple[str, float]],
    ) -> None:
        for line in self._extract_ocr_lines(value):
            lines.append((line.text, line.confidence_score))

    def _collect_dict_text_lines(
        self,
        value: dict,
        lines: List[Tuple[str, float]],
    ) -> None:
        self._collect_text_lines(value, lines)

    def _extract_ocr_lines(self, raw_result: Any) -> List[OCRTextLine]:
        lines: List[OCRTextLine] = []
        self._collect_ocr_lines(raw_result, lines)
        return lines

    def _collect_ocr_lines(
        self,
        value: Any,
        lines: List[OCRTextLine],
    ) -> None:
        value = self._coerce_result_value(value)

        if value is None:
            return

        if isinstance(value, dict):
            if self._collect_dict_ocr_lines(value, lines):
                return
            for item in value.values():
                self._collect_ocr_lines(item, lines)
            return

        if self._is_legacy_text_line(value):
            text, score = value[1][0], value[1][1]
            normalized_text = self._normalize_text(text)
            if normalized_text:
                lines.append(
                    OCRTextLine(
                        text=normalized_text,
                        confidence_score=self._normalize_score(score),
                        bbox=self._normalize_bbox(value[0]),
                    )
                )
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                self._collect_ocr_lines(item, lines)

    def _collect_dict_ocr_lines(
        self,
        value: dict,
        lines: List[OCRTextLine],
    ) -> bool:
        rec_texts = value.get("rec_texts")
        rec_scores = value.get("rec_scores") or value.get("scores") or []
        indexed_boxes = self._get_indexed_boxes(value)

        if isinstance(rec_texts, list):
            for index, text in enumerate(rec_texts):
                normalized_text = self._normalize_text(text)
                if not normalized_text:
                    continue

                score = 0.0
                bbox = None
                if index < len(rec_scores):
                    score = self._normalize_score(rec_scores[index])
                if index < len(indexed_boxes):
                    bbox = self._normalize_bbox(indexed_boxes[index])

                lines.append(
                    OCRTextLine(
                        text=normalized_text,
                        confidence_score=score,
                        bbox=bbox,
                    )
                )
            return True

        text = self._get_first_string(
            value,
            ("text", "rec_text", "recognized_text", "transcription"),
        )
        if text:
            score = self._get_first_value(
                value,
                ("confidence", "score", "rec_score"),
            )
            bbox = self._get_first_value(
                value,
                (
                    "bbox",
                    "box",
                    "text_region",
                    "poly",
                    "points",
                ),
            )
            lines.append(
                OCRTextLine(
                    text=text,
                    confidence_score=self._normalize_score(score),
                    bbox=self._normalize_bbox(bbox),
                )
            )
            return True

        return False

    @staticmethod
    def _coerce_result_value(value: Any) -> Any:
        if value is None or isinstance(value, (dict, list, tuple, str)):
            return value
        if hasattr(value, "tolist"):
            try:
                return value.tolist()
            except Exception:
                return value
        for attribute_name in ("res", "result"):
            if hasattr(value, attribute_name):
                try:
                    return getattr(value, attribute_name)
                except Exception:
                    pass
        for method_name in ("to_dict", "dict"):
            method = getattr(value, method_name, None)
            if callable(method):
                try:
                    return method()
                except Exception:
                    pass
        if hasattr(value, "__dict__"):
            try:
                return vars(value)
            except Exception:
                return value
        return value

    def _build_page_output(
        self,
        page_number: int,
        file_path: Path,
        lines: List[OCRTextLine],
        layout_result: Any,
        page_size: Tuple[float, float],
    ) -> Dict[str, Any]:
        structure_blocks = self._extract_structure_blocks(layout_result)

        if structure_blocks:
            sorted_blocks = self._sort_blocks_reading_order(
                structure_blocks,
            )
            text = self._format_blocks_text(sorted_blocks)
            if not text:
                text = self._format_coordinate_text(lines, page_size)

            return {
                "page_number": page_number,
                "image_name": file_path.name,
                "width": page_size[0],
                "height": page_size[1],
                "layout_source": "pp_structure",
                "layout_analysis_used": True,
                "text": text,
                "blocks": sorted_blocks,
                "lines": [self._line_to_dict(line) for line in lines],
            }

        coordinate_blocks = self._build_coordinate_blocks(lines, page_size)
        return {
            "page_number": page_number,
            "image_name": file_path.name,
            "width": page_size[0],
            "height": page_size[1],
            "layout_source": "ocr_bounding_boxes",
            "layout_analysis_used": False,
            "text": self._format_blocks_text(coordinate_blocks),
            "blocks": coordinate_blocks,
            "lines": [self._line_to_dict(line) for line in lines],
        }

    def _extract_structure_blocks(
        self,
        layout_result: Any,
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        self._collect_structure_blocks(layout_result, blocks)
        return blocks

    def _collect_structure_blocks(
        self,
        value: Any,
        blocks: List[Dict[str, Any]],
    ) -> None:
        value = self._coerce_result_value(value)
        if value is None:
            return

        if isinstance(value, dict):
            if self._is_structure_block(value):
                block = self._build_structure_block(value)
                if block is not None:
                    blocks.append(block)
                return
            for item in value.values():
                self._collect_structure_blocks(item, blocks)
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                self._collect_structure_blocks(item, blocks)

    @staticmethod
    def _is_structure_block(value: dict) -> bool:
        block_type = value.get("type") or value.get("label")
        if not isinstance(block_type, str):
            return False
        return any(
            key in value
            for key in (
                "bbox",
                "box",
                "layout_bbox",
                "res",
                "result",
                "html",
            )
        )

    def _build_structure_block(
        self,
        value: dict,
    ) -> Optional[Dict[str, Any]]:
        block_type = self._normalize_block_type(
            value.get("type")
            or value.get("label")
            or "text",
        )
        html_content = self._find_first_string_value(
            value,
            ("html", "html_content", "table_html"),
        )
        table_rows = self._parse_html_table(html_content)
        block_lines = self._extract_ocr_lines(
            value.get("res") or value.get("result") or value,
        )
        bbox = self._normalize_bbox(
            self._get_first_value(
                value,
                ("bbox", "box", "layout_bbox", "region"),
            )
        ) or self._bbox_for_lines(block_lines)
        text = self._build_structure_block_text(
            value=value,
            block_lines=block_lines,
            table_rows=table_rows,
        )

        if not text and not block_lines and not table_rows:
            return None

        block: Dict[str, Any] = {
            "block_type": block_type,
            "bbox": self._bbox_to_list(bbox),
            "text": text,
            "lines": [self._line_to_dict(line) for line in block_lines],
            "source": "pp_structure",
        }
        if table_rows:
            block["table"] = {
                "rows": table_rows,
                "html": html_content,
            }
        return block

    def _build_structure_block_text(
        self,
        value: dict,
        block_lines: List[OCRTextLine],
        table_rows: List[List[str]],
    ) -> str:
        if table_rows:
            return self._format_table_rows(table_rows)
        if block_lines:
            return self._format_coordinate_text(
                block_lines,
                page_size=(0.0, 0.0),
            )
        for key in ("text", "content", "markdown", "plain_text"):
            text = self._normalize_text(value.get(key))
            if text:
                return text
        return ""

    def _build_coordinate_blocks(
        self,
        lines: List[OCRTextLine],
        page_size: Tuple[float, float],
    ) -> List[Dict[str, Any]]:
        if not lines:
            return []

        positioned_lines = [line for line in lines if line.bbox]
        unpositioned_lines = [line for line in lines if not line.bbox]

        if not positioned_lines:
            text = "\n".join(line.text for line in lines).strip()
            return [
                {
                    "block_type": "text",
                    "bbox": None,
                    "text": text,
                    "lines": [self._line_to_dict(line) for line in lines],
                    "source": "ocr_text_order",
                }
            ]
        rows = self._group_lines_by_visual_rows(positioned_lines)
        row_groups = self._group_rows_into_blocks(rows)
        blocks = []

        for row_group in row_groups:
            blocks.extend(
                self._build_blocks_for_row_group(
                    row_group,
                    page_size[0],
                )
            )

        if unpositioned_lines:
            text = "\n".join(
                line.text
                for line in unpositioned_lines
            ).strip()
            blocks.append(
                {
                    "block_type": "text",
                    "bbox": None,
                    "text": text,
                    "lines": [
                        self._line_to_dict(line)
                        for line in unpositioned_lines
                    ],
                    "source": "ocr_text_order",
                }
            )

        return blocks

    def _build_blocks_for_row_group(
        self,
        row_group: List[List[OCRTextLine]],
        page_width: float,
    ) -> List[Dict[str, Any]]:
        blocks = []

        for block_type, rows in self._split_table_segments(row_group):
            group_lines = [line for row in rows for line in row]
            if block_type in {"table", "delimited_table"}:
                if block_type == "delimited_table":
                    table_block = self._build_delimited_table_block(rows)
                else:
                    table_block = self._build_table_block(rows)
                if table_block is not None:
                    blocks.append(table_block)
                    continue

            text = "\n".join(
                self._format_visual_row(row, page_width)
                for row in rows
            ).strip()
            if not text:
                continue
            blocks.append(
                {
                    "block_type": "text",
                    "bbox": self._bbox_to_list(
                        self._bbox_for_lines(group_lines),
                    ),
                    "text": text,
                    "lines": [
                        self._line_to_dict(line)
                        for line in group_lines
                    ],
                    "source": "ocr_bounding_boxes",
                }
            )

        return blocks

    def _split_table_segments(
        self,
        row_group: List[List[OCRTextLine]],
    ) -> List[Tuple[str, List[List[OCRTextLine]]]]:
        segments: List[Tuple[str, List[List[OCRTextLine]]]] = []
        text_start = 0
        row_index = 0

        while row_index < len(row_group):
            if self._is_delimited_table_header(row_group[row_index]):
                candidate_end = row_index + 1
                while candidate_end < len(row_group):
                    if self._is_section_heading_row(
                        row_group[candidate_end],
                    ):
                        break
                    candidate_end += 1

                candidate = row_group[row_index:candidate_end]
                if self._parse_delimited_table_rows(candidate):
                    if text_start < row_index:
                        segments.append(
                            ("text", row_group[text_start:row_index])
                        )
                    segments.append(("delimited_table", candidate))
                    row_index = candidate_end
                    text_start = candidate_end
                    continue

            header = sorted(
                row_group[row_index],
                key=lambda line: line.left,
            )
            if len(header) < 2:
                row_index += 1
                continue

            column_lefts = [line.left for line in header]
            candidate_end = row_index + 1
            tolerance = max(
                self._median_line_height(
                    [
                        line
                        for row in row_group[row_index:]
                        for line in row
                    ]
                ) * 1.5,
                12.0,
            )

            while candidate_end < len(row_group):
                candidate_row = row_group[candidate_end]
                if self._is_section_heading_row(
                    candidate_row,
                    column_lefts,
                ):
                    break
                if not all(
                    min(abs(line.left - left) for left in column_lefts)
                    <= tolerance
                    for line in candidate_row
                ):
                    break
                candidate_end += 1

            candidate = row_group[row_index:candidate_end]
            if self._infer_block_type(candidate) != "table":
                row_index += 1
                continue

            if text_start < row_index:
                segments.append(
                    ("text", row_group[text_start:row_index])
                )
            segments.append(("table", candidate))
            row_index = candidate_end
            text_start = candidate_end

        if text_start < len(row_group):
            segments.append(("text", row_group[text_start:]))

        return segments

    @staticmethod
    def _is_delimited_table_header(
        row: List[OCRTextLine],
    ) -> bool:
        if len(row) != 1:
            return False
        text = row[0].text.strip()
        parts = [part.strip() for part in text.split("|")]
        letters = [character for character in text if character.isalpha()]
        return (
            len(parts) >= 3
            and all(parts)
            and bool(letters)
            and text == text.upper()
        )

    def _is_section_heading_row(
        self,
        row: List[OCRTextLine],
        column_lefts: Optional[List[float]] = None,
    ) -> bool:
        if len(row) != 1:
            return False
        line = row[0]
        letters = [
            character for character in line.text
            if character.isalpha()
        ]
        if not letters or line.text != line.text.upper():
            return False
        if column_lefts is None or len(column_lefts) < 2:
            return "|" not in line.text
        tolerance = max(line.height * 1.5, 12.0)
        return (
            line.left <= column_lefts[0] + tolerance
            and line.right >= column_lefts[1]
        )

    def _build_table_block(
        self,
        rows: List[List[OCRTextLine]],
    ) -> Optional[Dict[str, Any]]:
        if self._infer_block_type(rows) != "table":
            return None

        header = sorted(rows[0], key=lambda line: line.left)
        column_lefts = [line.left for line in header]
        column_count = len(column_lefts)
        data_by_column: List[List[OCRTextLine]] = [
            [] for _ in range(column_count)
        ]

        for row in rows[1:]:
            for line in sorted(row, key=lambda item: item.left):
                column_index = min(
                    range(column_count),
                    key=lambda index: abs(
                        line.left - column_lefts[index]
                    ),
                )
                data_by_column[column_index].append(line)

        wrap_gap = max(
            self._median_line_height(
                [line for row in rows for line in row]
            ) * 0.25,
            4.0,
        )
        anchor_column_index = 0
        if not data_by_column[anchor_column_index]:
            anchor_column_index = max(
                range(column_count),
                key=lambda index: len(data_by_column[index]),
            )
        anchor_groups = self._group_cell_fragments(
            data_by_column[anchor_column_index],
            wrap_gap,
        )
        if not anchor_groups:
            return None

        anchor_centers = [
            (
                min(line.top for line in group)
                + max(line.bottom for line in group)
            ) / 2
            for group in anchor_groups
        ]
        table_rows = [[line.text for line in header]]
        table_rows.extend(
            [[""] * column_count for _ in anchor_groups]
        )
        cells = []
        cell_lines: Dict[Tuple[int, int], List[OCRTextLine]] = {}

        for column_index, line in enumerate(header):
            cells.append(
                self._coordinate_cell(
                    [line],
                    row_index=0,
                    column_index=column_index,
                )
            )

        for data_row_index, group in enumerate(anchor_groups):
            cell_lines[(data_row_index + 1, anchor_column_index)] = list(
                group
            )

        for column_index, column_lines in enumerate(data_by_column):
            if column_index == anchor_column_index:
                continue
            for line in column_lines:
                line_center = (line.top + line.bottom) / 2
                data_row_index = min(
                    range(len(anchor_centers)),
                    key=lambda index: abs(
                        line_center - anchor_centers[index]
                    ),
                )
                cell_lines.setdefault(
                    (data_row_index + 1, column_index),
                    [],
                ).append(line)

        for (row_index, column_index), fragments in sorted(
            cell_lines.items(),
        ):
            cell = self._coordinate_cell(
                fragments,
                row_index=row_index,
                column_index=column_index,
            )
            table_rows[row_index][column_index] = cell["text"]
            cells.append(cell)

        markdown = self._format_markdown_table(table_rows)
        html = self._format_html_table(table_rows)
        group_lines = [line for row in rows for line in row]
        columns = []
        for column_index in range(column_count):
            column_lines = [header[column_index]]
            column_lines.extend(data_by_column[column_index])
            columns.append(
                {
                    "column_index": column_index,
                    "bbox": self._bbox_to_list(
                        self._bbox_for_lines(column_lines)
                    ),
                }
            )

        return {
            "block_type": "table",
            "bbox": self._bbox_to_list(
                self._bbox_for_lines(group_lines),
            ),
            "text": markdown,
            "lines": [
                self._line_to_dict(line) for line in group_lines
            ],
            "source": "ocr_bounding_boxes",
            "table": {
                "rows": table_rows,
                "cells": cells,
                "columns": columns,
                "markdown": markdown,
                "html": html,
            },
        }

    @staticmethod
    def _group_cell_fragments(
        lines: List[OCRTextLine],
        wrap_gap: float,
    ) -> List[List[OCRTextLine]]:
        groups: List[List[OCRTextLine]] = []
        for line in sorted(lines, key=lambda item: (item.top, item.left)):
            if not groups:
                groups.append([line])
                continue
            previous_bottom = max(item.bottom for item in groups[-1])
            if line.top - previous_bottom <= wrap_gap:
                groups[-1].append(line)
            else:
                groups.append([line])
        return groups

    def _parse_delimited_table_rows(
        self,
        rows: List[List[OCRTextLine]],
    ) -> List[List[str]]:
        if not rows or not self._is_delimited_table_header(rows[0]):
            return []
        header_line = rows[0][0]
        header = [
            self._normalize_text(part)
            for part in header_line.text.split("|")
        ]
        if len(header) != 3 or not all(header):
            return []

        body_text = self._normalize_text(
            " ".join(
                line.text
                for row in rows[1:]
                for line in row
            )
        )
        tokens = [
            self._normalize_text(part)
            for part in body_text.split("|")
        ]
        if len(tokens) < 3:
            return []
        if re.match(r"^[-–—_]", tokens[0]):
            tokens[0] = re.sub(
                r"^[\s\-–—_I]+",
                "",
                tokens[0],
            )

        data_rows = []
        question = tokens[0]
        token_index = 1
        while question and token_index + 1 < len(tokens):
            answer = tokens[token_index]
            matter, next_question = self._split_trailing_question(
                tokens[token_index + 1]
            )
            if not answer or not matter:
                return []
            data_rows.append([question, answer, matter])
            token_index += 2
            if next_question is None:
                break
            question = next_question

        if token_index < len(tokens) and next_question is not None:
            return []
        return [header, *data_rows] if data_rows else []

    @staticmethod
    def _split_trailing_question(
        text: str,
    ) -> Tuple[str, Optional[str]]:
        split_positions = []
        for match in re.finditer(r"\s+(?=[A-Z])", text):
            suffix = text[match.end():].strip()
            if suffix.endswith("?") and suffix.count("?") == 1:
                split_positions.append(match.start())
        if not split_positions:
            return text.strip(), None
        split_at = split_positions[-1]
        return text[:split_at].strip(), text[split_at:].strip()

    def _build_delimited_table_block(
        self,
        rows: List[List[OCRTextLine]],
    ) -> Optional[Dict[str, Any]]:
        table_rows = self._parse_delimited_table_rows(rows)
        if not table_rows:
            return None

        header_line = rows[0][0]
        group_lines = [line for row in rows for line in row]
        block_bbox = self._bbox_for_lines(group_lines)
        if block_bbox is None or header_line.bbox is None:
            return None

        raw_header = header_line.text
        pipe_positions = [
            index for index, character in enumerate(raw_header)
            if character == "|"
        ]
        text_length = max(len(raw_header), 1)
        column_edges = [header_line.left]
        column_edges.extend(
            header_line.left
            + (header_line.right - header_line.left)
            * ((position + 0.5) / text_length)
            for position in pipe_positions
        )
        column_edges.append(header_line.right)

        data_top = min(
            line.top for row in rows[1:] for line in row
        )
        data_bottom = max(
            line.bottom for row in rows[1:] for line in row
        )
        data_row_count = len(table_rows) - 1
        data_row_height = (data_bottom - data_top) / data_row_count
        cells = []
        for row_index, table_row in enumerate(table_rows):
            if row_index == 0:
                row_top = header_line.top
                row_bottom = header_line.bottom
            else:
                row_top = data_top + data_row_height * (row_index - 1)
                row_bottom = data_top + data_row_height * row_index
            for column_index, text in enumerate(table_row):
                cells.append(
                    {
                        "text": text,
                        "row_index": row_index,
                        "column_index": column_index,
                        "bbox": self._bbox_to_list(
                            (
                                column_edges[column_index],
                                row_top,
                                column_edges[column_index + 1],
                                row_bottom,
                            )
                        ),
                        "rowspan": 1,
                        "colspan": 1,
                    }
                )

        markdown = self._format_markdown_table(table_rows)
        html = self._format_html_table(table_rows)
        columns = [
            {
                "column_index": column_index,
                "bbox": self._bbox_to_list(
                    (
                        column_edges[column_index],
                        block_bbox[1],
                        column_edges[column_index + 1],
                        block_bbox[3],
                    )
                ),
            }
            for column_index in range(len(table_rows[0]))
        ]
        return {
            "block_type": "table",
            "bbox": self._bbox_to_list(block_bbox),
            "text": markdown,
            "lines": [
                self._line_to_dict(line) for line in group_lines
            ],
            "source": "ocr_bounding_boxes",
            "table": {
                "rows": table_rows,
                "cells": cells,
                "columns": columns,
                "markdown": markdown,
                "html": html,
            },
        }

    def _coordinate_cell(
        self,
        lines: List[OCRTextLine],
        row_index: int,
        column_index: int,
    ) -> Dict[str, Any]:
        ordered_lines = sorted(
            lines,
            key=lambda line: (line.top, line.left),
        )
        return {
            "text": " ".join(line.text for line in ordered_lines),
            "row_index": row_index,
            "column_index": column_index,
            "bbox": self._bbox_to_list(
                self._bbox_for_lines(ordered_lines)
            ),
            "rowspan": 1,
            "colspan": 1,
        }

    @staticmethod
    def _format_markdown_table(table_rows: List[List[str]]) -> str:
        def format_row(row: List[str]) -> str:
            cells = [cell.replace("|", "\\|").strip() for cell in row]
            return f"| {' | '.join(cells)} |"

        header = format_row(table_rows[0])
        separator = "|" + "---|" * len(table_rows[0])
        data_rows = [format_row(row) for row in table_rows[1:]]
        return "\n".join([header, separator, *data_rows])

    @staticmethod
    def _format_html_table(table_rows: List[List[str]]) -> str:
        header = "".join(
            f"<th>{escape(cell)}</th>" for cell in table_rows[0]
        )
        body = "".join(
            "<tr>"
            + "".join(f"<td>{escape(cell)}</td>" for cell in row)
            + "</tr>"
            for row in table_rows[1:]
        )
        return (
            f"<table><thead><tr>{header}</tr></thead>"
            f"<tbody>{body}</tbody></table>"
        )

    def _format_coordinate_text(
        self,
        lines: List[OCRTextLine],
        page_size: Tuple[float, float],
    ) -> str:
        return self._format_blocks_text(
            self._build_coordinate_blocks(lines, page_size),
        )

    def _group_lines_by_visual_rows(
        self,
        lines: List[OCRTextLine],
    ) -> List[List[OCRTextLine]]:
        sorted_lines = sorted(lines, key=lambda line: (line.top, line.left))
        median_height = self._median_line_height(sorted_lines)
        tolerance = max(
            median_height * self.ROW_TOLERANCE_MULTIPLIER,
            4.0,
        )
        rows: List[List[OCRTextLine]] = []

        for line in sorted_lines:
            if not rows:
                rows.append([line])
                continue

            current_row = rows[-1]
            current_center_y = sum(
                row_line.center_y
                for row_line in current_row
            ) / len(current_row)

            if abs(line.center_y - current_center_y) <= tolerance:
                current_row.append(line)
                current_row.sort(key=lambda row_line: row_line.left)
                continue

            rows.append([line])

        return rows

    def _group_rows_into_blocks(
        self,
        rows: List[List[OCRTextLine]],
    ) -> List[List[List[OCRTextLine]]]:
        if not rows:
            return []

        median_height = self._median_line_height(
            [line for row in rows for line in row],
        )
        gap_threshold = max(
            median_height * self.BLOCK_GAP_MULTIPLIER,
            12.0,
        )
        groups: List[List[List[OCRTextLine]]] = [[rows[0]]]

        for row in rows[1:]:
            previous_row = groups[-1][-1]
            previous_bottom = max(line.bottom for line in previous_row)
            row_top = min(line.top for line in row)

            if row_top - previous_bottom > gap_threshold:
                groups.append([row])
            else:
                groups[-1].append(row)

        return groups

    def _format_visual_row(
        self,
        row: List[OCRTextLine],
        page_width: float,
    ) -> str:
        sorted_row = sorted(row, key=lambda line: line.left)
        if not sorted_row:
            return ""

        formatted_parts = [sorted_row[0].text]
        previous_right = sorted_row[0].right
        median_height = self._median_line_height(sorted_row)

        for line in sorted_row[1:]:
            gap = line.left - previous_right
            large_gap_threshold = max(
                median_height * 2.5,
                page_width * 0.025 if page_width else 12.0,
            )
            separator = "\t" if gap > large_gap_threshold else " "
            formatted_parts.append(f"{separator}{line.text}")
            previous_right = max(previous_right, line.right)

        return "".join(formatted_parts).strip()

    def _infer_block_type(
        self,
        row_group: List[List[OCRTextLine]],
    ) -> str:
        if len(row_group) < 2 or len(row_group[0]) < 2:
            return "text"

        header = sorted(row_group[0], key=lambda line: line.left)
        column_lefts = [line.left for line in header]
        tolerance = max(
            self._median_line_height(
                [line for row in row_group for line in row]
            ) * 1.5,
            12.0,
        )
        matched_columns = {
            min(
                range(len(column_lefts)),
                key=lambda index: abs(
                    line.left - column_lefts[index]
                ),
            )
            for row in row_group[1:]
            for line in row
            if min(abs(line.left - left) for left in column_lefts)
            <= tolerance
        }
        if len(matched_columns) >= 2:
            return "table"
        return "text"

    @staticmethod
    def _sort_blocks_reading_order(
        blocks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return sorted(
            blocks,
            key=lambda block: (
                (block.get("bbox") or [0, 0, 0, 0])[1],
                (block.get("bbox") or [0, 0, 0, 0])[0],
            ),
        )

    @staticmethod
    def _format_blocks_text(blocks: List[Dict[str, Any]]) -> str:
        return "\n\n".join(
            str(block.get("text") or "").strip()
            for block in blocks
            if str(block.get("text") or "").strip()
        ).strip()

    @staticmethod
    def _format_table_rows(table_rows: List[List[str]]) -> str:
        return "\n".join(
            "\t".join(cell.strip() for cell in row)
            for row in table_rows
            if any(cell.strip() for cell in row)
        ).strip()

    @staticmethod
    def _parse_html_table(html_content: Optional[str]) -> List[List[str]]:
        if not html_content:
            return []

        parser = _HTMLTableParser()
        parser.feed(html_content)
        parser.close()
        return parser.rows

    def _build_document_output(
        self,
        extension: str,
        page_results: List[OCRPageText],
    ) -> Dict[str, Any]:
        layout_sources = sorted(
            {
                page.structured_output.get("layout_source")
                for page in page_results
                if page.structured_output.get("layout_source")
            }
        )
        return {
            "schema_version": self.STRUCTURED_OUTPUT_VERSION,
            "engine": "PADDLEOCR",
            "source_extension": extension,
            "page_count": len(page_results),
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
    def _get_image_size(file_path: Path) -> Tuple[float, float]:
        try:
            from PIL import Image

            with Image.open(file_path) as image:
                return float(image.width), float(image.height)
        except Exception:
            return 0.0, 0.0

    @staticmethod
    def _get_indexed_boxes(value: dict) -> Sequence[Any]:
        for key in (
            "rec_polys",
            "rec_boxes",
            "dt_polys",
            "dt_boxes",
            "boxes",
            "polys",
            "text_regions",
        ):
            boxes = value.get(key)
            if boxes is None:
                continue
            if hasattr(boxes, "tolist"):
                try:
                    boxes = boxes.tolist()
                except Exception:
                    pass
            if isinstance(boxes, (list, tuple)):
                return boxes
        return []

    @staticmethod
    def _normalize_block_type(block_type: Any) -> str:
        normalized_type = str(block_type or "text").strip().lower()
        if normalized_type in {"table", "figure", "title", "list"}:
            return normalized_type
        if "table" in normalized_type:
            return "table"
        if "title" in normalized_type or "header" in normalized_type:
            return "title"
        return "text"

    @staticmethod
    def _get_first_string(value: dict, keys: Sequence[str]) -> str:
        for key in keys:
            normalized_text = PaddleOCRExtractionService._normalize_text(
                value.get(key),
            )
            if normalized_text:
                return normalized_text
        return ""

    @staticmethod
    def _get_first_value(value: dict, keys: Sequence[str]) -> Any:
        for key in keys:
            if key in value and value.get(key) is not None:
                return value.get(key)
        return None

    def _find_first_string_value(
        self,
        value: Any,
        keys: Sequence[str],
    ) -> Optional[str]:
        value = self._coerce_result_value(value)
        if isinstance(value, dict):
            for key in keys:
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate
            for item in value.values():
                candidate = self._find_first_string_value(item, keys)
                if candidate:
                    return candidate
        if isinstance(value, (list, tuple)):
            for item in value:
                candidate = self._find_first_string_value(item, keys)
                if candidate:
                    return candidate
        return None

    @staticmethod
    def _bbox_for_lines(lines: List[OCRTextLine]) -> Optional[BoundingBox]:
        positioned_lines = [line for line in lines if line.bbox]
        if not positioned_lines:
            return None
        return (
            min(line.left for line in positioned_lines),
            min(line.top for line in positioned_lines),
            max(line.right for line in positioned_lines),
            max(line.bottom for line in positioned_lines),
        )

    @staticmethod
    def _bbox_to_list(bbox: Optional[BoundingBox]) -> Optional[List[float]]:
        if bbox is None:
            return None
        return [round(float(value), 2) for value in bbox]

    @staticmethod
    def _line_to_dict(line: OCRTextLine) -> Dict[str, Any]:
        return {
            "text": line.text,
            "confidence_score": line.confidence_score,
            "bbox": PaddleOCRExtractionService._bbox_to_list(line.bbox),
        }

    @staticmethod
    def _median_line_height(lines: List[OCRTextLine]) -> float:
        heights = sorted(
            line.height
            for line in lines
            if line.height > 0
        )
        if not heights:
            return 12.0

        middle = len(heights) // 2
        if len(heights) % 2:
            return heights[middle]
        return (heights[middle - 1] + heights[middle]) / 2

    @staticmethod
    def _normalize_bbox(value: Any) -> Optional[BoundingBox]:
        if value is None:
            return None
        if hasattr(value, "tolist"):
            try:
                value = value.tolist()
            except Exception:
                pass

        numbers = PaddleOCRExtractionService._flatten_numbers(value)
        if len(numbers) < 4:
            return None

        if len(numbers) == 4:
            left, top, right, bottom = numbers
            if right < left:
                left, right = right, left
            if bottom < top:
                top, bottom = bottom, top
            return left, top, right, bottom

        points = list(zip(numbers[0::2], numbers[1::2]))
        if not points:
            return None

        x_values = [point[0] for point in points]
        y_values = [point[1] for point in points]
        return (
            min(x_values),
            min(y_values),
            max(x_values),
            max(y_values),
        )

    @staticmethod
    def _flatten_numbers(value: Any) -> List[float]:
        if value is None or isinstance(value, (str, bytes)):
            return []
        if isinstance(value, (int, float)):
            return [float(value)]
        if isinstance(value, dict):
            numbers = []
            for item in value.values():
                numbers.extend(
                    PaddleOCRExtractionService._flatten_numbers(item),
                )
            return numbers
        if hasattr(value, "tolist"):
            try:
                value = value.tolist()
            except Exception:
                pass
        if isinstance(value, (list, tuple)):
            numbers = []
            for item in value:
                numbers.extend(
                    PaddleOCRExtractionService._flatten_numbers(item),
                )
            return numbers
        return []

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
    def _normalize_text(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return " ".join(value.strip().split())

    @staticmethod
    def _merge_page_text(page_results: List[OCRPageText]) -> str:
        return PaddleOCRExtractionService.PAGE_BREAK.join(
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
