"""Unit tests for typography and headings validation rules."""

import pytest
from docx import Document
from docx.shared import Mm

from app.adapters.extractors.docx.document_parser import DocxExtractor
from app.domain.dto.document import DocumentDTO, ParagraphDTO, RunDTO
from app.domain.dto.violation import ViolationDTO
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RULE_REGISTRY
from app.rule_engine.rules.typography.fonts import MainTextFontRule
from app.rule_engine.rules.typography.headings import HeadingsFormatRule
from app.rule_engine.rules.typography.margins import MarginsRule


# ==========================================
# 1. Tests for MarginsRule (PAGE_MARGINS)
# ==========================================


def test_margins_rule_registered():
    """Verify that MarginsRule is registered in RULE_REGISTRY with PAGE_MARGINS."""
    assert "PAGE_MARGINS" in RULE_REGISTRY
    assert RULE_REGISTRY["PAGE_MARGINS"] is MarginsRule
    assert MarginsRule.rule_id == "PAGE_MARGINS"


def test_margins_rule_valid():
    """Test that correct margins (30/15/20/20 mm) produce zero violations."""
    doc = DocumentDTO(
        margin_left_mm=30.0,
        margin_right_mm=15.0,
        margin_top_mm=20.0,
        margin_bottom_mm=20.0,
    )
    rule = MarginsRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_margins_rule_within_tolerance():
    """Test that margins within default tolerance (±1.0 mm) produce zero violations."""
    doc = DocumentDTO(
        margin_left_mm=30.8,
        margin_right_mm=14.2,
        margin_top_mm=20.5,
        margin_bottom_mm=19.5,
    )
    rule = MarginsRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_margins_rule_invalid_margins():
    """Test that erroneous margins (20/20/20/20 mm) trigger ERROR violations for left and right."""
    doc = DocumentDTO(
        margin_left_mm=20.0,  # Expected 30.0 (diff 10.0 > 1.0)
        margin_right_mm=20.0,  # Expected 15.0 (diff 5.0 > 1.0)
        margin_top_mm=20.0,  # Expected 20.0 (diff 0.0 <= 1.0)
        margin_bottom_mm=20.0,  # Expected 20.0 (diff 0.0 <= 1.0)
    )
    rule = MarginsRule()
    violations = rule.check(doc, {})

    assert len(violations) == 2

    # Check left margin violation
    v_left = next(v for v in violations if "левое" in v.message)
    assert v_left.rule_id == "PAGE_MARGINS"
    assert v_left.severity == "ERROR"
    assert v_left.actual_value == "20.0 мм"
    assert v_left.expected_value == "30.0 мм"
    assert "30.0" in v_left.message

    # Check right margin violation
    v_right = next(v for v in violations if "правое" in v.message)
    assert v_right.rule_id == "PAGE_MARGINS"
    assert v_right.severity == "ERROR"
    assert v_right.actual_value == "20.0 мм"
    assert v_right.expected_value == "15.0 мм"
    assert "15.0" in v_right.message


def test_margins_rule_missing_margins():
    """Test that undefined (None) margins produce ERROR violations."""
    doc = DocumentDTO(
        margin_left_mm=None,
        margin_right_mm=15.0,
        margin_top_mm=20.0,
        margin_bottom_mm=20.0,
    )
    rule = MarginsRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "PAGE_MARGINS"
    assert v.severity == "ERROR"
    assert v.actual_value == "Не определено"
    assert "Не задан размер поля" in v.message


# ==========================================
# 2. Tests for MainTextFontRule (MAIN_TEXT_FONT)
# ==========================================


def test_main_text_font_rule_registered():
    """Verify that MainTextFontRule is registered in RULE_REGISTRY with MAIN_TEXT_FONT."""
    assert "MAIN_TEXT_FONT" in RULE_REGISTRY
    assert RULE_REGISTRY["MAIN_TEXT_FONT"] is MainTextFontRule
    assert MainTextFontRule.rule_id == "MAIN_TEXT_FONT"


