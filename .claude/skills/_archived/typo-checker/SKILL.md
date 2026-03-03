---
name: typo-checker
description: "PHPテンプレート内の日本語テキストの誤字脱字をtextlint+AIパターンチェックで検出・修正する"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# Typo Checker

PHPテンプレート内の日本語テキストに対する誤字脱字チェック。
textlint（機械的ルール）+ AIパターン検出（助詞脱落等）の2フェーズで検出する。

## Usage

```
/typo-checker                # check mode (default): textlint + AI
/typo-checker fix            # fix mode: textlint --fix + AI report
/typo-checker textlint       # textlint only
/typo-checker ai             # AI pattern check only
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| mode | No | `check` (default), `fix`, `textlint`, `ai` |

## Processing Flow

### Check Mode (default)

```bash
npm run typo:check
```

Extracts Japanese text from PHP templates, runs textlint + AI pattern checks, reports issues. Exits with code 1 if issues found.

### Fix Mode

```bash
npm run typo:fix
```

Runs textlint with `--fix` for auto-fixable issues. AI-detected issues are reported only (manual fix required).

### Additional Options

```bash
# Verbose output
npm run typo:check -- --verbose

# Single file
npm run typo:check -- --file themes/{{THEME_NAME}}/template-parts/sections/home/service.php

# textlint only
npm run typo:check -- --textlint-only

# AI pattern check only
npm run typo:check -- --ai-only
```

## Detection Categories

### textlint Rules

| Rule | Description |
|------|-------------|
| preset-ja-technical-writing | 日本語技術文書向けルール群 |
| preset-jtf-style | JTFスタイルガイド |
| no-doubled-joshi | 助詞の連続使用 |
| no-mix-dearu-desumasu | ですます/である混在 |
| no-doubled-conjunction | 接続詞の連続使用 |
| no-nfd | NFD文字検出 |

### AI Pattern Checks

| Category | Description |
|----------|-------------|
| missing-particle | 助詞の脱落（「～ついて」→「～について」等） |

## Output

Report saved to `reports/typo-check-report.json`.

Console output example:
```
  themes/{{THEME_NAME}}/template-parts/sections/home/service.php
    L126 [error] [AI:missing-particle] 助詞の脱落: 「界ついて」→「界について」
         → 界について
```

## Scan Targets

- `themes/{{THEME_NAME}}/template-parts/sections/**/*.php`
- `themes/{{THEME_NAME}}/pages/page-*.php`
- `themes/{{THEME_NAME}}/template-parts/common/**/*.php`
- `themes/{{THEME_NAME}}/template-parts/components/**/*.php`

## When to Use

- Before production review
- After content updates
- During QA checks
- Before client delivery

## Do NOT Use

- For SCSS/JS file checking (use lint tools instead)
- For ACF dynamic content (skipped by design)

## Related Tools

- `comment-cleaner`: Redundant comment detection/removal
- `production-reviewer`: Includes text quality in review checklist
- `qa-agent`: Includes quality checks

## Error Handling

| Error | Response |
|-------|----------|
| No PHP files found | Exits with code 0, empty report |
| textlint not installed | Error message with install instructions |
| File read error | Skips file, continues processing |
