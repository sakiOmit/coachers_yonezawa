# Astro → WordPress Conversion Patterns

## Props → PHP Args

| Astro | WordPress PHP |
|-------|---------------|
| `const { title, description } = Astro.props` | `$args = validate_template_args($args, [...])` |
| camelCase | snake_case |
| TypeScript interface | PHP $defaults array |

### 変換例

```
// Astro (camelCase)          // PHP (snake_case)
interface Props {
  enHeading: string;     →    'en_heading' => '',
  jaLabel?: string;      →    'ja_label' => '',
  modifierClass?: string; →   'modifier_class' => '',
  isTall?: boolean;      →    'is_tall' => false,
}
```

## Template Syntax

| Astro | WordPress PHP |
|-------|---------------|
| `{text}` | `<?php echo esc_html($text); ?>` |
| `{url}` | `<?php echo esc_url($url); ?>` |
| `set:html={html}` | `<?php echo wp_kses_post($html); ?>` |
| `{items.map(item => ...)}` | `<?php while(have_rows('items')): the_row(); ... endwhile; ?>` |
| `<ResponsiveImage src="..." />` | `<?php render_responsive_image($image_id); ?>` |
| `import Component` | `<?php get_template_part('template-parts/...'); ?>` |
| `<Component prop={value} />` | `get_template_part('...', null, ['prop' => $value])` |
| `import data from '../data/...'` | `get_field('field')` / `get_acf_or_default(...)` |
| `{condition && <div>...</div>}` | `<?php if ($cond): ?><div>...</div><?php endif; ?>` |
| Astro `Props` interface | `validate_template_args()` + `merge_template_defaults()` |
| `import '@root-src/css/...'` | `vite_enqueue_page_style()` in enqueue.php |

## ACF Field Mapping

| フィールドタイプ | 取得方法 | エスケープ |
|----------------|---------|-----------|
| テキスト | `get_field('field_name')` | `esc_html()` |
| URL | `get_field('field_name')` | `esc_url()` |
| 画像 | `get_field('field_name')` (returns ID) | `render_responsive_image()` |
| リピーター | `have_rows()` + `the_row()` + `get_sub_field()` | 各フィールドに応じて |
| WYSIWYG | `get_field('field_name')` | `wp_kses_post()` |
| 真偽値 | `get_field('field_name')` | 不要（bool） |
| セレクト | `get_field('field_name')` | `esc_attr()` |

## 必須PHP処理

### Template Name コメント

```php
<?php
/**
 * Template Name: ページ名
 * @package Theme
 */
```

### validate_template_args パターン

```php
if (!validate_template_args($args, ['en_heading', 'breadcrumbs'], 'page-header')) {
    return;
}
```

### merge_template_defaults パターン

```php
$args = merge_template_defaults($args, [
    'en_heading' => '',
    'ja_label' => '',
]);
```

### エスケープルール

- テキスト出力: `esc_html()`
- URL: `esc_url()`
- HTML属性: `esc_attr()`
- リッチテキスト: `wp_kses_post()`
- JS内データ: `esc_js()` or `wp_json_encode()`

### ACF 空チェックパターン

```php
<?php if ($title = get_field('title')): ?>
  <h2><?php echo esc_html($title); ?></h2>
<?php endif; ?>
```

### 禁止事項

- `the_field()` は使用禁止 → `get_field()` + エスケープ関数を使用すること
