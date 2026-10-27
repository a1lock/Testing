"""Tables format and cross-references validation rule."""

import re

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule

TABLE_CAPTION_REGEX = re.compile(r"^Таблица\s+(\d+(?:\.\d+)*)\s*[—–-]\s*(.+)$", re.IGNORECASE)


@register_rule("TABLES_FORMAT")
class TablesRule(BaseRule):
    """Validates table captions formatting (alignment, indent, dot) and cross-references in text."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Validate table captions and cross-references throughout document body.

        Args:
            doc: Extracted document DTO.
            params: Rule parameters (optional).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        violations: list[ViolationDTO] = []

        # 1. Identify all table captions
        tables: list[tuple[int, str, ParagraphDTO]] = []  # (p_idx, tbl_num, paragraph)
        caption_indices: set[int] = set()

        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            match = TABLE_CAPTION_REGEX.match(text)
            if match:
                tbl_num = match.group(1)
                tables.append((i, tbl_num, p))
                caption_indices.add(i)

                # 2. Check alignment and indent: strictly LEFT / None, without paragraph indent (< 1.0 mm)
                is_left_aligned = p.alignment in ("LEFT", None)
                is_no_indent = p.indent_mm < 1.0

                if not (is_left_aligned and is_no_indent):
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=(
                                f"Подпись таблицы '{tbl_num}' должна быть выровнена по левому краю "
                                f"без абзацного отступа. Обнаружено выравнивание: {p.alignment or 'по умолчанию'}, "
                                f"отступ: {p.indent_mm:.1f} мм."
                            ),
                            location=LocationDTO(paragraph_index=i, snippet=text[:60]),
                            actual_value=f"alignment={p.alignment}, indent={p.indent_mm:.1f} мм",
                            expected_value="alignment=LEFT, indent < 1.0 мм",
                        )
                    )

                # 3. Check trailing dot: prohibited (WARNING if present)
                if text.endswith("."):
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="WARNING",
                            message=f"В конце названия таблицы '{tbl_num}' точка не ставится.",
                            location=LocationDTO(paragraph_index=i, snippet=text[:60]),
                            actual_value=text[-10:],
                            expected_value="Без точки",
                        )
                    )

        # 4. Check cross-references in non-caption text
        body_text = "\n".join(
            p.text for idx, p in enumerate(doc.paragraphs) if idx not in caption_indices
        )

        for p_idx, tbl_num, p in tables:
            caption_text = p.text.strip()
            # Reference patterns: "таблица X", "табл. X", "табл X", "(таблица X)", "(табл. X)"
            ref_pattern = rf"(?:\b|\()(?:\u0442\u0430\u0431\u043b\u0438\u0446[а-я]*|\u0442\u0430\u0431\u043b\.?)\s+{re.escape(tbl_num)}(?!(?:\.\d|\d))"
            if not re.search(ref_pattern, body_text, re.IGNORECASE):
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=f"Отсутствует ссылка на таблицу {tbl_num} в тексте",
                        location=LocationDTO(paragraph_index=p_idx, snippet=caption_text[:60]),
                        actual_value="Ссылка отсутствует",
                        expected_value=f"Ссылка на таблицу {tbl_num}",
                    )
                )

        return violations
