"""Structure rules package."""

from app.rule_engine.rules.structure.chapters import ChaptersCountRule
from app.rule_engine.rules.structure.required_sections import RequiredSectionsRule
from app.rule_engine.rules.structure.toc_matching import TocMatchingRule

__all__ = [
    "ChaptersCountRule",
    "RequiredSectionsRule",
    "TocMatchingRule",
]
