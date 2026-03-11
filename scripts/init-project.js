#!/usr/bin/env node

/**
 * プロジェクト初期化スクリプト
 *
 * gitテンプレートから新規プロジェクトを作成した後、
 * このスクリプトを実行してプロジェクト固有の情報に置き換えます。
 *
 * 使い方:
 *   npm run init
 *   または
 *   node scripts/init-project.js
 *
 * オプション:
 *   --dry-run  実際の変更を行わず、対象ファイルを表示
 */

import { readFileSync, writeFileSync, renameSync, existsSync, readdirSync, lstatSync } from 'fs';
import { join, dirname } from 'path';
import readline from 'readline';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

const LOCK_FILE = join(projectRoot, '.init-done');
const isDryRun = process.argv.includes('--dry-run');
const batchArg = process.argv.find((a) => a.startsWith('--batch='));
const batchInputs = batchArg ? JSON.parse(readFileSync(batchArg.slice('--batch='.length), 'utf8')) : null;

// ============================================================
// プレースホルダー定義（Single Source of Truth）
// ============================================================
// template: テンプレート内のリテラル文字列（リネーム用）
// prompt: 対話プロンプト
// default: デフォルト値（関数の場合、先行入力値から動的生成）
// validate: 入力バリデーション（省略時はチェックなし）
// ============================================================
const SCHEMA = [
  {
    key: 'PROJECT_NAME',
    template: 'project-name',
    prompt: 'プロジェクト名（英数字とハイフン、アンダースコア）',
    default: () => projectRoot.split('/').pop(),
    validate: (v) => /^[a-zA-Z0-9_-]+$/.test(v) || '英数字・ハイフン・アンダースコアのみ使用可能',
  },
  {
    key: 'THEME_DIR',
    template: 'wordpress-template-wp',
    prompt: 'テーマディレクトリ名（英数字とハイフン）',
    default: (inputs) => inputs.PROJECT_NAME + '-wp',
    validate: (v) => /^[a-zA-Z0-9-]+$/.test(v) || '英数字とハイフンのみ使用可能',
  },
  {
    key: 'THEME_NAME',
    template: 'theme-name',
    prompt: 'テーマ名（表示用）',
    default: (inputs) => inputs.THEME_DIR,
  },
  {
    key: 'THEME_PREFIX',
    template: 'theme_prefix',
    prompt: 'テーマプレフィックス（PHP関数名用、アンダースコア区切り）',
    default: (inputs) => inputs.THEME_DIR.replace(/-/g, '_'),
    validate: (v) => /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(v) || 'PHP識別子として有効な文字のみ使用可能',
  },
  {
    key: 'COMPANY_NAME',
    template: 'Company Name',
    prompt: '会社名（日本語）',
    default: () => '株式会社サンプル',
  },
  {
    key: 'COMPANY_NAME_EN',
    template: 'Company Name English',
    prompt: '会社名（英語）',
    default: () => 'Sample Company Inc.',
  },
  {
    key: 'TEXT_DOMAIN',
    template: 'text-domain',
    prompt: 'テキストドメイン（WordPress翻訳用）',
    default: (inputs) => inputs.THEME_DIR,
    validate: (v) => /^[a-zA-Z0-9-]+$/.test(v) || '英数字とハイフンのみ使用可能',
  },
  {
    key: 'PACKAGE_NAME',
    template: 'Package_Name',
    prompt: 'パッケージ名（PHPパッケージ名）',
    default: (inputs) =>
      inputs.THEME_DIR
        .split('-')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join('_') + '_Theme',
    validate: (v) => /^[A-Z][a-zA-Z0-9_]*$/.test(v) || 'PascalCase_Snake形式で入力してください',
  },
  {
    key: 'DESCRIPTION',
    template: 'Project Description',
    prompt: 'プロジェクト説明',
    default: (inputs) => inputs.COMPANY_NAME + 'のWebサイト',
  },
];

// テキストファイル判定用の拡張子
const TEXT_EXTENSIONS = new Set([
  '.php', '.js', '.mjs', '.cjs', '.ts', '.tsx',
  '.md', '.scss', '.css', '.yaml', '.yml',
  '.json', '.txt', '.sh', '.astro', '.html',
  '.xml', '.toml', '.env', '.gitkeep',
]);

