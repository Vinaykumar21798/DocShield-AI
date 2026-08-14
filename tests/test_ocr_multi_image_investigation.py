import pytest
import fitz
import base64
from pathlib import Path
from typing import List, Tuple, Dict, Any
from database.models import Document
from modules.extraction.ocr import OCRDecisionEngine, OCREngine
from modules.extraction.native import NativePDFExtractionService

# Valid 1x1 PNG image
VALID_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")

def create_investigation_pdf(path: Path, pages_config: List[Dict[str, Any]]):
    """
    Creates a PDF based on page configurations.
    pages_config = [
        {
            "text": "Footer text",
            "images": [fitz.Rect(x0, y0, x1, y1), ...],
        },
        ...
    ]
    """
    doc = fitz.open()
    for page_cfg in pages_config:
        page = doc.new_page()
        # Insert text
        if "text" in page_cfg:
            page.insert_text((50, 800), page_cfg["text"])
        # Insert images
        if "images" in page_cfg:
            for rect in page_cfg["images"]:
                page.insert_image(rect, stream=VALID_PNG)
    doc.save(path)
    doc.close()

def analyze_page_coverage(pdf_path: Path, page_index: int):
    """Calculates actual individual and combined coverage for a page."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    page_area = page.rect.width * page.rect.height
    
    images = page.get_images(full=True)
    individual_coverages = []
    combined_area = 0
    
    # In a real scenario, we should handle overlaps using a union of rects.
    # For these synthetic tests, we'll place them non-overlapping.
    for img in images:
        rects = page.get_image_rects(img[0])
        for rect in rects:
            area = rect.width * rect.height
            coverage = area / page_area
            individual_coverages.append(coverage)
            combined_area += area
            
    doc.close()
    return {
        "individual": individual_coverages,
        "combined": combined_area / page_area if page_area > 0 else 0,
        "text_length": len(page.get_text("text").strip()) if 'page' in locals() else 0 # This is wrong because doc closed
    }

# Re-implementing analysis to fix the local variable issue
def analyze_page_full(pdf_path: Path, page_index: int):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    text_len = len(page.get_text("text").strip())
    page_area = page.rect.width * page.rect.height
    
    images = page.get_images(full=True)
    individual = []
    total_area = 0
    for img in images:
        for rect in page.get_image_rects(img[0]):
            a = rect.width * rect.height
            individual.append(a / page_area)
            total_area += a
    doc.close()
    return {
        "text_length": text_len,
        "individual": individual,
        "combined": total_area / page_area,
        "num_images": len(images)
    }

def run_investigation_case(name: str, pages_config: List[Dict[str, Any]], expected_engine: OCREngine):
    tmp_path = Path("investigation_temp.pdf")
    create_investigation_pdf(tmp_path, pages_config)
    
    doc_model = Document(id="test", storage_path=str(tmp_path))
    decision_engine = OCRDecisionEngine()
    native_service = NativePDFExtractionService()
    
    decision = decision_engine.decide(doc_model)
    actual_engine = decision.engine
    
    # Extract using native service to see if content is missed
    extracted_text = native_service.extract(doc_model).extracted_text
    
    results = []
    for i in range(len(pages_config)):
        metrics = analyze_page_full(tmp_path, i)
        results.append(metrics)
        
    # Clean up
    if tmp_path.exists():
        tmp_path.unlink()
        
    return {
        "name": name,
        "actual_engine": actual_engine,
        "expected_engine": expected_engine,
        "page_metrics": results,
        "extracted_text": extracted_text,
        "missed_body": actual_engine == OCREngine.NATIVE_PDF and any(m["combined"] > 0.3 for m in results)
    }

def test_multi_image_investigation():
    # A4 size: 595 x 842 = 499990
    page_w = 595
    page_h = 842
    
    # Case 1: Multi-medium (3 x 20% = 60%)
    # Rect area ~ 100,000. 100k / 500k = 0.2
    rect_20pct = fitz.Rect(0, 0, 300, 333) # 99,900
    case1_pages = [
        {
            "text": "Searchable footer text here",
            "images": [
                fitz.Rect(0, 0, 300, 333),
                fitz.Rect(300, 0, 600, 333),
                fitz.Rect(0, 333, 300, 666),
            ]
        }
    ]
    
    # Case 2: Multi-small (3 x 5% = 15%)
    # Rect area ~ 25,000
    rect_5pct = fitz.Rect(0, 0, 100, 250) # 25,000
    case2_pages = [
        {
            "text": "Searchable footer text here",
            "images": [
                fitz.Rect(0, 0, 100, 250),
                fitz.Rect(100, 0, 200, 250),
                fitz.Rect(200, 0, 300, 250),
            ]
        }
    ]
    
    # Case 3: Single large (1 x 40% = 40%)
    # Rect area ~ 200,000
    rect_40pct = fitz.Rect(0, 0, 595, 336) # 199,752
    case3_pages = [
        {
            "text": "Searchable footer text here",
            "images": [rect_40pct]
        }
    ]
    
    # Case 4: Mixed
    case4_pages = [
        {"text": "This is a perfectly native page with lots of text content. " * 20, "images": []},
        {
            "text": "Searchable footer text here",
            "images": [
                fitz.Rect(0, 0, 300, 333),
                fitz.Rect(300, 0, 600, 333),
                fitz.Rect(0, 333, 300, 666),
            ]
        }
    ]
    
    scenarios = [
        ("Multi-Medium", case1_pages, OCREngine.PADDLEOCR),
        ("Multi-Small", case2_pages, OCREngine.NATIVE_PDF),
        ("Single-Large", case3_pages, OCREngine.PADDLEOCR),
        ("Mixed-PDF", case4_pages, OCREngine.MIXED_PDF),
    ]
    
    print(f"{'Scenario':<20} | {'Actual':<12} | {'Expected':<12} | {'Result'}")
    print("-" * 60)
    
    all_passed = True
    for name, cfg, expected in scenarios:
        res = run_investigation_case(name, cfg, expected)
        status = "PASS" if res["actual_engine"] == expected else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"{name:<20} | {res['actual_engine']:<12} | {expected:<12} | {status}")
        
        # Detailed report for the failure
        if status == "FAIL":
            print(f"  -> Investigation for {name}:")
            for i, m in enumerate(res["page_metrics"]):
                print(f"    Page {i+1}: TextLen={m['text_length']}, Imgs={m['num_images']}, "
                      f"Individual={m['individual']}, Combined={m['combined']:.3f}")
            print(f"    Native Extract: {res['extracted_text'][:50]}...")
            print(f"    Body Missed: {res['missed_body']}")
    
    if not all_passed:
        pytest.fail("Multi-image routing edge cases failed.")

if __name__ == "__main__":
    # This allows running the investigation script directly
    import sys
    # To run as a script, we need to mock the pytest part or just call the logic
    try:
        test_multi_image_investigation()
    except Exception as e:
        print(f"\nResult: {e}")
        sys.exit(1)
