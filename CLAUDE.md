# Claude Code プロジェクトガイド

## プロジェクト概要

WordPress 6.x + ACF サイト。FLOCSS + BEM、Vite ビルド、Astro 静的コーディング → WordPress 変換の2段階ワークフロー。

## コマンド

```bash
npm run dev            # WordPress開発サーバー (Vite)
npm run build          # WordPress本番ビルド
npm run astro:dev      # Astro静的コーディングサーバー
npm run astro:build    # Astro静的ビルド
npm run lint:fix       # Lint自動修正
npm run docker:init    # Docker起動 + 自動セットアップ
```

## コア原則

- **エージェント必須**: コーディングタスクは専門エージェントを起動。メインが直接コードを書くことは禁止
- **SCSS**: BEM + kebab-case、`&__`ネスト、`rv()`/`svw()`、`@include container()`のみ、`@include hover`必須
- **WordPress**: セクション=独立Block（`p-page__section`禁止）、画像=`render_responsive_image()`、出力=全エスケープ
- **Astro**: BEMクラス名はWP版と完全一致、SCSS/JSは`.astro`内インポート禁止、`<ResponsiveImage />`使用
- **Figma**: nodeベース実装（スクリーンショットのみ実装禁止）、2倍書き出し
- **パーミッション**: PHP/CSS/JS=644、ディレクトリ=755

## エージェント起動判断

| タスク | エージェント |
|--------|-------------|
| WordPress・SCSS実装 | wordpress-professional-engineer → production-reviewer |
| Astroページ・コンポーネント | astro-component-engineer → production-reviewer |
| アニメーション | interactive-ux-engineer → production-reviewer |
| レビュー (`/review`) | production-reviewer |
| 修正 (`/fix`) | code-fixer |
| QA (`/qa`) | qa-agent |
| 納品チェック (`/delivery`) | delivery-checker |
| SCSS設計相談 | flocss-base-specialist |
| 設計レビュー | architecture-consultant |

## MCP

| MCP | 用途 |
|-----|------|
| Figma | デザイン解析（`get_design_context` 使用） |
| Playwright | ビジュアル検証（使用後は必ずプロセス終了・画像削除） |

## ルールファイル

`.claude/rules/` 配下。globs フロントマターにより対象ファイル編集時のみ自動ロード。
詳細: `docs/coding-guidelines/`、`.claude/agents/README.md`
