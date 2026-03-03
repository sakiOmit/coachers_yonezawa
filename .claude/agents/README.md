# エージェント詳細ガイド

## 自動起動の仕組み

コーディングタスクを検出すると、Claudeが**自動的に専門エージェントを起動**します。
ユーザーが明示的に「エージェントを起動して」と指示する必要はありません。

| ユーザーの指示例 | 自動起動されるエージェント |
| ---------------- | -------------------------- |
| 「このページを実装して」 | `wordpress-professional-engineer` |
| 「SCSSを修正して」 | `wordpress-professional-engineer` |
| 「Astroでページを作って」 | `astro-component-engineer` |
| 「Astroコンポーネントを追加」 | `astro-component-engineer` |
| 「アニメーションを追加」 | `interactive-ux-engineer` |
| 「コードをレビューして」 | `production-reviewer` |
| 「QAチェックして」 | `qa-agent` |
| （実装完了時） | `production-reviewer`（proactive） |

**メインエージェント（Claude本体）が直接コードを書くことは禁止。** 理由：

- 専門エージェントはコーディング規約を熟知
- レビュー・修正のワークフローが確立
- 品質の一貫性を担保

## エージェント一覧

| エージェント | 用途 | プロンプト |
|-------------|------|-----------|
| wordpress-professional-engineer | WordPress・SCSS実装 | `wordpress-professional-engineer.md` |
| production-reviewer | 統合レビュー（SCSS/JS/PHP） | `production-reviewer.md` |
| code-fixer | 統合修正（SCSS/JS/PHP） | `code-fixer.md` |
| qa-agent | QA統合チェック・修正 | `qa-agent.md` |
| flocss-base-specialist | SCSS設計相談 | `flocss-base-specialist.md` |
| interactive-ux-engineer | GSAP・Lottie・アニメーション | `interactive-ux-engineer.md` |
| astro-component-engineer | Astroコンポーネント・ページ実装 | `astro-component-engineer.md` |
| architecture-consultant | アーキテクチャ第三者レビュー | `architecture-consultant.md` |
| delivery-checker | 納品品質チェック・レポート生成 | `delivery-checker.md` |

## 起動判断（Claude内部ロジック）

### エージェント起動するケース

- すべてのコーディング作業
- コード検索・調査が複数回必要
- 複数ファイルにまたがる変更
- 本番デプロイ前のレビュー
- 新規ページ作成

### メインで直接対応するケース

- 設定ファイルの軽微な修正（1行程度）
- ドキュメント編集
- 質問への回答・相談

## 推奨連携パターン

| タスク | エージェント連携 |
|--------|-----------------|
| 新規ページ実装（WP） | wordpress-professional-engineer → production-reviewer |
| 新規ページ実装（Astro） | astro-component-engineer → production-reviewer |
| Astro → WordPress変換 | wordpress-professional-engineer → production-reviewer |
| SCSS最適化 | production-reviewer → flocss-base-specialist |
| アニメーション | interactive-ux-engineer → production-reviewer |
| Figma実装 | wordpress-professional-engineer → production-reviewer |
| 納品前チェック | production-reviewer → delivery-checker |

**Note**: 独立したページは複数エージェントを並列起動可能

## スラッシュコマンドとの対応

| コマンド | 起動エージェント |
|----------|-----------------|
| `/review` | production-reviewer |
| `/fix` | code-fixer |
| `/qa` | qa-agent |
| `/delivery` | delivery-checker |
| `/architecture-review` | architecture-consultant |

## 各エージェントの詳細

### wordpress-professional-engineer

WordPress/SCSS実装の主力エージェント。
- 新規ページ作成（page-*.php + SCSS + vite.config.js）
- SCSS実装（FLOCSS + BEM準拠）
- ACFフィールド実装
- 画像出力（render_responsive_image()使用）

### production-reviewer

コード品質を統合レビュー。
- FLOCSS + BEM命名規則チェック
- セキュリティ（XSS, SQLi）チェック
- ベーススタイル重複検出
- 未使用コード検出

### code-fixer

レビュー結果に基づく修正実行。
- Safe issues: 自動修正
- Risky issues: 承認後修正

### qa-agent

QA統合チェックと修正。
- Lint（SCSS/JS/PHP）
- リンクチェック
- 画像チェック
- 自動修正対応

### flocss-base-specialist

SCSS設計相談。
- ベーススタイル抽出提案
- FLOCSS構造最適化
- 変数・mixin改善

### interactive-ux-engineer

アニメーション・インタラクション実装。
- GSAP + ScrollTrigger
- Lottie
- CSS Animation
- パフォーマンス最適化

### astro-component-engineer

Astro静的コーディング環境でのページ・コンポーネント実装。
- Astroページ作成（pages/*.astro + セクションコンポーネント + データJSON）
- 共通コンポーネント作成（Props interface + BEM + WordPress変換先マッピング）
- SCSS接続（@root-src経由の共有SCSS参照）
- ACFモックデータモデリング（JSON形式）

### architecture-consultant

アーキテクチャの第三者レビュー。
- 設計一貫性評価
- 技術的負債検出
- スケーラビリティ評価

### delivery-checker

納品品質チェック・レポート生成。
- 自動チェック（リンク、画像、パフォーマンス、SEO）
- コード品質検証
- レポート生成
