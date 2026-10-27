"""Appendices validation rule."""

import re

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule

APPENDIX_HEADER_REGEX = re.compile(r"^\s*ПРИЛОЖЕНИЕ\s+([А-ЯA-Z])\b(.*)$", re.IGNORECASE)


@register_rule("APPENDICES_FORMAT")
class AppendicesRule(BaseRule):
    """Validates that appendices have meaningful titles on the same line or immediate next line."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Verify that every appendix has an informative title.

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

            match = APPENDIX_HEADER_REGEX.match(text)
            if not match:
                continue

            letter = match.group(1).upper()
            remainder = match.group(2).strip()

            # Check if title is present in the same paragraph
            same_line_title = re.sub(r"^[\.\s—–-]+", "", remainder).strip()
            has_title = False

            if same_line_title:
                has_title = True
            else:
                # Check next paragraph
                if i + 1 < len(doc.paragraphs):
                    next_p = doc.paragraphs[i + 1]
                    next_text = next_p.text.strip()

                    # Title cannot be empty or another appendix header
                    if next_text and not APPENDIX_HEADER_REGEX.match(next_text):
                        # A title is typically concise (<= 20 words) and not a multi-sentence body paragraph
                        words = next_text.split()
                        if len(words) <= 20:
                            has_title = True

            if not has_title:
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message="Приложение должно иметь содержательное название",
                        location=LocationDTO(
                            paragraph_index=i,
                            item_title=f"Приложение {letter}",
                            snippet=text[:60],
                        ),
                        actual_value=text,
                        expected_value=f"ПРИЛОЖЕНИЕ {letter} — Содержательное название",
                    )
                )

        return violations
