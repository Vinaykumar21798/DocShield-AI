import fitz
from pathlib import Path
from typing import Tuple

def native_2page_pdf(path: Path):
    """Creates a 2-page PDF with native text on both pages."""
    doc = fitz.open()
    
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Page 1: john.smith@example.com")
    
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Page 2: 123-45-6789")
    
    doc.save(path)
    doc.close()

def scanned_pdf_with_footer(path: Path) -> Tuple[str, str]:
    """
    Creates a PDF that looks like a scan (one large image) 
    but has a searchable footer.
    """
    doc = fitz.open()
    page = doc.new_page()
    
    # Create a valid 1x1 PNG image
    import base64
    img_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
    
    # Insert it and scale it to cover 90% of the page
    rect = fitz.Rect(50, 50, 545, 792)
    page.insert_image(rect, stream=img_bytes)
    
    # 2. Insert searchable footer
    page.insert_text((50, 820), "CONFIDENTIAL DOCSHIELD DOCUMENT - INTERNAL USE ONLY")
    
    doc.save(path)
    doc.close()
    return "jane.roe@example.com", "123-45-6789"

def short_native_pdf(path: Path):
    """Creates a PDF with very short native text and no images."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Short native text.")
    doc.save(path)
    doc.close()

def native_with_logo_pdf(path: Path):
    """Creates a PDF with short native text and a small logo."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Native text with logo.")
    
    import base64
    img_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
    # Small logo: 50x50
    rect = fitz.Rect(0, 0, 50, 50)
    page.insert_image(rect, stream=img_bytes)
    
    doc.save(path)
    doc.close()
