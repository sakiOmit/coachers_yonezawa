---
name: figma-design-tokens-extractor
description: "Extract design tokens from Figma Variables and convert to SCSS variables (CSS Custom Properties)"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - mcp__figma__get_variable_defs
  - mcp__figma__get_design_context
context: fork
agent: general-purpose
---

# Figma Design Tokens Extractor

## Overview

Extract design tokens from Figma Variables and automatically convert them to SCSS variables (CSS Custom Properties). This skill outputs colors, typography, spacing, and other design tokens to SCSS files, ensuring consistency between design and implementation.

## Usage

```
/figma-design-tokens-extractor [Figma URL]
```

Or with explicit parameters:

```
/figma-design-tokens-extractor --file-key {fileKey} --node-id {nodeId}
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| URL | Yes* | Figma page URL |
| --file-key | Yes* | Figma file key (alternative to URL) |
| --node-id | No | Target node ID for analysis |
| --output | No | Output path (default: `src/scss/foundation/_figma-tokens.scss`) |
| --mode | No | Output mode: `replace` or `merge` (default: `replace`) |
| --prefix | No | CSS Custom Properties prefix (default: none) |

*Either URL or --file-key is required

## Output

### SCSS Format (Default)

```scss
// ===== Figma Design Tokens (Auto-generated) =====
// Source: {fileKey} / {nodeId}
// Generated: {timestamp}
// ================================================

:root {
  // Colors
  --color-primary: #d71218;
  --color-secondary: #333333;
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #666666;

  // Typography
  --font-family-base: "Noto Sans JP", sans-serif;
  --font-size-body: 16px;
  --line-height-base: 1.75;

  // Spacing
  --spacing-8: 8px;
  --spacing-16: 16px;
  --spacing-section: 80px;

  // Border Radius
  --radius-small: 4px;
  --radius-medium: 8px;
}

// ===== End Figma Design Tokens =====
```

## Processing Flow

```
1. Parse Input
   └─ Extract fileKey/nodeId from URL

2. Fetch Figma Variables
   ├─ Call mcp__figma__get_variable_defs
   └─ Fallback to get_design_context if empty

3. Transform Naming Convention
   ├─ Slash `/` → Hyphen `-`
   ├─ camelCase → kebab-case
   ├─ Add CSS Custom Properties prefix `--`
   └─ Preserve numeric suffixes

4. Categorize Tokens
   ├─ colors: hex, rgba, hsla values
   ├─ typography: font-*, line-height, letter-spacing
   ├─ spacing: numeric values
   ├─ radius: corner radius
   └─ shadows: drop shadow effects

5. Merge Processing (mode=merge)
   ├─ Detect auto-generated section markers
   ├─ Preserve manual additions
   └─ Update only auto-generated section

6. Generate SCSS Output
   ├─ Add header comment
   ├─ Group by category
   └─ Write to file
```

## Naming Convention Mapping

| Figma Variable | SCSS Variable (CSS Custom Property) |
|----------------|-------------------------------------|
| `color/primary` | `--color-primary` |
| `color/text/secondary` | `--color-text-secondary` |
| `fontSize/body` | `--font-size-body` |
| `lineHeight/tight` | `--line-height-tight` |
| `spacing/8` | `--spacing-8` |

## Fallback Processing

When `get_variable_defs` returns empty (Figma Variables not defined):

1. Fetch node data via `get_design_context`
2. Extract colors, fonts, spacing from style information
3. Present high-frequency values as token candidates
4. Convert to SCSS variables after user confirmation

## Error Handling

| Error | Response |
|-------|----------|
| Figma API timeout | Retry 3 times, then report error |
| Variables empty | Execute fallback extraction |
| Permission error | Output error message |
| Output path not writable | Suggest alternative path |
| Existing file conflict | Create backup, then overwrite |

## Related Files

| File | Purpose |
|------|---------|
| `src/scss/foundation/_figma-tokens.scss` | Default output |
| `src/scss/foundation/_variables.scss` | Manual variable definitions |
| `.claude/rules/scss.md` | Naming convention reference |
| `.claude/cache/figma/` | Cache storage |

## Examples

### Basic Usage

```bash
/figma-design-tokens-extractor https://www.figma.com/design/xxx/file?node-id=1-2
```

### Custom Output Path

```bash
/figma-design-tokens-extractor --file-key xxx --output src/scss/foundation/_design-tokens.scss
```

### Merge Mode (Preserve Existing)

```bash
/figma-design-tokens-extractor --file-key xxx --mode merge
```

### With Prefix

```bash
/figma-design-tokens-extractor --file-key xxx --prefix theme
# Output: --theme-color-primary, --theme-spacing-8, etc.
```

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Author**: Auto-generated
