"""Table of contents (TOC) matching validation rule."""

import re

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule
from app.rule_engine.utils import matches_heading_fuzzy

FORBIDDEN_TOC_ITEMS: tuple[str, ...] = (
    "титульный лист",
    "задание",
    "аннотация",
    "содержание",
    "оглавление",
)


def _is_real_heading(p: ParagraphDTO) -> bool:
    """Determine whether paragraph is a real body heading (Level 1 or Level 2)."""
    text = p.text.strip()
    if not text:
        return False

    style_lower = (p.style_name or "").lower()
    if p.is_heading or "heading" in style_lower or "заголовок" in style_lower:
        return True

    # Check structural section or chapter pattern
    is_numbered_chapter = bool(re.match(r"^\s*(?:глава|раздел)?\s*\d+[\.\s]+", text, re.IGNORECASE))
    is_numbered_sub = bool(re.match(r"^\s*(?:подраздел\s+)?\d+\.\d+", text, re.IGNORECASE))
    is_structural = bool(
        re.match(
            r"^\s*(?:заключение|список\s+(?:использованных\s+)?источников|список\s+литературы|библиографический\s+список|библиография|приложение)\b",
            text,
            re.IGNORECASE,
        )
    )

    if (is_numbered_chapter or is_structural) and (text.isupper() or len(text.split()) <= 8):
        return True
    if is_numbered_sub and len(text.split()) <= 12 and not text.endswith("."):
        return True

    return False


@register_rule("TOC_MATCHING")
class TocMatchingRule(BaseRule):
    """Validates Table of Contents boundaries, forbidden items, and consistency with body headings."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Verify Table of Contents items against document structure.

        Args:
            doc: Extracted document DTO.
            params: Rule parameters (optional).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        violations: list[ViolationDTO] = []

        toc_start_idx: int | None = None
        intro_idx: int | None = None

        # 1. Locate boundaries: 'СОДЕРЖАНИЕ' and 'ВВЕДЕНИЕ'
        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            if toc_start_idx is None and re.match(r"^\s*(?:содержание|оглавление)\b", text, re.IGNORECASE):
                toc_start_idx = i
                continue

            if toc_start_idx is not None and intro_idx is None and re.match(r"^\s*введение\b", text, re.IGNORECASE):
                intro_idx = i
                break

        if toc_start_idx is None:
            violations.append(
                ViolationDTO(
                    rule_id=self.rule_id,
                    severity="ERROR",
                    message="Раздел 'СОДЕРЖАНИЕ' не найден в документе.",
                    location=LocationDTO(item_title="Содержание"),
                    actual_value="Не найдено",
                    expected_value="Наличие раздела 'СОДЕРЖАНИЕ'",
                )
            )
            return violations

        if intro_idx is None:
            violations.append(
                ViolationDTO(
                    rule_id=self.rule_id,
                    severity="ERROR",
                    message="Раздел 'ВВЕДЕНИЕ' не найден после раздела 'СОДЕРЖАНИЕ'.",
                    location=LocationDTO(item_title="Введение"),
                    actual_value="Не найдено",
                    expected_value="Наличие раздела 'ВВЕДЕНИЕ'",
                )
            )
            return violations

        # 2. Extract and clean TOC lines between 'СОДЕРЖАНИЕ' and 'ВВЕДЕНИЕ'
        toc_entries: list[tuple[int, str, str]] = []  # (paragraph_index, raw_line, cleaned_title)

        for p_idx in range(toc_start_idx + 1, intro_idx):
            p = doc.paragraphs[p_idx]
            raw_text = p.text.strip()
            if not raw_text:
                continue

            for line in raw_text.splitlines():
                line_str = line.strip()
                if not line_str:
                    continue

                # Strip trailing dots/tabs/underscores/dashes and page numbers
                cleaned = re.sub(r"[\.\s\t_—–-]+\d+\s*$", "", line_str)
                cleaned = re.sub(r"[\.\s\t_—–-]+$", "", cleaned).strip()
                if cleaned:
                    toc_entries.append((p_idx, line_str, cleaned))

        # 3. Check forbidden TOC items (п. 9 регламента)
        for p_idx, raw_line, cleaned in toc_entries:
            cleaned_lower = cleaned.lower()
            for forbidden in FORBIDDEN_TOC_ITEMS:
                if forbidden in cleaned_lower:
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=f"В Содержании запрещено указывать элемент: '{cleaned}' (п. 9 регламента).",
                            location=LocationDTO(paragraph_index=p_idx, snippet=raw_line[:60]),
                            actual_value=cleaned,
                            expected_value="Элемент не должен входить в Содержание",
                        )
                    )
                    break

        # 4. Check that all real headings after Введение are present in TOC (п. 11 регламента)
        for i in range(intro_idx + 1, len(doc.paragraphs)):
            p = doc.paragraphs[i]
            if not _is_real_heading(p):
                continue

            real_heading_text = p.text.strip()
            matched = any(matches_heading_fuzzy(real_heading_text, cleaned) for _, _, cleaned in toc_entries)
            if not matched:
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=f"Заголовок документа отсутствует в Содержании: {real_heading_text}",
                        location=LocationDTO(paragraph_index=i, snippet=real_heading_text[:60]),
                        actual_value=real_heading_text,
                        expected_value="Присутствует в Содержании",
                    )
                )

        return violations
