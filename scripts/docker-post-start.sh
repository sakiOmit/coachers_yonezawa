#!/bin/bash
set -e

# Docker起動後に自動実行されるスクリプト
# docker compose up 後にwp-config.phpの生成を待ってから設定を適用

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WP_CONFIG="$PROJECT_ROOT/wordpress_data/wp-config.php"

echo "🚀 Docker起動後の自動セットアップを開始..."
echo ""

# wp-config.phpが作成されるまで待機（最大60秒）
WAIT_COUNT=0
MAX_WAIT=30

echo "⏳ WordPressの初期化を待機中..."
while [ ! -f "$WP_CONFIG" ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
  sleep 2
  WAIT_COUNT=$((WAIT_COUNT + 1))
  if [ $((WAIT_COUNT % 5)) -eq 0 ]; then
    echo "   ${WAIT_COUNT}秒経過... (最大 ${MAX_WAIT}秒待機)"
  fi
done

if [ ! -f "$WP_CONFIG" ]; then
  echo ""
  echo "⏭️  wp-config.php がまだ作成されていません"
  echo ""
  echo "WordPress初期セットアップを完了後、以下を実行してください:"
  echo "  npm run setup:vite-dev"
  exit 0
fi

echo ""
echo "✅ wp-config.php が見つかりました"
echo ""

# WordPress標準テーマ（twenty系）を削除
echo "🗑️  WordPress標準テーマ（twenty系）を削除中..."

# Dockerコンテナ内で削除（パーミッション問題を回避）
if docker compose exec -T wordpress test -d /var/www/html/wp-content/themes 2>/dev/null; then
  # 削除対象のテーマをリストアップ
  THEMES_LIST=$(docker compose exec -T wordpress sh -c 'ls -d /var/www/html/wp-content/themes/twenty* 2>/dev/null || true')

  if [ -n "$THEMES_LIST" ]; then
    # コンテナ内で削除を実行
    docker compose exec -T wordpress sh -c 'rm -rf /var/www/html/wp-content/themes/twenty*'

    # 削除したテーマ数をカウント
    REMOVED_COUNT=$(echo "$THEMES_LIST" | wc -l)
    echo "$THEMES_LIST" | while IFS= read -r theme_path; do
      theme_name=$(basename "$theme_path")
      echo "   ✓ ${theme_name} を削除"
    done
    echo "   合計 ${REMOVED_COUNT} 個のテーマを削除しました"
  else
    echo "   削除対象のテーマはありませんでした"
  fi
else
  echo "   WordPressコンテナが起動していません（スキップ）"
fi
echo ""

# themesディレクトリの所有権を修正（npm run init でリネーム可能にする）
echo "🔧 themesディレクトリの所有権を修正中..."
if docker compose exec -T wordpress test -d /var/www/html/wp-content/themes 2>/dev/null; then
  CURRENT_USER=$(whoami)
  CURRENT_UID=$(id -u)
  CURRENT_GID=$(id -g)
  docker compose exec -T wordpress chown -R "$CURRENT_UID:$CURRENT_GID" /var/www/html/wp-content/themes
  echo "   ✓ 所有権を ${CURRENT_USER} に変更しました"
else
  echo "   WordPressコンテナが起動していません（スキップ）"
fi
echo ""

# setup:vite-devスクリプトを実行
bash "$PROJECT_ROOT/scripts/setup-vite-dev.sh"

echo ""
echo "🎉 自動セットアップ完了！"
