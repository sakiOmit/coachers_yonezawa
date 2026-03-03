#!/usr/bin/env node
/**
 * テンプレート品質チェックスクリプト
 *
 * PHPテンプレートファイルを解析し、コーディング規約違反や
 * 潜在的な問題を検出します。
 *
 * 検出項目:
 * - WordPress規約違反（エスケープ関数未使用等）
 * - FLOCSS + BEM命名規則違反（camelCase等）
 * - アクセシビリティ問題（alt属性なし等）
 * - コード品質問題（インラインstyle、TODO残存等）
 * - HTML構造バリデーション（html-validate）
 * - セマンティック構造問題（html-semantic）
 *
 * Usage:
 *   npm run check:templates
 */

import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { execSync } from 'child_process';
import { detectThemeName } from '../lib/detect-theme.js';

const THEME_NAME = detectThemeName();

// チェック対象のディレクトリ
const TARGET_DIRS = [
  `themes/${THEME_NAME}/pages`,
  `themes/${THEME_NAME}/template-parts`,
  `themes/${THEME_NAME}`,
];

// 除外ファイル
const EXCLUDE_FILES = [
  'functions.php',
  'style.css',
  'screenshot.png',
  'favicon.ico',
];

interface TemplateIssue {
  file: string;
  line: number;
  type:
    | 'security' // セキュリティ（エスケープなし）
    | 'wordpress' // WordPress規約
    | 'bem-naming' // BEM命名規則
    | 'accessibility' // アクセシビリティ
    | 'code-quality' // コード品質
    | 'inline-style' // インラインスタイル
    | 'deprecated'; // 非推奨タグ
  severity: 'error' | 'warning' | 'info';
  message: string;
  content: string;
  suggestion?: string;
}

/**
 * セキュリティチェック: エスケープ関数の未使用
 */
function checkSecurity(line: string, lineNumber: number, filePath: string): TemplateIssue[] {
  const issues: TemplateIssue[] = [];

  // inc/ ディレクトリ内のファイルはWordPress管理画面用なのでスキップ
  if (filePath.includes('/inc/')) {
    return issues;
  }

  // phpcs:ignore コメントがある場合はスキップ
  if (line.includes('phpcs:ignore')) {
    return issues;
  }

  // PHP変数出力でエスケープなし（簡易チェック）
  // 例: <?php echo $var; ?> （esc_html等がない）
  const echoWithoutEscape =
    /echo\s+\$[\w>-]+(?!\s*\))/g; // echo $var; （関数呼び出しでない）

  // ただし、すでにエスケープ関数を使っている場合は除外
  if (
    !line.includes('esc_html') &&
    !line.includes('esc_url') &&
    !line.includes('esc_attr') &&
    !line.includes('wp_kses')
  ) {
    const matches = line.matchAll(echoWithoutEscape);

    for (const match of matches) {
      // 数値や配列アクセスは許容
      if (/echo\s+\d+|echo\s+\$[\w>-]+\[/.test(match[0])) {
        continue;
      }

      issues.push({
        file: filePath,
        line: lineNumber,
        type: 'security',
        severity: 'error',
        message: 'エスケープ関数が使用されていない可能性があります',
        content: match[0].trim(),
        suggestion: 'esc_html(), esc_url(), esc_attr() のいずれかを使用してください',
      });
    }
  }

  return issues;
}

/**
 * WordPress規約チェック
 */
