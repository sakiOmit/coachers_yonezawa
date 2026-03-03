---
name: favicon-generator
description: "Generate modern favicon set (SVG, ICO, Apple Touch Icon, Web Manifest) from source SVG and configure WordPress theme"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
context: fork
agent: general-purpose
---

# Favicon Generator

## Overview

ソースSVGから2025年モダンファビコンセット一式を生成し、WordPressテーマに自動設定するスキル。
sharp（Node.js）を使用してSVGからPNG/ICOを生成し、`functions.php` にファビコン出力フックを追加する。

## Usage

```
/favicon-generator [svg-path]
```

引数なしの場合、`themes/{{THEME_NAME}}/favicon.svg` を自動検出する。

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| svg-path | No | ソースSVGのパス（省略時は自動検出） |

## Prerequisites

- `sharp` npm パッケージがインストール済みであること
- ソースSVGファイルが存在すること

## Output

### Generated Files

**Favicon assets:**
- `themes/{{THEME_NAME}}/assets/images/favicon.ico` — 32x32 ICO（レガシーブラウザ）
- `themes/{{THEME_NAME}}/assets/images/apple-touch-icon.png` — 180x180 PNG（iOS）
- `themes/{{THEME_NAME}}/assets/images/favicon-192x192.png` — 192x192 PNG（Android/PWA）
- `themes/{{THEME_NAME}}/assets/images/favicon-512x512.png` — 512x512 PNG（PWA スプラッシュ）

**Web Manifest:**
- `themes/{{THEME_NAME}}/site.webmanifest`

### Updated Files

- `themes/{{THEME_NAME}}/functions.php` — ファビコン出力フック追加

### HTML Output（wp_head に自動出力）

```html
<link rel="icon" href=".../favicon.svg" type="image/svg+xml">
<link rel="icon" href=".../favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href=".../apple-touch-icon.png">
<link rel="manifest" href=".../site.webmanifest">
```

## Processing Flow

```
1. Prerequisites Check
   ├─ sharp パッケージの存在確認
   ├─ ソースSVG の検出
   └─ 既存ファビコン設定の有無確認

2. Information Collection
   ├─ サイト名（webmanifest 用）
   ├─ 短縮名（short_name 用）
   └─ テーマカラー（SVGの主要色から自動提案）

3. Asset Generation（Node.js + sharp）
   ├─ favicon.ico (32x32 PNG embedded ICO)
   ├─ apple-touch-icon.png (180x180)
   ├─ favicon-192x192.png (192x192)
   └─ favicon-512x512.png (512x512)

4. Web Manifest Generation
   └─ site.webmanifest（name, short_name, icons, theme_color, background_color）

5. WordPress Integration
   ├─ functions.php にファビコン出力関数追加
   ├─ site_icon_meta_tags フィルター無効化（重複防止）
   └─ 既存設定がある場合はスキップ

6. Verification
   ├─ 全ファイルの存在確認
   ├─ ファイルサイズ確認
   └─ functions.php の構文チェック
```

## Generation Rules (Mandatory)

### ブラウザ優先順位

1. **SVG** — モダンブラウザが最優先で使用（スケーラブル、ダークモード対応可）
2. **ICO** — SVG未対応ブラウザのフォールバック
3. **Apple Touch Icon** — iOS ホーム画面追加時
4. **Web Manifest** — Android/PWA

### ICO生成方式

PNG データを ICO コンテナに格納する方式（モダンICO）:

```javascript
const sharp = require('sharp');

// 32x32 PNG を生成
const png32 = await sharp(svgBuffer).resize(32, 32).png().toBuffer();

// ICO ヘッダー（6バイト）+ エントリ（16バイト）+ PNG データ
const icoHeader = Buffer.alloc(6);
icoHeader.writeUInt16LE(0, 0);     // Reserved
icoHeader.writeUInt16LE(1, 2);     // Type: ICO
icoHeader.writeUInt16LE(1, 4);     // Count: 1

const entry = Buffer.alloc(16);
entry.writeUInt8(32, 0);           // Width
entry.writeUInt8(32, 1);           // Height
entry.writeUInt8(0, 2);            // Color palette
entry.writeUInt8(0, 3);            // Reserved
entry.writeUInt16LE(1, 4);         // Color planes
entry.writeUInt16LE(32, 6);        // Bits per pixel
entry.writeUInt32LE(png32.length, 8);  // Data size
entry.writeUInt32LE(22, 12);       // Offset (6 + 16)

const ico = Buffer.concat([icoHeader, entry, png32]);
```

### WordPress 統合

```php
add_action('wp_head', '{theme_prefix}_output_favicon', 1);
function {theme_prefix}_output_favicon() {
    $theme_uri = get_template_directory_uri();
    echo '<link rel="icon" href="' . esc_url($theme_uri . '/favicon.svg') . '" type="image/svg+xml">' . "\n";
    echo '<link rel="icon" href="' . esc_url($theme_uri . '/assets/images/favicon.ico') . '" sizes="32x32">' . "\n";
    echo '<link rel="apple-touch-icon" href="' . esc_url($theme_uri . '/assets/images/apple-touch-icon.png') . '">' . "\n";
    echo '<link rel="manifest" href="' . esc_url($theme_uri . '/site.webmanifest') . '">' . "\n";
}

// WordPress管理画面のサイトアイコン出力を無効化（テーマ側で制御するため）
add_filter('site_icon_meta_tags', '__return_empty_array');
```

### Web Manifest テンプレート

```json
{
  "name": "{site_name}",
  "short_name": "{short_name}",
  "icons": [
    { "src": "assets/images/favicon-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "assets/images/favicon-512x512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "theme_color": "{theme_color}",
  "background_color": "#ffffff",
  "display": "standalone"
}
```

## Error Handling

| Error | Response |
|-------|----------|
| sharp 未インストール | `npm install sharp` の実行を提案 |
| SVG ファイル不在 | パス入力を求めるか、作成を案内 |
| 既存ファビコン設定あり | 上書き確認を求める |
| functions.php 構文エラー | 変更をロールバックして報告 |
| 画像生成失敗 | sharp のエラーメッセージを表示し代替手段を提案 |

## Examples

### Example 1: デフォルト実行

```
/favicon-generator
```

```
Agent: favicon.svg を検出しました (themes/{{THEME_NAME}}/favicon.svg)
Agent: サイト情報を入力してください:

サイト名: 株式会社ティアラボ 採用サイト
短縮名: Tialabo
テーマカラー: #e096a5 (SVGから自動検出)

生成ファイル:
  themes/{{THEME_NAME}}/assets/images/favicon.ico (32x32)
  themes/{{THEME_NAME}}/assets/images/apple-touch-icon.png (180x180)
  themes/{{THEME_NAME}}/assets/images/favicon-192x192.png (192x192)
  themes/{{THEME_NAME}}/assets/images/favicon-512x512.png (512x512)
  themes/{{THEME_NAME}}/site.webmanifest

更新ファイル:
  themes/{{THEME_NAME}}/functions.php (ファビコン出力フック追加)

Continue? (yes/no)
```

### Example 2: パス指定

```
/favicon-generator themes/{{THEME_NAME}}/assets/images/logo.svg
```

## Related Skills

| Skill | Purpose |
|-------|---------|
| `wordpress-page-generator` | WordPress ページテンプレート生成 |
| `seo-check` | JSON-LD・SEO要素検証 |

---

**Version**: 1.0.0
**Created**: 2026-02-09
