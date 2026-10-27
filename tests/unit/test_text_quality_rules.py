"""Unit tests for text quality validation rules (lists, homoglyphs, anglicisms)."""

import pytest

from app.domain.dictionaries.homoglyphs import detect_mixed_scripts
from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RULE_REGISTRY
from app.rule_engine.rules.text_quality.anglicisms import AnglicismsRule
from app.rule_engine.rules.text_quality.homoglyphs import HomoglyphsRule
from app.rule_engine.rules.text_quality.lists import ListsFormatRule


# ==========================================
# 1. Tests for ListsFormatRule (LISTS_FORMAT)
# ==========================================


def test_lists_format_rule_registered():
    """Verify that ListsFormatRule is registered in RULE_REGISTRY with LISTS_FORMAT."""
    assert "LISTS_FORMAT" in RULE_REGISTRY
    assert RULE_REGISTRY["LISTS_FORMAT"] is ListsFormatRule
    assert ListsFormatRule.rule_id == "LISTS_FORMAT"


def test_lists_format_base_level_valid():
    """Test single-level list (list_level=0) and non-list paragraphs producing 0 violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Обычный абзац текста.", style_name="Normal", list_level=None),
            ParagraphDTO(text="Первый пункт списка.", style_name="List Bullet", list_level=0),
            ParagraphDTO(text="Второй пункт списка.", style_name="List Bullet", list_level=0),
        ]
    )
    rule = ListsFormatRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_lists_format_nested_level_error():
    """Test nested multi-level list (list_level=1) triggering ERROR violation."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Пункт 1", style_name="List Bullet", list_level=0),
            ParagraphDTO(text="Подпункт 1.1 (вложенный список)", style_name="List Bullet", list_level=1),
        ]
    )
    rule = ListsFormatRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "LISTS_FORMAT"
    assert v.severity == "ERROR"
    assert "Многоуровневые списки не допускаются" in v.message
    assert v.location.paragraph_index == 1


# ==========================================
# 2. Tests for Homoglyphs / Mixed Scripts (ANTI_PLAGIARISM_HOMOGLYPHS)
# ==========================================


def test_detect_mixed_scripts_function():
    """Verify detect_mixed_scripts behavior with various script combinations."""
    # Pure Cyrillic -> False
    assert detect_mixed_scripts("база") is False
    assert detect_mixed_scripts("Архитектура") is False

    # Pure Latin -> False
    assert detect_mixed_scripts("dataset") is False
    assert detect_mixed_scripts("Backend") is False

    # Mixed Cyrillic and Latin -> True
    # 'бaза' has Russian 'б', 'з', 'а' with Latin 'a' at index 1
    mixed_word = "б" + "a" + "за"
    assert detect_mixed_scripts(mixed_word) is True

    # Latin word with Cyrillic 'о' or 'е'
    assert detect_mixed_scripts("mоdel") is True


def test_homoglyphs_rule_registered():
    """Verify that HomoglyphsRule is registered in RULE_REGISTRY with ANTI_PLAGIARISM_HOMOGLYPHS."""
    assert "ANTI_PLAGIARISM_HOMOGLYPHS" in RULE_REGISTRY
    assert RULE_REGISTRY["ANTI_PLAGIARISM_HOMOGLYPHS"] is HomoglyphsRule
    assert HomoglyphsRule.rule_id == "ANTI_PLAGIARISM_HOMOGLYPHS"


def test_homoglyphs_rule_clean_text():
    """Test document with legitimate pure Cyrillic and pure Latin words producing 0 violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="В данной работе используется база данных и dataset для обучения модели.",
                style_name="Normal",
            )
        ]
    )
    rule = HomoglyphsRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_homoglyphs_rule_detects_mixed_script_substitution():
    """Test that mixed-script word 'бaза' (with Latin 'a') triggers an ERROR violation."""
    # 'бaза' with Latin 'a'
    cheating_word = "б" + "a" + "за"
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text=f"В проекте использована {cheating_word} данных PostgreSQL.",
                style_name="Normal",
            )
        ]
    )
    rule = HomoglyphsRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "ANTI_PLAGIARISM_HOMOGLYPHS"
    assert v.severity == "ERROR"
    assert "Обнаружена попытка подмены символов" in v.message
    assert cheating_word in v.message


def test_homoglyphs_rule_allows_hyphenated_technical_terms():
    """Verify that legitimate compound IT terms (IP-адрес, HTTP-сервер, etc.) do NOT trigger violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Схема IP-адресации, внешний HTTP-сервер и настройка DNS-сервера в VLAN-сегменте.",
                style_name="Normal",
            )
        ]
    )
    rule = HomoglyphsRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


# ==========================================
# 3. Tests for AnglicismsRule (FORBIDDEN_ANGLICISMS)
# ==========================================


def test_anglicisms_rule_registered():
    """Verify that AnglicismsRule is registered in RULE_REGISTRY with FORBIDDEN_ANGLICISMS."""
    assert "FORBIDDEN_ANGLICISMS" in RULE_REGISTRY
    assert RULE_REGISTRY["FORBIDDEN_ANGLICISMS"] is AnglicismsRule
    assert AnglicismsRule.rule_id == "FORBIDDEN_ANGLICISMS"


def test_anglicisms_rule_finds_and_suggests():
    """Test that AnglicismsRule finds 'Бэкенд' and suggests 'серверная часть'."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Бэкенд приложения разработан на Python с использованием FastAPI.",
                style_name="Normal",
            )
        ]
    )
    rule = AnglicismsRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "FORBIDDEN_ANGLICISMS"
    assert v.severity == "ERROR"
    assert "Найден недопустимый англицизм 'Бэкенд'" in v.message
    assert "серверная часть" in v.message
    assert v.expected_value == "серверная часть"


def test_anglicisms_rule_clean_text():
    """Test document using recommended Russian terminology without anglicisms."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Серверная часть и клиентская часть системы обрабатывают подготовленный набор данных.",
                style_name="Normal",
            )
        ]
    )
    rule = AnglicismsRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


# ==========================================
# 4. Integration Test with RuleEngine
# ==========================================


def test_rule_engine_runs_text_quality_rules():
    """Verify that RuleEngine runs all text quality rules together."""
    config = {
        "LISTS_FORMAT": {"enabled": True},
        "ANTI_PLAGIARISM_HOMOGLYPHS": {"enabled": True},
        "FORBIDDEN_ANGLICISMS": {"enabled": True},
    }
    engine = RuleEngine(config)

    cheating_word = "б" + "a" + "за"
    doc = DocumentDTO(
        paragraphs=[
            # Multi-level list
            ParagraphDTO(text="Вложенный список", style_name="Normal", list_level=2),
            # Homoglyph
            ParagraphDTO(text=f"Слово {cheating_word} здесь.", style_name="Normal"),
            # Anglicism
            ParagraphDTO(text="Разработан новый фронтенд.", style_name="Normal"),
        ]
    )
    violations = engine.run(doc)

    rule_ids = {v.rule_id for v in violations}
    assert "LISTS_FORMAT" in rule_ids
    assert "ANTI_PLAGIARISM_HOMOGLYPHS" in rule_ids
    assert "FORBIDDEN_ANGLICISMS" in rule_ids
