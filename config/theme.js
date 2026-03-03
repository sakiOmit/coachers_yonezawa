/**
 * Theme Configuration
 *
 * テーマ名の一元管理モジュール
 * 環境変数 THEME_NAME が設定されていれば優先、なければ自動検出
 */

import path from "path";
import { readdirSync, statSync } from "fs";
import { fileURLToPath } from "url";
import { config } from "dotenv";

// .env ファイルを読み込み
config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, "..");

/**
 * themes/ ディレクトリからカスタムテーマを自動検出
 * @returns {string} テーマ名
 */
function detectThemeName() {
  const themesDir = path.resolve(ROOT_DIR, "themes");
  const wpDefaultThemes = /^twenty/; // WordPress標準テーマを除外

  try {
    const entries = readdirSync(themesDir);
    for (const entry of entries) {
      const entryPath = path.resolve(themesDir, entry);
      if (
        statSync(entryPath).isDirectory() &&
        !wpDefaultThemes.test(entry) &&
        !entry.startsWith(".")
      ) {
        return entry;
      }
    }
  } catch (error) {
    console.warn("Warning: Could not detect theme name:", error.message);
  }
  return "starter"; // フォールバック
}

/**
 * テーマ名を取得
 * 優先順位: 環境変数 THEME_NAME > 自動検出
 */
export const THEME_NAME = process.env.THEME_NAME || detectThemeName();

/**
 * テーマディレクトリのパス
 */
export const THEME_DIR = `themes/${THEME_NAME}`;

/**
 * テーマの絶対パス
 */
export const THEME_PATH = path.resolve(ROOT_DIR, THEME_DIR);

/**
 * プロジェクトルートの絶対パス
 */
export const ROOT_PATH = ROOT_DIR;

// デフォルトエクスポート
export default {
  THEME_NAME,
  THEME_DIR,
  THEME_PATH,
  ROOT_PATH,
  detectThemeName,
};
