---
name: figma-url-parser
description: "Parse Figma URL, --page slug, or --file-key + --node-id into unified file_key and node_id format for other Figma skills."
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Bash
context: fork
agent: general-purpose
---

# Figma URL Parser

## Overview

A utility skill that provides unified parsing of Figma identifiers from multiple input formats. Returns consistent file_key and node_id regardless of input method, enabling other Figma skills to accept flexible input formats.

### Key Features

- **URL Parsing**: Extract file_key and node_id from Figma URL
- **Page Slug Resolution**: Resolve --page slug to file_key + node_id via wordpress-pages.yaml
- **Direct Input**: Accept --file-key and --node-id directly
- **Format Normalization**: Convert URL node-id format (1-2) to API format (1:2)
- **Unified Output**: Consistent JSON response across all input methods

### Why This Skill?

Multiple Figma skills (figma-implement, figma-prefetch, figma-page-analyzer, etc.) need to parse Figma identifiers. This shared utility:

1. **DRY Principle**: Eliminates duplicate parsing logic across 5+ skills
2. **Consistency**: Ensures all skills handle inputs identically
3. **Maintainability**: Single point of update for URL format changes
4. **Flexibility**: New input methods can be added centrally

## Usage

```
/figma-url-parser {input}
```

### Input Patterns

```bash
# Pattern 1: Figma URL
/figma-url-parser https://www.figma.com/design/abc123/MyDesign?node-id=1-2

# Pattern 2: Page slug (requires wordpress-pages.yaml)
/figma-url-parser --page home

# Pattern 3: Direct specification
/figma-url-parser --file-key abc123 --node-id 1:2

# Pattern 4: PC/SP dual mode with URL
/figma-url-parser https://www.figma.com/design/abc123/MyDesign?node-id=1-2 \
  --sp https://www.figma.com/design/abc123/MyDesign?node-id=3-4

# Pattern 5: PC/SP dual mode with page slug
/figma-url-parser --page home
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| URL | Yes* | Figma page URL |
| --page | Yes* | Page slug (resolves via wordpress-pages.yaml) |
| --file-key | Yes* | Figma file key (with --node-id) |
| --node-id | Yes* | Node ID (with --file-key) |
| --sp | No | SP Figma URL (for PC/SP dual mode) |
| --config | No | Custom config path (default: config/wordpress-pages.yaml) |

*One of URL, --page, or --file-key + --node-id is required

## Output Format

### Standard Output (JSON)

```json
{
  "pc": {
    "file_key": "abc123XYZ",
    "node_id": "1:2",
    "url": "https://www.figma.com/design/abc123XYZ/MyDesign?node-id=1-2"
  },
  "sp": null,
  "page_slug": "home",
  "source": "url",
  "dual_mode": false
}
```

### PC/SP Dual Mode Output

```json
{
  "pc": {
    "file_key": "abc123XYZ",
    "node_id": "1:2",
    "url": "https://www.figma.com/design/abc123XYZ/MyDesign?node-id=1-2"
  },
  "sp": {
    "file_key": "abc123XYZ",
    "node_id": "3:4",
    "url": "https://www.figma.com/design/abc123XYZ/MyDesign?node-id=3-4"
  },
  "page_slug": "home",
  "source": "page",
  "dual_mode": true
}
```

### Source Values

| Source | Description |
|--------|-------------|
| `url` | Parsed from Figma URL |
| `page` | Resolved from wordpress-pages.yaml via --page |
| `direct` | Provided via --file-key + --node-id |

## Processing Flow

```
INPUT
  │
  ▼
