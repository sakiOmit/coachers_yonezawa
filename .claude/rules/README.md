# Claude Code Rules

## Overview

このディレクトリには、プロジェクト固有のコーディングルールがモジュール化されて格納されています。
エージェントは必要に応じてこれらのルールを参照し、一貫した品質のコードを生成します。

## ルールファイル一覧

| ファイル | 内容 | 対象 |
|---------|------|------|
| `security.md` | セキュリティルール | XSS, SQLi, CSRF対策 |
| `scss.md` | SCSS/CSS規約 | FLOCSS + BEM |
| `wordpress.md` | WordPress固有ルール | テンプレート, ACF |
| `coding-style.md` | 一般コーディング | 命名, 構成, エラー処理 |
| `skill.md` | スキル作成規約 | SKILL.md形式, フロントマター |
| `astro.md` | Astroワークフロー | 静的コーディング, 変換規約 |
| `figma.md` | Figma実装規約 | キャッシュ, 分割, Code Connect, 再利用 |
| `agents.md` | エージェント規約 | MCP参照, ツール名 |

## 使い方

### エージェントによる自動参照

各エージェントは作業内容に応じて適切なルールを自動的に参照します:

- **SCSS実装時**: `scss.md` + `coding-style.md`
- **PHP/WordPress実装時**: `wordpress.md` + `security.md` + `coding-style.md`
- **JavaScript実装時**: `security.md` + `coding-style.md`
- **スキル作成時**: `skill.md`
- **Astro実装時**: `astro.md` + `scss.md` + `coding-style.md`
- **Figma実装時**: `figma.md` + `scss.md` + `wordpress.md`

### 手動参照

特定のルールを確認したい場合:

```
「security.mdのXSS対策を確認して」
「scss.mdのBEM命名規則を教えて」
```

## ルールの更新

### 閾値ベース自動更新

同じ問題が3回検出されると、該当するルールファイルに自動追加されます。

### 手動追加

新しいルールを追加する場合:

1. 該当するルールファイルを編集
2. チェックリストに項目を追加
3. 必要に応じてCLAUDE.mdのクイックリファレンスにも追加

## 設計方針

- **モジュール化**: ルール種別ごとに分離し、更新・共有を容易に
- **実用性重視**: 具体的なコード例を含める
- **チェックリスト**: 各ファイル末尾にレビュー用チェックリスト

## 関連ファイル

- `CLAUDE.md` - プロジェクトガイド（クイックリファレンス）
- `docs/coding-guidelines/` - 詳細なコーディングガイドライン
- `.claude/mcp-configs/README.md` - MCP管理ガイド
