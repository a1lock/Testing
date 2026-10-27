"""Lists formatting validation rule."""

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule


@register_rule("LISTS_FORMAT")
class ListsFormatRule(BaseRule):
    """Validates that document lists are flat (single level) and multi-level lists are not used."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Check all paragraphs for nested (multi-level) lists.

        Args:
            doc: Extracted document DTO.
            params: Rule parameters (optional).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        violations: list[ViolationDTO] = []

        for i, p in enumerate(doc.paragraphs):
            # Level 0 is a standard single-level list; Level 1+ is nested / multi-level
            if p.list_level is not None and p.list_level > 0:
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message="Многоуровневые списки не допускаются",
                        location=LocationDTO(
                            paragraph_index=i,
                            snippet=p.text[:60] if p.text else None,
                        ),
                        actual_value=f"Уровень списка: {p.list_level}",
                        expected_value="Уровень списка <= 0",
                    )
                )

        return violations
