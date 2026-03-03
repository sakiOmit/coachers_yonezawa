#!/usr/bin/env node
/**
 * HTMLセマンティック構造チェック
 *
 * html-validateでは検出できないWordPress/プロジェクト固有の
 * セマンティック構造問題を検出
 */

import fs from 'fs';
import { glob } from 'glob';
import path from 'path';

interface SemanticIssue {
  file: string;
  line: number;
  type: 'semantic-structure' | 'list-candidate' | 'article-candidate' | 'button-vs-link';
  severity: 'error' | 'warning' | 'info';
  message: string;
  content: string;
  suggestion: string;
}

interface SemanticReport {
  timestamp: string;
  totalFiles: number;
  totalIssues: number;
  issues: SemanticIssue[];
  summary: {
    errors: number;
    warnings: number;
    info: number;
    byType: Record<string, number>;
  };
}

/**
 * PHPコードを除外してHTMLのみを抽出
 */
function extractHTML(content: string): string {
  // PHP開始タグから終了タグまでを一時的にプレースホルダーに置換
  return content.replace(/<\?php[\s\S]*?\?>/g, '<?php /* ... */ ?>');
}

/**
 * セクションに見出しがあるかチェック
 */
function checkSectionHeadings(content: string, filePath: string): SemanticIssue[] {
  const issues: SemanticIssue[] = [];
  const lines = content.split('\n');

  let inSection = false;
  let sectionStartLine = -1;
  let hasHeading = false;

  lines.forEach((line, index) => {
    const lineNum = index + 1;

    // セクション開始
    if (/<section[\s>]/.test(line)) {
      inSection = true;
      sectionStartLine = lineNum;
      hasHeading = false;
    }

    // セクション内で見出しを検出
    if (inSection && /<h[1-6][\s>]/.test(line)) {
      hasHeading = true;
    }

    // セクション終了
    if (inSection && /<\/section>/.test(line)) {
      if (!hasHeading) {
        issues.push({
          file: filePath,
          line: sectionStartLine,
          type: 'semantic-structure',
          severity: 'warning',
          message: '<section> に見出し要素がありません',
          content: lines[sectionStartLine - 1].trim(),
          suggestion: '<section> 内に <h2>～<h6> の見出しを追加するか、意味的に <div> に変更してください'
        });
      }
      inSection = false;
    }
  });

  return issues;
}

/**
 * リスト候補を検出（同じクラス名の要素が3つ以上連続）
 */
