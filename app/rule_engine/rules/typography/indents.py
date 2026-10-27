"""Paragraph indent validation rule."""

import re

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule

FIGURE_CAPTION_REGEX = re.compile(r"^Рисунок\s+(\d+(?:\.\d+)*)\s*[—–-]\s*(.+)$", re.IGNORECASE)
TABLE_CAPTION_REGEX = re.compile(r"^Таблица\s+(\d+(?:\.\d+)*)\s*[—–-]\s*(.+)$", re.IGNORECASE)


@register_rule("PARAGRAPH_INDENT")
class ParagraphIndentRule(BaseRule):
    """Validates that normal body paragraphs adhere to expected first-line indent."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Check all body paragraphs for correct first line indent in millimeters.

        Args:
            doc: Extracted document DTO.
            params: Parameters including 'expected_mm' (default 12.5) and 'tolerance_mm' (default 1.0).

        Returns:
            List of detected ViolationDTO instances.
        """
        expected_mm = float(params.get("expected_mm", 12.5))
        tolerance_mm = float(params.get("tolerance_mm", 1.0))
        violations: list[ViolationDTO] = []

        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            # 1. Skip empty paragraphs and headings
            if not text or p.is_heading:
                continue

            # 2. Skip paragraphs containing embedded images
            if getattr(p, "has_image", False):
                continue

            # 3. Skip figure captions (governed by FIGURES_FORMAT rule)
            if FIGURE_CAPTION_REGEX.match(text):
                continue

            # Also skip centered figure lines like "Рисунок 1"
            if p.alignment == "CENTER" and re.match(r"^Рисунок\s+\d+", text, re.IGNORECASE):
                continue

            # 4. Skip table captions (governed by TABLES_FORMAT rule)
            if TABLE_CAPTION_REGEX.match(text):
                continue

            # 5. Check indent tolerance
            if abs(p.indent_mm - expected_mm) > tolerance_mm:
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=(
                            f"Неверный абзацный отступ. Требуется {expected_mm} мм, "
                            f"обнаружено {p.indent_mm:.1f} мм."
                        ),
                        location=LocationDTO(
                            paragraph_index=i,
                            snippet=p.text[:60] if len(p.text) > 60 else p.text,
                        ),
                        actual_value=f"{p.indent_mm:.1f} мм",
                        expected_value=f"{expected_mm} мм",
                    )
                )

        return violations
