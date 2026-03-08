"""Pattern-based detection functions for figma-prepare.

Thin facade that re-exports from focused sub-modules:
- detect_tuple_patterns: Repeating tuple pattern detection
- detect_consecutive: Consecutive similar element detection
- detect_highlight: Highlight text (RECTANGLE+TEXT) detection
- detect_en_jp: EN+JP label pair detection
"""

from .detect_tuple_patterns import (  # noqa: F401
    detect_repeating_tuple,
)
from .detect_consecutive import (  # noqa: F401
    detect_consecutive_similar,
)
from .detect_highlight import (  # noqa: F401
    _check_rect_text_overlap,
    _find_rect_text_overlaps,
    detect_highlight_text,
)
from .detect_en_jp import (  # noqa: F401
    _is_en_label,
    _is_jp_text,
    _pair_distance,
    detect_en_jp_label_pairs,
)
