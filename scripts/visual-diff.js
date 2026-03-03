#!/usr/bin/env node

/**
 * Visual Diff Validator
 *
 * Figma-WordPress間のピクセル差分を自動検出・可視化するスクリプト
 *
 * Usage:
 *   node scripts/visual-diff.js <figma-image> <wordpress-image> [options]
 *
 * Options:
 *   --output, -o     差分画像の出力パス（デフォルト: 自動生成）
 *   --threshold, -t  色差許容値（0-1、デフォルト: 0.2）
 *   --ratio, -r      許容する差分ピクセル比率（0-1、デフォルト: 0.05）
 *   --preset, -p     プリセット名（strict, default, lenient）
 *   --json           JSON形式で結果を出力
 *   --quiet, -q      最小限の出力
 *
 * Examples:
 *   node scripts/visual-diff.js figma.png wordpress.png
 *   node scripts/visual-diff.js figma.png wordpress.png --preset strict
 *   node scripts/visual-diff.js figma.png wordpress.png -t 0.1 -r 0.01
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import pixelmatch from 'pixelmatch';
import { PNG } from 'pngjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 設定ファイル読み込み
const configPath = path.join(__dirname, 'visual-diff-config.json');
const defaultConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));

/**
 * コマンドライン引数をパース
 */
function parseArgs(args) {
  const options = {
    figmaImage: null,
    wordpressImage: null,
    output: null,
    threshold: defaultConfig.threshold,
    maxDiffPixelRatio: defaultConfig.maxDiffPixelRatio,
    preset: null,
    json: false,
    quiet: false,
  };

  let i = 0;
  while (i < args.length) {
    const arg = args[i];

    if (arg === '--output' || arg === '-o') {
      options.output = args[++i];
    } else if (arg === '--threshold' || arg === '-t') {
      options.threshold = parseFloat(args[++i]);
    } else if (arg === '--ratio' || arg === '-r') {
      options.maxDiffPixelRatio = parseFloat(args[++i]);
    } else if (arg === '--preset' || arg === '-p') {
      options.preset = args[++i];
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--quiet' || arg === '-q') {
      options.quiet = true;
    } else if (!arg.startsWith('-')) {
      if (!options.figmaImage) {
        options.figmaImage = arg;
      } else if (!options.wordpressImage) {
        options.wordpressImage = arg;
      }
    }
    i++;
  }

  // プリセット適用
  if (options.preset && defaultConfig.presets[options.preset]) {
    const preset = defaultConfig.presets[options.preset];
    options.threshold = preset.threshold;
    options.maxDiffPixelRatio = preset.maxDiffPixelRatio;
  }

  return options;
}

/**
 * PNG画像を読み込み
 */
function loadImage(imagePath) {
  return new Promise((resolve, reject) => {
    const absolutePath = path.resolve(imagePath);

    if (!fs.existsSync(absolutePath)) {
      reject(new Error(`Image not found: ${absolutePath}`));
      return;
    }

    fs.createReadStream(absolutePath)
      .pipe(new PNG())
      .on('parsed', function () {
        resolve(this);
      })
      .on('error', reject);
  });
}

/**
 * 画像サイズを揃える（小さい方に合わせる）
 */
function normalizeImageSizes(img1, img2) {
  const width = Math.min(img1.width, img2.width);
  const height = Math.min(img1.height, img2.height);

  const warnings = [];

  if (img1.width !== img2.width || img1.height !== img2.height) {
    warnings.push({
      type: 'size_mismatch',
      figma: { width: img1.width, height: img1.height },
      wordpress: { width: img2.width, height: img2.height },
      normalized: { width, height },
    });
  }

  return { width, height, warnings };
}

/**
 * 差分検出を実行
 */
