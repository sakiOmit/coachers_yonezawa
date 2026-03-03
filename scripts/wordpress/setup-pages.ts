#!/usr/bin/env tsx

/**
 * WordPress固定ページ自動作成スクリプト (TypeScript版)
 *
 * YAMLファイルから設定を読み込み、DockerコンテナのWP-CLIを使用してページを作成します。
 *
 * 使用方法:
 *   npm run wp:setup
 */

import { readFileSync } from "fs";
import { execSync } from "child_process";
import { resolve } from "path";
import yaml from "js-yaml";

// 色付き出力用
const colors = {
  reset: "\x1b[0m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
};

/**
 * 実行中のWordPressコンテナ名を取得
 * プロジェクトディレクトリ名から推測: <dirname>-wordpress-1
 */
function getWordPressContainer(): string {
  try {
    // プロジェクトルートディレクトリ名を取得
    const projectRoot = resolve(import.meta.dirname || __dirname, '../..');
    const projectName = projectRoot.split('/').pop() || 'unknown';
    const expectedContainer = `${projectName}-wordpress-1`;

    // 期待されるコンテナ名が存在するか確認
    const output = execSync(
      `docker ps --filter name=^${expectedContainer}$ --format '{{.Names}}'`,
      { encoding: 'utf8' }
    ).trim();

    if (output) {
      return output;
    }

    // 見つからない場合はフォールバック: name=wordpress でフィルタ
    const fallbackOutput = execSync(
      "docker ps --filter name=wordpress --format '{{.Names}}'",
      { encoding: 'utf8' }
    ).trim();

    if (!fallbackOutput) {
      throw new Error(
        `WordPressコンテナが見つかりません。\n` +
        `期待されるコンテナ名: ${expectedContainer}\n` +
        `docker compose up -d を実行してください。`
      );
    }

    const containers = fallbackOutput.split('\n').filter(name => name.includes('wordpress'));
    if (containers.length === 0) {
      throw new Error('WordPressコンテナが見つかりません');
    }

    // フォールバックで見つかった場合は警告
    console.warn(`⚠️  期待されるコンテナ名 "${expectedContainer}" が見つからず、"${containers[0]}" を使用します`);
    return containers[0];
  } catch (error) {
    if (error instanceof Error && error.message.includes('WordPressコンテナ')) {
      throw error;
    }
    throw new Error(`WordPressコンテナの検出に失敗: ${error}`);
  }
}

// 設定
const CONFIG = {
  get dockerContainer() {
    return getWordPressContainer();
  },
  configFile: resolve(import.meta.dirname || __dirname, "../../config/wordpress-pages.yaml"),
  wpUrl: "http://localhost:8000",
} as const;

