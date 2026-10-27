"""Forbidden anglicisms validation rule."""

import json
from pathlib import Path
import re

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule

DEFAULT_DICT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "domain"
    / "dictionaries"
    / "anglicisms.json"
)


@register_rule("FORBIDDEN_ANGLICISMS")
class AnglicismsRule(BaseRule):
    """Validates that document does not contain unacceptable borrowed terms / anglicisms."""

    def __init__(self, dict_path: Path | str | None = None) -> None:
        """Load forbidden anglicisms dictionary from JSON."""
        target_path = Path(dict_path) if dict_path else DEFAULT_DICT_PATH
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                self.anglicisms: dict[str, str] = json.load(f)
        else:
            self.anglicisms = {
                "бэкенд": "серверная часть",
                "фронтенд": "клиентская часть",
                "датасет": "набор данных",
            }

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Scan all paragraphs for forbidden anglicisms and suggest replacements.

        Args:
            doc: Extracted document DTO.
            params: Parameters including optional 'anglicisms' dictionary override.

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        dictionary = params.get("anglicisms", self.anglicisms)
        violations: list[ViolationDTO] = []

        for i, p in enumerate(doc.paragraphs):
            text = p.text
            if not text.strip():
                continue

            for key, suggestion in dictionary.items():
                pattern = rf"\b{re.escape(key)}\b"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    found_word = match.group(0)
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=f"Найден недопустимый англицизм '{found_word}'. Рекомендуется заменить на: '{suggestion}'",
                            location=LocationDTO(
                                paragraph_index=i,
                                snippet=p.text[:60],
                            ),
                            actual_value=found_word,
                            expected_value=suggestion,
                        )
                    )

        return violations
