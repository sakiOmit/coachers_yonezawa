# Contact Form 7 フォームコード

このドキュメントは、現在のHTMLフォーム（`themes/{{THEME_NAME}}/template-parts/contact/form.php`）をContact Form 7形式に変換したコードを含みます。

## フォームコード

以下のコードをContact Form 7の管理画面でフォームエディタにコピペしてください：

```html
<div class="c-form__item c-form__item--grid">
  <label class="c-label">
    <span class="c-label__text">お問い合わせ種別</span>
    <span class="c-label__required">*</span>
  </label>
  [select* category class:c-select first_as_label "お問い合わせ種別を選択してください" "サービスについて" "お見積りについて" "採用について" "その他"]
</div>

<div class="c-form__item c-form__item--grid">
  <label class="c-label">
    <span class="c-label__text">会社名</span>
  </label>
  [text company class:c-input placeholder "{{COMPANY_NAME}}"]
</div>

<div class="c-form__item c-form__item--grid">
  <label class="c-label">
    <span class="c-label__text">氏名</span>
    <span class="c-label__required">*</span>
  </label>
  [text* name class:c-input placeholder "東京　太朗（全角）"]
</div>

<div class="c-form__item c-form__item--grid">
  <label class="c-label">
    <span class="c-label__text">ふりがな</span>
    <span class="c-label__required">*</span>
  </label>
  [text* furigana class:c-input placeholder "トウキョウ　タロウ（全角カナ）"]
</div>

<div class="c-form__item c-form__item--grid">
  <label class="c-label">
    <span class="c-label__text">電話番号</span>
  </label>
  [tel tel class:c-input placeholder "00-0000-0000（半角数字）"]
</div>

<div class="c-form__item c-form__item--grid">
  <label class="c-label">
    <span class="c-label__text">メールアドレス</span>
    <span class="c-label__required">*</span>
  </label>
  [email* email class:c-input placeholder "tokyo@mail.com（半角英数字）"]
</div>

<div class="c-form__item c-form__item--grid">
  <label class="c-label">
    <span class="c-label__text">お問い合わせ内容</span>
    <span class="c-label__required">*</span>
  </label>
  [textarea* message class:c-textarea placeholder "採用について" 10x1]
</div>

<div class="c-form__item c-checkbox-layout">
  [acceptance privacy class:c-checkbox]
  <span class="c-checkbox__text">
    <a href="/privacy-policy/" target="_blank" rel="noopener">プライバシーポリシー</a>に同意します。
  </span>
  [/acceptance]
</div>

<div class="c-submit">
  [submit class:c-submit__button "送信する"]
</div>
```

## メールテンプレート設定

Contact Form 7の管理画面の「メール」タブで以下のように設定してください：

### 管理者宛メール（メールタブ）

**送信先:**
```
[_site_admin_email]
```
または実際の管理者メールアドレス（例：`info@example.com`）

**送信元:**
```
[name] <[email]>
```

**題名:**
```
お問い合わせ: [category]
```

**追加ヘッダー:**
```
Reply-To: [email]
```

**メッセージ本文:**
```
お問い合わせがありました。

━━━━━━━━━━━━━━━━━━━━━━━━
■ お問い合わせ種別
━━━━━━━━━━━━━━━━━━━━━━━━
[category]

━━━━━━━━━━━━━━━━━━━━━━━━
■ 会社名
━━━━━━━━━━━━━━━━━━━━━━━━
[company]

━━━━━━━━━━━━━━━━━━━━━━━━
■ 氏名
━━━━━━━━━━━━━━━━━━━━━━━━
[name]

━━━━━━━━━━━━━━━━━━━━━━━━
■ ふりがな
━━━━━━━━━━━━━━━━━━━━━━━━
[furigana]

━━━━━━━━━━━━━━━━━━━━━━━━
■ 電話番号
━━━━━━━━━━━━━━━━━━━━━━━━
[tel]

━━━━━━━━━━━━━━━━━━━━━━━━
■ メールアドレス
━━━━━━━━━━━━━━━━━━━━━━━━
[email]

━━━━━━━━━━━━━━━━━━━━━━━━
■ お問い合わせ内容
━━━━━━━━━━━━━━━━━━━━━━━━
[message]

━━━━━━━━━━━━━━━━━━━━━━━━

このメールは [_site_title] ([_site_url]) のお問い合わせフォームから送信されました。
```

### 自動返信メール（メール (2) タブ）

**有効化:** チェックを入れる

**送信先:**
```
[email]
```

**送信元:**
```
[_site_title] <wordpress@yourdomain.com>
```
（`wordpress@yourdomain.com` は実際のドメインに変更）

**題名:**
```
【自動返信】お問い合わせを受け付けました
```

**追加ヘッダー:**
```
Reply-To: info@example.com
```
（実際の管理者メールアドレスに変更）

