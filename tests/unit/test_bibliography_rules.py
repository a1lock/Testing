"""Unit tests for bibliography validation rules (sources count, composition, cross-references)."""

import pytest

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RULE_REGISTRY
from app.rule_engine.rules.bibliography.cross_references import CrossReferencesRule
from app.rule_engine.rules.bibliography.sources_count import SourcesCountRule
from app.rule_engine.rules.bibliography.utils import (
    extract_sources,
    parse_bracket_content,
    split_document_by_bibliography,
)


def _generate_valid_sources(count: int = 50) -> list[ParagraphDTO]:
    """Generate mock bibliography paragraphs with compliant composition.

    Composition for 50 sources:
      - 5 foreign sources (10% >= 5%)
      - 10 electronic sources with access date (20% <= 50%)
      - 35 domestic printed monographs/articles
    """
    paragraphs: list[ParagraphDTO] = [
        ParagraphDTO(text="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", style_name="Heading 1", is_heading=True)
    ]

    for i in range(1, count + 1):
        if i <= 5:
            # Foreign language literature
            text = f"{i}. Smith J., Brown A. Modern Software Architecture: Principles and Patterns. NY: Springer, 2022. 350 p."
        elif i <= 15:
            # Electronic resource with date of access
            text = f"{i}. Официальная документация FastAPI. URL: https://fastapi.tiangolo.com/ (дата обращения: 15.01.2025)."
        else:
            # Domestic monographs and standard literature
            text = f"{i}. Иванов И. И., Петров П. П. Проектирование информационных систем. — М.: Горячая линия — Телеком, 2021. — 240 с."

        paragraphs.append(ParagraphDTO(text=text, style_name="Normal"))

    return paragraphs


# ==========================================
# 1. Tests for Utility Functions
# ==========================================


def test_parse_bracket_content():
    """Verify parsing of various bracket citation formats."""
    # Single and multiple comma-separated
    assert parse_bracket_content("1") == {1}
    assert parse_bracket_content("1, 3, 5") == {1, 3, 5}
    assert parse_bracket_content("2; 4; 6") == {2, 4, 6}

    # Ranges
    assert parse_bracket_content("3-6") == {3, 4, 5, 6}
    assert parse_bracket_content("10—13") == {10, 11, 12, 13}
    assert parse_bracket_content("20–22") == {20, 21, 22}

    # Citations with page numbers
    assert parse_bracket_content("10, с. 15") == {10}
    assert parse_bracket_content("12, стр. 45-48") == {12}
    assert parse_bracket_content("14, p. 100") == {14}

    # Empty or non-number
    assert parse_bracket_content("") == set()
    assert parse_bracket_content("не число") == set()


