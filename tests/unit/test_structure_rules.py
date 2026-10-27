"""Unit tests for structure validation rules (required sections, chapters count, TOC matching)."""

import pytest

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RULE_REGISTRY
from app.rule_engine.rules.structure.chapters import ChaptersCountRule
from app.rule_engine.rules.structure.required_sections import RequiredSectionsRule
from app.rule_engine.rules.structure.toc_matching import TocMatchingRule


# ==========================================
# 1. Tests for RequiredSectionsRule (REQUIRED_SECTIONS)
# ==========================================


def test_required_sections_rule_registered():
    """Verify that RequiredSectionsRule is registered in RULE_REGISTRY with REQUIRED_SECTIONS."""
    assert "REQUIRED_SECTIONS" in RULE_REGISTRY
    assert RULE_REGISTRY["REQUIRED_SECTIONS"] is RequiredSectionsRule
    assert RequiredSectionsRule.rule_id == "REQUIRED_SECTIONS"


def test_required_sections_all_present():
    """Test that document containing all mandatory sections produces 0 violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="АННОТАЦИЯ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст аннотации к дипломной работе.", style_name="Normal"),
            ParagraphDTO(text="СОДЕРЖАНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="ВВЕДЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст введения.", style_name="Normal"),
            ParagraphDTO(text="1 АНАЛИТИЧЕСКИЙ РАЗДЕЛ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="ЗАКЛЮЧЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", style_name="Heading 1", is_heading=True),
        ]
    )
    rule = RequiredSectionsRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_required_sections_missing_introduction():
    """Test that missing Introduction (Введение) generates an ERROR violation."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="АННОТАЦИЯ", style_name="Heading 1", is_heading=True),
            # Missing ВВЕДЕНИЕ
            ParagraphDTO(text="1 АНАЛИТИЧЕСКИЙ РАЗДЕЛ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="ЗАКЛЮЧЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="СПИСОК ЛИТЕРАТУРЫ", style_name="Heading 1", is_heading=True),
        ]
    )
    rule = RequiredSectionsRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "REQUIRED_SECTIONS"
    assert v.severity == "ERROR"
    assert "Отсутствует обязательный структурный элемент" in v.message
    assert "ВВЕДЕНИЕ" in v.message
    assert v.location.item_title == "ВВЕДЕНИЕ"


# ==========================================
# 2. Tests for ChaptersCountRule (CHAPTERS_COUNT)
# ==========================================


def test_chapters_count_rule_registered():
    """Verify that ChaptersCountRule is registered in RULE_REGISTRY with CHAPTERS_COUNT."""
    assert "CHAPTERS_COUNT" in RULE_REGISTRY
    assert RULE_REGISTRY["CHAPTERS_COUNT"] is ChaptersCountRule
    assert ChaptersCountRule.rule_id == "CHAPTERS_COUNT"


def test_chapters_count_three_chapters_with_conclusions():
    """Test 3 chapters, all containing conclusions, producing 0 violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1.1 Обзор существующих решений", style_name="Heading 2", is_heading=True),
            ParagraphDTO(text="Текст подраздела.", style_name="Normal"),
            ParagraphDTO(text="1.2 Выводы по главе 1", style_name="Heading 2", is_heading=True),
            ParagraphDTO(text="2 ПРОЕКТИРОВАНИЕ АРХИТЕКТУРЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст второй главы.", style_name="Normal"),
            ParagraphDTO(text="Выводы: разработана диаграмма классов.", style_name="Normal"),
            ParagraphDTO(text="3 РЕАЛИЗАЦИЯ И ТЕСТИРОВАНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст третьей главы.", style_name="Normal"),
            ParagraphDTO(text="3.3 Вывод по разделу 3", style_name="Heading 2", is_heading=True),
            ParagraphDTO(text="ЗАКЛЮЧЕНИЕ", style_name="Heading 1", is_heading=True),
        ]
    )
    rule = ChaptersCountRule()
    violations = rule.check(doc, {"min_chapters": 3})
    assert len(violations) == 0


def test_chapters_count_two_chapters():
    """Test document with only 2 chapters, generating ERROR for chapter count."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Выводы по главе 1.", style_name="Normal"),
            ParagraphDTO(text="2 ПРОЕКТИРОВАНИЕ СИСТЕМЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Выводы по главе 2.", style_name="Normal"),
            ParagraphDTO(text="ЗАКЛЮЧЕНИЕ", style_name="Heading 1", is_heading=True),
        ]
    )
    rule = ChaptersCountRule()
    violations = rule.check(doc, {"min_chapters": 3})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "CHAPTERS_COUNT"
    assert v.severity == "ERROR"
    assert "Недостаточное количество глав" in v.message
    assert v.actual_value == "2"
    assert v.expected_value == ">= 3"


