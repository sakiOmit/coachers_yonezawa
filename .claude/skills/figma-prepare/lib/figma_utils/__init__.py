"""Shared utilities for figma-prepare scripts.

Package facade: re-exports all public API from submodules for backward compatibility.
All existing imports (`from figma_utils import X`) continue to work unchanged.

Submodule hierarchy (39 modules):

  Foundation:
    constants           - Thresholds, regex patterns, lookup tables (106+ constants)
    geometry            - Coordinate/bbox utilities (get_bbox, snap, resolve_absolute_coords)
    metadata            - I/O, parsing, node lookup, structural predicates
    naming              - Text conversion (to_kebab, _jp_keyword_lookup)
    scoring             - Proximity scoring, structure hashing, layout inference

  Detection (facade chain: __init__ → detection → detection_patterns/detection_semantic → leaf modules):
    detection           - Core detection (heading, absorption) + re-exports
    detection_patterns  - Facade → detect_tuple_patterns, detect_consecutive, detect_highlight, detect_en_jp
    detection_semantic  - Facade → detect_decoration, detect_horizontal_bar, detect_bg_content, detect_table
    detect_tuple_patterns - Repeating tuple pattern detection
    detect_consecutive    - Consecutive similar element detection
    detect_highlight      - Highlight text (RECT+TEXT overlap) detection
    detect_en_jp          - EN+JP label pair detection
    detect_decoration     - Decoration dot/pattern detection
    detect_horizontal_bar - Horizontal bar/news ticker detection
    detect_bg_content     - Background-content layer separation
    detect_table          - Table row structure detection

  Grouping (facade: __init__ → grouping_engine → leaf modules):
    grouping_engine     - Entry point + pattern/spacing detectors
    grouping_proximity  - UnionFind, proximity groups, spatial gap splitting
    grouping_semantic   - Card/navigation/grid semantic detectors
    grouping_zones      - Header/footer/vertical zone detection
    grouping_walker     - Tree walking (_is_protected_node, walk_and_detect)

  Comparison (facade: __init__ → comparison → leaf modules):
    comparison          - Stage A/C comparison entry points
    comparison_dedup    - Deduplication, divider absorption
    comparison_column   - Two-column layout validation
    comparison_matching - Jaccard matching, coverage metrics

  Stage C (facade: __init__ → stage_c → leaf modules):
    stage_c             - Recursion target collection
    stage_c_yaml        - YAML I/O (parse/write plan, enriched table)
    stage_c_strategies  - Heuristic sub-grouping (heading/column/spatial/yband split)

  Rename (facade: __init__ → semantic_rename → rename_strategies, rename_llm_fallback):
    semantic_rename     - Name inference dispatcher, rename collection, entry point
    rename_strategies   - Priority-based naming strategies (text/shape/position/children)
    rename_llm_fallback - LLM fallback for low-confidence renames (context, prompt, merge)

  Cross-Section:
    pattern_registry    - Cross-section pattern registry (frequency tracking, lookup, formatting)

  Enrichment & Analysis:
    enrichment          - Enriched table generation
    nested_context      - Nested grouping context (plan/groups modes)
    grouping_compare    - Stage A vs Stage C comparison (YAML parsing, report)
    metadata_enricher   - Metadata enrichment (merge design context into tree)
    grouping_postprocess - Grouping plan post-processing (divider absorption)
    autolayout          - Auto Layout inference (Phase 4)
    sectioning          - Sectioning context preparation (Phase 2 Stage B)
    structure_analysis  - Structure quality analysis (Phase 1)
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
from .enrichment import _collect_text_preview, _compute_child_types, _compute_flags, _compute_method_tag  # noqa: F401
from .comparison import *  # noqa: F401,F403
from .comparison import _stage_a_pattern_key  # noqa: F401
from .comparison import _merge_stage_c_with_a_remainder, _merge_stage_a_with_c_confident  # noqa: F401
from .comparison import _should_absorb_into_higher  # noqa: F401
from .stage_c import *  # noqa: F401,F403
from .stage_c import _write_group_yaml, _try_heading_split, _try_column_split  # noqa: F401
from .stage_c import _try_spatial_split, _try_yband_split, _collect_from_groups  # noqa: F401
from .nested_context import *  # noqa: F401,F403
from .grouping_engine import (  # noqa: F401
    UnionFind, compute_adaptive_gap, detect_grouping_candidates, detect_proximity_groups,
    detect_pattern_groups, detect_spacing_groups, detect_semantic_groups,
    detect_header_footer_groups, detect_vertical_zone_groups,
    infer_zone_semantic_name, walk_and_detect,
    is_card_like, is_navigation_like, is_grid_like, detect_variant_groups,
    _is_protected_node, _split_by_spatial_gap,
)
from .semantic_rename import (  # noqa: F401
    generate_rename_map, collect_renames, infer_name, infer_name_with_confidence,
    infer_text_role, has_image_wrapper, SHAPE_PREFIXES, CTA_KEYWORDS,
    _estimate_children_confidence,
)
from .rename_llm_fallback import (  # noqa: F401
    collect_low_confidence_renames, build_fallback_context,
    format_fallback_prompt, parse_llm_suggestions, merge_llm_suggestions,
    generate_fallback_context_file, LLM_FALLBACK_CONFIDENCE_THRESHOLD,
    LLM_CONFIDENCE_MAP, LLM_DEFAULT_CONFIDENCE,
)
from .grouping_compare import (  # noqa: F401
    parse_stage_a_yaml, parse_stage_c_yaml, run_comparison, format_report,
)
from .metadata_enricher import (  # noqa: F401
    enrich_node, enrich_metadata, enrich_metadata_from_files, ENRICHMENT_KEYS,
)
from .grouping_postprocess import (  # noqa: F401
    parse_plan_yaml as parse_plan_yaml_lines,  # line-based parser (postprocess-grouping-plan.sh)
    format_plan_yaml, postprocess_plan,
)
# Note: parse_plan_yaml (file-based) comes from stage_c_yaml via stage_c wildcard import (line 82)
# parse_plan_yaml_lines (line-based) is the grouping_postprocess version for shell scripts
from .autolayout import (  # noqa: F401
    infer_layout, layout_from_enrichment, walk_and_infer, run_autolayout_inference,
    _infer_direction, _infer_direction_by_grid, _direction_hint_from_name,
)
from .sectioning import (  # noqa: F401
    detect_heuristic_hints, run_sectioning_context,
    classify_section_type, _compute_gap_analysis,
)
from .nested_context import _format_stage_b_context  # noqa: F401
from .structure_analysis import (  # noqa: F401
    count_nodes, detect_grouping_candidates_simple, run_structure_analysis,
)
from .pattern_registry import (  # noqa: F401
    build_pattern_registry, lookup_pattern, format_registry_summary,
)
