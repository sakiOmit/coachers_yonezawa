# WordPress Template

WordPress + Astro + FLOCSS + BEM で構築されたテンプレートプロジェクトです。

## ✨ 特徴

- 🚀 **完全自動セットアップ** - `npm run docker:init` だけで開発環境が整う
- ⚡ **Vite HMR対応** - SCSS/JSの変更が即座にブラウザに反映
- 🔧 **パーミッション自動修正** - Docker環境特有の権限問題を自動解決
- 🎨 **FLOCSS + BEM** - 保守性の高いCSS設計
- 🪐 **Astro静的コーディング** - Astroで先にデザイン実装・確認し、WordPress PHPへ変換
- 🤖 **AI支援ワークフロー** - Claude Codeエージェントによる実装・レビュー
- 📊 **QA自動化** - 納品前チェックリストの自動生成

---

## 🚀 クイックスタート

### 📦 テンプレートから新規プロジェクト作成

このリポジトリをテンプレートとして使用する場合：

```bash
# 1. GitHubで "Use this template" ボタンから新規リポジトリを作成
# 2. クローン
git clone https://github.com/your-org/your-new-project.git
cd your-new-project

# 3. 依存関係をインストール
npm install

# 4. プロジェクト初期化（対話形式でプロジェクト名などを設定）
npm run init
```

**`npm run init` で設定される内容:**
- プロジェクト名
- テーマディレクトリ名
- 会社名（日本語・英語）
- テキストドメイン
- パッケージ名

**詳細**: `docs/setup/project-template.md`

---

### 初回セットアップ（完全自動）

```bash
# 1. Docker起動 + 自動設定（初回のみ）
npm run docker:init

# 2. ブラウザで WordPress初期セットアップ
# http://localhost:8000 にアクセスしてWordPressをセットアップ

# 3. 開発サーバー起動
npm run dev
```

**自動実行される内容:**
- ✅ Docker起動
- ✅ wp-config.php自動設定（Vite HMR有効化）
- ✅ パーミッション自動修正（644/755）

### 日常の開発

```bash
# WordPress開発サーバー起動（HMR有効）
npm run dev

# Astro静的コーディングサーバー起動
npm run astro:dev

# ビルド
npm run build          # WordPress本番ビルド
npm run astro:build    # Astro静的ビルド

# Lint修正
npm run lint:fix
```

---

## 📋 作業フロー（重要）

### ⭐️ 現在の作業ステータスを確認
```bash
/next
```
→ **次に何をすべきか自動で案内されます**（迷ったらこれを実行）

### よくある作業パターン

#### 1️⃣ 新規ページ実装（Astro → WordPress）
```bash
# Step 1: Astroで静的コーディング
/astro-page-generator

# Step 2: 承認後、WordPress PHPへ変換
/astro-to-wordpress
```

#### 1️⃣-b Figmaから直接実装
```bash
/figma-implement
```
→ FigmaデザインからWordPress実装まで自動化

#### 2️⃣ コード修正・改善
```bash
# 軽微な修正
npm run lint:fix

# レビュー＋修正
/review  # → 問題検出 → 専門エージェントが修正
```

#### 3️⃣ 納品前チェック（最重要）
```bash
# Step 1: 完全QA実行（このチャット）
/qa full
→ チェックリスト生成: reports/delivery-checklist-YYYYMMDD.md

# Step 2: 課題修正（新規チャット推奨）
/delivery-fix
→ 対話形式で一つずつ修正

# Step 3: 最終確認
/qa verify
/delivery-report
→ クライアント提出用レポート更新
```

---

## 🎯 カスタムコマンド一覧

| コマンド | 用途 | チャット |
|---------|------|---------|
| **`/next`** | **次のステップ案内** | 現在 |
| `/astro-page-generator` | Astroページ対話的生成 | 現在 |
| `/astro-to-wordpress` | Astro → WordPress PHP変換 | 現在 |
| `/figma-implement` | Figma → WordPress実装 | 現在 |
| `/review` | 全コードレビュー（SCSS/JS/PHP/Astro） | 現在 |
| `/fix auto` | Safe issues自動修正 | 現在 |
| `/qa check` | QA統合チェック | 現在 |
| `/qa full` | 完全QA（納品前推奨） | 現在 |
| `/delivery check` | 納品品質チェック | 現在 |

---

## 📊 プロジェクト状態の確認

### 現在のステータスを知りたい
```bash
/next
```

### QA結果を確認したい
```bash
cat reports/qa-report.md
```

### 納品準備の進捗を確認したい
```bash
cat reports/delivery-checklist-20251215.md
# または
/delivery-fix --status
```

---

## 🗂️ プロジェクト構成

