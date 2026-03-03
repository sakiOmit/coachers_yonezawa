# Boilerplate Cleanup Changelog

Date: 2026-02-19

TRF（東京レストランツファクトリー）固有コンテンツを除去し、`init-project.js` で初期化可能なクリーンなボイラープレートに変換した。

---

## Step 1: 固有ファイルの削除

### SCSS
- `src/scss/object/components/_c-brand-card.scss`
- `src/scss/object/components/_c-brand-modal.scss`
- `src/scss/object/components/_c-recruit-breadcrumbs.scss`
- `src/scss/object/components/_c-recruit-page-header.scss`
- `src/scss/object/projects/top/` (8ファイル)
- `src/css/pages/top/`

### WordPress
- `themes/{{THEME_DIR}}/pages/page-home.php`

### Astro
- `astro/src/pages/index.astro`
- `astro/src/components/sections/top/` (7ファイル: Hero, Business, Brands, Company, Recruitment, WhatsNew, ContactBanner)
- `astro/src/data/pages/home.json`

### ビルド成果物
- `themes/starter/`

## Step 2: PHP固有参照の置換

| ファイル | 変更内容 |
|---------|---------|
| `inc/acf-auto-import.php` | `trf_*` → `{{THEME_PREFIX}}_*`, `'trf_wp'` → `'{{TEXT_DOMAIN}}'` |
| `inc/constants.php` | `TRF_GOOGLE_MAPS_URL` → `{{THEME_PREFIX}}_GOOGLE_MAPS_URL`, URL → プレースホルダー |
| `index.php` | `'trf_wp'` → `'{{TEXT_DOMAIN}}'` |
| `inc/helpers.php` | コメント内 `themes/trf_wp/` → `themes/{{THEME_DIR}}/` |
| `foundation/_utilities.scss` | `@package TRF_Theme` → `@package {{PACKAGE_NAME}}` |
| `inc/enqueue.php` | `has_js` / `uses_splide` 配列をクリア |

## Step 3: header.php の最小化

- Google Fonts: Cormorant Infant, Roboto, Shippori Mincho を削除、Noto Sans JP + Poppins のみ
- ナビリンク: TRF固有 → Home / About / Contact
- ハンバーガーメニュー: 同じ3リンク構造に簡略化
- CTA（採用・お問い合わせ）ボタン削除

## Step 4: footer.php の最小化

- `making fans of japan` / `JAPAN QUALITY` キャッチフレーズ削除
- 会社名 → `{{COMPANY_NAME}}`
- 住所 → `get_site_info('address')` 参照
- Google Maps URL → `{{THEME_PREFIX}}_GOOGLE_MAPS_URL`
- Copyright → `{{COMPANY_NAME_EN}}`
- ナビリンク → Home / About / Contact

## Step 5: SCSS _variables.scss のジェネリック化

- コメント汎用化 (`CSS Variables - Project`)
- `--color-beebuzz-blue` 削除
- `--font-trajan`, `--font-roboto` 削除
- `--font-secondary`: `serif` (汎用明朝体フォールバック)
- `--font-english`: `"Poppins", sans-serif` (汎用欧文フォールバック)
- `_section-heading.scss`: `var(--font-trajan)` → `var(--font-english)`
- `_footer.scss`: ハードコード `"Shippori Mincho"` → `var(--font-secondary)`

## Step 6: スクリプトの動的化

| ファイル | 変更内容 |
|---------|---------|
| `scripts/check/html-semantic.ts` | `'themes/trf_wp/**/*.php'` → `detectThemeName()` 使用 |
| `scripts/check/templates-quality.ts` | `TARGET_DIRS` 3箇所 + `html-validate` コマンド → 動的パス |
| `scripts/qa/check.ts` | `trf_wp` 参照3箇所 → `detectThemeName()` + `RegExp` テンプレートリテラル |
| `scripts/check/links-crawl.ts` | TRF固有30ページ → `['/', '/contact/', '/thanks/', '/privacy/']` |
| `scripts/check/images-404.ts` | TRF固有ページ → `['/', '/contact/', '/privacy/']` |

## Step 7: package.json

削除したスクリプト: `tvcm:import`, `news:import`, `mid-career:import`

## Step 8: vite.config.js

`"style-top"` エントリーを削除

## Step 9: wordpress-pages.yaml

TRF固有ページ構造 → home, about, contact, thanks, privacy の汎用構成に置換

## Step 10: ACF設定ファイル

| ファイル | 変更内容 |
|---------|---------|
| `company-settings.php` | 電話・住所・メール → 汎用プレースホルダー、採用固有フィールド削除 |
| `config.php` | 存在しないファイル参照削除 (shop, topics, brand, top-page) |
| `README.md` | `themes/trf_wp/` → `themes/{{THEME_DIR}}/` |

## Step 11: ドキュメント

| ファイル | 変更内容 |
|---------|---------|
| `docs/features/contact-form-7/setup.md` | 会社名・メール・電話・URL → プレースホルダー |
| `docs/features/contact-form-7/code.md` | 同上 |
| `docs/setup/automated-setup.md` | `trf_acf_imported` → `{{THEME_PREFIX}}_acf_imported` |

## Step 12: Astro BaseLayout.astro

Google Fonts から Cormorant Infant, Shippori Mincho, Roboto を削除、Noto Sans JP + Poppins のみ

## Step 13: component-catalog.yaml

存在しないコンポーネント `c-page-kv`, `p-entry-cta` を削除

## Step 14: CLAUDE.md フォルダ構成更新

プロジェクト構成セクションに確定フォルダ構成ツリーを記載

## 追加: .claude/skills/ の例示データ

| ファイル | 変更内容 |
|---------|---------|
| `figma-section-splitter/SKILL.md` | `Cormorant Infant` → `Poppins` |
| `figma-text-extractor/SKILL.md` | `Shippori Mincho` → `Noto Serif JP` |
| `implementation-quality-validator/SKILL.md` | `Shippori Mincho` → `Georgia` |

---

## 検証結果

| チェック | 結果 |
|---------|------|
| TRF固有文字列 grep | 0件 |
| `npm run build` | Pass |
| `npm run astro:build` | Pass |
| `init-project.js` プレースホルダー整合性 | 全カバー |
