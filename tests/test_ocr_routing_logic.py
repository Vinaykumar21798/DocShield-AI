import pytest
from pathlib import Path
from database.models import Document
from modules.extraction.ocr import OCRDecisionEngine, OCREngine
from benchmarks.docs_synth import (
    native_2page_pdf, 
    scanned_pdf_with_footer, 
    short_native_pdf, 
    native_with_logo_pdf
)
import base64
import fitz

VALID_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")

def test_routing_short_native(tmp_path):
    """Case 1: Short native page (~50 chars, no images) -> NATIVE_PDF"""
    pdf_path = tmp_path / "short_native.pdf"
    short_native_pdf(pdf_path)
    
    doc = Document(id="doc", storage_path=str(pdf_path))
    decision = OCRDecisionEngine().decide(doc)
    assert decision.engine == OCREngine.NATIVE_PDF

def test_routing_native_with_logo(tmp_path):
    """Case 2: Native page with small logo (~50 chars, small image) -> NATIVE_PDF"""
    pdf_path = tmp_path / "native_logo.pdf"
    native_with_logo_pdf(pdf_path)
    
    doc = Document(id="doc", storage_path=str(pdf_path))
    decision = OCRDecisionEngine().decide(doc)
    assert decision.engine == OCREngine.NATIVE_PDF

def test_routing_scanned_with_footer(tmp_path):
    """Case 3: Scanned page with searchable footer (short footer + large raster image) -> PADDLEOCR"""
    pdf_path = tmp_path / "scanned_footer.pdf"
    scanned_pdf_with_footer(pdf_path)
    
    doc = Document(id="doc", storage_path=str(pdf_path))
    decision = OCRDecisionEngine().decide(doc)
    # This was the bug: previously NATIVE_PDF, now should be PADDLEOCR
    assert decision.engine == OCREngine.PADDLEOCR

def test_routing_pure_scanned(tmp_path):
    """Case 4: Pure scanned page (no native text + large raster image) -> PADDLEOCR"""
    pdf_path = tmp_path / "pure_scan.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(fitz.Rect(0, 0, 595, 842), stream=VALID_PNG)
    doc.save(pdf_path)
    doc.close()
    
    doc_model = Document(id="doc", storage_path=str(pdf_path))
    decision = OCRDecisionEngine().decide(doc_model)
    assert decision.engine == OCREngine.PADDLEOCR

def test_routing_mixed_pdf(tmp_path):
    """Case 5: Mixed PDF (native page + scanned page) -> MIXED_PDF"""
    pdf_path = tmp_path / "mixed.pdf"
    doc = fitz.open()
    # Page 1: Native
    p1 = doc.new_page()
    p1.insert_text((50, 50), "This is a native page with plenty of text." * 10)
    # Page 2: Scanned with footer
    p2 = doc.new_page()
    p2.insert_image(fitz.Rect(0, 0, 595, 842), stream=VALID_PNG)
    p2.insert_text((50, 800), "Footer text")
    doc.save(pdf_path)
    doc.close()
    
    doc_model = Document(id="doc", storage_path=str(pdf_path))
    decision = OCRDecisionEngine().decide(doc_model)
    assert decision.engine == OCREngine.MIXED_PDF
