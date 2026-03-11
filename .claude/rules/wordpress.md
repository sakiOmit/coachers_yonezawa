---
globs: ["*.php", "themes/**"]
---

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

## ACFオプションページ（PRO不要）

ACF PROの `acf_add_options_page()` は有料プラン限定。
無料版ACFでも以下の方法でオプションページを実現できる。

### 仕組み

1. `add_menu_page()` で管理画面にページ追加
2. ACF無料版の内部関数でフィールドを描画・保存
3. `get_field('key', 'options')` で値を取得

### 実装ファイル構成

```
inc/
├── options-page.php              # オプションページ本体（共通テンプレート）
├── helpers/acf-helpers.php       # get_acf_or_default() ラッパー
└── advanced-custom-fields/
    └── groups/options/           # オプションページ用フィールドグループ
```

### オプションページ本体（共通テンプレート）

```php
// inc/options-page.php

function {{PREFIX}}_add_options_page() {
    add_menu_page(
        'サイト設定',
        'サイト設定',
        'manage_options',
        'site-settings',
        '{{PREFIX}}_render_settings_page',
        'dashicons-admin-settings',
        60
    );
}
add_action( 'admin_menu', '{{PREFIX}}_add_options_page' );

function {{PREFIX}}_render_settings_page() {
    {{PREFIX}}_render_options_page_template( 'group_site_settings' );
}

/**
 * 共通レンダリングテンプレート
 * フィールドグループキーを渡すだけで別ページにも使い回せる
 */
function {{PREFIX}}_render_options_page_template( $field_group_key ) {
    if ( ! current_user_can( 'manage_options' ) ) {
        return;
    }

    // 保存処理
    if ( isset( $_POST['acf'], $_POST['_acfnonce'] ) ) {
        if ( wp_verify_nonce( $_POST['_acfnonce'], 'acf_form' ) ) {
            if ( function_exists( 'acf_save_post' ) ) {
                acf_save_post( 'options' );
                echo '<div class="notice notice-success is-dismissible"><p>設定を保存しました。</p></div>';
            }
        }
    }

    if ( ! function_exists( 'acf_get_fields' ) ) {
        echo '<div class="wrap"><div class="notice notice-error"><p>ACFプラグインが有効化されていません。</p></div></div>';
        return;
    }

    $field_group = acf_get_local_field_group( $field_group_key );
    if ( ! $field_group ) {
        echo '<div class="wrap"><div class="notice notice-error"><p>フィールドグループが見つかりません。</p></div></div>';
        return;
    }

    $fields = acf_get_fields( $field_group_key );
    if ( ! $fields ) {
        echo '<div class="wrap"><div class="notice notice-error"><p>フィールドが見つかりません。</p></div></div>';
        return;
    }
    ?>
    <div class="wrap">
        <h1><?php echo esc_html( get_admin_page_title() ); ?></h1>
        <form method="post" action="">
            <?php
            wp_nonce_field( 'acf_form', '_acfnonce' );
            echo '<div class="acf-fields acf-form-fields -top">';
            foreach ( $fields as $field ) {
                $field['value'] = acf_get_value( 'options', $field );
                acf_render_field_wrap( $field );
            }
            echo '</div>';
            ?>
            <div class="acf-form-submit">
                <input type="submit" class="acf-button button button-primary button-large" value="設定を保存">
            </div>
        </form>
    </div>
    <?php
}
```

### ACFスクリプト読み込み（必須）

```php
// acf_form_head + acf_enqueue_scripts を該当ページでのみ読み込む
function {{PREFIX}}_acf_form_head_on_load() {
    if ( function_exists( 'acf_form_head' ) ) {
        acf_form_head();
    }
    do_action( 'add_meta_boxes', 'acf_options_page', null );
}
add_action( 'load-toplevel_page_site-settings', '{{PREFIX}}_acf_form_head_on_load' );

function {{PREFIX}}_acf_enqueue_scripts() {
    $screen = get_current_screen();
    if ( $screen && $screen->id === 'toplevel_page_site-settings' ) {
        wp_enqueue_media();
        acf_enqueue_scripts();
    }
}
add_action( 'admin_enqueue_scripts', '{{PREFIX}}_acf_enqueue_scripts' );
```

### ACFヘルパー

```php
// inc/helpers/acf-helpers.php

/**
 * ACFフィールド取得（ACF無効時はデフォルト値を返す）
 */
function get_acf_or_default( $field_name, $default = '', $post_id = null ) {
    if ( ! function_exists( 'get_field' ) ) {
        return $default;
    }
    $value = get_field( $field_name, $post_id );
    return ( $value !== null && $value !== '' && $value !== false ) ? $value : $default;
}
```

### ページ追加の拡張

新しいオプションページを追加する場合:

1. `add_menu_page()` / `add_submenu_page()` でページ追加
2. コールバックで `{{PREFIX}}_render_options_page_template('group_xxx')` を呼ぶ
3. 対応するACFフィールドグループをPHPで登録
4. `load-*` フックに `acf_form_head` を追加

### 使用する ACF 内部関数

| 関数 | 用途 |
|------|------|
| `acf_get_local_field_group()` | PHPコード登録済みフィールドグループ取得 |
| `acf_get_fields()` | フィールド一覧取得 |
| `acf_get_value()` | 保存値取得 |
| `acf_render_field()` | フィールドHTML描画 |
| `acf_save_post()` | `'options'` を渡してオプション保存 |
| `acf_form_head()` | フォーム処理の初期化 |
| `acf_enqueue_scripts()` | ACF用CSS/JS読み込み |

## チェックリスト

- [ ] Template Nameコメント記述
- [ ] セクションは独立Block
- [ ] 画像はrender_responsive_image()使用
- [ ] ACFフィールドは空チェック
- [ ] 出力はエスケープ済み
- [ ] テンプレートパーツで再利用
- [ ] パーミッション644/755
- [ ] オプションページはACF PRO不要の自前実装を使用
