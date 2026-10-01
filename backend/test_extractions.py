"""Verify document extraction libraries are installed and functional."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")

tests = []

# Test pypdf
try:
    from pypdf import PdfReader
    from io import BytesIO
    # Create a minimal PDF for testing
    import struct
    tests.append(("pypdf", "OK — importable"))
except ImportError as e:
    tests.append(("pypdf", f"FAIL — {e}"))

# Test python-docx
try:
    from docx import Document
    tests.append(("python-docx", "OK — importable"))
except ImportError as e:
    tests.append(("python-docx", f"FAIL — {e}"))

# Test openpyxl
try:
    from openpyxl import Workbook
    tests.append(("openpyxl", "OK — importable"))
except ImportError as e:
    tests.append(("openpyxl", f"FAIL — {e}"))

# Test python-pptx
try:
    from pptx import Presentation
    tests.append(("python-pptx", "OK — importable"))
except ImportError as e:
    tests.append(("python-pptx", f"FAIL — {e}"))

# Test Pillow
try:
    from PIL import Image
    tests.append(("Pillow", "OK — importable"))
except ImportError as e:
    tests.append(("Pillow", f"FAIL — {e}"))

# Test CSV
import csv
tests.append(("csv (stdlib)", "OK — available"))

# Test document_service end-to-end
try:
    from app.services.document_service import DocumentService
    svc = DocumentService()
    
    # Test TXT extraction
    txt_result = svc._extract_text(b"Hello World. This is a test document.", ".txt", "test.txt")
    assert "Hello World" in txt_result
    tests.append(("TXT extraction", "OK"))
    
    # Test Markdown extraction
    md_result = svc._extract_text(b"# Title\n\nSome content.", ".md", "test.md")
    assert "Title" in md_result
    tests.append(("Markdown extraction", "OK"))
    
    # Test CSV extraction
    csv_data = b"Name,Age\nAlice,30\nBob,25\n"
    csv_result = svc._extract_text(csv_data, ".csv", "test.csv")
    assert "Alice" in csv_result
    tests.append(("CSV extraction", "OK"))
    
    # Test XLSX extraction
    try:
        from openpyxl import Workbook
        from io import BytesIO
        wb = Workbook()
        ws = wb.active
        ws.append(["Name", "Score"])
        ws.append(["Alice", 95])
        ws.append(["Bob", 87])
        buf = BytesIO()
        wb.save(buf)
        xlsx_result = svc._extract_text(buf.getvalue(), ".xlsx", "test.xlsx")
        assert "Alice" in xlsx_result
        tests.append(("XLSX extraction", "OK"))
    except Exception as e:
        tests.append(("XLSX extraction", f"FAIL — {e}"))
    
    # Test DOCX extraction
    try:
        from docx import Document
        from io import BytesIO
        doc = Document()
        doc.add_heading("Test Document", level=1)
        doc.add_paragraph("This is a test paragraph.")
        buf = BytesIO()
        doc.save(buf)
        docx_result = svc._extract_text(buf.getvalue(), ".docx", "test.docx")
        assert "Test Document" in docx_result
        assert "test paragraph" in docx_result
        tests.append(("DOCX extraction", "OK"))
    except Exception as e:
        tests.append(("DOCX extraction", f"FAIL — {e}"))
    
    # Test PPTX extraction
    try:
        from pptx import Presentation
        from io import BytesIO
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = "Test Slide"
        buf = BytesIO()
        prs.save(buf)
        pptx_result = svc._extract_text(buf.getvalue(), ".pptx", "test.pptx")
        assert "Test Slide" in pptx_result
        tests.append(("PPTX extraction", "OK"))
    except Exception as e:
        tests.append(("PPTX extraction", f"FAIL — {e}"))
    
    # Test image extraction (metadata only)
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.new("RGB", (100, 100), color="red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_result = svc._extract_text(buf.getvalue(), ".png", "test.png")
        assert "Image" in img_result or "image" in img_result
        tests.append(("PNG metadata extraction", "OK"))
    except Exception as e:
        tests.append(("PNG metadata extraction", f"FAIL — {e}"))
    
    tests.append(("DocumentService initialized", "OK"))
except Exception as e:
    tests.append(("DocumentService", f"FAIL — {e}"))

# Test AI agents
try:
    from ai.agents.paper_analyzer_agent import PaperAnalyzerAgent
    analyzer = PaperAnalyzerAgent()
    result = analyzer.analyze([{
        "title": "Test Paper",
        "abstract": "This paper presents a deep learning approach for classification.",
        "authors": ["Author One"],
        "year": 2024,
        "filename": "test.pdf",
        "extracted_characters": 1000,
    }])
    assert "papers_processed" in result
    assert result["papers_processed"] == 1
    assert len(result["papers"]) == 1
    paper = result["papers"][0]
    assert "Deep Learning" in paper["methods"] or "Classification" in paper["methods"]
    tests.append(("PaperAnalyzerAgent analysis", "OK"))
except Exception as e:
    tests.append(("PaperAnalyzerAgent analysis", f"FAIL — {e}"))

# Test dataset recommendations
try:
    from ai.agents.dataset_recommendation_agent import DatasetRecommendationAgent
    ds_agent = DatasetRecommendationAgent()
    ds_result = ds_agent.recommend("machine learning classification", [])
    assert len(ds_result["recommendations"]) > 0
    has_url = any(rec.get("url", "").startswith("http") for rec in ds_result["recommendations"])
    assert has_url, "No clickable URLs found"
    tests.append(("DatasetRecommendationAgent", f"OK — {len(ds_result['recommendations'])} datasets with URLs"))
except Exception as e:
    tests.append(("DatasetRecommendationAgent", f"FAIL — {e}"))

print()
print("=" * 60)
print("RESEARCHOS DEPENDENCY & FUNCTIONALITY VERIFICATION")
print("=" * 60)
passed = 0
failed = 0
for name, result in tests:
    status = "OK" if result.startswith("OK") else "!!"
    print(f"  [{status}]  {name}: {result}")
    if result.startswith("OK"):
        passed += 1
    else:
        failed += 1

print()
print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
if failed:
    print("FAIL")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
