/**
 * Clean Build Assets
 *
 * ビルド出力ディレクトリをクリーンアップ
 */

import { rmSync, existsSync } from "fs";
import path from "path";
import { THEME_PATH, THEME_NAME } from "../../config/theme.js";

const assetsDir = path.join(THEME_PATH, "assets");

const dirsToClean = ["js", "css", ".vite", "critical"];

console.log(`🧹 Cleaning build assets for theme: ${THEME_NAME}`);

dirsToClean.forEach((dir) => {
  const dirPath = path.join(assetsDir, dir);
  if (existsSync(dirPath)) {
    try {
      rmSync(dirPath, { recursive: true, force: true });
      console.log(`  ✓ Removed: ${THEME_NAME}/assets/${dir}`);
    } catch (error) {
      console.error(`  ✗ Failed to remove ${dir}:`, error.message);
    }
  }
});

console.log("✨ Clean complete");
