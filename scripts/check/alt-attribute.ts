#!/usr/bin/env node
/**
 * alt属性詳細チェックスクリプト
 *
 * PHPテンプレートファイル内の画像を解析し、
 * alt属性の問題を検出します。
 *
 * 検出項目:
 * - alt属性が完全に欠落
 * - alt=""（空文字）で装飾画像でないもの
 * - alt="画像" などの無意味な値
 * - ファイル名がそのまま使われている（image.jpg等）
 *
 * Usage:
 *   npm run check:alt
 */

import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

// チェック対象のディレクトリ
const TARGET_DIRS = [
  'themes/lpc-group-wp/pages',
  'themes/lpc-group-wp/template-parts',
  'themes/lpc-group-wp',
];

// 除外ファイル
const EXCLUDE_FILES = ['functions.php', 'style.css', 'screenshot.png', 'favicon.ico'];

// 無意味なalt値のパターン
const MEANINGLESS_ALT_PATTERNS = [
  /^(画像|イメージ|image|img|photo|picture|pic)$/i,
  /\.(jpg|jpeg|png|gif|webp|svg)$/i, // ファイル名がそのまま
  /^(no|none|null|undefined|n\/a)$/i,
];

interface AltIssue {
  file: string;
  line: number;
  type: 'missing' | 'empty' | 'meaningless' | 'filename';
  severity: 'error' | 'warning' | 'info';
  message: string;
  context: string; // 前後3行を含むコンテキスト
  imgTag: string;
  altValue?: string;
  suggestion?: string;
}

/**
 * ファイル内容を複数行対応で解析
 */
function extractImages(content: string, filePath: string): AltIssue[] {
  const issues: AltIssue[] = [];
  const lines = content.split('\n');

  // 複数行にまたがるimgタグを結合
  let i = 0;
  while (i < lines.length) {
    const lineNumber = i + 1;
    let currentLine = lines[i];

    // <img で始まる行を検出
    if (/<img\s/.test(currentLine)) {
      // 閉じタグ（> または />）まで結合（最大20行まで）
      let fullTag = currentLine;
      let endLine = i;
      const maxLines = 20;
      let foundClosing = false;

      // 現在行に閉じタグがあるかチェック
      if (/>/.test(currentLine)) {
        foundClosing = true;
      } else {
        // 次の行から閉じタグを探す
        while (endLine < lines.length - 1 && endLine < i + maxLines && !foundClosing) {
          endLine++;
          const nextLine = lines[endLine].trim();
          fullTag += ' ' + nextLine;

          if (/>/.test(nextLine)) {
            foundClosing = true;
          }
        }
      }

      // imgタグ全体を抽出
      // PHPコードの?>を考慮して、単純な>ではなく、属性の終わりを検出
      // 最後の閉じタグ（> または />）までを抽出
      const imgMatch = fullTag.match(/<img\s[\s\S]*?(?:\/>|>)/);
      if (imgMatch) {
        const imgTag = imgMatch[0];

        // デバッグ（page-recruit-entry 58行目のみ）
        if (filePath.includes('page-recruit-entry') && lineNumber === 58) {
          console.log('[DEBUG] fullTag:', fullTag);
          console.log('[DEBUG] imgTag:', imgTag);
          console.log('[DEBUG] has alt?:', /alt=/.test(imgTag));
        }

        const issue = checkAltAttribute(imgTag, filePath, lineNumber, lines, i);
        if (issue) {
          issues.push(issue);
        }
      }

      i = endLine + 1;
    } else {
      i++;
    }
  }

  return issues;
}

/**
 * alt属性をチェック
 */