// 型定義
interface PageConfig {
  title: string;
  slug: string;
  template: string;
  description?: string;
  parent?: string; // 親ページのslug
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
 * WP-CLIコマンドを実行（Dockerコンテナ内）
 */
function wpCommand(command: string): string {
  try {
    const result = execSync(`docker exec -i ${CONFIG.dockerContainer} wp ${command} --allow-root`, {
      encoding: "utf-8",
    });
    return result.trim();
  } catch (error) {
    if (error instanceof Error && "stderr" in error) {
      throw new Error((error as any).stderr || error.message);
    }
    throw error;
  }
}

/**
 * Dockerコンテナの起動確認
 */
function checkDocker(): void {
  try {
    execSync(`docker ps --format '{{.Names}}' | grep -q "^${CONFIG.dockerContainer}$"`, {
      encoding: "utf-8",
    });
    log.success(`✓ Dockerコンテナ: ${CONFIG.dockerContainer}`);
  } catch {
    log.error(`エラー: コンテナ「${CONFIG.dockerContainer}」が起動していません`);
    log.warn("以下のコマンドで起動してください:");
    log.warn("  docker compose up -d");
    process.exit(1);
  }
}

/**
 * WP-CLIのインストール確認
 */
function checkWpCli(): void {
  try {
    execSync(`docker exec ${CONFIG.dockerContainer} which wp`, { encoding: "utf-8" });
    log.success("✓ WP-CLI (Docker内)");
  } catch {
    log.error("エラー: コンテナ内にWP-CLIがインストールされていません");
    process.exit(1);
  }
}

/**
 * WordPress環境の確認
 */
function checkWordPress(): void {
  try {
    wpCommand("core is-installed");
    const version = wpCommand("core version");
    log.success(`✓ WordPress環境: ${version}`);
  } catch {
    log.error("エラー: WordPressがインストールされていません");
    process.exit(1);
  }
}

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
 * 親ページIDを取得（存在する場合）
 * @param parentSlug 親ページのスラッグ
 * @returns 親ページID（存在しない場合はnull）
 */
function getParentPageId(parentSlug: string): string | null {
  try {
    const parentId = wpCommand(
      `post list --post_type=page --name="${parentSlug}" --post_parent=0 --field=ID --format=csv`
    );
    return parentId || null;
  } catch (error) {
    return null;
  }
}

/**
 * 親ページを考慮した既存ページ検索
 * @param slug ページスラッグ
 * @param parentSlug 親ページスラッグ（オプション）
 * @returns 既存ページID（存在しない場合はnull）
 */
function findExistingPage(slug: string, parentSlug?: string): string | null {
  try {
    let searchCommand = `post list --post_type=page --name="${slug}"`;

    if (parentSlug) {
      const parentId = getParentPageId(parentSlug);
      if (!parentId) {
        // 親ページが存在しない場合、既存ページなしとみなす
        return null;
      }
      searchCommand += ` --post_parent=${parentId}`;
    } else {
      // 親ページ指定なし = トップレベルページのみ検索
      searchCommand += ` --post_parent=0`;
    }

    const existingCount = wpCommand(`${searchCommand} --format=count`);

    if (existingCount === "1") {
      const existingId = wpCommand(`${searchCommand} --field=ID --format=csv`);
      return existingId || null;
    }

    return null;
  } catch (error) {
    return null;
  }
}

/**
 * 設定内容のプレビュー表示
 */
function showPreview(config: WordPressConfig): void {
  console.log("");
  log.info("==================================");
  log.info("設定ファイルの内容");
  log.info("==================================");
  console.log("");

  config.pages.forEach((page, index) => {
    log.warn(`[${index + 1}] ${page.title}`);
    console.log(`    スラッグ: ${page.slug}`);
    console.log(`    テンプレート: ${page.template}`);
    console.log("");
  });
}

/**
 * 既存ページのチェックとプレビュー表示
 */
function showExistingPagesPreview(config: WordPressConfig): void {
  console.log("");
  log.info("==================================");
  log.info("既存ページのチェック");
  log.info("==================================");
  console.log("");

  const existingPages: Array<{ page: PageConfig; id: string }> = [];
  const newPages: string[] = [];

  config.pages.forEach((page) => {
    try {
      const existingId = findExistingPage(page.slug, page.parent);

      if (existingId) {
        existingPages.push({ page, id: existingId });
      } else {
        newPages.push(page.title);
      }
    } catch (error) {
      // エラーは無視してスキップ
      newPages.push(page.title);
    }
  });

  if (existingPages.length > 0) {
    log.info("【既存ページ（スキップ）】");
    existingPages.forEach(({ page, id }) => {
      log.success(`  ✓ ${page.title} (ID: ${id}, slug: ${page.slug})`);
    });
    console.log("");
  }

  if (newPages.length > 0) {
    log.info("【新規作成されるページ】");
    newPages.forEach((title) => {
      log.warn(`  + ${title}`);
    });
    console.log("");
  } else {
    log.info("新規作成されるページはありません");
  }

  console.log("");
}

/**
 * 固定ページを作成（既存ページはスキップ）
 */
function createPage(page: PageConfig, index: number, total: number): void {
  console.log("");
  log.warn(`[${index + 1}/${total}] ページ作成中: ${page.title}`);

  try {
    // 親ページを考慮した既存ページ検索
    const existingId = findExistingPage(page.slug, page.parent);

    let pageId: string;

    if (existingId) {
      // 既存ページがある場合は全てスキップ
      log.warn(`  → スキップ: ページは既に存在します (ID: ${existingId})`);
      log.success(`  ✓ URL: ${CONFIG.wpUrl}/${page.slug}/`);
      return;
    }

    // 親ページのIDを取得（指定されている場合）
    let parentId = "";
    if (page.parent) {
      const parentPageId = getParentPageId(page.parent);
      if (parentPageId) {
        parentId = parentPageId;
        log.info(`  → 親ページ「${page.parent}」を検出 (ID: ${parentId})`);
      } else {
        log.warn(`  ⚠ 警告: 親ページ「${page.parent}」が見つかりません`);
      }
    }

    // ページを作成
    const createCommand = parentId
      ? `post create --post_type=page --post_title="${page.title}" --post_name="${page.slug}" --post_parent=${parentId} --post_status=publish --porcelain`
      : `post create --post_type=page --post_title="${page.title}" --post_name="${page.slug}" --post_status=publish --porcelain`;

    pageId = wpCommand(createCommand);
    log.success(`  ✓ ページ作成完了 (ID: ${pageId})`);

    // テンプレートを設定
    wpCommand(`post meta update ${pageId} "_wp_page_template" "${page.template}"`);
    log.success(`  ✓ テンプレート設定: ${page.template}`);

    // メタディスクリプション設定（Yoast SEOがある場合）
    if (page.description) {
      try {
        wpCommand(`post meta update ${pageId} "_yoast_wpseo_metadesc" "${page.description}"`);
      } catch {
        // Yoast SEOがない場合はスキップ
      }
    }

    log.success(`  ✓ URL: ${CONFIG.wpUrl}/${page.slug}/`);
  } catch (error) {
    log.error(`  ✗ ページ作成失敗`);
    if (error instanceof Error) {
      log.error(`  詳細: ${error.message}`);
    }
  }
}

/**
 * ユーザー確認プロンプト
 */
function confirm(question: string): Promise<boolean> {
  return new Promise((resolve) => {
    process.stdout.write(question);
    process.stdin.once("data", (data) => {
      const answer = data.toString().trim();
      resolve(answer.toLowerCase() === "y" || answer.toLowerCase() === "yes");
    });
  });
}

/**
 * メイン処理
 */
async function main() {
  log.success("==================================");
  log.success("WordPress固定ページ自動作成 (TypeScript)");
  log.success("==================================");
  console.log("");

  // 環境チェック
  log.warn("環境チェック中...");
  checkDocker();
  checkWpCli();
  checkWordPress();

  console.log("");
  log.warn("設定ファイルを読み込み中...");
  const config = loadConfig();

  // プレビュー表示
  showPreview(config);

  // 既存ページのチェックとプレビュー表示
  showExistingPagesPreview(config);

  // 確認プロンプト
  const answer = await confirm("この内容で実行しますか？ (y/N): ");
  if (!answer) {
    log.warn("キャンセルしました");
    process.exit(0);
  }

  // ページ作成
  console.log("");
  log.success("==================================");
  log.success("固定ページの作成");
  log.success("==================================");

  config.pages.forEach((page, index) => {
    createPage(page, index, config.pages.length);
  });

  // 完了メッセージ
  console.log("");
  log.success("==================================");
  log.success("作成完了！");
  log.success("==================================");
  console.log("");
  log.info(`設定ファイルの編集: ${CONFIG.configFile}`);
  console.log("");
  // 終了
  process.exit(0);
}

// スクリプト実行
main().catch((error) => {
  log.error("予期しないエラーが発生しました");
  console.error(error);
  process.exit(1);
});
