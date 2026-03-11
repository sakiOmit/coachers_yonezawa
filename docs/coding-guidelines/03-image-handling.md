# 画像出力規約

このドキュメントは、WordPressテーマにおける画像出力の規約を定義します。

**SSOT**: `.claude/rules/wordpress.md`（render_responsive_image の基本原則）

## 画像ソースによる使い分け（必須）

| 画像ソース | 使用関数 | 理由 |
|-----------|---------|------|
| **テーマ静的画像** (`/assets/images/`) | `render_responsive_image()` | ビルドプロセスでWebP・Retina対応済み |
| **WordPress投稿サムネイル** | `the_post_thumbnail()` | WordPress標準の画像最適化を活用 |
| **ACFアップロード画像** (Media Library) | `wp_get_attachment_image()` | WordPress標準の画像最適化を活用 |
| **ACF PC/SP別画像グループ** | `render_responsive_image(['acf_field' => ...])` | テーマ静的画像と同じ扱い |
| **noimage等のフォールバック** | `render_responsive_image()` | テーマ静的画像と同じ扱い |

**重要原則:**
- **テーマ静的画像**: `render_responsive_image()` のみ使用可能
- **WordPressアップロード画像**: `render_responsive_image()` 使用禁止（@2x.webpが存在せず404エラー）

## 禁止パターン

```php
// ❌ BAD: WordPressアップロード画像にrender_responsive_image()を使用
$thumbnail_url = get_the_post_thumbnail_url(get_the_ID(), 'large');
render_responsive_image([
  'src' => $thumbnail_url,  // ← /wp-content/uploads/の画像は@2x.webpが存在しない
  'alt' => 'サムネイル',
]);

// ❌ BAD: 直接imgタグを記述
<img src="<?php echo get_template_directory_uri(); ?>/assets/images/example.png" alt="説明">
```

## 正しいパターン

### 1. テーマ静的画像

```php
<?php
render_responsive_image([
  'src' => get_template_directory_uri() . '/assets/images/hero.png',
  'alt' => 'ヒーロー画像',
  'class' => 'p-page__hero-image',
  'loading' => 'eager'
]);
?>
```

### 2. WordPress投稿サムネイル

```php
<?php if ( has_post_thumbnail() ) :
  the_post_thumbnail('large', [
    'class' => 'p-single__thumbnail-image',
    'loading' => 'eager',
  ]);
endif; ?>
```

### 3. ACFアップロード画像（Media Library）

```php
<?php
$thumbnail_id = $brand['thumbnail_id'] ?? 0;
if ( $thumbnail_id ) :
  echo wp_get_attachment_image($thumbnail_id, 'full', false, [
    'alt' => $brand_name,
    'loading' => 'lazy',
  ]);
endif;
?>
```

### 4. ACF PC/SP別画像グループ

```php
<?php
render_responsive_image([
  'acf_field' => 'hero_image',  // ['pc' => image, 'sp' => image]形式
  'alt' => 'ヒーロー画像',
  'class' => 'p-kv__image',
  'loading' => 'eager'
]);
?>
```

### 5. フォールバック画像

```php
<?php if ( has_post_thumbnail() ) :
  the_post_thumbnail('medium', ['class' => 'p-topics__item-image']);
else :
  render_responsive_image([
    'src' => get_template_directory_uri() . '/assets/images/common/noimage.png',
    'alt' => 'No Image',
    'class' => 'p-topics__item-image',
    'sp' => false,
  ]);
endif; ?>
```

## render_responsive_image() リファレンス

**ファイル:** `themes/{{THEME_NAME}}/inc/helpers/image-helpers.php`

| 引数 | 型 | 説明 | デフォルト |
|------|-----|------|-----------|
| `src` | string | 画像パス | '' |
| `sp` | bool | SP別画像を使用するか | true |
| `alt` | string | alt属性 | '' |
| `class` | string | img要素のclass | なし |
| `wrapper_class` | string | picture要素のclass | なし |
| `loading` | string | 'lazy' / 'eager' | 'lazy' |
| `width` | int | width属性（メタデータから自動取得可能） | null |
| `height` | int | height属性（メタデータから自動取得可能） | null |
| `breakpoint` | int | SP/PC切り替えブレークポイント | 767 |
| `acf_field` | string | ACF画像フィールド名 | なし |

## loading属性の使い分け

| 用途 | loading値 | 理由 |
|------|-----------|------|
| ファーストビュー画像 | `eager` | LCPスコア向上 |
| スクロール後の画像 | `lazy` | 初期ロード高速化 |
| ロゴ | `eager` | すぐに表示が必要 |

## 例外ケース

以下の場合のみ直接`<img>`タグ使用可能：

```php
// SVG画像
<img src="<?php echo get_template_directory_uri(); ?>/assets/images/icon.svg" alt="アイコン">

// 外部URL画像
<img src="https://cdn.example.com/image.jpg" alt="外部画像" loading="lazy">
```

## チェックリスト

- [ ] 画像ソースを確認（`/assets/images/` or `/wp-content/uploads/`）
- [ ] 関数選択が正しいか
- [ ] WPアップロード画像に`render_responsive_image()`を使っていないか
- [ ] `loading` 属性を適切に設定（lazy/eager）
- [ ] `alt` 属性を設定（アクセシビリティ）
- [ ] BEM命名規則の `class` 属性
- [ ] 存在チェック（`has_post_thumbnail()`, `if ($thumbnail_id)` 等）
- [ ] ファーストビュー画像は `loading="eager"`
