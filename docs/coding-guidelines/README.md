# LPCグループWP コーディング規約

このドキュメントは、プロジェクトで統一すべきコーディングパターンと規約をまとめたものです。

## 📂 ドキュメント構成

規約は以下のファイルに分割されています。**必要な時に必要なファイルのみを読み込んでください。**

### 📋 全体把握・構造理解

- **[01-project-structure.md](./01-project-structure.md)**
  - プロジェクト構造・ディレクトリ構成
  - 技術スタック
  - 実装済みページ一覧
  - Serenaメモリ機能

### 🎨 SCSS実装時

- **[02-scss-design.md](./02-scss-design.md)**
  - FLOCSS + BEM命名規則
  - レスポンシブ設計（rv/svw/pvw関数）
  - コンテナ幅設定
  - ベーススタイル継承ルール
  - エントリーポイントの書き方

### 🔌 WordPress実装時

- **[03-wordpress-integration.md](./03-wordpress-integration.md)**（インデックス）
  - [03-html-structure.md](./03-html-structure.md) - HTML構造・セマンティック規約
  - [03-template-parts.md](./03-template-parts.md) - テンプレートパーツ設計規約
  - [03-image-handling.md](./03-image-handling.md) - 画像出力規約
  - [03-sanitization.md](./03-sanitization.md) - サニタイズ規約

### ⚙️ ビルド設定時

- **[04-build-configuration.md](./04-build-configuration.md)**
  - vite.config.js エントリーポイント追加
  - enqueue.php 読み込み設定
  - 本番ビルド確認方法

### ✅ 新規ページ作成時

- **[05-checklist.md](./05-checklist.md)**
  - ステップバイステップチェックリスト
  - 必須確認項目
  - 動作確認手順

### ⚠️ レビュー・修正時

- **[06-faq.md](./06-faq.md)**
  - よくある規約違反パターン
  - アンチパターン集
  - FAQ（よくある質問）
  - 参考実装ファイル

### 📁 template-parts / SCSS対応

- **[07-template-parts-scss-mapping.md](./07-template-parts-scss-mapping.md)**
  - template-partsとSCSSの1対1対応ルール
  - 命名規則の変換ルール
  - ファイル分割の判断基準
  - 対応表テンプレート

### 📦 ライブラリ統合時

- **[08-library-integration.md](./08-library-integration.md)**
  - SimpleBar / Splide / GSAP 統合方法
  - iOS対応ベストプラクティス
  - 二重初期化の回避方法
  - レスポンシブ対応パターン
  - トラブルシューティング

## 🎯 使い方ガイド（エージェント向け）

### ケース別の読み込みファイル

| 実装タスク | 読み込むファイル | 順序 |
|-----------|----------------|------|
| **プロジェクト初見** | `01-project-structure.md` | 最初に読む |
| **新規ページ作成** | `05-checklist.md` → 必要に応じて `02`, `03`, `04` | チェックリストから開始 |
| **SCSSコンポーネント作成** | `02-scss-design.md` | SCSS規約のみ |
| **WordPressテンプレート作成** | `03-html-structure.md` + `03-template-parts.md` | WordPress規約 |
| **画像出力実装** | `03-image-handling.md` | 画像出力規約 |
| **ビルドエラー対応** | `04-build-configuration.md` | ビルド設定のみ |
| **コードレビュー** | `06-faq.md` → 該当する規約ファイル | アンチパターン確認 |
| **既存コード修正** | `06-faq.md` で参考実装確認 → 該当規約 | 模範例から学ぶ |
| **template-parts作成** | `07-template-parts-scss-mapping.md` → `03` | 対応ルール確認 |
| **ライブラリ実装** | `08-library-integration.md` | SimpleBar/Splide/GSAP |

### 効率的な読み込み方

1. **最小限の読み込み**: 必要なセクションのみを読む
2. **並列読み込み**: 複数のエージェントで分担可能
3. **段階的読み込み**: チェックリスト → 詳細規約 の順

## 🚨 重要ルールまとめ（クイックリファレンス）

### SCSS設計
- ✅ エントリーポイントには`@use`のみ
- ✅ コンテナ幅は`__container` + `@include container`
- ✅ デフォルトPC、`@include sp`でオーバーライド
- 🚫 `&-`ネスト記法は絶対禁止
- 🚫 `@include pc`と`@include sp`の併用禁止

### WordPress連携
- ✅ 画像出力は`render_responsive_image()`必須
- ✅ Template Nameコメント必須
- ✅ PageHeaderコンポーネント活用

### ビルド設定
- ✅ vite.config.js エントリーポイント追加必須
- ✅ `npm run build`で生成確認

## 📝 ドキュメント更新時の注意

規約を更新する際は、該当するファイルのみを編集してください。

- プロジェクト構造変更 → `01-project-structure.md`
- SCSS規約変更 → `02-scss-design.md`
- WordPress規約変更 → `03-*.md`（該当する分割ファイル）
- ビルド設定変更 → `04-build-configuration.md`
- チェックリスト追加 → `05-checklist.md`
- FAQ追加 → `06-faq.md`
- template-parts/SCSS対応 → `07-template-parts-scss-mapping.md`
- ライブラリ統合追加 → `08-library-integration.md`

---

**注**: 旧`CODING_GUIDELINES.md`は非推奨です。このディレクトリ配下のファイルを使用してください。
