"""Constants submodule for figma-prepare utilities.

Centralises all threshold values, detection parameters, and lookup tables
used across figma-prepare scripts.  Extracted from ``__init__.py`` so that
other modules can ``from figma_utils.constants import X`` without pulling
in the entire utility module.

Every constant listed here has a corresponding entry in
``.claude/rules/figma-prepare.md`` (閾値パラメータ table).
"""

import re

# ---------------------------------------------------------------------------
# Core layout / snap constants
# ---------------------------------------------------------------------------

GRID_SNAP = 4  # px — gap/padding snap unit (figma-prepare.md)
SECTION_ROOT_WIDTH = 1440  # Figma page-level frame width
SECTION_ROOT_WIDTH_RATIO = 0.9  # Issue 191: min width ratio for section root detection (>= 1296px)
ROW_TOLERANCE = 20  # px — Y-coordinate grouping tolerance for WRAP/grid row detection (Issue 131)
CV_THRESHOLD = 0.25  # Coefficient of variation threshold for regular spacing detection (Issue 138)
FLAT_THRESHOLD = 15  # children — flat structure detection threshold (Issue 140)
DEEP_NESTING_THRESHOLD = 6  # levels — deep nesting detection threshold (Issue 140)
OFF_CANVAS_MARGIN = 1.5  # multiplier — elements with x > page_width * OFF_CANVAS_MARGIN are off-canvas (Issue 182)
HORIZONTAL_BAR_MAX_HEIGHT = 100  # px — max Y-range for a horizontal bar pattern (Issue 184)
HORIZONTAL_BAR_MIN_ELEMENTS = 4  # minimum elements in a horizontal bar (Issue 184)
HORIZONTAL_BAR_VARIANCE_RATIO = 3  # X variance must exceed Y variance by this factor (Issue 184)
CENTER_ALIGN_VARIANCE = 4  # Center alignment variance threshold for counter-axis (std ~2px) (Issue 202)
ALIGN_TOLERANCE = 2  # px — alignment position tolerance for counter-axis MIN/MAX detection (Issue 202)
CONFIDENCE_HIGH_COV = 0.15  # Gap CoV below this → high confidence (Issue 202)
CONFIDENCE_MEDIUM_COV = 0.35  # Gap CoV below this → medium confidence (Issue 202)
BG_LEFT_OVERFLOW_WIDTH_RATIO = 0.5  # Left-overflow bg detection: min width as ratio of parent width (Issue 204)
SPATIAL_SPLIT_MIN_NON_LEAF = 6  # Non-leaf groups smaller than this are not split by spatial gap (Issue 206)

# --- Issue 201: Stage B heuristic hint thresholds (prepare-sectioning-context.sh) ---
HINT_HEADER_Y_RATIO = 0.05  # Header zone: top 5% of page height
HINT_FOOTER_Y_RATIO = 0.9  # Footer zone: bottom 10% of page height (y+h > page_h * 0.9)
HINT_WIDE_ELEMENT_RATIO = 0.8  # Header/footer width must exceed 80% of page width
HINT_BG_MIN_HEIGHT = 100  # px — background candidate RECTANGLE minimum height
HINT_HEADING_MAX_HEIGHT = 200  # px — heading candidate maximum height

# --- Issue 203: _compute_flags thresholds ---
FLAG_OVERFLOW_X_RATIO = 1.05  # Overflow detection: right edge > page_width * 1.05 (5% tolerance)
FLAG_OVERFLOW_Y_RATIO = 1.02  # Overflow-y detection: bottom edge > page_height * 1.02 (2% tolerance)
FLAG_BG_FULL_WIDTH_RATIO = 0.95  # bg-full: width >= 95% of page width
# bg-wide reuses BG_WIDTH_RATIO (0.8) — same semantic: "wide enough to be a background"
FLAG_TINY_MAX_SIZE = 50  # px — tiny element: both width and height < 50px

# ---------------------------------------------------------------------------
# Issues 207-210: detect-grouping-candidates.sh constants
# ---------------------------------------------------------------------------

