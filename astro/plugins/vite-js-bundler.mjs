import { build } from "esbuild";
import fs from "fs";
import path from "path";
import { glob } from "glob";

/**
 * Vite plugin: JS bundler (esbuild)
 *
 * src/js/ 配下の ES modules を esbuild でバンドルし、
 * astro/public/assets/js/ に IIFE 形式で出力する。
 *
 * - ES modules (import/export) を解決してバンドル
 * - 開発時: minify なし、ビルド時: minify あり
 * - HMR: Vite内蔵watcherでフルリロード
 */
export default function jsBundler({ rootDir }) {
  const srcJsDir = path.join(rootDir, "src/js");
  const outDir = path.join(rootDir, "astro/public/assets/js");
  let isDev = true;

  function getEntryPoints() {
    const entries = [];

    const mainJs = path.join(srcJsDir, "main.js");
    if (fs.existsSync(mainJs)) {
      entries.push(mainJs);
    }

    const pageEntries = glob.sync(path.join(srcJsDir, "pages/*/index.js"));
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
        format: "iife",
        platform: "browser",
        minify: !isDev,
        sourcemap: isDev ? "inline" : false,
        logLevel: "warning",
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
    name: "vite-js-bundler",

    configResolved(config) {
      isDev = config.command === "serve";
    },

    async buildStart() {
      await bundleAll();
    },

    configureServer(server) {
      // Vite 内蔵 watcher に外部ディレクトリを追加
      server.watcher.add(srcJsDir);
      console.log(`[js-bundler] Added to Vite watcher: ${srcJsDir}`);

      server.watcher.on("change", async (filePath) => {
        if (!filePath.endsWith(".js")) return;
        if (!filePath.startsWith(srcJsDir)) return;

        console.log(`[js-bundler] Change detected: ${filePath}`);
        await bundleAll();
        server.ws.send({ type: "full-reload", path: "*" });
      });

      server.watcher.on("add", async (filePath) => {
        if (!filePath.endsWith(".js")) return;
        if (!filePath.startsWith(srcJsDir)) return;

        await bundleAll();
        server.ws.send({ type: "full-reload", path: "*" });
      });
    },
  };
}
