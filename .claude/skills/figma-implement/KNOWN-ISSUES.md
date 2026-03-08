# /figma-implement OPEN Issues

FIXED 済みの課題は削除済み（コード・ルールに反映済み）。

| # | Step | 概要 | Status |
|---|------|------|--------|
| 1 | 5 | nested-grouping-plan.yaml の構造情報を Step 5 で読み込み、pattern/セクション名/デザインコンテキストを総合して Claude にリンク判定させる（figma-prepare #254 関連） | OPEN |

## Issue 1: list-item リンク判定の改善

### 背景

figma-prepare の Stage C が出力する `nested-grouping-plan.yaml` には `pattern: "list"` 等の
セマンティック情報が含まれるが、現在 figma-implement はこのファイルを読んでいない。
結果、list-item が `<a>` でラップされるべきかの判断材料が不足し、
クリッカブル領域の誤解釈が発生する可能性がある。

### 方針

矢印アイコン等の単一シグナルでルール判定するのではなく、
figma-implement の Claude（Opus/Sonnet）に複数情報を渡して総合推論させる:

1. `nested-grouping-plan.yaml` の `pattern` / `name` / `reason`
2. `get_design_context` の hover state / style 情報
3. セクション名・CTA ボタンとの関連性
4. 一般的な Web デザインパターン（製品一覧 = リンク等）

### 実装ポイント

- Step 5（Project Convention Translate）で `nested-grouping-plan.yaml` を読み込み
- `pattern: "list"` のグループ情報を astro-component-engineer に渡す
- リンクかどうかの最終判断は Claude に委ねる（ルールは書かない）
