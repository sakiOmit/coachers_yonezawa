/**
 * テーマ名自動検出ユーティリティ
 *
 * themes/ ディレクトリ内のカスタムテーマを自動検出します。
 * WordPress標準テーマ（twenty*）は除外されます。
 */

import { readdirSync, statSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../..');

// WordPress標準テーマのパターン（除外対象）
const WP_DEFAULT_THEMES = /^twenty/;

/**
 * themes/ ディレクトリからカスタムテーマを検出
 * @returns {string} テーマ名
 */
export function detectThemeName() {
  const themesDir = resolve(PROJECT_ROOT, 'themes');

  try {
    const entries = readdirSync(themesDir);

    for (const entry of entries) {
      const entryPath = resolve(themesDir, entry);

      // ディレクトリかつWordPress標準テーマでないものを検出
      if (
        statSync(entryPath).isDirectory() &&
        !WP_DEFAULT_THEMES.test(entry) &&
        !entry.startsWith('.')
      ) {
        return entry;
      }
    }
  } catch (error) {
    console.warn('Warning: Could not detect theme name:', error.message);
  }

  // フォールバック
  return 'starter';
}

/**
 * テーマのフルパスを取得
 * @returns {string} テーマディレクトリの絶対パス
 */
export function getThemePath() {
  return resolve(PROJECT_ROOT, 'themes', detectThemeName());
}

// CLI実行時はテーマ名を出力
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  console.log(detectThemeName());
}
