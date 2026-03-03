# プロジェクト構造・技術スタック

## 技術スタック

- **CMS**: WordPress 6.x
- **テーマ**: カスタムテーマ（`themes/{{THEME_NAME}}/`）
- **CSS設計**: FLOCSS (Foundation, Layout, Object)
- **スタイリング**: SCSS
- **ビルドツール**: Vite
- **開発環境**: Docker Compose（WordPress + MySQL + phpMyAdmin）
- **カスタムフィールド**: Advanced Custom Fields (ACF)

## ディレクトリ構成

```
/
├── themes/{{THEME_NAME}}/          # WordPressカスタムテーマ
│   ├── functions.php             # テーマ機能
│   ├── inc/                      # 機能分割
│   │   ├── enqueue.php           # CSS/JS読み込み
│   │   ├── custom-post-types.php # カスタム投稿タイプ
│   │   ├── setup.php             # テーマセットアップ
│   │   ├── image-helpers.php     # 画像ヘルパー関数
│   │   └── ...
│   ├── pages/                    # ページテンプレート
│   │   ├── page-vision.php       # ビジョンページ
│   │   ├── page-company.php      # 会社情報
│   │   ├── page-aboutus.php      # ABOUT US
│   │   ├── page-message.php      # メッセージ
│   │   ├── page-art.php          # アートプロジェクト
│   │   ├── page-contact.php      # お問い合わせ
│   │   ├── page-thanks.php       # サンクスページ
│   │   ├── page-privacy.php      # プライバシーポリシー
│   │   └── ...
│   ├── template-parts/           # 再利用可能パーツ
│   │   ├── common/
│   │   │   ├── page-header.php          # ページヘッダー
│   │   │   ├── breadcrumbs.php          # パンくず
│   │   │   ├── link-button.php          # 汎用リンクボタン
│   │   │   ├── section-heading.php      # セクション見出し
│   │   │   ├── numbered-heading.php     # 番号付き見出し
│   │   │   ├── infinite-scroll-text.php # 無限スクロールテキスト
│   │   │   └── pagination.php           # ページネーション
│   │   ├── home/                 # トップ専用パーツ
│   │   │   ├── section-kv.php           # キービジュアル
│   │   │   ├── section-business.php     # 事業紹介
│   │   │   ├── section-about.php        # About us
│   │   │   ├── section-news.php         # ニュース
│   │   │   ├── section-message.php      # メッセージ
│   │   │   ├── section-recruit.php      # 採用情報
│   │   │   └── top-heading.php          # セクション見出し（トップ用）
│   │   └── header/
│   │       └── navigation.php           # グローバルナビ
│   ├── front-page.php            # トップページ
│   ├── archive-tvcm.php          # TVCMギャラリー
│   ├── single.php                # 投稿詳細
│   ├── 404.php                   # 404エラーページ
│   └── assets/                   # ビルド済みアセット
│       ├── css/
│       └── js/
├── src/                          # ソースファイル
│   ├── scss/                     # SCSSソースファイル
│   │   ├── foundation/           # 基礎スタイル
│   │   │   ├── _variables.scss   # CSS変数定義
│   │   │   ├── _function.scss    # レスポンシブ関数
│   │   │   └── mixins/           # mixin集
│   │   ├── layout/               # レイアウト要素
│   │   │   ├── _header.scss
│   │   │   └── _footer.scss
│   │   └── object/
│   │       ├── components/       # 汎用コンポーネント（c-）
│   │       ├── projects/         # ページ固有スタイル（p-）
│   │       │   ├── _p-page-header.scss    # 共通ページヘッダー
│   │       │   ├── _p-pagination.scss    # ページネーション
│   │       │   ├── home/                 # トップ専用
│   │       │   │   ├── _p-kv.scss
│   │       │   │   ├── _p-business.scss
│   │       │   │   └── ...
│   │       │   ├── vision/               # ビジョンページ
│   │       │   ├── company/              # 会社情報
│   │       │   ├── aboutus/              # ABOUT US
│   │       │   ├── thanks/               # サンクスページ
│   │       │   ├── gallery/              # TVCMギャラリー
│   │       │   └── ...
│   │       └── utility/          # ユーティリティ（u-）
│   ├── css/
│   │   ├── common.scss           # 共通スタイル（全ページ読み込み）
│   │   └── pages/                # ページ別エントリーポイント
│   │       ├── top/style.scss
│   │       ├── vision/style.scss
│   │       ├── company/style.scss
│   │       ├── aboutus/style.scss
│   │       ├── thanks/style.scss
│   │       ├── gallery/style.scss
│   │       ├── contact/style.scss
│   │       └── ...
│   └── js/                       # JavaScriptファイル
├── config/                       # データファイル
│   ├── tvcm-data.yaml            # TVCMデータ
│   └── news-data.yaml            # ニュースデータ
├── scripts/                      # ユーティリティスクリプト
│   ├── import-tvcm-data.ts       # TVCMインポート
│   └── import-news-data.ts       # ニュースインポート
├── docs/                         # ドキュメント
│   └── coding-guidelines/        # コーディング規約
│       ├── README.md
│       ├── 01-project-structure.md
│       ├── 02-scss-design.md
│       ├── 03-wordpress-integration.md
│       ├── 04-build-configuration.md
│       ├── 05-checklist.md
│       └── 06-faq.md
├── .serena/memories/             # Serenaメモリ（プロジェクト知識）
│   └── base-styles-reference.md  # ベーススタイル一覧
├── vite.config.js                # Viteビルド設定
└── docker-compose.yml            # Docker環境設定
```

