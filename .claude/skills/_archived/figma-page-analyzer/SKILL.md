---
name: figma-page-analyzer
description: "Pre-analyze Figma page scale (height, element count, complexity) and propose optimal retrieval strategy (normal/split) considering MCP limits."
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - mcp__figma__get_metadata
context: fork
agent: general-purpose
---

# Figma Page Analyzer

## Overview

A skill that pre-analyzes Figma page scale (height, element count, complexity) and proposes optimal retrieval strategies (normal retrieval/split retrieval).
Considers Figma MCP limits (8,000px height limit, 60,000 character output limit) to determine the best approach before implementation.

### Background

Figma MCP has the following limits:

| Limit Type | Threshold | Behavior When Exceeded |
|------------|-----------|------------------------|
| Output size | 60,000 chars | Returns metadata + screenshot only |
| Node height | 8,000px | Warning/truncation may occur |
| Element count | No clear threshold | Degrades based on complexity |

Running `get_design_context` without pre-analysis on large pages causes:
- Token waste
- Incomplete data retrieval
- Time loss from re-fetching

This skill prevents these issues and supports efficient Figma implementation.

## Usage

```
/figma-page-analyzer [Figma URL]
```

Or

```
/figma-page-analyzer --file-key {fileKey} --node-id {nodeId}
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| URL | Yes* | Figma page URL |
| --file-key | Yes* | Figma file key (alternative to URL) |
| --node-id | Yes* | Target node ID |
| --threshold | No | Custom threshold settings (JSON format) |
| --output | No | Output path (default: stdout) |

*Either URL or --file-key + --node-id is required

## Output

### Analysis Report (JSON Format)

```json
{
  "metadata": {
    "file_key": "wbpri0A53IqL1KvkRBtvkl",
    "node_id": "1:2",
    "page_name": "Top Page",
    "timestamp": "2026-01-30T13:00:00Z"
  },
  "dimensions": {
    "width": 1440,
    "height": 12500,
    "height_exceeds_limit": true
  },
  "complexity": {
    "total_nodes": 450,
    "top_level_frames": 8,
    "estimated_chars": 75000,
    "complexity_score": "HIGH"
  },
  "risk_assessment": {
    "height_risk": "HIGH",
    "size_risk": "HIGH",
    "overall_risk": "HIGH"
  },
  "recommended_strategy": {
    "approach": "SPLIT",
    "reason": "Height 12,500px exceeds 8,000px limit, estimated output 75,000 chars exceeds 60,000 limit",
    "split_plan": [
      {
        "section_name": "Hero + About",
        "node_ids": ["1:100", "1:200"],
        "estimated_height": 2500,
        "priority": 1
      }
    ]
  },
  "cache_recommendation": {
    "use_cache": true,
    "cache_path": ".claude/cache/figma/{fileKey}_{nodeId}_*.json",
    "ttl_hours": 24
  }
}
```

### Standard Output (Summary)

```
══════════════════════════════════════════════════════════
  Figma Page Analysis Report
══════════════════════════════════════════════════════════

📄 Page: Top Page (1:2)
📐 Dimensions: 1440 x 12500 px
📊 Complexity: HIGH (450 nodes)

⚠️  RISK ASSESSMENT
   • Height: HIGH (12,500px > 8,000px limit)
   • Size:   HIGH (75,000 chars > 60,000 limit)

✅ RECOMMENDED STRATEGY: SPLIT

   Split into 4 sections:
   1. Hero + About     (2,500px)  → node-ids: 1:100, 1:200
   2. Services         (3,000px)  → node-ids: 1:300
   3. News + Contact   (4,000px)  → node-ids: 1:400, 1:500
   4. Footer           (3,000px)  → node-ids: 1:600

💡 TIP: Run get_design_context for each section separately.
══════════════════════════════════════════════════════════
```

## Processing Flow

```
1. Input Parsing
   └─ Extract fileKey/nodeId from URL

2. Lightweight Metadata Retrieval
   └─ Get page structure via get_metadata (no code retrieval)

3. Scale Analysis
   ├─ Calculate page height (from top-level Frame coordinates)
   ├─ Count nodes
   └─ Estimate character count (nodes × average coefficient)

4. Risk Assessment
   ├─ Height risk: height > 8,000px
   ├─ Size risk: estimated_chars > 60,000
   └─ Overall risk: MAX(height, size)

5. Strategy Decision
   ├─ LOW/MEDIUM risk → NORMAL (standard retrieval)
   └─ HIGH risk → SPLIT (split retrieval)

6. Split Plan Generation (for SPLIT)
   ├─ Get top-level Frames
   ├─ Sort by Y coordinate
   ├─ Group to stay under 8,000px
   └─ Assign execution priority

7. Cache Check
   └─ Check for existing cache

8. Output Generation
   └─ JSON + summary output
```

## Analysis Algorithm

### Scale Metrics Calculation

```
1. Page height
   height = max(frame.y + frame.height) for all top-level frames

2. Node count
   total_nodes = count(all nodes in metadata)

3. Estimated characters
   estimated_chars = total_nodes × 150  # empirical coefficient

4. Complexity score
   if total_nodes > 300 OR estimated_chars > 50000:
     complexity_score = "HIGH"
   elif total_nodes > 150 OR estimated_chars > 30000:
     complexity_score = "MEDIUM"
   else:
     complexity_score = "LOW"
```

### Risk Assessment Matrix

| Metric | LOW | MEDIUM | HIGH |
|--------|-----|--------|------|
| Height | < 5,000px | 5,000-8,000px | > 8,000px |
| Estimated chars | < 40,000 | 40,000-60,000 | > 60,000 |
| Node count | < 150 | 150-300 | > 300 |

### Strategy Decision Logic

```
if overall_risk == "LOW":
    strategy = "NORMAL"
    reason = "Page scale within MCP limits"

elif overall_risk == "MEDIUM":
    strategy = "NORMAL_WITH_CAUTION"
    reason = "Close to limits, monitor response"

elif overall_risk == "HIGH":
    strategy = "SPLIT"
    reason = "High probability of exceeding MCP limits"
    generate_split_plan()
```

### Split Plan Algorithm

```
1. Get top-level Frames
2. Sort by Y coordinate
3. Group to keep cumulative height under 8,000px
4. Assign section names to each group
5. Assign priority (top to bottom)
```

## Error Handling

| Error | Response |
|-------|----------|
| Figma API timeout | 3 retries, then error output |
| Permission error | Output error message and exit |
| Metadata fetch failure | Check cache, error if none |
| Invalid nodeId | Output error message and exit |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma/` | Cache storage |
| `.claude/rules/figma.md` | Figma rules (cache strategy) |
| `.claude/rules/figma-workflow.md` | Figma workflow rules |
| `.claude/skills/figma-component-analyzer/` | Related skill (component analysis) |

## Examples

### Basic Usage

```bash
/figma-page-analyzer https://www.figma.com/design/xxx/file?node-id=1-2
```

### File Key Specification

```bash
/figma-page-analyzer --file-key wbpri0A53IqL1KvkRBtvkl --node-id 1:2
```

### Custom Threshold

```bash
/figma-page-analyzer --file-key xxx --node-id 1:2 --threshold '{"height_limit": 6000, "char_limit": 50000}'
```

### JSON Output

```bash
/figma-page-analyzer --file-key xxx --node-id 1:2 --output ./analysis.json
```

## Related Skills

| Skill | Integration |
|-------|-------------|
| figma-component-analyzer | Pass analysis results to component analysis |
| figma-implement-orchestrator | Execute implementation following split plan |

---

**Version**: 1.0.0
**Created**: 2026-01-30
