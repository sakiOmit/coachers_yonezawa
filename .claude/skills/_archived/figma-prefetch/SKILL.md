---
name: figma-prefetch
description: "Pre-fetch Figma design data before implementation. Use when user says 'prepare Figma', 'prefetch design', 'check Figma cache', or before running /figma-implement. Handles cache validation (24h TTL), CLI download, and strategy recommendation."
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - mcp__figma__get_metadata
context: fork
agent: general-purpose
---

# Figma Prefetch

## Overview

A preprocessing skill that prepares Figma design data before implementation. Validates cache, executes CLI pre-fetch, checks component catalog, and recommends the optimal retrieval strategy.

### Key Features

- **URL Parsing**: Extract fileKey and nodeId from Figma URL
- **Cache Validation**: Check existing cache with 24h TTL
- **CLI Pre-fetch**: Execute figma-mcp-downloader for token-free data retrieval
- **Scale Check**: Quick page size estimation
- **Catalog Check**: Verify component-catalog.yaml for reusable components
- **Strategy Recommendation**: Suggest normal/split retrieval based on page scale
- **Next Step Guidance**: Recommend appropriate skill for next phase

### Why This Skill?

Separating prefetch from implementation provides:

1. **Token Efficiency**: CLI pre-fetch consumes zero LLM tokens
2. **Clear Responsibility**: prefetch = preparation, implement = orchestration
3. **Reusability**: Cache can be reused across multiple implementation attempts
4. **Fail-fast**: Detect issues before expensive implementation begins

## Usage

```
/figma-prefetch {pc_url} [--sp {sp_url}] [options]
```

### Options

```
/figma-prefetch {pc_url} [options]

Options:
  --sp {sp_url}     SP version Figma URL (for PC/SP dual implementation)
  --force           Force re-fetch even if cache exists
  --skip-cli        Skip CLI pre-fetch (use MCP only)
  --dry-run         Show plan without execution
  --type {page|cpt} Page type: page (default) or cpt (custom post type)
  --post-type {name} Custom post type name (required when --type cpt)
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| pc_url | Yes | Figma page URL for PC design |
| --sp | No | Figma page URL for SP design |
| --force | No | Force re-fetch ignoring cache |
| --skip-cli | No | Skip CLI download, use MCP directly |
| --dry-run | No | Show plan only, no execution |
| --type | No | Page type: page (default) or cpt |
| --post-type | No | Custom post type name (required when --type cpt) |

## Processing Flow

```
/figma-prefetch {url}
        │
        ▼
┌───────────────────────────────────────┐
│  Step 1: URL Parsing                  │
│  ├─ Extract fileKey from URL          │
│  ├─ Extract nodeId from URL           │
│  └─ Handle branch URLs                │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 2: Cache Validation             │
│  ├─ Check .claude/cache/figma/{page}/ │
│  ├─ Validate TTL (24h)                │
│  └─ Report cache status               │
└───────────────────────────────────────┘
        │
        ├─ Cache valid → Skip to Step 6
        │
        ▼
┌───────────────────────────────────────┐
│  Step 3: Quick Scale Check            │
│  ├─ get_metadata for structure        │
│  ├─ Extract page height               │
│  ├─ Count top-level frames            │
│  └─ **Extract Y-sorted sections**     │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 4: CLI Pre-fetch                │
│  ├─ Check Figma app running           │
│  ├─ Execute figma-mcp-downloader      │
│  ├─ Save to cache directory           │
│  └─ Validate output                   │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 5: Component Catalog Check      │
│  ├─ Read component-catalog.yaml       │
│  └─ List reusable components          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 6: Strategy Decision            │
│  ├─ Evaluate page scale               │
│  ├─ Determine strategy (normal/split) │
│  └─ Recommend next skill              │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 7: Task File Generation         │
│  ├─ Generate task_id                  │
│  ├─ Collect page info (slug, URLs)    │
│  ├─ Collect scale info                │
│  ├─ List reusable components          │
│  └─ Write to .shogun/queue/tasks/     │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 8: wordpress-pages.yaml Update  │
│  ├─ Check if config file exists       │
│  ├─ Create if not exists              │
│  ├─ Find or create page entry         │
│  ├─ Update fields:                    │
│  │   ├─ pc_node_id                    │
│  │   ├─ sp_node_id (if --sp)          │
│  │   ├─ type (page or cpt)            │
│  │   ├─ post_type (if --type cpt)     │
│  │   ├─ height                         │
│  │   └─ strategy                       │
│  └─ Write back to YAML                │
└───────────────────────────────────────┘
        │
        ▼
       OUTPUT
