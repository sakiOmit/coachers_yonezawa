---
name: figma-recursive-splitter
description: "Split large Figma pages recursively using BFS algorithm when they exceed token limits, enabling efficient design data retrieval."
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - mcp__figma__get_metadata
  - mcp__figma__get_design_context
context: fork
agent: general-purpose
---

# Figma Recursive Splitter

## Overview

Split large Figma pages (exceeding token limits) hierarchically and retrieve design data recursively. Uses Breadth-First Search (BFS) algorithm to efficiently capture the overall structure while retrieving design data.

## Usage

```
/figma-recursive-splitter {Figma URL}
```

or

```
/figma-recursive-splitter --file-key {fileKey} --node-id {nodeId}
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| URL | Yes* | Figma page URL |
| --file-key | Yes* | Figma file key (alternative to URL) |
| --node-id | Yes* | Target node ID |
| --output | No | Output path (default: `.claude/cache/figma/split-{nodeId}-{timestamp}/`) |
| --threshold | No | Complexity threshold (default: 50) |
| --max-depth | No | Maximum recursion depth (default: 5) |
| --strategy | No | Split strategy: bfs/dfs (default: bfs) |

*Either URL or --file-key + --node-id is required

## Output

### Directory Structure

```
.claude/cache/figma/split-1:671-20260130/
├── metadata.json           # Split metadata
├── structure.json          # Hierarchy structure
├── nodes/
│   ├── 1:675.json         # Header
│   ├── 1:676.json         # Hero Text
│   └── ...                # Each split node
└── summary.md              # Split summary
```

### metadata.json

```json
{
  "file_key": "wbpri0A53IqL1KvkRBtvkl",
  "root_node_id": "1:671",
  "root_name": "/interview",
  "timestamp": "2026-01-30T13:00:00Z",
  "total_nodes": 18,
  "split_depth": 2,
  "strategy": "bfs",
  "threshold": 50
}
```

### structure.json

```json
{
  "1:671": {
    "name": "/interview",
    "file_key": "wbpri0A53IqL1KvkRBtvkl",
    "size": {"width": 1440, "height": 10410},
    "complexity": 95,
    "split": true,
    "children_sorted_by_y": [
      {"id": "1:675", "name": "Header", "section_id": "interview/header", "y": 0, "figma_url": "https://www.figma.com/design/wbpri0A53IqL1KvkRBtvkl/?node-id=1-675&m=dev"},
      {"id": "1:676", "name": "Hero Text", "section_id": "interview/hero-text", "y": 196, "figma_url": "https://www.figma.com/design/wbpri0A53IqL1KvkRBtvkl/?node-id=1-676&m=dev"},
      {"id": "1:691", "name": "Breadcrumb", "section_id": "interview/breadcrumb", "y": 112, "figma_url": "https://www.figma.com/design/wbpri0A53IqL1KvkRBtvkl/?node-id=1-691&m=dev"}
    ]
  }
}
```

**重要**: `figma_url` は各セクションのFigmaデザインに直接アクセスできるURL。
生成式: `https://www.figma.com/design/{file_key}/?node-id={nodeId（:を-に変換）}&m=dev`

**重要**: children はY座標の昇順でソートし、視覚的な表示順序と一致させる。

## Processing Flow

```
1. Parse input
   └─ Extract fileKey/nodeId from URL

2. Get initial metadata
   └─ get_metadata(root_node_id)

3. Extract top-level frames
   ├─ Exclude hidden frames
   └─ Mark instance frames

4. Calculate complexity score (per frame)
   ├─ Children count × 2 (max 40 points)
   ├─ Depth × 5 (max 30 points)
   ├─ Text element count (max 20 points)
   └─ Height / 1000 (max 10 points)

5. BFS split processing
   ├─ Add root node to queue
   ├─ WHILE queue is not empty:
   │   ├─ Dequeue node
   │   ├─ Complexity >= threshold AND depth < max depth?
   │   │   ├─ YES: Add children to queue
   │   │   └─ NO: Retrieve with get_design_context
   │   └─ Cache results
   └─ All nodes processed

6. Context integration
   ├─ Maintain parent-child relationships (Y-sorted)
   ├─ Share design tokens
   └─ Calculate coordinate offsets

7. Generate Figma URLs (MANDATORY)
   │
   │  各セクションのFigma URLを自動生成し、structure.json と summary.md に含める
   │
   ├─ URL生成式:
   │   ```
   │   figma_url = "https://www.figma.com/design/{file_key}/?node-id={nodeId_with_dash}&m=dev"
   │   ```
   │   ※ nodeId の ":" を "-" に変換（例: "8:246" → "8-246"）
   │
   ├─ structure.json の children_sorted_by_y 各エントリに figma_url を追加
   │
   └─ summary.md にセクション別URLテーブルを出力:
       ```markdown
       ## Section URLs
       | # | Section | Figma URL |
       |---|---------|-----------|
       | 1 | Header  | https://www.figma.com/design/xxx/?node-id=8-182&m=dev |
       ```

8. Generate output
   └─ metadata.json, structure.json (Y-sorted + figma_url), nodes/*.json, summary.md
```

