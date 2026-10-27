"""Cross-references validation rule between body text and bibliography."""

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule
from app.rule_engine.rules.bibliography.utils import (
    BRACKET_REF_REGEX,
    extract_sources,
    parse_bracket_content,
    split_document_by_bibliography,
)


@register_rule("CROSS_REFERENCES")
class CrossReferencesRule(BaseRule):
    """Validates that all bibliography citations in body text exist and all sources are cited."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Verify cross-references between body paragraphs and bibliography entries.

        Args:
            doc: Extracted document DTO.
            params: Rule parameters (optional).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        violations: list[ViolationDTO] = []

        body_paragraphs, bib_paragraphs = split_document_by_bibliography(doc)
        sources = extract_sources(bib_paragraphs)
        actual_ids = set(sources.keys())

        # Collect all referenced source IDs from body paragraphs
        referenced_ids: set[int] = set()
        ref_locations: dict[int, list[tuple[int, str]]] = {}  # source_id -> list of (paragraph_idx, snippet)

        for i, p in enumerate(body_paragraphs):
            text = p.text.strip()
            if not text:
                continue

            for match in BRACKET_REF_REGEX.finditer(text):
                content = match.group(1)
                nums = parse_bracket_content(content)
                for num in nums:
                    referenced_ids.add(num)
                    ref_locations.setdefault(num, []).append((i, text[:60]))

        # 1. Broken citations: referenced in body text, but missing in bibliography
        broken_ids = sorted(referenced_ids - actual_ids)
        for num in broken_ids:
            locations = ref_locations.get(num, [(None, None)])
            first_idx, snippet = locations[0]
            violations.append(
                ViolationDTO(
                    rule_id=self.rule_id,
                    severity="ERROR",
                    message=f"Ссылка на несуществующий источник [{num}]",
                    location=LocationDTO(
                        paragraph_index=first_idx,
                        item_title=f"Ссылка [{num}]",
                        snippet=snippet,
                    ),
                    actual_value=f"[{num}]",
                    expected_value="Источник должен присутствовать в библиографии",
                )
            )

        # 2. Unreferenced sources: present in bibliography, but never cited in body text
        # (According to item 18: "актуальные ссылки на все источники")
        if actual_ids:
            unreferenced_ids = sorted(actual_ids - referenced_ids)
            for num in unreferenced_ids:
                source_text = sources.get(num, "")
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=f"Источник [{num}] не имеет ссылок в тексте",
                        location=LocationDTO(
                            item_title=f"Источник [{num}]",
                            snippet=source_text[:60] if source_text else None,
                        ),
                        actual_value=f"[{num}]",
                        expected_value="На каждый источник должна быть ссылка в тексте",
                    )
                )

        return violations