function checkListCandidates(content: string, filePath: string): SemanticIssue[] {
  const issues: SemanticIssue[] = [];
  const lines = content.split('\n');

  // __item, __card, __post などのパターン
  const itemPattern = /class=["'][^"']*(?:__item|__card|__post|__entry|__box)[^"']*["']/;

  let consecutiveItems: { line: number; content: string; className: string }[] = [];
  let lastClassName = '';

  lines.forEach((line, index) => {
    const lineNum = index + 1;
    const match = line.match(itemPattern);

    if (match) {
      const classMatch = line.match(/class=["']([^"']+)["']/);
      const className = classMatch ? classMatch[1] : '';

      if (className === lastClassName) {
        consecutiveItems.push({ line: lineNum, content: line.trim(), className });
      } else {
        // 連続が途切れた、前の連続アイテムをチェック
        if (consecutiveItems.length >= 3) {
          const firstItem = consecutiveItems[0];
          issues.push({
            file: filePath,
            line: firstItem.line,
            type: 'list-candidate',
            severity: 'warning',
            message: `同じクラス "${firstItem.className}" の要素が${consecutiveItems.length}個連続しています`,
            content: firstItem.content,
            suggestion: '<ul> または <ol> でリスト構造にすることを検討してください'
          });
        }

        // 新しい連続開始
        consecutiveItems = [{ line: lineNum, content: line.trim(), className }];
        lastClassName = className;
      }
    } else {
      // アイテムでない行が来たら連続をチェック
      if (consecutiveItems.length >= 3) {
        const firstItem = consecutiveItems[0];
        issues.push({
          file: filePath,
          line: firstItem.line,
          type: 'list-candidate',
          severity: 'warning',
          message: `同じクラス "${firstItem.className}" の要素が${consecutiveItems.length}個連続しています`,
          content: firstItem.content,
          suggestion: '<ul> または <ol> でリスト構造にすることを検討してください'
        });
      }
      consecutiveItems = [];
      lastClassName = '';
    }
  });

  // ファイル末尾の連続アイテムをチェック
  if (consecutiveItems.length >= 3) {
    const firstItem = consecutiveItems[0];
    issues.push({
      file: filePath,
      line: firstItem.line,
      type: 'list-candidate',
      severity: 'warning',
      message: `同じクラス "${firstItem.className}" の要素が${consecutiveItems.length}個連続しています`,
      content: firstItem.content,
      suggestion: '<ul> または <ol> でリスト構造にすることを検討してください'
    });
  }

  return issues;
}

/**
 * article候補を検出（__item/__card/__postなのに<div>）
 */
function checkArticleCandidates(content: string, filePath: string): SemanticIssue[] {
  const issues: SemanticIssue[] = [];
  const lines = content.split('\n');

  // 記事らしいクラス名パターン
  const articlePattern = /<div[^>]*class=["'][^"']*(?:__post|__article|__card|__entry)[^"']*["']/;

  lines.forEach((line, index) => {
    const lineNum = index + 1;

    // PHP配列定義の行はスキップ（例: 'class' => 'p-top-company__card'）
    if (/['"]\s*=>\s*['"]/.test(line)) {
      return;
    }

    // PHPコメント内はスキップ
    if (/^\s*\/\//.test(line) || /^\s*\*/.test(line)) {
      return;
    }

    if (articlePattern.test(line)) {
      const classMatch = line.match(/class=["']([^"']+)["']/);
      const className = classMatch ? classMatch[1] : '';

      // クラス名にPHPコードの残骸がある場合はスキップ
      if (className.includes('<?') || className.includes('$')) {
        return;
      }

      issues.push({
        file: filePath,
        line: lineNum,
        type: 'article-candidate',
        severity: 'info',
        message: `"${className}" は <article> 要素が適切かもしれません`,
        content: line.trim(),
        suggestion: '独立したコンテンツの場合は <div> を <article> に変更してください'
      });
    }
  });

  return issues;
}

/**
 * ボタン vs リンクの誤用を検出
 */
function checkButtonVsLink(content: string, filePath: string): SemanticIssue[] {
  const issues: SemanticIssue[] = [];
  const lines = content.split('\n');

  lines.forEach((line, index) => {
    const lineNum = index + 1;

    // href="#" + onclick の <a> で button クラス（真にbuttonにすべきケース）
    if ((/<a[^>]*href=["']#["'][^>]*onclick/.test(line) || /<a[^>]*onclick[^>]*href=["']#["']/.test(line)) &&
        (/<a[^>]*class=["'][^"']*button[^"']*["']/.test(line))) {
      issues.push({
        file: filePath,
        line: lineNum,
        type: 'button-vs-link',
        severity: 'warning',
        message: 'JavaScript実行用の <a href="#"> でボタンスタイルが使用されています',
        content: line.trim(),
        suggestion: 'アクション実行の場合は <button type="button"> 要素を使用してください'
      });
    }

    // href="#" のみ（onclick なし）→ 実装未完了のダミーリンク
    // Note: これはリンクチェックで検出されるため、ここでは検出しない
  });

  return issues;
}

/**
 * 単一ファイルをチェック
 */
async function checkFile(filePath: string): Promise<SemanticIssue[]> {
  const content = fs.readFileSync(filePath, 'utf-8');
  const htmlContent = extractHTML(content);

  const issues: SemanticIssue[] = [
    ...checkSectionHeadings(htmlContent, filePath),
    ...checkListCandidates(htmlContent, filePath),
    ...checkArticleCandidates(htmlContent, filePath),
    ...checkButtonVsLink(htmlContent, filePath)
  ];

  return issues;
}

/**
 * メイン処理
 */
async function main() {
  console.log('🔍 HTMLセマンティック構造チェック開始...\n');

  // チェック対象ファイル
  const { detectThemeName } = await import('../lib/detect-theme.js');
  const themeName = detectThemeName();
  const files = await glob(`themes/${themeName}/**/*.php`, {
    ignore: ['**/node_modules/**', '**/vendor/**']
  });

  console.log(`📁 対象ファイル: ${files.length}件\n`);

  const allIssues: SemanticIssue[] = [];

  for (const file of files) {
    const issues = await checkFile(file);
    allIssues.push(...issues);
  }

  // サマリー集計
  const summary = {
    errors: allIssues.filter(i => i.severity === 'error').length,
    warnings: allIssues.filter(i => i.severity === 'warning').length,
    info: allIssues.filter(i => i.severity === 'info').length,
    byType: allIssues.reduce((acc, issue) => {
      acc[issue.type] = (acc[issue.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  };

  // レポート生成
  const report: SemanticReport = {
    timestamp: new Date().toISOString(),
    totalFiles: files.length,
    totalIssues: allIssues.length,
    issues: allIssues,
    summary
  };

  // JSON出力
  const reportDir = path.join(process.cwd(), 'reports');
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  const reportPath = path.join(reportDir, 'html-semantic-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8');

  // コンソール出力
  console.log('📊 セマンティック構造チェック結果:\n');
  console.log(`総ファイル数: ${files.length}`);
  console.log(`総問題数: ${allIssues.length}`);
  console.log(`  エラー: ${summary.errors}`);
  console.log(`  警告: ${summary.warnings}`);
  console.log(`  情報: ${summary.info}\n`);

  console.log('問題種別:');
  Object.entries(summary.byType).forEach(([type, count]) => {
    console.log(`  ${type}: ${count}`);
  });

  console.log(`\n✅ レポート保存: ${reportPath}`);

  // エラーがあれば終了コード1
  if (summary.errors > 0) {
    process.exit(1);
  }
}

main().catch(error => {
  console.error('❌ エラー:', error);
  process.exit(1);
});
