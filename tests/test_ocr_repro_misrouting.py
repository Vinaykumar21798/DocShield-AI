import pytest
from pathlib import Path
from database.models import Document
from modules.extraction.ocr import OCRDecisionEngine, OCREngine
from modules.extraction.native import NativePDFExtractionService
from benchmarks.docs_synth import scanned_pdf_with_footer

def test_reproduce_pdf_misrouting(tmp_path):
    \"\"\"
    Reproduction A: Verify that a PDF with a searchable footer but raster body
    is incorrectly routed to NATIVE_PDF, causing scanned content to be missed.
    \"\"\"
    # 1. Build misrouted PDF (raster body + searchable footer >= 10 chars)
    pdf_path = tmp_path / \"misroute_test.pdf\"
    config = scanned_pdf_with_footer(pdf_path)
    
    doc = Document(
        id=\"repro-a-doc\",
        filename=\"misroute.pdf\",
        stored_filename=\"misroute.pdf\",
        file_type=\"application/pdf\",
        file_size=pdf_path.stat().st_size,
        storage_path=str(pdf_path),
        status=\"PENDING\"
    )

    # 2. Decision check
    decision_engine = OCRDecisionEngine()
    decision = decision_engine.decide(doc)
    
    # Assert Bug: The engine should be PADDLEOCR (because body is scanned),
    # but it is incorrectly NATIVE_PDF because of the footer.
    assert decision.engine == OCREngine.NATIVE_PDF, \"Bug not reproduced: Decision was not NATIVE_PDF\"

    # 3. Extraction check
    extractor = NativePDFExtractionService()
    res = extractor.extract(doc)
    
    # Assert Bug: Body entities (e.g., SSN, Email) are missing
    # but footer is present.
    extracted_text = res.extracted_text
    assert \"CONFIDENTIAL DOCSHIELD\" in extracted_text
    assert \"jane.roe@example.com\" not in extracted_text, \"Bug not reproduced: Body content was extracted\"
    assert \"123-45-6789\" not in extracted_text, \"Bug not reproduced: Body content was extracted\"
