#!/usr/bin/env node
/**
 * リンククローラースクリプト
 *
 * 実際のWebサイトをクロールし、リンク切れやダミーリンクを検出します。
 *
 * Usage:
 *   npm run check-links:crawl
 *   npm run check-links:crawl -- --base-url http://localhost:8000
 */

import fs from 'fs';
import path from 'path';
import { JSDOM } from 'jsdom';

// デフォルトのベースURL
const DEFAULT_BASE_URL = 'http://localhost:8000';

// クロール対象のページ（プロジェクトに応じて編集してください）
const PAGES_TO_CRAWL = [
  '/',
  '/contact/',
  '/thanks/',
  '/privacy/',
];

interface LinkCheckResult {
  url: string;
  status: 'ok' | 'broken' | 'dummy' | 'redirect' | 'timeout' | 'error';
  statusCode?: number;
  redirectUrl?: string;
  error?: string;
  foundOn: string[];
}

interface CrawlResult {
  baseUrl: string;
  timestamp: string;
  totalLinks: number;
  checkedLinks: Map<string, LinkCheckResult>;
  summary: {
    ok: number;
    broken: number;
    dummy: number;
    redirect: number;
    timeout: number;
    error: number;
  };
}

/**
 * ダミーリンクかどうか判定
 */
function isDummyLink(url: string): boolean {
  const dummyPatterns = [
    /^#$/,
    /^javascript:void\(0\)$/i,
    /^javascript:$/i,
    /example\.com/i,
    /placeholder/i,
    /dummy/i,
    /test\.com/i,
  ];

  return dummyPatterns.some((pattern) => pattern.test(url));
}

/**
 * URLを正規化
 */
function normalizeUrl(url: string, baseUrl: string, currentPageUrl: string): string | null {
  // 空のURLはスキップ
  if (!url) {
    return null;
  }

  // ハッシュのみ・JavaScriptプロトコルはそのまま返す（ダミーリンクチェック対象）
  if (url === '#' || url.startsWith('javascript:')) {
    return url;
  }

  // メールリンク・電話リンクはスキップ
  if (url.startsWith('mailto:') || url.startsWith('tel:')) {
    return null;
  }

  // 絶対URL
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  // 相対URLを絶対URLに変換
  try {
    const base = new URL(currentPageUrl, baseUrl);
    return new URL(url, base.href).href;
  } catch {
    return null;
  }
}

/**
 * ページからリンクを抽出
 */
async function extractLinks(pageUrl: string, baseUrl: string): Promise<string[]> {
  try {
    console.log(`  📄 取得中: ${pageUrl}`);

    const response = await fetch(pageUrl, {
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      console.log(`  ⚠️  HTTPエラー: ${response.status}`);
      return [];
    }

    const html = await response.text();
    const dom = new JSDOM(html);
    const document = dom.window.document;

    const links: string[] = [];
    const anchorTags = document.querySelectorAll('a[href]');

    anchorTags.forEach((anchor) => {
      const href = anchor.getAttribute('href');
      if (href) {
        const normalized = normalizeUrl(href, baseUrl, pageUrl);
        if (normalized) {
          links.push(normalized);
        }
      }
    });

    console.log(`  ✓ ${links.length}個のリンクを抽出`);
    return links;
  } catch (error) {
    console.log(`  ❌ エラー: ${error instanceof Error ? error.message : String(error)}`);
    return [];
  }
}

/**
 * リンクをチェック
 */
async function checkLink(url: string, baseUrl: string): Promise<LinkCheckResult> {
  // ダミーリンクチェック
  if (isDummyLink(url)) {
    return {
      url,
      status: 'dummy',
      foundOn: [],
    };
  }

  // 外部リンクは一部のみチェック（オプションで変更可能）
  const isExternal = !url.startsWith(baseUrl);

  try {
    const response = await fetch(url, {
      method: 'HEAD', // HEADリクエストで軽量化
      signal: AbortSignal.timeout(10000),
      redirect: 'manual', // リダイレクトを手動処理
    });

    const statusCode = response.status;

    // リダイレクト
    if (statusCode >= 300 && statusCode < 400) {
      const redirectUrl = response.headers.get('location') || undefined;
      return {
        url,
        status: 'redirect',
        statusCode,
        redirectUrl,
        foundOn: [],
      };
    }

    // 正常
    if (statusCode >= 200 && statusCode < 300) {
      return {
        url,
        status: 'ok',
        statusCode,
        foundOn: [],
      };
    }

    // エラー
    return {
      url,
      status: 'broken',
      statusCode,
      foundOn: [],
    };
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'TimeoutError') {
        return {
          url,
          status: 'timeout',
          error: 'タイムアウト',
          foundOn: [],
        };
      }
      return {
        url,
        status: 'error',
        error: error.message,
        foundOn: [],
      };
    }
    return {
      url,
      status: 'error',
      error: String(error),
      foundOn: [],
    };
  }
}

/**
 * クロール実行
 */
