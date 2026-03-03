# MCP コンテキスト管理ガイド

## 重要: コンテキストウィンドウの最適化

MCPを過度に有効化すると、200kのコンテキストウィンドウが70k程度まで縮小します。

### 推奨設定

| 項目 | 推奨値 |
|------|--------|
| MCP総数 | 20-30個（設定ファイルに記述） |
| 有効化数 | 10個以下（プロジェクトごと） |
| アクティブツール | 80個以下 |

## このプロジェクトで使用するMCP

### 必須（常時有効）

| MCP | 用途 | ツール数 |
|-----|------|---------|
| serena | コード解析・編集・メモリ | 約20 |
| playwright | ビジュアル検証 | 約15 |

### 条件付き（タスクに応じて有効化）

| MCP | 用途 | 有効化タイミング |
|-----|------|-----------------|
| figma | デザイン解析 | Figma実装時のみ |
| chrome-devtools | パフォーマンス | 最適化作業時のみ |

## 設定方法

### プロジェクト単位で無効化

`.claude/settings.local.json`:

```json
{
  "disabledMcpServers": [
    "unused-mcp-1",
    "unused-mcp-2"
  ]
}
```

### グローバルで無効化

`~/.claude/settings.json`:

```json
{
  "disabledMcpServers": [
    "rarely-used-mcp"
  ]
}
```

## コンテキスト使用量の確認

会話中にコンテキストが不足した場合:

1. `/clear` で会話をリセット
2. 不要なMCPを `disabledMcpServers` に追加
3. 会話を再開

## このプロジェクトの現在設定

`settings.local.json`:

```json
{
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": [
    "serena",
    "figma-dev-mode-mcp-server",
    "playwright"
  ]
}
```

必要に応じて `disabledMcpServers` を追加してください。
