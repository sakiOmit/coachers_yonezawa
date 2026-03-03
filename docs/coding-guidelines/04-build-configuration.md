# ビルド設定規約

このドキュメントは、Viteビルド設定とWordPress CSS/JS読み込みの規約をまとめたものです。

## vite.config.js エントリーポイント追加

### 新規ページ追加時

```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        // 🆕 新規ページ追加
        "style-[page-slug]": path.resolve(__dirname, "src/css/pages/[page-slug]/style.scss"),

        // ページ別JS（必要な場合のみ）
        "page-[page-slug]": path.resolve(__dirname, "src/js/pages/[page-slug]/index.js"),
      }
    }
  }
});
```

### 命名規則

- **CSS**: `style-[page-slug]` → 出力: `css/style-[page-slug].css`
- **JS**: `page-[page-slug]` → 出力: `js/page-[page-slug].js`

## ⚠️ 重要: vite.config.js更新を忘れずに

新規ページのSCSSファイルを作成した後、**必ずvite.config.jsにエントリーポイントを追加してください。**

### これを忘れると

- ❌ 開発環境では動作するが、本番環境でCSSが読み込まれない
- ❌ `npm run build` でCSSファイルが生成されない
- ❌ WordPress側でスタイルが適用されない（致命的な問題）

### チェック方法

```bash
# 本番ビルド後に生成ファイルを確認
npm run build
ls themes/{{THEME_NAME}}/assets/css/style-[page-slug].css
```

### よくあるミス

1. SCSSファイルは作成したが、vite.config.jsを更新し忘れる
2. エントリー名を間違える（`style-news` のはずが `news-style` など）
3. パスが間違っている（`src/css/pages/news/` のはずが `src/scss/pages/news/` など）

## enqueue.php 読み込み設定

### 基本方針

固定ページは `$post->post_name` で自動対応します。**特殊な条件が必要な場合のみ追加してください。**

### 特殊条件が必要な例

```php
// themes/{{THEME_NAME}}/inc/enqueue.php

// 開発環境
function main_themeenqueue_page_assets_dev($vite_dev_server) {
  $page_slug = '';

  if (is_front_page()) {
    $page_slug = 'top';
  } elseif (is_404()) {
    $page_slug = 'notfound';  // 開発環境では notfound
  } elseif (is_post_type_archive('tvcm')) {
    $page_slug = 'gallery';  // 🆕 カスタム投稿タイプ用
  } elseif (is_page()) {
    global $post;
    $page_slug = $post->post_name;  // 通常ページは自動
  }

  // CSS読み込み
  if ($page_slug) {
    echo '<script type="module" src="' . esc_url($vite_dev_server . '/src/css/pages/' . $page_slug . '/style.scss') . '"></script>';
  }
}

// 本番環境
function main_themeenqueue_page_assets() {
  $page_slug = '';

  if (is_front_page()) {
    $page_slug = 'top';
  } elseif (is_404()) {
    $page_slug = '404';  // 本番環境では 404
  } elseif (is_post_type_archive('tvcm')) {
    $page_slug = 'gallery';
  } elseif (is_page()) {
    global $post;
    $page_slug = $post->post_name;
  }

  // CSS読み込み
  if ($page_slug) {
    $manifest = get_template_directory() . '/assets/.vite/manifest.json';
    // ...
  }
}
```

### 重要な注意点

1. **404ページのスラッグが環境で異なる**
   - 開発環境: `notfound`
   - 本番環境: `404`

2. **カスタム投稿タイプは手動マッピングが必要**
   - `is_post_type_archive('tvcm')` → `gallery`

3. **固定ページは自動対応**
   - `is_page()` → `$post->post_name` で自動取得

## 本番ビルド確認手順

新規ページ追加後、必ず以下の手順で確認してください。

### ステップ1: ビルド実行

```bash
npm run build
```

### ステップ2: 生成ファイル確認

```bash
# CSSファイルが生成されているか確認
ls -lh themes/{{THEME_NAME}}/assets/css/style-[page-slug].css

# JSファイル（必要な場合のみ）
ls -lh themes/{{THEME_NAME}}/assets/js/page-[page-slug].js
```

### ステップ3: manifestファイル確認

```bash
# manifestファイルにエントリーが含まれているか確認
cat themes/{{THEME_NAME}}/assets/.vite/manifest.json | grep "style-[page-slug]"
```

### ステップ4: WordPressで動作確認

1. 本番ビルドモードでWordPressにアクセス
2. 該当ページを表示
3. ブラウザ開発ツールでCSSが読み込まれているか確認

## トラブルシューティング

### CSSが生成されない

**原因:**
- vite.config.jsにエントリーポイントが追加されていない
- ファイルパスが間違っている

**解決策:**
```bash
# vite.config.jsを確認
cat vite.config.js | grep "style-[page-slug]"

# SCSSファイルが存在するか確認
ls -l src/css/pages/[page-slug]/style.scss
```

### 開発環境では動くが本番で動かない

**原因:**
- `npm run build` を実行していない
- enqueue.phpの条件分岐が正しくない

**解決策:**
```bash
# 必ずビルドを実行
npm run build

# enqueue.phpのページ判定ロジックを確認
```

### スタイルが全く適用されない

**原因:**
- WordPress側でCSSが読み込まれていない
- enqueue.phpのページスラッグが一致していない

**解決策:**
```php
// デバッグ用コードを一時的に追加
function main_themeenqueue_page_assets_dev($vite_dev_server) {
  $page_slug = '';

  // ... (条件分岐)

  // デバッグ出力
  error_log('Page slug: ' . $page_slug);
}
```

## ビルド設定チェックリスト

新規ページ追加時は以下を確認：

- [ ] `vite.config.js` に `style-[page-slug]` エントリーを追加した
- [ ] エントリー名が `style-`プレフィックス付きになっている
- [ ] パスが `src/css/pages/[page-slug]/style.scss` で正しい
- [ ] `npm run build` を実行した
- [ ] `themes/{{THEME_NAME}}/assets/css/style-[page-slug].css` が生成された
- [ ] カスタム投稿タイプなど特殊条件の場合、`enqueue.php` を更新した
- [ ] 開発環境と本番環境の両方で動作確認した
