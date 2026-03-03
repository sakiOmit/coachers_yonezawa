# CLI Pre-fetch Details

Detailed documentation for the figma-mcp-downloader CLI tool used in figma-prefetch.

## Overview

The CLI pre-fetch uses `figma-mcp-downloader` to retrieve Figma design data without consuming LLM tokens. This provides:

1. **Zero Token Consumption**: Bypasses LLM completely
2. **Full Data Retrieval**: No truncation or summarization
3. **Faster Execution**: Direct API calls
4. **Offline Caching**: Data persists locally

## Installation

### Prerequisites

- Node.js 18+
- Figma desktop app (must be running)

### Install Location

```
.claude/tools/figma-mcp-downloader/
├── package.json
├── dist/
│   └── cli.js
└── node_modules/
```

### Installation Steps

```bash
cd .claude/tools/figma-mcp-downloader
npm install
npm run build
```

## Usage

### Basic Command

```bash
node .claude/tools/figma-mcp-downloader/dist/cli.js get_design_context \
  --node-id={nodeId} \
  --force-code \
  --output .claude/cache/figma/{page-name}/
```

### Command Options

| Option | Required | Description |
|--------|----------|-------------|
| `get_design_context` | Yes | Command name |
| `--node-id` | Yes | Figma node ID (e.g., `1:2287` or `1-2287`) |
| `--force-code` | Recommended | Ensures full code output |
| `--output` | Yes | Output directory path |
| `--file-key` | No | Override file key (auto-detected from app) |

### PC/SP Dual Mode

```bash
# PC version
node .claude/tools/figma-mcp-downloader/dist/cli.js get_design_context \
  --node-id={pc_nodeId} \
  --force-code \
  --output .claude/cache/figma/{page-name}/pc/

# SP version
node .claude/tools/figma-mcp-downloader/dist/cli.js get_design_context \
  --node-id={sp_nodeId} \
  --force-code \
  --output .claude/cache/figma/{page-name}/sp/
```

## How It Works

### Connection Flow

```
Figma Desktop App
    │
    ├─ Local HTTP Server (localhost:3845)
    │
    ▼
figma-mcp-downloader CLI
    │
    ├─ Reads node from local server
    ├─ Processes design data
    │
    ▼
Output Files
    │
    ├─ design-context.json
    ├─ metadata.json (if applicable)
    └─ assets/ (downloaded images)
```

### Why Local Server?

- Figma's plugin sandbox allows local HTTP server
- Avoids API rate limits
- Faster than REST API
- Full data access (no pagination)

## Output Files

### design-context.json

```json
{
  "content": [
    {
      "type": "text",
      "text": "const img123 = \"https://...\";\n\nexport default function Group() {\n  return (\n    <div className=\"flex gap-[24px]\" data-node-id=\"1:2287\">\n      <div className=\"bg-[#f4f7f9] p-[32px]\" data-node-id=\"1:2288\">\n        ...\n      </div>\n    </div>\n  );\n}"
    }
  ],
  "assets": {
    "img123": "https://figma.com/api/mcp/asset/...",
    "img456": "https://figma.com/api/mcp/asset/..."
  }
}
```

### assets/ Directory

Downloaded images if `--download-assets` flag is used:

```
assets/
├── img123.png
├── img456.jpg
└── manifest.json
```

## Comparison with MCP

| Aspect | CLI Pre-fetch | MCP Direct |
|--------|--------------|------------|
| Token consumption | 0 | ~77,000+ tokens |
| Output truncation | None | Risk with large pages |
| Data completeness | Guaranteed | May be incomplete |
| Speed | Fast (~5s) | Slower (~15s) |
| Error visibility | Direct | Wrapped in MCP response |
| Offline capability | Cached | Requires connection |

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ECONNREFUSED` | Figma app not running | Start Figma desktop app |
| `ENOENT` | CLI not installed | Run `npm install` in tool directory |
| `Invalid node-id` | Malformed node ID | Use format `1:2287` or `1-2287` |
| `Permission denied` | Output directory issues | Check directory permissions |

### Error Recovery

```bash
# Check if Figma is running
curl -s http://localhost:3845/health

# If connection fails, start Figma app
open -a "Figma"  # macOS
# Wait 5 seconds for server startup

# Retry
node .claude/tools/figma-mcp-downloader/dist/cli.js ...
```

## Performance Optimization

### Parallel Fetching

For multiple pages:

```bash
# Sequential (safe)
for page in about contact services; do
  node cli.js get_design_context --node-id=${pages[$page]} --output .claude/cache/figma/$page/
done

# Parallel (faster, watch rate limits)
for page in about contact services; do
  node cli.js get_design_context --node-id=${pages[$page]} --output .claude/cache/figma/$page/ &
done
wait
```

### Recommended Batch Size

| Concurrent Fetches | Safety | Speed |
|-------------------|--------|-------|
| 1 (sequential) | High | Slow |
| 2-3 | Medium | Good |
| 4+ | Low (rate limit risk) | Fast |

## Integration with figma-prefetch

### Execution Flow

```python
def cli_prefetch(node_id, output_dir, options=None):
    """
    Execute CLI pre-fetch.

    Args:
        node_id: Figma node ID
        output_dir: Output directory path
        options: Additional CLI options

    Returns:
        tuple: (success, output_path, error_message)
    """
    cmd = [
        'node',
        '.claude/tools/figma-mcp-downloader/dist/cli.js',
        'get_design_context',
        f'--node-id={node_id}',
        '--force-code',
        f'--output={output_dir}'
    ]

    if options:
        cmd.extend(options)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            return True, output_dir, None
        else:
            return False, None, result.stderr

    except subprocess.TimeoutExpired:
        return False, None, "CLI timeout (60s exceeded)"
    except FileNotFoundError:
        return False, None, "CLI not found. Run: npm install in tools directory"
```

### Fallback to MCP

```python
def prefetch_with_fallback(node_id, output_dir):
    """
    Try CLI first, fallback to MCP if fails.
    """
    # Try CLI
    success, path, error = cli_prefetch(node_id, output_dir)

    if success:
        return path

    # Log CLI failure
    print(f"CLI failed: {error}")
    print("Falling back to MCP...")

    # Fallback to MCP
    response = mcp__figma__get_design_context(node_id)

    # Save MCP response to same location
    with open(f"{output_dir}/design-context.json", 'w') as f:
        json.dump(response, f)

    return output_dir
```

## Troubleshooting

### CLI Not Found

```bash
# Check installation
ls -la .claude/tools/figma-mcp-downloader/dist/

# If missing, reinstall
cd .claude/tools/figma-mcp-downloader
npm install
npm run build
```

### Figma App Connection Issues

```bash
# Check Figma local server
curl http://localhost:3845/health

# If fails:
# 1. Make sure Figma desktop app is open
# 2. Open any Figma file (server starts when file is open)
# 3. Wait 5 seconds
# 4. Try again
```

### Output File Empty

```bash
# Check node ID format
echo "Node ID should be: 1:2287 or 1-2287"

# Verify node exists
node cli.js get_metadata --node-id={nodeId}

# Check output directory permissions
ls -la .claude/cache/figma/
```

### Large File Issues

For very large design contexts:

```bash
# Increase Node.js memory
NODE_OPTIONS="--max-old-space-size=4096" node cli.js get_design_context ...

# Or split the retrieval
/figma-recursive-splitter {url}
```
