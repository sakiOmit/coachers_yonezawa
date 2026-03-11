---
name: astro-to-wordpress
description: "Convert approved Astro static pages to WordPress PHP templates with ACF integration, escaping, and validation"
argument-hint: "{page-slug}"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
model: opus
context: fork
agent: general-purpose
---

# Astro to WordPress Converter

## Dynamic Context

```
Available Astro pages:
!`ls astro/src/pages/*.astro 2>/dev/null || echo "No Astro pages"`
```

## Overview

デザイン承認済みのAstroページをWordPress PHPテンプレートに変換する。
Astroコンポーネントを読み取り、WordPress規約に準拠したPHP・ACF統合コードを生成する。

**半自動変換**: 機械的な変換をスクリプトで自動化し、ACFロジック・条件分岐等はLLMが担当する。

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | `/figma-implement`, `/astro-page-generator` |
| **後工程** | `/review`, `/qa` |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | wordpress-professional-engineer エージェント |

## Usage

```
/astro-to-wordpress [page-slug]
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| page-slug | Yes | 変換対象ページのスラッグ（例: about） |

## Processing Flow

### Step 0: Automated Scaffold (Script)

スクリプトで機械的な変換を先行実行する。

```bash
bash .claude/skills/astro-to-wordpress/scripts/convert-astro-to-php.sh {slug}
```

**スクリプトが自動実行する内容:**
- ソースファイル検証（Astro ページ、セクション、データの存在確認）
- Props interface 解析（camelCase → snake_case マッピング）
- PHP スタブファイル生成（ページテンプレート + セクション template-parts）
- ビルド設定チェック（vite.config.js, enqueue.php のエントリー確認）
- PHP syntax チェック + パーミッション検証

**出力**: `reports/convert-{slug}-{TIMESTAMP}.json`（変換レポート）

**exit code**: 0 = 成功、1 = ソース検証失敗

### Step 1: Script Report Analysis
- **入力**: Step 0 のレポート JSON を Read で読み込み
- **処理**: 自動生成されたスタブの確認、manual_required 項目の把握
- **出力**: LLM が担当すべき変換タスクの一覧
- **検証**: レポートの verdict が `READY_FOR_LLM` であること

### Step 2: HTML Conversion (LLM)
- **入力**: Astro セクションファイル（HTML テンプレート部分）、conversion-patterns.md
- **処理**: 自動生成スタブの `<!-- TODO -->` を実際の HTML に変換。ACF ロジック、条件分岐、ループ構造は LLM が判断。
  - Repeater フィールド: `{items.map(...)}` → `<?php while (have_rows('items')): the_row(); ?> ... <?php endwhile; ?>`
  - Group フィールド: `{data.group.field}` → `<?php echo esc_html(get_field('field', get_field('group'))); ?>`
  - テキストフィールド: `{text}` → `<?php echo esc_html(get_field('text_field')); ?>`
  - URL フィールド: `{url}` → `<?php echo esc_url(get_field('url_field')); ?>`
  - 条件分岐: `{condition && <div>...</div>}` → `<?php if (get_field('condition')): ?><div>...</div><?php endif; ?>`
- **出力**: 完成した PHP テンプレート
- **検証**: BEM クラス名が Astro 版と完全一致、全出力にエスケープ関数適用
- **エージェント委譲**: wordpress-professional-engineer が利用可能な場合、PHP 実装を Task として委譲する

### Step 3: Build Configuration Update
- **入力**: Step 0 レポートの manual_required 項目、Step 2 で完成した PHP テンプレート
- **処理**: `vite.config.js` へのエントリー追加、`enqueue.php` への条件分岐追加
- **出力**: 更新済みの設定ファイル
- **検証**: `npm run build` が成功すること
- **エージェント委譲**: 複雑な Vite 設定変更が必要な場合、wordpress-professional-engineer に委譲可能

### Step 4: Verification Checklist Execution
- **入力**: Step 2 で完成した全 PHP ファイル
- **処理**: 後述の Verification Checklist の全項目を確認
- **出力**: チェックリスト結果（全項目パス / 要修正の項目一覧）
- **検証**: 全項目パスするまで修正を繰り返すこと

## Conversion Rules

変換パターンの詳細は [references/conversion-patterns.md](references/conversion-patterns.md) を参照。

**主要な変換の概要:**
- Props → PHP $args（camelCase → snake_case）
- テンプレート構文（`{text}` → `<?php echo esc_html() ?>`）
- ACF フィールド取得パターン
- エスケープルール（esc_html / esc_url / wp_kses_post）

## Verification Checklist

変換完了時に必ず全項目を確認:

### HTML構造
- [ ] BEMクラス名がAstro版と完全一致
- [ ] セクションは独立Block（`p-page__section` 禁止）
- [ ] HTMLセマンティクスが適切（section, article, nav等）

### セキュリティ
- [ ] 全テキスト出力に `esc_html()` 使用
- [ ] 全URL出力に `esc_url()` 使用
- [ ] 全属性出力に `esc_attr()` 使用
- [ ] HTMLコンテンツは `wp_kses_post()` 使用
- [ ] `the_field()` は使用禁止（`get_field()` + エスケープ）

### WordPress規約
- [ ] `Template Name` コメント記述
- [ ] `validate_template_args()` 使用
- [ ] `merge_template_defaults()` 使用
- [ ] ACFフィールドに空チェック
- [ ] 画像は `render_responsive_image()` 使用
- [ ] `get_template_part()` で変数渡し

### ビルド
- [ ] vite.config.js にエントリー追加済み
- [ ] enqueue.php に条件分岐追加済み
- [ ] `npm run build` 成功
- [ ] ファイルパーミッション 644

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | exit code |
|-----------|------|-----------|
| `scripts/convert-astro-to-php.sh <slug> [--dry-run]` | 半自動変換（Props抽出 + PHPスタブ生成） | 0=PASS, 1=ソース検証失敗 |

**出力**: `reports/convert-{slug}-{TIMESTAMP}.json`

## Error Handling

| Error | Response |
|-------|----------|
| Astroページが存在しない | パス確認を促す |
| PHPテンプレートが既に存在 | 差分比較して更新提案 |
| ACFフィールド未定義 | フィールド定義メモを出力 |
| ビルドエラー | SCSS/PHP構文チェック |

## Output

### 生成レポート

```
✅ Astro → WordPress 変換完了: {slug}

| Astro Source | WordPress Output | Status |
|-------------|-----------------|--------|
| pages/{slug}.astro | pages/page-{slug}.php | ✅ |
| sections/{slug}/Hero.astro | template-parts/{slug}/hero.php | ✅ |
| sections/{slug}/About.astro | template-parts/{slug}/about.php | ✅ |
| data/pages/{slug}.json | → ACFフィールド定義 | 📋 |

チェックリスト: 全項目パス ✅

ACFフィールド定義メモ:
- hero_image (画像) - ヒーロー画像
- hero_title (テキスト) - ヒーロータイトル
- ...

Next steps:
1. WordPress管理画面で固定ページ作成、テンプレート選択
2. ACFフィールドグループ作成（/acf-field-generator）
3. コンテンツ入力
4. production-reviewer でレビュー
```

## Related Skills

| Skill | Purpose |
|-------|---------|
| `astro-page-generator` | Astro版ページ生成 |
| `wordpress-page-generator` | WordPress版ページ生成（ゼロから） |
| `acf-field-generator` | ACFフィールド生成 |

---

**Instructions for Claude:**

## 引数パース

`$ARGUMENTS` を以下のルールでパースする:

1. **引数あり** (`{page-slug}`): 直接変換を開始
   - 例: `/astro-to-wordpress about`
2. **引数なし**: Astro ページ一覧を表示し、対話で変換対象を選択

## 実行手順

1. **ソース検証**
   - `astro/src/pages/{slug}.astro` が存在するか確認
   - 存在しない場合: 動的コンテキストの Astro ページ一覧を表示し、有効なスラッグの選択を促す

2. **スクリプト実行**
   - `scripts/convert-astro-to-php.sh {slug}` が利用可能であれば先行実行
   - スクリプトが利用できない場合は直接 Read/Write/Edit で変換を実行

3. **レポート分析**
   - スクリプト出力の `reports/convert-{slug}-*.json` を Read で読み込み
   - `manual_required` 項目を把握し、LLM が担当すべき変換タスクを特定

4. **ACF ロジック付与**
   - HTML テンプレートの `<!-- TODO -->` を実際の ACF ロジックに変換
   - `get_field()` + エスケープ、`have_rows()` ループ、空チェック等を適用
   - wordpress-professional-engineer エージェントが利用可能であれば Task で委譲

5. **ビルド検証**
   - `npm run build` が成功することを確認
   - PHP syntax check (`php -l`) を実行
   - Verification Checklist の全項目を確認

### Fallback

wordpress-professional-engineer エージェントが利用できない場合は、Claude が直接 Edit ツールで変換を実行する。

---

**Version**: 1.0.0
**Created**: 2026-02-18
