# Docker & スクリプト作成ガイドライン

## 基本原則

このプロジェクトではDocker環境を使用しているため、スクリプト作成時には**ファイル所有権とパーミッション**に注意が必要です。

### 重要ルール

**Dockerコンテナ内で作成されたファイルは、コンテナ内で操作する**

- WordPressがコンテナ内で作成したファイル（テーマ、プラグイン、アップロード等）は `www-data` ユーザーが所有
- ホスト側から直接 `rm`, `mv`, `chmod` 等を実行すると**パーミッションエラー**が発生する
- コンテナ内でコマンドを実行することで問題を回避

## Docker操作のベストプラクティス

### ❌ 悪い例（パーミッションエラー）

```bash
# ホスト側から直接削除 → Permission denied
THEMES_DIR="./wordpress_data/wp-content/themes"
rm -rf "$THEMES_DIR/twentytwentyfour"
```

### ✅ 良い例（コンテナ内で実行）

```bash
# Dockerコンテナ内で削除 → 正常動作
docker compose exec -T wordpress sh -c 'rm -rf /var/www/html/wp-content/themes/twentytwentyfour'
```

## 実装パターン

### パターン1: ファイル削除

```bash
# コンテナが起動しているか確認してから実行
if docker compose exec -T wordpress test -d /var/www/html/wp-content/themes 2>/dev/null; then
  docker compose exec -T wordpress sh -c 'rm -rf /var/www/html/wp-content/themes/twenty*'
else
  echo "⚠️ WordPressコンテナが起動していません"
fi
```

### パターン2: ファイルコピー・移動

```bash
# ホスト → コンテナ
docker compose cp ./local-file.php wordpress:/var/www/html/wp-content/themes/theme-name/

# コンテナ → ホスト
docker compose cp wordpress:/var/www/html/wp-content/uploads ./backups/
```

### パターン3: パーミッション変更

```bash
# コンテナ内でchmod/chown
docker compose exec -T wordpress sh -c 'chmod 644 /var/www/html/wp-content/themes/theme-name/**/*.php'
docker compose exec -T wordpress sh -c 'chown www-data:www-data /var/www/html/wp-content/uploads -R'
```

### パターン4: ファイル存在確認

```bash
# コンテナ内でテスト
if docker compose exec -T wordpress test -f /var/www/html/wp-config.php 2>/dev/null; then
  echo "✅ wp-config.php が存在します"
fi
```

## Node.jsスクリプトでのファイル作成

### ファイルパーミッション設定（必須）

Node.jsでファイルを作成する際は、**必ず `mode: 0o644` を指定**すること：

```javascript
import { writeFileSync } from 'fs';

// ✅ 正しい（パーミッション指定）
writeFileSync(
  'themes/theme-name/page-example.php',
  content,
  { encoding: 'utf8', mode: 0o644 }
);

// ❌ 間違い（デフォルトパーミッションになる可能性）
writeFileSync('themes/theme-name/page-example.php', content);
```

### 推奨パーミッション

| ファイル種別 | パーミッション | 理由 |
|------------|--------------|------|
| PHP/CSS/JS | `644` (rw-r--r--) | www-dataが読み取れる |
| ディレクトリ | `755` (rwxr-xr-x) | www-dataがアクセスできる |
| 実行ファイル | `755` (rwxr-xr-x) | 実行権限が必要 |

### ディレクトリ作成

```javascript
import { mkdirSync } from 'fs';

// ディレクトリは 755 パーミッション
mkdirSync('themes/theme-name/template-parts/new-section', {
  recursive: true,
  mode: 0o755
});
```

## トラブルシューティング

### 既存ファイルのパーミッション確認

```bash
# テーマディレクトリのPHPファイルで644でないものを検索
find themes/theme-name -type f -name "*.php" ! -perm 644 -ls

# ディレクトリで755でないものを検索
find themes/theme-name -type d ! -perm 755 -ls
```

### 一括修正（緊急時のみ）

```bash
# ファイル: 644に変更
find themes/theme-name -type f -exec chmod 644 {} \;

# ディレクトリ: 755に変更
find themes/theme-name -type d -exec chmod 755 {} \;
```

**注意**: 一括修正は最終手段。スクリプト側で正しくパーミッションを設定するのが望ましい。

## チェックリスト

新しいスクリプトを作成する際の確認事項：

- [ ] `wordpress_data/` 配下のファイル操作は `docker compose exec` 経由で実行
- [ ] Node.jsでファイル作成時は `mode: 0o644` を指定
- [ ] ディレクトリ作成時は `mode: 0o755` を指定
- [ ] コンテナ起動状態を確認してからDocker操作を実行
- [ ] エラーハンドリング（コンテナ未起動時の対応）を実装

## 参考

- パーミッション問題修正例: `scripts/docker-post-start.sh`
- Node.jsファイル作成例: `scripts/wordpress/create-templates.ts`