PROXIMITY_GAP = 24  # px — proximity grouping distance (figma-prepare.md: proximity_gap)
REPEATED_PATTERN_MIN = 3  # occurrences — minimum for repeat pattern detection (figma-prepare.md: repeated_pattern_min)
JACCARD_THRESHOLD = 0.7  # fuzzy match threshold for pattern detection (figma-prepare.md: jaccard_threshold)
SPATIAL_GAP_THRESHOLD = 100  # px — min gap to split sub-groups (figma-prepare.md: spatial_gap_threshold)
HEADER_ZONE_HEIGHT = 120  # px — header detection zone from page top (figma-prepare.md: header_zone_height)
FOOTER_ZONE_HEIGHT = 300  # px — footer detection zone from page bottom (figma-prepare.md: footer_zone_height)
ZONE_OVERLAP_ITEM = 0.5  # 50% — vertical zone merge: item overlap ratio (figma-prepare.md: zone_overlap_item)
ZONE_OVERLAP_ZONE = 0.3  # 30% — vertical zone merge: zone overlap ratio (figma-prepare.md: zone_overlap_zone)
ZONE_MIN_MEMBERS = 3  # Minimum nodes per vertical zone group (benchmark fix: filter out tiny 1-2 node zones)
HEADER_MAX_ELEMENT_HEIGHT = 200  # px — max height for header zone elements (figma-prepare.md: header_max_element_height)
FOOTER_ZONE_MARGIN = 50  # px — extra margin for footer zone bottom (figma-prepare.md: footer_zone_margin)
HEADER_ZONE_MARGIN = 50  # px — extra margin for header zone bottom (Issue #266)
HEADER_TEXT_MAX_WIDTH = 200  # px — max width for nav-like text in header (figma-prepare.md: header_text_max_width)
HEADER_LOGO_MAX_WIDTH = 300  # px — max width for logo in header (figma-prepare.md: header_logo_max_width)
HEADER_LOGO_MAX_HEIGHT = 100  # px — max height for logo in header (figma-prepare.md: header_logo_max_height)
HEADER_NAV_MIN_TEXTS = 3  # min TEXT elements for nav detection in header (figma-prepare.md: header_nav_min_texts)
HERO_ZONE_DISTANCE = 200  # px — max distance from page top for hero detection (figma-prepare.md: hero_zone_distance)
LARGE_BG_WIDTH_RATIO = 0.6  # ratio of page width for large bg detection (figma-prepare.md: large_bg_width_ratio)

# --- Issues 215-220: generate-rename-map.sh / detect-grouping-candidates.sh constants ---
CTA_X_POSITION_RATIO = 0.8  # CTA detection: X position must be > parent_w * ratio (Issue 215)
SIDE_PANEL_RIGHT_X_RATIO = 0.9  # Side panel detection: right edge ratio (Issue 216)
SIDE_PANEL_LEFT_X_RATIO = 0.1  # Side panel detection: left edge ratio (Issue 216)
FOOTER_TEXT_RATIO = 0.3  # Footer detection: min TEXT children ratio (Issue 217)
IMAGE_WRAPPER_RATIO = 0.5  # Image wrapper detection: min image-like children ratio (Issue 218)
HEADING_BODY_TEXT_THRESHOLD = 50  # chars — text longer than this → body, shorter → heading (Issue 219)
GRID_SIZE_SIMILARITY = 0.20  # Grid detection: max width/height variation ratio (Issue 220)
DIVIDER_MAX_HEIGHT = 5  # px — thin horizontal rectangle → divider (figma-prepare.md: divider_max_height)
HEADER_Y_THRESHOLD = 100  # px — position from parent top to detect header (figma-prepare.md: header_y_threshold)
FOOTER_PROXIMITY = 100  # px — distance from parent bottom to detect footer (figma-prepare.md: footer_proximity)
FOOTER_MAX_HEIGHT = 200  # px — max height for footer detection (figma-prepare.md: footer_max_height)
WIDE_ELEMENT_RATIO = 0.7  # fraction of parent width to be 'wide' (figma-prepare.md: wide_element_ratio)
WIDE_ELEMENT_MIN_WIDTH = 500  # px — minimum absolute width for 'wide' (figma-prepare.md: wide_element_min_width)
ICON_MAX_SIZE = 48  # px — max width/height for icon detection (figma-prepare.md: icon_max_size)
BULLET_MAX_SIZE = 12  # px — max width/height for bullet point ELLIPSE detection (benchmark improvement 2)
SECTION_BG_WIDTH_RATIO = 0.9  # Section-level background RECTANGLE width ratio (>= 1296px, benchmark improvement 3)
BUTTON_MAX_HEIGHT = 70  # px — max height for button detection (figma-prepare.md: button_max_height)
BUTTON_MAX_WIDTH = 300  # px — max width for button detection (figma-prepare.md: button_max_width)
BUTTON_TEXT_MAX_LEN = 15  # chars — max text length for button role (figma-prepare.md: button_text_max_len)
LABEL_MAX_LEN = 20  # chars — max text length for label role (figma-prepare.md: label_max_len)
NAV_MIN_TEXT_COUNT = 4  # minimum TEXT children for nav detection (figma-prepare.md: nav_min_text_count)
NAV_MAX_TEXT_LEN = 20  # chars — max text length per nav item (figma-prepare.md: nav_max_text_len)
NAV_GRANDCHILD_MIN = 4  # minimum TEXT grandchildren for header nav (figma-prepare.md: nav_grandchild_min)