def test_chapters_count_three_chapters_without_conclusions():
    """Test 3 chapters without any conclusions, producing 3 WARNING violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст первой главы без каких-либо итогов.", style_name="Normal"),
            ParagraphDTO(text="2 ПРОЕКТИРОВАНИЕ АРХИТЕКТУРЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст второй главы без итогов.", style_name="Normal"),
            ParagraphDTO(text="3 РЕАЛИЗАЦИЯ СИСТЕМЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст третьей главы без итогов.", style_name="Normal"),
            ParagraphDTO(text="ЗАКЛЮЧЕНИЕ", style_name="Heading 1", is_heading=True),
        ]
    )
    rule = ChaptersCountRule()
    violations = rule.check(doc, {"min_chapters": 3})

    # Chapter count is valid (3 >= 3), but all 3 chapters lack conclusions
    assert len(violations) == 3
    for v in violations:
        assert v.rule_id == "CHAPTERS_COUNT"
        assert v.severity == "WARNING"
        assert "отсутствуют выводы" in v.message


# ==========================================
# 3. Tests for TocMatchingRule (TOC_MATCHING)
# ==========================================


def test_toc_matching_rule_registered():
    """Verify that TocMatchingRule is registered in RULE_REGISTRY with TOC_MATCHING."""
    assert "TOC_MATCHING" in RULE_REGISTRY
    assert RULE_REGISTRY["TOC_MATCHING"] is TocMatchingRule
    assert TocMatchingRule.rule_id == "TOC_MATCHING"


def test_toc_matching_perfect():
    """Test that perfectly consistent TOC and body headings yield 0 violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="СОДЕРЖАНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1 АРХИТЕКТУРА СИСТЕМЫ ................. 5", style_name="Normal"),
            ParagraphDTO(text="1.1 Обзор аналогов .................... 7", style_name="Normal"),
            ParagraphDTO(text="2 ПРОЕКТИРОВАНИЕ ...................... 15", style_name="Normal"),
            ParagraphDTO(text="ЗАКЛЮЧЕНИЕ ............................ 30", style_name="Normal"),
            ParagraphDTO(text="СПИСОК ИСТОЧНИКОВ ..................... 32", style_name="Normal"),
            ParagraphDTO(text="ВВЕДЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Текст введения.", style_name="Normal"),
            ParagraphDTO(text="1 АРХИТЕКТУРА СИСТЕМЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1.1 Обзор аналогов", style_name="Heading 2", is_heading=True),
            ParagraphDTO(text="2 ПРОЕКТИРОВАНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="ЗАКЛЮЧЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="СПИСОК ИСТОЧНИКОВ", style_name="Heading 1", is_heading=True),
        ]
    )
    rule = TocMatchingRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_toc_matching_forbidden_title_page():
    """Test that including 'Титульный лист' in TOC produces an ERROR violation."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="СОДЕРЖАНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Титульный лист ........................ 1", style_name="Normal"),
            ParagraphDTO(text="1 АРХИТЕКТУРА СИСТЕМЫ ................. 5", style_name="Normal"),
            ParagraphDTO(text="ВВЕДЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1 АРХИТЕКТУРА СИСТЕМЫ", style_name="Heading 1", is_heading=True),
        ]
    )
    rule = TocMatchingRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "TOC_MATCHING"
    assert v.severity == "ERROR"
    assert "запрещено указывать элемент" in v.message
    assert "Титульный лист" in v.message


def test_toc_matching_heading_missing_from_toc():
    """Test that a body heading missing from TOC produces an ERROR violation."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="СОДЕРЖАНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1 АРХИТЕКТУРА СИСТЕМЫ ................. 5", style_name="Normal"),
            # '2 РАЗРАБОТКА И ТЕСТИРОВАНИЕ' is missing in TOC!
            ParagraphDTO(text="ВВЕДЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1 АРХИТЕКТУРА СИСТЕМЫ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="2 РАЗРАБОТКА И ТЕСТИРОВАНИЕ", style_name="Heading 1", is_heading=True),
        ]
    )
    rule = TocMatchingRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "TOC_MATCHING"
    assert v.severity == "ERROR"
    assert "Заголовок документа отсутствует в Содержании" in v.message
    assert "2 РАЗРАБОТКА И ТЕСТИРОВАНИЕ" in v.message


# ==========================================
# 4. Integration Test with RuleEngine
# ==========================================


def test_rule_engine_runs_structure_rules():
    """Verify that RuleEngine runs all structure rules together."""
    config = {
        "REQUIRED_SECTIONS": {"enabled": True},
        "CHAPTERS_COUNT": {"enabled": True},
        "TOC_MATCHING": {"enabled": True},
    }
    engine = RuleEngine(config)

    # Document missing TOC and with only 1 chapter
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="АННОТАЦИЯ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="ВВЕДЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="Выводы по главе 1.", style_name="Normal"),
            ParagraphDTO(text="ЗАКЛЮЧЕНИЕ", style_name="Heading 1", is_heading=True),
            ParagraphDTO(text="СПИСОК ИСТОЧНИКОВ", style_name="Heading 1", is_heading=True),
        ]
    )
    violations = engine.run(doc)

    rule_ids = {v.rule_id for v in violations}
    # CHAPTERS_COUNT reports error (1 chapter < 3)
    assert "CHAPTERS_COUNT" in rule_ids
    # TOC_MATCHING reports error (СОДЕРЖАНИЕ not found)
    assert "TOC_MATCHING" in rule_ids
    # REQUIRED_SECTIONS has 0 errors because all 4 sections are present
    assert "REQUIRED_SECTIONS" not in rule_ids
