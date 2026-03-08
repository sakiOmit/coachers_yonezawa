"""Shared utilities for figma-prepare scripts.

Package facade: re-exports all public API from submodules for backward compatibility.
All existing imports (`from figma_utils import X`) continue to work unchanged.

Submodules:
  constants   - Thresholds, regex patterns, lookup tables
  geometry    - Coordinate/bbox utilities (get_bbox, snap, resolve_absolute_coords)
  metadata    - I/O, parsing, node lookup, structural predicates
  naming      - Text conversion (to_kebab, _jp_keyword_lookup)
  scoring     - Proximity scoring, structure hashing, layout inference
  detection   - Semantic/pattern detection (13 detectors)
  enrichment  - Enriched table generation
  comparison  - Deduplication, Stage A/C comparison, validation
  stage_c     - Stage C depth recursion (YAML I/O, heuristic sub-grouping)
"""

from .constants import *  # noqa: F401,F403
from .constants import _STAGE_A_TO_C_PATTERN_MAP  # noqa: F401
from .geometry import *  # noqa: F401,F403
from .metadata import *  # noqa: F401,F403
from .metadata import _count_flat_descendants  # noqa: F401
from .naming import *  # noqa: F401,F403
from .naming import _jp_keyword_lookup  # noqa: F401
from .scoring import *  # noqa: F401,F403
from .scoring import _raw_distance  # noqa: F401
from .detection import *  # noqa: F401,F403
from .detection import _compute_zone_bboxes  # noqa: F401
from .enrichment import *  # noqa: F401,F403
from .enrichment import _collect_text_preview, _compute_child_types, _compute_flags  # noqa: F401
from .comparison import *  # noqa: F401,F403
from .comparison import _stage_a_pattern_key  # noqa: F401
from .stage_c import *  # noqa: F401,F403
from .stage_c import _write_group_yaml, _try_heading_split, _try_column_split  # noqa: F401
from .stage_c import _try_spatial_split, _try_yband_split, _collect_from_groups  # noqa: F401