```

## Y座標ソート抽出ロジック (Step 3)

get_metadata のレスポンスからセクション一覧を Y 座標順で抽出する。

### 抽出手順

```python
def extract_sections_sorted_by_y(metadata):
    """Extract top-level frames sorted by Y coordinate"""
    sections = []

    for child in metadata.get('children', []):
        # Skip hidden frames
        if child.get('visible') == False:
            continue

        bbox = child.get('absoluteBoundingBox', {})
        sections.append({
            'nodeId': child.get('id'),
            'name': child.get('name'),
            'y': bbox.get('y', 0),
            'type': 'instance' if child.get('type') == 'INSTANCE' else 'frame'
        })

    # CRITICAL: Sort by Y coordinate (top to bottom)
    return sorted(sections, key=lambda s: s['y'])
```

### 重要性

Figma の node 順序（レイヤーパネル順）は視覚的表示順と異なる場合がある。
prefetch 時点で Y ソートしておくことで、後続の recursive-splitter が正しい順序で処理できる。

## Strategy Decision Logic

### Scale Thresholds

| Metric | Small | Medium | Large |
|--------|-------|--------|-------|
| Height | < 3,000px | 3,000-5,000px | > 5,000px |
| Frames | < 5 | 5-8 | > 8 |

### Strategy Matrix

| Cache | Scale | Strategy | Next Step |
|-------|-------|----------|-----------|
| Valid (24h) | Any | Use cache | `/figma-implement` |
| Invalid | Small | CLI pre-fetch | `/figma-implement` |
| Invalid | Medium | CLI pre-fetch | `/figma-implement` or `/figma-recursive-splitter` |
| Invalid | Large | Recommend split | `/figma-recursive-splitter` or `/figma-section-splitter` |

### Decision Output

```
Cache Status: VALID (2h old) / INVALID (expired) / NOT_FOUND
Page Scale: SMALL / MEDIUM / LARGE
Height: 4,500px
Top-level Frames: 6
Strategy: NORMAL / SPLIT_RECOMMENDED / SPLIT_REQUIRED

Recommended Next Step:
  /figma-implement https://... (for NORMAL)
  /figma-recursive-splitter https://... (for SPLIT)
```

## Task File Generation (Step 7)

Generates a task file for progress tracking and Shogun system integration.

### Task File Structure

```yaml
task_id: figma_implement_{slug}_{timestamp}
page:
  name: "Page Title"
  slug: "page-slug"
  pc_url: "https://figma.com/design/..."
  sp_url: "https://figma.com/design/..."  # if --sp provided
  pc_node_id: "1:2287"
  sp_node_id: "1:2288"  # if --sp provided
scale:
  height: 4500
  frames: 6
  strategy: "NORMAL"  # NORMAL | SPLIT_RECOMMENDED | SPLIT_REQUIRED
reusable_components:
  - c-link-button
  - c-page-header
  - c-breadcrumb
status: "pending"
created_at: "2026-01-31T14:30:00"
```

### Slug Resolution Logic

| Input Method | Slug Source |
|--------------|-------------|
| `--page {slug}` option | Use the provided slug directly |
| URL + wordpress-pages.yaml | Match node_id in config, use matching page's slug |
| URL only (no match) | Extract from URL path (last segment before query) |

**Resolution Priority:**
1. `--page` option (explicit)
2. wordpress-pages.yaml lookup by node_id
3. URL path extraction (fallback)

### Output Path

```
.shogun/queue/tasks/page-{slug}.yaml
```

If slug cannot be determined, use node_id as fallback:
```
.shogun/queue/tasks/page-{node_id}.yaml
```

### Benefits

- **Progress Tracking**: Enables Shogun/Karo to monitor page implementation status
- **Context Preservation**: Survives compaction (context reset)
- **Team Coordination**: Multiple workers can see pending tasks
- **Resume Capability**: Task file persists strategy and component info

## wordpress-pages.yaml Update (Step 8)

Automatically updates the project's page configuration file with Figma metadata.

### Update Logic

```
1. Check if config/wordpress-pages.yaml exists
   └─ If not exists → Create with initial structure

2. Find existing page entry by slug
   └─ If not found → Create new entry

3. Update fields:
   ├─ figma.pc.node_id (always)
   ├─ figma.sp.node_id (if --sp provided)
   ├─ type: "page" | "cpt" (based on --type, default: "page")
   ├─ post_type: {name} (if --type cpt)
   ├─ scale.height (from metadata)
   └─ scale.strategy (from Step 6 decision)

