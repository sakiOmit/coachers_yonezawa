---
name: figma-visual-diff-runner
description: "Automatically verify visual differences between Figma design and implemented page using Playwright and pixelmatch"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - mcp__figma__get_screenshot
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_take_screenshot
  - mcp__playwright__browser_snapshot
  - mcp__playwright__browser_resize
context: fork
agent: general-purpose
---

# Figma Visual Diff Runner

## Overview

Automatically verify visual differences between Figma design and implemented pages. This skill captures screenshots using Playwright MCP, compares images with pixelmatch/pngjs, and attempts auto-fix iterations up to 5 times when differences are detected.

## Usage

```
/figma-visual-diff-runner [Figma URL] [Implementation URL]
```

Or with explicit parameters:

```
/figma-visual-diff-runner --figma-file-key {fileKey} --figma-node-id {nodeId} --impl-url {URL}
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| Figma URL | Yes* | Figma node URL |
| Implementation URL | Yes | Implemented page URL (localhost allowed) |
| --figma-file-key | Yes* | Figma file key (alternative to URL) |
| --figma-node-id | Yes* | Figma node ID |
| --impl-url | Yes* | Implementation page URL |
| --viewport | No | Viewport size (default: 1440x900) |
| --selector | No | Target selector for comparison (default: full page) |
| --strict | No | Strict mode (zero tolerance) |
| --max-iterations | No | Max iteration count (default: 5) |
| --output | No | Output path (default: `.claude/reports/visual-diff/`) |

*Either Figma URL or --figma-file-key + --figma-node-id required

## Output

### Directory Structure

```
.claude/reports/visual-diff/{timestamp}/
├── figma-screenshot.png      # Figma design screenshot
├── impl-screenshot.png       # Implementation screenshot
├── diff.png                  # Diff image (red highlights)
├── diff-report.json          # Diff report (JSON)
└── diff-report.md            # Diff report (Markdown)
```

### diff-report.json

```json
{
  "metadata": {
    "figma_file_key": "xxx",
    "figma_node_id": "1:2",
    "impl_url": "http://localhost:8080/about/",
    "viewport": { "width": 1440, "height": 900 },
    "timestamp": "2026-01-30T12:00:00Z"
  },
  "result": {
    "status": "pass|fail",
    "diff_percentage": 0.5,
    "diff_pixels": 1250,
    "total_pixels": 1296000,
    "iterations_used": 2
  },
  "issues": [
    {
      "type": "color_mismatch",
      "location": { "x": 100, "y": 200 },
      "expected": "#d71218",
      "actual": "#d81318",
      "severity": "low"
    }
  ]
}
```

## Processing Flow

```
1. Parse Input
   ├─ Extract fileKey/nodeId from Figma URL
   └─ Validate implementation URL

2. Capture Figma Screenshot
   ├─ Call mcp__figma__get_screenshot
   └─ Save to figma-screenshot.png

3. Capture Implementation Screenshot
   ├─ Navigate with mcp__playwright__browser_navigate
   ├─ Capture with mcp__playwright__browser_take_screenshot
   └─ Save to impl-screenshot.png

4. Compare Images
   ├─ Load both images with pngjs
   ├─ Run pixelmatch comparison
   ├─ Apply tolerance settings:
   │   ├─ Position: ±1px
   │   ├─ Color (RGB): exact match (±0)
   │   └─ Opacity: ±0.01
   └─ Generate diff image

5. Evaluate Diff
   ├─ diff_percentage < 0.1% → PASS
   ├─ diff_percentage >= 0.1% → Fix iteration
   └─ --strict mode: diff_percentage = 0% for PASS

6. Fix Iteration (max 5 times)
   ├─ Identify diff locations
   ├─ Propose fixes
   ├─ Execute fixes (SCSS/HTML adjustments)
   ├─ Recapture screenshot
   └─ Re-compare

7. Generate Report
   ├─ Create diff-report.json
   └─ Create diff-report.md
```

## Tolerance Settings

Per `.claude/rules/figma-workflow.md`:

| Item | Tolerance | pixelmatch Option |
|------|-----------|-------------------|
| Position (px) | ±1px | N/A (preprocessing) |
| Color (RGB) | Exact match | `threshold: 0` |
| Opacity | ±0.01 | `alpha: 0.01` |

### Strict Mode (--strict)

```javascript
{
  threshold: 0,
  includeAA: true,
  alpha: 0
}
```

## Iteration Logic

```
iteration = 0
max_iterations = 5
pass_threshold = 0.1%

while (iteration < max_iterations) {
  1. Capture screenshots (Figma + Implementation)
  2. Compare images

  if (diff_percentage < pass_threshold) {
    return PASS
  }

  3. Analyze diff locations
     - Color mismatch → Fix SCSS variables
     - Position offset → Adjust margin/padding
     - Size difference → Adjust width/height

  4. Execute fixes
     - Edit SCSS/PHP with Edit tool
     - Run build (npm run build)

  5. iteration++
}

if (iteration >= max_iterations) {
  return FAIL with remaining_issues
}
```

### Iteration Abort Conditions

- Diff percentage not improving (2 consecutive times)
- Fatal error (build failure, page 404, etc.)
- User abort request

## Error Handling

| Error | Response |
|-------|----------|
| Figma screenshot failed | Retry 3 times, then report error |
| Implementation page 404 | Report error immediately, prompt URL check |
| Image size mismatch | Resize and compare, output warning |
| Playwright timeout | Extend page load wait time |
| pixelmatch error | Check image format, attempt PNG conversion |
| 5 iterations exceeded | Report remaining diffs and FAIL |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/figma-workflow.md` | Tolerance settings, Playwright conflict prevention |
| `.claude/reports/visual-diff/` | Diff report storage |
| `.claude/cache/figma/` | Figma screenshot cache |
| `package.json` | pixelmatch/pngjs dependencies |

## Examples

### Basic Usage (Section Level)

```bash
/figma-visual-diff-runner https://www.figma.com/design/xxx/file?node-id=1-2 http://localhost:8080/about/
```

### Selector Specified (Specific Section Only)

```bash
/figma-visual-diff-runner \
  --figma-file-key xxx \
  --figma-node-id 1:2 \
  --impl-url http://localhost:8080/ \
  --selector ".p-hero"
```

### Strict Mode (Zero Tolerance)

```bash
/figma-visual-diff-runner \
  --figma-file-key xxx \
  --figma-node-id 1:2 \
  --impl-url http://localhost:8080/ \
  --strict
```

### SP Viewport Verification

```bash
/figma-visual-diff-runner \
  --figma-file-key xxx \
  --figma-node-id 3:4 \
  --impl-url http://localhost:8080/ \
  --viewport 375x667
```

### Limited Iterations

```bash
/figma-visual-diff-runner \
  --figma-file-key xxx \
  --figma-node-id 1:2 \
  --impl-url http://localhost:8080/ \
  --max-iterations 3
```

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Author**: Auto-generated
