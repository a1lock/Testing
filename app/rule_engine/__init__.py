"""Rule Engine package following Strategy and Registry design patterns."""

from app.rule_engine.base import BaseRule
from app.rule_engine.engine import RuleEngine
from app.rule_engine.registry import RULE_REGISTRY, register_rule
import app.rule_engine.rules  # Ensures all rules are imported and registered

__all__ = [
    "BaseRule",
    "RuleEngine",
    "RULE_REGISTRY",
    "register_rule",
]
