import sharp from "sharp";
import path from "path";
import fs from "fs/promises";
import { fileURLToPath } from "url";
import { optimize } from "svgo";
import { detectThemeName, getThemePath } from "../lib/detect-theme.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// テーマ名を自動検出
const THEME_NAME = detectThemeName();
const THEME_PATH = getThemePath();

console.log(`📦 Theme detected: ${THEME_NAME}`);

// 設定
const CONFIG = {
  inputDir: path.resolve(__dirname, "../../src/images"),
  outputDir: path.resolve(THEME_PATH, "assets/images"),
  astroOutputDir: path.resolve(__dirname, "../../astro/public/assets/images"),
  metaOutputPath: path.resolve(THEME_PATH, "inc/data/images-meta.php"),
  quality: {
    jpeg: 85,
    webp: 85,
    png: 90,
  },
};

// グローバルにメタデータオブジェクトを保持
const imagesMeta = {};

/**
 * WordPress出力ファイルをAstro出力先にもコピー
 */
async function copyToAstro(wpFilePath: string): Promise<void> {
  const relativePath = path.relative(CONFIG.outputDir, wpFilePath);
  const astroFilePath = path.join(CONFIG.astroOutputDir, relativePath);
  await fs.mkdir(path.dirname(astroFilePath), { recursive: true });
  await fs.cp(wpFilePath, astroFilePath);
}

/**
 * ディレクトリ内のすべての画像ファイルを再帰的に取得
 */
async function getImageFiles(dir, fileList = []) {
  const files = await fs.readdir(dir);

  for (const file of files) {
    const filePath = path.join(dir, file);
    const stat = await fs.stat(filePath);

    if (stat.isDirectory()) {
      await getImageFiles(filePath, fileList);
    } else if (/\.(jpe?g|png|svg)$/i.test(file)) {
      // すべての画像を含める（_sp画像も含む）
      fileList.push(filePath);
    }
  }

  return fileList;
}

/**
 * SVG画像を最適化
 */
async function optimizeSvg(inputPath) {
  const relativePath = path.relative(CONFIG.inputDir, inputPath);
  const parsedPath = path.parse(relativePath);
  const outputBasePath = path.join(CONFIG.outputDir, parsedPath.dir);

  // 出力ディレクトリを作成
  await fs.mkdir(outputBasePath, { recursive: true });

  console.log(`\n📸 Processing SVG: ${relativePath}`);

  try {
    // SVGファイルを読み込み
    const svgContent = await fs.readFile(inputPath, "utf-8");

    // SVGOで最適化
    const result = optimize(svgContent, {
      plugins: [
        "preset-default",
        // viewBox属性を保持（レスポンシブ対応のため）
        {
          name: "removeViewBox",
          active: false,
        },
        // xmlns属性はデフォルトで保持される（removeXMLNSプラグインを追加しない）
      ],
    });

    // 最適化されたSVGを出力
    const outputPath = path.join(outputBasePath, `${parsedPath.name}.svg`);
    await fs.writeFile(outputPath, result.data);

    // Astro側にもコピー
    await copyToAstro(outputPath);

    // ファイルサイズを取得
    const originalStats = await fs.stat(inputPath);
    const optimizedStats = await fs.stat(outputPath);
    const reduction = ((1 - optimizedStats.size / originalStats.size) * 100).toFixed(1);

    console.log(`   ✅ Optimized: ${parsedPath.name}.svg`);
    console.log(`   📊 Size: ${originalStats.size}B → ${optimizedStats.size}B (-${reduction}%)`);

    // viewBox属性から幅と高さを取得してメタデータに保存
    const viewBoxMatch = result.data.match(/viewBox=["']([^"']+)["']/);
    if (viewBoxMatch) {
      const viewBoxValues = viewBoxMatch[1].split(/\s+/);
      if (viewBoxValues.length === 4) {
        const width = Math.round(parseFloat(viewBoxValues[2]));
        const height = Math.round(parseFloat(viewBoxValues[3]));

        // メタデータを保存（パスは/区切りで統一、拡張子を除去）
        const metaKey = relativePath.replace(/\\/g, "/").replace(/\.svg$/i, "");
        imagesMeta[metaKey] = {
          width,
          height,
        };
        console.log(`   📐 Dimensions: ${width}x${height}px (from viewBox)`);
      }
    }
  } catch (error) {
    console.error(`   ❌ Error processing SVG:`, error.message);
  }
}

/**
 * 通常画像と@2x画像を生成（ダウンスケールアプローチ）
 *
 * 前提: Figmaから2倍サイズで書き出した画像を使用
 * - 元画像 = 2x画像としてそのまま使用（高品質）
 * - 1x画像 = 元画像をダウンスケール生成（Lanczosアルゴリズムで高品質）
 * - SP画像のみ1.15倍補正を適用（375px基準の粗さ対策）
 */
