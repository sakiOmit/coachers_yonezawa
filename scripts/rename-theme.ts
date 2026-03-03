#!/usr/bin/env tsx
/**
 * テーマリネームスクリプト（完全版）
 *
 * 使用方法:
 *   npm run theme:rename <新しいテーマ名> [オプション]
 *
 * 例:
 *   npm run theme:rename my-new-theme
 *   npm run theme:rename my-new-theme --dry-run
 *   npm run theme:rename my-new-theme --prefix my_
 *
 * オプション:
 *   --dry-run: 実際の変更を行わず、変更内容のみ表示
 *   --prefix <prefix>: 関数プレフィックスを指定（デフォルト: テーマ名の頭文字）
 *   --skip-docs: docs/ の更新をスキップ
 */

import { readFileSync, writeFileSync, readdirSync, statSync, renameSync, existsSync } from 'fs';
import { join, basename, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 色付きログ
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

const log = {
  info: (msg: string) => console.log(`${colors.cyan}ℹ${colors.reset} ${msg}`),
  success: (msg: string) => console.log(`${colors.green}✓${colors.reset} ${msg}`),
  warning: (msg: string) => console.log(`${colors.yellow}⚠${colors.reset} ${msg}`),
  error: (msg: string) => console.error(`${colors.red}✗${colors.reset} ${msg}`),
  step: (msg: string) => console.log(`\n${colors.blue}▸${colors.reset} ${msg}`),
};

const PROJECT_ROOT = join(__dirname, '..');
const THEMES_DIR = join(PROJECT_ROOT, 'themes');

/** WordPress標準テーマを除外してカスタムテーマを検出 */
function detectCurrentTheme(): string | null {
  try {
    const entries = readdirSync(THEMES_DIR);
    for (const entry of entries) {
      const entryPath = join(THEMES_DIR, entry);
      if (
        statSync(entryPath).isDirectory() &&
        !entry.startsWith('twenty') &&
        !entry.startsWith('.')
      ) {
        return entry;
      }
    }
  } catch (error) {
    log.error(`テーマディレクトリの読み込みに失敗: ${error}`);
  }
  return null;
}

/** テーマ名から関数プレフィックスを生成 */
function generatePrefix(themeName: string): string {
  // ハイフンで分割して頭文字を取得（例: business-trip-kakida-wp → btk_）
  // wp で終わる場合は wp を除外
  const parts = themeName.split(/[-_]/).filter(p => p !== 'wp');
  const initials = parts.map(p => p[0]).join('');
  return `${initials}_`;
}

/** ファイル内容を置換 */
function replaceInFile(
  filePath: string,
  replacements: Array<{ from: string | RegExp; to: string }>,
  dryRun: boolean
): number {
  if (!existsSync(filePath)) {
    return 0;
  }

  let content = readFileSync(filePath, 'utf8');
  let changeCount = 0;

  for (const { from, to } of replacements) {
    const matches = content.match(typeof from === 'string' ? new RegExp(from, 'g') : from);
    if (matches) {
      changeCount += matches.length;
      content = content.replace(from, to);
    }
  }

  if (changeCount > 0 && !dryRun) {
    writeFileSync(filePath, content, 'utf8');
  }

  return changeCount;
}

/** 再帰的にファイルを検索して置換 */
function replaceInDirectory(
  dirPath: string,
  pattern: RegExp,
  replacements: Array<{ from: string | RegExp; to: string }>,
  dryRun: boolean
): { fileCount: number; changeCount: number } {
  let fileCount = 0;
  let changeCount = 0;

  function walk(dir: string) {
    const entries = readdirSync(dir);
    for (const entry of entries) {
      const fullPath = join(dir, entry);
      const stat = statSync(fullPath);

      if (stat.isDirectory()) {
        walk(fullPath);
      } else if (stat.isFile() && pattern.test(entry)) {
        const changes = replaceInFile(fullPath, replacements, dryRun);
        if (changes > 0) {
          fileCount++;
          changeCount += changes;
          if (dryRun) {
            log.info(`  ${fullPath}: ${changes}箇所`);
          }
        }
      }
    }
  }

  walk(dirPath);
  return { fileCount, changeCount };
}

interface Options {
  dryRun: boolean;
  prefix?: string;
  skipDocs: boolean;
}

function parseArgs(): { newThemeName: string | null; options: Options } {
  const args = process.argv.slice(2);
  let newThemeName: string | null = null;
  const options: Options = {
    dryRun: false,
    prefix: undefined,
    skipDocs: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--prefix') {
      options.prefix = args[++i];
    } else if (arg === '--skip-docs') {
      options.skipDocs = true;
    } else if (!arg.startsWith('--')) {
      newThemeName = arg;
    }
  }

  return { newThemeName, options };
}

