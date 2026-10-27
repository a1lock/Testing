import logging
from typing import Any

from app.adapters.extractors.docx.document_parser import DocxExtractor
from app.api.schemas.report import LocationDTO as LocationSchema, ViolationSchema
from app.domain.dto.violation import ViolationDTO
from app.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Document compliance validation pipeline orchestrating extraction and rule checking."""

    def __init__(self) -> None:
        self.extractor = DocxExtractor()

    def process_file(
        self,
        file_path: str,
        profile_config: dict[str, Any],
    ) -> tuple[bool, int, int, list[dict[str, Any]], dict[str, int]]:
        """
        Executes end-to-end extraction and rule validation for a .docx document.

        Args:
            file_path: Filesystem path to the .docx document.
            profile_config: Rule configurations dictionary.

        Returns:
            tuple containing:
                - is_valid (bool): True if total_errors == 0, False otherwise.
                - total_errors (int): Count of violations with severity == 'ERROR'.
                - total_warnings (int): Count of violations with severity == 'WARNING'.
                - violations_dict_list (list[dict]): Serialized violations according to ViolationSchema.
                - stats (dict): Document statistics: total_paragraphs, total_tables, total_sections.
        """
        # 1. Extract DTO
        doc_dto = self.extractor.extract(file_path)

        # 2. Instantiate engine
        engine = RuleEngine(profile_config)

        # 3. Run validation
        violations: list[ViolationDTO] = engine.run(doc_dto)

        # 4. Calculate metrics
        total_errors = sum(1 for v in violations if v.severity == "ERROR")
        total_warnings = sum(1 for v in violations if v.severity == "WARNING")
        is_valid = total_errors == 0

        # Serialize violations according to ViolationSchema
        violations_dict_list: list[dict[str, Any]] = []
        for v in violations:
            loc = v.location
            loc_schema = LocationSchema(
                page_number=loc.page_number if loc else None,
                paragraph_index=loc.paragraph_index if loc else None,
                item_title=loc.item_title if loc else None,
                snippet=loc.snippet if loc else None,
            )
            violation_schema = ViolationSchema(
                rule_id=v.rule_id,
                severity=v.severity,
                message=v.message,
                location=loc_schema,
                actual_value=v.actual_value,
                expected_value=v.expected_value,
            )
            violations_dict_list.append(violation_schema.model_dump())

        stats = {
            "total_paragraphs": len(doc_dto.paragraphs),
            "total_tables": len(doc_dto.tables),
            "total_sections": 1,
        }

        # 5. Return tuple
        return is_valid, total_errors, total_warnings, violations_dict_list, stats
