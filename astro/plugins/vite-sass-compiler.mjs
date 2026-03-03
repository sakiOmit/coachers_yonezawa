import * as sass from "sass";
import fs from "fs";
import path from "path";
import { glob } from "glob";
import { createRequire } from "module";
import { pathToFileURL } from "url";

/**
 * Vite plugin: SCSS precompiler
 *
 * src/css/ 配下の SCSS を dart-sass でコンパイルし、
 * astro/public/assets/css/ に CSS として出力する。
 *
 * - パーシャル(_*.scss)変更 → 全メインSCSS再コンパイル
 * - メインSCSS変更 → そのファイルのみ再コンパイル
 * - node_modules パッケージの @use を自動解決
 * - HMR: Vite内蔵watcherでフルリロード
 */
export default function sassCompiler({ rootDir }) {
  const srcCssDir = path.join(rootDir, "src/css");
  const srcScssDir = path.join(rootDir, "src/scss");
  const outDir = path.join(rootDir, "astro/public/assets/css");

  // node_modules パッケージ解決用
  const require = createRequire(rootDir + "/package.json");

  const nodeModulesImporter = {
    findFileUrl(url) {
      if (url.startsWith(".") || url.startsWith("/") || url.startsWith("file:")) {
        return null;
      }
      try {
        const resolved = require.resolve(url);
        return pathToFileURL(resolved);
      } catch {
        return null;
      }
    },
  };

  const sassOptions = {
    loadPaths: [path.join(rootDir, "src")],
    importers: [nodeModulesImporter],
  };

  const mainScssPattern = path.join(srcCssDir, "**/*.scss");
  const partialPattern = path.join(srcCssDir, "**/_*.scss");

  function ensureDir(filePath) {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  function compileSingleFile(filePath) {
    if (path.basename(filePath).startsWith("_")) return;

    const relativePath = path.relative(srcCssDir, filePath);
    const outFile = path.join(outDir, relativePath).replace(/\.scss$/, ".css");

    try {
      const result = sass.compile(filePath, {
        style: "expanded",
        ...sassOptions,
      });
      ensureDir(outFile);
      fs.writeFileSync(outFile, result.css);
      console.log(`[sass-compiler] Compiled: ${path.relative(rootDir, outFile)}`);
    } catch (error) {
      console.error(`[sass-compiler] Error compiling ${relativePath}:`, error.message);
    }
  }

  function compileAll() {
    const files = glob.sync(mainScssPattern, { ignore: partialPattern });
    files.forEach((file) => compileSingleFile(file));
  }

  return {
    name: "vite-sass-compiler",

    // Vite の server.watch に src/scss, src/css を追加
    config() {
      return {
        server: {
          watch: {
            // WSL2 対応: polling 有効化
            usePolling: true,
            interval: 300,
          },
        },
      };
    },

    buildStart() {
      compileAll();
    },

    configureServer(server) {
      // Vite 内蔵 watcher に外部ディレクトリを追加
      server.watcher.add([srcCssDir, srcScssDir]);

      console.log(`[sass-compiler] Added to Vite watcher: ${srcCssDir}`);
      console.log(`[sass-compiler] Added to Vite watcher: ${srcScssDir}`);

      server.watcher.on("change", (filePath) => {
        if (!filePath.endsWith(".scss")) return;
        if (!filePath.startsWith(srcCssDir) && !filePath.startsWith(srcScssDir)) return;

        const basename = path.basename(filePath);
        const isPartial = basename.startsWith("_");
        const isInScssDir = filePath.startsWith(srcScssDir);

        console.log(`[sass-compiler] Change detected: ${filePath}`);

        if (isPartial || isInScssDir) {
          console.log(`[sass-compiler] Partial/shared changed: ${basename} → recompile all`);
          compileAll();
        } else {
          compileSingleFile(filePath);
        }

        server.ws.send({ type: "full-reload", path: "*" });
      });

      server.watcher.on("add", (filePath) => {
        if (!filePath.endsWith(".scss")) return;
        if (!path.basename(filePath).startsWith("_") && filePath.startsWith(srcCssDir)) {
          compileSingleFile(filePath);
          server.ws.send({ type: "full-reload", path: "*" });
        }
      });
    },
  };
}
