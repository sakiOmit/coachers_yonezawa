"""Naming and text conversion utilities for figma-prepare."""

import re

# JP_KEYWORD_MAP is defined in __init__.py; import it from the package.
# Use a lazy import inside _jp_keyword_lookup to avoid circular imports
# since __init__.py may import from this module.

__all__ = [
    "to_kebab",
]


def to_kebab(text):
    """Convert text to kebab-case safe name.

    Non-ASCII-only text is matched against JP_KEYWORD_MAP for known
    Japanese terms. If no keyword matches, returns 'content' as a
    generic label. The downstream AI (via get_design_context) will
    assign final semantic names using the node's characters field.

    Issue 45: Extracted from generate-rename-map.sh to avoid duplication.
    Issue 47: Added CamelCase splitting (e.g. CamelCase → camel-case).
    Issue 170: Added JP_KEYWORD_MAP for Japanese keyword → English slug.
    """
    text = text.strip()
    if not text:
        return ''
    # Extract ASCII portion
    ascii_part = re.sub(r'[^\x00-\x7f]', '', text).strip()
    if not ascii_part:
        # Issue 170: Try JP_KEYWORD_MAP before falling back to 'content'
        slug = _jp_keyword_lookup(text)
        return slug if slug else 'content'
    # Split CamelCase before lowercasing (Issue 47)
    ascii_part = re.sub(r'([a-z])([A-Z])', r'\1 \2', ascii_part)
    ascii_part = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', ascii_part)
    # ASCII logic
    ascii_part = re.sub(r'[^\w\s-]', '', ascii_part.lower())
    ascii_part = re.sub(r'[\s_]+', '-', ascii_part)
    ascii_part = re.sub(r'-+', '-', ascii_part).strip('-')
    return ascii_part[:40] if ascii_part else 'content'


def _jp_keyword_lookup(text):
    """Look up Japanese text in JP_KEYWORD_MAP.

    Searches for known keywords in the text. Returns the first match
    found (longest match preferred to avoid partial hits).
    Returns empty string if no match.

    Issue 170: Extracted to share between to_kebab and generate-rename-map.
    """
    from . import JP_KEYWORD_MAP

    if not text:
        return ''
    # Sort by descending length so longer keywords match first
    # (e.g., "フィンガーフード" before "フード")
    for jp, en in sorted(JP_KEYWORD_MAP.items(), key=lambda kv: -len(kv[0])):
        if jp in text:
            return en
    return ''
