---
name: figma-form-generator
description: "Figma form design to SCSS + CF7 shortcode generator"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - mcp__figma__get_design_context
  - mcp__figma__get_metadata
context: fork
agent: general-purpose
---

# Figma Form Generator

## Overview

Figma のフォームデザインから SCSS + CF7 ショートコードを自動生成するスキル。
CSS Custom Properties 方式を活用し、プロジェクト固有のスタイルは CSS 変数の設定のみで完結する。

## Usage

```
/figma-form-generator --url <figma-url> --page <page-name>
```

## Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| url | Yes | - | Figma URL (node-id含む) |
| page | Yes | - | ページ名 (contact等) |
| adapter | No | cf7 | 出力形式 (cf7/mwwp/html) |
| output-dir | No | .claude/cache/form/ | 出力ディレクトリ |

## Processing Flow

### Step 1: Design Context 取得

```
1. Figma URL から fileKey と nodeId を抽出
2. mcp__figma__get_metadata でフォーム全体構造を取得
3. mcp__figma__get_design_context でフォーム詳細を取得
4. .claude/cache/form/{page}/ にキャッシュ保存
```

### Step 2: フォーム構造解析

フォーム要素の検出基準:

| 要素タイプ | 検出パターン |
|-----------|-------------|
| 入力フィールド | `input`, `field`, `text-field`, `入力` |
| テキストエリア | `textarea`, `message`, `本文`, height >= 100px |
| セレクト | `select`, `dropdown`, `選択` |
| ファイル | `file`, `upload`, `attach`, `添付`, `履歴書`, `職務経歴書` |
| チェックボックス | `checkbox`, `check`, `同意` |
| ラジオ | `radio`, `choice` |
| 送信ボタン | `submit`, `button`, `送信` |

### Step 3: 型マッピング

#### ラベルテキストベースの推定

| パターン | 推定型 | CF7タグ |
|----------|--------|---------|
| `/メール\|email\|e-mail/i` | email | `[email]` |
| `/電話\|tel\|phone\|携帯/i` | tel | `[tel]` |
| `/URL\|ホームページ\|website/i` | url | `[url]` |
| `/日付\|date\|生年月日/i` | date | `[date]` |
| `/数量\|個数\|人数\|amount/i` | number | `[number]` |

#### フィールド名ベースの推定

| パターン | 推定name |
|----------|----------|
| `/name\|氏名\|名前/i` | your-name |
| `/email\|mail/i` | your-email |
| `/tel\|phone/i` | your-tel |
| `/address\|住所/i` | your-address |
| `/company\|会社\|御社/i` | your-company |
| `/message\|内容\|本文/i` | your-message |

#### 必須判定

- ラベルに「必須」「required」「*」が含まれる → required: true
- デフォルト → required: false

### Step 4: デザイントークン抽出

Figma のデザイン値から CSS Custom Properties を生成:

```scss
// 抽出される CSS 変数の例
.p-{page} {
  // Form Items
  --form-gap: #{rv(32)};
  --form-item-gap: #{rv(12)};

  // Label
  --form-label-font-size: #{rv(16)};
  --form-label-color: #4c4c4c;
  --form-required-color: #195162;

  // Input / Select / Textarea
  --form-input-padding: 0 #{rv(20)};
  --form-input-font-size: #{rv(16)};
  --form-input-color: #4c4c4c;
  --form-input-radius: #{rv(4)};
  --form-input-border: 1px solid #ddd;
  --form-input-bg: #fff;

  // Submit
  --form-submit-bg: linear-gradient(...);
  --form-submit-radius: #{rv(60)};

  // SP Overrides
  @include sp {
    --form-gap: #{svw(24)};
    // ...
  }
}
```

### Step 5: コード生成

#### CF7 ショートコード生成

| フィールド型 | ショートコード形式 |
|-------------|-------------------|
| text | `[text* your-name class:c-input placeholder "..."]` |
| email | `[email* your-email class:c-input placeholder "..."]` |
| tel | `[tel your-tel class:c-input placeholder "..."]` |
| textarea | `[textarea* your-message class:c-textarea placeholder "..."]` |
| select | `[select your-inquiry class:c-select include_blank "..." "opt1" "opt2"]` |
| file | `[file your-resume filetypes:pdf\|doc\|docx limit:5mb]` |
| checkbox | `[checkbox your-checkbox class:c-checkbox__input "label"]` |
| acceptance | `[acceptance your-acceptance class:c-checkbox__input]` |
| submit | `[submit class:c-submit__button "label"]` |

※ `*` は必須フィールド

### Step 6: ファイル出力

