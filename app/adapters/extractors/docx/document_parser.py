from docx import Document
from docx.shared import Mm

from app.adapters.extractors.docx.app_props import extract_page_count
from app.adapters.extractors.docx.styles_xml import StyleHierarchyResolver
from app.domain.dto.document import DocumentDTO, ParagraphDTO, RunDTO, TableDTO


class DocxExtractor:
    """Extractor for Microsoft Word (.docx) documents into Domain DTOs."""

    def extract(self, file_path: str) -> DocumentDTO:
        """
        Extract document structure, paragraphs, tables, and metadata from a .docx file.

        Args:
            file_path: Path to the .docx document.

        Returns:
            DocumentDTO: Fully populated in-memory representation of the document.
        """
        # 1. Extract metadata (pages, words) from docProps/app.xml
        pages, words = extract_page_count(file_path)

        # 2. Open document via python-docx
        doc = Document(file_path)

        # 3. Initialize style hierarchy resolver
        resolver = StyleHierarchyResolver(doc)

        # 4. Initialize empty DTO collections
        paragraphs_dto: list[ParagraphDTO] = []
        tables_dto: list[TableDTO] = []

        # 5. Iterate over paragraphs
        for p in doc.paragraphs:
            text = p.text
            style_name = p.style.name if (p.style and hasattr(p.style, "name") and p.style.name) else "Normal"

            alignment = resolver.get_paragraph_alignment(p)
            indent_mm = resolver.get_paragraph_indent_mm(p)

            style_lower = style_name.lower()
            is_heading = "heading" in style_lower or "заголовок" in style_lower

            runs_dto: list[RunDTO] = []
            for run in p.runs:
                is_bold = bool(run.bold)
                is_italic = bool(run.italic)
                font_size_pt = resolver.get_run_font_size(run, p)

                runs_dto.append(
                    RunDTO(
                        text=run.text,
                        is_bold=is_bold,
                        is_italic=is_italic,
                        font_size_pt=font_size_pt,
                    )
                )

            # Extract list nesting level
            list_level = resolver.get_list_level(p)

            # Check for embedded images (DrawingML or VML)
            has_image = False
            if hasattr(p, "_p") and p._p is not None:
                has_image = bool(p._p.xpath(".//w:drawing | .//w:pict"))

            paragraphs_dto.append(
                ParagraphDTO(
                    text=text,
                    style_name=style_name,
                    alignment=alignment,
                    indent_mm=indent_mm,
                    is_heading=is_heading,
                    runs=runs_dto,
                    list_level=list_level,
                    has_image=has_image,
                )
            )

        # 5. Iterate over tables
        for table in doc.tables:
            rows_count = len(table.rows)
            cols_count = len(table.columns)
            text_content: list[list[str]] = []

            for row in table.rows:
                row_texts = [cell.text for cell in row.cells]
                text_content.append(row_texts)

            tables_dto.append(
                TableDTO(
                    rows_count=rows_count,
                    cols_count=cols_count,
                    text_content=text_content,
                )
            )

        # 6. Extract section margins (from the first section if available)
        margin_left_mm: float | None = None
        margin_right_mm: float | None = None
        margin_top_mm: float | None = None
        margin_bottom_mm: float | None = None

        if doc.sections:
            section = doc.sections[0]
            if section.left_margin is not None:
                try:
                    margin_left_mm = float(section.left_margin.mm)
                except Exception:
                    margin_left_mm = None
            if section.right_margin is not None:
                try:
                    margin_right_mm = float(section.right_margin.mm)
                except Exception:
                    margin_right_mm = None
            if section.top_margin is not None:
                try:
                    margin_top_mm = float(section.top_margin.mm)
                except Exception:
                    margin_top_mm = None
            if section.bottom_margin is not None:
                try:
                    margin_bottom_mm = float(section.bottom_margin.mm)
                except Exception:
                    margin_bottom_mm = None

        # 7. Return populated DocumentDTO
        return DocumentDTO(
            paragraphs=paragraphs_dto,
            tables=tables_dto,
            total_pages=pages,
            words_count=words,
            margin_left_mm=margin_left_mm,
            margin_right_mm=margin_right_mm,
            margin_top_mm=margin_top_mm,
            margin_bottom_mm=margin_bottom_mm,
        )
