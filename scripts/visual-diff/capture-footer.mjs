import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function captureFooter() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Set viewport to match Figma design width
  await page.setViewportSize({ width: 1440, height: 900 });

  await page.goto('http://localhost:8000/', { waitUntil: 'networkidle' });

  // Wait for footer to be visible
  await page.waitForSelector('.l-footer');

  // Capture footer element
  const footer = await page.$('.l-footer');
  if (footer) {
    const outputPath = path.join(__dirname, '../../.claude/cache/visual-diff/footer-implementation.png');

    // Ensure directory exists
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });

    await footer.screenshot({ path: outputPath });
    console.log(`Footer screenshot saved to: ${outputPath}`);

    // Get bounding box info
    const box = await footer.boundingBox();
    console.log(`Footer dimensions: ${box.width}x${box.height}`);
  }

  await browser.close();
}

captureFooter().catch(console.error);