# --- Issue 211: infer-autolayout.sh constants ---
VARIANCE_RATIO = 1.5  # Auto Layout direction: X var > Y var × ratio → HORIZONTAL (figma-prepare.md: variance_ratio)

# --- Issue 212: generate-nested-grouping-context.sh constants ---
GRANDCHILD_THRESHOLD = 5  # Stage C: max node_ids to switch to grandchildren mode

# --- Issue 214: compare_grouping_results constants ---
COMPARE_MATCH_THRESHOLD = 0.5  # Jaccard threshold for Stage A/C group matching
STAGE_C_COVERAGE_THRESHOLD = 0.8  # Stage C adoption: coverage >= 80% → use Stage C, else Stage A fallback (legacy, see tiers below)

# --- Graduated Stage integration thresholds (Proposal 2) ---
STAGE_MERGE_TIER1 = 0.8   # coverage >= 80% → Stage C fully adopted
STAGE_MERGE_TIER2 = 0.6   # coverage >= 60% → Stage C + unmatched Stage A merged
STAGE_MERGE_TIER3 = 0.4   # coverage >= 40% → Stage A + high-confidence Stage C
# coverage < 40% → Stage A only

# --- Issue 224: Stage C recursive nesting ---
MAX_STAGE_C_DEPTH = 10  # Safety upper bound for Stage C recursion (converges naturally at 3-4)

# ---------------------------------------------------------------------------
# Issue 229: Detector disable/coverable sets
# ---------------------------------------------------------------------------

# Detectors that Stage C Claude inference can potentially replace
STAGE_C_COVERABLE_DETECTORS = {
    'bg-content',      # bg-content pattern in Stage C prompt
    'table',           # table pattern in Stage C prompt
    'highlight',       # highlight detection in Stage C prompt
    'tuple',           # card/list patterns in Stage C prompt
    'consecutive',     # list patterns in Stage C prompt
    'heading-content', # heading-pair pattern in Stage C prompt
}

# Detectors that should always remain in Stage A (not coverable by Stage C)
STAGE_A_ONLY_DETECTORS = {
    'header-footer',   # Root-level only, handled by Stage B
    'horizontal-bar',  # Root-level only, specialized pattern
    'zone',            # Root-level only, spatial grouping
    'semantic',        # Always useful as fallback
    'proximity',       # Fine-grained, always useful
    'spacing',         # Fine-grained, always useful
    'pattern',         # General pattern matching
}

# ---------------------------------------------------------------------------
# Issue 236: deduplicate_candidates constants
# ---------------------------------------------------------------------------

# Method priority for deduplication: higher = better quality
# Issue 165/166: consecutive (2.5) between pattern and zone; heading-content (3.5) between zone and semantic
# Issue 186: tuple (2.8) between consecutive and zone — type-sequence based, higher than structure_hash pattern
METHOD_PRIORITY = {
    'variant': 4.5,  # Higher than semantic — componentId is definitive
    'semantic': 4,
    'highlight': 3.8,
    'heading-content': 3.5,
    'zone': 3,
    'tuple': 2.8,
    'consecutive': 2.5,
    'pattern': 2,
    'spacing': 1,
    'proximity': 0,
}

# ---------------------------------------------------------------------------
# Unnamed layer detection pattern
# ---------------------------------------------------------------------------