async function main() {
  console.log(`${colors.cyan}======================================${colors.reset}`);
  console.log(`${colors.cyan}  テーマリネームスクリプト（完全版）${colors.reset}`);
  console.log(`${colors.cyan}======================================${colors.reset}\n`);

  const { newThemeName, options } = parseArgs();

  // 引数チェック
  if (!newThemeName) {
    log.error('新しいテーマ名を指定してください');
    console.log('\n使用方法: npm run theme:rename <新しいテーマ名> [オプション]');
    console.log('例: npm run theme:rename my-new-theme');
    console.log('\nオプション:');
    console.log('  --dry-run: 実際の変更を行わず、変更内容のみ表示');
    console.log('  --prefix <prefix>: 関数プレフィックスを指定');
    console.log('  --skip-docs: docs/ の更新をスキップ');
    process.exit(1);
  }

  // テーマ名の検証
  if (!/^[a-zA-Z0-9_-]+$/.test(newThemeName)) {
    log.error('テーマ名には英数字、ハイフン、アンダースコアのみ使用できます');
    process.exit(1);
  }

  // 現在のテーマを検出
  const oldThemeName = detectCurrentTheme();
  if (!oldThemeName) {
    log.error('現在のテーマを検出できませんでした');
    process.exit(1);
  }

  // 同じ名前の場合
  if (oldThemeName === newThemeName) {
    log.warning('テーマ名が同じです。変更は不要です。');
    process.exit(0);
  }

  // 関数プレフィックスの設定
  const oldPrefix = generatePrefix(oldThemeName);
  const newPrefix = options.prefix || generatePrefix(newThemeName);

  // テーマ名をタイトルケースに変換（style.css用）
  const themeTitle = newThemeName
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  console.log(`${colors.yellow}変更内容:${colors.reset}`);
  console.log(`  旧テーマ名: ${oldThemeName}`);
  console.log(`  新テーマ名: ${newThemeName}`);
  console.log(`  テーマタイトル: ${themeTitle}`);
  console.log(`  旧関数プレフィックス: ${oldPrefix}`);
  console.log(`  新関数プレフィックス: ${newPrefix}`);
  if (options.dryRun) {
    console.log(`\n${colors.yellow}※ Dry-runモード: 実際の変更は行いません${colors.reset}`);
  }

  console.log();

  // ====================================
  // 1. テーマディレクトリのリネーム
  // ====================================
  log.step('1. テーマディレクトリをリネーム');
  const oldThemePath = join(THEMES_DIR, oldThemeName);
  const newThemePath = join(THEMES_DIR, newThemeName);

  if (!existsSync(oldThemePath)) {
    log.error(`テーマディレクトリが見つかりません: ${oldThemePath}`);
    process.exit(1);
  }

  if (!options.dryRun) {
    renameSync(oldThemePath, newThemePath);
  }
  log.success(`themes/${oldThemeName} → themes/${newThemeName}`);

  // dry-runの場合は、以降の処理で旧ディレクトリパスを使用
  const themePath = options.dryRun ? oldThemePath : newThemePath;

  // ====================================
  // 2. .env ファイルの更新
  // ====================================
  log.step('2. .env ファイルを更新');
  const envPath = join(PROJECT_ROOT, '.env');
  if (existsSync(envPath)) {
    const changes = replaceInFile(
      envPath,
      [{ from: `THEME_NAME=${oldThemeName}`, to: `THEME_NAME=${newThemeName}` }],
      options.dryRun
    );
    log.success(`THEME_NAME を更新 (${changes}箇所)`);
  } else {
    log.warning('.env ファイルが見つかりません');
  }

  // ====================================
  // 3. style.css の更新
  // ====================================
  log.step('3. style.css を更新');
  const styleCssPath = join(themePath, 'style.css');
  const styleChanges = replaceInFile(
    styleCssPath,
    [
      { from: /Theme Name: .*/, to: `Theme Name: ${themeTitle}` },
      { from: /Text Domain: .*/, to: `Text Domain: ${newThemeName}` },
    ],
    options.dryRun
  );
  log.success(`Theme Name, Text Domain を更新 (${styleChanges}箇所)`);

  // ====================================
  // 4. PHPファイルの Text Domain 更新
  // ====================================
  log.step('4. PHPファイルの Text Domain を更新');
  const phpResult = replaceInDirectory(
    themePath,
    /\.php$/,
    [
      { from: new RegExp(`'${oldThemeName}'`, 'g'), to: `'${newThemeName}'` },
      { from: new RegExp(`"${oldThemeName}"`, 'g'), to: `"${newThemeName}"` },
    ],
    options.dryRun
  );
  log.success(`${phpResult.fileCount}ファイル、${phpResult.changeCount}箇所を更新`);

  // ====================================
  // 5. 関数プレフィックスの更新
  // ====================================
  log.step('5. 関数プレフィックスを更新');
  const prefixResult = replaceInDirectory(
    themePath,
    /\.php$/,
    [
      { from: new RegExp(`function ${oldPrefix}`, 'g'), to: `function ${newPrefix}` },
      { from: new RegExp(`'${oldPrefix}`, 'g'), to: `'${newPrefix}` },
      { from: new RegExp(`\\(\\s*"${oldPrefix}`, 'g'), to: `("${newPrefix}` },
    ],
    options.dryRun
  );
  log.success(`${prefixResult.fileCount}ファイル、${prefixResult.changeCount}箇所を更新`);

  // ====================================
  // 6. phpcs.xml, phpcs.xml.dist の更新
  // ====================================
  log.step('6. phpcs.xml を更新');
  const phpcsFiles = ['phpcs.xml', 'phpcs.xml.dist'];
  let phpcsCount = 0;
  for (const file of phpcsFiles) {
    const filePath = join(PROJECT_ROOT, file);
    if (existsSync(filePath)) {
      const changes = replaceInFile(
        filePath,
        [
          { from: `themes/${oldThemeName}`, to: `themes/${newThemeName}` },
          { from: `./themes/${oldThemeName}`, to: `./themes/${newThemeName}` },
        ],
        options.dryRun
      );
      phpcsCount += changes;
    }
  }
  log.success(`phpcs設定を更新 (${phpcsCount}箇所)`);

  // ====================================
  // 7. docs/ ディレクトリの更新
  // ====================================
  if (!options.skipDocs) {
    log.step('7. docs/ ディレクトリを更新');
    const docsPath = join(PROJECT_ROOT, 'docs');
    if (existsSync(docsPath)) {
      const docsResult = replaceInDirectory(
        docsPath,
        /\.md$/,
        [{ from: new RegExp(`themes/${oldThemeName}`, 'g'), to: `themes/${newThemeName}` }],
        options.dryRun
      );
      log.success(`${docsResult.fileCount}ファイル、${docsResult.changeCount}箇所を更新`);
    } else {
      log.warning('docs/ ディレクトリが見つかりません');
    }
  } else {
    log.info('docs/ の更新をスキップしました');
  }

  // ====================================
  // 完了
  // ====================================
  console.log(`\n${colors.green}======================================${colors.reset}`);
  console.log(`${colors.green}  リネーム完了！${colors.reset}`);
  console.log(`${colors.green}======================================${colors.reset}\n`);

  if (options.dryRun) {
    console.log(`${colors.yellow}※ Dry-runモードのため、実際の変更は行われていません${colors.reset}`);
    console.log(`${colors.yellow}※ 問題がなければ --dry-run を外して再実行してください${colors.reset}\n`);
  } else {
    console.log('次のステップ:');
    console.log('  1. git add .                  # 変更をステージング');
    console.log('  2. git commit -m "テーマ名変更" # コミット');
    console.log('  3. npm run dev                # 開発サーバー起動');
    console.log();
  }
}

main().catch((error) => {
  log.error(`エラーが発生しました: ${error.message}`);
  process.exit(1);
});