4. Write back to YAML (preserve other fields)
```

### Field Definitions

| Field | Type | Description | When Set |
|-------|------|-------------|----------|
| `type` | string | Page type: "page" or "cpt" | Always (default: "page") |
| `post_type` | string | Custom post type name | Only when `type: "cpt"` |
| `figma.pc.node_id` | string | PC version node ID | Always |
| `figma.sp.node_id` | string | SP version node ID | When `--sp` provided |
| `scale.height` | number | Page height in px | Always |
| `scale.strategy` | string | "NORMAL" / "SPLIT_RECOMMENDED" / "SPLIT_REQUIRED" | Always |

### Examples

#### Fixed Page (default)
```yaml
- slug: about
  type: page
  figma:
    pc:
      node_id: "1-2287"
    sp:
      node_id: "1-5269"
  scale:
    height: 4500
    strategy: "NORMAL"
```

#### Custom Post Type
```yaml
- slug: interview
  type: cpt
  post_type: interview
  figma:
    pc:
      node_id: "1-671"
    sp:
      node_id: "1-5078"
  scale:
    height: 3200
    strategy: "NORMAL"
```

### Integration with npm Scripts

The `type` field determines whether the page is processed by npm page generation scripts:

- `type: "page"` → Included in `npm run wp:create-templates`
- `type: "cpt"` → Skipped (custom post types managed separately)

This prevents accidental template file generation for CPT archive/single pages.

## CLI Pre-fetch

### Command

```bash
node .claude/tools/figma-mcp-downloader/dist/cli.js get_design_context \
  --node-id={nodeId} \
  --force-code \
  --output .claude/cache/figma/{page-name}/
```

### PC/SP Dual Mode

```bash
# PC
node .claude/tools/figma-mcp-downloader/dist/cli.js get_design_context \
  --node-id={pc_nodeId} \
  --force-code \
  --output .claude/cache/figma/{page-name}/pc/

# SP
node .claude/tools/figma-mcp-downloader/dist/cli.js get_design_context \
  --node-id={sp_nodeId} \
  --force-code \
  --output .claude/cache/figma/{page-name}/sp/
```

### Prerequisites

- Figma desktop app must be running (for local server access)
- figma-mcp-downloader installed at `.claude/tools/figma-mcp-downloader/`

### Benefits vs MCP

| Aspect | CLI Pre-fetch | MCP Direct |
|--------|--------------|------------|
| Token consumption | Zero | ~77,000+ tokens |
| Output truncation | None (forceCode) | Risk of truncation |
| Data completeness | Guaranteed | AI may omit |
| Speed | Faster | Slower |

## Cache Structure

### Standard Mode

```
.claude/cache/figma/{page-name}/
├── metadata.json          # get_metadata result
├── design-context.json    # get_design_context result
├── text-extracted.json    # Extracted text list
└── prefetch-info.yaml     # Prefetch metadata
```

### PC/SP Dual Mode

```
.claude/cache/figma/{page-name}/
├── pc/
│   ├── metadata.json
│   ├── design-context.json
│   └── text-extracted.json
├── sp/
│   ├── metadata.json
│   ├── design-context.json
│   └── text-extracted.json
├── pc-sp-diff.json        # PC/SP difference info
└── prefetch-info.yaml
```

### prefetch-info.yaml

```yaml
prefetch_timestamp: "2026-01-31T12:00:00"
pc_url: "https://figma.com/design/..."
sp_url: "https://figma.com/design/..." # if --sp provided
file_key: "abc123"
pc_node_id: "1:2"
sp_node_id: "3:4" # if --sp provided
page_height: 4500
top_level_frames: 6
strategy: "NORMAL"
cache_valid_until: "2026-02-01T12:00:00"

# Y座標ソート済みセクション一覧 (CRITICAL)
# recursive-splitter はこの順序を使用すること
sections_sorted_by_y:
  pc:
    - nodeId: "1:675"
      name: "Header"
      y: 0
      type: "instance"  # optional: instance | frame
    - nodeId: "1:691"
      name: "Breadcrumb"
      y: 112
    - nodeId: "1:676"
      name: "Hero Text"
      y: 196
    - nodeId: "1:701"
      name: "Content Body"
      y: 1200
  sp:
    - nodeId: "3:100"
      name: "Header SP"
      y: 0
    # ...

reusable_components:
  - c-link-button
  - c-page-header
  - c-breadcrumb
