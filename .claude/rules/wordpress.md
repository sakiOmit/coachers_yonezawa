# WordPress Rules

## Overview

このルールファイルは、WordPress開発における規約を定義します。
テンプレート階層、ACF統合、画像処理の標準化を含みます。

## テンプレート構成

### ディレクトリ構造

```
themes/{{THEME_NAME}}/
├── pages/                    # ページテンプレート
│   └── page-*.php
├── template-parts/           # 再利用パーツ
│   ├── components/           # c-* コンポーネント
│   └── sections/             # セクション単位
├── inc/                      # PHP機能分割
│   ├── acf/                  # ACF設定
│   ├── custom-post-types/    # CPT登録
│   └── helpers/              # ヘルパー関数
└── functions.php             # メインエントリー
```

### Template Name（必須）

ページテンプレートには必ずコメントを記述:

```php
<?php
/**
 * Template Name: ページ名
 * Description: ページの説明
 */
```

## HTML構造

### セクション設計（必須）

セクションは独立したBlockとして実装:

```php
// ✅ 正しい - 独立Block
<section class="p-vision">
  <div class="p-vision__container">
    <h2 class="p-vision__title">...</h2>
  </div>
</section>

// ❌ 禁止 - 親Block__section
<div class="p-page">
  <section class="p-page__section">
    <h2 class="p-page__section-title">...</h2>
  </section>
</div>
```

### 理由

- セクション単位での再利用が可能
- スタイルの独立性確保
- 保守性向上

## 画像処理

### WebP専用・render_responsive_image()（必須）

すべての画像出力に使用。**WebPのみ出力**（PNG/JPGフォールバック不要）。

```php
// 基本使用（SP分岐あり: <picture> + <source> 1x,2x,3x）
<?php render_responsive_image([
    'src'   => get_template_directory_uri() . '/assets/images/hero.webp',
    'alt'   => 'ヒーロー画像',
    'class' => 'p-hero__image',
]); ?>

// ACF画像（PC/SP別画像）
<?php render_responsive_image([
    'acf_field' => 'hero_image',
    'alt'       => 'ヒーロー画像',
]); ?>

// SP分岐なし（<img srcset="1x, 2x"> のみ）
<?php render_responsive_image([
    'src' => get_template_directory_uri() . '/assets/images/logo.webp',
    'sp'  => false,
    'alt' => 'ロゴ',
]); ?>
```

### 出力パターン

| 条件 | HTML |
|------|------|
| SP分岐あり | `<picture>` + `<source>(1x,2x,3x)` + `<img>(1x,2x)` |
| SP分岐なし | `<img srcset="1x, 2x">` のみ |
| SVG | `<img>` のみ |

### width/height 自動取得

`images-meta.php`（`npm run image-opt` で生成）から取得。opcache 済みで実質コストゼロ。
手動指定がある場合はそちらを優先。

### 画像ファイル命名規約（`npm run image-opt` で自動生成）

| 用途 | ファイル名 |
|------|-----------|
| PC 1x | `image.webp` |
| PC 2x | `image@2x.webp` |
| SP 1x | `image_sp.webp` |
| SP 2x | `image_sp@2x.webp` |
| SP 3x | `image_sp@3x.webp` |

### Figma書き出し規則

**2倍サイズで書き出す（必須）**

```
Figma表示サイズ → 書き出しサイズ
300px × 200px  → 600px × 400px (@2x)
```

`npm run image-opt` が 2x 原画から 1x / 2x / 3x(SPのみ) の WebP を自動生成。

詳細: `docs/implementation/figma-export-guidelines.md`

## ACF統合

### フィールド出力

```php
// テキスト
echo esc_html(get_field('text_field'));

// URL
echo esc_url(get_field('url_field'));

// WYSIWYG（HTML許可）
echo wp_kses_post(get_field('content_field'));

// 画像
render_responsive_image([
    'acf_field' => 'image_field',
    'class'     => 'p-section__image',
]);
```

### Repeaterフィールド

```php
<?php if (have_rows('items')): ?>
  <ul class="p-list">
    <?php while (have_rows('items')): the_row(); ?>
      <li class="p-list__item">
        <?php echo esc_html(get_sub_field('title')); ?>
      </li>
    <?php endwhile; ?>
  </ul>
<?php endif; ?>
```

### 空チェック（必須）

```php
// ✅ 正しい - 空チェック
<?php if ($title = get_field('title')): ?>
  <h2><?php echo esc_html($title); ?></h2>
<?php endif; ?>

// ❌ 危険 - チェックなし
<h2><?php echo esc_html(get_field('title')); ?></h2>
```

## テンプレートパーツ

### get_template_part()使用

```php
// 基本
get_template_part('template-parts/components/button');

// 変数渡し
get_template_part('template-parts/sections/hero', null, [
    'title' => $title,
    'image' => $image
]);

// パーツ内で受け取り
<?php
$title = $args['title'] ?? '';
$image = $args['image'] ?? null;
?>
```

## カスタム投稿タイプ

### 登録

```php
// inc/custom-post-types/job.php
function register_job_post_type() {
    register_post_type('job', [
        'labels' => [
            'name' => '求人情報',
            'singular_name' => '求人'
        ],
        'public' => true,
        'has_archive' => true,
        'supports' => ['title', 'editor', 'thumbnail'],
        'menu_icon' => 'dashicons-businessman'
    ]);
}
add_action('init', 'register_job_post_type');
```

## Enqueue（スタイル/スクリプト）

### 正しいフック使用

```php
// フロントエンド
add_action('wp_enqueue_scripts', 'theme_enqueue_assets');

// 管理画面
add_action('admin_enqueue_scripts', 'theme_admin_assets');

function theme_enqueue_assets() {
    // Vite統合を使用
    vite_enqueue_assets();
}
```

## 禁止事項

| 禁止項目 | 理由 | 代替 |
|---------|------|------|
| `<img>`直接記述 | レスポンシブ非対応 | `render_responsive_image()` |
| `the_field()` | エスケープなし | `get_field()` + `esc_*` |
| インラインスタイル | 保守性低下 | SCSSクラス |
| `p-page__section` | 再利用性低下 | 独立Block |
| PNG/JPGフォールバック | WebP専用 | `.webp` のみ使用 |
| `getimagesize()` でランタイム取得 | リクエスト毎のFS I/O | `images-meta.php` + opcache |

## ファイルパーミッション

Docker環境での必須設定:

```
PHP/CSS/JS: 644 (rw-r--r--)
ディレクトリ: 755 (rwxr-xr-x)
```

## チェックリスト

- [ ] Template Nameコメント記述
- [ ] セクションは独立Block
- [ ] 画像はrender_responsive_image()使用
- [ ] ACFフィールドは空チェック
- [ ] 出力はエスケープ済み
- [ ] テンプレートパーツで再利用
- [ ] パーミッション644/755
