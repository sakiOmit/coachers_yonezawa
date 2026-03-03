#!/bin/bash
#
# テーマリネームスクリプト
# 使用方法: npm run theme:rename <新しいテーマ名>
# 例: npm run theme:rename my-project
#

set -e

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
THEMES_DIR="${PROJECT_ROOT}/themes"

# 現在のテーマを自動検出（WordPress標準テーマを除外）
detect_current_theme() {
    for dir in "${THEMES_DIR}"/*/; do
        dirname=$(basename "$dir")
        # twentyで始まるディレクトリとドットで始まるディレクトリを除外
        if [[ ! "$dirname" =~ ^twenty ]] && [[ ! "$dirname" =~ ^\. ]]; then
            echo "$dirname"
            return 0
        fi
    done
    echo "starter"
}

OLD_THEME_NAME=$(detect_current_theme)

# 引数チェック
if [ -z "$1" ]; then
    echo -e "${RED}エラー: 新しいテーマ名を指定してください${NC}"
    echo "使用方法: npm run theme:rename <新しいテーマ名>"
    echo "例: npm run theme:rename my-project"
    echo ""
    echo "現在のテーマ: ${OLD_THEME_NAME}"
    exit 1
fi

NEW_THEME_NAME="$1"

# 同じ名前の場合はスキップ
if [ "$OLD_THEME_NAME" = "$NEW_THEME_NAME" ]; then
    echo -e "${YELLOW}テーマ名が同じです。変更は不要です。${NC}"
    exit 0
fi

# テーマ名の検証（英数字とハイフン、アンダースコアのみ）
if ! [[ "$NEW_THEME_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo -e "${RED}エラー: テーマ名には英数字、ハイフン、アンダースコアのみ使用できます${NC}"
    exit 1
fi

echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}テーマリネームスクリプト${NC}"
echo -e "${YELLOW}================================${NC}"
echo ""
echo "旧テーマ名: ${OLD_THEME_NAME}"
echo "新テーマ名: ${NEW_THEME_NAME}"
echo ""

# 確認
read -p "続行しますか？ (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "キャンセルしました"
    exit 0
fi

echo ""
echo -e "${GREEN}1. テーマディレクトリをリネーム...${NC}"
if [ -d "${THEMES_DIR}/${OLD_THEME_NAME}" ]; then
    mv "${THEMES_DIR}/${OLD_THEME_NAME}" "${THEMES_DIR}/${NEW_THEME_NAME}"
    echo "   themes/${OLD_THEME_NAME} → themes/${NEW_THEME_NAME}"
else
    echo -e "${RED}エラー: themes/${OLD_THEME_NAME} が見つかりません${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}2. テーマの style.css を更新...${NC}"
STYLE_CSS="${THEMES_DIR}/${NEW_THEME_NAME}/style.css"
if [ -f "${STYLE_CSS}" ]; then
    # Theme Name を更新
    sed -i "s/Theme Name: .*/Theme Name: ${NEW_THEME_NAME}/" "${STYLE_CSS}"
    # Text Domain も更新
    sed -i "s/Text Domain: .*/Text Domain: ${NEW_THEME_NAME}/" "${STYLE_CSS}"
    echo "   Theme Name を ${NEW_THEME_NAME} に変更"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}完了！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "テーマ名は自動検出されるため、追加の設定変更は不要です。"
echo ""
echo "次のステップ:"
echo "  1. docker compose up -d  # Dockerを再起動"
echo "  2. npm run dev           # 開発サーバー起動"
echo ""
