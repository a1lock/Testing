"""Validation rules registry module.

Importing this package triggers the registration of all implemented rules in RULE_REGISTRY.
"""

from app.rule_engine.rules.typography.indents import ParagraphIndentRule

__all__ = [
    "ParagraphIndentRule",
]
