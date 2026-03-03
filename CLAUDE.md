# Claude Code プロジェクトガイド

## クイックリファレンス

### よく使うコマンド

```bash
npm run dev            # WordPress開発サーバー (Vite)
npm run build          # WordPress本番ビルド
npm run astro:dev      # Astro静的コーディングサーバー
npm run astro:build    # Astro静的ビルド
npm run astro:install  # Astro依存インストール
npm run lint:fix       # Lint自動修正
npm run docker:init    # Docker起動 + 自動セットアップ（初回推奨）
npm run check:all      # リンク・画像チェック一括実行
```

### カスタムコマンド

```bash
# --- 実装系 ---
/figma-analyze             # Figma複数ページ分析・戦略策定
/figma-implement           # Figma → WordPress完全実装
/figma-to-code             # Figmaデザイン調査・コード確認
/astro-page-generator      # Astroページ対話的生成
/astro-to-wordpress        # Astro → WordPress PHP変換
/wordpress-page-generator  # WordPressページテンプレート生成
/scss-component-generator  # SCSSコンポーネント生成

# --- 品質系 ---
/review                    # コードレビュー（SCSS + JS + PHP）
/fix                       # レビュー指摘の修正
/qa                        # QA統合チェック
/delivery                  # 納品品質チェック
```

## プロジェクト構成

- **CMS**: WordPress 6.x + ACF
- **CSS設計**: FLOCSS + BEM
- **ビルド**: Vite
- **静的コーディング**: Astro（SCSS共有）
- **環境**: Docker Compose

```text
wordpress-template/
├── astro/                          # 静的コーディング環境
│   └── src/
│       ├── layouts/                # BaseLayout.astro → header.php + footer.php
│       ├── pages/                  # *.astro → pages/page-*.php
│       ├── components/
│       │   ├── common/             # 共通コンポーネント → template-parts/common/
│       │   ├── components/         # 再利用コンポーネント → template-parts/components/
│       │   └── sections/{page}/    # セクション → template-parts/{page}/
│       ├── data/                   # ACFモックデータ (JSON)
│       │   ├── site-info.json      # ACFオプションページ相当
│       │   └── pages/              # ページ別フィールド
│       └── lib/                    # ヘルパー関数
├── config/
│   ├── theme.js                    # テーマ名自動検出
│   └── wordpress-pages.yaml        # WP固定ページ定義
├── scripts/
│   ├── init-project.js             # プロジェクト初期化
│   ├── lib/
│   │   ├── detect-theme.js         # テーマ自動検出 (JS)
│   │   └── detect-theme.ts         # テーマ自動検出 (TS)
│   ├── check/                      # QAチェックスクリプト
│   ├── qa/                         # QA統合
│   └── wordpress/                  # WPセットアップ自動化
├── src/                            # 共有ソース（Astro/WP両方が参照）
│   ├── scss/
│   │   ├── foundation/             # 変数・mixin・リセット
│   │   ├── layout/                 # l-header, l-footer, hamburger-menu
│   │   └── object/
│   │       ├── component/          # c-* 再利用コンポーネント
│   │       ├── project/            # p-* ページ固有スタイル
│   │       │   └── {page}/         # ページ単位でディレクトリ分割
│   │       └── utility/            # u-* ユーティリティ
│   ├── css/
│   │   ├── common.scss             # 共通CSSエントリー
│   │   └── pages/{page}/style.scss # ページ別CSSエントリー
│   ├── js/
│   │   ├── main.js                 # 共通JSエントリー
│   │   ├── modules/                # 共通JSモジュール
│   │   └── pages/{page}/index.js   # ページ別JSエントリー
│   └── images/                     # 画像ソース（image-optで最適化）
├── themes/
│   ├── {{THEME_DIR}}/              # WordPressテーマ
│   │   ├── pages/                  # ページテンプレート (page-*.php)
│   │   ├── template-parts/
│   │   │   ├── common/             # 共通パーツ
│   │   │   ├── components/         # 再利用コンポーネント
│   │   │   └── sections/           # セクション単位パーツ
│   │   ├── inc/
│   │   │   ├── advanced-custom-fields/ # ACFフィールドグループ
│   │   │   ├── custom-post-types/  # CPT登録
│   │   │   └── helpers/            # ヘルパー関数
│   │   ├── assets/                 # ビルド成果物（Vite出力先）
│   │   └── functions.php           # メインエントリー
│   └── index.php                   # WP必須ファイル
└── docker/                         # Docker設定
```

