"""Bibliography extraction and parsing utilities."""

import re

from app.domain.dto.document import DocumentDTO, ParagraphDTO

BIBLIOGRAPHY_HEADING_REGEX = re.compile(
    r"^\s*(?:список\s+(?:использованн(?:ых|ой)|используем(?:ой|ых)|основной)?\s*(?:источников(?:\s+и\s+литературы)?|литературы(?:\s+и\s+источников)?)|список\s+(?:источников|литературы)|библиографический\s+список|библиография|литература)\b",
    re.IGNORECASE,
)

APPENDIX_START_REGEX = re.compile(r"^\s*ПРИЛОЖЕНИЕ\s+[А-ЯA-Z]\b", re.IGNORECASE)

BRACKET_REF_REGEX = re.compile(r"\[([^\]]+)\]")


def split_document_by_bibliography(
    doc: DocumentDTO,
) -> tuple[list[ParagraphDTO], list[ParagraphDTO]]:
    """Split document paragraphs into body paragraphs and bibliography paragraphs.

    Args:
        doc: Extracted document DTO.

    Returns:
        tuple (body_paragraphs, bibliography_paragraphs).
    """
    bib_start_idx: int | None = None

    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        if not text:
            continue

        if BIBLIOGRAPHY_HEADING_REGEX.match(text):
            bib_start_idx = i
            break

    if bib_start_idx is None:
        return doc.paragraphs, []

    body_paragraphs = doc.paragraphs[:bib_start_idx]

    # Find the end of the bibliography (marked by appendices or end of document)
    bib_end_idx = len(doc.paragraphs)
    for j in range(bib_start_idx + 1, len(doc.paragraphs)):
        text = doc.paragraphs[j].text.strip()
        if APPENDIX_START_REGEX.match(text):
            bib_end_idx = j
            break

    bibliography_paragraphs = doc.paragraphs[bib_start_idx + 1 : bib_end_idx]
    return body_paragraphs, bibliography_paragraphs


def extract_sources(bibliography_paragraphs: list[ParagraphDTO]) -> dict[int, str]:
    """Extract numbered bibliography entries into a mapping of source ID to entry text.

    Args:
        bibliography_paragraphs: List of paragraphs within the bibliography section.

    Returns:
        dict[int, str]: Map of source number to its textual description.
    """
    sources: dict[int, str] = {}
    current_id: int | None = None

    for p in bibliography_paragraphs:
        text = p.text.strip()
        if not text:
            continue

        # Match entry starting with number: "1.", "1 ", "[1]", "1 -"
        match = re.match(r"^\s*\[?(\d+)\]?[\.\s\-]+(.*)$", text)
        if match:
            current_id = int(match.group(1))
            sources[current_id] = match.group(2).strip()
        elif current_id is not None:
            # Continuation paragraph of current source
            sources[current_id] += " " + text

    # Fallback: if no sources were parsed via leading text digits (e.g. Word auto-numbered list
    # where paragraph.text doesn't contain the bullet/number prefix), treat each non-empty paragraph as a source
    if not sources and bibliography_paragraphs:
        auto_id = 1
        for p in bibliography_paragraphs:
            text = p.text.strip()
            if text:
                sources[auto_id] = text
                auto_id += 1

    return sources


def parse_bracket_content(content: str) -> set[int]:
    """Parse citation bracket content into a set of referenced source IDs.

    Handles formats like:
      - '1' -> {1}
      - '1, 2, 5' -> {1, 2, 5}
      - '3-6' / '3—6' -> {3, 4, 5, 6}
      - '10, с. 15' / '10, p. 25' -> {10}

    Args:
        content: Inner text of bracket citation (without '[' and ']').

    Returns:
        set[int]: Set of referenced source numbers.
    """
    nums: set[int] = set()
    parts = re.split(r"[,;]", content)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Strip page references like "с. 15", "стр. 120", "p. 45", "pp. 10-12"
        part_clean = re.sub(
            r"(?:с|стр|с\.|стр\.|p|pp|page|pages)\s*\.?\s*\d+.*",
            "",
            part,
            flags=re.IGNORECASE,
        ).strip()

        # Handle range like "3-6", "3–6", "3—6"
        range_match = re.match(r"^(\d+)\s*[–—\-]\s*(\d+)$", part_clean)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if 0 < start <= end and (end - start) < 100:
                nums.update(range(start, end + 1))
            continue

        # Handle single number
        num_match = re.match(r"^(\d+)", part_clean)
        if num_match:
            nums.add(int(num_match.group(1)))

    return nums