UNNAMED_RE = re.compile(
    r'^(Rectangle|Ellipse|Line|Vector|Frame|Group|Component|Instance|Text|Polygon|Star|Image)\s*\d*$',
    re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Japanese keyword → English slug mapping (Issue 170)
# ---------------------------------------------------------------------------

JP_KEYWORD_MAP = {
    # Navigation / Actions
    'お問い合わせ': 'contact',
    '問い合わせ': 'contact',
    'お知らせ': 'news',
    '新着情報': 'news',
    '会社概要': 'company',
    '採用情報': 'recruit',
    'アクセス': 'access',
    'よくある質問': 'faq',
    'プライバシー': 'privacy',
    '利用規約': 'terms',
    'サイトマップ': 'sitemap',
    'ホーム': 'home',
    'トップ': 'top',
    'ログイン': 'login',
    '検索': 'search',
    '詳しく': 'more',
    '一覧': 'list',
    '特徴': 'features',
    '実績': 'works',
    'サービス': 'service',
    '料金': 'pricing',
    'メニュー': 'menu',
    'プラン': 'plan',
    'コンセプト': 'concept',
    # Food / Catering domain
    'ケータリング': 'catering',
    'フィンガーフード': 'finger-food',
    'フード': 'food',
    'イベント': 'event',
    'パーティー': 'party',
    'パーティ': 'party',
    # Business domain
    '企業': 'corporate',
    'オフィス': 'office',
    'スタッフ': 'staff',
    # Section types
    'ヒーロー': 'hero',
    'フッター': 'footer',
    'ヘッダー': 'header',
    'ナビゲーション': 'nav',
    'ギャラリー': 'gallery',
    'テスティモニアル': 'testimonial',
    'ブログ': 'blog',
    'カテゴリ': 'category',
    'カテゴリー': 'category',
    # Common words
    'ビジョン': 'vision',
    'ミッション': 'mission',
    '代表': 'representative',
    '紹介': 'introduction',
    'ご挨拶': 'greeting',
    '歴史': 'history',
    '沿革': 'history',
    '強み': 'strength',
    '理念': 'philosophy',
    '事業内容': 'business',
    '事業紹介': 'business',
    '事業': 'business',
    '求人': 'job',
    '募集': 'recruit',
    '会社情報': 'company-info',
    '採用ブログ': 'recruit-blog',
}

# ---------------------------------------------------------------------------
# Issue 186: Repeating tuple pattern detection
# ---------------------------------------------------------------------------

TUPLE_PATTERN_MIN = 3  # Minimum repetitions to detect a tuple pattern
TUPLE_MAX_SIZE = 5  # Maximum elements per tuple

# ---------------------------------------------------------------------------
# Issue 165: Consecutive pattern detection
# ---------------------------------------------------------------------------

CONSECUTIVE_PATTERN_MIN = 3  # Minimum consecutive siblings with similar structure

# ---------------------------------------------------------------------------
# Issue 166: Heading-content pair detection
# ---------------------------------------------------------------------------

HEADING_MAX_HEIGHT_RATIO = 0.4  # Heading must be < 40% of content height
HEADING_SOFT_HEIGHT_RATIO = 0.8  # Heading can be 40-80% of content height if heading-like
HEADING_MAX_CHILDREN = 5  # Heading frames typically have few children
HEADING_TEXT_RATIO = 0.5  # At least 50% of leaf descendants should be TEXT/VECTOR

# ---------------------------------------------------------------------------
# Issue 167: Loose element absorption
# ---------------------------------------------------------------------------

LOOSE_ELEMENT_MAX_HEIGHT = 20  # Small elements (dividers, spacers)
LOOSE_ABSORPTION_DISTANCE = 200  # Max distance to absorb into a group (member-level)

# ---------------------------------------------------------------------------
# Issue 189: Decoration dot pattern detection
# ---------------------------------------------------------------------------

DECORATION_MAX_SIZE = 200  # Max width/height for decoration frame
DECORATION_SHAPE_RATIO = 0.6  # Min ratio of shape children (ELLIPSE/RECTANGLE/VECTOR)
DECORATION_MIN_SHAPES = 3  # Min number of shape leaf children

# ---------------------------------------------------------------------------
# Issue 190: Highlight text pattern detection
# ---------------------------------------------------------------------------

HIGHLIGHT_OVERLAP_RATIO = 0.8  # Min Y-overlap ratio for highlight detection
HIGHLIGHT_X_OVERLAP_RATIO = 0.5  # Min X-overlap ratio for highlight detection (Issue 196)
HIGHLIGHT_TEXT_MAX_LEN = 30  # Max text length for highlight
HIGHLIGHT_HEIGHT_RATIO_MIN = 0.5  # Min RECT height / TEXT height ratio
HIGHLIGHT_HEIGHT_RATIO_MAX = 2.0  # Max RECT height / TEXT height ratio

# ---------------------------------------------------------------------------
# Issue 180: Background-content layer detection
# ---------------------------------------------------------------------------

BG_WIDTH_RATIO = 0.8  # Background RECTANGLE must cover >=80% of parent width
BG_MIN_HEIGHT_RATIO = 0.3  # Background must be >=30% of parent height
BG_DECORATION_MAX_AREA_RATIO = 0.05  # Small same-positioned elements are decoration
OVERFLOW_BG_MIN_WIDTH = 1400  # px — elements near/exceeding page width are bg candidates (Issue 183)

# ---------------------------------------------------------------------------
# Issue 185: EN+JP label pair detection
# ---------------------------------------------------------------------------

EN_LABEL_MAX_WORDS = 3  # Max words for English label (e.g., "OUR BUSINESS")
EN_JP_PAIR_MAX_DISTANCE = 200  # px — max distance between EN and JP label pair

# ---------------------------------------------------------------------------
# Issue 193: CTA square button detection
# ---------------------------------------------------------------------------

CTA_SQUARE_RATIO_MIN = 0.8  # Min width/height ratio for square CTA
CTA_SQUARE_RATIO_MAX = 1.2  # Max width/height ratio for square CTA
CTA_Y_THRESHOLD = 100  # px — max Y position from top for CTA placement

# ---------------------------------------------------------------------------
# Issue 192: Side panel detection
# ---------------------------------------------------------------------------

SIDE_PANEL_MAX_WIDTH = 80  # px — max width for side panel
SIDE_PANEL_HEIGHT_RATIO = 3.0  # Min height/width ratio for side panel

# ---------------------------------------------------------------------------
# Issue 181: Table row structure detection
# ---------------------------------------------------------------------------

TABLE_MIN_ROWS = 3  # Minimum background RECTANGLEs to form a table
TABLE_ROW_WIDTH_RATIO = 0.9  # Row bg RECTANGLE must cover >=90% of parent width
TABLE_DIVIDER_MAX_HEIGHT = 2  # px — divider VECTORs are <=2px height

# ---------------------------------------------------------------------------
# Viewport-relative threshold scaling (Proposal 6)
# ---------------------------------------------------------------------------

# Base viewport dimensions (design reference)
BASE_VIEWPORT_WIDTH = 1440
BASE_VIEWPORT_HEIGHT = 8500  # Typical tall landing page


def compute_viewport_scale(page_width, page_height=0):
    """Compute scale factors relative to base viewport.

    Args:
        page_width: Actual page/artboard width in px.
        page_height: Actual page/artboard height in px (0 = use width ratio).

    Returns:
        dict with 'w_scale', 'h_scale', 'scale' (geometric mean).
    """
    w_scale = page_width / BASE_VIEWPORT_WIDTH if BASE_VIEWPORT_WIDTH > 0 else 1.0
    h_scale = page_height / BASE_VIEWPORT_HEIGHT if page_height > 0 and BASE_VIEWPORT_HEIGHT > 0 else w_scale
    scale = (w_scale * h_scale) ** 0.5  # geometric mean
    return {
        'w_scale': w_scale,
        'h_scale': h_scale,
        'scale': scale,
    }


def scaled_threshold(base_value, scale_factor, min_value=None, max_value=None):
    """Scale a threshold value by a factor, with optional bounds.

    Args:
        base_value: Original threshold value.
        scale_factor: Multiplier (e.g., 0.5 for half-width viewport).
        min_value: Floor value (don't go below this).
        max_value: Ceiling value (don't go above this).

    Returns:
        Scaled integer value.
    """
    result = int(base_value * scale_factor)
    if min_value is not None:
        result = max(result, min_value)
    if max_value is not None:
        result = min(result, max_value)
    return result


# ---------------------------------------------------------------------------
# Stage A → Stage C pattern mapping (Issue 229)
# ---------------------------------------------------------------------------

_STAGE_A_TO_C_PATTERN_MAP = {
    # Stage A method -> possible Stage C patterns
    'semantic:card-list': ['card'],
    'semantic:navigation': ['list'],
    'semantic:grid': ['card', 'list'],
    'semantic:header': ['single'],
    'semantic:footer': ['single'],
    'pattern': ['card', 'list'],
    'spacing': ['list'],
    'proximity': ['single', 'list', 'two-column'],
    'consecutive': ['card', 'list'],
    'tuple': ['card', 'list'],
    'heading-content': ['heading-pair'],
    'highlight': ['heading-pair', 'single', 'decoration'],
    'zone': ['single', 'list', 'two-column'],
    'bg-content': ['bg-content'],
    'table': ['table'],
    'horizontal-bar': ['list', 'single'],
    'variant': ['card', 'list'],  # Variants are typically card or list patterns
}