## Threshold Settings

### Recommended Values

| Parameter | Value | Description |
|-----------|-------|-------------|
| COMPLEXITY_THRESHOLD | 50 | Split required above this |
| MAX_CHILDREN | 10 | Max direct children guideline |
| MAX_DEPTH | 5 | Maximum recursion depth |
| MIN_SPLIT_HEIGHT | 500px | Don't split below this |

### Complexity Score Formula

```python
def calculate_complexity(node):
    score = 0
    score += min(len(node.children) * 2, 40)  # Children (40%)
    score += min(estimate_depth(node) * 5, 30)  # Max depth (30%)
    score += min(count_text_elements(node), 20)  # Text elements (20%)
    score += min(node.height / 1000, 10)  # Height (10%)
    return int(score)
```

### Page Type Adjustments

| Page Type | THRESHOLD | MAX_DEPTH |
|-----------|-----------|-----------|
| LP (long single page) | 40 | 6 |
| List page | 60 | 4 |
| Detail page | 50 | 5 |
| Form page | 45 | 4 |

## Split Algorithm

### Breadth-First Search (BFS) - Recommended

```python
def bfs_split(root_node_id, file_key):
    queue = [(root_node_id, 0, {})]
    results = {}

    while queue:
        node_id, depth, context = queue.pop(0)
        metadata = get_metadata(file_key, node_id)
        complexity = calculate_complexity(metadata)

        if complexity >= THRESHOLD and depth < MAX_DEPTH:
            for child in get_children(metadata):
                if child.hidden:
                    continue
                queue.append((child.id, depth + 1, {'parent_id': node_id}))
        else:
            result = get_design_context(file_key, node_id)
            results[node_id] = {'data': result, 'complexity': complexity}

    return results
```

### Depth-First Search (DFS) - Alternative

```python
def dfs_split(node_id, file_key, depth=0, context=None):
    if context is None:
        context = {}

    metadata = get_metadata(file_key, node_id)
    complexity = calculate_complexity(metadata)

    if complexity >= THRESHOLD and depth < MAX_DEPTH:
        results = {}
        for child in get_children(metadata):
            if child.hidden:
                continue
            results.update(dfs_split(child.id, file_key, depth + 1))
        return results
    else:
        return {node_id: get_design_context(file_key, node_id)}
```

## Error Handling

| Error | Response |
|-------|----------|
| Token limit exceeded | Automatically split further |
| API rate limit (429) | Exponential backoff retry (max 3 times) |
| Invalid nodeId | Skip and log, continue processing |
| Permission error | Output error message, terminate |
| Network error | 3 retries, then save partial results |

### Retry Logic

```python
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff

def fetch_with_retry(node_id, file_key):
    for attempt in range(MAX_RETRIES):
        try:
            return get_design_context(file_key, node_id)
        except TokenLimitError:
            return split_and_retry(node_id, file_key)
        except APIError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
            else:
                raise FetchFailedError(f"Failed: {node_id}")
```

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma/` | Cache storage |
| `.claude/rules/figma.md` | Figma rules |
| `.claude/rules/figma-workflow.md` | Figma workflow rules |

---

**Version**: 1.1.0
**Created**: 2026-01-30
**Updated**: 2026-02-26
**Author**: Auto-generated
**Status**: Approved

## Changelog

### v1.1.0 (2026-02-26)

**Feature: Figma URL自動生成 & Y座標ソート**

- Step 7 追加: Figma URL自動生成ステップ
- structure.json の各セクションに `figma_url` フィールド追加
- structure.json を `children_sorted_by_y` 形式に変更（Y座標昇順ソート）
- summary.md にセクション別URLテーブルを出力
- structure.json ルートに `file_key` フィールド追加
