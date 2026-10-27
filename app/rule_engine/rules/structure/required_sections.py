"""Required document structural sections validation rule."""

import re

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule

DEFAULT_REQUIRED_SECTIONS: list[tuple[str, str]] = [
    ("АННОТАЦИЯ", r"^\s*аннотация\b"),
    ("ВВЕДЕНИЕ", r"^\s*введение\b"),
    ("ЗАКЛЮЧЕНИЕ", r"^\s*заключение\b"),
    (
        "СПИСОК ИСТОЧНИКОВ",
        r"^\s*(?:список\s+(?:использованн(?:ых|ой)|используем(?:ой|ых)|основной)?\s*(?:источников(?:\s+и\s+литературы)?|литературы(?:\s+и\s+источников)?)|список\s+(?:источников|литературы)|библиографический\s+список|библиография|литература)\b",
    ),
]


@register_rule("REQUIRED_SECTIONS")
class RequiredSectionsRule(BaseRule):
    """Validates the presence of mandatory structural sections in the document."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Verify that all mandatory structural elements are present.

        Args:
            doc: Extracted document DTO.
            params: Parameters including optional 'required_sections' list of (name, regex) pairs.

        Returns:
            List of detected ViolationDTO instances (empty if all sections are present).
        """
        required = params.get("required_sections", DEFAULT_REQUIRED_SECTIONS)
        found_sections: set[str] = set()

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_lower = (p.style_name or "").lower()
            is_heading_or_caps = (
                p.is_heading
                or text.isupper()
                or "heading" in style_lower
                or "заголовок" in style_lower
                or len(text.split()) <= 6
            )
            if not is_heading_or_caps:
                continue

            for sec_name, pattern in required:
                if sec_name in found_sections:
                    continue
                if re.search(pattern, text, re.IGNORECASE):
                    found_sections.add(sec_name)

        violations: list[ViolationDTO] = []
        for sec_name, _ in required:
            if sec_name not in found_sections:
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=f"Отсутствует обязательный структурный элемент: {sec_name}",
                        location=LocationDTO(item_title=sec_name),
                        actual_value="Не найден",
                        expected_value=f"Наличие раздела '{sec_name}'",
                    )
                )

        return violations
