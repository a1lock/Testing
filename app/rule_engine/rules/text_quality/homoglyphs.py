"""Anti-plagiarism homoglyphs / mixed scripts detection rule."""

import re

from app.domain.dictionaries.homoglyphs import detect_mixed_scripts
from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule


@register_rule("ANTI_PLAGIARISM_HOMOGLYPHS")
class HomoglyphsRule(BaseRule):
    """Validates that words do not mix Cyrillic and Latin alphabets to bypass plagiarism checkers."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Scan all paragraphs for mixed-script homoglyph substitutions.

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

            seen_in_paragraph: set[str] = set()
            for raw_token in text.split():
                # Strip leading and trailing punctuation (quotes, brackets, commas, periods)
                word = re.sub(r"^[^\w\-–—]+|[^\w\-–—]+$", "", raw_token)
                if not word or word in seen_in_paragraph:
                    continue

                if detect_mixed_scripts(word):
                    seen_in_paragraph.add(word)
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=f"Обнаружена попытка подмены символов (смешивание кириллицы и латиницы) в слове: '{word}'",
                            location=LocationDTO(
                                paragraph_index=i,
                                snippet=text[:60],
                            ),
                            actual_value=word,
                            expected_value="Однородный алфавит",
                        )
                    )

        return violations
