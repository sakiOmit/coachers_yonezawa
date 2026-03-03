# Strategy Decision

Detailed documentation for the retrieval strategy decision logic in figma-prefetch.

## Overview

The strategy decision determines the optimal approach for retrieving Figma design data based on page scale and complexity.

## Strategy Types

### NORMAL

Direct retrieval using CLI or MCP.

**Criteria**:
- Height < 5,000px
- Top-level frames < 8
- Estimated token usage < 100,000

**Next Step**: `/figma-implement`

### SPLIT_RECOMMENDED

Split retrieval recommended but not mandatory.

**Criteria**:
- Height 5,000-8,000px
- Top-level frames 8-12
- Estimated token usage 100,000-150,000

**Next Step**: `/figma-recursive-splitter` or `/figma-implement`

### SPLIT_REQUIRED

Split retrieval mandatory to avoid token limits.

**Criteria**:
- Height > 8,000px
- Top-level frames > 12
- Estimated token usage > 150,000

**Next Step**: `/figma-recursive-splitter`

## Scale Thresholds

### Height Thresholds

| Height | Scale | Risk Level |
|--------|-------|------------|
| < 3,000px | Small | Low |
| 3,000-5,000px | Medium | Medium |
| 5,000-8,000px | Large | High |
| > 8,000px | Very Large | Critical |

### Frame Count Thresholds

| Frames | Scale | Notes |
|--------|-------|-------|
| < 5 | Simple | Single-shot retrieval OK |
| 5-8 | Moderate | May need monitoring |
| 8-12 | Complex | Consider split |
| > 12 | Very Complex | Split required |

## Decision Algorithm

```python
def decide_strategy(page_height, frame_count, estimated_complexity=None):
    """
    Determine the optimal retrieval strategy.

    Args:
        page_height: Total page height in pixels
        frame_count: Number of top-level frames
        estimated_complexity: Optional complexity score

    Returns:
        tuple: (strategy, next_step, reason)
    """

    # Critical thresholds
    if page_height > 8000:
        return (
            "SPLIT_REQUIRED",
            "/figma-recursive-splitter",
            f"Page height {page_height}px exceeds 8,000px limit"
        )

    if frame_count > 12:
        return (
            "SPLIT_REQUIRED",
            "/figma-recursive-splitter",
            f"Frame count {frame_count} exceeds 12 frame limit"
        )

    # Recommended thresholds
    if page_height > 5000 or frame_count > 8:
        return (
            "SPLIT_RECOMMENDED",
            "/figma-recursive-splitter",
            f"Page scale (height: {page_height}px, frames: {frame_count}) "
            "may cause token limit issues"
        )

    # Normal operation
    return (
        "NORMAL",
        "/figma-implement",
        "Page scale is within normal limits"
    )
```

## Token Estimation

### Estimation Formula

```python
def estimate_tokens(page_height, frame_count, text_density=1.0):
    """
    Estimate token consumption for get_design_context.

    This is a rough estimate; actual tokens may vary.

    Base factors:
    - ~50 tokens per 100px height
    - ~5,000 tokens per frame
    - Text density multiplier (0.5-2.0)
    """
    height_tokens = (page_height / 100) * 50
    frame_tokens = frame_count * 5000

    base_tokens = (height_tokens + frame_tokens) * text_density

    # Add overhead for structure
    overhead = base_tokens * 0.2

    return int(base_tokens + overhead)
```

### Token Limits

| Limit | Value | Source |
|-------|-------|--------|
| MCP soft limit | ~100,000 | Truncation risk |
| MCP hard limit | ~150,000 | Guaranteed truncation |
| Recommended max | 80,000 | Safe operation |

## Strategy Matrix

### By Cache Status

| Cache Status | Page Scale | Strategy |
|--------------|------------|----------|
| Valid (< 24h) | Any | Use cache directly |
| Expired | Small | CLI pre-fetch → NORMAL |
| Expired | Medium | CLI pre-fetch → NORMAL or SPLIT |
| Expired | Large | CLI pre-fetch → SPLIT_RECOMMENDED |
| Not Found | Small | CLI pre-fetch → NORMAL |
| Not Found | Large | Metadata only → SPLIT_REQUIRED |

### By Page Type

| Page Type | Typical Scale | Recommended Strategy |
|-----------|---------------|---------------------|
| LP (Landing Page) | Large | SPLIT_RECOMMENDED |
| Company Page | Medium | NORMAL |
| Contact Form | Small | NORMAL |
| Article/News | Small-Medium | NORMAL |
| Product List | Large | SPLIT_REQUIRED |
| Portfolio | Medium-Large | SPLIT_RECOMMENDED |

## Decision Output Format

### Console Output

```
╔═══════════════════════════════════════════════════════════════╗
║  Strategy Decision                                            ║
╠═══════════════════════════════════════════════════════════════╣
║  Page Scale: LARGE                                            ║
║  Height: 7,500px                                              ║
║  Top-level Frames: 10                                         ║
║  Estimated Tokens: ~95,000                                    ║
╠═══════════════════════════════════════════════════════════════╣
║  Strategy: SPLIT_RECOMMENDED                                  ║
║                                                               ║
║  Reason: Page height 7,500px exceeds 5,000px threshold.       ║
║          Direct retrieval may cause token limit issues.       ║
╠═══════════════════════════════════════════════════════════════╣
║  Next Step Options:                                           ║
║                                                               ║
║  Option A (Recommended):                                      ║
║    /figma-recursive-splitter https://...                      ║
║                                                               ║
║  Option B (If tokens are acceptable):                         ║
║    /figma-implement https://... --no-screenshot               ║
╚═══════════════════════════════════════════════════════════════╝
```

### YAML Output (prefetch-info.yaml)

```yaml
strategy: "SPLIT_RECOMMENDED"
scale:
  height: 7500
  frames: 10
  estimated_tokens: 95000
  risk_level: "high"
decision:
  reason: "Page height 7,500px exceeds 5,000px threshold"
  next_step: "/figma-recursive-splitter"
  alternatives:
    - skill: "/figma-implement"
      condition: "If tokens are acceptable"
```

## Override Options

### Force Normal Strategy

```bash
/figma-prefetch {url} --force-normal
```

Use when:
- Previous successful retrieval at this scale
- Token limit has been increased
- Testing purposes

### Force Split Strategy

```bash
/figma-prefetch {url} --force-split
```

Use when:
- Want maximum reliability
- Preparing for parallel workers
- Previous token limit issues

## Edge Cases

### Very Small Pages

Pages under 1,000px height:
- Always use NORMAL
- Skip detailed scale check
- Proceed directly to CLI pre-fetch

### Extremely Large Pages

Pages over 15,000px height:
- Force SPLIT_REQUIRED
- Recommend `/figma-section-splitter` for parallel workers
- Warn about potential multi-session implementation

### Dynamic Content Pages

Pages with repeater/list content:
- Frame count may be misleading
- Check actual nested complexity
- Consider lower thresholds

## Related Configuration

### Threshold Overrides

In `.claude/config/figma-thresholds.yaml`:

```yaml
# Custom thresholds for this project
height:
  normal_max: 5000
  split_recommended_max: 8000
frames:
  normal_max: 8
  split_recommended_max: 12
tokens:
  soft_limit: 100000
  hard_limit: 150000
```

### Page-Specific Overrides

In `config/wordpress-pages.yaml`:

```yaml
- slug: home
  figma:
    override_strategy: "SPLIT_REQUIRED"
    reason: "Home page has dynamic components"
```