| ファイル | 内容 |
|----------|------|
| `form-fields.txt` | CF7ショートコードリスト（個別） |
| `form-cf7-template.txt` | CF7管理画面にそのまま貼り付けるHTML |
| `form-template.php` | PHPテンプレート（CF7埋め込み用） |
| `form-variables.scss` | CSS Custom Properties（p-{page}用） |
| `form-structure.json` | 解析結果JSON |

## Output Structure

```
.claude/cache/form/{page}/
├── form-fields.txt       # CF7ショートコード（個別）
├── form-cf7-template.txt # CF7管理画面貼り付け用HTML ← NEW
├── form-template.php     # PHPテンプレート
├── form-variables.scss   # CSS Custom Properties
└── form-structure.json   # 解析結果
```

## Error Handling

| エラー | 対応 |
|--------|------|
| Figma URL無効 | エラーメッセージ + 正しい形式を提示 |
| フォーム要素未検出 | 警告 + 手動でnode-idを指定するよう案内 |
| 型推定不可 | text型にフォールバック + 警告 |
| ラベル抽出失敗 | プレースホルダーから推定 |

## SCSS Integration

### CSS Custom Properties 方式

フォームコンポーネントは CSS Custom Properties でスタイル制御される:

```
src/scss/object/components/form/
├── _c-form.scss              # フォームコンテナ
├── _c-form-item.scss         # フォームアイテムレイアウト
├── _c-form-label.scss        # ラベル
├── _c-form-input.scss        # テキスト入力
├── _c-form-input-group.scss  # 入力グループ（横並び等）
├── _c-form-select.scss       # セレクトボックス
├── _c-form-textarea.scss     # テキストエリア
├── _c-form-checkbox.scss     # チェックボックス
├── _c-form-radio.scss        # ラジオボタン
├── _c-form-radio-group.scss  # ラジオグループ
├── _c-form-file-input.scss   # ファイルアップロード
├── _c-form-submit.scss       # 送信ボタン
├── _c-form-validation.scss   # バリデーション
├── _c-form-confirm.scss      # 確認画面
└── adapters/
    ├── _index.scss           # アダプタindex
    └── _cf7.scss             # CF7 DOM構造アダプタ
```

### CF7 DOM構造（実際の出力）

CF7はショートコードを処理して以下のDOM構造を生成する。
`adapters/_cf7.scss` はこの構造に対応するためのスタイルを提供。

#### テキスト入力 / Email / Tel

```html
<!-- CF7ショートコード -->
[text* your-name class:c-input placeholder "例）山田 太郎"]

<!-- CF7出力 -->
<span class="wpcf7-form-control-wrap" data-name="your-name">
  <input type="text" name="your-name"
         class="wpcf7-form-control wpcf7-text wpcf7-validates-as-required c-input"
         aria-required="true" aria-invalid="false"
         placeholder="例）山田 太郎" value="">
</span>
```

#### セレクトボックス

```html
<!-- CF7ショートコード -->
[select* job-type class:c-select include_blank "選択してください" "営業" "エンジニア"]

<!-- CF7出力 -->
<span class="wpcf7-form-control-wrap" data-name="job-type">
  <select name="job-type"
          class="wpcf7-form-control wpcf7-select wpcf7-validates-as-required c-select"
          aria-required="true" aria-invalid="false">
    <option value="">—以下から選択してください—</option>
    <option value="選択してください">選択してください</option>
    <option value="営業">営業</option>
    <option value="エンジニア">エンジニア</option>
  </select>
</span>
```

#### ファイル入力

```html
<!-- CF7ショートコード -->
[file your-resume filetypes:pdf|doc|docx limit:5mb]

<!-- CF7出力 -->
<span class="wpcf7-form-control-wrap" data-name="your-resume">
  <input type="file" name="your-resume"
         class="wpcf7-form-control wpcf7-file"
         accept=".pdf,.doc,.docx" aria-invalid="false">
</span>
```

#### Acceptance（同意チェックボックス）

```html
<!-- CF7ショートコード -->
[acceptance your-acceptance class:c-checkbox__input]

<!-- CF7出力（深いネスト構造） -->
<span class="wpcf7-form-control-wrap" data-name="your-acceptance">
  <span class="wpcf7-form-control wpcf7-acceptance">
    <span class="wpcf7-list-item">
      <input type="checkbox" name="your-acceptance" value="1"
             class="c-checkbox__input" aria-invalid="false">
    </span>
  </span>
</span>
```

#### 送信ボタン

```html
<!-- CF7ショートコード -->
[submit class:c-submit__button "送信する"]

<!-- CF7出力 -->
<input type="submit" value="送信する"
       class="wpcf7-form-control wpcf7-submit has-spinner c-submit__button"
       disabled="">
<span class="wpcf7-spinner"></span>
```

