# Contact Form 7 セットアップガイド

お問い合わせページで使用するContact Form 7のフォーム設定方法です。

## フォームマークアップ（Contact Form 7 管理画面に貼り付け）

以下のマークアップを Contact Form 7 の管理画面（`/wp-admin/admin.php?page=wpcf7`）でフォーム作成時に使用してください。

```html
<label>
  <span class="wpcf7-form-label-text">お問い合わせ種別 <span class="wpcf7-required">*</span></span>
  [select* inquiry-type class:wpcf7-select first_as_label "お問い合わせ種別を選択" "サービスについて" "お見積りについて" "採用について" "その他"]
</label>

<label>
  <span class="wpcf7-form-label-text">会社名</span>
  [text company-name class:wpcf7-text placeholder "{{COMPANY_NAME}}"]
</label>

<label>
  <span class="wpcf7-form-label-text">氏名 <span class="wpcf7-required">*</span></span>
  [text* your-name class:wpcf7-text placeholder "東京　太朗（全角）"]
</label>

<label>
  <span class="wpcf7-form-label-text">ふりがな <span class="wpcf7-required">*</span></span>
  [text* furigana class:wpcf7-text placeholder "トウキョウ　タロウ（全角カナ）"]
</label>

<label>
  <span class="wpcf7-form-label-text">電話番号</span>
  [tel tel class:wpcf7-tel placeholder "00-0000-0000（半角数字）"]
</label>

<label>
  <span class="wpcf7-form-label-text">メールアドレス <span class="wpcf7-required">*</span></span>
  [email* your-email class:wpcf7-email placeholder "tokyo@mail.com（半角英数字）"]
</label>

<label>
  <span class="wpcf7-form-label-text">お問い合わせ内容 <span class="wpcf7-required">*</span></span>
  [textarea* your-message class:wpcf7-textarea placeholder "採用について"]
</label>

<div class="wpcf7-acceptance">
  [acceptance acceptance-privacy class:wpcf7-acceptance-checkbox]
  [link privacy-policy "プライバシーポリシー" "/privacy/"]に同意します。
</div>

[submit class:wpcf7-submit "送信する"]
```

## フィールド説明

### お問い合わせ種別（必須）
- タイプ: `select*` (必須ドロップダウン)
- name: `inquiry-type`
- オプション:
  - サービスについて
  - お見積りについて
  - 採用について
  - その他

### 会社名（任意）
- タイプ: `text`
- name: `company-name`
- placeholder: {{COMPANY_NAME}}

### 氏名（必須）
- タイプ: `text*`
- name: `your-name`
- placeholder: 東京　太朗（全角）

### ふりがな（必須）
- タイプ: `text*`
- name: `furigana`
- placeholder: トウキョウ　タロウ（全角カナ）

### 電話番号（任意）
- タイプ: `tel`
- name: `tel`
- placeholder: 00-0000-0000（半角数字）

### メールアドレス（必須）
- タイプ: `email*`
- name: `your-email`
- placeholder: tokyo@mail.com（半角英数字）

### お問い合わせ内容（必須）
- タイプ: `textarea*`
- name: `your-message`
- placeholder: 採用について

### プライバシーポリシー同意（必須）
- タイプ: `acceptance`
- name: `acceptance-privacy`
- リンク先: /privacy/

## メール設定

### 送信先（管理者宛）

**To:** `info@example.com`（管理者メールアドレス）

**From:** `[your-email]`

**Subject:** `お問い合わせがありました - [your-name]様`

**メッセージ本文:**
```
お問い合わせ種別: [inquiry-type]
会社名: [company-name]
氏名: [your-name]
ふりがな: [furigana]
電話番号: [tel]
メールアドレス: [your-email]

お問い合わせ内容:
[your-message]

---
このメールは [_site_title] から送信されました
送信日時: [_date] [_time]
送信元URL: [_url]
```

### 自動返信メール（お客様宛）

**To:** `[your-email]`

**From:** `info@example.com`（送信元メールアドレス）

**Subject:** `お問い合わせを受け付けました - {{COMPANY_NAME}}`

**メッセージ本文:**
```
[your-name] 様

この度はお問い合わせいただきまして誠にありがとうございます。

以下の内容でお問い合わせを受け付けました。
内容を確認次第、担当者より折返しご連絡させていただきます。
今しばらくお待ちくださいませ。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
お問い合わせ内容
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

お問い合わせ種別: [inquiry-type]
会社名: [company-name]
氏名: [your-name]
ふりがな: [furigana]
電話番号: [tel]
メールアドレス: [your-email]

お問い合わせ内容:
[your-message]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{COMPANY_NAME}}
URL: [_site_url]
```

## メッセージ設定

Contact Form 7 の「メッセージ」タブで以下のメッセージをカスタマイズしてください。

| メッセージタイプ | デフォルトテキスト |
|----------------|----------------|
| **送信成功** | ありがとうございます。メッセージは送信されました。 |
| **送信エラー** | メッセージの送信に失敗しました。後でまたお試しください。 |
| **検証エラー** | 1つ以上の項目に入力エラーがあります。ご確認ください。 |
| **必須項目エラー** | この項目は必須です。 |
| **メールアドレス不正** | メールアドレスの形式が正しくありません。 |

## バリデーション設定

Contact Form 7 のバリデーション機能で以下をチェック:

- **氏名**: 全角文字のみ許可
- **ふりがな**: 全角カタカナのみ許可
- **電話番号**: 数字とハイフンのみ許可
- **メールアドレス**: RFC準拠のメールアドレス形式

## リダイレクト設定（送信完了後）

送信完了後に「お問い合わせ完了」ページ（`/thanks/`）にリダイレクトする場合:

1. `functions.php` に以下を追加:

```php
// Contact Form 7 送信完了後のリダイレクト
add_action('wp_footer', 'add_contact_form_redirect_script');
function add_contact_form_redirect_script() {
    if (is_page('contact')) {
        ?>
        <script>
        document.addEventListener('wpcf7mailsent', function(event) {
            location = '/thanks/';
        }, false);
        </script>
        <?php
    }
}
```

## プラグイン依存関係

お問い合わせページは **Contact Form 7** プラグインに依存しています。

**プラグインインストール:**
```bash
# WP-CLIを使用する場合
wp plugin install contact-form-7 --activate
```

または、WordPress管理画面から:
1. `プラグイン > 新規追加`
2. 「Contact Form 7」を検索
3. インストール＆有効化

## テスト手順

1. Contact Form 7 でフォーム作成（ID確認）
2. `page-contact.php` のショートコードIDを更新
3. フォーム送信テスト
   - 必須項目のバリデーション
   - メール送信（管理者宛・自動返信）
   - リダイレクト動作
4. レスポンシブ表示確認（PC/SP）

## スタイルカスタマイズ

スタイル調整が必要な場合は以下を編集:
- `/src/scss/object/projects/contact/_p-contact.scss`

ビルドコマンド:
```bash
npm run dev   # 開発環境
npm run build # 本番環境
```

## トラブルシューティング

### メールが送信されない

**原因:** SMTPサーバー設定不足

**解決策:**
- WP Mail SMTPプラグインを導入
- または、サーバーのSMTP設定を確認

### スタイルが反映されない

**原因:** ビルド未実行

**解決策:**
```bash
npm run build
```

### フォームが表示されない

**原因:** Contact Form 7プラグイン未有効化、またはショートコードID不正

**解決策:**
1. プラグイン有効化確認
2. `page-contact.php` のショートコードID確認
3. ブラウザのキャッシュクリア