async function crawl(baseUrl: string): Promise<CrawlResult> {
  console.log(`\n🔍 リンククロールを開始します...`);
  console.log(`🌐 ベースURL: ${baseUrl}\n`);

  const allLinks = new Map<string, Set<string>>(); // URL -> Set<発見元ページ>
  const checkedLinks = new Map<string, LinkCheckResult>();

  // 各ページからリンクを収集
  console.log(`📋 ページからリンクを収集中...\n`);

  for (const pagePath of PAGES_TO_CRAWL) {
    const pageUrl = `${baseUrl}${pagePath}`;
    const links = await extractLinks(pageUrl, baseUrl);

    links.forEach((link) => {
      if (!allLinks.has(link)) {
        allLinks.set(link, new Set());
      }
      allLinks.get(link)!.add(pageUrl);
    });
  }

  console.log(`\n✓ 合計 ${allLinks.size} 個のユニークなリンクを検出\n`);
  console.log(`🔗 リンクをチェック中...\n`);

  // 各リンクをチェック
  let checked = 0;
  for (const [link, foundOnPages] of allLinks.entries()) {
    checked++;
    process.stdout.write(`\r  進捗: ${checked}/${allLinks.size}`);

    const result = await checkLink(link, baseUrl);
    result.foundOn = Array.from(foundOnPages);
    checkedLinks.set(link, result);

    // レート制限（100ms間隔）
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  console.log(`\n`);

  // サマリー計算
  const summary = {
    ok: 0,
    broken: 0,
    dummy: 0,
    redirect: 0,
    timeout: 0,
    error: 0,
  };

  checkedLinks.forEach((result) => {
    summary[result.status]++;
  });

  return {
    baseUrl,
    timestamp: new Date().toISOString(),
    totalLinks: allLinks.size,
    checkedLinks,
    summary,
  };
}

/**
 * 結果を表示
 */
function printResults(result: CrawlResult) {
  console.log(`\n${'='.repeat(80)}`);
  console.log(`\n📊 クロール結果サマリー\n`);
  console.log(`  ✅ 正常: ${result.summary.ok}`);
  console.log(`  ❌ リンク切れ: ${result.summary.broken}`);
  console.log(`  🔗 ダミーリンク: ${result.summary.dummy}`);
  console.log(`  ➡️  リダイレクト: ${result.summary.redirect}`);
  console.log(`  ⏱️  タイムアウト: ${result.summary.timeout}`);
  console.log(`  ⚠️  エラー: ${result.summary.error}`);
  console.log(`  ━━━━━━━━━━━━━━━━`);
  console.log(`  📋 合計: ${result.totalLinks}\n`);

  // 問題のあるリンクを詳細表示
  const issues = Array.from(result.checkedLinks.values()).filter(
    (r) => r.status !== 'ok'
  );

  if (issues.length === 0) {
    console.log(`✅ 問題のあるリンクは見つかりませんでした。\n`);
    return;
  }

  console.log(`${'─'.repeat(80)}\n`);
  console.log(`❌ 問題のあるリンク (${issues.length}件):\n`);

  // タイプごとにグループ化
  const grouped = issues.reduce((acc, issue) => {
    if (!acc[issue.status]) {
      acc[issue.status] = [];
    }
    acc[issue.status].push(issue);
    return acc;
  }, {} as Record<string, LinkCheckResult[]>);

  Object.entries(grouped).forEach(([status, statusIssues]) => {
    const statusLabels: Record<string, string> = {
      broken: 'リンク切れ',
      dummy: 'ダミーリンク',
      redirect: 'リダイレクト',
      timeout: 'タイムアウト',
      error: 'エラー',
    };

    console.log(`\n📋 ${statusLabels[status]} (${statusIssues.length}件):`);
    console.log('─'.repeat(80));

    statusIssues.forEach((issue) => {
      console.log(`\n  🔗 ${issue.url}`);
      if (issue.statusCode) {
        console.log(`  📊 ステータス: ${issue.statusCode}`);
      }
      if (issue.redirectUrl) {
        console.log(`  ➡️  リダイレクト先: ${issue.redirectUrl}`);
      }
      if (issue.error) {
        console.log(`  ⚠️  エラー: ${issue.error}`);
      }
      console.log(`  📄 発見元 (${issue.foundOn.length}ページ):`);
      issue.foundOn.slice(0, 3).forEach((page) => {
        console.log(`     - ${page}`);
      });
      if (issue.foundOn.length > 3) {
        console.log(`     ... 他${issue.foundOn.length - 3}ページ`);
      }
    });
  });

  console.log(`\n${'─'.repeat(80)}\n`);
}

/**
 * JSONレポート保存
 */
function saveJsonReport(result: CrawlResult, outputPath: string) {
  const report = {
    baseUrl: result.baseUrl,
    timestamp: result.timestamp,
    totalLinks: result.totalLinks,
    summary: result.summary,
    links: Array.from(result.checkedLinks.entries()).map(([url, result]) => ({
      url,
      ...result,
    })),
  };

  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
  console.log(`📊 レポートを保存しました: ${outputPath}\n`);
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

  const result = await crawl(baseUrl);

  printResults(result);

  // JSONレポート保存
  const reportPath = path.join(process.cwd(), 'reports/link-crawl-report.json');
  saveJsonReport(result, reportPath);
}

main().catch((error) => {
  console.error('エラーが発生しました:', error);
  process.exit(1);
});
