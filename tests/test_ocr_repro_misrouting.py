import pytest
from pathlib import Path
from database.models import Document
from modules.extraction.ocr import OCRDecisionEngine, OCREngine
from modules.extraction.native import NativePDFExtractionService
from benchmarks.docs_synth import scanned_pdf_with_footer

def test_reproduce_pdf_misrouting(tmp_path):
    """
    Regression Test: Verify that a PDF with a searchable footer but raster body
    is correctly routed to PADDLEOCR, ensuring scanned content is not missed.
    """
    # 1. Build PDF (raster body + searchable footer >= 10 chars)
    pdf_path = tmp_path / "misroute_test.pdf"
    config = scanned_pdf_with_footer(pdf_path)
    
    doc = Document(
        id="repro-a-doc",
        filename="misroute.pdf",
        stored_filename="misroute.pdf",
        file_type="application/pdf",
        file_size=pdf_path.stat().st_size,
        storage_path=str(pdf_path),
        status="PENDING"
    )

    # 2. Decision check
    decision_engine = OCRDecisionEngine()
    decision = decision_engine.decide(doc)
    
    # Fixed: The engine should now be PADDLEOCR because the body is scanned
    assert decision.engine == OCREngine.PADDLEOCR, f"Bug regression: Decision was {decision.engine}, expected PADDLEOCR"

    # 3. Extraction check using Native service
    # We verify that the native service STILL cannot see the body,
    # proving why routing to PADDLEOCR was necessary.
    extractor = NativePDFExtractionService()
    res = extractor.extract(doc)
    
    extracted_text = res.extracted_text
    assert "CONFIDENTIAL DOCSHIELD" in extracted_text
    assert "jane.roe@example.com" not in extracted_text, "Native extraction unexpectedly recovered body content"
    assert "123-45-6789" not in extracted_text, "Native extraction unexpectedly recovered body content"