async function runDiff(options) {
  const startTime = Date.now();

  // 画像読み込み
  const [figmaImg, wordpressImg] = await Promise.all([
    loadImage(options.figmaImage),
    loadImage(options.wordpressImage),
  ]);

  // サイズ正規化
  const { width, height, warnings } = normalizeImageSizes(figmaImg, wordpressImg);

  // 差分画像用バッファ
  const diff = new PNG({ width, height });

  // pixelmatch実行
  const diffPixels = pixelmatch(
    figmaImg.data,
    wordpressImg.data,
    diff.data,
    width,
    height,
    {
      threshold: options.threshold,
      includeAA: defaultConfig.antialiasing,
      alpha: defaultConfig.alpha,
      diffColor: defaultConfig.diffColor,
    }
  );

  // 統計計算
  const totalPixels = width * height;
  const diffRatio = diffPixels / totalPixels;
  const passed = diffRatio <= options.maxDiffPixelRatio;

  // 結果オブジェクト
  const result = {
    passed,
    comparison: {
      figmaImage: options.figmaImage,
      wordpressImage: options.wordpressImage,
      dimensions: { width, height },
    },
    statistics: {
      totalPixels,
      diffPixels,
      diffRatio: parseFloat(diffRatio.toFixed(6)),
      diffPercentage: parseFloat((diffRatio * 100).toFixed(4)),
    },
    thresholds: {
      threshold: options.threshold,
      maxDiffPixelRatio: options.maxDiffPixelRatio,
      preset: options.preset || 'custom',
    },
    warnings,
    timing: {
      durationMs: Date.now() - startTime,
    },
  };

  // 差分画像保存
  if (diffPixels > 0) {
    const outputPath =
      options.output ||
      path.join(
        defaultConfig.outputDir,
        `diff_${Date.now()}.png`
      );

    // 出力ディレクトリ作成
    const outputDir = path.dirname(outputPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // PNG書き出し
    await new Promise((resolve, reject) => {
      diff
        .pack()
        .pipe(fs.createWriteStream(outputPath))
        .on('finish', resolve)
        .on('error', reject);
    });

    result.diffImage = outputPath;
  }

  return result;
}

/**
 * 結果を出力
 */
function outputResult(result, options) {
  if (options.json) {
    console.log(JSON.stringify(result, null, 2));
    return;
  }

  if (options.quiet) {
    console.log(result.passed ? 'PASS' : 'FAIL');
    return;
  }

  const statusIcon = result.passed ? '✅' : '❌';
  const statusText = result.passed ? 'PASS' : 'FAIL';

  console.log('\n' + '='.repeat(60));
  console.log(`${statusIcon} Visual Diff Result: ${statusText}`);
  console.log('='.repeat(60));

  console.log('\n📊 Statistics:');
  console.log(`   Total Pixels:    ${result.statistics.totalPixels.toLocaleString()}`);
  console.log(`   Diff Pixels:     ${result.statistics.diffPixels.toLocaleString()}`);
  console.log(`   Diff Percentage: ${result.statistics.diffPercentage}%`);

  console.log('\n⚙️  Thresholds:');
  console.log(`   Preset:          ${result.thresholds.preset}`);
  console.log(`   Threshold:       ${result.thresholds.threshold}`);
  console.log(`   Max Diff Ratio:  ${result.thresholds.maxDiffPixelRatio} (${(result.thresholds.maxDiffPixelRatio * 100).toFixed(2)}%)`);

  if (result.warnings.length > 0) {
    console.log('\n⚠️  Warnings:');
    result.warnings.forEach((warning) => {
      if (warning.type === 'size_mismatch') {
        console.log(`   Image size mismatch:`);
        console.log(`     Figma:     ${warning.figma.width}x${warning.figma.height}`);
        console.log(`     WordPress: ${warning.wordpress.width}x${warning.wordpress.height}`);
        console.log(`     Compared:  ${warning.normalized.width}x${warning.normalized.height}`);
      }
    });
  }

  if (result.diffImage) {
    console.log(`\n📁 Diff Image: ${result.diffImage}`);
  }

  console.log(`\n⏱️  Duration: ${result.timing.durationMs}ms`);
  console.log('='.repeat(60) + '\n');
}

/**
 * ヘルプ表示
 */
function showHelp() {
  console.log(`
Visual Diff Validator - Figma-WordPress間のピクセル差分検出ツール

Usage:
  node scripts/visual-diff.js <figma-image> <wordpress-image> [options]

Options:
  --output, -o     差分画像の出力パス（デフォルト: 自動生成）
  --threshold, -t  色差許容値（0-1、デフォルト: 0.2）
  --ratio, -r      許容する差分ピクセル比率（0-1、デフォルト: 0.05）
  --preset, -p     プリセット名（strict, default, lenient）
  --json           JSON形式で結果を出力
  --quiet, -q      最小限の出力
  --help, -h       このヘルプを表示

Presets:
  strict   - threshold: 0.1, maxDiffPixelRatio: 0.01（厳格）
  default  - threshold: 0.2, maxDiffPixelRatio: 0.05（標準）
  lenient  - threshold: 0.3, maxDiffPixelRatio: 0.10（緩和）

Examples:
  node scripts/visual-diff.js figma.png wordpress.png
  node scripts/visual-diff.js figma.png wordpress.png --preset strict
  node scripts/visual-diff.js figma.png wordpress.png -t 0.1 -r 0.01 --json
`);
}

/**
 * メイン処理
 */
async function main() {
  const args = process.argv.slice(2);

  // ヘルプ表示
  if (args.includes('--help') || args.includes('-h')) {
    showHelp();
    process.exit(0);
  }

  const options = parseArgs(args);

  // 引数チェック
  if (!options.figmaImage || !options.wordpressImage) {
    console.error('Error: Both figma-image and wordpress-image are required.');
    console.error('Usage: node scripts/visual-diff.js <figma-image> <wordpress-image>');
    process.exit(1);
  }

  try {
    const result = await runDiff(options);
    outputResult(result, options);
    process.exit(result.passed ? 0 : 1);
  } catch (error) {
    if (options.json) {
      console.log(JSON.stringify({ error: error.message }, null, 2));
    } else {
      console.error(`Error: ${error.message}`);
    }
    process.exit(1);
  }
}

// エクスポート（モジュールとして使用する場合）
export { runDiff, loadImage, parseArgs };

// CLI実行
main();
