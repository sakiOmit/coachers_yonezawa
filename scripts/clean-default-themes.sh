#!/bin/bash
#
# WordPress標準テーマ（twenty系）削除スクリプト
# 使用方法: npm run clean:themes
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEMES_DIR="$PROJECT_ROOT/wordpress_data/wp-content/themes"

echo "🗑️  WordPress標準テーマ（twenty系）を削除します..."
echo ""

if [ ! -d "$THEMES_DIR" ]; then
  echo "❌ テーマディレクトリが見つかりません: $THEMES_DIR"
  exit 1
fi

# 削除対象のテーマを確認
FOUND_THEMES=()
for theme_dir in "$THEMES_DIR"/twenty*; do
  if [ -d "$theme_dir" ]; then
    FOUND_THEMES+=("$(basename "$theme_dir")")
  fi
done

if [ ${#FOUND_THEMES[@]} -eq 0 ]; then
  echo "✅ 削除対象のテーマはありませんでした"
  exit 0
fi

# 確認リスト表示
echo "以下のテーマを削除します:"
for theme in "${FOUND_THEMES[@]}"; do
  echo "  - $theme"
done
echo ""

# 確認
read -p "続行しますか？ (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "キャンセルしました"
  exit 0
fi

echo ""

# 削除実行（Dockerコンテナ内で実行してパーミッション問題を回避）
if docker compose exec -T wordpress test -d /var/www/html/wp-content/themes 2>/dev/null; then
  # コンテナ内で削除を実行
  docker compose exec -T wordpress sh -c 'rm -rf /var/www/html/wp-content/themes/twenty*'

  REMOVED_COUNT=${#FOUND_THEMES[@]}
  for theme in "${FOUND_THEMES[@]}"; do
    echo "✓ ${theme} を削除"
  done

  echo ""
  echo "🎉 合計 ${REMOVED_COUNT} 個のテーマを削除しました"
else
  echo ""
  echo "❌ WordPressコンテナが起動していません"
  echo "   docker compose up -d を実行してから再度お試しください"
  exit 1
fi