function checkWordPressConventions(
  line: string,
  lineNumber: number,
  filePath: string
): TemplateIssue[] {
  const issues: TemplateIssue[] = [];

  // inc/ ディレクトリ内のファイルはWordPress管理画面用なのでスキップ
  if (filePath.includes('/inc/')) {
    return issues;
  }

  // get_field() を if文なしで使用
  // 例: <?php echo get_field('foo'); ?> （値が存在しない場合を考慮していない）
  if (/the_field\(|get_field\(/.test(line) && !line.includes('if')) {
    // ただし、同じ行に三項演算子がある場合は許容
    if (!line.includes('?') || !line.includes(':')) {
      issues.push({
        file: filePath,
        line: lineNumber,
        type: 'wordpress',
        severity: 'warning',
        message: 'ACFフィールドの存在チェックなしで使用しています',
        content: line.trim(),
        suggestion: 'if (get_field(...)) { } で囲むか、三項演算子を使用してください',
      });
    }
  }

  // get_template_part() の引数不足
  const templatePartMatch = line.match(/get_template_part\(\s*['"]([^'"]+)['"]\s*\)/);
  if (templatePartMatch) {
    const path = templatePartMatch[1];
    // template-parts/ 配下を指定していない場合は警告
    if (!path.startsWith('template-parts/')) {
      issues.push({
        file: filePath,
        line: lineNumber,
        type: 'wordpress',
        severity: 'warning',
        message: 'get_template_part() のパスが template-parts/ から始まっていません',
        content: line.trim(),
        suggestion: "get_template_part('template-parts/...')",
      });
    }
  }

  return issues;
}

/**
 * BEM命名規則チェック
 */
function checkBemNaming(
  line: string,
  lineNumber: number,
  filePath: string
): TemplateIssue[] {
  const issues: TemplateIssue[] = [];

  // inc/ ディレクトリ内のファイルはWordPress管理画面用なのでスキップ
  if (filePath.includes('/inc/')) {
    return issues;
  }

  // class属性を抽出
  const classMatches = line.matchAll(/class=["']([^"']+)["']/g);

  for (const match of classMatches) {
    // PHPコードを除去してからクラス名を分割
    // <?php echo ... ?> や <?= ... ?> を除去
    const classAttrValue = match[1]
      .replace(/<\?php[^?]*\?>/g, '')
      .replace(/<\?=[^?]*\?>/g, '')
      .trim();

    const classes = classAttrValue.split(/\s+/).filter(c => c.length > 0);

    for (const className of classes) {
      // PHPコードの残骸や不正なトークンをスキップ
      // 例: <?php, echo, $変数, 演算子, カッコなど
      if (
        className.startsWith('<?') ||
        className.startsWith('$') ||
        className.includes('(') ||
        className.includes(')') ||
        /^(echo|if|else|endif|empty|isset|!|===|!==|&&|\|\|)$/.test(className)
      ) {
        continue;
      }

      // クラス名として有効な文字列のみチェック（英数字・ハイフン・アンダースコアのみ）
      if (!/^[a-zA-Z0-9_-]+$/.test(className)) {
        continue;
      }

      // camelCase検出（BEM違反）
      // 例: .p-page__mainVisual → エラー
      if (/^[a-z]+-[a-zA-Z]+__[a-z]+[A-Z]/.test(className)) {
        issues.push({
          file: filePath,
          line: lineNumber,
          type: 'bem-naming',
          severity: 'error',
          message: `BEMクラス名にcamelCaseが使用されています: ${className}`,
          content: line.trim(),
          suggestion: `kebab-caseに変更してください（例: ${className.replace(/([A-Z])/g, '-$1').toLowerCase()}）`,
        });
      }

      // プレフィックスなし（c-, p-, u-, l- 等がない）
      // ただし、以下は除外:
      // - FLOCSS標準プレフィックス（c-, p-, u-, l-, is-, has-）
      // - JavaScriptフック（js-*）
      // - WordPress標準クラス（wp-*, screen-reader-text, wrap, notice*, widefat, fixed, striped等）
      // - WordPress管理画面クラス（button*, form-table, postbox, meta-box等）
      // - サードパーティライブラリ（splide*, swiper*, slick*）
      // - ユーティリティ（container, row, col）
      if (
        !/^(c-|p-|u-|l-|is-|has-|js-|wp-|screen-reader|sr-only|container|row|col|splide|swiper|slick|wrap|notice|widefat|fixed|striped|button|form-table|postbox|meta-box|dashicons)/.test(className) &&
        className.length > 2
      ) {
        issues.push({
          file: filePath,
          line: lineNumber,
          type: 'bem-naming',
          severity: 'warning',
          message: `FLOCSSプレフィックスがありません: ${className}`,
          content: line.trim(),
          suggestion:
            'c-(component), p-(project), u-(utility), l-(layout) のいずれかを付けてください。JavaScriptフック用は js- プレフィックスを使用してください。',
        });
      }
    }
  }

  return issues;
}

/**
 * アクセシビリティチェック
 */
function checkAccessibility(
  line: string,
  lineNumber: number,
  filePath: string
): TemplateIssue[] {
  const issues: TemplateIssue[] = [];

  // inc/ ディレクトリ内のファイルはWordPress管理画面用なのでスキップ
  if (filePath.includes('/inc/')) {
    return issues;
  }

  // <img> タグに alt属性なし
  if (/<img\s+[^>]*src=/.test(line) && !line.includes('alt=')) {
    issues.push({
      file: filePath,
      line: lineNumber,
      type: 'accessibility',
      severity: 'error',
      message: 'img要素にalt属性がありません',
      content: line.trim(),
      suggestion: 'alt="" または alt="説明文" を追加してください',
    });
  }

  // <a> タグに href="#" のみ（JavaScriptイベント必須）
  if (/<a\s+[^>]*href=["']#["']/.test(line) && !line.includes('onclick')) {
    issues.push({
      file: filePath,
      line: lineNumber,
      type: 'accessibility',
      severity: 'warning',
      message: 'aタグが href="#" のみでJavaScriptイベントがありません',
      content: line.trim(),
      suggestion: '適切なhrefを設定するか、<button>タグを使用してください',
    });
  }

  return issues;
}

/**
 * コード品質チェック
 */
function checkCodeQuality(
  line: string,
  lineNumber: number,
  filePath: string
): TemplateIssue[] {
  const issues: TemplateIssue[] = [];

  // inc/ ディレクトリ内のファイルはWordPress管理画面用なのでスキップ
  if (filePath.includes('/inc/')) {
    return issues;
  }

  // インラインstyle属性
  if (/style=["'][^"']+["']/.test(line)) {
    issues.push({
      file: filePath,
      line: lineNumber,
      type: 'inline-style',
      severity: 'warning',
      message: 'インラインstyle属性が使用されています',
      content: line.trim(),
      suggestion: 'SCSSファイルにスタイルを移動してください',
    });
  }

  // TODO/FIXME/HACKコメント
  if (/TODO|FIXME|HACK/i.test(line)) {
    issues.push({
      file: filePath,
      line: lineNumber,
      type: 'code-quality',
      severity: 'info',
      message: 'TODOコメントが残っています',
      content: line.trim(),
      suggestion: '本番デプロイ前に対応してください',
    });
  }

  // 非推奨タグ
  const deprecatedTags = ['<center', '<font', '<marquee', '<blink'];
  for (const tag of deprecatedTags) {
    if (line.includes(tag)) {
      issues.push({
        file: filePath,
        line: lineNumber,
        type: 'deprecated',
        severity: 'error',
        message: `非推奨タグが使用されています: ${tag}`,
        content: line.trim(),
        suggestion: '最新のHTML5タグとCSSを使用してください',
      });
    }
  }

  return issues;
}

/**
 * ファイルをチェック
 */
function checkFile(filePath: string): TemplateIssue[] {
  const issues: TemplateIssue[] = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  lines.forEach((line, index) => {
    const lineNumber = index + 1;

    // 各チェック実行
    issues.push(...checkSecurity(line, lineNumber, filePath));
    issues.push(...checkWordPressConventions(line, lineNumber, filePath));
    issues.push(...checkBemNaming(line, lineNumber, filePath));
    issues.push(...checkAccessibility(line, lineNumber, filePath));
    issues.push(...checkCodeQuality(line, lineNumber, filePath));
  });

  return issues;
}

/**
 * ディレクトリ内のPHPファイルを再帰的に検索
 */
async function findPhpFiles(baseDir: string): Promise<string[]> {
  const pattern = path.join(baseDir, '**/*.php');
  const files = await glob(pattern, { ignore: ['**/node_modules/**', '**/vendor/**'] });

  // 除外ファイルをフィルタ
  return files.filter((file) => {
    const basename = path.basename(file);
    return !EXCLUDE_FILES.includes(basename);
  });
}

/**
 * 結果をコンソールに出力
 */
function printResults(issues: TemplateIssue[]) {
  if (issues.length === 0) {
    console.log('✅ 問題は見つかりませんでした。\n');
    return;
  }

  console.log(`\n❌ ${issues.length}件の問題が見つかりました:\n`);

  // 重要度ごとにカウント
  const errorCount = issues.filter((i) => i.severity === 'error').length;
  const warningCount = issues.filter((i) => i.severity === 'warning').length;
  const infoCount = issues.filter((i) => i.severity === 'info').length;

  console.log(`  🔴 エラー: ${errorCount}件`);
  console.log(`  🟡 警告: ${warningCount}件`);
  console.log(`  🔵 情報: ${infoCount}件\n`);

  // タイプごとにグループ化
  const grouped = issues.reduce((acc, issue) => {
    if (!acc[issue.type]) {
      acc[issue.type] = [];
    }
    acc[issue.type].push(issue);
    return acc;
  }, {} as Record<string, TemplateIssue[]>);

  // タイプごとに出力
  const typeLabels: Record<string, string> = {
    security: '🔒 セキュリティ',
    wordpress: '📦 WordPress規約',
    'bem-naming': '🎨 BEM命名規則',
    accessibility: '♿ アクセシビリティ',
    'code-quality': '✨ コード品質',
    'inline-style': '💅 インラインスタイル',
    deprecated: '⚠️ 非推奨タグ',
  };

  Object.entries(grouped).forEach(([type, typeIssues]) => {
    console.log(`\n${typeLabels[type]} (${typeIssues.length}件):`);
    console.log('─'.repeat(80));

    typeIssues.forEach((issue) => {
      const relativePath = path.relative(process.cwd(), issue.file);
      const severityIcon =
        issue.severity === 'error' ? '🔴' : issue.severity === 'warning' ? '🟡' : '🔵';

      console.log(`\n  ${severityIcon} ${relativePath}:${issue.line}`);
      console.log(`  💬 ${issue.message}`);
      console.log(`  📝 ${issue.content}`);
      if (issue.suggestion) {
        console.log(`  💡 ${issue.suggestion}`);
      }
    });
  });

  console.log('\n' + '─'.repeat(80));
  console.log(`\n合計: ${issues.length}件の問題\n`);
}

/**
 * JSONレポート出力
 */
function saveJsonReport(issues: TemplateIssue[], outputPath: string) {
  const report = {
    timestamp: new Date().toISOString(),
    totalIssues: issues.length,
    summary: {
      error: issues.filter((i) => i.severity === 'error').length,
      warning: issues.filter((i) => i.severity === 'warning').length,
      info: issues.filter((i) => i.severity === 'info').length,
    },
    byType: {
      security: issues.filter((i) => i.type === 'security').length,
      wordpress: issues.filter((i) => i.type === 'wordpress').length,
      'bem-naming': issues.filter((i) => i.type === 'bem-naming').length,
      accessibility: issues.filter((i) => i.type === 'accessibility').length,
      'code-quality': issues.filter((i) => i.type === 'code-quality').length,
      'inline-style': issues.filter((i) => i.type === 'inline-style').length,
      deprecated: issues.filter((i) => i.type === 'deprecated').length,
    },
    issues,
  };

  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
  console.log(`📊 レポートを保存しました: ${outputPath}\n`);
}

/**
 * HTML Validateを実行
 */
async function runHtmlValidate(): Promise<boolean> {
  console.log('\n🔍 HTML構造バリデーション (html-validate) を実行中...\n');

  try {
    execSync(`npx html-validate "themes/${THEME_NAME}/**/*.php"`, {
      stdio: 'inherit',
      encoding: 'utf-8'
    });
    console.log('✅ HTML構造バリデーション: 問題なし\n');
    return true;
  } catch (error) {
    console.log('❌ HTML構造バリデーション: 問題が見つかりました\n');
    return false;
  }
}

/**
 * HTMLセマンティックチェックを実行
 */
async function runSemanticCheck(): Promise<boolean> {
  console.log('🔍 セマンティック構造チェック (html-semantic) を実行中...\n');

  try {
    execSync('tsx scripts/check/html-semantic.ts', {
      stdio: 'inherit',
      encoding: 'utf-8'
    });
    console.log('✅ セマンティック構造チェック: 問題なし\n');
    return true;
  } catch (error) {
    console.log('❌ セマンティック構造チェック: 問題が見つかりました\n');
    return false;
  }
}

/**
 * メイン処理
 */
async function main() {
  console.log('🔍 テンプレート品質チェックを開始します...\n');
  console.log('='.repeat(80));

  let hasErrors = false;

  // 1. 基本的なPHPテンプレートチェック
  console.log('\n📋 Step 1: PHP テンプレート品質チェック\n');
  const allIssues: TemplateIssue[] = [];

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
  const reportPath = path.join(process.cwd(), 'reports/template-quality-report.json');
  saveJsonReport(allIssues, reportPath);

  if (allIssues.some((i) => i.severity === 'error')) {
    hasErrors = true;
  }

  // 2. HTML構造バリデーション
  console.log('\n='.repeat(80));
  console.log('\n📋 Step 2: HTML構造バリデーション\n');
  const htmlValidatePassed = await runHtmlValidate();
  if (!htmlValidatePassed) {
    hasErrors = true;
  }

  // 3. セマンティック構造チェック
  console.log('\n='.repeat(80));
  console.log('\n📋 Step 3: セマンティック構造チェック\n');
  const semanticCheckPassed = await runSemanticCheck();
  if (!semanticCheckPassed) {
    hasErrors = true;
  }

  // 最終結果
  console.log('\n' + '='.repeat(80));
  console.log('\n📊 テンプレート品質チェック完了\n');
  console.log(`基本チェック: ${allIssues.length === 0 ? '✅ PASS' : `❌ ${allIssues.length}件の問題`}`);
  console.log(`HTML構造: ${htmlValidatePassed ? '✅ PASS' : '❌ FAIL'}`);
  console.log(`セマンティック: ${semanticCheckPassed ? '✅ PASS' : '❌ FAIL'}`);
  console.log('\n' + '='.repeat(80) + '\n');

  // エラーがあった場合は終了コード1
  if (hasErrors) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('エラーが発生しました:', error);
  process.exit(1);
});
