"""Chapters count and conclusions validation rule."""

import re

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule


@register_rule("CHAPTERS_COUNT")
class ChaptersCountRule(BaseRule):
    """Validates that the document has at least min_chapters and each has conclusions."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Verify the number of main chapters and presence of conclusions in each.

        Args:
            doc: Extracted document DTO.
            params: Parameters including 'min_chapters' (default 3) and
                    'conclusions_severity' (default 'WARNING').

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        min_chapters = int(params.get("min_chapters", 3))
        conclusions_severity = str(params.get("conclusions_severity", "WARNING"))
        violations: list[ViolationDTO] = []

        # Find all numbered Level 1 chapters
        chapters: list[tuple[int, ParagraphDTO]] = []

        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            style_lower = (p.style_name or "").lower()
            is_heading_candidate = (
                p.is_heading
                or "heading" in style_lower
                or "заголовок" in style_lower
                or text.isupper()
            )
            if not is_heading_candidate:
                continue

            # Must not be a subsection like 1.1 or 2.3
            if re.match(r"^\s*(?:подраздел\s+)?\d+\.\d+", text, re.IGNORECASE):
                continue

            # Must start with a chapter number: "1 ", "1.", "ГЛАВА 1", "РАЗДЕЛ 1"
            if re.match(r"^\s*(?:глава|раздел)?\s*\d+[\.\s]+", text, re.IGNORECASE):
                chapters.append((i, p))

        # 1. Check chapter count
        if len(chapters) < min_chapters:
            violations.append(
                ViolationDTO(
                    rule_id=self.rule_id,
                    severity="ERROR",
                    message=(
                        f"Недостаточное количество глав в основной части работы. "
                        f"Требуется минимум {min_chapters}, обнаружено {len(chapters)}."
                    ),
                    location=LocationDTO(item_title="Главы основной части"),
                    actual_value=str(len(chapters)),
                    expected_value=f">= {min_chapters}",
                )
            )

        # 2. Check conclusions for each chapter
        for k, (ch_idx, ch_p) in enumerate(chapters):
            start_idx = ch_idx + 1
            end_idx = chapters[k + 1][0] if k + 1 < len(chapters) else len(doc.paragraphs)

            has_conclusions = False
            for p_idx in range(start_idx, end_idx):
                para = doc.paragraphs[p_idx]
                para_text = para.text.strip()
                if not para_text:
                    continue

                # Stop searching if structural conclusion section is reached
                if re.match(r"^\s*(?:заключение|список|приложение)\b", para_text, re.IGNORECASE):
                    break

                # Check for word "Вывод" / "Выводы"
                if re.search(r"\bвывод[ыа]?(?:ми|ов)?\b", para_text, re.IGNORECASE):
                    has_conclusions = True
                    break

            if not has_conclusions:
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity=conclusions_severity,
                        message=f"В главе '{ch_p.text.strip()}' отсутствуют выводы.",
                        location=LocationDTO(
                            paragraph_index=ch_idx,
                            snippet=ch_p.text.strip()[:60],
                        ),
                        actual_value="Выводы отсутствуют",
                        expected_value="Наличие выводов в конце главы",
                    )
                )

        return violations