┌───────────────────────────────────────┐
│  Step 1: Input Type Detection         │
│  ├─ URL pattern match?                │
│  ├─ --page flag present?              │
│  └─ --file-key + --node-id present?   │
└───────────────────────────────────────┘
  │
  ├─ URL ────────────────────────────────┐
  │                                      │
  │  ┌───────────────────────────────────▼───┐
  │  │  Step 2A: URL Parsing                 │
  │  │  ├─ Extract file_key from path        │
  │  │  ├─ Extract node-id from query        │
  │  │  ├─ Handle branch URLs (?branch-id=)  │
  │  │  └─ Normalize node_id (1-2 → 1:2)     │
  │  └───────────────────────────────────────┘
  │                                      │
  ├─ --page ─────────────────────────────┐
  │                                      │
  │  ┌───────────────────────────────────▼───┐
  │  │  Step 2B: Page Slug Resolution        │
  │  │  ├─ Read config/wordpress-pages.yaml  │
  │  │  ├─ Find page by slug                 │
  │  │  ├─ Extract global file_key           │
  │  │  ├─ Extract pc.node_id                │
  │  │  ├─ Extract sp.node_id (if exists)    │
  │  │  └─ Normalize node_ids                │
  │  └───────────────────────────────────────┘
  │                                      │
  ├─ --file-key + --node-id ─────────────┐
  │                                      │
  │  ┌───────────────────────────────────▼───┐
  │  │  Step 2C: Direct Input                │
  │  │  ├─ Validate file_key format          │
  │  │  ├─ Validate node_id format           │
  │  │  └─ Normalize node_id if needed       │
  │  └───────────────────────────────────────┘
  │
  ▼
┌───────────────────────────────────────┐
│  Step 3: SP URL Processing (if --sp)  │
│  ├─ Parse SP URL (same as Step 2A)    │
│  └─ Set dual_mode: true               │
└───────────────────────────────────────┘
  │
  ▼
┌───────────────────────────────────────┐
│  Step 4: URL Generation               │
│  └─ Generate canonical URLs from IDs  │
└───────────────────────────────────────┘
  │
  ▼
┌───────────────────────────────────────┐
│  Step 5: Output Generation            │
│  └─ Format JSON response              │
└───────────────────────────────────────┘
  │
  ▼
OUTPUT (JSON)
```

## URL Parsing Algorithm

### Supported URL Formats

```
# Standard design URL
https://www.figma.com/design/{file_key}/{name}?node-id={node_id}

# File URL (legacy)
https://www.figma.com/file/{file_key}/{name}?node-id={node_id}

# Branch URL
https://www.figma.com/design/{file_key}/{name}?node-id={node_id}&branch-id={branch_id}

# Prototype URL
https://www.figma.com/proto/{file_key}/{name}?node-id={node_id}
```

### Regex Patterns

```javascript
// File key extraction
const FILE_KEY_PATTERN = /figma\.com\/(design|file|proto)\/([a-zA-Z0-9]+)/;

// Node ID extraction
const NODE_ID_PATTERN = /node-id=([0-9]+-[0-9]+)/;

// Branch ID extraction (optional)
const BRANCH_ID_PATTERN = /branch-id=([a-zA-Z0-9]+)/;
```

### Node ID Normalization

```javascript
function normalizeNodeId(input) {
  // URL format: 1-2 → API format: 1:2
  if (input.includes('-')) {
    return input.replace(/-/g, ':');
  }
  return input;
}

function denormalizeNodeId(input) {
  // API format: 1:2 → URL format: 1-2
  if (input.includes(':')) {
    return input.replace(/:/g, '-');
  }
  return input;
}
```

## wordpress-pages.yaml Schema

### Expected Location

```
config/wordpress-pages.yaml
```

### Schema

```yaml
# Global Figma settings
figma:
  file_key: "abcd1234XYZ"

# Page definitions
pages:
  - slug: "home"
    title: "トップページ"
    figma:
      pc:
        node_id: "1-2287"
      sp:
        node_id: "1-2288"
    status: pending

  - slug: "about"
    title: "会社概要"
    figma:
      pc:
        node_id: "2-100"
      sp:
        node_id: "2-101"
    status: completed
```

### Resolution Logic

```python
def resolve_page_slug(slug, config_path="config/wordpress-pages.yaml"):
    config = read_yaml(config_path)

    global_file_key = config['figma']['file_key']

    for page in config['pages']:
        if page['slug'] == slug:
            return {
                'pc': {
                    'file_key': global_file_key,
                    'node_id': normalize_node_id(page['figma']['pc']['node_id'])
                },
                'sp': {
                    'file_key': global_file_key,
                    'node_id': normalize_node_id(page['figma']['sp']['node_id'])
                } if 'sp' in page['figma'] else None,
                'page_slug': slug,
                'source': 'page',
                'dual_mode': 'sp' in page['figma']
            }

    raise PageNotFoundError(f"Page '{slug}' not found in config")
