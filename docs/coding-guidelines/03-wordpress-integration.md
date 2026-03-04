# WordPress統合規約（インデックス）

このセクションは以下のドキュメントに分割されています。

**SSOT**: `.claude/rules/wordpress.md`, `.claude/rules/security.md`

## ドキュメント一覧

| ファイル | 内容 |
|---------|------|
| [03-html-structure.md](03-html-structure.md) | HTML構造パターン・セマンティック規約 |
| [03-template-parts.md](03-template-parts.md) | テンプレートパーツ設計・分割規約 |
| [03-image-handling.md](03-image-handling.md) | 画像出力規約（render_responsive_image） |
| [03-sanitization.md](03-sanitization.md) | HTML出力サニタイズ規約 |

## クイックリファレンス

- **セクション設計**: 独立Block必須（`p-section-name`）、`p-page__section`禁止
- **画像**: テーマ静的画像は`render_responsive_image()`、WPアップロード画像は`wp_get_attachment_image()`
- **出力**: 全てエスケープ（`esc_html`, `esc_url`, `wp_kses_post`）
- **テンプレート分割**: 200行以上は分割、「迷ったら切り出さない」
