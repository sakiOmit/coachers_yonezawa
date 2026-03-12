import { build } from 'esbuild';
import chokidar from 'chokidar';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

/**
 * Vite plugin: JS bundler (esbuild)
 *
 * src/js/ 配下の ES modules を esbuild でバンドルし、
 * astro/public/assets/js/ に IIFE 形式で出力する。
 *
 * - ES modules (import/export) を解決してバンドル
 * - 開発時: minify なし、ビルド時: minify あり
 * - HMR: フルリロード
 */
export default function jsBundler({ rootDir }) {
  const srcJsDir = path.join(rootDir, 'src/js');
  const outDir = path.join(rootDir, 'astro/public/assets/js');
  let isDev = true;

  // エントリーポイントパターン
  // - src/js/main.js（共通）
  // - src/js/pages/*/index.js（ページ別、存在する場合）
  function getEntryPoints() {
    const entries = [];

    const mainJs = path.join(srcJsDir, 'main.js');
    if (fs.existsSync(mainJs)) {
      entries.push(mainJs);
    }

    const pageEntries = glob.sync(path.join(srcJsDir, 'pages/*/index.js'));
    entries.push(...pageEntries);

    return entries;
  }

  function ensureDir(filePath) {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  async function bundleFile(entryPoint) {
    const relativePath = path.relative(srcJsDir, entryPoint);
    const outFile = path.join(outDir, relativePath);

    try {
      ensureDir(outFile);
      await build({
        entryPoints: [entryPoint],
        outfile: outFile,
        bundle: true,
        format: 'iife',
        platform: 'browser',
        minify: !isDev,
        sourcemap: isDev ? 'inline' : false,
        logLevel: 'warning',
      });
      console.log(`[js-bundler] Bundled: ${path.relative(rootDir, outFile)}`);
    } catch (error) {
      console.error(`[js-bundler] Error bundling ${relativePath}:`, error.message);
    }
  }

  async function bundleAll() {
    const entries = getEntryPoints();
    await Promise.all(entries.map((entry) => bundleFile(entry)));
  }

  return {
    name: 'vite-js-bundler',

    configResolved(config) {
      isDev = config.command === 'serve';
    },

    async buildStart() {
      // 初回: 全バンドル
      await bundleAll();

      // chokidar で src/js/ を監視
      const watcher = chokidar.watch(path.join(srcJsDir, '**/*.js'), {
        ignoreInitial: true,
      });

      watcher.on('change', async () => {
        // どのファイルが変わっても全エントリーを再バンドル
        // （import 依存関係の追跡が複雑なため）
        await bundleAll();
      });

      watcher.on('add', async () => {
        await bundleAll();
      });
    },

    handleHotUpdate({ server }) {
      server.ws.send({ type: 'full-reload', path: '*' });
    },
  };
}