def test_split_document_by_bibliography_and_appendices():
    """Test splitting document paragraphs into body and bibliography separated by appendices."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="ВВЕДЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст работы [1].", style_name="Normal"),
            ParagraphDTO(text="СПИСОК ЛИТЕРАТУРЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1. Источник 1", style_name="Normal"),
            ParagraphDTO(text="2. Источник 2", style_name="Normal"),
            ParagraphDTO(text="ПРИЛОЖЕНИЕ А — Код", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="print('hello')", style_name="Normal"),
        ]
    )
    body, bib = split_document_by_bibliography(doc)

    assert len(body) == 2
    assert body[0].text == "ВВЕДЕНИЕ"
    assert len(bib) == 2
    assert bib[0].text == "1. Источник 1"
    assert bib[1].text == "2. Источник 2"

    sources = extract_sources(bib)
    assert len(sources) == 2
    assert sources[1] == "Источник 1"
    assert sources[2] == "Источник 2"


# ==========================================
# 2. Tests for SourcesCountRule (SOURCES_COUNT)
# ==========================================


def test_sources_count_rule_registered():
    """Verify that SourcesCountRule is registered in RULE_REGISTRY with SOURCES_COUNT."""
    assert "SOURCES_COUNT" in RULE_REGISTRY
    assert RULE_REGISTRY["SOURCES_COUNT"] is SourcesCountRule
    assert SourcesCountRule.rule_id == "SOURCES_COUNT"


def test_sources_count_valid_50_sources():
    """Test fully compliant bibliography with 50 sources, >5% foreign, and <50% electronic."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Основной текст работы.", style_name="Normal"),
            *_generate_valid_sources(50),
        ]
    )
    rule = SourcesCountRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_sources_count_insufficient_sources():
    """Test document with only 20 sources triggering ERROR for total count."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Основной текст.", style_name="Normal"),
            *_generate_valid_sources(20),
        ]
    )
    rule = SourcesCountRule()
    violations = rule.check(doc, {"min_count": 50})

    assert len(violations) >= 1
    v_count = next(v for v in violations if "Недостаточное количество источников" in v.message)
    assert v_count.severity == "ERROR"
    assert "20" in v_count.actual_value
    assert "50" in v_count.expected_value


def test_sources_count_missing_access_date_in_electronic_source():
    """Test electronic source missing '(дата обращения: ...)' format."""
    paragraphs: list[ParagraphDTO] = [
        ParagraphDTO(text="СПИСОК ИСТОЧНИКОВ", style_name="Heading 1", is_heading=True)
    ]
    for i in range(1, 51):
        if i == 5:
            # Foreign literature
            text = f"{i}. Tanenbaum A. Structured Computer Organization. Prentice Hall, 2016."
        elif i == 10:
            # Invalid electronic resource: missing (дата обращения: ...)
            text = f"{i}. Docker Documentation. URL: https://docs.docker.com/"
        elif i == 11:
            # Valid electronic resource
            text = f"{i}. Python Docs. URL: https://docs.python.org/ (дата обращения: 10.02.2025)."
        else:
            text = f"{i}. Иванов И. И. Книга {i}. — М.: Наука, 2020."
        paragraphs.append(ParagraphDTO(text=text, style_name="Normal"))

    doc = DocumentDTO(paragraphs=paragraphs)
    rule = SourcesCountRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "SOURCES_COUNT"
    assert v.severity == "ERROR"
    assert "отсутствует дата обращения" in v.message
    assert "[10]" in v.message


def test_sources_count_low_foreign_percent():
    """Test bibliography with 0 foreign sources violating min_foreign_percent."""
    paragraphs: list[ParagraphDTO] = [
        ParagraphDTO(text="СПИСОК ЛИТЕРАТУРЫ", style_name="Heading 1", is_heading=True)
    ]
    for i in range(1, 51):
        # All purely Cyrillic sources without Latin letters
        paragraphs.append(
            ParagraphDTO(text=f"{i}. Сидоров С. С. Монография {i}. — М.: Наука, 2021.", style_name="Normal")
        )

    doc = DocumentDTO(paragraphs=paragraphs)
    rule = SourcesCountRule()
    violations = rule.check(doc, {"min_foreign_percent": 5.0})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "SOURCES_COUNT"
    assert v.severity == "ERROR"
    assert "Недостаточная доля источников на иностранном языке" in v.message


# ==========================================
# 3. Tests for CrossReferencesRule (CROSS_REFERENCES)
# ==========================================


def test_cross_references_rule_registered():
    """Verify that CrossReferencesRule is registered in RULE_REGISTRY with CROSS_REFERENCES."""
    assert "CROSS_REFERENCES" in RULE_REGISTRY
    assert RULE_REGISTRY["CROSS_REFERENCES"] is CrossReferencesRule
    assert CrossReferencesRule.rule_id == "CROSS_REFERENCES"


def test_cross_references_valid():
    """Test that valid matching citations produce 0 violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Обзор технологий приведен в работах [1-3].", style_name="Normal"),
            ParagraphDTO(text="СПИСОК ЛИТЕРАТУРЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1. Источник 1", style_name="Normal"),
            ParagraphDTO(text="2. Источник 2", style_name="Normal"),
            ParagraphDTO(text="3. Источник 3", style_name="Normal"),
        ]
    )
    rule = CrossReferencesRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_cross_references_broken_reference_99():
    """Test citation [99] referencing a non-existent source in bibliography."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Согласно исследованию [1, 99], метод эффективен.", style_name="Normal"),
            ParagraphDTO(text="СПИСОК ИСТОЧНИКОВ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1. Источник 1", style_name="Normal"),
        ]
    )
    rule = CrossReferencesRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "CROSS_REFERENCES"
    assert v.severity == "ERROR"
    assert "Ссылка на несуществующий источник [99]" in v.message


def test_cross_references_unreferenced_source():
    """Test source listed in bibliography but never cited in body text."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="В работе используется методика [1].", style_name="Normal"),
            ParagraphDTO(text="СПИСОК ЛИТЕРАТУРЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1. Источник 1", style_name="Normal"),
            ParagraphDTO(text="2. Источник 2 (не упомянут в тексте)", style_name="Normal"),
        ]
    )
    rule = CrossReferencesRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "CROSS_REFERENCES"
    assert v.severity == "ERROR"
    assert "Источник [2] не имеет ссылок в тексте" in v.message


# ==========================================
# 4. Integration Test with RuleEngine
# ==========================================


def test_rule_engine_runs_bibliography_rules():
    """Verify that RuleEngine runs all bibliography rules together."""
    config = {
        "SOURCES_COUNT": {"enabled": True, "min_count": 5},
        "CROSS_REFERENCES": {"enabled": True},
    }
    engine = RuleEngine(config)

    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Текст с цитированием [1, 99].", style_name="Normal"),
            ParagraphDTO(text="СПИСОК ЛИТЕРАТУРЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1. Источник 1", style_name="Normal"),
        ]
    )
    violations = engine.run(doc)

    rule_ids = {v.rule_id for v in violations}
    # SOURCES_COUNT complains about total sources (1 < 5)
    assert "SOURCES_COUNT" in rule_ids
    # CROSS_REFERENCES complains about [99]
    assert "CROSS_REFERENCES" in rule_ids