## 実装済みページ一覧

| スラッグ                 | テンプレートファイル                  | CSS                              | 説明                         |
| ------------------------ | ------------------------------------- | -------------------------------- | ---------------------------- |
| `/`                      | `front-page.php`                      | `style-top.css`                  | トップページ                 |
| `/vision/`               | `pages/page-vision.php`               | `style-vision.css`               | ビジョン                     |
| `/company/`              | `pages/page-company.php`              | `style-company.css`              | 会社情報                     |
| `/aboutus/`              | `pages/page-aboutus.php`              | `style-aboutus.css`              | ABOUT US                     |
| `/message/`              | `pages/page-message.php`              | `style-message.css`              | メッセージ                   |
| `/art/`                  | `pages/page-art.php`                  | `style-art.css`                  | アートプロジェクト           |
| `/contact/`              | `pages/page-contact.php`              | `style-contact.css`              | お問い合わせ                 |
| `/thanks/`               | `pages/page-thanks.php`               | `style-thanks.css`               | サンクスページ               |
| `/tvcm/`                 | `archive-tvcm.php`                    | `style-gallery.css`              | TVCMギャラリー               |
| `/news/`                 | `index.php`                           | （共通CSS）                      | お知らせ一覧                 |
| `/news/:slug/`           | `single.php`                          | `style-news.css`                 | お知らせ詳細                 |
| `/privacy/`              | `pages/page-privacy.php`              | `style-privacy.css`              | プライバシーポリシー         |
| `/privacy-recruit/`      | `pages/page-privacy-recruit.php`      | `style-privacy-recruit.css`      | プライバシーポリシー（採用） |
| `/privacy-social-media/` | `pages/page-privacy-social-media.php` | `style-privacy-social-media.css` | プライバシーポリシー（SNS）  |
| `/recruit-message/`      | `pages/page-recruit-message.php`      | `style-recruit-message.css`      | 採用メッセージ               |
| `404`                    | `404.php`                             | `style-404.css`                  | 404エラーページ              |

## Serenaメモリ機能

プロジェクト固有の重要情報は `.serena/memories/` に保存されています。

| メモリファイル                       | 内容                          | 用途                               |
| ------------------------------------ | ----------------------------- | ---------------------------------- |
| `base-styles-reference.md`           | ベーススタイル一覧            | コンポーネント作成時の重複チェック |
| `wordpress_render_function_patterns` | WordPressレンダリングパターン | テンプレート実装時の参考           |

**Serenaメモリの読み込み:**
Serena MCPを使用時、必要に応じて `read_memory` ツールでこれらのメモリを読み込み、コーディング規約の遵守を徹底できます。

## よく使うコマンド

### npmコマンド

```bash
# 開発サーバー起動
npm run dev

# 本番ビルド
npm run build

# WordPressデータインポート
npm run tvcm:import    # TVCMデータ
npm run news:import    # ニュースデータ

# 画像最適化
npm run image-opt      # 画像最適化実行
npm run image-retina   # Retina画像生成

# コード品質チェック
npm run lint           # ESLint + Stylelint
npm run lint:fix       # 自動修正
npm run format         # Prettier実行
```

### Dockerコマンド

```bash
# Docker環境起動
docker compose up -d

# Docker環境停止
docker compose down

# Docker環境確認
docker compose ps
```
