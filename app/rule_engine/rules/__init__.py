"""Validation rules registry module.

Importing this package triggers the registration of all implemented rules in RULE_REGISTRY.
"""

from app.rule_engine.rules.bibliography.cross_references import CrossReferencesRule
from app.rule_engine.rules.bibliography.sources_count import SourcesCountRule
from app.rule_engine.rules.objects.appendices import AppendicesRule
from app.rule_engine.rules.objects.figures import FiguresRule
from app.rule_engine.rules.objects.listings import ListingsRule
from app.rule_engine.rules.objects.tables import TablesRule
from app.rule_engine.rules.structure.chapters import ChaptersCountRule
from app.rule_engine.rules.structure.required_sections import RequiredSectionsRule
from app.rule_engine.rules.structure.toc_matching import TocMatchingRule
from app.rule_engine.rules.text_quality.anglicisms import AnglicismsRule
from app.rule_engine.rules.text_quality.homoglyphs import HomoglyphsRule
from app.rule_engine.rules.text_quality.lists import ListsFormatRule
from app.rule_engine.rules.typography.fonts import MainTextFontRule
from app.rule_engine.rules.typography.headings import HeadingsFormatRule
from app.rule_engine.rules.typography.indents import ParagraphIndentRule
from app.rule_engine.rules.typography.margins import MarginsRule

__all__ = [
    "AnglicismsRule",
    "AppendicesRule",
    "ChaptersCountRule",
    "CrossReferencesRule",
    "FiguresRule",
    "HeadingsFormatRule",
    "HomoglyphsRule",
    "ListingsRule",
    "ListsFormatRule",
    "MainTextFontRule",
    "MarginsRule",
    "ParagraphIndentRule",
    "RequiredSectionsRule",
    "SourcesCountRule",
    "TablesRule",
    "TocMatchingRule",
]
