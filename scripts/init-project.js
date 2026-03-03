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
 */

import { readFileSync, writeFileSync, renameSync, existsSync, readdirSync, statSync } from 'fs';
import { join, dirname } from 'path';
import { execSync } from 'child_process';
import readline from 'readline';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// プレースホルダー定義
const PLACEHOLDERS = {
  PROJECT_NAME: 'project-name',
  THEME_NAME: 'theme-name',
  THEME_DIR: 'wordpress-template-wp',
  THEME_PREFIX: 'theme_prefix',
  COMPANY_NAME: 'Company Name',
  COMPANY_NAME_EN: 'Company Name English',
  TEXT_DOMAIN: 'text-domain',
  PACKAGE_NAME: 'Package_Name',
  DESCRIPTION: 'Project Description'
};

// 対話形式で入力を取得
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const question = (query) => new Promise((resolve) => rl.question(query, resolve));

async function getUserInputs() {
  console.log('\n===========================================');
  console.log('🚀 プロジェクト初期化セットアップ');
  console.log('===========================================\n');

  const inputs = {};

  // プロジェクト名（ディレクトリ名から推測）
  const currentDirName = projectRoot.split('/').pop();
  inputs.PROJECT_NAME = await question(
    `プロジェクト名（英数字とハイフン、アンダースコア）[${currentDirName}]: `
  ) || currentDirName;

  // テーマディレクトリ名
  const suggestedThemeDir = inputs.PROJECT_NAME + '-wp';
  inputs.THEME_DIR = await question(
    `テーマディレクトリ名（英数字とハイフン）[${suggestedThemeDir}]: `
  ) || suggestedThemeDir;

  // テーマ名（表示用）
  inputs.THEME_NAME = await question(
    `テーマ名（表示用）[${inputs.THEME_DIR}]: `
  ) || inputs.THEME_DIR;

  // テーマプレフィックス（PHP関数名用）
  const suggestedPrefix = inputs.THEME_DIR.replace(/-/g, '_');
  inputs.THEME_PREFIX = await question(
    `テーマプレフィックス（PHP関数名用、アンダースコア区切り）[${suggestedPrefix}]: `
  ) || suggestedPrefix;

  // 会社名（日本語）
  inputs.COMPANY_NAME = await question(
    '会社名（日本語）[株式会社サンプル]: '
  ) || '株式会社サンプル';

  // 会社名（英語）
  inputs.COMPANY_NAME_EN = await question(
    '会社名（英語）[Sample Company Inc.]: '
  ) || 'Sample Company Inc.';

  // テキストドメイン
  inputs.TEXT_DOMAIN = await question(
    `テキストドメイン（WordPress翻訳用）[${inputs.THEME_DIR}]: `
  ) || inputs.THEME_DIR;

  // パッケージ名（PHPパッケージ名、アンダースコア区切り）
  const suggestedPackage = inputs.THEME_DIR
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join('_') + '_Theme';
  inputs.PACKAGE_NAME = await question(
    `パッケージ名（PHPパッケージ名）[${suggestedPackage}]: `
  ) || suggestedPackage;

  // 説明
  inputs.DESCRIPTION = await question(
    `プロジェクト説明: `
  ) || inputs.COMPANY_NAME + 'のWebサイト';

  rl.close();

  // 確認
  console.log('\n===========================================');
  console.log('📋 入力内容の確認');
  console.log('===========================================');
  Object.entries(inputs).forEach(([key, value]) => {
    console.log(`${key}: ${value}`);
  });
  console.log('===========================================\n');

  return inputs;
}

// ファイル内容を置き換え
function replaceInFile(filePath, replacements) {
  try {
    let content = readFileSync(filePath, 'utf8');
    let modified = false;

    Object.entries(replacements).forEach(([placeholder, value]) => {
      // {{PLACEHOLDER}} 形式の置換（既存）
      const doubleRegex = new RegExp(`{{${placeholder}}}`, 'g');
      if (content.includes(`{{${placeholder}}}`)) {
        content = content.replace(doubleRegex, value);
        modified = true;
      }

      // {PLACEHOLDER} 形式の置換（新規追加）
      const singleRegex = new RegExp(`{${placeholder}}`, 'g');
      if (content.includes(`{${placeholder}}`)) {
        content = content.replace(singleRegex, value);
        modified = true;
      }
    });

    if (modified) {
      writeFileSync(filePath, content, { encoding: 'utf8', mode: 0o644 });
      return true;
    }
    return false;
  } catch (error) {
    console.error(`Error processing ${filePath}:`, error.message);
    return false;
  }
}

