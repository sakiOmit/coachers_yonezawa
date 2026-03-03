# Cache Structure

Detailed documentation for the Figma prefetch cache structure and management.

## Directory Structure

### Standard Mode (PC only)

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

### Split Mode (with recursive-splitter)

```
.claude/cache/figma/{page-name}/
├── pc/
│   ├── metadata.json
│   ├── structure.json        # Y-sorted hierarchy
│   └── nodes/
│       ├── {nodeId}.json     # Raw JSX per section
│       └── ...
├── sp/
│   └── (same structure)
├── split-metadata.json       # Split execution info
├── prefetch-info.yaml
└── summary.md                # Human-readable summary
```

## File Specifications

### metadata.json

Contains the raw response from `get_metadata` MCP call.

```json
{
  "id": "1:2287",
  "name": "/about",
  "type": "FRAME",
  "absoluteBoundingBox": {
    "x": 0,
    "y": 0,
    "width": 1440,
    "height": 4500
  },
  "children": [
    {
      "id": "1:2288",
      "name": "Header",
      "type": "INSTANCE",
      "absoluteBoundingBox": { "x": 0, "y": 0, "width": 1440, "height": 112 }
    },
    // ...
  ]
}
```

### design-context.json

Contains the raw response from `get_design_context` MCP call (or CLI equivalent).

```json
{
  "content": [
    {
      "type": "text",
      "text": "const img123 = \"https://...\";\n\nexport default function Group() {\n  return (\n    <div className=\"flex gap-[24px]\" data-node-id=\"1:2287\">\n      ...\n    </div>\n  );\n}"
    }
  ],
  "assets": {
    "img123": "https://figma.com/api/mcp/asset/..."
  }
}
```

**Critical**: This file must contain the FULL raw JSX, not abstracted comments.

### text-extracted.json

Extracted text content for verification.

```json
{
  "extracted_at": "2026-01-31T12:00:00Z",
  "texts": [
    {
      "nodeId": "1:2290",
      "content": "会社概要",
      "element": "h1"
    },
    {
      "nodeId": "1:2295",
      "content": "私たちは...",
      "element": "p"
    }
  ],
  "total_count": 45
}
```

### prefetch-info.yaml

Prefetch metadata for cache management and downstream skill coordination.

```yaml
prefetch_timestamp: "2026-01-31T12:00:00"
pc_url: "https://figma.com/design/abc123/MyDesign?node-id=1-2287"
sp_url: "https://figma.com/design/abc123/MyDesign?node-id=1-5269"
file_key: "abc123"
pc_node_id: "1:2287"
sp_node_id: "1:5269"
page_height: 4500
top_level_frames: 6
strategy: "NORMAL"
cache_valid_until: "2026-02-01T12:00:00"

# Y-sorted section list (CRITICAL)
# recursive-splitter uses this order
sections_sorted_by_y:
  pc:
    - nodeId: "1:2288"
      name: "Header"
      y: 0
      type: "instance"
    - nodeId: "1:2300"
      name: "Breadcrumb"
      y: 112
    - nodeId: "1:2305"
      name: "Hero"
      y: 160
    - nodeId: "1:2400"
      name: "Content"
      y: 800
    - nodeId: "1:2500"
      name: "Footer"
      y: 4200
      type: "instance"
  sp:
    - nodeId: "1:5270"
      name: "Header SP"
      y: 0
    # ...

reusable_components:
  - c-link-button
  - c-page-header
  - c-breadcrumb
```

## Cache TTL (Time To Live)

### Default: 24 hours

```python
CACHE_TTL_HOURS = 24

def is_cache_valid(prefetch_info):
    if not prefetch_info:
        return False

    valid_until = datetime.fromisoformat(prefetch_info['cache_valid_until'])
    return datetime.now() < valid_until
```

### Cache Invalidation

| Condition | Action |
|-----------|--------|
| TTL expired (> 24h) | Auto-invalidate, re-fetch required |
| `--force` flag | Force invalidation |
| Design update detected | Manual invalidation recommended |
| Incomplete files | Auto-invalidate |

### Validation Checks

```python
def validate_cache(cache_dir):
    required_files = ['metadata.json', 'prefetch-info.yaml']

    for f in required_files:
        path = cache_dir / f
        if not path.exists():
            return False, f"Missing: {f}"
        if path.stat().st_size == 0:
            return False, f"Empty: {f}"

    # Check design-context.json if exists
    dc_path = cache_dir / 'design-context.json'
    if dc_path.exists():
        with open(dc_path) as f:
            data = json.load(f)
            if 'export default function' not in str(data):
                return False, "design-context.json may be incomplete"

    return True, "Valid"
```

## Cache Naming Convention

### Page Name Extraction

```python
def extract_page_name(figma_url, metadata):
    """
    Priority:
    1. Node name from metadata (cleaned)
    2. URL path segment
    3. Node ID as fallback
    """
    # From metadata
    if metadata and 'name' in metadata:
        name = metadata['name']
        # Remove leading slash if present
        name = name.lstrip('/')
        # Convert to kebab-case
        return to_kebab_case(name)

    # From URL
    # https://figma.com/design/abc/MyDesign?node-id=1-2
    # Extract: my-design

    # Fallback
    return node_id.replace(':', '-')
```

### Examples

| Node Name | Cache Directory |
|-----------|-----------------|
| `/about` | `about/` |
| `/Company Info` | `company-info/` |
| `Top Page - v2` | `top-page-v2/` |
| `1:2287` (no name) | `1-2287/` |

## Cache Size Management

### Recommended Limits

| Category | Limit | Action |
|----------|-------|--------|
| Single design-context.json | < 50MB | Split if exceeds |
| Total cache per page | < 100MB | Archive old versions |
| Total .claude/cache/figma/ | < 1GB | Periodic cleanup |

### Cleanup Script

```bash
#!/bin/bash
# Clean caches older than 7 days
find .claude/cache/figma -type d -mtime +7 -exec rm -rf {} +

# Keep only last 3 versions per page
# (implement version management if needed)
```

## Integration Points

### With figma-recursive-splitter

1. Read `prefetch-info.yaml` first
2. If `sections_sorted_by_y` exists, use it (skip get_metadata)
3. Split nodes into `nodes/` directory
4. Update `split-metadata.json`

### With figma-implement

1. Read `prefetch-info.yaml` for strategy
2. If `strategy: "NORMAL"`, read `design-context.json` directly
3. If `strategy: "SPLIT_*"`, iterate `nodes/` directory
4. Use `text-extracted.json` for verification

### With figma-visual-diff-runner

1. Use cache for reference images
2. Don't re-fetch unless explicit

## Troubleshooting

### Error: "Cache appears incomplete"

**Cause**: Files exist but are empty or corrupted.

**Solution**:
```bash
# Check file contents
ls -la .claude/cache/figma/{page}/
cat .claude/cache/figma/{page}/prefetch-info.yaml

# Force re-fetch
/figma-prefetch {url} --force
```

### Error: "Cache expired"

**Cause**: TTL (24h) exceeded.

**Solution**:
```bash
# Re-fetch (automatic)
/figma-prefetch {url}
```

### Error: "design-context.json too large"

**Cause**: Page is too complex for single fetch.

**Solution**:
```bash
# Use split strategy
/figma-recursive-splitter {url}
```
