"""Shared utility functions for rule engine validations."""

import difflib
import re


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive whitespace characters and trim edges."""
    return re.sub(r"\s+", " ", text).strip()


def matches_heading_fuzzy(norm_a: str, norm_b: str) -> bool:
    """Fuzzy matching between two heading titles (e.g. comparing TOC entries with body headings)."""
    if norm_a == norm_b:
        return True
    if norm_a.lower() == norm_b.lower():
        return True

    text_a = re.sub(r"^[\d\s\.]+", "", norm_a).strip().lower()
    text_b = re.sub(r"^[\d\s\.]+", "", norm_b).strip().lower()

    if text_a and text_b:
        if text_a == text_b or text_a in text_b or text_b in text_a:
            return True

    if len(norm_a) > 6 and len(norm_b) > 6:
        if difflib.SequenceMatcher(None, norm_a.lower(), norm_b.lower()).ratio() >= 0.82:
            return True

    return False