// ディレクトリを再帰的に処理
function processDirectory(dirPath, replacements, stats = { files: 0, modified: 0 }) {
  const items = readdirSync(dirPath);

  items.forEach(item => {
    const itemPath = join(dirPath, item);
    const stat = statSync(itemPath);

    // 除外ディレクトリ
    if (stat.isDirectory()) {
      if (['node_modules', '.git', 'vendor', 'wordpress_data', 'dist'].includes(item)) {
        return;
      }
      processDirectory(itemPath, replacements, stats);
    } else {
      // テキストファイルのみ処理
      const textExtensions = ['.php', '.js', '.ts', '.md', '.scss', '.css', '.yaml', '.yml', '.json', '.txt', '.sh', '.gitkeep'];
      const ext = item.substring(item.lastIndexOf('.'));

      if (textExtensions.includes(ext)) {
        stats.files++;
        if (replaceInFile(itemPath, replacements)) {
          stats.modified++;
          console.log(`✓ ${itemPath.replace(projectRoot + '/', '')}`);
        }
      }
    }
  });

  return stats;
}

// テーマディレクトリをリネーム
function renameThemeDirectory(oldName, newName) {
  const themesDir = join(projectRoot, 'themes');
  const oldPath = join(themesDir, oldName);
  const newPath = join(themesDir, newName);

  if (existsSync(oldPath) && oldName !== newName) {
    console.log(`\n📁 テーマディレクトリをリネーム: ${oldName} → ${newName}`);
    renameSync(oldPath, newPath);
    return true;
  }
  return false;
}

// .mcp.json のプロジェクトパスを更新
function updateMcpJson(projectName) {
  const mcpPath = join(projectRoot, '.mcp.json');
  if (existsSync(mcpPath)) {
    const content = readFileSync(mcpPath, 'utf8');
    const mcpConfig = JSON.parse(content);

    if (mcpConfig.mcpServers?.serena?.args) {
      const args = mcpConfig.mcpServers.serena.args;
      const projectIndex = args.indexOf('--project');
      if (projectIndex !== -1 && projectIndex + 1 < args.length) {
        const currentPath = args[projectIndex + 1];
        const newPath = currentPath.replace(/\/[^\/]+$/, `/${projectName}`);
        args[projectIndex + 1] = newPath;

        writeFileSync(mcpPath, JSON.stringify(mcpConfig, null, 2), 'utf8');
        console.log(`✓ .mcp.json のプロジェクトパスを更新: ${newPath}`);
      }
    }
  }
}

// メイン処理
async function main() {
  try {
    // ユーザー入力を取得
    const inputs = await getUserInputs();

    console.log('\n🔄 ファイルを置き換え中...\n');

    // ファイル内容を置き換え
    const stats = processDirectory(projectRoot, inputs);

    // テーマディレクトリをリネーム
    renameThemeDirectory(PLACEHOLDERS.THEME_DIR, inputs.THEME_DIR);

    // .mcp.json を更新
    updateMcpJson(inputs.PROJECT_NAME);

    // 完了メッセージ
    console.log('\n===========================================');
    console.log('✅ プロジェクト初期化完了！');
    console.log('===========================================');
    console.log(`処理ファイル数: ${stats.files}`);
    console.log(`変更ファイル数: ${stats.modified}`);
    console.log('===========================================\n');

    console.log('📝 次のステップ:');
    console.log('  1. npm install');
    console.log('  2. npm run docker:init');
    console.log('  3. npm run dev\n');

    // このスクリプト自体を削除するか確認
    console.log('⚠️  このスクリプトは1回のみ実行してください。');
    console.log('   再実行すると意図しない置き換えが発生する可能性があります。\n');

  } catch (error) {
    console.error('\n❌ エラーが発生しました:', error.message);
    process.exit(1);
  }
}

main();
