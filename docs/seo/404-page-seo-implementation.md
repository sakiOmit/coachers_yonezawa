# 404ページ SEO設定実装ドキュメント

## 概要

All in One SEO (AIOSEO) v4.9.1.1 を使用した WordPress サイトで、404ページのSEOメタ情報（タイトル・ディスクリプション）をカスタマイズする実装。

## 問題の背景

### AIOSEO v4の404ページハンドリング

AIOSEO v4では、404ページのタイトル・ディスクリプションが**デフォルトで空文字**となります。

**コード調査結果:**
- `/app/Common/Meta/Title.php` の `getTitle()` メソッド
- `/app/Common/Meta/Description.php` の `getDescription()` メソッド

上記メソッドでは `is_404()` の条件分岐が存在せず、404ページでは空文字 `''` を返します。

### 従来の実装の問題点

```php
// これは機能しない
add_filter('aioseo_title', 'custom_404_seo_title');
add_filter('aioseo_description', 'custom_404_seo_description');
```

理由: `aioseo_title` / `aioseo_description` というフィルターフックは AIOSEO v4 には存在しません。

## 正しい実装方法

### 実装ファイル

`/themes/{{THEME_NAME}}/inc/seo.php`

### 実装内容

#### 1. タイトルのカスタマイズ

```php
function jll_custom_404_seo_title($title)
{
    if (is_404()) {
        return 'ページが見つかりません｜日本ライフライン';
    }
    return $title;
}
add_filter('pre_get_document_title', 'jll_custom_404_seo_title', 100000);
```

**ポイント:**
- フック: `pre_get_document_title` (WordPress標準)
- 優先度: `100000` (AIOSEO の `99999` より後に実行)
- AIOSEO のフィルター処理: `/app/Common/Main/Head.php` の `registerTitleHooks()` で登録

#### 2. メタディスクリプションのカスタマイズ

```php
function jll_custom_404_meta_description()
{
    if (!is_404()) {
        return;
    }

    $description = 'お探しのページは見つかりません。URLをご確認いただくか、トップページへお戻りください。日本ライフライン採用サイト。';
    echo '<meta name="description" content="' . esc_attr($description) . '" />' . "\n";
}
add_action('wp_head', 'jll_custom_404_meta_description', 1);
```

**ポイント:**
- アクション: `wp_head`
- 優先度: `1` (AIOSEO のメタタグ出力より前)
- 直接 `<meta>` タグを出力
- `esc_attr()` でサニタイズ必須

## 動作確認方法

### 1. 開発環境でのテスト

```bash
# Docker環境起動
docker compose up -d

# ブラウザで存在しないURLにアクセス
# 例: http://localhost:8000/this-page-does-not-exist
```

### 2. HTMLソースの確認

ブラウザで「ページのソースを表示」を開き、以下を確認:

```html
<head>
  <title>ページが見つかりません｜日本ライフライン</title>
  <meta name="description" content="お探しのページは見つかりません。URLをご確認いただくか、トップページへお戻りください。日本ライフライン採用サイト。" />

  <!-- All in One SEO のコメントが存在することも確認 -->
  <!-- All in One SEO 4.9.1.1 - aioseo.com -->
</head>
```

### 3. ブラウザ開発者ツールでの確認

#### Chrome / Edge / Firefox

1. F12で開発者ツールを開く
2. **Elements** (要素) タブを選択
3. `<head>` セクションを展開
4. `<title>` と `<meta name="description">` を確認

### 4. SEOツールでの確認

以下のツールで404ページをチェック:

- [Google Search Console](https://search.google.com/search-console) - URL検査ツール
- [Screaming Frog SEO Spider](https://www.screamingfrogseoseo.com/)
- [Ahrefs Site Audit](https://ahrefs.com/)

### 5. curlコマンドでの確認

```bash
# タイトルタグの確認
curl -s http://localhost:8000/non-existent-page | grep -i "<title>"

# メタディスクリプションの確認
curl -s http://localhost:8000/non-existent-page | grep -i 'meta name="description"'
```

期待される出力:

```html
<title>ページが見つかりません｜日本ライフライン</title>
<meta name="description" content="お探しのページは見つかりません。URLをご確認いただくか、トップページへお戻りください。日本ライフライン採用サイト。" />
```

## トラブルシューティング

### タイトルが反映されない場合

1. **キャッシュクリア**
   ```bash
   # WordPress オブジェクトキャッシュ
   wp cache flush

   # ブラウザのキャッシュもクリア
   ```

2. **テーマが title-tag をサポートしているか確認**
   ```php
   // functions.php で以下が呼ばれているか
   add_theme_support('title-tag');
   ```

3. **AIOSEO の設定確認**
   - WordPress管理画面 → All in One SEO → 検索の外観
   - 「Advanced Settings」で「Title Rewrites」が有効になっているか

### メタディスクリプションが重複する場合

AIOSEOが空でもメタタグを出力している可能性があります。

**対処法:**

```php
// wp_head の優先度を調整
add_action('wp_head', 'jll_custom_404_meta_description', 1); // より早く実行

// または、AIOSEO のメタタグを削除
add_filter('aioseo_description_tag', function($tag) {
    if (is_404()) {
        return ''; // 空にして AIOSEO の出力を抑制
    }
    return $tag;
});
```

### 404ページが表示されない場合

1. **パーマリンク設定の再保存**
   - WordPress管理画面 → 設定 → パーマリンク設定
   - 「変更を保存」をクリック

2. **404.php テンプレートが存在するか確認**
   ```bash
   ls -la themes/{{THEME_NAME}}/404.php
   ```

## 参考情報

### AIOSEO v4 関連ファイル

- メインクラス: `/app/AIOSEO.php`
- タイトル処理: `/app/Common/Meta/Title.php`
- ディスクリプション処理: `/app/Common/Meta/Description.php`
- Head出力: `/app/Common/Main/Head.php`
- フィルター登録: `registerTitleHooks()` @ Line 99-110

### WordPress フィルター優先度

| フィルター/アクション       | 優先度 | 処理内容                   |
| --------------------------- | ------ | -------------------------- |
| wp_head (AIOSEO)            | 1      | AIOSEO メタタグ出力開始    |
| pre_get_document_title (WP) | 10     | WordPress デフォルト       |
| pre_get_document_title (AI) | 99999  | AIOSEO タイトル処理        |
| pre_get_document_title (JL) | 100000 | 日本ライフライン カスタム  |

## 設定値

### タイトル
```
ページが見つかりません｜日本ライフライン
```

### ディスクリプション
```
お探しのページは見つかりません。URLをご確認いただくか、トップページへお戻りください。日本ライフライン採用サイト。
```

## 変更履歴

- 2025-12-15: 初版作成 - AIOSEO v4.9.1.1 対応実装