def test_main_text_font_rule_valid():
    """Test that body paragraphs with expected 14 pt font pass without violations."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Обычный абзац текста со шрифтом 14 пт.",
                style_name="Normal",
                is_heading=False,
                runs=[
                    RunDTO(text="Обычный абзац ", font_size_pt=14.0),
                    RunDTO(text="текста со шрифтом 14 пт.", font_size_pt=14.0),
                ],
            )
        ]
    )
    rule = MainTextFontRule()
    violations = rule.check(doc, {"expected_size_pt": 14.0, "tolerance_pt": 0.5})
    assert len(violations) == 0


def test_main_text_font_rule_invalid_size_and_deduplication():
    """Test that runs with wrong font size produce violations and deduplicate per paragraph."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Первый абзац с несколькими словами 12 пт.",
                style_name="Normal",
                is_heading=False,
                runs=[
                    RunDTO(text="Первый ", font_size_pt=12.0),
                    RunDTO(text="абзац ", font_size_pt=12.0),
                    RunDTO(text="с несколькими ", font_size_pt=12.0),
                    RunDTO(text="словами 12 пт.", font_size_pt=12.0),
                ],
            )
        ]
    )
    rule = MainTextFontRule()
    violations = rule.check(doc, {"expected_size_pt": 14.0, "tolerance_pt": 0.5})

    # Exactly 1 violation should be produced for this paragraph, not 4
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "MAIN_TEXT_FONT"
    assert v.severity == "ERROR"
    assert v.location.paragraph_index == 0
    assert "14.0 пт" in v.message
    assert "12.0 пт" in v.message
    assert v.actual_value == "12.0 пт"
    assert v.expected_value == "14.0 пт"


def test_main_text_font_rule_skips_headings_and_empty():
    """Test that headings and empty paragraphs are ignored by MainTextFontRule."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="ГЛАВА 1. ВВЕДЕНИЕ",
                style_name="Heading 1",
                is_heading=True,
                runs=[RunDTO(text="ГЛАВА 1. ВВЕДЕНИЕ", font_size_pt=16.0)],
            ),
            ParagraphDTO(
                text="   \n\t ",
                style_name="Normal",
                is_heading=False,
                runs=[RunDTO(text="   ", font_size_pt=10.0)],
            ),
        ]
    )
    rule = MainTextFontRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


# ==========================================
# 3. Tests for HeadingsFormatRule (HEADINGS_FORMAT)
# ==========================================


def test_headings_format_rule_registered():
    """Verify that HeadingsFormatRule is registered in RULE_REGISTRY with HEADINGS_FORMAT."""
    assert "HEADINGS_FORMAT" in RULE_REGISTRY
    assert RULE_REGISTRY["HEADINGS_FORMAT"] is HeadingsFormatRule
    assert HeadingsFormatRule.rule_id == "HEADINGS_FORMAT"


def test_headings_format_level1_valid():
    """Test correct Level 1 heading: '1 АРХИТЕКТУРА СИСТЕМЫ' (no indent, uppercase, no dot)."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="1 АРХИТЕКТУРА СИСТЕМЫ",
                style_name="Heading 1",
                is_heading=True,
                indent_mm=0.0,
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_headings_format_level1_structural_section_valid():
    """Test correct structural Level 1 heading 'ВВЕДЕНИЕ' (no indent, uppercase, no dot)."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="ВВЕДЕНИЕ",
                style_name="Normal",
                is_heading=True,
                indent_mm=0.0,
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_headings_format_level1_invalid_lowercase_and_dot():
    """Test erroneous Level 1 heading: '1 Архитектура системы.' (lowercase and trailing dot)."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="1 Архитектура системы.",
                style_name="Heading 1",
                is_heading=True,
                indent_mm=0.0,
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})

    assert len(violations) >= 2
    # Verify uppercase violation exists
    v_caps = next(v for v in violations if "ПРОПИСНЫМИ" in v.message)
    assert v_caps.severity == "ERROR"
    assert v_caps.rule_id == "HEADINGS_FORMAT"
    assert v_caps.location.paragraph_index == 0

    # Verify dot violation exists
    v_dot = next(v for v in violations if "Точка" in v.message)
    assert v_dot.severity == "ERROR"
    assert v_dot.rule_id == "HEADINGS_FORMAT"
    assert v_dot.location.paragraph_index == 0


