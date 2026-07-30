from uuid import uuid4

import pytest

from database.models import Document
from modules.extraction.mixed_pdf import MixedPDFExtractionService
from modules.extraction.ocr import OCRDecisionEngine, OCREngine
from modules.extraction.paddle import OCRPageText


def create_pdf_document(file_path):
    return Document(
        id=str(uuid4()),
        filename=file_path.name,
        stored_filename=file_path.name,
        file_type="application/pdf",
        file_size=100,
        storage_path=str(file_path),
        status="PENDING",
    )


def write_pdf(file_path, page_texts):
    fitz = pytest.importorskip("fitz")
    pdf_document = fitz.open()

    for page_text in page_texts:
        page = pdf_document.new_page()
        if page_text:
            page.insert_text((72, 72), page_text)

    pdf_document.save(file_path)
    pdf_document.close()


class FakePaddleOCRExtractor:
    def __init__(self):
        self.calls = []

    def extract_pdf_pages(self, file_path, page_numbers=None):
        self.calls.append((file_path, tuple(page_numbers or [])))
        return [
            OCRPageText(
                text=f"OCR text for page {page_number}",
                confidence_scores=(0.82,),
                structured_output={
                    "page_number": page_number,
                    "layout_source": "ocr_bounding_boxes",
                    "layout_analysis_used": False,
                    "text": f"OCR text for page {page_number}",
                    "blocks": [],
                    "lines": [],
                },
            )
            for page_number in page_numbers
        ]


def test_ocr_decision_detects_mixed_pdf_pages(tmp_path):
    pdf_path = tmp_path / "mixed.pdf"
    write_pdf(
        pdf_path,
        [
            "Native searchable invoice text",
            "",
            "Native searchable summary text",
        ],
    )

    decision = OCRDecisionEngine().decide(create_pdf_document(pdf_path))

    assert decision.engine == OCREngine.MIXED_PDF
    assert decision.is_searchable is False
    assert [
        (page.page_number, page.is_searchable)
        for page in decision.page_searchability
    ] == [
        (1, True),
        (2, False),
        (3, True),
    ]


def test_mixed_pdf_extractor_ocrs_only_scanned_pages(tmp_path):
    pdf_path = tmp_path / "mixed.pdf"
    write_pdf(
        pdf_path,
        [
            "Native searchable invoice text",
            "",
        ],
    )
    fake_ocr = FakePaddleOCRExtractor()
    extractor = MixedPDFExtractionService(fake_ocr)

    result = extractor.extract(create_pdf_document(pdf_path))

    assert fake_ocr.calls == [(pdf_path, (2,))]
    assert "Native searchable invoice text" in result.extracted_text
    assert "OCR text for page 2" in result.extracted_text
    assert result.page_count == 2
    assert result.confidence_score == pytest.approx(0.91)
    assert result.structured_output["engine"] == "MIXED_PDF"
    assert result.structured_output["searchable_pages"] == [1]
    assert result.structured_output["ocr_pages"] == [2]
    assert (
        result.structured_output["pages"][0]["extraction_source"]
        == "native_pdf"
    )
    assert (
        result.structured_output["pages"][1]["extraction_source"]
        == "paddleocr"
    )
