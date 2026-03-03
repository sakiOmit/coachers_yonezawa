#!/usr/bin/env node
/**
 * 画像404チェッククローラー
 *
 * 実際のWebサイトをクロールし、画像の404エラーや読み込み失敗を検出します。
 *
 * 検出対象:
 * - <img src="...">
 * - <img srcset="...">
 * - <source srcset="..."> (picture要素)
 *
 * Usage:
 *   npm run check:images
 *   npm run check:images -- --base-url http://localhost:8000
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
  '/privacy/',
];

interface ImageCheckResult {
  url: string;
  status: 'ok' | 'broken' | 'timeout' | 'error';
  statusCode?: number;
  error?: string;
  foundOn: Array<{
    page: string;
    element: string; // img, source, etc.
    attribute: string; // src, srcset
  }>;
}

interface CrawlResult {
  baseUrl: string;
  timestamp: string;
  totalImages: number;
  checkedImages: Map<string, ImageCheckResult>;
  summary: {
    ok: number;
    broken: number;
    timeout: number;
    error: number;
  };
}

/**
 * URLを正規化
 */
function normalizeUrl(url: string, baseUrl: string, currentPageUrl: string): string | null {
  // 空のURL
  if (!url || url.trim() === '') {
    return null;
  }

  // データURI、SVG等はスキップ
  if (url.startsWith('data:') || url.startsWith('blob:')) {
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
 * srcset属性から複数のURLを抽出
 * 例: "image-1x.jpg 1x, image-2x.jpg 2x" -> ["image-1x.jpg", "image-2x.jpg"]
 */
function parseSrcset(srcset: string): string[] {
  if (!srcset) return [];

  return srcset
    .split(',')
    .map((part) => part.trim().split(/\s+/)[0]) // "url 1x" -> "url"
    .filter((url) => url && url.length > 0);
}

/**
 * ページから画像URLを抽出
 */
async function extractImages(
  pageUrl: string,
  baseUrl: string
): Promise<
  Array<{
    url: string;
    element: string;
    attribute: string;
  }>
> {
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

    const images: Array<{
      url: string;
      element: string;
      attribute: string;
    }> = [];

    // <img src="...">
    const imgTags = document.querySelectorAll('img[src]');
    imgTags.forEach((img) => {
      const src = img.getAttribute('src');
      if (src) {
        const normalized = normalizeUrl(src, baseUrl, pageUrl);
        if (normalized) {
          images.push({
            url: normalized,
            element: 'img',
            attribute: 'src',
          });
        }
      }
    });

    // <img srcset="...">
    const imgWithSrcset = document.querySelectorAll('img[srcset]');
    imgWithSrcset.forEach((img) => {
      const srcset = img.getAttribute('srcset');
      if (srcset) {
        const urls = parseSrcset(srcset);
        urls.forEach((url) => {
          const normalized = normalizeUrl(url, baseUrl, pageUrl);
          if (normalized) {
            images.push({
              url: normalized,
              element: 'img',
              attribute: 'srcset',
            });
          }
        });
      }
    });

    // <source srcset="..."> (picture要素内)
    const sourceTags = document.querySelectorAll('source[srcset]');
    sourceTags.forEach((source) => {
      const srcset = source.getAttribute('srcset');
      if (srcset) {
        const urls = parseSrcset(srcset);
        urls.forEach((url) => {
          const normalized = normalizeUrl(url, baseUrl, pageUrl);
          if (normalized) {
            images.push({
              url: normalized,
              element: 'source',
              attribute: 'srcset',
            });
          }
        });
      }
    });

    console.log(`  ✓ ${images.length}個の画像を抽出`);
    return images;
  } catch (error) {
    console.log(`  ❌ エラー: ${error instanceof Error ? error.message : String(error)}`);
    return [];
  }
}

/**
 * 画像URLをチェック
 */
async function checkImage(url: string): Promise<Omit<ImageCheckResult, 'foundOn'>> {
  try {
    const response = await fetch(url, {
      method: 'HEAD', // HEADリクエストで軽量化
      signal: AbortSignal.timeout(10000),
    });

    const statusCode = response.status;

    // 正常
    if (statusCode >= 200 && statusCode < 300) {
      return {
        url,
        status: 'ok',
        statusCode,
      };
    }

    // エラー
    return {
      url,
      status: 'broken',
      statusCode,
    };
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'TimeoutError') {
        return {
          url,
          status: 'timeout',
          error: 'タイムアウト',
        };
      }
      return {
        url,
        status: 'error',
        error: error.message,
      };
    }
    return {
      url,
      status: 'error',
      error: String(error),
    };
  }
}

/**
 * クロール実行
 */
