"""Bibliography rules package (sources count, composition, cross-references)."""

from app.rule_engine.rules.bibliography.cross_references import CrossReferencesRule
from app.rule_engine.rules.bibliography.sources_count import SourcesCountRule

__all__ = [
    "CrossReferencesRule",
    "SourcesCountRule",
]
