from uuid import uuid4

import pytest

from database.models import Document
from modules.extraction.paddle import PaddleOCRExtractionService


class FakePaddleOCRExtractionService(PaddleOCRExtractionService):
    def __init__(self, raw_result, layout_result=None):
        super().__init__(use_layout_analysis=True)
        self.raw_result = raw_result
        self.layout_result = layout_result

    def _run_paddle_ocr(self, file_path):
        return self.raw_result

    def _run_layout_analysis(self, file_path):
        return self.layout_result

    def _get_image_size(self, file_path):
        return 400.0, 300.0


def create_image_document(file_path):
    return Document(
        id=str(uuid4()),
        filename=file_path.name,
        stored_filename=file_path.name,
        file_type="image/png",
        file_size=100,
        storage_path=str(file_path),
        status="PENDING",
    )


def box(left, top, right, bottom):
    return [
        [left, top],
        [right, top],
        [right, bottom],
        [left, bottom],
    ]


def test_paddleocr_reconstructs_layout_from_ocr_bounding_boxes(tmp_path):
    image_path = tmp_path / "invoice.png"
    image_path.write_bytes(b"fake image bytes")
    raw_result = [
        [box(10, 10, 70, 25), ("Seller", 0.90)],
        [box(220, 10, 290, 25), ("Client", 0.80)],
        [box(10, 60, 50, 75), ("Item", 0.95)],
        [box(150, 60, 180, 75), ("Qty", 0.85)],
        [box(250, 60, 310, 75), ("Total", 0.75)],
        [box(10, 82, 70, 97), ("Widget", 0.90)],
        [box(150, 82, 165, 97), ("2", 0.90)],
        [box(250, 82, 300, 97), ("10.00", 0.90)],
    ]

    result = FakePaddleOCRExtractionService(raw_result).extract(
        create_image_document(image_path),
    )

    assert "Seller\tClient" in result.extracted_text
    assert "Item\tQty\tTotal" in result.extracted_text
    assert result.confidence_score == pytest.approx(0.86875)
    assert result.structured_output["layout_analysis_used"] is False

    page = result.structured_output["pages"][0]
    assert page["layout_source"] == "ocr_bounding_boxes"
    assert page["lines"][0]["bbox"] == [10.0, 10.0, 70.0, 25.0]
    assert any(
        block["block_type"] == "table"
        for block in page["blocks"]
    )


def test_paddleocr_uses_pp_structure_table_when_available(tmp_path):
    image_path = tmp_path / "table.png"
    image_path.write_bytes(b"fake image bytes")
    raw_result = {
        "rec_texts": ["Item", "Total"],
        "rec_scores": [0.70, 0.90],
        "rec_boxes": [[10, 10, 50, 25], [80, 10, 140, 25]],
    }
    layout_result = [
        {
            "type": "table",
            "bbox": [10, 20, 300, 120],
            "res": {
                "html": (
                    "<table><tr><th>Item</th><th>Total</th></tr>"
                    "<tr><td>Widget</td><td>10.00</td></tr></table>"
                ),
            },
        }
    ]

    result = FakePaddleOCRExtractionService(
        raw_result,
        layout_result=layout_result,
    ).extract(create_image_document(image_path))

    assert result.extracted_text == "Item\tTotal\nWidget\t10.00"
    assert result.confidence_score == pytest.approx(0.80)
    assert result.structured_output["layout_analysis_used"] is True

    page = result.structured_output["pages"][0]
    block = page["blocks"][0]
    assert page["layout_source"] == "pp_structure"
    assert block["block_type"] == "table"
    assert block["table"]["rows"] == [
        ["Item", "Total"],
        ["Widget", "10.00"],
    ]
