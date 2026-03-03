#!/bin/bash
set -e

# WordPressのwp-config.phpにVITE_DEV_MODE設定を自動追加 + パーミッション修正するスクリプト

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WP_CONFIG_PATH="wordpress_data/wp-config.php"
WP_CONFIG="$PROJECT_ROOT/$WP_CONFIG_PATH"
THEME_DIR="$PROJECT_ROOT/themes"

echo "📦 プロジェクトルート: $PROJECT_ROOT"
echo ""

# wp-config.phpが存在するか確認
if [ ! -f "$WP_CONFIG" ]; then
  echo "❌ wp-config.php が見つかりません。"
  echo ""
  echo "次の手順を実行してください:"
  echo "1. docker compose up -d"
  echo "2. http://localhost:8000 でWordPressの初期セットアップを完了"
  echo "3. 再度このスクリプトを実行"
  exit 1
fi

# Dockerコンテナ名を取得（wordpressを含む名前）
CONTAINER_NAME=$(docker compose ps --format '{{.Name}}' | grep wordpress | head -1)

if [ -z "$CONTAINER_NAME" ]; then
  echo "❌ WordPressコンテナが起動していません"
  echo "docker compose up -d を実行してください"
  exit 1
fi

echo "🐳 Dockerコンテナ: $CONTAINER_NAME"
echo ""

# すでに設定済みか確認
if grep -q "define('VITE_DEV_MODE'" "$WP_CONFIG"; then
  echo "✅ VITE_DEV_MODE はすでに設定済みです"

  # 間違った設定を修正（コンテナ内で実行）
  if grep -q "getenv_docker('VITE_DEV_MODE'" "$WP_CONFIG"; then
    echo "🔧 誤った設定を修正しています..."
    docker compose exec -T wordpress sed -i "s/getenv_docker('VITE_DEV_MODE', 'false') === 'true'/getenv_docker('VITE_DEV', '0') === '1'/" /var/www/html/wp-config.php
    echo "✅ 修正完了"
  fi
else
  echo "🔧 VITE_DEV_MODE を wp-config.php に追加しています..."

  # "stop editing" の直前に追加（コンテナ内で実行）
  docker compose exec -T wordpress sed -i "/\/\* That's all, stop editing/i \\
define('VITE_DEV_MODE', getenv_docker('VITE_DEV', '0') === '1');\\
" /var/www/html/wp-config.php

  echo "✅ 追加完了"
fi

echo ""
echo "📦 設定内容:"
grep -A 1 "VITE_DEV_MODE" "$WP_CONFIG" || true

echo ""
echo "🔧 パーミッションを修正しています..."
echo ""

# テーマディレクトリのパーミッション修正
if [ -d "$THEME_DIR" ]; then
  # ディレクトリ: 755
  echo "  📁 ディレクトリ権限を 755 に設定..."
  find "$THEME_DIR" -type d -exec chmod 755 {} \; 2>/dev/null || true

  # PHPファイル: 644
  echo "  🐘 PHPファイル権限を 644 に設定..."
  find "$THEME_DIR" -type f -name "*.php" -exec chmod 644 {} \; 2>/dev/null || true

  # SCSS/CSSファイル: 644
  echo "  🎨 CSS/SCSSファイル権限を 644 に設定..."
  find "$THEME_DIR" -type f \( -name "*.css" -o -name "*.scss" \) -exec chmod 644 {} \; 2>/dev/null || true

  # JSファイル: 644
  echo "  ⚡ JavaScriptファイル権限を 644 に設定..."
  find "$THEME_DIR" -type f -name "*.js" -exec chmod 644 {} \; 2>/dev/null || true

  # 画像ファイル: 644
  echo "  🖼️  画像ファイル権限を 644 に設定..."
  find "$THEME_DIR" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" -o -name "*.svg" -o -name "*.webp" \) -exec chmod 644 {} \; 2>/dev/null || true

  echo ""
  echo "✅ パーミッション修正完了"
else
  echo "⚠️  テーマディレクトリが見つかりません: $THEME_DIR"
fi

# wp-config.phpのパーミッション（Dockerコンテナ内で実行）
echo "  ⚙️  wp-config.php のパーミッション設定..."
docker compose exec -T wordpress chmod 644 /var/www/html/wp-config.php 2>/dev/null || true

echo ""
echo "🎉 セットアップ完了！"
echo ""
echo "次のステップ:"
echo "1. docker compose restart (設定を反映)"
echo "2. npm run dev (Viteサーバー起動)"
echo "3. http://localhost:8000 にアクセス"