#### バリデーションエラー

```html
<!-- エラー時にCF7が自動追加 -->
<span class="wpcf7-form-control-wrap" data-name="your-name">
  <input type="text" class="wpcf7-form-control wpcf7-not-valid c-input" ...>
  <span class="wpcf7-not-valid-tip" aria-hidden="true">
    必須項目です。
  </span>
</span>
```

### adapters/_cf7.scss の役割

CF7が生成するDOM構造に対してスタイルを適用:

```scss
// adapters/_cf7.scss の主な対応
.wpcf7-form-control-wrap {
  display: block;
  width: 100%;
}

.wpcf7-not-valid-tip {
  color: var(--form-error-color);
  font-size: var(--form-error-font-size);
}

.wpcf7-spinner {
  // 送信中スピナーのスタイル
}

// acceptance の深いネスト対応
.wpcf7-acceptance {
  .wpcf7-list-item {
    display: inline;
  }
}
```

### スタイルカスタマイズ方法

プロジェクト固有のスタイルは p-*.scss で CSS 変数を設定:

```scss
// src/scss/object/project/_p-contact.scss
.p-contact {
  // CSS Custom Properties を設定するだけ
  --form-gap: #{rv(32)};
  --form-label-color: #4c4c4c;
  --form-submit-bg: linear-gradient(88.45deg, #195162 5.54%, #08414e 182.82%);

  @include sp {
    --form-gap: #{svw(24)};
  }
}
```

c-* コンポーネントの直接編集は不要。

### 利用可能な CSS 変数一覧

| カテゴリ | 変数名 | 説明 |
|----------|--------|------|
| Form | `--form-gap` | フォームアイテム間の間隔 |
| Label | `--form-label-font-size` | ラベルのフォントサイズ |
| Label | `--form-label-color` | ラベルの文字色 |
| Label | `--form-required-color` | 必須バッジの色 |
| Label | `--form-optional-color` | 任意バッジの色 |
| Input | `--form-input-padding` | 入力欄のパディング |
| Input | `--form-input-font-size` | 入力欄のフォントサイズ |
| Input | `--form-input-color` | 入力欄の文字色 |
| Input | `--form-input-radius` | 入力欄の角丸 |
| Input | `--form-input-border` | 入力欄のボーダー |
| Input | `--form-input-bg` | 入力欄の背景色 |
| Input | `--form-placeholder-color` | プレースホルダーの色 |
| Input | `--form-focus-color` | フォーカス時のボーダー色 |
| Textarea | `--form-textarea-min-height` | テキストエリアの最小高さ |
| Select | `--form-select-*` | セレクトボックス関連 |
| File | `--form-file-*` | ファイル入力関連 |
| Checkbox | `--form-checkbox-*` | チェックボックス関連 |
| Radio | `--form-radio-*` | ラジオボタン関連 |
| Submit | `--form-submit-*` | 送信ボタン関連 |
| Error | `--form-error-color` | エラー時の色 |

※ SP用は `-sp` サフィックス付き（例: `--form-gap-sp`）

## Example

### Input (Figma)

```
Form Container
├── Field: お名前（必須）
│   └── Input placeholder: "お名前を入力してください"
├── Field: メールアドレス（必須）
│   └── Input placeholder: "example@email.com"
├── Field: お問い合わせ種別
│   └── Select options: 製品について, サービスについて, その他
├── Field: 添付ファイル（任意）
│   └── File: 複数ファイル対応
├── Field: お問い合わせ内容（必須）
│   └── Textarea placeholder: "お問い合わせ内容を入力してください"
├── Checkbox: 個人情報の取り扱いに同意する
└── Submit: 送信する
```

### Output (form-fields.txt)

```
[text* your-name class:c-input placeholder "お名前を入力してください"]

[email* your-email class:c-input placeholder "example@email.com"]

[select your-inquiry class:c-select include_blank "選択してください" "製品について" "サービスについて" "その他"]

[file your-attachment filetypes:pdf|doc|docx limit:5mb]

[textarea* your-message class:c-textarea placeholder "お問い合わせ内容を入力してください"]

[acceptance your-acceptance class:c-checkbox__input]

[submit class:c-submit__button "送信する"]
```

### Output (form-cf7-template.txt)

CF7管理画面にそのまま貼り付けるテンプレート:

