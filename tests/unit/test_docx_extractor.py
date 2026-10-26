import io
import zipfile
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Mm, Pt

from app.adapters.extractors.docx.app_props import extract_page_count
from app.adapters.extractors.docx.document_parser import DocxExtractor
from app.domain.dto.document import DocumentDTO


def test_extract_page_count_valid(tmp_path):
    docx_file = tmp_path / "valid_metadata.docx"

    app_xml_content = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
        <Pages>45</Pages>
        <Words>12340</Words>
    </Properties>
    """

    with zipfile.ZipFile(docx_file, "w") as zf:
        zf.writestr("docProps/app.xml", app_xml_content)
        zf.writestr("[Content_Types].xml", b"<Types/>")

    pages, words = extract_page_count(str(docx_file))
    assert pages == 45
    assert words == 12340


def test_extract_page_count_missing_app_xml(tmp_path):
    docx_file = tmp_path / "no_metadata.docx"
    with zipfile.ZipFile(docx_file, "w") as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")

    pages, words = extract_page_count(str(docx_file))
    assert pages is None
    assert words is None


def test_extract_page_count_invalid_file(tmp_path):
    bad_file = tmp_path / "corrupted.docx"
    bad_file.write_text("not a zip file", encoding="utf-8")

    pages, words = extract_page_count(str(bad_file))
    assert pages is None
    assert words is None


def test_docx_extractor_full_document(tmp_path):
    docx_file = tmp_path / "sample.docx"
    doc = Document()

    # 1. Heading paragraph ("Заголовок 1")
    p_heading = doc.add_paragraph("Глава 1. Введение", style="Heading 1")

    # 2. Paragraph with runs, bold, italic, font size 14 pt, indent 12.5 mm, justified
    p_body = doc.add_paragraph()
    p_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_body.paragraph_format.first_line_indent = Mm(12.5)

    run_plain = p_body.add_run("Обычный текст. ")
    run_bold = p_body.add_run("Жирный текст. ")
    run_bold.bold = True
    run_italic = p_body.add_run("Курсивный текст. ")
    run_italic.italic = True
    run_styled = p_body.add_run("Текст 14 pt.")
    run_styled.font.size = Pt(14)

    # 3. Heading with english style name ("Heading 2")
    p_heading2 = doc.add_paragraph("1.1. Обзор предметной области", style="Heading 2")

    # 4. Table 2x3
    table = doc.add_table(rows=2, cols=3)
    table.rows[0].cells[0].text = "Header 1"
    table.rows[0].cells[1].text = "Header 2"
    table.rows[0].cells[2].text = "Header 3"
    table.rows[1].cells[0].text = "Val 1"
    table.rows[1].cells[1].text = "Val 2"
    table.rows[1].cells[2].text = "Val 3"

    doc.save(str(docx_file))

    # Inject custom docProps/app.xml with Pages and Words metadata cleanly
    app_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
        <Pages>12</Pages>
        <Words>2450</Words>
    </Properties>
    """
    clean_docx = tmp_path / "sample_with_meta.docx"
    with zipfile.ZipFile(docx_file, "r") as zin:
        with zipfile.ZipFile(clean_docx, "w") as zout:
            for item in zin.infolist():
                if item.filename != "docProps/app.xml":
                    zout.writestr(item, zin.read(item.filename))
            zout.writestr("docProps/app.xml", app_xml)

    # Extract via DocxExtractor
    extractor = DocxExtractor()
    result = extractor.extract(str(clean_docx))

    assert isinstance(result, DocumentDTO)
    assert result.total_pages == 12
    assert result.words_count == 2450

    # Verify paragraphs
    assert len(result.paragraphs) == 3

    # Check heading 1
    h1 = result.paragraphs[0]
    assert h1.text == "Глава 1. Введение"
    assert h1.is_heading is True

    # Check body paragraph
    body = result.paragraphs[1]
    assert body.is_heading is False
    assert body.alignment == "JUSTIFY"
    assert round(body.indent_mm, 1) == 12.5
    assert len(body.runs) == 4

    assert body.runs[0].text == "Обычный текст. "
    assert body.runs[0].is_bold is False
    assert body.runs[0].is_italic is False

    assert body.runs[1].text == "Жирный текст. "
    assert body.runs[1].is_bold is True

    assert body.runs[2].text == "Курсивный текст. "
    assert body.runs[2].is_italic is True

    assert body.runs[3].text == "Текст 14 pt."
    assert body.runs[3].font_size_pt == 14.0

    # Check heading 2
    h2 = result.paragraphs[2]
    assert h2.text == "1.1. Обзор предметной области"
    assert h2.is_heading is True

    # Check table
    assert len(result.tables) == 1
    t = result.tables[0]
    assert t.rows_count == 2
    assert t.cols_count == 3
    assert t.text_content == [
        ["Header 1", "Header 2", "Header 3"],
        ["Val 1", "Val 2", "Val 3"],
    ]


def test_docx_extractor_none_properties(tmp_path):
    docx_file = tmp_path / "none_props.docx"
    doc = Document()

    # Paragraph with no explicit font size, no indent, no alignment
    p = doc.add_paragraph()
    r = p.add_run("Minimal run without explicit styles")

    doc.save(str(docx_file))

    extractor = DocxExtractor()
    result = extractor.extract(str(docx_file))

    assert len(result.paragraphs) == 1
    p_dto = result.paragraphs[0]
    assert p_dto.text == "Minimal run without explicit styles"
    assert p_dto.alignment is None
    assert p_dto.indent_mm == 0.0
    assert p_dto.is_heading is False
    assert len(p_dto.runs) == 1
    assert p_dto.runs[0].is_bold is False
    assert p_dto.runs[0].is_italic is False
    assert p_dto.runs[0].font_size_pt is None

