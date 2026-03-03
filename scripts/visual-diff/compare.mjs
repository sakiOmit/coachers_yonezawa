import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function compareFigmaAndImplementation() {
  const cacheDir = path.join(__dirname, '../../.claude/cache/visual-diff');
  fs.mkdirSync(cacheDir, { recursive: true });

  // Capture implementation
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:8000/', { waitUntil: 'networkidle' });
  await page.waitForSelector('.l-footer');

  const footer = await page.$('.l-footer');
  const implPath = path.join(cacheDir, 'footer-impl.png');

  if (footer) {
    await footer.screenshot({ path: implPath });
    const box = await footer.boundingBox();
    console.log(`Implementation footer: ${box.width}x${box.height}`);
  }

  await browser.close();

  // Check Figma reference exists
  const figmaPath = path.join(cacheDir, 'footer-figma.png');
  if (!fs.existsSync(figmaPath)) {
    console.log('\n⚠ Figma reference not found. Manual comparison required.');
    console.log('Implementation screenshot saved to:', implPath);
    return;
  }

  // Compare images
  const img1 = PNG.sync.read(fs.readFileSync(implPath));
  const img2 = PNG.sync.read(fs.readFileSync(figmaPath));

  const { width, height } = img1;
  const diff = new PNG({ width, height });

  const numDiffPixels = pixelmatch(
    img1.data, img2.data, diff.data,
    width, height,
    { threshold: 0.1 }
  );

  const diffPath = path.join(cacheDir, 'footer-diff.png');
  fs.writeFileSync(diffPath, PNG.sync.write(diff));

  const totalPixels = width * height;
  const diffPercent = ((numDiffPixels / totalPixels) * 100).toFixed(2);

  console.log(`\n=== Visual Diff Results ===`);
  console.log(`Different pixels: ${numDiffPixels} / ${totalPixels} (${diffPercent}%)`);
  console.log(`Diff image saved to: ${diffPath}`);

  return { numDiffPixels, totalPixels, diffPercent };
}

compareFigmaAndImplementation().catch(console.error);
