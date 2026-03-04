# Chrome DevTools MCP Setup

## Overview

Phase 2-4 では Chrome DevTools MCP を使い、ブラウザ上の Figma Plugin API (`figma` グローバル) を `evaluate_script` で直接実行する。

## 前提条件

| 項目 | 必要 |
|------|------|
| Google Chrome (Windows) | インストール済み |
| Chrome で Figma Web | ログイン済み |
| chrome-devtools-mcp | `.mcp.json` に登録済み（`--browserUrl` 付き） |
| SSH トンネル (WSL2) | ポート 9222 転送 |

## セットアップ手順

### 1. `.mcp.json` への登録

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest", "--browserUrl", "http://127.0.0.1:9222"]
    }
  }
}
```

**重要**: `--browserUrl` がないと MCP が Chrome に接続できない。

### 2. Chrome をリモートデバッグモードで起動

#### Windows（WSL2 環境での推奨手順）

```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="C:\Users\%USERNAME%\.chrome-debug" ^
  https://www.figma.com/design/{fileKey}/{fileName}
```

**Chrome 136+ の必須要件**:
- `--remote-debugging-port` だけでは TCP リスナーが起動しない
- `--user-data-dir` を通常のプロファイルとは**別のディレクトリ**に指定する必要がある
- `C:\Users\{username}\.chrome-debug` のような永続ディレクトリを使えば毎回ログインし直す必要なし

#### Linux（ネイティブ）

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug"
```

#### macOS

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.chrome-debug"
```

### 3. SSH トンネル（WSL2 → Windows）

WSL2 から Windows の Chrome に接続するため、ポート転送が必要:

```bash
ssh -L 9222:127.0.0.1:9222 -N {username}@{windows_host_ip}
```

**確認方法**:
```bash
# Windows のホスト IP を取得
ip route show default | awk '{print $3}'

# トンネル確認
curl -s http://localhost:9222/json/version
```

成功時のレスポンス:
```json
{
  "Browser": "Chrome/145.x.x.x",
  "Protocol-Version": "1.3",
  "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/..."
}
```

### 4. Figma Plugin API の初期化

1. Chrome で対象の Figma ファイルを開く
2. Figma のプラグインを一度開閉する（`figma` グローバルを初期化）
   - メニュー → Plugins → 任意のプラグインを開く → 閉じる

### 5. 接続確認

Claude Code セッションを再起動（MCP 設定の反映に必要）後:

```
mcp__chrome-devtools__list_pages
→ Figma タブが一覧に表示されること

mcp__chrome-devtools__evaluate_script
  function: () => typeof figma
→ "object" が返ること
```

## トラブルシューティング

### `figma` が undefined

**原因**: Figma Plugin API が初期化されていない

**解決策**:
1. Figma のプラグインパネルを開く（何でもよい）
2. プラグインを閉じる
3. 再度 `typeof figma` を試行

### Chrome DevTools MCP に接続できない

**チェックリスト**:
1. Chrome が `--remote-debugging-port=9222 --user-data-dir=...` で起動しているか
2. SSH トンネルが起動しているか (`lsof -i :9222`)
3. `curl http://localhost:9222/json/version` でレスポンスがあるか
4. `.mcp.json` に `--browserUrl` が含まれているか
5. Claude Code セッションを再起動したか

### ポート 9222 が既に使用中

```bash
# 何がポートを使っているか確認
lsof -i :9222

# 古いトンネルを停止
kill {PID}
```

### Chrome がリモートデバッグポートをリスンしない

**Chrome 136+ の問題**:
- `--user-data-dir` が未指定、または通常のプロファイルと同じパスを指している
- 通常プロファイルとは異なるディレクトリを `--user-data-dir` に指定すること

### タイムアウトエラー

**原因**: バッチサイズが大きすぎる

**解決策**:
- バッチサイズを 50 → 25 に縮小
- 処理間に適切なウェイトを挿入

## Figma Desktop について

Figma Desktop (Electron) は `--remote-debugging-port` フラグを受け付けるが、CDP を正しく公開しないため**非推奨**。Chrome Web 版を使用すること。

## セキュリティ注意事項

- Chrome DevTools MCP はローカルマシン上でのみ使用
- リモートデバッグポートを外部に公開しない
- `--user-data-dir` で使用するプロファイルは作業専用にすることを推奨
