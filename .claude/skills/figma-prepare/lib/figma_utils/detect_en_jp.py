"""EN+JP label pair detection for figma-prepare.

Detects English uppercase labels paired with nearby Japanese text nodes.

Issue 185: EN+JP label pairs get generic names. Detect them for
semantic renaming (en-label-* / heading-*).
"""

import re

from .constants import (
    EN_JP_PAIR_MAX_DISTANCE,
    EN_LABEL_MAX_WORDS,
)
from .geometry import get_bbox


def _is_en_label(text):
    """Check if text is a short uppercase or title-case ASCII label.

    Args:
        text: Text string to check.

    Returns:
        bool: True if text is a short (1-3 word) uppercase or title-case
              ASCII label (e.g., "COMPANY", "Environment", "Human resources").

    Issue 185: EN+JP label pair detection.
    Benchmark fix: Accept title-case labels (first letter uppercase per word)
    in addition to all-uppercase labels. Common in Figma designs where
    section headings use "Environment" style rather than "ENVIRONMENT".
    """
    ascii_only = re.sub(r'[^\x00-\x7f]', '', text).strip()
    if not ascii_only or ascii_only != text.strip():
        return False
    words = ascii_only.split()
    if len(words) < 1 or len(words) > EN_LABEL_MAX_WORDS:
        return False
    # Must have alphabetic characters
    alpha_chars = re.sub(r'[^a-zA-Z]', '', ascii_only)
    if not alpha_chars:
        return False
    # Accept all-uppercase (e.g., "COMPANY", "OUR BUSINESS")
    if alpha_chars == alpha_chars.upper():
        return True
    # Accept title-case: first word must start with uppercase letter,
    # and all words must start with uppercase (e.g., "Environment", "Human Resources")
    # Also accept sentence-case where only first word is capitalized
    # (e.g., "Human resources", "Business organization")
    if words[0][0].isupper():
        # At least the first word starts uppercase — accept as EN label
        return True
    return False


def _is_jp_text(text):
    """Check if text contains non-ASCII (Japanese) characters.

    Args:
        text: Text string to check.

    Returns:
        bool: True if text contains non-ASCII characters.

    Issue 185: EN+JP label pair detection.
    """
    non_ascii = re.sub(r'[\x00-\x7f]', '', text).strip()
    return len(non_ascii) > 0


def _pair_distance(node_a, node_b):
    """Compute minimum distance between two nodes (Y-range or X-range proximity).

    Args:
        node_a: First Figma node dict with absoluteBoundingBox.
        node_b: Second Figma node dict with absoluteBoundingBox.

    Returns:
        float: Minimum edge-to-edge distance between the two nodes.

    Issue 185: EN+JP label pair detection.
    """
    bb_a = get_bbox(node_a)
    bb_b = get_bbox(node_b)
    # Y distance
    if bb_a['y'] + bb_a['h'] < bb_b['y']:
        dy = bb_b['y'] - (bb_a['y'] + bb_a['h'])
    elif bb_b['y'] + bb_b['h'] < bb_a['y']:
        dy = bb_a['y'] - (bb_b['y'] + bb_b['h'])
    else:
        dy = 0
    # X distance
    if bb_a['x'] + bb_a['w'] < bb_b['x']:
        dx = bb_b['x'] - (bb_a['x'] + bb_a['w'])
    elif bb_b['x'] + bb_b['w'] < bb_a['x']:
        dx = bb_a['x'] - (bb_b['x'] + bb_b['w'])
    else:
        dx = 0
    return min(dx, dy) if dx > 0 and dy > 0 else max(dx, dy)


def detect_en_jp_label_pairs(children):
    """Detect English + Japanese label pairs among sibling TEXT nodes.

    Pattern: An uppercase ASCII text (e.g., "COMPANY") paired with a
    Japanese text (e.g., "会社情報") at similar Y or X position.

    Args:
        children: List of sibling nodes.

    Returns:
        list of pairs: [{'en_idx': i, 'jp_idx': j, 'en_text': '...', 'jp_text': '...'}]

    Issue 185: EN+JP label pairs get generic names. Detect them for
    semantic renaming (en-label-* / heading-*).
    """
    children = [c for c in children if c.get('visible') != False]
    if len(children) < 2:
        return []

    # Collect TEXT nodes with their indices
    text_nodes = []
    for i, child in enumerate(children):
        if child.get('type') != 'TEXT':
            continue
        content = child.get('characters', '') or child.get('name', '')
        if not content or not content.strip():
            continue
        text_nodes.append((i, child, content.strip()))

    if len(text_nodes) < 2:
        return []

    # Find all EN labels and JP texts
    en_indices = [(i, node, text) for i, node, text in text_nodes if _is_en_label(text)]
    jp_indices = [(i, node, text) for i, node, text in text_nodes if _is_jp_text(text)]

    pairs = []
    used_en = set()
    used_jp = set()

    for en_i, en_node, en_text in en_indices:
        best_jp = None
        best_dist = float('inf')
        for jp_i, jp_node, jp_text in jp_indices:
            if jp_i in used_jp:
                continue
            dist = _pair_distance(en_node, jp_node)
            if dist <= EN_JP_PAIR_MAX_DISTANCE and dist < best_dist:
                best_dist = dist
                best_jp = (jp_i, jp_node, jp_text)
        if best_jp and en_i not in used_en:
            jp_i, jp_node, jp_text = best_jp
            pairs.append({
                'en_idx': en_i,
                'jp_idx': jp_i,
                'en_text': en_text,
                'jp_text': jp_text,
            })
            used_en.add(en_i)
            used_jp.add(jp_i)

    return pairs