```
/
├── astro/                      # Astro静的コーディング環境
│   └── src/
│       ├── layouts/            # → header.php + footer.php
│       ├── pages/              # → pages/page-*.php
│       ├── components/         # → template-parts/
│       │   ├── common/         # 共通コンポーネント
│       │   ├── components/     # c-* コンポーネント
│       │   └── sections/{page}/ # セクション
│       ├── data/               # ACFモックデータ (JSON)
│       └── lib/                # ヘルパー関数
├── themes/{THEME_NAME}/        # WordPressテーマ
│   ├── pages/                  # ページテンプレート
│   ├── template-parts/         # 再利用パーツ
│   └── inc/                    # PHP機能分割
├── src/                        # 共有（Astro/WP両方が参照）
│   ├── scss/                   # FLOCSS構成
│   │   ├── foundation/         # 変数・mixin
│   │   ├── layout/             # ヘッダー・フッター
│   │   └── object/             # c-/p-/u-
│   ├── css/pages/              # ページ別エントリー
│   └── js/                     # JavaScript
├── reports/                    # QA・納品レポート
└── docs/                       # ドキュメント
```

---

## 📖 ドキュメント

- **プロジェクトガイド**: `CLAUDE.md`
- **コーディング規約**: `docs/coding-guidelines/`
- **Astroワークフロー**: `.claude/rules/astro.md`
- **納品ワークフロー**: `docs/workflows/delivery-workflow.md`
- **テンプレート化ガイド**: `docs/setup/project-template.md`

### テンプレート作成者向け

既存プロジェクトをテンプレート化する場合：

```bash
npm run create-template
```

詳細は `docs/setup/project-template.md` を参照

---

## 🔧 トラブルシューティング

### HMR（ホットリロード）が効かない

```bash
# 設定を再実行
npm run setup:vite-dev

# Dockerを再起動
docker compose restart

# Viteサーバーを再起動
npm run dev
```

ブラウザのコンソールで以下が表示されていることを確認：
- `http://localhost:3000/@vite/client`
- `http://localhost:3000/src/css/common.scss`

### パーミッションエラーが出る

```bash
# パーミッションを自動修正
npm run setup:vite-dev
```

または手動で修正：
```bash
# ディレクトリ: 755
find themes/{THEME_NAME} -type d -exec chmod 755 {} \;

# ファイル: 644
find themes/{THEME_NAME} -type f -name "*.php" -exec chmod 644 {} \;
```

### WordPress初期セットアップ後にwp-config.phpに設定が追加されない

```bash
# 手動で設定を実行
npm run setup:vite-dev
docker compose restart
```

### コマンドを忘れた
```bash
/next  # 次のステップを案内
```

### 何から始めればいいか分からない
```bash
/next  # 現在のプロジェクト状態から判断して案内
```

### 納品前に何をすべきか分からない
```bash
/qa full  # すべて自動で実行
```

---

## 🎓 初めての人向け

### 初回起動（プロジェクトを始める）

```bash
# 1. 完全自動セットアップ
npm run docker:init

# 2. WordPress初期設定（ブラウザ）
# http://localhost:8000 にアクセス
# サイト名、ユーザー名、パスワードを設定

# 3. Astro依存インストール（初回のみ）
npm run astro:install

# 4. 開発開始
npm run dev            # WordPress (port 3000/8000)
npm run astro:dev      # Astro静的コーディング (port 4321)
```

### 日常の作業フロー

#### 1. まず現在の状態を確認
```bash
/next
```

#### 2. 案内されたコマンドを実行
```bash
# 例: 「次は /qa full を実行してください」と表示された場合
/qa full
```

#### 3. 完了後、再度確認
```bash
/next  # 次のステップが表示される
```

**このサイクルを繰り返すだけで、適切なワークフローに従って作業できます。**

---

## 📞 ヘルプ

- **プロジェクト固有のルール**: `CLAUDE.md` を参照
- **Astroワークフロー**: `.claude/rules/astro.md` を参照
- **納品フロー**: `docs/workflows/delivery-workflow.md` を参照

---

## 🤖 エージェント構成

### 実装系
- `wordpress-professional-engineer` - WordPress・SCSS実装
- `astro-component-engineer` - Astroページ・コンポーネント実装
- `interactive-ux-engineer` - GSAP・アニメーション

### レビュー・修正系
- `production-reviewer` - 本番前統合レビュー（SCSS/JS/PHP/Astro）
- `code-fixer` - 統合修正
- `qa-agent` - QA統合チェック・修正

### 専門家系
- `flocss-base-specialist` - FLOCSS設計相談
- `architecture-consultant` - アーキテクチャ第三者レビュー
- `delivery-checker` - 納品チェックリスト生成

---

**迷ったら `/next` を実行してください。次にすべきことが自動で案内されます。**