**メッセージ本文:**
```
[name] 様

この度は、お問い合わせいただきありがとうございます。
以下の内容でお問い合わせを受け付けました。

━━━━━━━━━━━━━━━━━━━━━━━━
■ お問い合わせ種別
━━━━━━━━━━━━━━━━━━━━━━━━
[category]

━━━━━━━━━━━━━━━━━━━━━━━━
■ 会社名
━━━━━━━━━━━━━━━━━━━━━━━━
[company]

━━━━━━━━━━━━━━━━━━━━━━━━
■ 氏名
━━━━━━━━━━━━━━━━━━━━━━━━
[name]

━━━━━━━━━━━━━━━━━━━━━━━━
■ ふりがな
━━━━━━━━━━━━━━━━━━━━━━━━
[furigana]

━━━━━━━━━━━━━━━━━━━━━━━━
■ 電話番号
━━━━━━━━━━━━━━━━━━━━━━━━
[tel]

━━━━━━━━━━━━━━━━━━━━━━━━
■ メールアドレス
━━━━━━━━━━━━━━━━━━━━━━━━
[email]

━━━━━━━━━━━━━━━━━━━━━━━━
■ お問い合わせ内容
━━━━━━━━━━━━━━━━━━━━━━━━
[message]

━━━━━━━━━━━━━━━━━━━━━━━━

内容を確認の上、担当者より折り返しご連絡いたします。
しばらくお待ちください。

※このメールは自動送信です。このメールに返信されても対応できません。

━━━━━━━━━━━━━━━━━━━━━━━━
[_site_title]
[_site_url]
━━━━━━━━━━━━━━━━━━━━━━━━
```

## メッセージ設定

「メッセージ」タブで以下のメッセージをカスタマイズできます（任意）：

**送信完了メッセージ:**
```
お問い合わせありがとうございます。送信が完了しました。
```

**送信エラーメッセージ:**
```
メッセージの送信に失敗しました。しばらくしてからもう一度お試しください。
```

**必須項目エラー:**
```
この項目は必須です。
```

**バリデーションエラー:**
```
入力内容に誤りがあります。
```

## セットアップ手順

1. WordPress管理画面 → 「お問い合わせ」→「新規追加」または既存フォームを編集
2. フォーム名を入力（例：「お問い合わせフォーム」）
3. 「フォーム」タブに上記のフォームコードをコピー＆ペースト
4. 「メール」タブで管理者宛メールを設定
5. 「メール (2)」タブで自動返信メールを設定（チェックを入れて有効化）
6. 「メッセージ」タブでメッセージをカスタマイズ（任意）
7. 「保存」をクリック
8. 表示されるショートコードをメモ

## 固定ページへの挿入方法

### 方法1: ブロックエディタで挿入（推奨）

1. お問い合わせページ（`page-contact.php`を使用しているページ）を編集
2. 「+」ボタンをクリック
3. 「Contact Form 7」ブロックを検索して追加
4. 作成したフォームを選択
5. 公開または更新

### 方法2: ショートコードで挿入

フォーム保存後に表示されるショートコードをコピー：
```
[contact-form-7 id="123" title="お問い合わせフォーム"]
```

固定ページのブロックエディタで「ショートコード」ブロックを追加し、上記をペースト。

### 方法3: PHPテンプレートに直接挿入

`themes/{{THEME_NAME}}/pages/page-contact.php` の83-86行目を以下のように変更：

```php
<?php
// CF7ショートコードを直接出力
echo do_shortcode('[contact-form-7 id="123" title="お問い合わせフォーム"]');
?>
```

## フィールド一覧

| フィールド名 | CF7タグ | タイプ | 必須 | 説明 |
|-------------|---------|--------|------|------|
| category | `[select* category]` | select | ○ | お問い合わせ種別 |
| company | `[text company]` | text | - | 会社名 |
| name | `[text* name]` | text | ○ | 氏名 |
| furigana | `[text* furigana]` | text | ○ | ふりがな |
| tel | `[tel tel]` | tel | - | 電話番号 |
| email | `[email* email]` | email | ○ | メールアドレス |
| message | `[textarea* message]` | textarea | ○ | お問い合わせ内容 |
| privacy | `[acceptance privacy]` | acceptance | ○ | プライバシーポリシー同意 |

## 注意事項

### CSSクラスについて
- 既存のCSSクラス（`c-form__item--grid`, `c-input`, `c-textarea`, `c-label`等）を使用しているため、既存のスタイルがそのまま適用されます
- 追加のCSSは基本的に不要ですが、CF7特有のスタイル調整が必要な場合は以下を参考にしてください：

```scss
.wpcf7 {
  .c-select {
    display: block;
  }

  select {
    width: 100%;
  }
}
```

### メールアドレスについて
- `[_site_admin_email]` はWordPressの管理者メールアドレスを自動的に使用します
- `wordpress@yourdomain.com` は実際のドメインのメールアドレスに変更してください
- `info@example.com` は実際の管理者メールアドレスに変更してください

### URLについて
- プライバシーポリシーのURL（`/privacy-policy/`）は実際のURLを確認してください

### テストについて
- 設定完了後、必ず送信テストを実施してください
- 管理者宛メール、自動返信メール両方が正しく届くことを確認してください

## 既存HTMLフォームとの対応関係

| 既存HTML | CF7タグ |
|---------|---------|
| `<select id="contact-category" name="category">` | `[select* category]` |
| `<input type="text" name="company">` | `[text company]` |
| `<input type="text" name="name" required>` | `[text* name]` |
| `<input type="text" name="furigana" required>` | `[text* furigana]` |
| `<input type="tel" name="tel">` | `[tel tel]` |
| `<input type="email" name="email" required>` | `[email* email]` |
| `<textarea name="message" required>` | `[textarea* message]` |
| `<input type="checkbox" name="privacy" required>` | `[acceptance privacy]` |

フィールド名を既存HTMLと完全に一致させているため、既存のバックエンド処理（メール送信など）との互換性を保っています。
