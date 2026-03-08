"""Semantic structure detection functions for figma-prepare.

Thin facade: re-exports all public API from focused submodules for backward
compatibility. All existing imports continue to work unchanged.

Submodules:
  detect_decoration     - Decoration pattern detection (dots, shapes)
  detect_horizontal_bar - Horizontal bar / news ticker detection
  detect_bg_content     - Background-content layer separation
  detect_table          - Table row structure detection
"""

# --- Decoration ---
from .detect_decoration import (  # noqa: F401
    is_decoration_pattern,
    decoration_dominant_shape,
)

# --- Horizontal bar ---
from .detect_horizontal_bar import (  # noqa: F401
    _cluster_by_y_band,
    _expand_y_band,
    _infer_bar_name,
    _is_valid_horizontal_bar,
    detect_horizontal_bar,
)

# --- Background-content layers ---
from .detect_bg_content import (  # noqa: F401
    _find_bg_rectangle,
    _classify_decorations,
    detect_bg_content_layers,
)

# --- Table rows ---
from .detect_table import (  # noqa: F401
    _find_table_row_backgrounds,
    _find_table_dividers,
    _assign_members_to_rows,
    _include_table_headings,
    _infer_table_name,
    detect_table_rows,
)
