from docx import Document
from docx.shared import Mm

from app.adapters.extractors.docx.app_props import extract_page_count
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

        # 3. Initialize empty DTO collections
        paragraphs_dto: list[ParagraphDTO] = []
        tables_dto: list[TableDTO] = []

        # 4. Iterate over paragraphs
        for p in doc.paragraphs:
            text = p.text
            style_name = p.style.name if (p.style and hasattr(p.style, "name") and p.style.name) else "Normal"

            alignment: str | None = None
            if p.alignment is not None:
                alignment = getattr(p.alignment, "name", str(p.alignment))

            indent_mm = 0.0
            if p.paragraph_format and p.paragraph_format.first_line_indent is not None:
                try:
                    indent_mm = float(p.paragraph_format.first_line_indent.mm)
                except Exception:
                    indent_mm = 0.0

            style_lower = style_name.lower()
            is_heading = "heading" in style_lower or "заголовок" in style_lower

            runs_dto: list[RunDTO] = []
            for run in p.runs:
                is_bold = bool(run.bold)
                is_italic = bool(run.italic)
                font_size_pt: float | None = None

                if run.font and run.font.size is not None:
                    try:
                        font_size_pt = float(run.font.size.pt)
                    except Exception:
                        font_size_pt = None

                runs_dto.append(
                    RunDTO(
                        text=run.text,
                        is_bold=is_bold,
                        is_italic=is_italic,
                        font_size_pt=font_size_pt,
                    )
                )

            paragraphs_dto.append(
                ParagraphDTO(
                    text=text,
                    style_name=style_name,
                    alignment=alignment,
                    indent_mm=indent_mm,
                    is_heading=is_heading,
                    runs=runs_dto,
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

        # 6. Return populated DocumentDTO
        return DocumentDTO(
            paragraphs=paragraphs_dto,
            tables=tables_dto,
            total_pages=pages,
            words_count=words,
        )
