# Astro Workflow Rules

## Overview

Astro静的コーディング → WordPress変換の2段階ワークフローにおける規約を定義する。
Astroで先にデザインを実装・確認し、承認後にWordPress PHPへ変換する。

## ディレクトリ構成

```
astro/
├── astro.config.mjs          # Vite設定（プラグイン登録）
├── package.json              # Astro固有依存のみ
├── tsconfig.json             # TypeScript設定
├── plugins/
│   ├── vite-sass-compiler.mjs  # SCSS→CSS プリコンパイル
│   └── vite-js-bundler.mjs     # JS バンドル (esbuild)
├── public/assets/              # ← プラグイン生成（.gitignore済み）
│   ├── css/                    #   common.css, pages/*/style.css
│   └── js/                     #   main.js, pages/*/index.js
└── src/
    ├── layouts/              # → header.php + footer.php
    ├── pages/                # → pages/page-*.php
    ├── components/
    │   ├── common/           # → template-parts/common/
    │   ├── components/       # → template-parts/components/
    │   └── sections/{page}/  # → template-parts/{page}/
    ├── data/                 # ACFモックデータ (JSON)
    │   ├── site-info.json    # ACFオプションページ相当
    │   └── pages/            # ページ別フィールド
    └── lib/                  # ヘルパー関数
```

## SCSS/JS ビルドフロー（核心）

Astro/WordPress両環境が同一の `src/scss/` `src/js/` を参照する。
**SCSS/JS は Vite プラグインで独立プリコンパイル** → `<link>`/`<script>` で読み込む。

### プリコンパイルの仕組み

- `vite-sass-compiler.mjs`: `src/css/` の SCSS → `astro/public/assets/css/` に CSS 出力
- `vite-js-bundler.mjs`: `src/js/` の ES modules → `astro/public/assets/js/` に IIFE バンドル出力
- 開発時: chokidar で `src/scss/` `src/css/` `src/js/` を監視 → 自動再コンパイル + フルリロード

### レイアウトでの読み込み

```astro
<!-- ✅ BaseLayout.astro — 共通CSS/JS -->
<link rel="stylesheet" href="/assets/css/common.css" />
<slot name="addCSS" />
...
<script src="/assets/js/main.js" is:inline></script>
<slot name="addJS" />
```

### ページでの読み込み

```astro
<!-- ✅ ページファイル — 固有CSS/JSをslotで注入 -->
<BaseLayout title="..." bodyClass="p-top">
  <link rel="stylesheet" href="/assets/css/pages/top/style.css" slot="addCSS" />
  <main>...</main>
  <!-- <script src="/assets/js/pages/top/index.js" slot="addJS" is:inline></script> -->
</BaseLayout>
```

- `rv()`, `svw()`, `pvw()` → 同一SCSS経由で両環境で動作
- `@include sp`, `@include hover`, `@include container()` → 同一mixin
- SCSS変更は `src/scss/` に書く → 両環境に即反映

## 命名規約

### ファイル名

| WordPress (PHP) | Astro |
|-----------------|-------|
| `page-header.php` | `PageHeader.astro` |
| `link-button.php` | `LinkButton.astro` |
| `page-home.php` | `index.astro` (または `about.astro` 等) |

**変換**: `kebab-case.php` → `PascalCase.astro`

### Props

| WordPress (PHP) | Astro (TypeScript) |
|------------------|--------------------|
| `$args['ja_label']` | `jaLabel` |
| `$args['en_heading']` | `enHeading` |
| `$args['modifier_class']` | `modifierClass` |

**変換**: `snake_case` → `camelCase`

### BEMクラス名

**完全一致**（変更なし）:
- `c-page-header__title` → そのまま
- `p-top-whats-new__item` → そのまま

## コンポーネントマッピング

| Astro | WordPress PHP |
|-------|---------------|
| `<Component prop={value} />` | `get_template_part('...', null, ['prop' => $value])` |
| `import data from '../data/...'` | `get_field('field')` |
| `<ResponsiveImage src="..." />` | `render_responsive_image([...])` |
| `{text}` | `<?php echo esc_html($text); ?>` |
| `set:html={html}` | `<?php echo wp_kses_post($html); ?>` |
| `{condition && <div>...</div>}` | `<?php if ($cond): ?><div>...</div><?php endif; ?>` |
| `{items.map(i => <Item {...i} />)}` | `<?php while (have_rows(...)): the_row(); ?>...<?php endwhile; ?>` |

## データモデリング

ACF構造をJSONで表現し、`data-helpers.ts` でWordPress APIを模倣:

```typescript
getField(data, 'field', fallback)   // → get_field('field') ?? $default
getImage(data, 'image_field')       // → get_field('image_field')
getSiteInfo('phone')                // → get_field('phone', 'option')
getRepeater(data, 'items')          // → have_rows('items')
```

## 画像処理

### ResponsiveImage コンポーネント使用（必須）

すべての画像出力に `<ResponsiveImage />` コンポーネントを使用する。
`<img>` タグの直接記述は禁止。WordPress版 `render_responsive_image()` と同一HTMLを出力し、変換時の差分を防ぐ。

```astro
// ✅ 正しい - ResponsiveImage使用
<ResponsiveImage src="/assets/images/hero.webp" alt="ヒーロー画像" class="p-hero__image" />

// ✅ 正しい - SP分岐なし
<ResponsiveImage src="/assets/images/logo.webp" alt="ロゴ" sp={false} />

// ❌ 禁止 - img直接記述
<img src="/assets/images/hero.webp" alt="ヒーロー画像" />
```

