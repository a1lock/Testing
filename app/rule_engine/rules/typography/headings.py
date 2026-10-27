"""Headings format validation rule for Level 1 and Level 2 headings."""

import re

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule


def _is_heading_paragraph(p: ParagraphDTO) -> bool:
    """Determine whether paragraph is a heading by flag or style name."""
    if p.is_heading:
        return True
    style_lower = (p.style_name or "").lower()
    return "heading" in style_lower or "заголовок" in style_lower


def _determine_heading_level(p: ParagraphDTO) -> int | None:
    """Classify heading into Level 1 or Level 2 according to university guidelines.

    Level 1:
        - Style 'Heading 1', 'Заголовок 1'
        - Text starts with a single number ('1 НАЗВАНИЕ', '1. НАЗВАНИЕ', 'ГЛАВА 1')
        - Structural sections ('ВВЕДЕНИЕ', 'ЗАКЛЮЧЕНИЕ', 'СОДЕРЖАНИЕ', etc.)

    Level 2:
        - Style 'Heading 2', 'Заголовок 2'
        - Subsection numbers like '1.1', '2.3', '1.1.2'
    """
    text = p.text.strip()
    if not text:
        return None

    style_lower = (p.style_name or "").lower()

    # Subsection numbering like 1.1, 2.3, 1.1.2 takes precedence for Level 2
    has_sub_number = bool(re.match(r"^\s*(?:подраздел\s+)?\d+(?:\.\d+)+", text, flags=re.IGNORECASE))
    if has_sub_number or "heading 2" in style_lower or "заголовок 2" in style_lower:
        return 2

    # Section numbering like "1 ", "1.", "1 -", "ГЛАВА 1"
    has_single_number = bool(re.match(r"^\s*(?:глава|раздел)?\s*\d+([\.\s]|$)", text, flags=re.IGNORECASE))

    # Structural sections (always Level 1)
    structural_sections = (
        "введение",
        "заключение",
        "аннотация",
        "содержание",
        "список использованных источников",
        "список источников",
        "список литературы",
        "библиографический список",
        "приложение",
    )
    clean_lower = text.lower()
    is_structural = any(clean_lower.startswith(sec) for sec in structural_sections)

    if (
        "heading 1" in style_lower
        or "заголовок 1" in style_lower
        or has_single_number
        or is_structural
    ):
        return 1

    return None


@register_rule("HEADINGS_FORMAT")
class HeadingsFormatRule(BaseRule):
    """Validates formatting requirements for Level 1 and Level 2 headings."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Validate all heading paragraphs for typography and formatting compliance.

        Args:
            doc: Extracted document DTO.
            params: Parameters including 'l1_max_indent_mm' (default 1.0),
                    'l2_expected_indent_mm' (default 12.5),
                    'l2_indent_tolerance_mm' (default 1.5).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        l1_max_indent_mm = float(params.get("l1_max_indent_mm", 1.0))
        l2_expected_indent_mm = float(params.get("l2_expected_indent_mm", 12.5))
        l2_indent_tolerance_mm = float(params.get("l2_indent_tolerance_mm", 1.5))

        violations: list[ViolationDTO] = []

        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            if not _is_heading_paragraph(p):
                continue

            level = _determine_heading_level(p)
            if level is None:
                continue

            snippet = text[:60]

            if level == 1:
                # 1. Level 1 must be UPPERCASE (excluding leading number / chapter)
                title_part = re.sub(
                    r"^\s*(?:глава|раздел)?\s*\d+[\.\s]*", "", text, flags=re.IGNORECASE
                ).strip()

                has_letters = any(c.isalpha() for c in title_part)
                if has_letters and not title_part.isupper():
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message="Заголовок 1 уровня должен быть написан ПРОПИСНЫМИ буквами.",
                            location=LocationDTO(paragraph_index=i, snippet=snippet),
                            actual_value=text,
                            expected_value=text.upper(),
                        )
                    )

                # 2. Level 1 must be without paragraph indent (< 1.0 mm)
                if p.indent_mm >= l1_max_indent_mm:
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=(
                                f"Заголовок 1 уровня должен быть без абзацного отступа. "
                                f"Обнаружен отступ {p.indent_mm:.1f} мм."
                            ),
                            location=LocationDTO(paragraph_index=i, snippet=snippet),
                            actual_value=f"{p.indent_mm:.1f} мм",
                            expected_value="0.0 мм",
                        )
                    )

                # 3. No dot at the end
                if text.endswith("."):
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message="Точка в конце заголовка не допускается.",
                            location=LocationDTO(paragraph_index=i, snippet=snippet),
                            actual_value=text[-10:],
                            expected_value="Без точки в конце",
                        )
                    )

            elif level == 2:
                # 1. Level 2 must NOT be ALL CAPS; must be capitalized lowercase
                title_part = re.sub(
                    r"^\s*(?:подраздел\s+)?\d+(?:\.\d+)+[\.\s]*", "", text, flags=re.IGNORECASE
                ).strip()

                has_letters = any(c.isalpha() for c in title_part)
                if text.isupper() or (has_letters and title_part.isupper()):
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=(
                                "Заголовок 2 уровня должен быть написан с прописной буквы строчными "
                                "(не допускается весь заголовок прописными буквами)."
                            ),
                            location=LocationDTO(paragraph_index=i, snippet=snippet),
                            actual_value=text,
                            expected_value="С прописной буквы строчными",
                        )
                    )
                elif title_part and title_part[0].islower():
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message="Заголовок 2 уровня должен начинаться с прописной буквы.",
                            location=LocationDTO(paragraph_index=i, snippet=snippet),
                            actual_value=text,
                            expected_value="С первой прописной буквы",
                        )
                    )

                # 2. Level 2 must have paragraph indent 12.5 mm (±1.5 mm)
                if abs(p.indent_mm - l2_expected_indent_mm) > l2_indent_tolerance_mm:
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=(
                                f"Заголовок 2 уровня должен иметь абзацный отступ {l2_expected_indent_mm:.1f} мм "
                                f"(допуск ±{l2_indent_tolerance_mm:.1f} мм). "
                                f"Обнаружен отступ {p.indent_mm:.1f} мм."
                            ),
                            location=LocationDTO(paragraph_index=i, snippet=snippet),
                            actual_value=f"{p.indent_mm:.1f} мм",
                            expected_value=f"{l2_expected_indent_mm:.1f} мм",
                        )
                    )

                # 3. No dot at the end
                if text.endswith("."):
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message="Точка в конце заголовка не допускается.",
                            location=LocationDTO(paragraph_index=i, snippet=snippet),
                            actual_value=text[-10:],
                            expected_value="Без точки в конце",
                        )
                    )

        return violations