// 除外ディレクトリ
const EXCLUDED_DIRS = new Set([
  'node_modules', '.git', 'vendor', 'wordpress_data', 'dist',
]);

// 置換から除外するファイル
const EXCLUDED_FILES = new Set([
  'init-project.js',
  'create-template.js',
  'package-lock.json',
]);

// ============================================================
// 対話入力
// ============================================================
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const question = (query) => new Promise((resolve) => rl.question(query, resolve));

async function getUserInputs() {
  console.log('\n===========================================');
  console.log('  プロジェクト初期化セットアップ');
  console.log('===========================================\n');

  if (isDryRun) {
    console.log('[dry-run] 実際の変更は行いません\n');
  }

  const inputs = {};

  if (batchInputs) {
    // --batch=file.json: 対話なしで値を適用（CI / dry-run 用）
    for (const field of SCHEMA) {
      const defaultValue = typeof field.default === 'function'
        ? field.default(inputs)
        : field.default;
      inputs[field.key] = batchInputs[field.key] || defaultValue;
    }
  } else {
    for (const field of SCHEMA) {
      const defaultValue = typeof field.default === 'function'
        ? field.default(inputs)
        : field.default;

      let value;
      while (true) {
        value = await question(`${field.prompt} [${defaultValue}]: `) || defaultValue;

        if (field.validate) {
          const result = field.validate(value);
          if (result !== true) {
            console.log(`  -> ${result}`);
            continue;
          }
        }
        break;
      }

      inputs[field.key] = value;
    }
    rl.close();
  }

  // 確認
  console.log('\n===========================================');
  console.log('  入力内容の確認');
  console.log('===========================================');
  for (const field of SCHEMA) {
    console.log(`  ${field.key}: ${inputs[field.key]}`);
  }
  console.log('===========================================\n');

  return inputs;
}

async function confirmProceed() {
  const confirmRl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  const answer = await new Promise((resolve) =>
    confirmRl.question('この内容で初期化を実行しますか？ (y/N): ', resolve)
  );
  confirmRl.close();
  return answer.toLowerCase() === 'y';
}

// ============================================================
// ファイル置換
function replaceInFile(filePath, replacements, dryRun) {
  try {
    let content = readFileSync(filePath, 'utf8');
    let original = content;

    for (const [placeholder, value] of Object.entries(replacements)) {
      content = content.replace(
        new RegExp(`\\{\\{${placeholder}\\}\\}`, 'g'),
        value,
      );
    }

    if (content !== original) {
      if (!dryRun) {
        writeFileSync(filePath, content, { encoding: 'utf8', mode: 0o644 });
      }
      return true;
    }
    return false;
  } catch (error) {
    console.error(`Error processing ${filePath}:`, error.message);
    return false;
  }
}

function processDirectory(dirPath, replacements, dryRun, stats = { files: 0, modified: 0 }) {
  const items = readdirSync(dirPath);

  for (const item of items) {
    const itemPath = join(dirPath, item);
    const stat = lstatSync(itemPath);

    // シンボリックリンクはスキップ（循環リンク対策）
    if (stat.isSymbolicLink()) {
      continue;
    }

    if (stat.isDirectory()) {
      if (EXCLUDED_DIRS.has(item)) {
        continue;
      }
      processDirectory(itemPath, replacements, dryRun, stats);
    } else {
      const dotIndex = item.lastIndexOf('.');
      const ext = dotIndex !== -1 ? item.substring(dotIndex) : '';

      if (TEXT_EXTENSIONS.has(ext) && !EXCLUDED_FILES.has(item)) {
        stats.files++;
        if (replaceInFile(itemPath, replacements, dryRun)) {
          stats.modified++;
          const prefix = dryRun ? '[dry-run] ' : '';
          console.log(`${prefix}  ${itemPath.replace(projectRoot + '/', '')}`);
        }
      }
    }
  }

  return stats;
}

// ============================================================
// テーマディレクトリリネーム
// ============================================================
function renameThemeDirectory(templateName, newName, dryRun) {
  const themesDir = join(projectRoot, 'themes');

  // {{THEME_DIR}} リテラル名のディレクトリも検出（テンプレート未初期化時）
  const candidates = [templateName, '{{THEME_DIR}}'];
  for (const candidate of candidates) {
    const candidatePath = join(themesDir, candidate);
    if (existsSync(candidatePath) && candidate !== newName) {
      const prefix = dryRun ? '[dry-run] ' : '';
      console.log(`\n${prefix}テーマディレクトリをリネーム: ${candidate} -> ${newName}`);
      if (!dryRun) {
        renameSync(candidatePath, join(themesDir, newName));
      }
      return true;
    }
  }
  return false;
}

