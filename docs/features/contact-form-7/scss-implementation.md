# Contact Form 7 SCSS Implementation

## Overview

Contact Form 7のフォームに既存デザインを適用するため、プロジェクト専用のSCSSスタイルを実装しました。

## 実装内容

### 1. 既存コンポーネントの活用

以下のコンポーネントファイルが既に存在し、基本的なフォームスタイルを提供しています：

- **`src/scss/object/components/form/_c-Form.scss`** - フォームベーススタイル
- **`src/scss/object/components/form/_c-FormLabel.scss`** - ラベルスタイル（`.c-label`, `.c-label__text`, `.c-label__required`）
- **`src/scss/object/components/form/_c-FormInput.scss`** - テキスト入力フィールド（`.c-input`）
- **`src/scss/object/components/form/_c-FormSelect.scss`** - セレクトボックス（`.c-select`）
- **`src/scss/object/components/form/_c-FormTextarea.scss`** - テキストエリア（`.c-textarea`）
- **`src/scss/object/components/form/_c-FormCheckbox.scss`** - チェックボックス（`.c-checkbox`）
- **`src/scss/object/components/form/_c-FormSubmit.scss`** - 送信ボタン（`.c-submit`）

これらのコンポーネントは `src/css/pages/contact/style.scss` で既にインポート済みです。

### 2. CF7専用スタイルの追加

`src/scss/object/projects/contact/_p-contact.scss` に以下のCF7専用スタイルを追加：

#### A. フォーム制御要素

```scss
.wpcf7-form {
  // CF7がspan.wpcf7-form-control-wrapで包むため、幅を100%に
  .wpcf7-form-control-wrap {
    display: block;
    width: 100%;
  }

  // select要素のラッパー調整
  .c-select {
    display: block;
    width: 100%;
  }
}
```

#### B. バリデーションエラー

```scss
// エラー時の赤枠
.wpcf7-not-valid {
  border-color: var(--color-primary) !important;
}

// エラーメッセージ
.wpcf7-not-valid-tip {
  display: block;
  margin-top: rv(8);
  font-size: rv(14);
  color: var(--color-primary);
}
```

#### C. 送信ボタン

```scss
.c-submit__button,
input[type="submit"] {
  display: block;
  width: auto;
  padding: rv(5) rv(60);
  font-size: rv(20);
  color: var(--color-white);
  background: var(--color-text);
  border-radius: 40px;
  // ...
}
```

#### D. レスポンスメッセージ

```scss
.wpcf7-response-output {
  margin: rv(20) 0;
  padding: rv(15) rv(20);
  text-align: center;
  border-radius: 5px;

  // 成功メッセージ（緑）
  &.wpcf7-mail-sent-ok {
    color: #155724;
    background-color: #d4edda;
  }

  // エラーメッセージ（赤）
  &.wpcf7-mail-sent-ng,
  &.wpcf7-spam-blocked {
    color: #721c24;
    background-color: #f8d7da;
  }

  // バリデーションエラー（黄）
  &.wpcf7-validation-errors {
    color: #856404;
    background-color: #fff3cd;
  }
}
```

#### E. ローディングスピナー

```scss
.wpcf7-spinner {
  display: inline-block;
  width: rv(20);
  height: rv(20);
  border: 2px solid var(--color-gray-light);
  border-top-color: var(--color-text);
  border-radius: 50%;
  animation: wpcf7-spin 0.6s linear infinite;
}

@keyframes wpcf7-spin {
  to {
    transform: rotate(360deg);
  }
}
```

## CF7フォームタグとCSSクラスの対応

| CF7タグ | CSSクラス | スタイルファイル |
|---------|-----------|-----------------|
| `[select* category]` | `.c-select` | `_c-FormSelect.scss` |
| `[text* name]` | `.c-input` | `_c-FormInput.scss` |
| `[email* email]` | `.c-input` | `_c-FormInput.scss` |
| `[tel tel]` | `.c-input` | `_c-FormInput.scss` |
| `[textarea* message]` | `.c-textarea` | `_c-FormTextarea.scss` |
| `[acceptance privacy]` | `.c-checkbox` | `_c-FormCheckbox.scss` |
| `[submit]` | `.c-submit__button` | `_p-contact.scss` (CF7専用) |

## HTML構造例

### CF7が出力するHTML