async function generateRetinaImages(inputPath: string): Promise<void> {
  const relativePath = path.relative(CONFIG.inputDir, inputPath);
  const parsedPath = path.parse(relativePath);
  const outputBasePath = path.join(CONFIG.outputDir, parsedPath.dir);

  // 出力ディレクトリを作成
  await fs.mkdir(outputBasePath, { recursive: true });

  // 元画像の情報を取得（元画像 = 2xサイズ）
  const metadata = await sharp(inputPath).metadata();
  const original2xWidth = metadata.width;
  const original2xHeight = metadata.height;

  console.log(`\n📸 Processing: ${relativePath}`);
  console.log(`   Original size (2x): ${original2xWidth}x${original2xHeight}px`);

  const baseName = parsedPath.name;

  // SP画像判定: ファイル名に_spを含むか
  const isSPImage = baseName.includes("_sp");
  const SCALE_FACTOR = isSPImage ? 1.15 : 1.0;

  try {
    // 1x画像サイズ計算（元画像の1/2をベースに、SP画像は1.15倍補正）
    // PC: original2xWidth / 2
    // SP: (original2xWidth / 2) * 1.15
    const size1x = Math.round((original2xWidth / 2) * SCALE_FACTOR);
    const height1x = Math.round((original2xHeight / 2) * SCALE_FACTOR);

    // WebP 1x画像（ダウンスケール生成）
    const outputWebp1xPath = path.join(outputBasePath, `${baseName}.webp`);
    await sharp(inputPath)
      .resize(size1x, null, { kernel: sharp.kernel.lanczos3 }) // Lanczos3で高品質ダウンスケール
      .webp({ quality: CONFIG.quality.webp })
      .toFile(outputWebp1xPath);

    const scaleLabel = isSPImage ? " [SP: 1.15x downscale]" : " [PC: 0.5x downscale]";
    console.log(`   ✅ Generated: ${baseName}.webp (${size1x}x${height1x}px)${scaleLabel}`);

    // Astro側にもコピー
    await copyToAstro(outputWebp1xPath);

    // 2x画像サイズ計算（SP画像のみ1.15倍補正）
    // PC: original2xWidth（元画像そのまま）
    // SP: original2xWidth * 1.15
    const size2x = Math.round(original2xWidth * SCALE_FACTOR);
    const height2x = Math.round(original2xHeight * SCALE_FACTOR);

    // WebP 2x画像
    const outputWebp2xPath = path.join(outputBasePath, `${baseName}@2x.webp`);

    if (SCALE_FACTOR === 1.0) {
      // PC画像: 元画像をそのまま使用（リサイズなし、最高品質）
      await sharp(inputPath).webp({ quality: CONFIG.quality.webp }).toFile(outputWebp2xPath);
      console.log(
        `   ✅ Generated: ${baseName}@2x.webp (${size2x}x${height2x}px) [PC: original, no resize]`
      );
    } else {
      // SP画像: 1.15倍にリサイズ
      await sharp(inputPath)
        .resize(size2x, null, { kernel: sharp.kernel.lanczos3 })
        .webp({ quality: CONFIG.quality.webp })
        .toFile(outputWebp2xPath);
      console.log(
        `   ✅ Generated: ${baseName}@2x.webp (${size2x}x${height2x}px) [SP: 1.15x resize]`
      );
    }

    // Astro側にもコピー
    await copyToAstro(outputWebp2xPath);

    // WebP 3x画像（SP画像のみ: 元画像の1.5倍 * 1.15倍補正）
    if (isSPImage) {
      const outputWebp3xPath = path.join(outputBasePath, `${baseName}@3x.webp`);
      const size3x = Math.round((original2xWidth * 1.5) * SCALE_FACTOR);
      const height3x = Math.round((original2xHeight * 1.5) * SCALE_FACTOR);

      await sharp(inputPath)
        .resize(size3x, null, { kernel: sharp.kernel.lanczos3 })
        .webp({ quality: CONFIG.quality.webp })
        .toFile(outputWebp3xPath);
      console.log(
        `   ✅ Generated: ${baseName}@3x.webp (${size3x}x${height3x}px) [SP: 1.5x * 1.15x]`
      );

      // Astro側にもコピー
      await copyToAstro(outputWebp3xPath);
    }

    // メタデータを保存（1xサイズを記録、パスは/区切りで統一、拡張子を除去）
    const metaKey = relativePath.replace(/\\/g, "/").replace(/\.(jpe?g|png)$/i, "");
    (imagesMeta as Record<string, { width: number; height: number }>)[metaKey] = {
      width: size1x,
      height: height1x,
    };
  } catch (error) {
    console.error(`   ❌ Error processing:`, error instanceof Error ? error.message : String(error));
  }
}

