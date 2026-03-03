---
name: architecture-review
description: "アーキテクチャレビュー"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Glob
  - Grep
  - mcp__serena__list_dir
  - mcp__serena__get_symbols_overview
context: fork
agent: general-purpose
---

# アーキテクチャレビュー

第三者視点でプロジェクト全体のアーキテクチャをスクリーニングします。

## 実行内容

architecture-consultant エージェントを起動し、以下の観点でレビューを実施:

1. **構造的一貫性** - FLOCSS・BEM・命名規則
2. **関心の分離** - 責務の明確化
3. **再利用性** - コンポーネント設計
4. **保守性** - 可読性・ドキュメント
5. **スケーラビリティ** - 拡張性
6. **パフォーマンス** - 最適化状況
7. **セキュリティ** - 脆弱性チェック

## 使用方法

```
/architecture-review           # 全体レビュー
/architecture-review scss      # SCSS設計に特化
/architecture-review wordpress # WordPress構造に特化
/architecture-review js        # JavaScript設計に特化
```

---

$ARGUMENTS の内容に基づいてレビュー範囲を決定してください。

引数がない場合は「全体レビュー」を実施してください。

引数の解釈:
- `scss` / `css` / `style` → SCSS設計レビュー
- `wordpress` / `wp` / `php` → WordPress構造レビュー
- `js` / `javascript` → JavaScript設計レビュー
- `build` / `vite` → ビルド設定レビュー
- `docker` / `env` → 開発環境レビュー
- その他 / 空 → 全体レビュー

## エージェント起動

Task tool で architecture-consultant エージェントを起動し、以下のプロンプトを渡してください:

```
プロジェクトのアーキテクチャレビューを実施してください。

レビュー範囲: [引数に基づく範囲]

手順:
1. Serena MCPでディレクトリ構造・ファイル構成を確認
2. 該当範囲の設定ファイル・ソースコードを分析
3. レビュー観点に基づいて評価
4. 問題をCRITICAL/WARNING/INFOで分類
5. 改善ロードマップを提案
6. Markdownレポートを作成

レポートは reports/architecture-review-[日付].md に出力してください。

重要: 実装は行わず、レビューとアドバイスのみを行ってください。
```

## 出力

- `reports/architecture-review-YYYY-MM-DD.md` - レビューレポート
- コンソールにサマリーを表示

## 推奨実行タイミング

- スプリント終了時（変更範囲のみ）
- マイルストーン達成時（全体）
- リリース前（全体）
- 技術的負債が気になった時