async function crawl(baseUrl: string): Promise<CrawlResult> {
  console.log(`\n🔍 画像チェックを開始します...`);
  console.log(`🌐 ベースURL: ${baseUrl}\n`);

  const allImages = new Map<
    string,
    Array<{
      page: string;
      element: string;
      attribute: string;
    }>
  >(); // URL -> [発見元情報]

  const checkedImages = new Map<string, ImageCheckResult>();

  // 各ページから画像URLを収集
  console.log(`📋 ページから画像を収集中...\n`);

  for (const pagePath of PAGES_TO_CRAWL) {
    const pageUrl = `${baseUrl}${pagePath}`;
    const images = await extractImages(pageUrl, baseUrl);

    images.forEach((img) => {
      if (!allImages.has(img.url)) {
        allImages.set(img.url, []);
      }
      allImages.get(img.url)!.push({
        page: pageUrl,
        element: img.element,
        attribute: img.attribute,
      });
    });
  }

  console.log(`\n✓ 合計 ${allImages.size} 個のユニークな画像を検出\n`);
  console.log(`🖼️  画像をチェック中...\n`);

  // 各画像をチェック
  let checked = 0;
  for (const [imageUrl, foundOnList] of allImages.entries()) {
    checked++;
    process.stdout.write(`\r  進捗: ${checked}/${allImages.size}`);

    const result = await checkImage(imageUrl);
    checkedImages.set(imageUrl, {
      ...result,
      foundOn: foundOnList,
    });

    // レート制限（100ms間隔）
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  console.log(`\n`);

  // サマリー計算
  const summary = {
    ok: 0,
    broken: 0,
    timeout: 0,
    error: 0,
  };

  checkedImages.forEach((result) => {
    summary[result.status]++;
  });

  return {
    baseUrl,
    timestamp: new Date().toISOString(),
    totalImages: allImages.size,
    checkedImages,
    summary,
  };
}

/**
 * 結果を表示
 */
function printResults(result: CrawlResult) {
  console.log(`\n${'='.repeat(80)}`);
  console.log(`\n📊 画像チェック結果サマリー\n`);
  console.log(`  ✅ 正常: ${result.summary.ok}`);
  console.log(`  ❌ 404/エラー: ${result.summary.broken}`);
  console.log(`  ⏱️  タイムアウト: ${result.summary.timeout}`);
  console.log(`  ⚠️  その他エラー: ${result.summary.error}`);
  console.log(`  ━━━━━━━━━━━━━━━━`);
  console.log(`  📋 合計: ${result.totalImages}\n`);

  // 問題のある画像を詳細表示
  const issues = Array.from(result.checkedImages.values()).filter((r) => r.status !== 'ok');

  if (issues.length === 0) {
    console.log(`✅ 問題のある画像は見つかりませんでした。\n`);
    return;
  }

  console.log(`${'─'.repeat(80)}\n`);
  console.log(`❌ 問題のある画像 (${issues.length}件):\n`);

  // タイプごとにグループ化
  const grouped = issues.reduce((acc, issue) => {
    if (!acc[issue.status]) {
      acc[issue.status] = [];
    }
    acc[issue.status].push(issue);
    return acc;
  }, {} as Record<string, ImageCheckResult[]>);

  Object.entries(grouped).forEach(([status, statusIssues]) => {
    const statusLabels: Record<string, string> = {
      broken: '404/エラー',
      timeout: 'タイムアウト',
      error: 'その他エラー',
    };

    console.log(`\n📋 ${statusLabels[status]} (${statusIssues.length}件):`);
    console.log('─'.repeat(80));

    statusIssues.forEach((issue) => {
      console.log(`\n  🖼️  ${issue.url}`);
      if (issue.statusCode) {
        console.log(`  📊 ステータス: ${issue.statusCode}`);
      }
      if (issue.error) {
        console.log(`  ⚠️  エラー: ${issue.error}`);
      }
      console.log(`  📄 発見元 (${issue.foundOn.length}箇所):`);
      issue.foundOn.slice(0, 5).forEach((location) => {
        console.log(
          `     - ${location.page} (<${location.element} ${location.attribute}="...">)`
        );
      });
      if (issue.foundOn.length > 5) {
        console.log(`     ... 他${issue.foundOn.length - 5}箇所`);
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
    totalImages: result.totalImages,
    summary: result.summary,
    images: Array.from(result.checkedImages.entries()).map(([url, result]) => ({
      url,
      status: result.status,
      statusCode: result.statusCode,
      error: result.error,
      foundOn: result.foundOn,
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
  const reportPath = path.join(process.cwd(), 'reports/image-check-report.json');
  saveJsonReport(result, reportPath);
}

main().catch((error) => {
  console.error('エラーが発生しました:', error);
  process.exit(1);
});
