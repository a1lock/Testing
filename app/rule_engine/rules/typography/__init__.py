"""Typography rules package."""

from app.rule_engine.rules.typography.fonts import MainTextFontRule
from app.rule_engine.rules.typography.headings import HeadingsFormatRule
from app.rule_engine.rules.typography.indents import ParagraphIndentRule
from app.rule_engine.rules.typography.margins import MarginsRule

__all__ = [
    "HeadingsFormatRule",
    "MainTextFontRule",
    "MarginsRule",
    "ParagraphIndentRule",
]
