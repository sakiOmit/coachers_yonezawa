# Security Rules

## Overview

このルールファイルは、WordPress開発におけるセキュリティ対策を定義します。
OWASP Top 10を基準とし、特にXSS、SQLインジェクション、CSRF対策を重視します。

## XSS（クロスサイトスクリプティング）対策

### 出力エスケープ（必須）

WordPress の出力関数を使用:

```php
// ✅ 正しい
echo esc_html($text);           // HTMLコンテキスト
echo esc_attr($attribute);      // HTML属性
echo esc_url($url);             // URL
echo esc_js($javascript);       // JavaScript内

// ❌ 禁止
echo $text;                     // エスケープなし
echo $_GET['param'];            // 直接出力
```

### WordPress翻訳関数との組み合わせ

```php
// ✅ 正しい
esc_html_e('Text', 'theme-domain');
echo esc_html__('Text', 'theme-domain');

// ❌ 禁止
_e('Text', 'theme-domain');     // エスケープなし
```

### ACFフィールドの出力

```php
// ✅ 正しい
echo esc_html(get_field('text_field'));
echo esc_url(get_field('url_field'));
echo wp_kses_post(get_field('wysiwyg_field'));

// ❌ 禁止
echo get_field('text_field');   // エスケープなし
the_field('text_field');        // the_field()は非推奨
```

## SQLインジェクション対策

### $wpdb使用時の必須事項

```php
// ✅ 正しい - prepare()使用
$results = $wpdb->get_results(
    $wpdb->prepare(
        "SELECT * FROM {$wpdb->posts} WHERE post_type = %s AND post_status = %s",
        $post_type,
        'publish'
    )
);

// ❌ 禁止 - 直接変数埋め込み
$results = $wpdb->get_results(
    "SELECT * FROM {$wpdb->posts} WHERE post_type = '{$post_type}'"
);
```

### WP_Queryの使用（推奨）

```php
// ✅ 推奨 - WP_Queryは内部でサニタイズ
$query = new WP_Query([
    'post_type' => 'job',
    'meta_key' => 'salary',
    'orderby' => 'meta_value_num'
]);
```

## CSRF対策

### Nonce検証（フォーム処理時必須）

```php
// フォーム生成時
wp_nonce_field('action_name', 'nonce_field_name');

// 検証時
if (!wp_verify_nonce($_POST['nonce_field_name'], 'action_name')) {
    wp_die('Security check failed');
}
```

### AJAX処理時

```php
// JavaScript側
$.ajax({
    url: ajaxurl,
    data: {
        action: 'my_action',
        nonce: my_vars.nonce  // wp_localize_scriptで渡す
    }
});

// PHP側
add_action('wp_ajax_my_action', function() {
    check_ajax_referer('my_nonce_action', 'nonce');
    // 処理
});
```

## 入力サニタイズ

### 用途別サニタイズ関数

```php
sanitize_text_field()      // テキスト入力
sanitize_email()           // メールアドレス
sanitize_file_name()       // ファイル名
absint()                   // 正の整数
wp_kses_post()             // HTMLコンテンツ（投稿許可タグのみ）
```

## ファイルアップロード

### 安全なファイル処理

```php
// ✅ 正しい - WordPress関数使用
$upload = wp_handle_upload($file, ['test_form' => false]);

// ファイルタイプ検証
$filetype = wp_check_filetype($filename);
if (!$filetype['ext']) {
    wp_die('Invalid file type');
}
```

## 禁止事項

| 禁止項目 | 理由 |
|---------|------|
| `eval()` | コードインジェクションリスク |
| `extract()` | 変数汚染リスク |
| `$_GET/$_POST`直接出力 | XSSリスク |
| `mysql_*`関数 | 非推奨・$wpdb使用 |
| ファイルパス直接連結 | パストラバーサルリスク |

## デバッグコード（本番禁止）

以下は開発時のみ使用し、本番環境では必ず削除:

```php
// PHP
var_dump()
print_r()
dd()
error_log() // 開発用

// JavaScript
console.log()
console.warn()
console.error()
debugger
```

**注意**: `debug-code-detector.py` フックがこれらを自動検出します。

## チェックリスト

コードレビュー時に確認:

- [ ] すべての出力がエスケープされている
- [ ] ユーザー入力がサニタイズされている
- [ ] SQLクエリで$wpdb->prepare()を使用
- [ ] フォームにnonce検証がある
- [ ] デバッグコードが削除されている
- [ ] ファイルアップロードの検証がある
