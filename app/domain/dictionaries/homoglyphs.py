"""Homoglyph and mixed-script detection utilities."""

import re

CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")
LATIN_PATTERN = re.compile(r"[A-Za-z]")

# Homoglyph characters that visually look identical or very similar between scripts
HOMOGLYPH_CYRILLIC = set("асеорхуАВЕКМНОРСТХ")
HOMOGLYPH_LATIN = set("aceopxyABEKMHOPCTX")


def detect_mixed_scripts(word: str) -> bool:
    """
    Check whether a word contains an illegal mixture of Cyrillic and Latin characters
    used to bypass anti-plagiarism checks.

    Compound hyphenated terms (e.g., 'IP-адрес', 'HTTP-сервер', 'DNS-сервера', 'P2P-соединение')
    are split by hyphen: if each component is homogeneously Latin or Cyrillic, it is valid.
    Only if a single indivisible sub-word mixes both scripts is it flagged as a violation.

    Args:
        word: A token or compound word string.

    Returns:
        bool: True if an indivisible part of the word mixes Cyrillic and Latin, False otherwise.
    """
    if not word:
        return False

    # Split compound words by hyphens and dashes (e.g. IP-адрес, HTTP-сервер, Wi-Fi)
    subwords = re.split(r"[-–—_]", word)

    for part in subwords:
        part = part.strip()
        if not part:
            continue

        has_cyrillic = bool(CYRILLIC_PATTERN.search(part))
        has_latin = bool(LATIN_PATTERN.search(part))

        if has_cyrillic and has_latin:
            return True

    return False