```

**重要**: `sections_sorted_by_y` は get_metadata の `absoluteBoundingBox.y` から抽出し、昇順でソートすること。
後続の recursive-splitter はこの順序を使用して分割処理を行う。

## Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Invalid URL | Regex mismatch | Output error with URL format hint |
| Figma app not running | CLI connection fail | Suggest starting Figma app |
| CLI not installed | File not found | Output installation instructions |
| get_metadata timeout | MCP timeout | 3 retries, then error |
| Cache directory permission | Write fail | Output permission fix command |
| Large page without split | Height > 8,000px | Force split recommendation |

## Output Examples

### Case 1: Cache Valid

```
╔══════════════════════════════════════════════════════════════╗
║  Figma Prefetch Result                                       ║
╠══════════════════════════════════════════════════════════════╣
║  URL: https://figma.com/design/abc123/MyDesign?node-id=1-2   ║
║  Page: About Page                                            ║
╠══════════════════════════════════════════════════════════════╣
║  Cache Status: ✅ VALID (2h ago)                             ║
║  Cache Path: .claude/cache/figma/about/                      ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ Ready for implementation                                 ║
║                                                              ║
║  Next Step:                                                  ║
║    /figma-implement https://figma.com/... --no-screenshot    ║
╚══════════════════════════════════════════════════════════════╝
```

### Case 2: Small Page - CLI Pre-fetch

```
╔══════════════════════════════════════════════════════════════╗
║  Figma Prefetch Result                                       ║
╠══════════════════════════════════════════════════════════════╣
║  URL: https://figma.com/design/abc123/MyDesign?node-id=1-2   ║
║  Page: Contact Page                                          ║
╠══════════════════════════════════════════════════════════════╣
║  Cache Status: ❌ NOT FOUND                                  ║
║  Page Scale: SMALL (2,800px, 4 frames)                       ║
╠══════════════════════════════════════════════════════════════╣
║  ⏳ Executing CLI pre-fetch...                               ║
║  ✅ Pre-fetch complete                                       ║
║  Cache Path: .claude/cache/figma/contact/                    ║
╠══════════════════════════════════════════════════════════════╣
║  Reusable Components Found:                                  ║
║    - c-link-button (Button/Primary)                          ║
║    - c-page-header (existing)                                ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ Ready for implementation                                 ║
║                                                              ║
║  Next Step:                                                  ║
║    /figma-implement https://figma.com/... --no-screenshot    ║
╚══════════════════════════════════════════════════════════════╝
```

**Generated Task File:**
```yaml
# .shogun/queue/tasks/page-contact.yaml
task_id: figma_implement_contact_20260131T143000
page:
  name: "Contact Page"
  slug: "contact"
  pc_url: "https://figma.com/design/abc123/MyDesign?node-id=1-2"
  sp_url: null
  pc_node_id: "1:2"
  sp_node_id: null
scale:
  height: 2800
  frames: 4
  strategy: "NORMAL"
reusable_components:
  - c-link-button
  - c-page-header