```

## Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Invalid URL format | Regex mismatch | Error with URL format examples |
| Missing node-id in URL | Query param missing | Error with correct format hint |
| Page slug not found | Not in config | Error listing available pages |
| Config file missing | File not found | Error with config path hint |
| Invalid node_id format | Validation fail | Error with format examples |
| Missing required params | Arg parsing | Error with usage examples |

### Error Response Format

```json
{
  "error": true,
  "code": "INVALID_URL_FORMAT",
  "message": "Could not parse Figma URL. Expected format: https://www.figma.com/design/{file_key}/{name}?node-id={node_id}",
  "input": "https://invalid-url.com",
  "suggestions": [
    "Check that the URL is a valid Figma design URL",
    "Ensure the URL contains a node-id parameter"
  ]
}
```

## Integration with Other Skills

### Recommended Usage Pattern

Other Figma skills should call this parser at the start of their workflow:

```python
# In figma-implement, figma-prefetch, etc.
def parse_input(args):
    # Delegate to figma-url-parser
    result = invoke_skill('figma-url-parser', args)

    if result.get('error'):
        raise ParseError(result['message'])

    return result
```

### Skills That Should Use This Parser

| Skill | Current Parsing | Migration |
|-------|-----------------|-----------|
| figma-implement | URL only | Add --page support |
| figma-prefetch | URL only | Add --page support |
| figma-page-analyzer | URL or --file-key + --node-id | Add --page support |
| figma-recursive-splitter | URL or --file-key + --node-id | Add --page support |
| figma-section-splitter | URL or --file-key + --node-id | Add --page support |

## Examples

### Example 1: Parse URL

```bash
/figma-url-parser https://www.figma.com/design/abc123/MyDesign?node-id=1-2
```

Output:
```json
{
  "pc": {
    "file_key": "abc123",
    "node_id": "1:2",
    "url": "https://www.figma.com/design/abc123/MyDesign?node-id=1-2"
  },
  "sp": null,
  "page_slug": null,
  "source": "url",
  "dual_mode": false
}
```

### Example 2: Resolve Page Slug

```bash
/figma-url-parser --page home
```

Output (with wordpress-pages.yaml configured):
```json
{
  "pc": {
    "file_key": "abcd1234XYZ",
    "node_id": "1:2287",
    "url": "https://www.figma.com/design/abcd1234XYZ/?node-id=1-2287"
  },
  "sp": {
    "file_key": "abcd1234XYZ",
    "node_id": "1:2288",
    "url": "https://www.figma.com/design/abcd1234XYZ/?node-id=1-2288"
  },
  "page_slug": "home",
  "source": "page",
  "dual_mode": true
}
```

### Example 3: Direct Input

```bash
/figma-url-parser --file-key abc123 --node-id 1:2
```

Output:
```json
{
  "pc": {
    "file_key": "abc123",
    "node_id": "1:2",
    "url": "https://www.figma.com/design/abc123/?node-id=1-2"
  },
  "sp": null,
  "page_slug": null,
  "source": "direct",
  "dual_mode": false
}
```

### Example 4: PC/SP Dual Mode with URLs

```bash
/figma-url-parser https://www.figma.com/design/abc123/Design?node-id=1-2 \
  --sp https://www.figma.com/design/abc123/Design?node-id=3-4
```

Output:
```json
{
  "pc": {
    "file_key": "abc123",
    "node_id": "1:2",
    "url": "https://www.figma.com/design/abc123/Design?node-id=1-2"
  },
  "sp": {
    "file_key": "abc123",
    "node_id": "3:4",
    "url": "https://www.figma.com/design/abc123/Design?node-id=3-4"
  },
  "page_slug": null,
  "source": "url",
  "dual_mode": true
}
```

## Related Files

| File | Purpose |
|------|---------|
| `config/wordpress-pages.yaml` | Page definitions with Figma node IDs |
| `.claude/skills/figma-implement/SKILL.md` | Primary consumer skill |
| `.claude/skills/figma-prefetch/SKILL.md` | Primary consumer skill |
| `.shogun/reports/task-file-review-skills.md` | Integration analysis |

## Changelog

### v1.0.0 (2026-01-31)
- Initial release
- URL parsing with file_key and node_id extraction
- Page slug resolution via wordpress-pages.yaml
- Direct --file-key + --node-id input
- PC/SP dual mode support
- Node ID format normalization

---

**Version**: 1.0.0
**Created**: 2026-01-31
**Author**: ashigaru1
