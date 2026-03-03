#!/usr/bin/env node

/**
 * テンプレート化スクリプト
 *
 * 現在のプロジェクトをgitテンプレートリポジトリ化するために、
 * プロジェクト固有の情報をプレースホルダーに置き換えます。
 *
 * 使い方:
 *   npm run create-template
 *   または
 *   node scripts/create-template.js
 */

import { readFileSync, writeFileSync, renameSync, existsSync, readdirSync, statSync } from 'fs';
import { join, dirname } from 'path';
import readline from 'readline';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// 対話形式で入力を取得
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const question = (query) => new Promise((resolve) => rl.question(query, resolve));

async function getCurrentProjectInfo() {
  console.log('\n===========================================');
  console.log('🔄 プロジェクトのテンプレート化');
  console.log('===========================================\n');
  console.log('現在のプロジェクト固有情報を入力してください。');
  console.log('これらの情報がプレースホルダーに置き換えられます。\n');

  const info = {};

  info.PROJECT_NAME = await question('現在のプロジェクト名: ');
  info.THEME_DIR = await question('現在のテーマディレクトリ名: ');
  info.THEME_NAME = await question('現在のテーマ名（表示用）: ');
  info.THEME_PREFIX = await question('現在のテーマプレフィックス（PHP関数名用）: ');
  info.COMPANY_NAME = await question('現在の会社名（日本語）: ');
  info.COMPANY_NAME_EN = await question('現在の会社名（英語）: ');
  info.TEXT_DOMAIN = await question('現在のテキストドメイン: ');
  info.PACKAGE_NAME = await question('現在のパッケージ名: ');
  info.DESCRIPTION = await question('現在のプロジェクト説明: ');

  rl.close();

  // 確認
  console.log('\n===========================================');
  console.log('📋 置き換える情報の確認');
  console.log('===========================================');
  Object.entries(info).forEach(([key, value]) => {
    console.log(`${value} → {{${key}}}`);
  });
  console.log('===========================================\n');

  const confirm = await new Promise(resolve => {
    const rl2 = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
    rl2.question('この内容でテンプレート化しますか？ (y/N): ', (answer) => {
      rl2.close();
      resolve(answer.toLowerCase() === 'y');
    });
  });

  if (!confirm) {
    console.log('\n❌ キャンセルしました。');
    process.exit(0);
  }

  return info;
}

// ファイル内容を置き換え
function replaceInFile(filePath, replacements) {
  try {
    let content = readFileSync(filePath, 'utf8');
    let modified = false;

    Object.entries(replacements).forEach(([placeholder, value]) => {
      if (value && content.includes(value)) {
        const regex = new RegExp(escapeRegExp(value), 'g');
        content = content.replace(regex, `{{${placeholder}}}`);
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

// 正規表現のエスケープ
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ディレクトリを再帰的に処理
function processDirectory(dirPath, replacements, stats = { files: 0, modified: 0 }) {
  const items = readdirSync(dirPath);

  items.forEach(item => {
    const itemPath = join(dirPath, item);
    const stat = statSync(itemPath);

    // 除外ディレクトリ
    if (stat.isDirectory()) {
      if (['node_modules', '.git', 'vendor', 'wordpress_data', 'dist', 'themes'].includes(item)) {
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

// テーマディレクトリ内を処理
function processThemeDirectory(oldName, replacements) {
  const themesDir = join(projectRoot, 'themes');
  const themeDir = join(themesDir, oldName);

  if (!existsSync(themeDir)) {
    console.warn(`⚠️  テーマディレクトリが見つかりません: ${themeDir}`);
    return { files: 0, modified: 0 };
  }

  console.log(`\n📁 テーマディレクトリを処理中: ${oldName}`);
  const stats = processDirectory(themeDir, replacements);

  // ディレクトリ名を変更
  const newPath = join(themesDir, 'wordpress-template-wp');
  if (oldName !== 'wordpress-template-wp') {
    renameSync(themeDir, newPath);
    console.log(`✓ テーマディレクトリをリネーム: ${oldName} → wordpress-template-wp`);
  }

  return stats;
}

// .mcp.json のプロジェクトパスをプレースホルダー化
function templateMcpJson() {
  const mcpPath = join(projectRoot, '.mcp.json');
  if (existsSync(mcpPath)) {
    const content = readFileSync(mcpPath, 'utf8');
    const mcpConfig = JSON.parse(content);

    if (mcpConfig.mcpServers?.serena?.args) {
      const args = mcpConfig.mcpServers.serena.args;
      const projectIndex = args.indexOf('--project');
      if (projectIndex !== -1 && projectIndex + 1 < args.length) {
        const currentPath = args[projectIndex + 1];
        const newPath = currentPath.replace(/\/[^\/]+$/, '/wordpress-template');
        args[projectIndex + 1] = newPath;

        writeFileSync(mcpPath, JSON.stringify(mcpConfig, null, 2), 'utf8');
        console.log(`✓ .mcp.json をテンプレート化`);
      }
    }
  }
}

// メイン処理
async function main() {
  try {
    // 現在のプロジェクト情報を取得
    const info = await getCurrentProjectInfo();

    console.log('\n🔄 ファイルを置き換え中...\n');

    // 通常のファイルを処理
    const stats = processDirectory(projectRoot, info);

    // テーマディレクトリを処理
    const themeStats = processThemeDirectory(info.THEME_DIR, info);

    // .mcp.json をテンプレート化
    templateMcpJson();

    // 完了メッセージ
    console.log('\n===========================================');
    console.log('✅ テンプレート化完了！');
    console.log('===========================================');
    console.log(`処理ファイル数: ${stats.files + themeStats.files}`);
    console.log(`変更ファイル数: ${stats.modified + themeStats.modified}`);
    console.log('===========================================\n');

    console.log('📝 次のステップ:');
    console.log('  1. GitHubリポジトリを作成');
    console.log('  2. Settings > Template repository にチェック');
    console.log('  3. README.md にテンプレート使用方法を記載');
    console.log('  4. プッシュ\n');

    console.log('⚠️  テンプレート化したプロジェクトは開発用として使用できません。');
    console.log('   新規プロジェクトで `npm run init` を実行してください。\n');

  } catch (error) {
    console.error('\n❌ エラーが発生しました:', error.message);
    process.exit(1);
  }
}

main();
