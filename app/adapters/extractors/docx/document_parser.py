from app.domain.dto.document import DocumentDTO


class DocxExtractor:
    """Extractor for Microsoft Word (.docx) documents into Domain DTOs."""

    def extract(self, file_path: str) -> DocumentDTO:
        """
        Extract document structure, paragraphs, tables, and metadata from a .docx file.

        Currently returns an empty DocumentDTO stub. Real parsing logic will be implemented
        in the subsequent development stage.
        """
        return DocumentDTO(
            paragraphs=[],
            tables=[],
            total_pages=None,
            words_count=None,
        )

