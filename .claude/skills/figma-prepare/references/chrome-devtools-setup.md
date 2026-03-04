# Chrome DevTools MCP Setup

## Overview

Phase 2-4 では Chrome DevTools MCP を使い、ブラウザ上の Figma Plugin API (`figma` グローバル) を `evaluate_script` で直接実行する。

## 前提条件

| 項目 | 必要 |
|------|------|
| Google Chrome | インストール済み |
| Figma デスクトップアプリ **または** Chrome で Figma Web | いずれか |
| chrome-devtools-mcp | `.mcp.json` に登録済み |

## セットアップ手順

### 1. Chrome DevTools MCP の登録

`.mcp.json` に以下を追加:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest"]
    }
  }
}
```

### 2. Chrome をリモートデバッグモードで起動

```bash
# Linux
google-chrome --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Windows (WSL2からの場合)
"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9222
```

### 3. Figma ファイルを Chrome で開く

1. Chrome で対象の Figma ファイル（**ブランチ**）を開く
2. Figma のプラグインを一度開閉する（`figma` グローバルを初期化）
   - メニュー → Plugins → 任意のプラグインを開く → 閉じる

### 4. 接続確認

```javascript
// evaluate_script で実行
typeof figma
// 期待結果: "object"
```

```javascript
// ファイル名確認
figma.root.name
// 期待結果: "ファイル名"
```

## トラブルシューティング

### `figma` が undefined

**原因**: Figma Plugin API が初期化されていない

**解決策**:
1. Figma のプラグインパネルを開く（何でもよい）
2. プラグインを閉じる
3. 再度 `typeof figma` を試行

### Chrome DevTools MCP に接続できない

**原因**: Chrome がリモートデバッグモードで起動していない

**解決策**:
1. Chrome を完全に終了
2. `--remote-debugging-port=9222` 付きで再起動
3. `http://localhost:9222/json` にアクセスしてタブ一覧が表示されることを確認

### タイムアウトエラー

**原因**: バッチサイズが大きすぎる

**解決策**:
- バッチサイズを 50 → 25 に縮小
- 処理間に適切なウェイトを挿入

## セキュリティ注意事項

- Chrome DevTools MCP はローカルマシン上でのみ使用
- リモートデバッグポートを外部に公開しない
- 作業完了後は Chrome を通常モードで再起動を推奨