**WebP専用**。`ResponsiveImage.astro` と `render_responsive_image()` が同一HTML出力を生成。

### 出力パターン

| 条件 | HTML |
|------|------|
| SP分岐あり | `<picture>` + `<source>(1x,2x,3x)` + `<img>(1x,2x)` |
| SP分岐なし | `<img srcset="1x, 2x">` のみ（`<picture>` 不要） |
| SVG | `<img>` のみ |

```html
<!-- SP分岐あり -->
<picture>
  <source media="(max-width: 767px)"
    srcset="*_sp.webp 1x, *_sp@2x.webp 2x, *_sp@3x.webp 3x" />
  <img src="*.webp" srcset="*.webp 1x, *@2x.webp 2x" ... />
</picture>

<!-- SP分岐なし -->
<img src="*.webp" srcset="*.webp 1x, *@2x.webp 2x" ... />
```

### 画像ファイル命名規約

| 用途 | ファイル名 |
|------|-----------|
| PC 1x | `image.webp` |
| PC 2x | `image@2x.webp` |
| SP 1x | `image_sp.webp` |
| SP 2x | `image_sp@2x.webp` |
| SP 3x | `image_sp@3x.webp` |

`npm run image-opt` が `src/images/` から上記一式を自動生成。

### width/height 自動取得

| 環境 | 方式 | コスト |
|------|------|--------|
| Astro | `image-size` パッケージでビルド時に直接取得 | ランタイムゼロ |
| WordPress | `images-meta.php` (`npm run image-opt` 生成) | opcache 済み、実質ゼロ |

- Retina(2x) 画像: 実寸法 ÷ 2 = 表示寸法
- SVG: viewBox から取得（Astro: `xml2js`、PHP: 正規表現）
- 手動 width/height 指定がある場合はそちらを優先

### 禁止

| 禁止項目 | 理由 |
|---------|------|
| `<img>` 直接記述 | `<ResponsiveImage />` を使用。WP版との出力一致を保証 |
| PNG/JPG フォールバック | WebP専用。`<source type="image/...">` 不要 |
| `<img src="*.png">` | WebPのみ出力 |
| `getimagesize()` でランタイム取得 | リクエスト毎のFS I/O。`images-meta.php` を使用 |

## 禁止事項

| 禁止項目 | 理由 |
|---------|------|
| Astro独自のクラス名追加 | WordPress変換時の差分発生 |
| `<style>` scoped（Astro機能） | SCSS共有と競合 |
| Astro固有の画像最適化 | WordPress版と出力が異なる |
| `src/scss/` の直接編集をAstro側から | 既存ビルドに影響 |
| `.astro` 内での SCSS/JS インポート | WP変換時にビルド経路が異なる |
| `.astro` 内での `<script>` インライン | WP側は `src/js/` からViteビルド |

### SCSS/JS インポート禁止（厳守）

`.astro` ファイル内で SCSS や JS を直接インポート・インライン記述してはならない。
SCSS/JS は Vite プラグインで独立プリコンパイルされ、`<link>`/`<script>` で読み込む。

```astro
// ❌ 禁止 — .astro 内での SCSS インポート
---
import '@root-src/scss/object/components/l-header/_use-with-action.scss';
import '@root-src/css/common.scss';
import '../styles/custom.scss';
---

// ❌ 禁止 — .astro 内での <style>
<style lang="scss">
  .p-hero { color: red; }
</style>

// ❌ 禁止 — .astro 内での <script> インライン
<script>
  document.querySelector('.js-toggle')?.addEventListener('click', () => {});
</script>

// ❌ 禁止 — .astro 内での JS インポート
---
import './header-toggle.js';
---
```

**正しい方法**: `src/css/` と `src/js/` に配置 → プラグインが自動コンパイル → `<link>`/`<script>` で読み込む。

```
src/css/common.scss             ← 共通 SCSS エントリー → /assets/css/common.css
src/css/pages/top/style.scss    ← ページ別 SCSS エントリー → /assets/css/pages/top/style.css
src/js/main.js                  ← 共通 JS エントリー → /assets/js/main.js
src/js/pages/top/index.js       ← ページ別 JS エントリー → /assets/js/pages/top/index.js
```

**共通CSS/JS は BaseLayout.astro で `<link>`/`<script>` として読み込む。**
**ページ固有CSS/JS は `<slot name="addCSS" />` / `<slot name="addJS" />` で注入する。**

```astro
// ✅ 正しい — ページファイルでの slot 注入
<BaseLayout title="..." bodyClass="p-top">
  <link rel="stylesheet" href="/assets/css/pages/top/style.css" slot="addCSS" />
  <main>...</main>
</BaseLayout>
```

## 開発サーバー

```
[Port 4321] Astro Dev Server    ← npm run astro:dev
[Port 3000] Vite Dev Server     ← npm run dev
[Port 8000] WordPress           ← Docker
```

2つのdev serverは独立。同時起動可能。

## チェックリスト

### Astro実装時
- [ ] BEMクラス名がWordPress版と完全一致
- [ ] SCSS/JSは `src/css/` `src/js/` 経由（.astro内インポート禁止）
- [ ] Props interfaceが定義されている
- [ ] モックデータがACF構造を模倣
- [ ] `ResponsiveImage` コンポーネントを使用

### WordPress変換時
- [ ] 全出力がエスケープされている（esc_html, esc_url, wp_kses_post）
- [ ] ACFフィールドに空チェックがある
- [ ] `validate_template_args` + `merge_template_defaults` を使用
- [ ] Template Nameコメントが記述されている
- [ ] セクションは独立Block
