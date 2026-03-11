#!/usr/bin/env node
/**
 * 静的リンクチェックスクリプト
 *
 * PHPテンプレートファイル内のaタグを解析し、
 * ダミーリンクや問題のあるリンクを検出します。
 *
 * Usage:
 *   npm run check-links
 */

import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { detectThemeName } from '../lib/detect-theme.js';

const THEME_NAME = detectThemeName();

// チェック対象のディレクトリ
const TARGET_DIRS = [
  `themes/${THEME_NAME}/pages`,
  `themes/${THEME_NAME}/template-parts`,
  `themes/${THEME_NAME}`,
];

// ダミーリンクのパターン
const DUMMY_PATTERNS = {
  emptyHref: /href=["']["']/,
  hashOnly: /href=["']#["']/,
  placeholderDomains: /href=["'][^"']*(?:example\.com|placeholder|dummy|test\.com)[^"']*["']/i,
  noHref: /<a(?:\s+[^>]*)?(?<!href=["'][^"']*)[^>]*>/,
};

/**
 * PHP変数展開を含むかチェック（偽陽性除外用）
 */
function containsPhpVariable(line: string): boolean {
  return /\$\w+|<\?php|\?>|esc_url|esc_attr/.test(line);
}

interface LinkIssue {
  file: string;
  line: number;
  type: 'empty-href' | 'hash-only' | 'placeholder' | 'no-href' | 'suspicious';
  content: string;
  url?: string;
}

/**
 * ファイル内のリンクをチェック
 */
function checkFile(filePath: string): LinkIssue[] {
  const issues: LinkIssue[] = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  lines.forEach((line, index) => {
    const lineNumber = index + 1;

    // PHP変数展開を含む行はスキップ（偽陽性除外）
    if (containsPhpVariable(line)) {
      return;
    }

    // aタグを検出
    const aTagMatches = line.matchAll(/<a\s+[^>]*>/g);

    for (const match of aTagMatches) {
      const aTag = match[0];

      // href属性なし
      if (!aTag.includes('href=')) {
        issues.push({
          file: filePath,
          line: lineNumber,
          type: 'no-href',
          content: aTag.trim(),
        });
        continue;
      }

      // href=""
      if (DUMMY_PATTERNS.emptyHref.test(aTag)) {
        issues.push({
          file: filePath,
          line: lineNumber,
          type: 'empty-href',
          content: aTag.trim(),
          url: '',
        });
        continue;
      }

      // href="#"
      if (DUMMY_PATTERNS.hashOnly.test(aTag)) {
        issues.push({
          file: filePath,
          line: lineNumber,
          type: 'hash-only',
          content: aTag.trim(),
          url: '#',
        });
        continue;
      }

      // プレースホルダードメイン
      const placeholderMatch = aTag.match(/href=["']([^"']*)["']/);
      if (placeholderMatch) {
        const url = placeholderMatch[1];
        if (DUMMY_PATTERNS.placeholderDomains.test(aTag)) {
          issues.push({
            file: filePath,
            line: lineNumber,
            type: 'placeholder',
            content: aTag.trim(),
            url,
          });
        }
      }
    }
  });

  return issues;
}

/**
 * ディレクトリ内のPHPファイルを再帰的に検索
 */
async function findPhpFiles(baseDir: string): Promise<string[]> {
  const pattern = path.join(baseDir, '**/*.php');
  return await glob(pattern, { ignore: ['**/node_modules/**', '**/vendor/**'] });
}

/**
 * 結果をコンソールに出力
 */
function printResults(issues: LinkIssue[]) {
  if (issues.length === 0) {
    console.log('✅ 問題のあるリンクは見つかりませんでした。\n');
    return;
  }

  console.log(`\n❌ ${issues.length}件の問題が見つかりました:\n`);

  // タイプごとにグループ化
  const grouped = issues.reduce((acc, issue) => {
    if (!acc[issue.type]) {
      acc[issue.type] = [];
    }
    acc[issue.type].push(issue);
    return acc;
  }, {} as Record<string, LinkIssue[]>);

  // タイプごとに出力
  Object.entries(grouped).forEach(([type, typeIssues]) => {
    const typeLabels = {
      'empty-href': '空のhref',
      'hash-only': 'ハッシュのみ (#)',
      'placeholder': 'プレースホルダードメイン',
      'no-href': 'href属性なし',
      'suspicious': '疑わしいリンク',
    };

    console.log(`\n📋 ${typeLabels[type as keyof typeof typeLabels]} (${typeIssues.length}件):`);
    console.log('─'.repeat(80));

    typeIssues.forEach((issue) => {
      const relativePath = path.relative(process.cwd(), issue.file);
      console.log(`\n  📄 ${relativePath}:${issue.line}`);
      if (issue.url) {
        console.log(`  🔗 URL: ${issue.url}`);
      }
      console.log(`  📝 ${issue.content}`);
    });
  });

  console.log('\n' + '─'.repeat(80));
  console.log(`\n合計: ${issues.length}件の問題\n`);
}

/**
 * JSONレポート出力
 */
function saveJsonReport(issues: LinkIssue[], outputPath: string) {
  const report = {
    timestamp: new Date().toISOString(),
    totalIssues: issues.length,
    issues,
    summary: {
      'empty-href': issues.filter((i) => i.type === 'empty-href').length,
      'hash-only': issues.filter((i) => i.type === 'hash-only').length,
      'placeholder': issues.filter((i) => i.type === 'placeholder').length,
      'no-href': issues.filter((i) => i.type === 'no-href').length,
      'suspicious': issues.filter((i) => i.type === 'suspicious').length,
    },
  };

  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
  console.log(`📊 レポートを保存しました: ${outputPath}\n`);
}

/**
 * メイン処理
 */
async function main() {
  console.log('🔍 リンクチェックを開始します...\n');

  const allIssues: LinkIssue[] = [];

  for (const dir of TARGET_DIRS) {
    const fullPath = path.join(process.cwd(), dir);

    if (!fs.existsSync(fullPath)) {
      console.log(`⚠️  ディレクトリが見つかりません: ${dir}`);
      continue;
    }

    console.log(`📂 チェック中: ${dir}`);
    const files = await findPhpFiles(fullPath);
    console.log(`   ${files.length}ファイル見つかりました`);

    for (const file of files) {
      const issues = checkFile(file);
      allIssues.push(...issues);
    }
  }

  console.log('\n' + '='.repeat(80));
  printResults(allIssues);

  // JSONレポート出力
  const reportPath = path.join(process.cwd(), 'reports/link-check-report.json');
  saveJsonReport(allIssues, reportPath);
}

main().catch((error) => {
  console.error('エラーが発生しました:', error);
  process.exit(1);
});
