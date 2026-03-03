---
name: astro-to-wordpress
description: "Convert approved Astro static pages to WordPress PHP templates with ACF integration, escaping, and validation"
disable-model-invocation: false
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
  - mcp__serena__get_symbols_overview
  - mcp__serena__replace_symbol_body
  - mcp__serena__insert_after_symbol
context: fork
agent: general-purpose
---

# Astro to WordPress Converter

## Overview

デザイン承認済みのAstroページをWordPress PHPテンプレートに変換する。
Astroコンポーネントを読み取り、WordPress規約に準拠したPHP・ACF統合コードを生成する。

**自動変換ではなく、規約に基づく手動変換をガイドする。**
理由: PHP固有のACFヘルパー、エスケープ、バリデーションは手動の方が正確。

## Usage

```
/astro-to-wordpress [page-slug]
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| page-slug | Yes | 変換対象ページのスラッグ（例: about） |

## Processing Flow

```
1. Astroソース読み取り
   ├─ astro/src/pages/{slug}.astro
   ├─ astro/src/components/sections/{slug}/*.astro
   ├─ astro/src/data/pages/{slug}.json
   └─ 使用されている共通コンポーネントの特定

2. 既存WordPress環境チェック
   ├─ PHPテンプレートが既に存在するか
   ├─ SCSSエントリーが存在するか
   ├─ vite.config.jsにエントリーがあるか
   └─ enqueue.phpに条件分岐があるか

3. 変換マッピング生成
   ├─ コンポーネント → get_template_part() マッピング
   ├─ Props → PHP $args マッピング
   ├─ データ → ACFフィールド マッピング
   └─ 画像 → render_responsive_image() マッピング

4. PHP生成（セクション単位）
   ├─ ページテンプレート（page-{slug}.php）
   ├─ セクション template-parts（{slug}/section.php）
   └─ ACFフィールド定義メモ

5. 検証チェックリスト実行
   └─ 全項目パス確認

6. ビルド構成更新（不足分のみ）
   ├─ vite.config.js
   └─ enqueue.php
```

## Conversion Rules (Mandatory)

### 変換テーブル

| Astro | WordPress PHP |
|-------|---------------|
| `<Component prop={value} />` | `get_template_part('...', null, ['prop' => $value])` |
| `import data from '../data/...'` | `get_field('field')` / `get_acf_or_default(...)` |
| `<ResponsiveImage src="..." />` | `render_responsive_image([...])` |
| `{text}` | `<?php echo esc_html($text); ?>` |
| `set:html={html}` | `<?php echo wp_kses_post($html); ?>` |
| `{condition && <div>...</div>}` | `<?php if ($cond): ?><div>...</div><?php endif; ?>` |
| `{items.map(i => <Item />)}` | `<?php while (have_rows('items')): the_row(); ?>...<?php endwhile; ?>` |
| Astro `Props` interface | `validate_template_args()` + `merge_template_defaults()` |
| `import '@root-src/css/...'` | `vite_enqueue_page_style()` in enqueue.php |

### Props → PHP Args 変換

```
// Astro (camelCase)          // PHP (snake_case)
interface Props {
  enHeading: string;     →    'en_heading' => '',
  jaLabel?: string;      →    'ja_label' => '',
  modifierClass?: string; →   'modifier_class' => '',
  isTall?: boolean;      →    'is_tall' => false,
}
```

### 必須PHP処理の追加

Astroには存在しないが、PHPで必須の処理:

1. **出力エスケープ**
   - テキスト: `esc_html()`
   - URL: `esc_url()`
   - 属性: `esc_attr()`
   - HTML: `wp_kses_post()`

2. **引数バリデーション**
   ```php
   if (!validate_template_args($args, ['en_heading', 'breadcrumbs'], 'page-header')) {
       return;
   }
   ```

3. **デフォルト値マージ**
   ```php
   $args = merge_template_defaults($args, [
       'en_heading' => '',
       'ja_label' => '',
   ]);
   ```

4. **ACF空チェック**
   ```php
   <?php if ($title = get_field('title')): ?>
     <h2><?php echo esc_html($title); ?></h2>
   <?php endif; ?>
   ```

5. **Template Name コメント**
   ```php
   <?php
   /**
    * Template Name: ページ名
    * @package Theme
    */
   ```

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

**Version**: 1.0.0
**Created**: 2026-02-18
