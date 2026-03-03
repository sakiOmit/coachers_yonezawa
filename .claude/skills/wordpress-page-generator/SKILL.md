---
name: wordpress-page-generator
description: "Generate WordPress page templates interactively with PHP template, SCSS structure, and build configuration"
argument-hint: "[page-slug]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - mcp__serena__read_memory
  - mcp__serena__search_for_pattern
  - mcp__serena__find_symbol
model: opus
context: fork
agent: general-purpose
---

# WordPress Page Generator

## Dynamic Context

```
Existing WP page templates:
!`ls themes/*/pages/page-*.php 2>/dev/null || echo "No WP pages"`
```

## Overview

Generate WordPress fixed page templates interactively. This skill collects page name, section structure, and ACF fields through dialogue, then generates PHP templates, SCSS structure, and build configuration in compliance with project conventions.

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | なし（WordPress-first ワークフロー起点） |
| **後工程** | `/review`, `/qa` |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | なし |

## Usage

```
/wordpress-page-generator
```

The skill will guide you through an interactive dialogue to collect:
- Page name (Japanese)
- Page slug (kebab-case)
- Section list
- Estimated line count (for split decision)

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| (interactive) | Yes | Page name in Japanese |
| (interactive) | Yes | Page slug in kebab-case (e.g., about, contact) |
| (interactive) | Yes | Section list (comma-separated) |
| (interactive) | Yes | Estimated line count (200+ triggers split) |

## Output

### Generated Files

**PHP Templates:**
- `themes/{{THEME_NAME}}/pages/page-{slug}.php`
- `themes/{{THEME_NAME}}/template-parts/{slug}/` (if 200+ lines)

**SCSS Structure:**
- `src/scss/object/projects/{slug}/` directory
- `_p-{slug}.scss` - main file
- `_p-{slug}-{section}.scss` - section files

**Entry Point:**
- `src/css/pages/{slug}/style.scss`

### Updated Files

- `vite.config.js` - entry addition
- `themes/{{THEME_NAME}}/inc/enqueue.php` - conditional enqueue

## Processing Flow

```
1. Information Collection (Interactive)
   ├─ Page name (Japanese)
   ├─ Page slug (kebab-case)
   ├─ Section list
   └─ Estimated line count

2. Existing Pattern Check
   ├─ find_symbol: Check existing page structure
   └─ read_memory: Confirm base styles

3. File Generation
   ├─ PHP templates (single or split)
   ├─ SCSS directory structure
   └─ Entry point file

4. Build Configuration Update
   ├─ vite.config.js entry
   └─ enqueue.php conditional

5. Verification
   ├─ PHP syntax check
   ├─ Directory structure confirmation
   └─ Next steps guidance
```

## Generation Rules (Mandatory)

PHP テンプレートパターン、SCSS 構造、Split ルール（200行以上で template-parts 分割）は references に定義。

**詳細**: → [references/template-patterns.md](references/template-patterns.md)（テンプレート + Split ルール + 実装例）

## Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Slug duplicate | ファイル存在チェック | 既存ファイルを確認、別名提案 |
| Invalid kebab-case | 正規表現 `/^[a-z][a-z0-9-]*$/` | バリデーションして修正提案 |
| PHP syntax error | `php -l` exit code != 0 | エラー行を表示して修正 |
| vite.config.js syntax error | `node -e "require('./vite.config.js')"` で検出 | 変更前のバックアップから復元、手動修正を案内 |
| Permission error | `stat` でパーミッション確認 | `chmod 644` を実行 |
| Theme not found | `config/theme.js` + `themes/*/functions.php` 両方不在 | テーマディレクトリの作成手順を案内 |
| `npm run build` 失敗 | exit code != 0 | vite.config.js エントリー追加を確認、enqueue.php の条件分岐を検証 |

## Related Files

| File | Purpose |
|------|---------|
| `docs/coding-guidelines/05-checklist.md` | New page checklist |
| `docs/coding-guidelines/03-wordpress-integration.md` | WordPress conventions |
| `docs/coding-guidelines/04-build-configuration.md` | Build settings |

---

**Instructions for Claude:**

## 引数パース

`$ARGUMENTS` を以下のルールでパースする:

1. **引数あり** (`{page-slug}`): 非対話モードで直接生成を開始
   - `--sections s1,s2,s3` オプション: セクション一覧をカンマ区切りで指定
   - `--lines N` オプション: 推定行数（200以上で template-parts 分割）
   - 例: `/wordpress-page-generator recruit --sections hero,message,positions --lines 300`
2. **引数なし**: 対話モード（従来通りユーザーに質問）

## 実行手順

1. **テーマ名取得**
   - `config/theme.js` から自動検出
   - 検出失敗時: `themes/` 配下を Glob で検索し、テーマディレクトリを特定
   - テーマディレクトリが存在しない場合: 「テーマが見つかりません。`themes/` 配下にテーマディレクトリを作成してください」と案内して終了

2. **セクション確定**
   - 引数に `--sections` あり → カンマ区切りでパース
   - 引数に `--sections` なし → 対話で収集
   - 各セクション名を kebab-case でバリデーション

3. **生成実行**
   - Processing Flow のステップ1-5に従ってファイルを生成
   - `scripts/generate-wp-page.sh` が利用可能であれば先行実行
   - スクリプトが利用できない場合は直接 Write/Edit で生成

4. **検証**
   - PHP syntax check (`php -l`) を実行
   - ファイルパーミッション 644 を確認
   - 生成ファイル一覧と次のステップを出力

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | 入力 | 出力 |
|-----------|------|------|------|
| `scripts/generate-wp-page.sh` | テンプレートベースの WP ページ足場生成 | slug, sections, lines | PHP + SCSS files |

### generate-wp-page.sh

```bash
bash .claude/skills/wordpress-page-generator/scripts/generate-wp-page.sh <slug> <sections> [lines]
# Example:
bash .claude/skills/wordpress-page-generator/scripts/generate-wp-page.sh recruit hero,message,positions 300
```

- **入力**: page-slug (kebab-case), sections (カンマ区切り), lines (省略時: 100)
- **出力**: PHP テンプレート, template-parts (200行以上時), SCSS 構造
- **テーマ検出**: `config/theme.js` → `themes/*/functions.php` フォールバック
- **生成ファイル**:
  - `themes/{theme}/pages/page-{slug}.php` - ページテンプレート
  - `themes/{theme}/template-parts/{slug}/*.php` - セクションパーツ (200行以上時)
  - `src/scss/object/project/{slug}/` - SCSS ファイル群
  - `src/css/pages/{slug}/style.scss` - CSS エントリーポイント
- **パーミッション**: PHP ファイルは 644 に設定
- **終了コード**: 0=成功, 1=バリデーションエラー

## Agent Integration

Step 3（ファイル生成）が複雑な場合、wordpress-professional-engineer エージェントに委譲可能:

```
Task tool:
  subagent_type: wordpress-professional-engineer
  prompt: |
    以下の仕様で WordPress ページテンプレートを生成してください:
    - slug: {slug}
    - sections: {sections}
    - template-parts 分割: {split_required}

    生成ルール: references/template-patterns.md を参照。
    SCSS は src/scss/object/project/{slug}/ に配置。
    php -l で構文チェック後、パーミッション 644 を確認してください。
```

**委譲条件**: セクション数 >= 5 または ACF フィールド構造が複雑な場合
**Fallback**: エージェント不在時は直接 Write/Edit で生成

## Related Skills

| Skill | Purpose |
|-------|---------|
| `acf-field-generator` | Generate ACF fields |
| `scss-component-generator` | Add SCSS components |
| `astro-page-generator` | Astro版ページ生成（Astro-first ワークフロー） |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Original Author**: Theme Development Team
