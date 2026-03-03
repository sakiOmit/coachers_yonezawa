# Scripts ディレクトリ

WordPressサイトの開発・運用に必要なスクリプト集です。

## 📁 ディレクトリ構成

```
scripts/
├── check/              # チェック系スクリプト
│   ├── links-static.ts     # リンクチェック（静的解析）
│   ├── links-crawl.ts      # リンクチェック（クローラー）
│   └── images-404.ts       # 画像404チェック
├── import/             # データインポート系
│   ├── tvcm-data.ts        # TVCMデータインポート
│   └── news-data.ts        # ニュースデータインポート
├── optimize/           # 最適化系
│   └── images.ts           # 画像最適化
├── wordpress/          # WordPress関連
│   ├── setup-pages.ts      # WordPressページセットアップ
│   └── create-templates.ts # ページテンプレート作成
└── README.md           # このファイル
```

---

## 🔍 チェック系スクリプト (check/)

### 統合チェック（推奨）

**ファイル**: `check/run-all.ts`
**コマンド**: `npm run check:all`

リンクチェック・画像チェックを一括実行し、Markdownレポートを生成します。

**実行内容**:
1. リンクチェック（静的解析）
2. リンクチェック（クローラー）
3. 画像404チェック
4. Markdownレポート生成

**特徴**:
- 🚀 ワンコマンドで全チェック実行
- 📝 Markdownレポート自動生成（`reports/check-report.md`）
- 📊 サマリー表示で問題を一目で把握
- 🎯 本番デプロイ前に最適

**使い方**:
```bash
# Docker環境起動
docker compose up -d

# 全チェック実行
npm run check:all

# カスタムURL
npm run check:all -- --base-url http://localhost:3000
```

**生成ファイル**（`reports/` ディレクトリ内）:
- `reports/check-report.md` - Markdownレポート
- `reports/link-check-report.json` - リンクチェック（静的）詳細
- `reports/link-crawl-report.json` - リンクチェック（クローラー）詳細
- `reports/image-check-report.json` - 画像チェック詳細

**クイックスタート**: [docs/check-workflow-quickstart.md](../docs/check-workflow-quickstart.md)

---

### リンクチェック（静的解析）

**ファイル**: `check/links-static.ts`
**コマンド**: `npm run check:links`

PHPファイル内のaタグを解析し、ダミーリンクを検出します。

**検出対象**:
- `href="#"` - ハッシュのみ
- `href=""` - 空のhref
- `href` 属性なし
- `href="https://example.com"` - プレースホルダードメイン

**特徴**:
- ⚡ 高速（数秒で完了）
- 🔍 PHP変数を自動除外（偽陽性を防ぐ）
- 📄 JSON レポート出力（`reports/link-check-report.json`）

**使い方**:
```bash
npm run check:links
```

---

### リンクチェック（クローラー）

**ファイル**: `check/links-crawl.ts`
**コマンド**: `npm run check:links:crawl`

実際のWebサイトをクロールし、リンク切れを検出します。

**検出対象**:
- リンク切れ（404, 500等）
- ダミーリンク
- リダイレクト（301, 302等）
- タイムアウト

**特徴**:
- 🎯 正確（実際のHTTPリクエスト）
- 🌐 外部リンクも検証
- 📄 JSON レポート出力（`reports/link-crawl-report.json`）

**使い方**:
```bash
# Docker環境起動
docker compose up -d

# デフォルト（localhost:8000）
npm run check:links:crawl

# カスタムURL
npm run check:links:crawl -- --base-url http://localhost:3000
```

---

### 画像404チェック

**ファイル**: `check/images-404.ts`
**コマンド**: `npm run check:images`

実際のWebサイトをクロールし、画像の404エラーを検出します。

**検出対象**:
- `<img src="...">`
- `<img srcset="...">` （Retina対応）
- `<source srcset="...">` （picture要素）

**特徴**:
- 🖼️ すべての画像タイプを検出
- 🎯 HTTPステータスコードをチェック
- 📄 JSON レポート出力（`reports/image-check-report.json`）

**使い方**:
```bash
# Docker環境起動
docker compose up -d

# デフォルト（localhost:8000）
npm run check:images

# カスタムURL
npm run check:images -- --base-url http://localhost:3000
```

