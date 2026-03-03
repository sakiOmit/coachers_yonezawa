---
name: comment-cleaner
description: "Detect and remove redundant/obvious comments from PHP, SCSS, and JS files."
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# Comment Cleaner

Detect and remove redundant, obvious, or auto-generated comments that reduce code readability.

## Usage

```
/comment-cleaner           # check mode (default)
/comment-cleaner check     # check mode (explicit)
/comment-cleaner fix       # fix mode (auto-delete)
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| mode | No | `check` (default) or `fix` |

## Processing Flow

### Check Mode

```bash
npm run comment-clean:check
```

Scans PHP/SCSS/JS files and reports redundant comments. Exits with code 1 if issues found.

### Fix Mode

```bash
npm run comment-clean:fix
```

Removes detected comments and compresses consecutive blank lines.

### Additional Options

```bash
# Verbose output (show every issue with file:line)
npm run comment-clean -- --verbose

# Filter by category
npm run comment-clean -- --category what-comment

# Single file
npm run comment-clean -- --file src/scss/object/project/_p-hero.scss
```

## Detection Categories

| Category | Example |
|----------|---------|
| `what-comment` | `// タイトルを取得する` |
| `numbered-step` | `// 1. ACFから画像データ取得` |
| `obvious-api` | `// タイトルタグのサポート` before `add_theme_support(...)` |
| `separator` | `// ============` |
| `redundant-modifier` | `// Dark mode` before `&--dark` |
| `obvious-jsdoc` | `/** クリーンアップ関数 */` before `function cleanup()` |
| `import-label` | `// コンポーネント` before `import ...` |

## Whitelist (Preserved)

- Security comments (XSS, CSRF, nonce)
- WHY comments (のため, 理由:, TODO, FIXME, NOTE)
- Browser-specific notes (bfcache, iOS, Safari)
- PHPDoc with tags (@param, @return)
- Performance notes (リフロー, LCP)
- SCSS design-spec comments (px + color)
- _variables.scss separators
- Lint directives (eslint-disable, phpcs:)

## Output

Report saved to `reports/comment-clean-report.json`.

## When to Use

- After Figma implementation (AI-generated comments)
- Before production review
- During QA checks

## Do NOT Use

- For removing TODO/FIXME (those are preserved)
- For security-related comments (preserved)

## Related Tools

- `production-reviewer`: Includes comment quality in review checklist
- `qa-agent`: Includes `comments` category for QA checks

## Error Handling

| Error | Response |
|-------|----------|
| No files found | Exits with code 0, empty report |
| File read error | Skips file, logs warning |
| Invalid --category | Processes all categories (no filter) |