def test_headings_format_level1_invalid_indent():
    """Test erroneous Level 1 heading with an illegal first-line indent."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="1 АРХИТЕКТУРА СИСТЕМЫ",
                style_name="Heading 1",
                is_heading=True,
                indent_mm=12.5,  # Violates indent_mm < 1.0
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "HEADINGS_FORMAT"
    assert v.severity == "ERROR"
    assert "без абзацного отступа" in v.message
    assert v.actual_value == "12.5 мм"
    assert v.expected_value == "0.0 мм"


def test_headings_format_level2_valid():
    """Test correct Level 2 heading: '1.1 Обзор аналогов' (indent 12.5 mm, capitalized lowercase, no dot)."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="1.1 Обзор аналогов",
                style_name="Heading 2",
                is_heading=True,
                indent_mm=12.5,
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_headings_format_level2_invalid_all_caps():
    """Test erroneous Level 2 heading written in ALL CAPS: '1.1 ОБЗОР АНАЛОГОВ'."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="1.1 ОБЗОР АНАЛОГОВ",
                style_name="Heading 2",
                is_heading=True,
                indent_mm=12.5,
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "HEADINGS_FORMAT"
    assert v.severity == "ERROR"
    assert "строчными" in v.message


def test_headings_format_level2_invalid_indent():
    """Test erroneous Level 2 heading missing required 12.5 mm indent."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="1.1 Обзор аналогов",
                style_name="Heading 2",
                is_heading=True,
                indent_mm=0.0,  # Missing 12.5 mm indent
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "HEADINGS_FORMAT"
    assert v.severity == "ERROR"
    assert "12.5 мм" in v.message


def test_headings_format_level2_invalid_dot():
    """Test erroneous Level 2 heading with trailing dot."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="1.1 Обзор аналогов.",
                style_name="Heading 2",
                is_heading=True,
                indent_mm=12.5,
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "HEADINGS_FORMAT"
    assert v.severity == "ERROR"
    assert "Точка" in v.message


def test_headings_format_skips_non_headings():
    """Test that normal non-heading paragraphs are skipped by HeadingsFormatRule."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Обычный текст документа.",
                style_name="Normal",
                is_heading=False,
                indent_mm=12.5,
            )
        ]
    )
    rule = HeadingsFormatRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


# ==========================================
# 4. Extractor and RuleEngine Integration Tests
# ==========================================


def test_docx_extractor_section_margins_integration(tmp_path):
    """Test that DocxExtractor correctly extracts margins from doc.sections[0]."""
    docx_file = tmp_path / "custom_margins.docx"
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = Mm(30.0)
    sec.right_margin = Mm(15.0)
    sec.top_margin = Mm(20.0)
    sec.bottom_margin = Mm(20.0)
    doc.save(str(docx_file))

    extractor = DocxExtractor()
    result = extractor.extract(str(docx_file))

    assert result.margin_left_mm == pytest.approx(30.0, rel=1e-2)
    assert result.margin_right_mm == pytest.approx(15.0, rel=1e-2)
    assert result.margin_top_mm == pytest.approx(20.0, rel=1e-2)
    assert result.margin_bottom_mm == pytest.approx(20.0, rel=1e-2)


def test_rule_engine_runs_all_typography_rules():
    """Verify that RuleEngine can run PAGE_MARGINS, MAIN_TEXT_FONT, and HEADINGS_FORMAT together."""
    config = {
        "PAGE_MARGINS": {"enabled": True},
        "MAIN_TEXT_FONT": {"enabled": True},
        "HEADINGS_FORMAT": {"enabled": True},
    }
    engine = RuleEngine(config)

    doc = DocumentDTO(
        margin_left_mm=20.0,  # Invalid margin
        margin_right_mm=15.0,
        margin_top_mm=20.0,
        margin_bottom_mm=20.0,
        paragraphs=[
            ParagraphDTO(
                text="1 Архитектура системы.",  # Invalid heading
                style_name="Heading 1",
                is_heading=True,
                indent_mm=0.0,
            ),
            ParagraphDTO(
                text="Текст абзаца со шрифтом 10 пт.",  # Invalid font
                style_name="Normal",
                is_heading=False,
                runs=[RunDTO(text="Текст абзаца со шрифтом 10 пт.", font_size_pt=10.0)],
            ),
        ],
    )
    violations = engine.run(doc)

    rule_ids = {v.rule_id for v in violations}
    assert "PAGE_MARGINS" in rule_ids
    assert "HEADINGS_FORMAT" in rule_ids
    assert "MAIN_TEXT_FONT" in rule_ids
