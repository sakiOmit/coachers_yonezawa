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

  Detection (facade chain: __init__ -> detection -> detection_patterns/detection_semantic -> leaf modules):
    detection           - Core detection (heading, absorption) + re-exports
    detection_patterns  - Facade -> detect_tuple_patterns, detect_consecutive, detect_highlight, detect_en_jp
    detection_semantic  - Facade -> detect_decoration, detect_horizontal_bar, detect_bg_content, detect_table
    detect_tuple_patterns - Repeating tuple pattern detection
    detect_consecutive    - Consecutive similar element detection
    detect_highlight      - Highlight text (RECT+TEXT overlap) detection
    detect_en_jp          - EN+JP label pair detection
    detect_decoration     - Decoration dot/pattern detection
    detect_horizontal_bar - Horizontal bar/news ticker detection
    detect_bg_content     - Background-content layer separation
    detect_table          - Table row structure detection

  Grouping (facade: __init__ -> grouping_engine -> leaf modules):
    grouping_engine     - Entry point + pattern/spacing detectors
    grouping_proximity  - UnionFind, proximity groups, spatial gap splitting
    grouping_semantic   - Card/navigation/grid semantic detectors
    grouping_zones      - Header/footer/vertical zone detection
    grouping_walker     - Tree walking (_is_protected_node, walk_and_detect)

  Comparison (facade: __init__ -> comparison -> leaf modules):
    comparison          - Stage A/C comparison entry points
    comparison_dedup    - Deduplication, divider absorption
    comparison_column   - Two-column layout validation
    comparison_matching - Jaccard matching, coverage metrics

  Stage C (facade: __init__ -> stage_c -> leaf modules):
    stage_c             - Recursion target collection
    stage_c_yaml        - YAML I/O (parse/write plan, enriched table)
    stage_c_strategies  - Heuristic sub-grouping (heading/column/spatial/yband split)

  Rename (facade: __init__ -> semantic_rename -> rename_strategies, rename_llm_fallback):
    semantic_rename     - Name inference dispatcher, rename collection, entry point
    rename_strategies   - Priority-based naming strategies (text/shape/position/children)
    rename_llm_fallback - LLM fallback for low-confidence renames (context, prompt, merge)

  Grouping LLM Fallback:
    grouping_llm_fallback - LLM fallback for undergrouped sections (1:N heading-content, Issue #274)

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

from .constants import *  # noqa: F403
from .constants import _STAGE_A_TO_C_PATTERN_MAP
from .geometry import *  # noqa: F403
from .metadata import *  # noqa: F403
from .metadata import _count_flat_descendants
from .naming import *  # noqa: F403
from .naming import _jp_keyword_lookup
from .scoring import *  # noqa: F403
from .scoring import _raw_distance
from .detection import *  # noqa: F403
from .detection import _compute_zone_bboxes
from .enrichment import *  # noqa: F403
from .enrichment import _collect_text_preview, _compute_child_types, _compute_flags, _compute_method_tag
from .comparison import *  # noqa: F403
from .comparison import _stage_a_pattern_key
from .comparison import _merge_stage_c_with_a_remainder, _merge_stage_a_with_c_confident
from .comparison import _should_absorb_into_higher
from .stage_c import *  # noqa: F403
from .stage_c import _write_group_yaml, _try_heading_split, _try_column_split
from .stage_c import _try_spatial_split, _try_yband_split, _collect_from_groups
from .nested_context import *  # noqa: F403
from .grouping_engine import (
    UnionFind, compute_adaptive_gap, detect_grouping_candidates, detect_proximity_groups,
    detect_pattern_groups, detect_spacing_groups, detect_semantic_groups,
    detect_header_footer_groups, detect_vertical_zone_groups,
    infer_zone_semantic_name, walk_and_detect,
    is_card_like, is_navigation_like, is_grid_like, detect_variant_groups,
    _is_protected_node, _split_by_spatial_gap,
)
from .semantic_rename import (
    generate_rename_map, collect_renames, infer_name, infer_name_with_confidence,
    infer_text_role, has_image_wrapper, SHAPE_PREFIXES, CTA_KEYWORDS,
    _estimate_children_confidence, RENAME_STRATEGIES,
)
from .rename_llm_fallback import (
    collect_low_confidence_renames, build_fallback_context,
    format_fallback_prompt, parse_llm_suggestions, merge_llm_suggestions,
    generate_fallback_context_file, LLM_FALLBACK_CONFIDENCE_THRESHOLD,
    LLM_CONFIDENCE_MAP, LLM_DEFAULT_CONFIDENCE,
)
from .grouping_compare import (
    parse_stage_a_yaml, parse_stage_c_yaml, run_comparison, format_report,
)
from .metadata_enricher import (
    enrich_node, enrich_metadata, enrich_metadata_from_files, ENRICHMENT_KEYS,
)
from .grouping_postprocess import (
    parse_plan_yaml as parse_plan_yaml_lines,  # line-based parser (postprocess-grouping-plan.sh)
    format_plan_yaml, postprocess_plan,
)
# Note: parse_plan_yaml (file-based) comes from stage_c_yaml via stage_c wildcard import
# parse_plan_yaml_lines (line-based) is the grouping_postprocess version for shell scripts
from .autolayout import (
    infer_layout, layout_from_enrichment, walk_and_infer, run_autolayout_inference,
    _infer_direction, _infer_direction_by_grid, _direction_hint_from_name,
)
from .sectioning import (
    detect_heuristic_hints, run_sectioning_context,
    classify_section_type, _compute_gap_analysis,
)
from .nested_context import _format_stage_b_context
from .structure_analysis import (
    count_nodes, detect_grouping_candidates_simple, run_structure_analysis,
)
from .grouping_llm_fallback import (
    collect_undergrouped_sections, build_grouping_fallback_context,
    format_grouping_fallback_prompt, parse_llm_grouping_suggestions,
    merge_grouping_suggestions, generate_grouping_fallback_context_file,
    GROUPING_FALLBACK_HEADING_MAX_HEIGHT,
    GROUPING_FALLBACK_MIN_SIBLINGS_AFTER_HEADING,
    GROUPING_FALLBACK_STRUCTURE_SIMILARITY,
    GROUPING_LLM_CONFIDENCE_MAP, GROUPING_LLM_DEFAULT_CONFIDENCE,
)
from .pattern_registry import (
    build_pattern_registry, lookup_pattern, format_registry_summary,
)

# ---------------------------------------------------------------------------
# Explicit public API surface.
#
# This ``__all__`` replaces the former F401/F403 noqa suppression pattern and
# makes the package's public API explicit for IDEs, documentation tools, and
# ``from figma_utils import *`` consumers.
#
# Every symbol that was importable before is still listed here to maintain
# backward compatibility.  Private helpers (``_``-prefixed) that are
# intentionally re-exported for tests are included as well.
# ---------------------------------------------------------------------------

__all__ = [
    # -- Constants (from .constants) ----------------------------------------
    "ALIGN_TOLERANCE",
    "BASE_VIEWPORT_HEIGHT",
    "BASE_VIEWPORT_WIDTH",
    "BG_DECORATION_MAX_AREA_RATIO",
    "BG_LEFT_OVERFLOW_WIDTH_RATIO",
    "BG_MIN_HEIGHT_RATIO",
    "BG_WIDTH_RATIO",
    "BULLET_MAX_SIZE",
    "BUTTON_MAX_HEIGHT",
    "BUTTON_MAX_WIDTH",
    "BUTTON_TEXT_MAX_LEN",
    "CENTER_ALIGN_VARIANCE",
    "COMPARE_MATCH_THRESHOLD",
    "CONFIDENCE_HIGH_COV",
    "CONFIDENCE_MEDIUM_COV",
    "CONSECUTIVE_PATTERN_MIN",
    "CTA_SQUARE_RATIO_MAX",
    "CTA_SQUARE_RATIO_MIN",
    "CTA_X_POSITION_RATIO",
    "CTA_Y_THRESHOLD",
    "CV_THRESHOLD",
    "DECORATION_MAX_SIZE",
    "DECORATION_MIN_SHAPES",
    "DECORATION_SHAPE_RATIO",
    "DEEP_NESTING_THRESHOLD",
    "DIVIDER_MAX_HEIGHT",
    "EN_JP_PAIR_MAX_DISTANCE",
    "EN_LABEL_MAX_WORDS",
    "FLAG_BG_FULL_WIDTH_RATIO",
    "FLAG_OVERFLOW_X_RATIO",
    "FLAG_OVERFLOW_Y_RATIO",
    "FLAG_TINY_MAX_SIZE",
    "FLAT_THRESHOLD",
    "FOOTER_MAX_HEIGHT",
    "FOOTER_PROXIMITY",
    "FOOTER_TEXT_RATIO",
    "FOOTER_ZONE_HEIGHT",
    "FOOTER_ZONE_MARGIN",
    "GRANDCHILD_THRESHOLD",
    "GRID_SIZE_SIMILARITY",
    "GRID_SNAP",
    "HEADER_LOGO_MAX_HEIGHT",
    "HEADER_LOGO_MAX_WIDTH",
    "HEADER_MAX_ELEMENT_HEIGHT",
    "HEADER_NAV_MIN_TEXTS",
    "HEADER_TEXT_MAX_WIDTH",
    "HEADER_Y_THRESHOLD",
    "HEADER_ZONE_HEIGHT",
    "HEADER_ZONE_MARGIN",
    "HEADING_BODY_TEXT_THRESHOLD",
    "HEADING_MAX_CHILDREN",
    "HEADING_MAX_HEIGHT_RATIO",
    "HEADING_SOFT_HEIGHT_RATIO",
    "HEADING_TEXT_RATIO",
    "HERO_ZONE_DISTANCE",
    "HIGHLIGHT_HEIGHT_RATIO_MAX",
    "HIGHLIGHT_HEIGHT_RATIO_MIN",
    "HIGHLIGHT_OVERLAP_RATIO",
    "HIGHLIGHT_TEXT_MAX_LEN",
    "HIGHLIGHT_X_OVERLAP_RATIO",
    "HINT_BG_MIN_HEIGHT",
    "HINT_FOOTER_Y_RATIO",
    "HINT_HEADER_Y_RATIO",
    "HINT_HEADING_MAX_HEIGHT",
    "HINT_WIDE_ELEMENT_RATIO",
    "HORIZONTAL_BAR_MAX_HEIGHT",
    "HORIZONTAL_BAR_MIN_ELEMENTS",
    "HORIZONTAL_BAR_VARIANCE_RATIO",
    "ICON_MAX_SIZE",
    "IMAGE_WRAPPER_RATIO",
    "JACCARD_THRESHOLD",
    "JP_KEYWORD_MAP",
    "LABEL_MAX_LEN",
    "LARGE_BG_WIDTH_RATIO",
    "LOOSE_ABSORPTION_DISTANCE",
    "LOOSE_ELEMENT_MAX_HEIGHT",
    "MAX_STAGE_C_DEPTH",
    "METHOD_PRIORITY",
    "NAV_GRANDCHILD_MIN",
    "NAV_MAX_TEXT_LEN",
    "NAV_MIN_TEXT_COUNT",
    "OFF_CANVAS_MARGIN",
    "OVERFLOW_BG_MIN_WIDTH",
    "PROXIMITY_GAP",
    "REPEATED_PATTERN_MIN",
    "ROW_TOLERANCE",
    "SECTION_BG_WIDTH_RATIO",
    "SECTION_ROOT_WIDTH",
    "SECTION_ROOT_WIDTH_RATIO",
    "SIDE_PANEL_HEIGHT_RATIO",
    "SIDE_PANEL_LEFT_X_RATIO",
    "SIDE_PANEL_MAX_WIDTH",
    "SIDE_PANEL_RIGHT_X_RATIO",
    "SPATIAL_GAP_THRESHOLD",
    "SPATIAL_SPLIT_MIN_NON_LEAF",
    "STAGE_A_ONLY_DETECTORS",
    "STAGE_C_COVERABLE_DETECTORS",
    "STAGE_C_COVERAGE_THRESHOLD",
    "STAGE_MERGE_TIER1",
    "STAGE_MERGE_TIER2",
    "STAGE_MERGE_TIER3",
    "TABLE_DIVIDER_MAX_HEIGHT",
    "TABLE_MIN_ROWS",
    "TABLE_ROW_WIDTH_RATIO",
    "TUPLE_MAX_SIZE",
    "TUPLE_PATTERN_MIN",
    "UNNAMED_RE",
    "VARIANCE_RATIO",
    "WIDE_ELEMENT_MIN_WIDTH",
    "WIDE_ELEMENT_RATIO",
    "ZONE_MIN_MEMBERS",
    "ZONE_OVERLAP_ITEM",
    "ZONE_OVERLAP_ZONE",
    "_STAGE_A_TO_C_PATTERN_MAP",
    # -- Geometry (from .geometry) ------------------------------------------
    "get_bbox",
    "resolve_absolute_coords",
    "snap",
    "yaml_str",
    # -- Geometry (from .geometry) --------------------------------------------
    "filter_visible_children",
    "sort_by_y",
    # -- Metadata (from .metadata) ------------------------------------------
    "find_node_by_id",
    "get_root_node",
    "get_text_children_content",
    "is_off_canvas",
    "is_section_root",
    "is_unnamed",
    "load_metadata",
    "parse_figma_xml",
    "_count_flat_descendants",
    # -- Nested Context (from .nested_context) -------------------------------
    "load_prompt_template",
    # -- Naming (from .naming) ----------------------------------------------
    "to_kebab",
    "_jp_keyword_lookup",
    # -- Scoring (from .scoring) --------------------------------------------
    "alignment_bonus",
    "compute_gap_consistency",
    "compute_grouping_score",
    "compute_viewport_scale",
    "detect_regular_spacing",
    "detect_space_between",
    "detect_wrap",
    "infer_direction_two_elements",
    "is_decoration_pattern",
    "is_heading_like",
    "scaled_threshold",
    "size_similarity_bonus",
    "structure_hash",
    "structure_similarity",
    "_raw_distance",
    # -- Detection (from .detection) ----------------------------------------
    "count_nested_flat",
    "decoration_dominant_shape",
    "detect_bg_content_layers",
    "detect_consecutive_similar",
    "detect_en_jp_label_pairs",
    "detect_heading_content_pairs",
    "detect_highlight_text",
    "detect_horizontal_bar",
    "detect_repeating_tuple",
    "detect_table_rows",
    "find_absorbable_elements",
    "_compute_zone_bboxes",
    # -- Enrichment (from .enrichment) --------------------------------------
    "generate_enriched_table",
    "parse_enriched_table",
    "_collect_text_preview",
    "_compute_child_types",
    "_compute_flags",
    "_compute_method_tag",
    # -- Comparison (from .comparison) --------------------------------------
    "absorb_stage_c_dividers",
    "compare_grouping_by_section",
    "compare_grouping_results",
    "deduplicate_candidates",
    "validate_column_consistency",
    "_merge_stage_a_with_c_confident",
    "_merge_stage_c_with_a_remainder",
    "_should_absorb_into_higher",
    "_stage_a_pattern_key",
    # -- Stage C (from .stage_c) --------------------------------------------
    "collect_leaf_sections",
    "collect_recursion_targets",
    "heuristic_sub_group",
    "parse_plan_yaml",
    "write_plan_yaml",
    "_collect_from_groups",
    "_try_column_split",
    "_try_heading_split",
    "_try_spatial_split",
    "_try_yband_split",
    "_write_group_yaml",
    # -- Nested Context (from .nested_context) ------------------------------
    "generate_nested_context",
    "_format_stage_b_context",
    # -- Grouping Engine (from .grouping_engine) ----------------------------
    "UnionFind",
    "compute_adaptive_gap",
    "detect_grouping_candidates",
    "detect_header_footer_groups",
    "detect_pattern_groups",
    "detect_proximity_groups",
    "detect_semantic_groups",
    "detect_spacing_groups",
    "detect_variant_groups",
    "detect_vertical_zone_groups",
    "infer_zone_semantic_name",
    "is_card_like",
    "is_grid_like",
    "is_navigation_like",
    "walk_and_detect",
    "_is_protected_node",
    "_split_by_spatial_gap",
    # -- Semantic Rename (from .semantic_rename) ----------------------------
    "CTA_KEYWORDS",
    "RENAME_STRATEGIES",
    "SHAPE_PREFIXES",
    "collect_renames",
    "generate_rename_map",
    "has_image_wrapper",
    "infer_name",
    "infer_name_with_confidence",
    "infer_text_role",
    "_estimate_children_confidence",
    # -- Rename LLM Fallback (from .rename_llm_fallback) -------------------
    "LLM_CONFIDENCE_MAP",
    "LLM_DEFAULT_CONFIDENCE",
    "LLM_FALLBACK_CONFIDENCE_THRESHOLD",
    "build_fallback_context",
    "collect_low_confidence_renames",
    "format_fallback_prompt",
    "generate_fallback_context_file",
    "merge_llm_suggestions",
    "parse_llm_suggestions",
    # -- Grouping Compare (from .grouping_compare) -------------------------
    "format_report",
    "parse_stage_a_yaml",
    "parse_stage_c_yaml",
    "run_comparison",
    # -- Metadata Enricher (from .metadata_enricher) -----------------------
    "ENRICHMENT_KEYS",
    "enrich_metadata",
    "enrich_metadata_from_files",
    "enrich_node",
    # -- Grouping Postprocess (from .grouping_postprocess) -----------------
    "format_plan_yaml",
    "parse_plan_yaml_lines",
    "postprocess_plan",
    # -- Auto Layout (from .autolayout) ------------------------------------
    "infer_layout",
    "layout_from_enrichment",
    "run_autolayout_inference",
    "walk_and_infer",
    "_direction_hint_from_name",
    "_infer_direction",
    "_infer_direction_by_grid",
    # -- Sectioning (from .sectioning) -------------------------------------
    "classify_section_type",
    "detect_heuristic_hints",
    "run_sectioning_context",
    "_compute_gap_analysis",
    # -- Structure Analysis (from .structure_analysis) ---------------------
    "count_nodes",
    "detect_grouping_candidates_simple",
    "run_structure_analysis",
    # -- Grouping LLM Fallback (from .grouping_llm_fallback) ---------------
    "GROUPING_FALLBACK_HEADING_MAX_HEIGHT",
    "GROUPING_FALLBACK_MAX_SIBLINGS",
    "GROUPING_FALLBACK_MIN_SIBLINGS_AFTER_HEADING",
    "GROUPING_FALLBACK_STRUCTURE_SIMILARITY",
    "GROUPING_LLM_CONFIDENCE_MAP",
    "GROUPING_LLM_DEFAULT_CONFIDENCE",
    "build_grouping_fallback_context",
    "collect_undergrouped_sections",
    "format_grouping_fallback_prompt",
    "generate_grouping_fallback_context_file",
    "merge_grouping_suggestions",
    "parse_llm_grouping_suggestions",
    # -- Pattern Registry (from .pattern_registry) -------------------------
    "build_pattern_registry",
    "format_registry_summary",
    "lookup_pattern",
]
