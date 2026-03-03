#!/usr/bin/env tsx

/**
 * WordPress固定ページテンプレート自動作成スクリプト
 *
 * YAMLファイルから未作成のテンプレートファイルを検出して作成します。
 *
 * 使用方法:
 *   npm run wp:create-templates
 */

import { readFileSync, writeFileSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { mkdirSync } from "fs";
import yaml from "js-yaml";
import { detectThemeName, getThemePath } from "../lib/detect-theme.js";

// テーマ名を自動検出
const THEME_NAME = detectThemeName();
const THEME_PATH = getThemePath();

console.log(`📦 Theme detected: ${THEME_NAME}`);

// 色付き出力用
const colors = {
  reset: "\x1b[0m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
};

// 設定
const CONFIG = {
  configFile: resolve(import.meta.dirname || dirname(import.meta.url), "../../config/wordpress-pages.yaml"),
  themePath: THEME_PATH,
} as const;

// 型定義
interface PageConfig {
  title: string;
  slug: string;
  template: string;
  description?: string;
  parent?: string;
}

interface WordPressConfig {
  pages: PageConfig[];
}

/**
 * 色付きログ出力
 */
const log = {
  info: (msg: string) => console.log(`${colors.blue}${msg}${colors.reset}`),
  success: (msg: string) => console.log(`${colors.green}${msg}${colors.reset}`),
  warn: (msg: string) => console.log(`${colors.yellow}${msg}${colors.reset}`),
  error: (msg: string) => console.error(`${colors.red}${msg}${colors.reset}`),
};

/**
 * YAMLファイルから設定を読み込み
 */
function loadConfig(): WordPressConfig {
  try {
    const fileContents = readFileSync(CONFIG.configFile, "utf8");
    const data = yaml.load(fileContents) as WordPressConfig;
    log.success(`✓ 設定ファイル: ${CONFIG.configFile}`);
    log.info(`読み込んだページ数: ${data.pages.length}`);
    return data;
  } catch (error) {
    log.error(`エラー: 設定ファイルの読み込みに失敗しました: ${CONFIG.configFile}`);
    if (error instanceof Error) {
      log.error(error.message);
    }
    process.exit(1);
  }
}

/**
 * 基本テンプレートを生成
 */
function generateTemplate(page: PageConfig): string {
  // 親ページがある場合は親スラッグを含める
  const slugParts: string[] = [];
  if (page.parent) {
    slugParts.push(page.parent);
  }
  slugParts.push(page.slug);

  const className = `p-${slugParts.join("-")}`;

  return `<?php
/**
 * Template Name: ${page.title}
 */

get_header();
?>

<main class="${className}">
  <div class="${className}__container">
    <h1>${page.title}</h1>
    <p>このページは自動生成されたテンプレートです。</p>
  </div>
</main>

<?php get_footer(); ?>
`;
}

/**
 * テンプレートファイルを作成
 */
function createTemplateFile(page: PageConfig): void {
  const templatePath = resolve(CONFIG.themePath, page.template);

  // 既に存在する場合はスキップ
  if (existsSync(templatePath)) {
    log.warn(`  → スキップ: ${page.template} は既に存在します`);
    return;
  }

  // ディレクトリが存在しない場合は作成
  const dir = dirname(templatePath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
    log.info(`  → ディレクトリ作成: ${dir}`);
  }

  // テンプレートファイルを作成
  const content = generateTemplate(page);
  writeFileSync(templatePath, content, { encoding: "utf8", mode: 0o644 });
  log.success(`  ✓ テンプレート作成: ${page.template}`);
}

/**
 * メイン処理
 */
async function main() {
  log.success("==================================");
  log.success("WordPress テンプレート自動作成");
  log.success("==================================");
  console.log("");

  // 設定を読み込み
  const config = loadConfig();

  console.log("");
  log.warn("テンプレートファイルを作成中...");
  console.log("");

  let createdCount = 0;
  let skippedCount = 0;

  config.pages.forEach((page, index) => {
    log.info(`[${index + 1}/${config.pages.length}] ${page.title}`);

    const templatePath = resolve(CONFIG.themePath, page.template);
    if (existsSync(templatePath)) {
      log.warn(`  → スキップ: ${page.template} は既に存在します`);
      skippedCount++;
    } else {
      createTemplateFile(page);
      createdCount++;
    }
  });

  // 完了メッセージ
  console.log("");
  log.success("==================================");
  log.success("作成完了！");
  log.success("==================================");
  console.log("");
  log.info(`新規作成: ${createdCount}ファイル`);
  log.info(`スキップ: ${skippedCount}ファイル`);
  console.log("");
}

// スクリプト実行
main().catch((error) => {
  log.error("予期しないエラーが発生しました");
  console.error(error);
  process.exit(1);
});