status: "pending"
created_at: "2026-01-31T14:30:00"
```

### Case 3: Large Page - Split Recommended

```
╔══════════════════════════════════════════════════════════════╗
║  Figma Prefetch Result                                       ║
╠══════════════════════════════════════════════════════════════╣
║  URL: https://figma.com/design/abc123/MyDesign?node-id=1-2   ║
║  Page: Top Page                                              ║
╠══════════════════════════════════════════════════════════════╣
║  Cache Status: ❌ EXPIRED (26h ago)                          ║
║  Page Scale: LARGE (12,500px, 12 frames)                     ║
╠══════════════════════════════════════════════════════════════╣
║  ⚠️  SPLIT RECOMMENDED                                       ║
║                                                              ║
║  Reason: Page height 12,500px exceeds 5,000px threshold.     ║
║          Direct retrieval may cause token limit issues.      ║
╠══════════════════════════════════════════════════════════════╣
║  Next Step Options:                                          ║
║                                                              ║
║  Option A (Recommended for single worker):                   ║
║    /figma-recursive-splitter https://figma.com/...           ║
║                                                              ║
║  Option B (Recommended for parallel workers):                ║
║    /figma-section-splitter https://figma.com/...             ║
╚══════════════════════════════════════════════════════════════╝
```

## When to Use

| Situation | Recommendation |
|-----------|---------------|
| Before any Figma implementation | ✅ Always use |
| Resuming interrupted work | ✅ Check cache validity |
| After Figma design update | ✅ Use with --force |
| Quick implementation check | ✅ Use with --dry-run |

## Do NOT Use

Use alternative skills in these cases:

| Situation | Alternative |
|-----------|-------------|
| Need detailed page analysis | `/figma-page-analyzer` |
| Already know page is large | `/figma-recursive-splitter` |
| Parallel worker assignment | `/figma-section-splitter` |
| Already have valid cache | `/figma-implement` directly |

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `figma-page-analyzer` | Detailed scale analysis (prefetch calls this internally for large pages) |
| `figma-recursive-splitter` | BFS split retrieval (recommended for large pages) |
| `figma-section-splitter` | Parallel worker split (recommended for team work) |
| `figma-implement` | Implementation orchestrator (next step after prefetch) |

## Examples

### Example 1: Basic Prefetch (PC only)

User says: "Prepare the about page for implementation"

```bash
/figma-prefetch https://figma.com/design/abc123/MyDesign?node-id=1-2287
```

Actions:
1. Parse URL → fileKey: abc123, nodeId: 1:2287
2. Check cache → Not found
3. get_metadata → Height: 3,200px, 5 frames
4. CLI pre-fetch → Save to .claude/cache/figma/about/
5. Component check → 2 reusable components
6. Strategy decision → NORMAL
7. Generate task file

Result: Cache ready, recommended `/figma-implement`

### Example 2: PC/SP Dual Mode

User says: "Prepare both PC and SP designs"

```bash
/figma-prefetch https://figma.com/.../node-id=1-2287 --sp https://figma.com/.../node-id=1-5269
```

Actions:
1. Parse both URLs
2. CLI pre-fetch for PC → .claude/cache/figma/about/pc/
3. CLI pre-fetch for SP → .claude/cache/figma/about/sp/
4. Extract Y-sorted sections for both
5. Generate unified task file

Result:
```yaml
# prefetch-info.yaml
sections_sorted_by_y:
  pc:
    - nodeId: "1:2288"
      name: "Header"
      y: 0
  sp:
    - nodeId: "1:5270"
      name: "Header SP"
      y: 0
```

### Example 3: Force Re-fetch

User says: "Design was updated, refresh the cache"

```bash
/figma-prefetch https://... --force
```

Actions:
1. Ignore existing cache (even if valid)
2. Re-fetch from Figma
3. Overwrite cache files
4. Update prefetch-info.yaml timestamp

## Troubleshooting

### Error: "Figma app not running"

**Cause**: CLI pre-fetch requires Figma desktop app with local server.

**Solution**:
```bash
# 1. Start Figma desktop app
# 2. Open any file in Figma
# 3. Wait 5 seconds for server startup
# 4. Retry prefetch
```

### Error: "CLI not installed"

**Cause**: figma-mcp-downloader not found.

**Solution**:
```bash
cd .claude/tools/figma-mcp-downloader
npm install
npm run build
```

### Error: "Strategy says SPLIT but I want NORMAL"

**Cause**: Page exceeds thresholds but you know it's manageable.

**Solution**:
```bash
# Override strategy (at your own risk)
/figma-implement {url} --force-normal
```

### Error: "Cache exists but seems corrupted"

**Cause**: Incomplete previous fetch or disk issue.

**Solution**:
```bash
# Force re-fetch
/figma-prefetch {url} --force

# Or manually delete cache
rm -rf .claude/cache/figma/{page}/
```

## References

For detailed technical documentation, see:

| File | Content |
|------|---------|
| [references/cache-structure.md](references/cache-structure.md) | Cache directory structure, file formats, TTL management |
| [references/strategy-decision.md](references/strategy-decision.md) | Strategy decision algorithm, thresholds, token estimation |
| [references/cli-prefetch-details.md](references/cli-prefetch-details.md) | CLI tool usage, troubleshooting, MCP comparison |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma/` | Cache storage directory |
| `.claude/tools/figma-mcp-downloader/` | CLI tool location |
| `.claude/data/component-catalog.yaml` | Component catalog |
| `.claude/rules/figma-workflow.md` | Figma workflow rules |
| `.claude/skills/INDEX.md` | Skill usage index |
| `.shogun/queue/tasks/page-{slug}.yaml` | **Task file output** (Step 7) |
| `config/wordpress-pages.yaml` | Page definitions (for slug resolution) |

---

**Version**: 1.1.0
**Created**: 2026-01-31
**Updated**: 2026-01-31
**Author**: ashigaru2

## Changelog

### v1.1.0 (2026-01-31)

**Features:**
- Y座標ソート済みセクション情報を `sections_sorted_by_y` として出力
- recursive-splitter がこの情報を優先使用し、再計算をスキップ

**Reason:**
- prefetch → recursive-splitter の連携時に Y 座標情報が失われていた問題を修正
- セクション順序逆転問題の根本対策
