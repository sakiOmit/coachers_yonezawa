/**
 * HTML Validation Wrapper
 *
 * html-validate を動的テーマパスで実行
 */

import { spawn } from "child_process";
import { THEME_DIR, THEME_NAME } from "../../config/theme.js";

const files = [
  "pages",
  "template-parts",
  "front-page",
  "header",
  "footer",
  "404",
  "index",
  "archive",
  "single",
  "page",
];

// ブレース展開でパターンを生成
const globPattern = `${THEME_DIR}/{${files.join(",")}}.php`;

console.log(`🔍 Validating HTML in theme: ${THEME_NAME}`);
console.log(`   Pattern: ${globPattern}`);

const child = spawn("npx", ["html-validate", globPattern], {
  stdio: "inherit",
  shell: true,
});

child.on("close", (code) => {
  process.exit(code);
});