## コア原則

### SCSS（必須）

- **BEM命名**: kebab-case、`&__`ネスト必須
- **レスポンシブ**: PC First → `@include sp`でSP
- **関数**: `rv()` PC用、`svw()` SP用
- **container**: `@include container()`のみ記述可能（他プロパティ禁止）
- **ホバー**: `@include hover`必須（`:hover`直接記述禁止）

詳細: `.claude/rules/scss.md`

### WordPress（必須）

- **セクション**: 独立Block（`p-section-name`）、`p-page__section`禁止
- **画像**: `render_responsive_image()`必須、Figmaから2倍書き出し
- **テンプレート**: `Template Name`コメント必須
- **出力**: 全てエスケープ（`esc_html`, `esc_url`, `wp_kses_post`）

詳細: `.claude/rules/wordpress.md`, `.claude/rules/security.md`

### パーミッション

- PHP/CSS/JS: `644`、ディレクトリ: `755`
- Dockerファイル操作: `docker compose exec`経由

詳細: `docs/setup/initial-setup.md`

## エージェント

コーディングタスク検出時、専門エージェントを**自動起動**。
メインエージェントが直接コードを書くことは**禁止**。

| エージェント                    | 用途                              |
| ------------------------------- | --------------------------------- |
| wordpress-professional-engineer | WordPress・SCSS実装               |
| astro-component-engineer        | Astroページ・コンポーネント実装   |
| production-reviewer             | 統合レビュー（SCSS/JS/PHP/Astro） |
| code-fixer                      | 統合修正                          |
| qa-agent                        | QA統合チェック・修正              |
| interactive-ux-engineer         | GSAP・Lottie・アニメーション      |
| delivery-checker                | 納品品質チェック                  |
| flocss-base-specialist          | SCSS設計相談                      |
| architecture-consultant         | アーキテクチャ第三者レビュー      |

詳細: `.claude/agents/README.md`

## MCP

| MCP        | 用途                                     |
| ---------- | ---------------------------------------- |
| Serena     | コード解析・編集・メモリ                 |
| Figma      | デザイン解析（`get_design_context`使用） |
| Playwright | ビジュアル検証                           |

**Figma**: nodeベース実装徹底、スクリーンショットのみ実装禁止
**Playwright**: セクション単位検証、フルページは最終確認のみ

詳細: `docs/claude-guide/mcp-usage.md`

## 拡張機能

### Rules（モジュラー規約）

`.claude/rules/`: security, scss, wordpress, coding-style, astro

### Hooks

`debug-code-detector.py`: コミット前にデバッグコード自動検出

### フィードバックループ

- 同じ問題が3回検出 → Lintルール/ガイドライン自動更新
- `/learn`で手動記録可能

詳細: Serenaメモリ（`common-issues-patterns.md`等）

## 作業時の注意

1. **Just-in-Time読み込み** - 必要な規約のみ参照
2. **既存活用** - `page-header`, `link-button`等を使う
3. **レビュー必須** - 本番前は production-reviewer
4. **納品前** - delivery-checker でチェック

## 詳細ドキュメント

| カテゴリ          | ファイル                                             |
| ----------------- | ---------------------------------------------------- |
| 初回セットアップ  | `docs/setup/initial-setup.md`                        |
| SCSS規約          | `docs/coding-guidelines/02-scss-design.md`           |
| WordPress規約     | `docs/coding-guidelines/03-wordpress-integration.md` |
| 新規ページ        | `docs/coding-guidelines/05-checklist.md`             |
| Docker            | `docs/coding-guidelines/09-docker-scripting.md`      |
| エージェント      | `.claude/agents/README.md`                           |
| Astroワークフロー | `.claude/rules/astro.md`                             |

## プロジェクト固有ルール

技術固有のルールは `.claude/rules/` 配下を参照せよ。
ルールファイルは必要に応じて自動的に読み込まれる。
