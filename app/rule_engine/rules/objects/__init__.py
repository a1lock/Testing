"""Objects rules package (figures, tables, listings, appendices)."""

from app.rule_engine.rules.objects.appendices import AppendicesRule
from app.rule_engine.rules.objects.figures import FiguresRule
from app.rule_engine.rules.objects.listings import ListingsRule
from app.rule_engine.rules.objects.tables import TablesRule

__all__ = [
    "AppendicesRule",
    "FiguresRule",
    "ListingsRule",
    "TablesRule",
]
