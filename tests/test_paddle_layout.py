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


class FakePageSizedPaddleOCRExtractionService(
    FakePaddleOCRExtractionService
):
    def __init__(self, raw_result, page_size):
        super().__init__(raw_result)
        self.page_size = page_size

    def _get_image_size(self, file_path):
        return self.page_size


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


def legacy_lines(specs):
    return [
        [box(left, top, right, bottom), (text, score)]
        for text, (left, top, right, bottom), score in specs
    ]


def find_table_blocks(page):
    return [
        block
        for block in page["blocks"]
        if block.get("block_type") == "table"
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
    assert "| Item | Qty | Total |" in result.extracted_text
    assert "| Widget | 2 | 10.00 |" in result.extracted_text
    assert result.confidence_score == pytest.approx(0.86875)
    assert result.structured_output["layout_analysis_used"] is False

    page = result.structured_output["pages"][0]
    assert page["layout_source"] == "ocr_bounding_boxes"
    assert page["lines"][0]["bbox"] == [10.0, 10.0, 70.0, 25.0]
    table_blocks = find_table_blocks(page)
    assert len(table_blocks) == 1
    table_block = table_blocks[0]
    assert table_block["table"]["rows"] == [
        ["Item", "Qty", "Total"],
        ["Widget", "2", "10.00"],
    ]
    assert table_block["table"]["markdown"].startswith("| Item | Qty | Total |")


def test_paddleocr_merges_wrapped_cell_fragments(tmp_path):
    image_path = tmp_path / "wrapped.png"
    image_path.write_bytes(b"fake image bytes")
    raw_result = legacy_lines(
        [
            ("Col A", (10, 10, 80, 25), 0.90),
            ("Col B", (150, 10, 240, 25), 0.90),
            ("$1,500 individual / $3,000", (10, 40, 120, 60), 0.90),
            ("$5,000 individual / $10,000", (150, 40, 260, 60), 0.90),
            ("family", (10, 63, 60, 83), 0.90),
            ("family", (150, 63, 220, 83), 0.90),
        ]
    )

    result = FakePaddleOCRExtractionService(raw_result).extract(
        create_image_document(image_path),
    )

    assert (
        "| $1,500 individual / $3,000 family "
        "| $5,000 individual / $10,000 family |"
        in result.extracted_text
    )
    assert "family\n" not in result.extracted_text

    page = result.structured_output["pages"][0]
    table_block = find_table_blocks(page)[0]
    wrapped_cells = [
        cell
        for cell in table_block["table"]["cells"]
        if cell["text"] == "$1,500 individual / $3,000 family"
    ]
    assert len(wrapped_cells) == 1
    assert wrapped_cells[0]["row_index"] == 1
    assert wrapped_cells[0]["column_index"] == 0
    assert wrapped_cells[0]["bbox"][0] == pytest.approx(10.0)


def test_paddleocr_reconstructs_insurance_coverage_table(tmp_path):
    image_path = tmp_path / "policy.png"
    image_path.write_bytes(b"fake image bytes")
    raw_result = legacy_lines(
        [
            ("COVERAGE SUMMARY", (70, 1204, 388, 1231), 0.99),
            ("IN-NETWORK BENEFITS", (70, 1270, 376, 1294), 0.99),
            ("Service", (80, 1325, 164, 1352), 0.99),
            ("Deductible", (219, 1327, 334, 1350), 0.99),
            ("Coinsurance", (546, 1324, 679, 1351), 0.99),
            ("Out-of-Pocket Maximum", (821, 1328, 1073, 1350), 0.99),
            ("$1,500 individual / $3,000", (222, 1372, 464, 1393), 0.99),
            ("$5,000 individual / $10,000", (822, 1371, 1078, 1394), 0.99),
            ("Medical", (79, 1389, 161, 1417), 0.99),
            ("20% after deductible", (549, 1393, 748, 1414), 0.99),
            ("family", (216, 1409, 283, 1438), 0.99),
            ("family", (817, 1409, 884, 1438), 0.99),
            ("See Prescription", (546, 1453, 706, 1480), 0.99),
            ("Prescription", (82, 1475, 200, 1499), 0.99),
            ("$250 individual / $500 family", (220, 1473, 494, 1499), 0.99),
            ("Included in medical maximum", (821, 1475, 1101, 1498), 0.99),
            ("Coverage", (548, 1496, 642, 1521), 0.99),
        ]
    )

    service = FakePageSizedPaddleOCRExtractionService(
        raw_result,
        (1224.0, 1584.0),
    )
    result = service.extract(create_image_document(image_path))

    assert "COVERAGE SUMMARY\nIN-NETWORK BENEFITS" in result.extracted_text
    assert (
        "| Service | Deductible | Coinsurance | Out-of-Pocket Maximum |\n"
        "|---|---|---|---|\n"
        "| Medical | $1,500 individual / $3,000 family "
        "| 20% after deductible | $5,000 individual / $10,000 family |\n"
        "| Prescription | $250 individual / $500 family "
        "| See Prescription Coverage | Included in medical maximum |"
        in result.extracted_text
    )

    page = result.structured_output["pages"][0]
    table_blocks = find_table_blocks(page)
    assert len(table_blocks) == 1
    table_block = table_blocks[0]
    assert table_block["table"]["rows"] == [
        ["Service", "Deductible", "Coinsurance", "Out-of-Pocket Maximum"],
        [
            "Medical",
            "$1,500 individual / $3,000 family",
            "20% after deductible",
            "$5,000 individual / $10,000 family",
        ],
        [
            "Prescription",
            "$250 individual / $500 family",
            "See Prescription Coverage",
            "Included in medical maximum",
        ],
    ]


def test_paddleocr_keeps_prose_outside_table(tmp_path):
    image_path = tmp_path / "mixed.png"
    image_path.write_bytes(b"fake image bytes")
    raw_result = legacy_lines(
        [
            ("Heading", (70, 10, 200, 25), 0.90),
            ("Name: Jane R. Smith", (70, 30, 300, 45), 0.90),
            ("Name", (82, 60, 140, 75), 0.90),
            ("Relationship", (342, 60, 450, 75), 0.90),
            ("Robert Smith", (82, 85, 160, 100), 0.90),
            ("Spouse", (342, 85, 430, 100), 0.90),
        ]
    )

    result = FakePaddleOCRExtractionService(raw_result).extract(
        create_image_document(image_path),
    )

    assert "Heading\nName: Jane R. Smith" in result.extracted_text
    assert "| Name | Relationship |" in result.extracted_text
    assert "| Robert Smith | Spouse |" in result.extracted_text

    page = result.structured_output["pages"][0]
    prose_blocks = [
        block
        for block in page["blocks"]
        if block.get("block_type") != "table"
    ]
    prose_text = "\n".join(block["text"] for block in prose_blocks)
    assert "Heading" in prose_text
    assert "Name: Jane R. Smith" in prose_text
    assert "|" not in prose_text


def test_paddleocr_keeps_normal_paragraph_as_text(tmp_path):
    image_path = tmp_path / "paragraph.png"
    image_path.write_bytes(b"fake image bytes")
    raw_result = legacy_lines(
        [
            ("This is a normal paragraph", (70, 10, 300, 25), 0.90),
            ("that should not become a table", (70, 30, 320, 45), 0.90),
            ("with another wrapped line", (70, 50, 310, 65), 0.90),
        ]
    )

    result = FakePaddleOCRExtractionService(raw_result).extract(
        create_image_document(image_path),
    )

    assert "This is a normal paragraph" in result.extracted_text
    assert "|" not in result.extracted_text

    page = result.structured_output["pages"][0]
    assert find_table_blocks(page) == []
    assert all(
        block["block_type"] == "text"
        for block in page["blocks"]
    )


def test_paddleocr_table_cells_carry_geometry_metadata(tmp_path):
    image_path = tmp_path / "cells.png"
    image_path.write_bytes(b"fake image bytes")
    raw_result = legacy_lines(
        [
            ("Item", (10, 10, 50, 25), 0.90),
            ("Qty", (150, 10, 180, 25), 0.90),
            ("Total", (250, 10, 310, 25), 0.90),
            ("Widget", (10, 40, 70, 55), 0.90),
            ("2", (150, 40, 165, 55), 0.90),
            ("10.00", (250, 40, 300, 55), 0.90),
        ]
    )

    result = FakePaddleOCRExtractionService(raw_result).extract(
        create_image_document(image_path),
    )

    page = result.structured_output["pages"][0]
    table_block = find_table_blocks(page)[0]
    cells = table_block["table"]["cells"]
    assert len(cells) == 6
    for cell in cells:
        assert set(cell.keys()) == {
            "text",
            "row_index",
            "column_index",
            "bbox",
            "rowspan",
            "colspan",
        }
        assert cell["rowspan"] == 1
        assert cell["colspan"] == 1
        assert len(cell["bbox"]) == 4
    header_cells = [cell for cell in cells if cell["row_index"] == 0]
    assert [cell["text"] for cell in header_cells] == ["Item", "Qty", "Total"]
    assert [cell["column_index"] for cell in header_cells] == [0, 1, 2]


def test_paddleocr_reconstructs_separate_sbc_tables(tmp_path):
    image_path = tmp_path / "synthetic_sbc.png"
    image_path.write_bytes(b"fake image bytes")
    raw_result = legacy_lines(
        [
            (
                "IMPORTANT QUESTIONS | ANSWERS | WHY THIS MATTERS",
                (70, 10, 900, 25),
                0.99,
            ),
            (
                "---I---I--- Question one? | Answer one | "
                "Reason one Question two? | Answer two",
                (70, 45, 1130, 60),
                0.99,
            ),
            (
                "| Reason two Question three? | Answer three | "
                "Reason three Question four?",
                (70, 63, 1140, 78),
                0.99,
            ),
            (
                "| Answer four | Reason four",
                (70, 81, 500, 96),
                0.99,
            ),
            (
                "COMMON MEDICAL EVENTS - WHAT YOU WILL PAY",
                (70, 115, 700, 130),
                0.99,
            ),
            ("Service", (80, 150, 150, 165), 0.99),
            ("In-Network", (335, 150, 450, 165), 0.99),
            ("Out-of-Network", (670, 150, 830, 165), 0.99),
            ("Limitations", (900, 150, 1010, 165), 0.99),
            ("Primary care", (80, 185, 210, 200), 0.99),
            ("$25", (335, 185, 380, 200), 0.99),
            ("40%", (670, 185, 720, 200), 0.99),
            ("Preauthorization", (900, 185, 1080, 200), 0.99),
            ("required", (900, 202, 980, 217), 0.99),
            ("Specialist", (80, 220, 180, 235), 0.99),
            ("$45", (335, 220, 380, 235), 0.99),
            ("40%", (670, 220, 720, 235), 0.99),
            ("None", (900, 220, 950, 235), 0.99),
            ("Preventive", (80, 255, 180, 270), 0.99),
            ("No charge", (335, 255, 430, 270), 0.99),
            ("40%", (670, 255, 720, 270), 0.99),
            ("None", (900, 255, 950, 270), 0.99),
            (
                "PRESCRIPTION DRUGS - WHAT YOU WILL PAY",
                (70, 290, 700, 305),
                0.99,
            ),
            ("Type", (80, 325, 130, 340), 0.99),
            ("Retail", (330, 325, 390, 340), 0.99),
            ("Mail Order", (555, 325, 650, 340), 0.99),
            ("Limitations", (790, 325, 900, 340), 0.99),
            ("Generic (Tier 1)", (80, 365, 220, 380), 0.99),
            ("$10", (330, 365, 370, 380), 0.99),
            ("$25", (555, 365, 595, 380), 0.99),
            ("Deductible applies", (790, 365, 980, 380), 0.99),
            ("Preferred brand (Tier 2)", (80, 400, 290, 415), 0.99),
            ("$35", (330, 400, 370, 415), 0.99),
            ("$87.50", (555, 400, 620, 415), 0.99),
            ("Deductible applies", (790, 400, 980, 415), 0.99),
            ("Non-preferred (Tier 3)", (80, 435, 285, 450), 0.99),
            ("$60", (330, 435, 370, 450), 0.99),
            ("$150", (555, 435, 605, 450), 0.99),
            ("Deductible applies", (790, 435, 980, 450), 0.99),
            ("Specialty (Tier 4)", (80, 470, 245, 485), 0.99),
            ("30%", (330, 470, 370, 485), 0.99),
            ("Unavailable", (555, 470, 650, 485), 0.99),
            ("Authorization required", (790, 470, 1010, 485), 0.99),
            ("RECENT CLAIMS INFORMATION", (70, 505, 520, 520), 0.99),
            ("Service Date", (80, 540, 190, 555), 0.99),
            ("Provider", (270, 540, 350, 555), 0.99),
            ("Service", (520, 540, 590, 555), 0.99),
            ("Billed", (770, 540, 830, 555), 0.99),
            ("Plan Paid", (880, 540, 970, 555), 0.99),
            ("You Paid", (1020, 540, 1100, 555), 0.99),
            *[
                (f"Day {index}", (80, top, 140, top + 15), 0.99)
                for index, top in enumerate(
                    (580, 615, 650, 685, 720),
                    start=1,
                )
            ],
            *[
                (f"Provider {index}", (270, top, 380, top + 15), 0.99)
                for index, top in enumerate(
                    (580, 615, 650, 685, 720),
                    start=1,
                )
            ],
            *[
                (f"Service {index}", (520, top, 610, top + 15), 0.99)
                for index, top in enumerate(
                    (580, 615, 650, 685, 720),
                    start=1,
                )
            ],
            *[
                (f"${index}00", (770, top, 825, top + 15), 0.99)
                for index, top in enumerate(
                    (580, 615, 650, 685, 720),
                    start=1,
                )
            ],
            *[
                (f"${index}0", (880, top, 930, top + 15), 0.99)
                for index, top in enumerate(
                    (580, 615, 650, 685, 720),
                    start=1,
                )
            ],
            *[
                (f"${index}", (1020, top, 1060, top + 15), 0.99)
                for index, top in enumerate(
                    (580, 615, 650, 685, 720),
                    start=1,
                )
            ],
            ("COVERAGE EXAMPLES", (70, 760, 390, 775), 0.99),
            (
                "This coverage example stays normal text.",
                (70, 790, 430, 805),
                0.99,
            ),
        ]
    )

    service = FakePageSizedPaddleOCRExtractionService(
        raw_result,
        (1224.0, 1584.0),
    )
    result = service.extract(create_image_document(image_path))
    page = result.structured_output["pages"][0]
    table_blocks = find_table_blocks(page)

    assert len(table_blocks) == 4
    tables = {
        tuple(block["table"]["rows"][0]): block["table"]["rows"]
        for block in table_blocks
    }
    assert tables[("IMPORTANT QUESTIONS", "ANSWERS", "WHY THIS MATTERS")] == [
        ["IMPORTANT QUESTIONS", "ANSWERS", "WHY THIS MATTERS"],
        ["Question one?", "Answer one", "Reason one"],
        ["Question two?", "Answer two", "Reason two"],
        ["Question three?", "Answer three", "Reason three"],
        ["Question four?", "Answer four", "Reason four"],
    ]
    assert tables[("Service", "In-Network", "Out-of-Network", "Limitations")] == [
        ["Service", "In-Network", "Out-of-Network", "Limitations"],
        ["Primary care", "$25", "40%", "Preauthorization required"],
        ["Specialist", "$45", "40%", "None"],
        ["Preventive", "No charge", "40%", "None"],
    ]
    prescription_rows = tables[("Type", "Retail", "Mail Order", "Limitations")]
    assert [row[0] for row in prescription_rows[1:]] == [
        "Generic (Tier 1)",
        "Preferred brand (Tier 2)",
        "Non-preferred (Tier 3)",
        "Specialty (Tier 4)",
    ]
    claim_rows = tables[
        ("Service Date", "Provider", "Service", "Billed", "Plan Paid", "You Paid")
    ]
    assert len(claim_rows) == 6
    assert [row[0] for row in claim_rows[1:]] == [
        "Day 1",
        "Day 2",
        "Day 3",
        "Day 4",
        "Day 5",
    ]

    table_text = "\n".join(block["text"] for block in table_blocks)
    assert "PRESCRIPTION DRUGS - WHAT YOU WILL PAY" not in table_text
    assert "RECENT CLAIMS INFORMATION" not in table_text
    assert "COVERAGE EXAMPLES" not in table_text
    prose_text = "\n".join(
        block["text"]
        for block in page["blocks"]
        if block["block_type"] != "table"
    )
    assert "PRESCRIPTION DRUGS - WHAT YOU WILL PAY" in prose_text
    assert "RECENT CLAIMS INFORMATION" in prose_text
    assert "COVERAGE EXAMPLES" in prose_text
    assert "This coverage example stays normal text." in prose_text


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
