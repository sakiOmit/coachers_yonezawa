# 初回セットアップガイド

新しいプロジェクトでViteのHMR（Hot Module Replacement）を有効にするための詳細手順です。

## 方法1: 完全自動（推奨）

```bash
npm run docker:init
```

このコマンドは以下を自動実行します：
- Docker起動
- wp-config.php生成待機
- 自動設定適用

**手順:**
1. コマンド実行
2. WordPress初期セットアップを http://localhost:8000 で完了
3. 完了したら自動的に設定が適用される
4. `npm run dev` でViteサーバー起動

## 方法2: 手動（細かく制御したい場合）

```bash
# 1. Dockerを起動
docker compose up -d

# 2. WordPressの初期セットアップを完了（ブラウザで http://localhost:8000）

# 3. 自動設定実行（wp-config.php編集 + パーミッション修正）
npm run setup:vite-dev

# 4. Dockerを再起動（設定反映）
docker compose restart

# 5. Viteサーバー起動
npm run dev
```

## 自動設定の内容

- ✅ wp-config.phpに`VITE_DEV_MODE`定数を追加
- ✅ テーマディレクトリのパーミッション修正（644/755）
- ✅ 既存設定の検証・修正

## 動作確認

`http://localhost:8000` にアクセスすると、SCSS/JSの変更がブラウザに即座に反映されます。

## ファイルパーミッション

Docker環境での重要ルール:

| 対象 | パーミッション |
|------|---------------|
| PHP/CSS/JS ファイル | `644` (rw-r--r--) |
| ディレクトリ | `755` (rwxr-xr-x) |

### Node.jsでファイル作成時

```javascript
writeFileSync(path, content, { encoding: "utf8", mode: 0o644 });
```

### Dockerコンテナ内のファイル操作

```bash
# ❌ ホスト側から直接実行 → Permission denied
rm -rf wordpress_data/wp-content/themes/twentytwentyfour

# ✅ コンテナ内で実行 → 正常動作
docker compose exec -T wordpress sh -c 'rm -rf /var/www/html/wp-content/themes/twentytwentyfour'
```

詳細: `docs/coding-guidelines/09-docker-scripting.md`

## トラブルシューティング

| 問題 | 確認事項 |
|------|----------|
| スタイル反映されない | `npm run dev` 起動中？ enqueue.php 正しい？ |
| ビルドエラー | vite.config.js パス確認、`npm install` 再実行 |
| WordPress表示エラー | `docker compose ps`、パーマリンク再保存 |