/**
 * メイン処理
 */
async function main(): Promise<void> {
  // コマンドライン引数から対象フォルダを取得（相対パスまたはフォルダ名）
  // npm run経由の場合、process.argv[2]以降が実際の引数
  const args = process.argv.slice(2).filter((arg: string) => arg !== "--");
  const targetFolder = args[0];

  let targetInputDir = CONFIG.inputDir;

  if (targetFolder) {
    // 絶対パスかどうか判定
    if (path.isAbsolute(targetFolder)) {
      targetInputDir = targetFolder;
    } else {
      // 相対パスまたはフォルダ名として扱う
      targetInputDir = path.resolve(CONFIG.inputDir, targetFolder);
    }
  }

  console.log("🚀 Starting image optimization...\n");
  console.log(`Input:  ${targetInputDir}`);
  console.log(`Output: ${CONFIG.outputDir}`);
  console.log(`Astro:  ${CONFIG.astroOutputDir}\n`);

  try {
    // 入力ディレクトリの存在確認
    try {
      await fs.access(targetInputDir);
    } catch {
      console.error(`❌ Input directory not found: ${targetInputDir}`);
      if (targetFolder) {
        console.log(`\n💡 Specified folder "${targetFolder}" does not exist in src/images/`);
      } else {
        console.log("\n💡 Create src/images directory and add images.");
      }
      process.exit(1);
    }

    // 出力ディレクトリをクリーンアップ（既存の画像を削除）
    console.log("🧹 Cleaning output directories...");
    try {
      await fs.rm(CONFIG.outputDir, { recursive: true, force: true });
      await fs.rm(CONFIG.astroOutputDir, { recursive: true, force: true });
      console.log("   ✅ Old images removed\n");
    } catch (error) {
      // エラーは無視（ディレクトリが存在しない場合など）
    }

    // 出力ディレクトリを作成
    await fs.mkdir(CONFIG.outputDir, { recursive: true });
    await fs.mkdir(CONFIG.astroOutputDir, { recursive: true });

    // すべての画像ファイルを取得
    const imageFiles = await getImageFiles(targetInputDir);

    if (imageFiles.length === 0) {
      console.log("⚠️  No images found in src/images/");
      console.log("💡 Add .jpg or .png files to src/images/ and run again.");
      return;
    }

    console.log(`Found ${imageFiles.length} images to process.\n`);

    // 各画像を処理
    for (const imagePath of imageFiles) {
      const ext = path.extname(imagePath).toLowerCase();
      if (ext === ".svg") {
        await optimizeSvg(imagePath);
      } else {
        await generateRetinaImages(imagePath);
      }
    }

    // メタデータをPHP配列形式に変換
    const convertToPhpArray = (obj: Record<string, unknown>, indent = 2): string => {
      const spaces = " ".repeat(indent);
      const entries = Object.entries(obj).map(([key, value]) => {
        if (typeof value === "object" && value !== null) {
          const innerSpaces = " ".repeat(indent + 2);
          const innerEntries = Object.entries(value)
            .map(([k, v]) => `${innerSpaces}"${k}" => ${typeof v === "number" ? v : `"${v}"`}`)
            .join(",\n");
          return `${spaces}"${key}" => [\n${innerEntries}\n${spaces}]`;
        }
        return `${spaces}"${key}" => ${typeof value === "number" ? value : `"${value}"`}`;
      });
      return `[\n${entries.join(",\n")}\n]`;
    };

    // メタデータをPHPファイルとして出力
    const phpContent = `<?php
/**
 * 画像メタデータ
 * Auto-generated by generate-retina-images.js
 * DO NOT EDIT MANUALLY
 * Generated at: ${new Date().toISOString()}
 */
return ${convertToPhpArray(imagesMeta)};
`;

    await fs.writeFile(CONFIG.metaOutputPath, phpContent);

    console.log("\n✨ Retina image generation complete!\n");
    console.log(`✅ Generated images-meta.php with ${Object.keys(imagesMeta).length} images`);
    console.log(`   Location: ${path.relative(process.cwd(), CONFIG.metaOutputPath)}\n`);
    console.log("📝 Usage in PHP:");
    console.log("   render_responsive_image([");
    console.log("     'src' => get_template_directory_uri() . '/assets/images/hero.png',");
    console.log("     'alt' => 'Hero image',");
    console.log("   ]);");
  } catch (error) {
    console.error("\n❌ Error during generation:", error);
    process.exit(1);
  }
}

main();