function checkAltAttribute(
  imgTag: string,
  filePath: string,
  lineNumber: number,
  allLines: string[],
  lineIndex: number
): AltIssue | null {
  // コンテキスト（前後3行）を取得
  const contextStart = Math.max(0, lineIndex - 3);
  const contextEnd = Math.min(allLines.length - 1, lineIndex + 3);
  const context = allLines.slice(contextStart, contextEnd + 1).join('\n');

  // alt属性を抽出
  const altMatch = imgTag.match(/alt=["']([^"']*)["']/);

  // 1. alt属性が完全に欠落
  if (!altMatch) {
    // 装飾画像かどうか判定（role="presentation" や aria-hidden="true"）
    const isDecorative =
      /role=["']presentation["']/.test(imgTag) || /aria-hidden=["']true["']/.test(imgTag);

    if (!isDecorative) {
      return {
        file: filePath,
        line: lineNumber,
        type: 'missing',
        severity: 'error',
        message: 'alt属性が完全に欠落しています',
        context,
        imgTag: imgTag.trim(),
        suggestion:
          '装飾画像の場合は alt="" を追加。意味のある画像の場合は適切な説明を追加してください。',
      };
    }
    return null;
  }

  const altValue = altMatch[1];

  // 2. alt=""（空文字）のチェック
  if (altValue === '') {
    // 空文字は装飾画像として許容されるが、本当に装飾画像かを確認
    // src属性を取得して、意味がありそうな画像名かチェック
    const srcMatch = imgTag.match(/src=["']([^"']*)["']/);
    if (srcMatch) {
      const src = srcMatch[1];
      // logo, hero, thumbnail など意味がありそうな名前
      const meaningfulPatterns = [
        /logo/i,
        /hero/i,
        /thumbnail/i,
        /main/i,
        /feature/i,
        /product/i,
        /avatar/i,
        /profile/i,
      ];

      if (meaningfulPatterns.some((pattern) => pattern.test(src))) {
        return {
          file: filePath,
          line: lineNumber,
          type: 'empty',
          severity: 'warning',
          message: 'alt属性が空ですが、意味のある画像の可能性があります',
          context,
          imgTag: imgTag.trim(),
          altValue,
          suggestion: '画像の内容を説明するalt属性を追加してください。',
        };
      }
    }

    return null; // 装飾画像として許容
  }

  // 3. PHP変数展開を含む場合はスキップ（動的生成）
  if (/\$\w+|<\?php|\?>|esc_attr|esc_html/.test(altValue)) {
    return null;
  }

  // 4. 無意味なalt値
  for (const pattern of MEANINGLESS_ALT_PATTERNS) {
    if (pattern.test(altValue)) {
      return {
        file: filePath,
        line: lineNumber,
        type: 'meaningless',
        severity: 'warning',
        message: `無意味なalt値が使用されています: "${altValue}"`,
        context,
        imgTag: imgTag.trim(),
        altValue,
        suggestion: '画像の具体的な内容を説明する文言に変更してください。',
      };
    }
  }

  // 5. 短すぎるalt（2文字以下）
  if (altValue.length > 0 && altValue.length <= 2) {
    return {
      file: filePath,
      line: lineNumber,
      type: 'meaningless',
      severity: 'info',
      message: `alt属性が短すぎます: "${altValue}"`,
      context,
      imgTag: imgTag.trim(),
      altValue,
      suggestion: 'より具体的な説明を追加してください。',
    };
  }

  return null;
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
function printResults(issues: AltIssue[]) {
  if (issues.length === 0) {
    console.log('✅ alt属性の問題は見つかりませんでした。\n');
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
  }, {} as Record<string, AltIssue[]>);

  const typeLabels: Record<string, string> = {
    missing: '❌ alt属性欠落',
    empty: '⚠️ alt属性が空',
    meaningless: '🤔 無意味なalt値',
    filename: '📁 ファイル名がそのまま',
  };

  // タイプごとに出力
  Object.entries(grouped).forEach(([type, typeIssues]) => {
    console.log(`\n${typeLabels[type]} (${typeIssues.length}件):`);
    console.log('─'.repeat(80));

    typeIssues.forEach((issue) => {
      const relativePath = path.relative(process.cwd(), issue.file);
      const severityIcon =
        issue.severity === 'error' ? '🔴' : issue.severity === 'warning' ? '🟡' : '🔵';

      console.log(`\n  ${severityIcon} ${relativePath}:${issue.line}`);
      console.log(`  💬 ${issue.message}`);
      if (issue.altValue !== undefined) {
        console.log(`  📝 現在の値: "${issue.altValue}"`);
      }
      console.log(`  📄 コンテキスト:`);
      // コンテキストをインデント付きで表示
      issue.context.split('\n').forEach((line) => {
        console.log(`     ${line}`);
      });
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
function saveJsonReport(issues: AltIssue[], outputPath: string) {
  const report = {
    timestamp: new Date().toISOString(),
    totalIssues: issues.length,
    summary: {
      error: issues.filter((i) => i.severity === 'error').length,
      warning: issues.filter((i) => i.severity === 'warning').length,
      info: issues.filter((i) => i.severity === 'info').length,
    },
    byType: {
      missing: issues.filter((i) => i.type === 'missing').length,
      empty: issues.filter((i) => i.type === 'empty').length,
      meaningless: issues.filter((i) => i.type === 'meaningless').length,
      filename: issues.filter((i) => i.type === 'filename').length,
    },
    issues,
  };

  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
  console.log(`📊 レポートを保存しました: ${outputPath}\n`);
}

/**
 * メイン処理
 */
async function main() {
  console.log('🔍 alt属性チェックを開始します...\n');

  const allIssues: AltIssue[] = [];

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
      const content = fs.readFileSync(file, 'utf-8');
      const issues = extractImages(content, file);
      allIssues.push(...issues);
    }
  }

  console.log('\n' + '='.repeat(80));
  printResults(allIssues);

  // JSONレポート出力
  const reportPath = path.join(process.cwd(), 'reports/alt-attribute-report.json');
  saveJsonReport(allIssues, reportPath);

  // エラーがあった場合は終了コード1
  const hasErrors = allIssues.some((i) => i.severity === 'error');
  if (hasErrors) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('エラーが発生しました:', error);
  process.exit(1);
});
