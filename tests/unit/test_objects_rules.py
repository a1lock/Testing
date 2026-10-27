"""Unit tests for objects validation rules (figures, tables, listings, appendices)."""

import pytest

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RULE_REGISTRY
from app.rule_engine.rules.objects.appendices import AppendicesRule
from app.rule_engine.rules.objects.figures import FiguresRule
from app.rule_engine.rules.objects.listings import ListingsRule
from app.rule_engine.rules.objects.tables import TablesRule


# ==========================================
# 1. Tests for FiguresRule (FIGURES_FORMAT)
# ==========================================


def test_figures_rule_registered():
    """Verify that FiguresRule is registered in RULE_REGISTRY with FIGURES_FORMAT."""
    assert "FIGURES_FORMAT" in RULE_REGISTRY
    assert RULE_REGISTRY["FIGURES_FORMAT"] is FiguresRule
    assert FiguresRule.rule_id == "FIGURES_FORMAT"


def test_figures_rule_valid():
    """Test valid figure caption: centered, no dot, with cross-reference in text."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Архитектура системы приведена на рисунке 1.", style_name="Normal"),
            ParagraphDTO(
                text="Рисунок 1 — Структурная схема сервиса",
                style_name="Normal",
                alignment="CENTER",
                indent_mm=0.0,
            ),
        ]
    )
    rule = FiguresRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_figures_rule_caption_above_image():
    """Test figure caption placed ABOVE image triggering error."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Схема приведена на рисунке 1.", style_name="Normal"),
            ParagraphDTO(
                text="Рисунок 1 — Структурная схема сервиса",
                style_name="Normal",
                alignment="CENTER",
            ),
            ParagraphDTO(
                text="",
                style_name="Normal",
                has_image=True,
            ),
        ]
    )
    rule = FiguresRule()
    violations = rule.check(doc, {})
    assert len(violations) == 1
    assert "расположена над иллюстрацией" in violations[0].message


def test_figures_rule_missing_reference():
    """Test figure caption without any cross-reference in the body text."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Текст без каких-либо ссылок на иллюстрации.", style_name="Normal"),
            ParagraphDTO(
                text="Рисунок 1 — Структурная схема сервиса",
                style_name="Normal",
                alignment="CENTER",
            ),
        ]
    )
    rule = FiguresRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "FIGURES_FORMAT"
    assert v.severity == "ERROR"
    assert "Отсутствует ссылка на рисунок 1 в тексте" in v.message


def test_figures_rule_invalid_alignment_and_dot():
    """Test figure caption with left alignment and trailing dot."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Схема приведена на рис. 2.1.", style_name="Normal"),
            ParagraphDTO(
                text="Рисунок 2.1 — Диаграмма компонентов.",
                style_name="Normal",
                alignment="LEFT",  # Must be CENTER
            ),
        ]
    )
    rule = FiguresRule()
    violations = rule.check(doc, {})

    assert len(violations) == 2
    # Check alignment error
    v_align = next(v for v in violations if "по центру" in v.message)
    assert v_align.severity == "ERROR"

    # Check trailing dot warning
    v_dot = next(v for v in violations if "точка не ставится" in v.message)
    assert v_dot.severity == "WARNING"


# ==========================================
# 2. Tests for TablesRule (TABLES_FORMAT)
# ==========================================


def test_tables_rule_registered():
    """Verify that TablesRule is registered in RULE_REGISTRY with TABLES_FORMAT."""
    assert "TABLES_FORMAT" in RULE_REGISTRY
    assert RULE_REGISTRY["TABLES_FORMAT"] is TablesRule
    assert TablesRule.rule_id == "TABLES_FORMAT"


def test_tables_rule_valid():
    """Test valid table caption: left aligned, no indent, no dot, with cross-reference."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Результаты сравнения приведены в таблице 1.", style_name="Normal"),
            ParagraphDTO(
                text="Таблица 1 — Сравнительная характеристика алгоритмов",
                style_name="Normal",
                alignment="LEFT",
                indent_mm=0.0,
            ),
        ]
    )
    rule = TablesRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_tables_rule_missing_reference():
    """Test table caption without any cross-reference in the body text."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Текст без ссылки на таблицу.", style_name="Normal"),
            ParagraphDTO(
                text="Таблица 1 — Результаты экспериментов",
                style_name="Normal",
                alignment="LEFT",
                indent_mm=0.0,
            ),
        ]
    )
    rule = TablesRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "TABLES_FORMAT"
    assert v.severity == "ERROR"
    assert "Отсутствует ссылка на таблицу 1 в тексте" in v.message


