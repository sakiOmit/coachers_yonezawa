---
name: review
description: "Run all code reviews (SCSS, PHP, JS) or specific type"
argument-hint: "[all|scss|php|js]"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
model: opus
context: fork
agent: general-purpose
---

# Unified Code Review Command

## Dynamic Context

```
Recent review files:
!`ls -t .claude/reviews/ 2>/dev/null | head -5 || echo "(empty)"`
```

Run production readiness reviews for all code types or specific ones.

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | 任意の実装スキル完了後 |
| **後工程** | `/fix` |
| **呼び出し元** | ユーザー直接, production-reviewer（プロアクティブ） |
| **呼び出し先** | production-reviewer エージェント |

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

## Review Criteria

### SCSS レビュー観点

| # | 観点 | 検出方法 | 重要度 |
|---|------|---------|--------|
| 1 | BEM 命名違反（&- ネスト） | grep `&-[a-z]` | High |
| 2 | FLOCSS プレフィックス欠如 | クラス名がl-/c-/p-/u-で始まらない | High |
| 3 | Base style 重複 | `rv(16)`, `line-height: 1.6` 等の再宣言 | Medium |
| 4 | Container ルール違反 | `max-width`, `margin: 0 auto` の直書き | Medium |
| 5 | マジックナンバー | `rv()`/`svw()` 未使用の数値 | Medium |
| 6 | 深いネスト (4+) | インデント深度 | Medium |
| 7 | 未使用 @use | 宣言のみで使われていない import | Low |
| 8 | hover 直書き | `&:hover` を `@include hover` に | Low |
| 9 | mask-image 未使用 | アイコンに `background: url(SVG)` 使用 | Medium |
| 10 | レスポンシブ設計 | `@include sp` の有無 | High |

### PHP レビュー観点

| # | 観点 | 検出方法 | 重要度 |
|---|------|---------|--------|
| 1 | XSS（エスケープ漏れ） | `echo $var` without esc_* | Critical |
| 2 | the_field() 使用 | grep `the_field(` | Critical |
| 3 | ACF 空チェック漏れ | get_field() の戻り値未検証 | High |
| 4 | Template Name 欠如 | コメントヘッダー未記載 | High |
| 5 | validate_template_args 欠如 | 関数呼び出し未記載 | High |
| 6 | デバッグコード残留 | var_dump, print_r, error_log | High |
| 7 | SQL インジェクション | $wpdb->prepare 未使用 | Critical |
| 8 | CSRF 対策 | wp_nonce 未使用（フォーム） | Critical |
| 9 | 直書き HTML | PHP 内の長い HTML 文字列 | Medium |
| 10 | enqueue 登録 | CSS/JS が正しく登録されているか | Medium |

### JS レビュー観点

| # | 観点 | 検出方法 | 重要度 |
|---|------|---------|--------|
| 1 | console.log 残留 | grep | High |
| 2 | debugger 残留 | grep | Critical |
| 3 | グローバル変数 | var 宣言、window.* 汚染 | High |
| 4 | DOMContentLoaded 未使用 | 初期化パターン | Medium |
| 5 | ARIA 属性未更新 | トグル系で aria-expanded 未操作 | High |
| 6 | js- prefix 未使用 | BEM クラスを JS セレクタに流用 | Medium |
| 7 | メモリリーク | removeEventListener 未対応 | Medium |
| 8 | エラーハンドリング | try/catch 欠如 | Medium |

### Astro レビュー観点

| # | 観点 | 検出方法 | 重要度 |
|---|------|---------|--------|
| 1 | .astro 内 SCSS インポート違反 | `import '@root-src/scss'` または `import '.scss'` を検出 | High |
| 2 | .astro 内 JS インポート違反 | `.astro` 内で `import './js'` または `import 'module.js'` を検出 | High |
| 3 | .astro 内 style タグ禁止 | `<style>` タグまたは `<style lang="scss">` を検出 | High |
| 4 | .astro 内 script タグ禁止 | Astro frontmatter 外での `<script>` インライン記述を検出 | Medium |
| 5 | ResponsiveImage 非使用 | `<img>` 直接記述を検出、`<ResponsiveImage>` 未使用確認 | High |
| 6 | Props interface 欠如 | `interface Props {}` の定義を確認 | Medium |
| 7 | BEM クラス不一致 | WordPress 版と異なるクラス名の追加・変更を検出 | High |
| 8 | picture/source タグ直書き | `<ResponsiveImage>` に頼らず HTML 直書きを検出 | High |

### Severity Levels

