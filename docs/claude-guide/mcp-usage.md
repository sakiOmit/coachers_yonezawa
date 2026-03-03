# MCP サーバー使用ガイド

このドキュメントでは、プロジェクトで使用するMCPサーバーの詳細な使い方を説明します。

## 概要

| MCP | 主な用途 | 使用タイミング |
|-----|---------|---------------|
| Serena | コード解析・編集・メモリ | コード調査、シンボル検索、メモリ参照 |
| Figma | デザイン解析 | Figma実装時 |
| Playwright | ビジュアル検証 | 実装後の表示確認 |
| Chrome DevTools | パフォーマンス分析 | 本番前の性能検証 |

## Serena MCP

### シンボル検索

```
# クラス・関数を検索
find_symbol: name_path="ClassName/methodName"

# 部分一致検索
find_symbol: name_path="render", substring_matching=true

# 参照元を検索
find_referencing_symbols: name_path="functionName", relative_path="path/to/file.php"
```

### パターン検索

```
# 正規表現で検索
search_for_pattern: substring_pattern="font-size: rv\\(16\\)"

# ファイル種別を絞る
search_for_pattern: substring_pattern="@include sp", paths_include_glob="*.scss"
```

### メモリ機能

```
# メモリ読み込み
read_memory: memory_file_name="base-styles-reference.md"

# メモリ書き込み
write_memory: memory_file_name="refactor-plan.md", content="..."

# メモリ一覧
list_memories
```

### ベストプラクティス

- **ファイル全体を読まない** - `get_symbols_overview` → `find_symbol` で必要な部分のみ
- **メモリを活用** - 繰り返し参照する情報は `write_memory` で保存
- **相対パス指定** - `relative_path` で検索範囲を絞ってトークン節約

## Figma MCP

### デザイン取得

```
# デザインコンテキスト取得
get_design_context: figma_url="https://www.figma.com/..."

# メタデータのみ取得
get_metadata: figma_url="https://www.figma.com/..."

# スクリーンショット取得
get_screenshot: figma_url="https://www.figma.com/..."
```

### トークン制限対応

大きなデザインでnodeデータが省略される場合:

1. **セクション分割を依頼** - ユーザーにセクション別URLを送ってもらう
2. **セクションごとに取得** - 各URLで `get_design_context` を実行
3. **情報を統合** - 全セクションの情報が揃ってから実装

### 禁止事項

- スクリーンショットのみでのコーディング（node情報必須）
- クラス名の推測ベース実装

## Playwright MCP

### 基本操作

```
# ページ遷移
browser_navigate: url="http://localhost:8000/page/"

# セクション別スクリーンショット（推奨）
browser_screenshot: selector=".p-page__section", fullPage=false

# フルページスクリーンショット（最終確認のみ）
browser_screenshot: fullPage=true

# 要素の存在確認
browser_snapshot
```

### セクション単位検証の原則

**推奨:**
- CSSセレクタ指定でセクション単位キャプチャ
- 差分があったセクションのみ修正・再検証
- 最終確認時のみフルページスクリーンショット

**禁止:**
- フルページスクリーンショットのみでの検証
- セクション分割なしの一括検証

### ビューポートサイズ

`playwright-config.json` で設定:
- PC: 1440x900（デフォルト）
- SP: 375x812

## Chrome DevTools MCP

### パフォーマンス分析

```
# トレース開始
performance_start_trace: reload=true, autoStop=true

# トレース停止
performance_stop_trace

# インサイト分析
performance_analyze_insight: insightSetId="...", insightName="LCPBreakdown"
```

### ネットワーク・コンソール

```
# ネットワークリクエスト一覧
list_network_requests

# コンソールメッセージ一覧
list_console_messages: types=["error", "warn"]
```

### 使い分け

| タスク | 使用MCP |
|--------|---------|
| ビジュアル検証 | Playwright |
| レスポンシブ確認 | Playwright |
| パフォーマンス分析 | Chrome DevTools |
| JavaScriptエラー調査 | Chrome DevTools |
| Core Web Vitals | Chrome DevTools |

## セキュリティ注意事項

- 信頼できるMCPサーバーのみ使用
- 外部コンテンツをフェッチするMCPはprompt injectionリスクあり
- サードパーティMCPは自己責任でインストール

## トラブルシューティング

| 問題 | 対処法 |
|------|--------|
| MCPが応答しない | `--mcp-debug` フラグでデバッグ |
| ツールが見つからない | `.mcp.json` の設定確認 |
| タイムアウト | 複雑なクエリは分割して実行 |
