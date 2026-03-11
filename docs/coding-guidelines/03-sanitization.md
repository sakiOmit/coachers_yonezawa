# HTML出力サニタイズ規約

このドキュメントは、WordPressテーマにおけるHTML出力のサニタイズ規約を定義します。

**SSOT**: `.claude/rules/security.md`（XSS対策の基本原則）

## エスケープ関数の使い分け（必須）

| フィールドタイプ | 関数 | 用途 |
|----------------|------|------|
| **WYSIWYG** | `wp_kses_post()` | HTMLタグを許可しつつ危険なタグを除去 |
| **テキストエリア（HTML含む）** | `wp_kses_post()` | `<br>`等のHTMLを含む場合 |
| **テキストエリア（プレーン）** | `esc_html()` + `nl2br()` | 改行のみ変換する場合 |
| **テキスト（単行）** | `esc_html()` | HTMLタグを許可しない |
| **URL** | `esc_url()` | リンク先URL |
| **属性値** | `esc_attr()` | HTML属性値（class, id等） |
| **メールアドレス** | `sanitize_email()` | メールアドレス |

## 実装パターン

### WYSIWYGフィールド

```php
// ✅ GOOD: wp_kses_postでサニタイズ
<?php echo wp_kses_post($wysiwyg_content); ?>

// ❌ BAD: 直接出力（XSS脆弱性の可能性）
<?php echo $wysiwyg_content; ?>
```

### テキストエリア（HTML含む）

```php
// ✅ GOOD: brタグ等を含む場合
<?php echo wp_kses_post($textarea_with_html); ?>

// ✅ GOOD: ヘルパー関数との組み合わせ
<?php echo wp_kses_post(get_acf_field_with_fallback('field_name', 'デフォルト<br>テキスト', $page_id)); ?>
```

### テキスト・URL・属性値

```php
// ✅ GOOD: 単行テキスト
<?php echo esc_html($text_field); ?>

// ✅ GOOD: 属性値として使用
<div class="<?php echo esc_attr($class_name); ?>">

// ✅ GOOD: URL
<a href="<?php echo esc_url($link_url); ?>">
```

## 禁止パターン

```php
// ❌ BAD: ACFフィールドを直接出力
<?php echo get_field('wysiwyg_field'); ?>

// ❌ BAD: 変数を直接出力
<?php echo $content; ?>

// ❌ BAD: the_field()の使用（エスケープなし）
<?php the_field('wysiwyg_field'); ?>
```

## チェックリスト

- [ ] すべての出力に適切なエスケープ関数を使用しているか
- [ ] `wp_kses_post()` でHTML出力をサニタイズしているか
- [ ] `the_field()` を使用していないか（`get_field()` + エスケープを推奨）
- [ ] フォールバック値もHTMLを含む場合は `wp_kses_post()` を使用しているか
- [ ] URL出力に `esc_url()` を使用しているか