def test_tables_rule_invalid_alignment_indent_and_dot():
    """Test table caption centered, with indent, and ending with a dot."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="Данные сведены в табл. 3.", style_name="Normal"),
            ParagraphDTO(
                text="Таблица 3 — Метрики производительности.",
                style_name="Normal",
                alignment="CENTER",  # Must be LEFT
                indent_mm=12.5,     # Must be < 1.0
            ),
        ]
    )
    rule = TablesRule()
    violations = rule.check(doc, {})

    assert len(violations) == 2
    # Check alignment / indent error
    v_format = next(v for v in violations if "левому краю" in v.message)
    assert v_format.severity == "ERROR"

    # Check trailing dot warning
    v_dot = next(v for v in violations if "точка не ставится" in v.message)
    assert v_dot.severity == "WARNING"


# ==========================================
# 3. Tests for ListingsRule (LISTINGS_FORMAT)
# ==========================================


def test_listings_rule_registered():
    """Verify that ListingsRule is registered in RULE_REGISTRY with LISTINGS_FORMAT."""
    assert "LISTINGS_FORMAT" in RULE_REGISTRY
    assert RULE_REGISTRY["LISTINGS_FORMAT"] is ListingsRule
    assert ListingsRule.rule_id == "LISTINGS_FORMAT"


def test_listings_rule_valid():
    """Test valid listing: left-aligned, no indent, followed by editable text."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Листинг 1.1 — Функция валидации заголовков",
                style_name="Normal",
                alignment="LEFT",
                indent_mm=0.0,
            ),
            ParagraphDTO(text="def validate_headings(doc): pass", style_name="Normal"),
        ]
    )
    rule = ListingsRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_listings_rule_image_empty_next_paragraph():
    """Test listing followed by an empty paragraph (code pasted as image)."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(
                text="Листинг 2 — Обработчик задач Celery",
                style_name="Normal",
                alignment="LEFT",
                indent_mm=0.0,
            ),
            ParagraphDTO(text="   \n  \t", style_name="Normal"),  # Empty paragraph representing an image
        ]
    )
    rule = ListingsRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "LISTINGS_FORMAT"
    assert v.severity == "ERROR"
    assert "Листинг кода должен быть вставлен редактируемым текстом, а не рисунком" in v.message


# ==========================================
# 4. Tests for AppendicesRule (APPENDICES_FORMAT)
# ==========================================


def test_appendices_rule_registered():
    """Verify that AppendicesRule is registered in RULE_REGISTRY with APPENDICES_FORMAT."""
    assert "APPENDICES_FORMAT" in RULE_REGISTRY
    assert RULE_REGISTRY["APPENDICES_FORMAT"] is AppendicesRule
    assert AppendicesRule.rule_id == "APPENDICES_FORMAT"


def test_appendices_rule_valid_same_line():
    """Test appendix with title on the same line."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="ПРИЛОЖЕНИЕ А — Исходный программный код", style_name="Heading 1"),
        ]
    )
    rule = AppendicesRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_appendices_rule_valid_next_line():
    """Test appendix with title on the immediate next line."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="ПРИЛОЖЕНИЕ Б", style_name="Heading 1"),
            ParagraphDTO(text="Результаты нагрузочного тестирования", style_name="Normal"),
        ]
    )
    rule = AppendicesRule()
    violations = rule.check(doc, {})
    assert len(violations) == 0


def test_appendices_rule_missing_title():
    """Test appendix without any meaningful title (standalone header at EOF or before another appendix)."""
    doc = DocumentDTO(
        paragraphs=[
            ParagraphDTO(text="ПРИЛОЖЕНИЕ В", style_name="Heading 1"),
            # No title paragraph follows
        ]
    )
    rule = AppendicesRule()
    violations = rule.check(doc, {})

    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "APPENDICES_FORMAT"
    assert v.severity == "ERROR"
    assert "Приложение должно иметь содержательное название" in v.message


# ==========================================
# 5. Integration Test with RuleEngine
# ==========================================


def test_rule_engine_runs_objects_rules():
    """Verify that RuleEngine runs all objects rules together."""
    config = {
        "FIGURES_FORMAT": {"enabled": True},
        "TABLES_FORMAT": {"enabled": True},
        "LISTINGS_FORMAT": {"enabled": True},
        "APPENDICES_FORMAT": {"enabled": True},
    }
    engine = RuleEngine(config)

    doc = DocumentDTO(
        paragraphs=[
            # Figure without reference
            ParagraphDTO(text="Рисунок 1 — Архитектура", style_name="Normal", alignment="CENTER"),
            # Table without reference
            ParagraphDTO(text="Таблица 1 — Параметры", style_name="Normal", alignment="LEFT", indent_mm=0.0),
            # Listing with empty code (image)
            ParagraphDTO(text="Листинг 1 — Скрипт", style_name="Normal", alignment="LEFT", indent_mm=0.0),
            ParagraphDTO(text="", style_name="Normal"),
            # Appendix without title
            ParagraphDTO(text="ПРИЛОЖЕНИЕ А", style_name="Heading 1"),
        ]
    )
    violations = engine.run(doc)

    rule_ids = {v.rule_id for v in violations}
    assert "FIGURES_FORMAT" in rule_ids
    assert "TABLES_FORMAT" in rule_ids
    assert "LISTINGS_FORMAT" in rule_ids
    assert "APPENDICES_FORMAT" in rule_ids
