# 新規ページ作成チェックリスト

このドキュメントは、新規ページを作成する際の手順とチェック項目をまとめたものです。

## ステップ1: SCSSファイル作成

- [ ] `src/scss/object/projects/[page]/_p-[Component].scss` を作成
- [ ] `src/css/pages/[page]/style.scss` を作成
- [ ] 必須インポートを追加（function, block, responsive）
- [ ] 共通コンポーネント（c-Breadcrumbs, p-PageHeader）をインポート
- [ ] FLOCSS命名規則（`.p-[page]__element`）を使用
- [ ] レスポンシブは **デフォルトPC、`@include sp`でオーバーライド**
- [ ] `rv()` / `svw()` 関数を使用

### SCSSファイル例

```scss
// src/css/pages/[page]/style.scss
@use "scss/foundation/function" as *;
@use "scss/foundation/mixins/block" as *;
@use "scss/foundation/mixins/responsive" as *;

@use "scss/object/components/c-Breadcrumbs";
@use "scss/object/projects/p-PageHeader";
@use "scss/object/projects/[page]/p-[Page]";
```

```scss
// src/scss/object/projects/[page]/_p-[Page].scss
@use "../../foundation/function" as *;
@use "../../foundation/mixins/block" as *;
@use "../../foundation/mixins/responsive" as *;

.p-[page] {
  &__container {
    @include container(1232px);
  }

  &__content {
    padding-block: rv(84);

    @include sp {
      padding-block: svw(60) svw(84);
    }
  }
}
```

## ステップ2: WordPressテンプレート作成

- [ ] `themes/{{THEME_NAME}}/pages/page-[slug].php` を作成
- [ ] Template Nameコメントを追加
- [ ] `<main class="p-[page-class]">` でラップ
- [ ] 下層ページは `page-header` コンポーネントを使用
- [ ] パンくず配列を定義
- [ ] 画像出力は `render_responsive_image()` を使用

### テンプレート例

```php
<?php
/**
 * Template Name: ページ名
 */

get_header();

$breadcrumbs = array(
  array('href' => '/page-url/', 'label' => 'ページ名')
);
?>

<main class="p-[page]">
  <?php
  get_template_part('template-parts/common/page-header', null, array(
    'breadcrumbs' => $breadcrumbs,
    'ja_label' => '日本語ラベル',
    'en_heading' => 'English Heading'
  ));
  ?>

  <div class="p-[page]__content">
    <div class="p-[page]__container">
      <!-- コンテンツ -->
    </div>
  </div>
</main>

<?php get_footer(); ?>
```

## ステップ3: ビルド設定更新

- [ ] `vite.config.js` の `input` に追加
  - `"style-[page-slug]": path.resolve(__dirname, "src/css/pages/[page-slug]/style.scss")`
- [ ] 特殊条件が必要な場合のみ `enqueue.php` を更新

### vite.config.js例

```javascript
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        // 既存エントリー
        "style-top": path.resolve(__dirname, "src/css/pages/top/style.scss"),

        // 🆕 新規ページ追加
        "style-[page-slug]": path.resolve(__dirname, "src/css/pages/[page-slug]/style.scss"),
      }
    }
  }
});
```

## ステップ4: 動作確認

- [ ] `npm run dev` でスタイルが適用されるか確認
- [ ] レスポンシブ表示を確認（SP/PC）
- [ ] `npm run build` で本番ビルド
- [ ] 生成ファイルを確認: `themes/{{THEME_NAME}}/assets/css/style-[page].css`

### 確認コマンド

```bash
# 開発サーバー起動
npm run dev

# 本番ビルド
npm run build

# 生成ファイル確認
ls -lh themes/{{THEME_NAME}}/assets/css/style-[page-slug].css
```

## ステップ5: 規約準拠確認（最終チェック）

### SCSS設計規約

- [ ] エントリーポイント（`src/css/pages/[page]/style.scss`）に直接スタイルを書いていないか
- [ ] すべてのコンテナ幅で `__container` + `@include container` を使用しているか
- [ ] 手動幅制御（`max-width + margin: auto`）が残っていないか
- [ ] `padding-inline` での幅制御が残っていないか
- [ ] FLOCSS + BEM命名規則が守られているか（`.p-[page]__element`）
- [ ] **ケバブケース（kebab-case）のみ使用**（キャメルケース禁止）
- [ ] **`&-`ネスト記法を使用していないか**（絶対禁止）
- [ ] `@include pc` と `@include sp` の併用がないか
- [ ] デフォルト = PC、`@include sp` でSP用オーバーライドになっているか
- [ ] `rv()` / `svw()` 関数を適切に使用しているか
- [ ] ベーススタイル（font-size: rv(16) 等）を重複して書いていないか

### WordPress連携規約

- [ ] Template Name コメントが存在するか（WordPressテンプレートファイル冒頭）
- [ ] `<main class="p-[page-class]">` でラップされているか
- [ ] パンくずリスト、PageHeaderコンポーネントが正しく実装されているか
- [ ] 画像出力に `render_responsive_image()` を使用しているか
- [ ] ACFフィールドの存在チェックをしているか（`if ($field):`）

### ビルド設定規約

- [ ] `vite.config.js` に `"style-[page-slug]"` エントリーポイントを追加したか
- [ ] `npm run build` でエラーが出ないか
- [ ] `themes/{{THEME_NAME}}/assets/css/style-[page].css` が生成されているか

### 動作確認

- [ ] 開発環境（`npm run dev`）でスタイルが適用されるか
- [ ] 本番ビルド後もスタイルが適用されるか
- [ ] レスポンシブ表示（SP/PC）が正しく動作するか
- [ ] ブレークポイント前後（特に768px付近）で空白やスタイル適用漏れがないか
- [ ] ファーストビュー画像に `loading="eager"` を設定しているか
- [ ] スクロール後の画像に `loading="lazy"` を設定しているか

## クイックチェックポイント

新規ページ作成時に特に注意すべき点：

1. **vite.config.js更新を忘れない** - これを忘れると本番で動かない
2. **`&-`ネスト記法を使わない** - すべてのElementをBlock直下に定義
3. **ケバブケースを厳守** - キャメルケース・パスカルケースは禁止
4. **デフォルトPC、spでオーバーライド** - `@include pc`と`@include sp`の併用禁止
5. **画像は`render_responsive_image()`を使用** - 直接`<img>`タグ禁止
6. **ベーススタイル重複禁止** - `font-size: rv(16)` 等は不要

## トラブルシューティング

### スタイルが反映されない

**原因と対策:**
- vite.config.jsにエントリー追加したか？ → 追加して再ビルド
- `npm run build`を実行したか？ → 実行する
- CSSファイルが生成されているか？ → `ls themes/{{THEME_NAME}}/assets/css/` で確認

### ビルドエラーが出る

**原因と対策:**
- SCSSのimportパスが正しいか？ → パスを確認
- `@use`で名前空間を使っているか？ → `@use ... as *` を確認
- ファイル名が正しいか？ → スペルミス、アンダースコアの有無を確認

### 768px前後で表示が崩れる

**原因と対策:**
- `@include pc`と`@include sp`を併用していないか？ → 削除してデフォルトPCに
- デフォルトスタイルを書いているか？ → メディアクエリなしでPC用を記述
