"""Rule registry for discovering and registering rule strategies."""

from collections.abc import Callable
from typing import TypeVar

from app.rule_engine.base import BaseRule

RULE_REGISTRY: dict[str, type[BaseRule]] = {}

R = TypeVar("R", bound=type[BaseRule])


def register_rule(rule_id: str) -> Callable[[R], R]:
    """Decorator to register a rule class in the global RULE_REGISTRY.

    Args:
        rule_id: Unique string identifier for the rule (e.g., 'PARAGRAPH_INDENT').

    Returns:
        Decorator function that sets cls.rule_id and stores cls in RULE_REGISTRY.
    """

    def decorator(cls: R) -> R:
        cls.rule_id = rule_id
        RULE_REGISTRY[rule_id] = cls
        return cls

    return decorator
