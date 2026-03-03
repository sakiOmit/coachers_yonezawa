---
name: review
description: "Run all code reviews (SCSS, PHP, JS) or specific type"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Glob
  - Grep
  - Write
context: fork
agent: general-purpose
---

# Unified Code Review Command

Run production readiness reviews for all code types or specific ones.

## Usage

```bash
# Review all code types
/review
/review all

# Review specific type
/review scss         # SCSS only
/review php          # PHP/WordPress only
/review js           # JavaScript only

# Multiple types
/review scss php     # SCSS and PHP
/review scss js      # SCSS and JavaScript
```

## What This Does

### `/review` or `/review all`

Launches the `production-reviewer` agent to review all code:
- **SCSS**: FLOCSS + BEM compliance, naming, base style duplication
- **PHP/WordPress**: Security, HTML semantics, SEO, accessibility
- **JavaScript**: Code quality, performance, memory leaks

### `/review {type}`

| Command | Focus |
|---------|-------|
| `/review scss` | FLOCSS, BEM naming, base styles, container rules |
| `/review php` | Security (XSS, SQLi), WordPress best practices, HTML |
| `/review js` | console.log, unused code, error handling, memory leaks |

## Output

Review results are saved to `.claude/reviews/`:
- `production-YYYYMMDD-HHMMSS.md` - Full review
- `scss-YYYYMMDD-HHMMSS.md` - SCSS only
- `php-YYYYMMDD-HHMMSS.md` - PHP only
- `js-YYYYMMDD-HHMMSS.md` - JS only

### Report Format

```markdown
# Production Readiness Review

## Issues by Type

### SCSS Issues (5)
- [SAFE] name-001: CamelCase class name
- [RISKY] dup-001: Base style duplication

### PHP Issues (3)
- [RISKY] sec-001: XSS vulnerability
- [SAFE] quality-001: var_dump in code

### JavaScript Issues (2)
- [SAFE] quality-002: console.log in production

## Production Readiness: NEEDS REVISIONS

## Next Steps
- `/fix auto` - Fix all safe issues
- `/fix sec-001` - Fix specific issue
```

## After Review

```bash
# Fix safe issues automatically
/fix auto

# Fix specific type
/fix scss
/fix php
/fix js

# Fix specific issue
/fix name-001
/fix sec-001
```

---

**Instructions for Claude:**

Based on `$ARGUMENTS`, launch the production-reviewer agent:

1. **Parse Arguments**
   - No args or `all` → Full review (SCSS + JS + PHP)
   - `scss` → SCSS/FLOCSS/BEM only
   - `php` → PHP/WordPress only
   - `js` → JavaScript only
   - Multiple types → Review specified types

2. **Launch Agent**
   ```
   Task tool: subagent_type=production-reviewer
   prompt: |
     コードレビューを実行してください。

     【対象】$ARGUMENTS（空の場合は all）

     以下の手順で進めてください:
     1. docs/coding-guidelines/ から関連ガイドラインを読み込む
     2. Serena MCP を使用してコードを調査
     3. 問題を分類（Safe/Risky, Critical/High/Medium/Low）
     4. .claude/reviews/ にレポートを保存
     5. ユーザーに結果サマリーと次のステップを提示

     【重要】すべての出力は日本語で行ってください。
   ```

3. **Report Results**
   - Show issue summary
   - Display saved file path
   - Suggest next steps (/fix commands)
