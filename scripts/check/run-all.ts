#!/usr/bin/env node
/**
 * 統合チェックスクリプト
 *
 * リンクチェック・画像チェックを一括実行し、
 * Markdownレポートを生成します。
 *
 * Usage:
 *   npm run check:all
 *   npm run check:all -- --base-url http://localhost:3000
 */

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

// デフォルトのベースURL
const DEFAULT_BASE_URL = 'http://localhost:8000';

interface CheckResult {
  name: string;
  success: boolean;
  duration: number;
  summary?: {
    total: number;
    ok: number;
    issues: number;
  };
  error?: string;
}

/**
 * コマンドを実行して結果を取得
 */
function runCommand(command: string, description: string): CheckResult {
  const startTime = Date.now();
  console.log(`\n${'='.repeat(80)}`);
  console.log(`🔍 ${description}を実行中...`);
  console.log(`${'='.repeat(80)}\n`);

  try {
    execSync(command, {
      stdio: 'inherit',
      cwd: process.cwd(),
    });

    const duration = Date.now() - startTime;
    console.log(`\n✅ ${description}が完了しました (${(duration / 1000).toFixed(1)}秒)\n`);

    return {
      name: description,
      success: true,
      duration,
    };
  } catch (error) {
    const duration = Date.now() - startTime;
    console.log(`\n❌ ${description}でエラーが発生しました (${(duration / 1000).toFixed(1)}秒)\n`);

    return {
      name: description,
      success: false,
      duration,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

/**
 * JSONレポートを読み込んでサマリーを取得
 */
function loadReportSummary(reportPath: string): CheckResult['summary'] | null {
  try {
    if (!fs.existsSync(reportPath)) {
      return null;
    }

    const reportContent = fs.readFileSync(reportPath, 'utf-8');
    const report = JSON.parse(reportContent);

    // レポートの形式に応じてサマリーを抽出
    if (report.summary) {
      const summary = report.summary;
      const total = report.totalIssues || report.totalLinks || report.totalImages || 0;
      const ok = summary.ok || 0;
      const issues = total - ok;

      return { total, ok, issues };
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Markdownレポートを生成
 */
function generateMarkdownReport(results: CheckResult[], baseUrl: string): string {
  const timestamp = new Date().toISOString();
  const totalDuration = results.reduce((sum, r) => sum + r.duration, 0);

  let markdown = `# チェックレポート\n\n`;
  markdown += `**実行日時**: ${new Date(timestamp).toLocaleString('ja-JP')}\n`;
  markdown += `**ベースURL**: ${baseUrl}\n`;
  markdown += `**総実行時間**: ${(totalDuration / 1000).toFixed(1)}秒\n\n`;
  markdown += `---\n\n`;

  // サマリーテーブル
  markdown += `## 📊 サマリー\n\n`;
  markdown += `| チェック項目 | ステータス | 実行時間 | 検出数 |\n`;
  markdown += `|-------------|----------|---------|--------|\n`;

  results.forEach((result) => {
    const status = result.success ? '✅ 成功' : '❌ 失敗';
    const duration = `${(result.duration / 1000).toFixed(1)}秒`;
    const issues = result.summary ? `${result.summary.issues}件` : '-';

    markdown += `| ${result.name} | ${status} | ${duration} | ${issues} |\n`;
  });

  markdown += `\n---\n\n`;

  // 詳細結果
  markdown += `## 📋 詳細結果\n\n`;

  results.forEach((result, index) => {
    markdown += `### ${index + 1}. ${result.name}\n\n`;

    if (result.success) {
      markdown += `**ステータス**: ✅ 成功\n`;
      markdown += `**実行時間**: ${(result.duration / 1000).toFixed(1)}秒\n\n`;

      if (result.summary) {
        markdown += `**検出結果**:\n`;
        markdown += `- 総数: ${result.summary.total}件\n`;
        markdown += `- 正常: ${result.summary.ok}件\n`;
        markdown += `- 問題: ${result.summary.issues}件\n\n`;

        if (result.summary.issues > 0) {
          markdown += `⚠️ **問題が見つかりました。詳細はJSONレポートを確認してください。**\n\n`;
        } else {
          markdown += `✅ **問題は見つかりませんでした。**\n\n`;
        }
      }
    } else {
      markdown += `**ステータス**: ❌ 失敗\n`;
      markdown += `**実行時間**: ${(result.duration / 1000).toFixed(1)}秒\n\n`;

      if (result.error) {
        markdown += `**エラー内容**:\n`;
        markdown += `\`\`\`\n${result.error}\n\`\`\`\n\n`;
      }
    }

    markdown += `---\n\n`;
  });

  // 生成されたファイル
  markdown += `## 📄 生成されたファイル\n\n`;
  markdown += `- \`reports/link-check-report.json\` - リンクチェック（静的解析）の詳細結果\n`;
  markdown += `- \`reports/link-crawl-report.json\` - リンクチェック（クローラー）の詳細結果\n`;
  markdown += `- \`reports/image-check-report.json\` - 画像チェックの詳細結果\n`;
  markdown += `- \`reports/template-quality-report.json\` - テンプレート品質チェックの詳細結果\n`;
  markdown += `- \`reports/check-report.md\` - このMarkdownレポート\n\n`;

  markdown += `---\n\n`;
  markdown += `**レポート生成日時**: ${new Date(timestamp).toLocaleString('ja-JP')}\n`;

  return markdown;
}

/**
 * メイン処理
 */
async function main() {
  const args = process.argv.slice(2);
  const baseUrlIndex = args.indexOf('--base-url');
  const baseUrl =
    baseUrlIndex !== -1 && args[baseUrlIndex + 1]
      ? args[baseUrlIndex + 1]
      : DEFAULT_BASE_URL;

  console.log(`\n${'='.repeat(80)}`);
  console.log(`🚀 統合チェックを開始します`);
  console.log(`🌐 ベースURL: ${baseUrl}`);
  console.log(`${'='.repeat(80)}\n`);

  const results: CheckResult[] = [];

  // 1. リンクチェック（静的解析）
  const linksStaticResult = runCommand(
    'npm run check:links',
    'リンクチェック（静的解析）'
  );
  linksStaticResult.summary = loadReportSummary(
    path.join(process.cwd(), 'reports/link-check-report.json')
  ) || undefined;
  results.push(linksStaticResult);

  // 2. リンクチェック（クローラー）
  const linksCrawlResult = runCommand(
    `npm run check:links:crawl -- --base-url ${baseUrl}`,
    'リンクチェック（クローラー）'
  );
  linksCrawlResult.summary = loadReportSummary(
    path.join(process.cwd(), 'reports/link-crawl-report.json')
  ) || undefined;
  results.push(linksCrawlResult);

  // 3. 画像チェック
  const imagesResult = runCommand(
    `npm run check:images -- --base-url ${baseUrl}`,
    '画像404チェック'
  );
  imagesResult.summary = loadReportSummary(
    path.join(process.cwd(), 'reports/image-check-report.json')
  ) || undefined;
  results.push(imagesResult);

  // 4. テンプレート品質チェック
  const templatesResult = runCommand(
    'npm run check:templates',
    'テンプレート品質チェック'
  );
  templatesResult.summary = loadReportSummary(
    path.join(process.cwd(), 'reports/template-quality-report.json')
  ) || undefined;
  results.push(templatesResult);

  // Markdownレポート生成
  console.log(`\n${'='.repeat(80)}`);
  console.log(`📝 Markdownレポートを生成中...`);
  console.log(`${'='.repeat(80)}\n`);

  const markdown = generateMarkdownReport(results, baseUrl);
  const reportPath = path.join(process.cwd(), 'reports/check-report.md');
  fs.writeFileSync(reportPath, markdown);

  console.log(`✅ Markdownレポートを生成しました: ${reportPath}\n`);

  // 最終サマリー
  console.log(`\n${'='.repeat(80)}`);
  console.log(`📊 最終サマリー`);
  console.log(`${'='.repeat(80)}\n`);

  const successCount = results.filter((r) => r.success).length;
  const totalIssues = results.reduce((sum, r) => sum + (r.summary?.issues || 0), 0);

  console.log(`✅ 成功: ${successCount}/${results.length}件`);
  console.log(`⚠️  検出された問題: ${totalIssues}件\n`);

  if (totalIssues > 0) {
    console.log(`📄 詳細は以下のファイルを確認してください:`);
    console.log(`   - reports/check-report.md（Markdownレポート）`);
    console.log(`   - reports/*.json（各種JSONレポート）\n`);
  } else {
    console.log(`🎉 問題は見つかりませんでした！\n`);
  }

  // エラーがあった場合は終了コード1
  if (results.some((r) => !r.success)) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('エラーが発生しました:', error);
  process.exit(1);
});