**詳細ガイド**: [docs/link-check-guide.md](../docs/link-check-guide.md)

---

## 📥 データインポート系 (import/)

### TVCMデータインポート

**ファイル**: `import/tvcm-data.ts`
**コマンド**: `npm run tvcm:import`

YAMLファイルからTVCMデータをWordPressにインポートします。

**使い方**:
```bash
# config/tvcm-data.yaml を読み込んでインポート
npm run tvcm:import
```

**データソース**: `config/tvcm-data.yaml`

---

### ニュースデータインポート

**ファイル**: `import/news-data.ts`
**コマンド**: `npm run news:import`

YAMLファイルからニュースデータをWordPressにインポートします。

**使い方**:
```bash
# config/news-data.yaml を読み込んでインポート
npm run news:import
```

**データソース**: `config/news-data.yaml`

---

## 🎨 最適化系 (optimize/)

### 画像最適化

**ファイル**: `optimize/images.ts`
**コマンド**: `npm run image-opt`

画像ファイルを最適化し、WebP形式に変換します。

**処理内容**:
- JPEG/PNG の圧縮
- WebP 形式への変換
- ファイルサイズの削減

**使い方**:
```bash
npm run image-opt
```

**注意**: ビルドプロセス（`npm run build`）に自動的に含まれます。

---

## 🔧 WordPress関連 (wordpress/)

### WordPressページセットアップ

**ファイル**: `wordpress/setup-pages.ts`
**コマンド**: `npm run wp:setup`

YAMLファイルからWordPress固定ページを一括作成します。

**使い方**:
```bash
npm run wp:setup
```

**設定ファイル**: `config/wordpress-pages.yaml`

**作成される内容**:
- 固定ページ（スラッグ、タイトル、説明等）
- ページテンプレートの関連付け

---

### ページテンプレート作成

**ファイル**: `wordpress/create-templates.ts`
**コマンド**: `npm run wp:create-templates`

WordPressページテンプレートファイルを自動生成します。

**使い方**:
```bash
npm run wp:create-templates
```

**生成場所**: `themes/lpc-group-wp/pages/`

---

## 📋 よく使うワークフロー

### 開発中のチェック

```bash
# リンクの静的チェック（高速）
npm run check:links
```

### 本番デプロイ前

```bash
# Docker環境起動
docker compose up -d

# リンクチェック（完全）
npm run check:links:crawl

# 画像チェック
npm run check:images
```

### データ更新

```bash
# TVCMデータ更新
npm run tvcm:import

# ニュースデータ更新
npm run news:import
```

### ビルド

```bash
# 画像最適化 + ビルド（自動で image-opt が実行される）
npm run build
```

---

## 🛠️ トラブルシューティング

### スクリプトが見つからない

**原因**: package.json のパスが古い

**解決方法**:
```bash
# package.json を確認
grep "check:links" package.json

# 正しいパス: scripts/check/links-static.ts
```

### Docker環境エラー

**原因**: Docker環境が起動していない

**解決方法**:
```bash
# Docker環境起動
docker compose up -d

# 起動確認
docker compose ps
```

### 依存関係エラー

**原因**: node_modules が古い

**解決方法**:
```bash
# 依存関係を再インストール
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 関連ドキュメント

- [リンク・画像チェックガイド](../docs/link-check-guide.md) - 詳細な使い方
- [コーディングガイドライン](../CLAUDE.md) - プロジェクト全体の規約
- [WordPress移行ガイド](../tasks/wordpress-migration-guide.md) - WordPress関連タスク

---

## 🔄 スクリプト追加時の手順

新しいスクリプトを追加する際は、以下の手順に従ってください：

1. **適切なフォルダに配置**
   - チェック系 → `check/`
   - インポート系 → `import/`
   - 最適化系 → `optimize/`
   - WordPress関連 → `wordpress/`

2. **package.json にコマンド追加**
   ```json
   {
     "scripts": {
       "your-command": "tsx scripts/category/your-script.ts"
     }
   }
   ```

3. **このREADMEを更新**
   - 対応するセクションに説明を追加

4. **必要に応じてガイドを作成**
   - `docs/` ディレクトリに詳細ガイドを作成

---

**作成日**: 2025-11-09
**更新日**: 2025-11-18
