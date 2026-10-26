"""Orchestrator for executing validation rules against document DTOs."""

import logging

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import ViolationDTO
from app.rule_engine.registry import RULE_REGISTRY

logger = logging.getLogger(__name__)


class RuleEngine:
    """Core rule execution engine orchestrating registered BaseRule strategies."""

    def __init__(self, profile_config: dict | None = None) -> None:
        """Initialize the engine with profile settings.

        Args:
            profile_config: Dictionary mapping rule_id to rule configuration dict.
                Example:
                    {
                        "PARAGRAPH_INDENT": {
                            "enabled": True,
                            "expected_mm": 12.5,
                            "tolerance_mm": 1.0,
                        }
                    }
        """
        self.profile_config: dict = profile_config if profile_config is not None else {}

    def run(self, doc: DocumentDTO) -> list[ViolationDTO]:
        """Run all enabled and registered validation rules against the given document.

        Args:
            doc: Structured DocumentDTO containing document elements.

        Returns:
            List of all detected ViolationDTO instances across all executed rules.
        """
        all_violations: list[ViolationDTO] = []

        for rule_id, rule_settings in self.profile_config.items():
            if not isinstance(rule_settings, dict):
                continue

            if not rule_settings.get("enabled", True):
                continue

            if rule_id not in RULE_REGISTRY:
                logger.warning(
                    "Rule '%s' is enabled in profile config but not registered in RULE_REGISTRY",
                    rule_id,
                )
                continue

            try:
                rule_instance = RULE_REGISTRY[rule_id]()
                violations = rule_instance.check(doc, rule_settings)
                if violations:
                    all_violations.extend(violations)
            except Exception:
                logger.exception("Unexpected error while executing rule '%s'", rule_id)

        return all_violations
