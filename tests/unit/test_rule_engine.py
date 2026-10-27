"""Unit tests for the RuleEngine and ParagraphIndentRule."""

import pytest

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.domain.dto.violation import ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RULE_REGISTRY, register_rule
from app.rule_engine.rules.typography.indents import ParagraphIndentRule


def test_registry_contains_paragraph_indent_rule():
    """Verify that ParagraphIndentRule is properly registered in RULE_REGISTRY."""
    assert "PARAGRAPH_INDENT" in RULE_REGISTRY
    assert RULE_REGISTRY["PARAGRAPH_INDENT"] is ParagraphIndentRule
    assert ParagraphIndentRule.rule_id == "PARAGRAPH_INDENT"


def test_paragraph_indent_rule_valid_indent():
    """Test that paragraphs with correct indent (12.5 mm) produce no violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Это первый корректный абзац документа.",
                style_name="Normal",
                indent_mm=12.5,
                is_heading=False,
            ),
            ParagraphDTO(
                text="Это второй корректный абзац документа с допустимой погрешностью.",
                style_name="Normal",
                indent_mm=12.0,  # Within 1.0 mm tolerance of 12.5 mm
                is_heading=False,
            ),
        ]
    )
    rule = ParagraphIndentRule()
    violations = rule.check(doc, {"expected_mm": 12.5, "tolerance_mm": 1.0})
    assert len(violations) == 0


def test_paragraph_indent_rule_invalid_indent():
    """Test that a paragraph with erroneous indent (0.0 mm) generates a violation."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Абзац без красной строки, с нулевым отступом.",
                style_name="Normal",
                indent_mm=0.0,
                is_heading=False,
            )
        ]
    )
    rule = ParagraphIndentRule()
    violations = rule.check(doc, {"expected_mm": 12.5, "tolerance_mm": 1.0})

    assert len(violations) == 1
    v = violations[0]
    assert isinstance(v, ViolationDTO)
    assert v.rule_id == "PARAGRAPH_INDENT"
    assert v.severity == "ERROR"
    assert v.actual_value == "0.0 мм"
    assert v.expected_value == "12.5 мм"
    assert "Неверный абзацный отступ. Требуется 12.5 мм, обнаружено 0.0 мм." in v.message
    assert v.location.paragraph_index == 0
    assert v.location.snippet == "Абзац без красной строки, с нулевым отступом."


