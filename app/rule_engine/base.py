"""Base class for all rule engine validation rules."""

from abc import ABC, abstractmethod

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import ViolationDTO


class BaseRule(ABC):
    """Abstract base class for validation rules following the Strategy pattern."""

    rule_id: str = ""

    @abstractmethod
    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Execute the validation rule against the extracted document DTO.

        Args:
            doc: The structured DocumentDTO containing paragraphs, tables, etc.
            params: Rule-specific configuration parameters from the active profile.

        Returns:
            A list of detected ViolationDTO instances (empty if compliant).
        """
        pass
