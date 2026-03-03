---
name: analyze-project
description: "/analyze-project - プロジェクト分析コマンド"
disable-model-invocation: true
allowed-tools:
  - Read
  - Bash
  - Glob
  - mcp__serena__read_memory
  - mcp__serena__write_memory
context: fork
agent: general-purpose
---

# /analyze-project - プロジェクト分析コマンド

レビュー履歴を分析し、傾向と改善提案を生成します。

## 実行手順

1. 分析スクリプトを実行:
```bash
node scripts/analyze-reviews.cjs
```

2. 結果を確認し、ユーザーに報告

3. 改善提案がある場合、対応方針を提案:
   - Lintルール追加
   - ガイドライン更新
   - リファクタリング計画

## オプション

- `--json`: JSON形式で出力（プログラム処理用）
- `--save`: 結果をメモリに保存

## 出力内容

- 問題サマリー（優先度別件数）
- 頻出パターン TOP5
- 問題が多いディレクトリ
- 自動修正率
- 改善提案

## 使用例

```
/analyze-project
/analyze-project --save  # メモリに保存
```

## 関連コマンド

- `/suggest-rules` - 分析結果から新ルールを提案
- `/qa full` - フルQAチェック