def test_paragraph_indent_rule_skips_headings_and_empty():
    """Test that headings and blank paragraphs are skipped even with 0.0 mm indent."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="ГЛАВА 1. ВВЕДЕНИЕ",
                style_name="Heading 1",
                indent_mm=0.0,
                is_heading=True,
            ),
            ParagraphDTO(
                text="   \n\t  ",
                style_name="Normal",
                indent_mm=0.0,
                is_heading=False,
            ),
            ParagraphDTO(
                text="Нормальный абзац с корректным отступом.",
                style_name="Normal",
                indent_mm=12.5,
                is_heading=False,
            ),
        ]
    )
    rule = ParagraphIndentRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_paragraph_indent_rule_tolerance_boundaries():
    """Test tolerance edge cases: within boundary passes, exceeding boundary fails."""
    rule = ParagraphIndentRule()
    params = {"expected_mm": 12.5, "tolerance_mm": 1.0}

    # Within tolerance: 11.5 mm (abs diff = 1.0 <= 1.0) and 13.5 mm (abs diff = 1.0 <= 1.0)
    doc_boundary_ok = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Lower boundary", style_name="Normal", indent_mm=11.5),
            ParagraphDTO(text="Upper boundary", style_name="Normal", indent_mm=13.5),
        ]
    )
    assert len(rule.check(doc_boundary_ok, params)) == 0

    # Outside tolerance: 11.4 mm and 13.6 mm
    doc_boundary_fail = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Below boundary", style_name="Normal", indent_mm=11.4),
            ParagraphDTO(text="Above boundary", style_name="Normal", indent_mm=13.6),
        ]
    )
    violations = rule.check(doc_boundary_fail, params)
    assert len(violations) == 2
    assert violations[0].location.paragraph_index == 0
    assert violations[1].location.paragraph_index == 1


def test_paragraph_indent_rule_snippet_truncation():
    """Test that snippets longer than 60 chars are truncated to exactly 60 chars."""
    long_text = "А" * 100
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text=long_text, style_name="Normal", indent_mm=0.0),
            ParagraphDTO(text="Короткий текст", style_name="Normal", indent_mm=0.0),
        ]
    )
    rule = ParagraphIndentRule()
    violations = rule.check(doc, {})

    assert len(violations) == 2
    assert violations[0].location.snippet == "А" * 60
    assert len(violations[0].location.snippet) == 60
    assert violations[1].location.snippet == "Короткий текст"


def test_rule_engine_runs_enabled_rule():
    """Test that RuleEngine runs enabled rules and collects violations."""
    config = {
        "PARAGRAPH_INDENT": {
            "enabled": True,
            "expected_mm": 12.5,
            "tolerance_mm": 1.0,
        }
    }
    engine = RuleEngine(config)
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Ошибка красной строки",
                style_name="Normal",
                indent_mm=0.0,
            )
        ]
    )
    violations = engine.run(doc)

    assert len(violations) == 1
    assert violations[0].rule_id == "PARAGRAPH_INDENT"
    assert violations[0].severity == "ERROR"


def test_rule_engine_skips_disabled_rule():
    """Test that RuleEngine skips rules configured with enabled: False."""
    config = {
        "PARAGRAPH_INDENT": {
            "enabled": False,
            "expected_mm": 12.5,
        }
    }
    engine = RuleEngine(config)
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Этот абзац имеет отступ 0, но проверка отключена.",
                style_name="Normal",
                indent_mm=0.0,
            )
        ]
    )
    violations = engine.run(doc)
    assert len(violations) == 0


def test_rule_engine_ignores_unregistered_rule(caplog):
    """Test that unknown rules are gracefully skipped without crashing."""
    config = {
        "NON_EXISTENT_RULE": {
            "enabled": True,
        }
    }
    engine = RuleEngine(config)
    doc = DocumentDTO(paragraphs=[])
    violations = engine.run(doc)
    assert len(violations) == 0


def test_rule_engine_fault_isolation(caplog):
    """Test that an unexpected exception in one rule does not break other rules."""

    @register_rule("CRASHING_RULE_TEST")
    class CrashingRule(BaseRule):
        def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
            raise RuntimeError("Unexpected boom in CrashingRule!")

    try:
        config = {
            "CRASHING_RULE_TEST": {"enabled": True},
            "PARAGRAPH_INDENT": {"enabled": True, "expected_mm": 12.5},
        }
        engine = RuleEngine(config)
        doc = DocumentDTO(
            paragraphs=[
                ParagraphDTO(
                    text="Текст с ошибкой отступа",
                    style_name="Normal",
                    indent_mm=0.0,
                )
            ]
        )
        violations = engine.run(doc)

        # CrashingRule failed safely, but ParagraphIndentRule still succeeded
        assert len(violations) == 1
        assert violations[0].rule_id == "PARAGRAPH_INDENT"
    finally:
        # Clean up temporary test rule
        RULE_REGISTRY.pop("CRASHING_RULE_TEST", None)


def test_rule_engine_empty_config_and_empty_document():
    """Test RuleEngine with empty configuration and empty document."""
    engine = RuleEngine()
    assert engine.profile_config == {}
    violations = engine.run(DocumentDTO())
    assert violations == []


def test_paragraph_indent_rule_skips_figure_and_table_captions():
    """Verify that figure and table captions and image paragraphs do not trigger indent errors."""
    doc = DocumentDTO(
        paragraphs=[
            # Figure caption: should be skipped
            ParagraphDTO(
                text="Рисунок 1 – Настройка оборудования",
                style_name="Normal",
                indent_mm=0.0,
                alignment="CENTER",
            ),
            # Table caption: should be skipped
            ParagraphDTO(
                text="Таблица 2 – План адресации для подсети",
                style_name="Normal",
                indent_mm=0.0,
                alignment="LEFT",
            ),
            # Embedded image paragraph: should be skipped
            ParagraphDTO(
                text="",
                style_name="Normal",
                indent_mm=0.0,
                has_image=True,
            ),
            # Regular text paragraph starting with 'Рисунок 1' but without dash: MUST be checked!
            ParagraphDTO(
                text="Рисунок 1 демонстрирует общую схему взаимодействия маршрутизаторов.",
                style_name="Normal",
                indent_mm=0.0,  # Missing indent -> violation!
            ),
        ]
    )
    rule = ParagraphIndentRule()
    violations = rule.check(doc, {"expected_mm": 12.5, "tolerance_mm": 1.0})

    assert len(violations) == 1
    assert violations[0].rule_id == "PARAGRAPH_INDENT"
    assert "Рисунок 1 демонстрирует" in violations[0].location.snippet
