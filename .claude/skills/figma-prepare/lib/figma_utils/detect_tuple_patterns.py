"""Repeating tuple pattern detection for figma-prepare.

Detects repeating subsequences of mixed types (e.g., IMAGE + FRAME + INSTANCE x 3).

Issue 186: Separated card patterns.
"""

from .constants import (
    TUPLE_MAX_SIZE,
    TUPLE_PATTERN_MIN,
)

__all__ = [
    "detect_repeating_tuple",
]


def detect_repeating_tuple(children):
    """Detect repeating tuple patterns in flat sibling lists.

    Blog cards often consist of N separated sibling elements (e.g., IMAGE +
    FRAME + INSTANCE) repeated K times, producing N*K flat siblings. Standard
    structure_hash detection fails because each element within a tuple has a
    different type.

    This function detects such patterns by examining the sequence of element
    types and finding repeating subsequences of length 2..TUPLE_MAX_SIZE that
    repeat >= TUPLE_PATTERN_MIN times consecutively.

    Args:
        children: List of Figma node dicts with at least 'type', 'name', 'id'.

    Returns:
        list of detected tuple groups:
        [{'tuple_size': N, 'start_idx': S, 'count': C, 'children_indices': [...]}]
        - tuple_size: number of elements per tuple
        - start_idx: index of first element in the pattern
        - count: number of repetitions
        - children_indices: flat list of all element indices in the pattern

    Issue 186: Separated card patterns (IMAGE + FRAME + INSTANCE x 3).
    """
    children = [c for c in children if c.get('visible') != False]
    if len(children) < TUPLE_PATTERN_MIN * 2:
        # Need at least min_reps * 2 elements (smallest tuple_size is 2)
        return []

    types = [c.get('type', '') for c in children]
    n = len(types)
    results = []
    covered = set()  # Track indices already assigned to a tuple group

    # Try tuple sizes from largest to smallest (prefer larger tuples)
    for tuple_size in range(min(TUPLE_MAX_SIZE, n // TUPLE_PATTERN_MIN), 1, -1):
        # Slide a window across the type sequence
        start = 0
        while start + tuple_size * TUPLE_PATTERN_MIN <= n:
            if start in covered:
                start += 1
                continue

            reference = types[start:start + tuple_size]
            # Tuple must contain at least 2 distinct types (otherwise
            # detect_consecutive_similar handles homogeneous sequences)
            if len(set(reference)) < 2:
                start += 1
                continue
            reps = 1
            pos = start + tuple_size

            while pos + tuple_size <= n:
                candidate = types[pos:pos + tuple_size]
                if candidate == reference:
                    reps += 1
                    pos += tuple_size
                else:
                    break

            if reps >= TUPLE_PATTERN_MIN:
                indices = list(range(start, start + tuple_size * reps))
                # Check no overlap with already covered indices
                if not any(i in covered for i in indices):
                    results.append({
                        'tuple_size': tuple_size,
                        'start_idx': start,
                        'count': reps,
                        'children_indices': indices,
                    })
                    covered.update(indices)
                    start = start + tuple_size * reps
                    continue

            start += 1

    return results