| Level | 定義 | 対応 |
|-------|------|------|
| **Critical** | セキュリティ脆弱性・データ損失リスク | 即時修正必須 |
| **High** | 本番環境での不具合・コーディング規約の重大違反 | リリース前修正必須 |
| **Medium** | コーディング規約違反・改善推奨 | 修正推奨 |
| **Low** | スタイル的な改善・ベストプラクティス | 任意 |

## Output

Review results are saved to `.claude/reviews/`:
- `production-YYYYMMDD-HHMMSS.md` - Full review
- `scss-YYYYMMDD-HHMMSS.md` - SCSS only
- `php-YYYYMMDD-HHMMSS.md` - PHP only
- `js-YYYYMMDD-HHMMSS.md` - JS only

### 構造化出力（JSON）

レビュー結果は .md に加えて .json でも出力する:

```json
{
  "review_date": "YYYY-MM-DD",
  "type": "scss|php|js|all",
  "issues": [
    {
      "id": "scss-001",
      "type": "scss",
      "severity": "safe|risky",
      "priority": "critical|high|medium|low",
      "file": "path/to/file",
      "line": 42,
      "rule": "BEM命名違反",
      "description": "具体的な問題の説明",
      "suggestion": "修正案"
    }
  ],
  "summary": {
    "total": 10,
    "critical": 0,
    "high": 2,
    "medium": 5,
    "low": 3,
    "safe_count": 7,
    "risky_count": 3
  },
  "verdict": "READY|NEEDS_REVISIONS"
}
```

保存先: `.claude/reviews/{type}-{YYYYMMDD}-{HHMMSS}.json`

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

## 自動スキャン（レビュー前の前処理）

レビュー前に `bash .claude/skills/review/scripts/automated-review.sh $TYPE` を実行し、機械的に検出可能な問題を先に検出する。`$TYPE` は引数に応じて `scss`・`php`・`js`・`all` を指定する。スクリプトは `.claude/reviews/automated-{TYPE}-{TIMESTAMP}.json` にレポートを保存する。このレポートを production-reviewer への prompt に含めることで、人間的レビューの精度を高める。

```bash
# 引数なし or all の場合
bash .claude/skills/review/scripts/automated-review.sh all

# 特定タイプの場合
bash .claude/skills/review/scripts/automated-review.sh scss
bash .claude/skills/review/scripts/automated-review.sh php
bash .claude/skills/review/scripts/automated-review.sh js
```

0. **Run Automated Scan**
   - 上記スクリプトを Bash で実行する
   - 生成された `.claude/reviews/automated-*.json` を Read で読み込む
   - Critical 件数・Risky 件数を確認し、production-reviewer への context として渡す

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

     【自動スキャン結果】
     .claude/reviews/automated-{TYPE}-{TIMESTAMP}.json を参照してください。
     機械的に検出済みの問題はこのレポートに含まれています。

     以下の手順で進めてください:
     1. docs/coding-guidelines/ から関連ガイドラインを読み込む
     2. Grep/Glob ツールを使用してコードを調査
     3. 問題を分類（Safe/Risky, Critical/High/Medium/Low）
     4. .claude/reviews/ にレポートを保存
     5. ユーザーに結果サマリーと次のステップを提示

     【重要】すべての出力は日本語で行ってください。
   ```

3. **Report Results**
   - Show issue summary
   - Display saved file path
   - Suggest next steps (/fix commands)

## Related Files

### References

- `references/review-output-schema.md` - JSON 出力スキーマ（/fix との連携用）

### Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | exit code |
|-----------|------|-----------|
| `scripts/automated-review.sh [scss\|php\|js\|all]` | 機械的レビュー（前処理） | 0=PASS, 1=Critical検出 |

**出力**: `.claude/reviews/automated-{TYPE}-{TIMESTAMP}.json`

## Error Handling

| Error | Recovery |
|-------|----------|
| production-reviewer エージェント不在 | `.claude/agents/` を確認し、エージェント定義があるか検証。なければ直接レビューを実行する |
| Task tool 呼び出し失敗 | エージェントなしで Read/Grep を使用して直接レビューを実行する |
| レポート出力先のディレクトリ不在 | `.claude/reviews/` ディレクトリを自動作成してからレポートを保存する |

### Fallback

production-reviewer エージェントが利用できない場合、または Task tool が失敗した場合は、Claude 自身が直接以下を実行する:
1. `docs/coding-guidelines/` から関連ガイドラインを Read で読み込む
2. Glob/Grep でコードファイルを検索・精査
3. 問題を Safe/Risky, Critical/High/Medium/Low で分類
4. `.claude/reviews/` ディレクトリが存在しなければ Bash で作成し、レポートを Write で保存
5. 結果サマリーと次のステップをユーザーに提示する
