"""Code listings validation rule."""

import re

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule

LISTING_CAPTION_REGEX = re.compile(r"^Листинг\s+\d+(?:\.\d+)?\s*[-–—]\s*(.+)$", re.IGNORECASE)


@register_rule("LISTINGS_FORMAT")
class ListingsRule(BaseRule):
    """Validates code listing captions formatting and ensures code is inserted as editable text, not images."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Verify listing captions and check that following paragraph contains editable code text.

        Args:
            doc: Extracted document DTO.
            params: Rule parameters (optional).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        violations: list[ViolationDTO] = []

        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            match = LISTING_CAPTION_REGEX.match(text)
            if not match:
                continue

            # 1. Caption must be left-aligned without indent (< 1.0 mm)
            is_left_aligned = p.alignment in ("LEFT", None)
            is_no_indent = p.indent_mm < 1.0

            if not (is_left_aligned and is_no_indent):
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=(
                            "Подпись листинга должна быть выровнена по левому краю без отступа. "
                            f"Обнаружено выравнивание: {p.alignment or 'по умолчанию'}, "
                            f"отступ: {p.indent_mm:.1f} мм."
                        ),
                        location=LocationDTO(paragraph_index=i, snippet=text[:60]),
                        actual_value=f"alignment={p.alignment}, indent={p.indent_mm:.1f} мм",
                        expected_value="alignment=LEFT, indent < 1.0 мм",
                    )
                )

            # 2. Check the paragraph immediately following the listing caption
            is_empty_or_missing = False
            if i + 1 >= len(doc.paragraphs):
                is_empty_or_missing = True
            else:
                next_p = doc.paragraphs[i + 1]
                if not next_p.text.strip():
                    is_empty_or_missing = True

            if is_empty_or_missing:
                target_idx = i + 1 if i + 1 < len(doc.paragraphs) else i
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message="Листинг кода должен быть вставлен редактируемым текстом, а не рисунком",
                        location=LocationDTO(paragraph_index=target_idx, snippet=text[:60]),
                        actual_value="Пустой абзац (рисунок)",
                        expected_value="Редактируемый текст листинга",
                    )
                )

        return violations