```html
<div class="c-form__items">

  <div class="c-form__item c-form__item--flex">
    <label class="c-label">
      <span class="c-label__text">お名前</span>
      <span class="c-label__required">必須</span>
    </label>
    [text* your-name class:c-input placeholder "お名前を入力してください"]
  </div>

  <div class="c-form__item c-form__item--flex">
    <label class="c-label">
      <span class="c-label__text">メールアドレス</span>
      <span class="c-label__required">必須</span>
    </label>
    [email* your-email class:c-input placeholder "example@email.com"]
  </div>

  <div class="c-form__item c-form__item--flex">
    <label class="c-label">
      <span class="c-label__text">お問い合わせ種別</span>
      <span class="c-label__optional">任意</span>
    </label>
    [select your-inquiry class:c-select include_blank "選択してください" "製品について" "サービスについて" "その他"]
  </div>

  <!-- 添付ファイル（複数対応） -->
  <div class="c-form__item c-form__item--flex">
    <label class="c-label">
      <span class="c-label__text">添付ファイル</span>
      <span class="c-label__optional">任意</span>
    </label>
    <div class="c-file-group">
      <div class="c-file">
        <label class="c-file__label">
          ファイルを選択
          [file your-attachment filetypes:pdf|doc|docx limit:5mb]
        </label>
      </div>
      <div class="c-file">
        <label class="c-file__label">
          ファイルを選択
          [file your-attachment2 filetypes:pdf|doc|docx limit:5mb]
        </label>
      </div>
    </div>
  </div>

  <div class="c-form__item c-form__item--flex">
    <label class="c-label">
      <span class="c-label__text">お問い合わせ内容</span>
      <span class="c-label__required">必須</span>
    </label>
    [textarea* your-message class:c-textarea placeholder "お問い合わせ内容を入力してください"]
  </div>

</div>

<!-- プライバシーポリシー同意 -->
<div class="c-form__privacy">
  <label class="c-checkbox">
    [acceptance your-acceptance class:c-checkbox__input] <span class="c-checkbox__label"><a href="/privacy-policy/" target="_blank" class="c-checkbox__link">個人情報の取り扱い</a>に同意する</span>
  </label>
</div>

<!-- 送信ボタン -->
<div class="c-submit">
  [submit class:c-submit__button "送信する"]
</div>
```

### Output (form-variables.scss)

```scss
// Figma Design Tokens for Contact Form
// Generated: 2026-02-02

.p-contact {
  // Form Items
  --form-gap: #{rv(32)};
  --form-item-gap: #{rv(12)};

  // Label
  --form-label-font-size: #{rv(16)};
  --form-label-color: #4c4c4c;
  --form-required-color: #195162;
  --form-optional-color: #98a6ab;

  // Input / Select / Textarea
  --form-input-padding: 0 #{rv(20)};
  --form-input-font-size: #{rv(16)};
  --form-input-color: #4c4c4c;
  --form-input-radius: #{rv(4)};
  --form-input-border: 1px solid #ddd;
  --form-input-bg: #fff;
  --form-placeholder-color: #aaa;
  --form-focus-color: #195162;

  // Submit
  --form-submit-margin-top: #{rv(48)};
  --form-submit-min-width: #{rv(280)};
  --form-submit-padding: #{rv(20)} #{rv(48)};
  --form-submit-font-size: #{rv(16)};
  --form-submit-bg: linear-gradient(88.45deg, #195162 5.54%, #08414e 182.82%);
  --form-submit-radius: #{rv(60)};

  // SP Overrides
  @include sp {
    --form-gap: #{svw(24)};
    --form-item-gap: #{svw(8)};
    --form-label-font-size: #{svw(14)};
    --form-input-padding: 0 #{svw(16)};
    --form-input-font-size: #{svw(14)};
    --form-input-radius: #{svw(4)};
    --form-submit-margin-top: #{svw(32)};
    --form-submit-min-width: #{svw(200)};
    --form-submit-padding: #{svw(16)} #{svw(32)};
    --form-submit-font-size: #{svw(14)};
    --form-submit-radius: #{svw(40)};
  }
}
```

## Related

- `src/scss/object/components/form/` - フォームSCSS（CSS Custom Properties方式）
- `src/scss/object/project/_p-entry.scss` - 実装例（entry フォーム）

## Changelog

- v2.2.0 (2026-02-02): CF7 DOM構造セクション追加（実際の出力HTML、adapters説明）
- v2.1.1 (2026-02-02): SCSS構造を実態に合わせて更新（input-group, radio-group, confirm追加）
- v2.1.0 (2026-02-02): file型追加、acceptance閉じタグ削除、c-file-group構造追加
- v2.0.0 (2026-02-02): CSS Custom Properties 方式に移行、mixin廃止
- v1.0.0 (2026-02-02): Initial release
