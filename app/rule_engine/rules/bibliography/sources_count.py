"""Sources count and bibliography composition validation rule."""

import re

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule
from app.rule_engine.rules.bibliography.utils import (
    extract_sources,
    split_document_by_bibliography,
)

ELECTRONIC_SOURCE_REGEX = re.compile(r"\bURL\b|https?://", re.IGNORECASE)
ACCESS_DATE_REGEX = re.compile(r"\(дата обращения:?.*?\)", re.IGNORECASE)


@register_rule("SOURCES_COUNT")
class SourcesCountRule(BaseRule):
    """Validates bibliography volume, foreign literature proportion, electronic resources quota and access dates."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Validate bibliography sources count, composition and metadata.

        Args:
            doc: Extracted document DTO.
            params: Parameters including 'min_count' (default 50),
                    'min_foreign_percent' (default 5.0),
                    'max_electronic_percent' (default 50.0).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        min_count = int(params.get("min_count", 50))
        min_foreign_percent = float(params.get("min_foreign_percent", 5.0))
        max_electronic_percent = float(params.get("max_electronic_percent", 50.0))

        violations: list[ViolationDTO] = []

        _, bib_paragraphs = split_document_by_bibliography(doc)
        sources = extract_sources(bib_paragraphs)
        total_sources = len(sources)

        # 1. Check total number of sources
        if total_sources < min_count:
            violations.append(
                ViolationDTO(
                    rule_id=self.rule_id,
                    severity="ERROR",
                    message=(
                        f"Недостаточное количество источников в списке литературы. "
                        f"Требуется минимум {min_count}, обнаружено {total_sources}."
                    ),
                    location=LocationDTO(item_title="Список источников"),
                    actual_value=str(total_sources),
                    expected_value=f">= {min_count}",
                )
            )

        if total_sources == 0:
            return violations

        # 2. Check foreign sources proportion
        foreign_count = sum(
            1 for text in sources.values() if re.search(r"[A-Za-z]", text)
        )
        foreign_percent = (foreign_count / total_sources) * 100.0

        if foreign_percent < min_foreign_percent:
            violations.append(
                ViolationDTO(
                    rule_id=self.rule_id,
                    severity="ERROR",
                    message=(
                        f"Недостаточная доля источников на иностранном языке: {foreign_percent:.1f}%. "
                        f"Требуется минимум {min_foreign_percent:.1f}% (обнаружено {foreign_count} из {total_sources})."
                    ),
                    location=LocationDTO(item_title="Список источников"),
                    actual_value=f"{foreign_percent:.1f}%",
                    expected_value=f">= {min_foreign_percent:.1f}%",
                )
            )

        # 3. Check electronic sources proportion and access dates
        electronic_count = 0
        for num, text in sources.items():
            if ELECTRONIC_SOURCE_REGEX.search(text):
                electronic_count += 1

                # 4. Check date of access: r"\(дата обращения:.*?\)"
                if not ACCESS_DATE_REGEX.search(text):
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=(
                                f"У электронного источника [{num}] отсутствует дата обращения. "
                                f"Требуется формат: (дата обращения: ДД.ММ.ГГГГ)."
                            ),
                            location=LocationDTO(
                                item_title=f"Источник [{num}]",
                                snippet=text[:60],
                            ),
                            actual_value="Дата обращения отсутствует",
                            expected_value="(дата обращения: ...)",
                        )
                    )

        electronic_percent = (electronic_count / total_sources) * 100.0
        if electronic_percent > max_electronic_percent:
            violations.append(
                ViolationDTO(
                    rule_id=self.rule_id,
                    severity="ERROR",
                    message=(
                        f"Превышена максимальная доля электронных ресурсов: {electronic_percent:.1f}%. "
                        f"Допускается не более {max_electronic_percent:.1f}% (обнаружено {electronic_count} из {total_sources})."
                    ),
                    location=LocationDTO(item_title="Список источников"),
                    actual_value=f"{electronic_percent:.1f}%",
                    expected_value=f"<= {max_electronic_percent:.1f}%",
                )
            )

        return violations
