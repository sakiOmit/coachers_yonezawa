---
name: figma-container-width-calculator
description: "Calculate accurate container width from Figma design data using artboard margin-based calculation"
disable-model-invocation: false
allowed-tools:
  - Read
  - Grep
context: fork
agent: general-purpose
---

# Figma Container Width Calculator

## Overview

A utility skill that calculates accurate container widths from Figma design data.
Addresses the issue where directly using Figma frame width attributes can produce incorrect results due to Auto Layout constraints, absolute positioning, or nested frame structures.

## Problem Statement

**Current Issue:**
- Directly using frame `width` attribute from Figma data
- Produces incorrect results when:
  1. Auto Layout has `max-width` constraints
  2. Absolutely positioned elements
  3. Nested frame structures
  4. Variable-width content

**Example (requirements page):**
- Artboard width: 1440px
- Content frame (1:2143): x=106, width=1228
- Current method: Uses width=1228 directly
- Issues: Doesn't account for design intent or Auto Layout constraints

## Solution: Artboard Margin-Based Calculation (Default)

### Calculation Formula

```
containerWidth = artboardWidth - (firstContentFrame.x * 2)
```

**Example:**
```
paddingLeft = 106px  (firstContentFrame.x)
containerWidth = 1440 - (106 * 2) = 1228px
```

### Advantages

- **Consistency**: Same calculation formula for all pages
- **Simplicity**: Easy to implement and test
- **Design Intent**: Guarantees left-right symmetry
- **Low Risk**: Minimal chance of errors

### Limitations

- Cannot handle asymmetric left/right margins
- For such cases, use Auto Layout max-width method (optional)

## Usage

```
/figma-container-width-calculator {figma_cache_path}

Arguments:
  figma_cache_path: Path to cached Figma data (e.g., .claude/cache/figma/requirements/pc/)
```

### Example

```bash
/figma-container-width-calculator .claude/cache/figma/requirements/pc/
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| figma_cache_path | Yes | Path to Figma cache directory containing metadata.json and design-context.json |

## Processing Flow

```
1. Read metadata.json
   └─ Extract artboardWidth (e.g., 1440px)

2. Read design-context.json
   └─ Find first content frame
   └─ Extract x position (e.g., 106px)

3. Calculate containerWidth
   └─ containerWidth = artboardWidth - (x * 2)

4. Optional: Check Auto Layout max-width
   └─ If node.layoutMode && node.maxWidth exists
   └─ Compare with calculated value
   └─ Report discrepancy if any

5. Output result
   └─ containerWidth: {value}px
   └─ Calculation: {artboardWidth} - ({x} * 2)
   └─ Method: artboard-margin-based
```

## Output Format

```yaml
container_width:
  value: 1228
  unit: "px"
  calculation:
    method: "artboard-margin-based"
    artboard_width: 1440
    margin_left: 106
    formula: "1440 - (106 * 2) = 1228"
  validation:
    auto_layout_max_width: null  # or value if exists
    discrepancy: false
```

## Auto Layout max-width Method (Optional)

For designs using Auto Layout with explicit max-width constraints:

### Calculation

```javascript
if (node.layoutMode && node.maxWidth) {
  containerWidth = node.maxWidth;
} else {
  // Fallback to artboard margin-based method
  containerWidth = artboardWidth - (firstContentFrame.x * 2);
}
```

### Use Cases

- Variable-width content
- Responsive design constraints
- Explicit max-width in Figma

### Trade-offs

- **Pros**: More accurate for Auto Layout designs
- **Cons**: Requires fallback logic, more complex

## Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| Missing metadata.json | File not found | Prompt user to run /figma-prefetch |
| Missing design-context.json | File not found | Prompt user to run /figma-prefetch |
| No content frames found | Empty children array | Use artboard width as-is |
| Invalid x position | x is null or undefined | Default to x=0 |
| Auto Layout parsing error | Exception | Fallback to artboard method |

## Integration with figma-implement

This skill is referenced in `/figma-implement` workflow:

**Step 2 (Design Context Retrieval):**
- After getting design-context.json, use this skill to calculate accurate container width
- Store result in project-convention.yaml

**Step 5 (Project Convention Translation):**
- Use calculated container width for SCSS variable generation
- Reference: `$container-width: {value}px`

## Related Rules

See `.claude/rules/figma-workflow.md` for container width calculation priority rules.

## Examples

### Basic Usage

```bash
# Calculate container width for requirements page
/figma-container-width-calculator .claude/cache/figma/requirements/pc/
```

**Output:**
```yaml
container_width:
  value: 1228
  unit: "px"
  calculation:
    method: "artboard-margin-based"
    artboard_width: 1440
    margin_left: 106
    formula: "1440 - (106 * 2) = 1228"
  validation:
    auto_layout_max_width: null
    discrepancy: false
```

### With Auto Layout Validation

```bash
# Calculate with Auto Layout validation
/figma-container-width-calculator .claude/cache/figma/top/pc/ --validate-auto-layout
```

**Output (with discrepancy):**
```yaml
container_width:
  value: 1228
  unit: "px"
  calculation:
    method: "artboard-margin-based"
    artboard_width: 1440
    margin_left: 106
    formula: "1440 - (106 * 2) = 1228"
  validation:
    auto_layout_max_width: 1200
    discrepancy: true
    warning: "Auto Layout max-width (1200px) differs from calculated value (1228px)"
```

## Design Prerequisites

For accurate container width calculation:

| Requirement | Reason |
|-------------|--------|
| Consistent left/right margins | Ensures artboard method accuracy |
| Auto Layout properly used | Enables optional max-width validation |
| Content frame at top level | Simplifies first frame detection |

## Limitations

### Not Supported

- Asymmetric left/right margins (without Auto Layout max-width)
- Nested container structures (without explicit guidance)
- Multi-column layouts (requires manual specification)

### Workarounds

For asymmetric designs:
1. Use Auto Layout max-width method
2. Or manually specify container width in project-convention.yaml

## Version

**Version**: 1.0.0
**Created**: 2026-01-31
**Last Updated**: 2026-01-31

## See Also

- `/figma-implement` - Main Figma implementation workflow
- `.claude/rules/figma-workflow.md` - Container width calculation rules
- `.claude/cache/figma/` - Figma cache directory structure
