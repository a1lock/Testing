from dataclasses import dataclass, field


@dataclass
class RunDTO:
    """Represents a text run within a paragraph with specific inline formatting."""

    text: str
    is_bold: bool = False
    is_italic: bool = False
    font_size_pt: float | None = None


@dataclass
class ParagraphDTO:
    """Represents a paragraph in the document with structural and typographical properties."""

    text: str
    style_name: str
    alignment: str | None = None
    indent_mm: float = 0.0
    is_heading: bool = False
    runs: list[RunDTO] = field(default_factory=list)


@dataclass
class TableDTO:
    """Represents a table structure and textual content extracted from the document."""

    rows_count: int
    cols_count: int
    text_content: list[list[str]] = field(default_factory=list)


@dataclass
class DocumentDTO:
    """Represents the complete in-memory snapshot of an extracted document."""

    paragraphs: list[ParagraphDTO] = field(default_factory=list)
    tables: list[TableDTO] = field(default_factory=list)
    total_pages: int | None = None
    words_count: int | None = None