// ============================================================
// .mcp.json 更新
// ============================================================
function updateMcpJson(projectName, dryRun) {
  const mcpPath = join(projectRoot, '.mcp.json');
  if (!existsSync(mcpPath)) {
    return;
  }

  const content = readFileSync(mcpPath, 'utf8');
  const mcpConfig = JSON.parse(content);

  if (mcpConfig.mcpServers?.serena?.args) {
    const args = mcpConfig.mcpServers.serena.args;
    const projectIndex = args.indexOf('--project');
    if (projectIndex !== -1 && projectIndex + 1 < args.length) {
      const currentPath = args[projectIndex + 1];
      const newPath = currentPath.replace(/\/[^/]+$/, `/${projectName}`);
      args[projectIndex + 1] = newPath;

      const prefix = dryRun ? '[dry-run] ' : '';
      console.log(`${prefix}  .mcp.json のプロジェクトパスを更新: ${newPath}`);
      if (!dryRun) {
        writeFileSync(mcpPath, JSON.stringify(mcpConfig, null, 2), 'utf8');
      }
    }
  }
}

// ============================================================
// .env の THEME_NAME 更新
// ============================================================
function updateEnvThemeName(themeDir, dryRun) {
  const envPath = join(projectRoot, '.env');
  if (!existsSync(envPath)) {
    return;
  }

  let content = readFileSync(envPath, 'utf8');
  const updated = content.replace(
    /^#?\s*THEME_NAME=.*$/m,
    `THEME_NAME=${themeDir}`,
  );

  if (updated !== content) {
    const prefix = dryRun ? '[dry-run] ' : '';
    console.log(`${prefix}  .env の THEME_NAME を更新: ${themeDir}`);
    if (!dryRun) {
      writeFileSync(envPath, updated, 'utf8');
    }
  }
}

// ============================================================
// メイン処理
// ============================================================
async function main() {
  try {
    // 二重実行防止
    if (existsSync(LOCK_FILE) && !isDryRun) {
      console.error('\nこのプロジェクトは既に初期化済みです。');
      console.error(`再実行するには ${LOCK_FILE} を削除してください。\n`);
      process.exit(1);
    }

    const inputs = await getUserInputs();

    if (!isDryRun) {
      const confirmed = await confirmProceed();
      if (!confirmed) {
        console.log('\nキャンセルしました。\n');
        process.exit(0);
      }
    }

    console.log('\nファイルを置き換え中...\n');

    // SCHEMAからテンプレートリテラル名を取得してリネーム用に保持
    const themeTemplateDir = SCHEMA.find((f) => f.key === 'THEME_DIR').template;

    // ファイル内容を置き換え
    const stats = processDirectory(projectRoot, inputs, isDryRun);

    // テーマディレクトリをリネーム
    renameThemeDirectory(themeTemplateDir, inputs.THEME_DIR, isDryRun);

    // .mcp.json を更新
    updateMcpJson(inputs.PROJECT_NAME, isDryRun);

    // .env の THEME_NAME を更新
    updateEnvThemeName(inputs.THEME_DIR, isDryRun);

    // ロックファイル作成
    if (!isDryRun) {
      writeFileSync(LOCK_FILE, JSON.stringify({
        initializedAt: new Date().toISOString(),
        inputs,
      }, null, 2), 'utf8');
    }

    // 完了メッセージ
    const prefix = isDryRun ? '[dry-run] ' : '';
    console.log('\n===========================================');
    console.log(`${prefix}プロジェクト初期化完了`);
    console.log('===========================================');
    console.log(`処理ファイル数: ${stats.files}`);
    console.log(`変更ファイル数: ${stats.modified}`);
    console.log('===========================================\n');

    if (!isDryRun) {
      console.log('次のステップ:');
      console.log('  1. npm install');
      console.log('  2. npm run docker:init');
      console.log('  3. npm run dev\n');
    }
  } catch (error) {
    console.error('\nエラーが発生しました:', error.message);
    process.exit(1);
  }
}

main();