```html
<form class="wpcf7-form">
  <div class="c-form__item c-form__item--grid">
    <label class="c-label">
      <span class="c-label__text">氏名</span>
      <span class="c-label__required">*</span>
    </label>
    <span class="wpcf7-form-control-wrap" data-name="name">
      <input type="text" name="name" class="c-input wpcf7-text wpcf7-validates-as-required" />
      <span class="wpcf7-not-valid-tip">この項目は必須です。</span>
    </span>
  </div>
</form>
```

## レスポンシブ対応

すべてのCF7専用スタイルはレスポンシブ対応済み：

- **PC**: `rv()` 関数を使用（基準サイズから相対計算）
- **SP**: `@include sp` mixin内で `svw()` 関数を使用（viewport width単位）

例：
```scss
.wpcf7-response-output {
  margin: rv(20) 0;  // PC

  @include sp {
    margin: svw(20) 0;  // SP
  }
}
```

## デザイン仕様

### カラーパレット

- **プライマリ（エラー）**: `var(--color-primary)` (#d71218)
- **テキスト**: `var(--color-text)` (#111)
- **ボーダー**: `var(--color-text)` (#111)
- **背景（白）**: `var(--color-white)` (#fff)

### タイポグラフィ

- **ラベル**: `rv(18)` / `svw(18)`
- **入力フィールド**: `rv(18)` / `svw(18)`
- **エラーメッセージ**: `rv(14)` / `svw(14)`
- **ボタン**: `rv(20)` / `svw(20)`

### スペーシング

- **グリッドギャップ**: PC `rv(30)`, SP `svw(16)`
- **フィールド間マージン**: PC `rv(40)`, SP `svw(30)`
- **ボタン上マージン**: PC `rv(40)`, SP `svw(40)`

## 既存HTMLフォームとの互換性

既存の `themes/{{THEME_NAME}}/template-parts/contact/form.php` で使用しているクラス名をCF7でも同じように使用することで、スタイルの一貫性を保っています。

### クラス名の一致

- `.c-form__item` - フォームアイテムコンテナ
- `.c-form__item--grid` - 2カラムグリッドレイアウト
- `.c-label` - ラベル
- `.c-input` - テキスト入力
- `.c-select` - セレクトボックス
- `.c-textarea` - テキストエリア
- `.c-checkbox` - チェックボックス

## ビルド確認

実装後、以下のコマンドでビルドが正常に完了することを確認済み：

```bash
npm run build
```

出力:
```
themes/{{THEME_NAME}}/assets/css/contact/style.css  14.58 kB │ gzip: 3.08 kB
✓ built in 3.42s
```

## 使用方法

### 1. CF7フォーム設定

`code.md` に記載されているフォームコードをContact Form 7の管理画面に貼り付けてください。

### 2. 固定ページへの挿入

#### 方法A: ブロックエディタ（推奨）

1. お問い合わせページを編集
2. Contact Form 7ブロックを追加
3. フォームを選択

#### 方法B: PHPテンプレート

`themes/{{THEME_NAME}}/template-parts/contact/form.php` の24行目を編集：

```php
$form_type = 'cf7'; // 'html' から 'cf7' に変更
```

### 3. スタイル確認

ブラウザでお問い合わせページを開き、以下を確認：

- [ ] フォームフィールドが正しく表示される
- [ ] 必須項目（*）が赤く表示される
- [ ] バリデーションエラー時に赤枠が表示される
- [ ] 送信ボタンのスタイルが適用される
- [ ] レスポンシブ表示が正しく動作する

## トラブルシューティング

### スタイルが反映されない場合

1. **開発サーバーが起動しているか確認**
   ```bash
   npm run dev
   ```

2. **ブラウザキャッシュをクリア**
   - Chrome: Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)

3. **ビルドエラーがないか確認**
   ```bash
   npm run build
   ```

### CF7特有のクラスが見つからない場合

CF7が正しくインストールされ、有効化されているか確認：

```
WordPress管理画面 → プラグイン → Contact Form 7
```

## 参考ドキュメント

- **CF7フォームコード**: `docs/contact-form-7-code.md`
- **既存フォームテンプレート**: `themes/{{THEME_NAME}}/template-parts/contact/form.php`
- **コーディングガイドライン**: `docs/coding-guidelines/02-scss-design.md`
- **WordPress統合**: `docs/coding-guidelines/03-wordpress-integration.md`（インデックス）

## まとめ

既存のフォームコンポーネントを最大限活用しながら、CF7特有の要素（`.wpcf7-form-control-wrap`, `.wpcf7-not-valid-tip`, レスポンスメッセージ等）に対してプロジェクト固有のスタイルを追加しました。

すべてのスタイルはFLOCSS + BEM命名規則に準拠し、レスポンシブ対応済みです。
