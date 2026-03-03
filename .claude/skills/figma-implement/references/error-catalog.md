# Error Catalog

Comprehensive error handling reference for figma-implement skill.

## Error Categories

### 1. Cache Errors

| Error | Code | Cause | Solution |
|-------|------|-------|----------|
| Cache not found | CACHE_001 | `/figma-prefetch` not run | Run `/figma-prefetch {url}` first |
| Cache expired | CACHE_002 | Cache older than 24h | Run `/figma-prefetch {url} --force` |
| Cache corrupted | CACHE_003 | Invalid JSON in cache files | Delete cache and re-fetch |
| Cache incomplete | CACHE_004 | Missing required files | Re-run `/figma-prefetch` |

### 2. raw_jsx Validation Errors

| Error | Code | Cause | Solution |
|-------|------|-------|----------|
| raw_jsx empty | JSX_001 | Node not fetched | Re-fetch with `get_design_context` |
| raw_jsx too short | JSX_002 | Content abstracted/summarized | Re-fetch, save full response |
| Missing export | JSX_003 | Not valid JSX code | Verify MCP response format |
| Missing className | JSX_004 | No Tailwind classes | Check Figma design has styles |
| Contains abstraction | JSX_005 | Comments instead of code | Re-fetch, don't summarize |

### 3. Figma API Errors

| Error | Code | Cause | Solution |
|-------|------|-------|----------|
| Token limit exceeded | API_001 | Page too large | Use `/figma-recursive-splitter` |
| Rate limit (429) | API_002 | Too many requests | Wait and retry with backoff |
| Auth failed (401) | API_003 | Invalid/expired token | Re-authenticate Figma |
| Permission denied (403) | API_004 | No access to file | Check file sharing settings |
| Node not found (404) | API_005 | Invalid nodeId | Verify URL is correct |
| Server error (5xx) | API_006 | Figma service issue | Retry later |

### 4. Build Errors

| Error | Code | Cause | Solution |
|-------|------|-------|----------|
| SCSS syntax error | BUILD_001 | Invalid SCSS | Check lint output, fix syntax |
| Missing import | BUILD_002 | File not included | Add import to entry file |
| Missing variable | BUILD_003 | Undefined SCSS variable | Add to _variables.scss |
| PHP syntax error | BUILD_004 | Invalid PHP | Check PHP lint output |
| Missing template | BUILD_005 | Template file not found | Create required template |

### 5. Validation Errors

| Error | Code | Cause | Solution |
|-------|------|-------|----------|
| Visual diff failed | VAL_001 | Implementation differs from Figma | Review diff image, fix styles |
| Max iterations reached | VAL_002 | 5 fix attempts failed | Manual review required |
| Playwright connection | VAL_003 | Browser not available | Install/restart Playwright |
| Screenshot failed | VAL_004 | Element not found | Check selector, wait for load |

## Error Response Format

All errors follow this format:

```yaml
error:
  code: "CACHE_001"
  message: "Cache not found"
  details: |
    Expected cache at: .claude/cache/figma/about/
    No files found in this directory.
  suggestion: |
    Run the following command first:
    /figma-prefetch https://figma.com/design/...
  recoverable: true
  retry_command: "/figma-prefetch {url}"
```

## Automatic Recovery

### Retry Logic

```python
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds

def handle_error(error):
    if error.recoverable and error.retries < MAX_RETRIES:
        sleep(RETRY_DELAYS[error.retries])
        return retry(error.operation)
    else:
        return prompt_user(error)
```

### Recoverable vs Non-Recoverable

| Recoverable | Non-Recoverable |
|-------------|-----------------|
| Rate limit (429) | Auth failed (401) |
| Network timeout | Permission denied (403) |
| Server error (5xx) | Invalid nodeId (404) |
| Asset download fail | Cache corrupted |

## Human Intervention Points

When errors are non-recoverable, the skill pauses and prompts:

```
╔══════════════════════════════════════════════════════════════╗
║  Error: Cache not found (CACHE_001)                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  The required cache files were not found.                    ║
║                                                              ║
║  Options:                                                    ║
║    1. Run prefetch: /figma-prefetch {url}                   ║
║    2. Abort implementation                                   ║
║                                                              ║
║  Enter your choice (1/2):                                    ║
╚══════════════════════════════════════════════════════════════╝
```

## Logging

All errors are logged to:

```
.claude/logs/figma-implement-{timestamp}.log
```

Log format:

```
[2026-01-30T12:00:00] ERROR CACHE_001: Cache not found
  at Step0.validateCache()
  details: Expected .claude/cache/figma/about/
```
