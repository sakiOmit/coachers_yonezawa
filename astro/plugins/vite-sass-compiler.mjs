import * as sass from 'sass';
import chokidar from 'chokidar';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { createRequire } from 'module';
import { pathToFileURL } from 'url';

/**
 * Vite plugin: SCSS precompiler
 *
 * src/css/ 配下の SCSS を dart-sass でコンパイルし、
 * astro/public/assets/css/ に CSS として出力する。
 *
 * - 依存追跡: パーシャル変更時は影響するメインSCSSのみ再コンパイル
 * - メインSCSS変更 → そのファイルのみ再コンパイル
 * - node_modules パッケージの @use を自動解決
 * - HMR: フルリロード
 */
export default function sassCompiler({ rootDir }) {
  const srcCssDir = path.join(rootDir, 'src/css');
  const srcScssDir = path.join(rootDir, 'src/scss');
  const outDir = path.join(rootDir, 'astro/public/assets/css');

  // node_modules パッケージ解決用
  const require = createRequire(rootDir + '/package.json');

  /**
   * node_modules のベアスペシファイア(@scoped/pkg/path 等)を解決するインポーター
   * Vite のネイティブ sass 処理と同等の解決を standalone sass で実現する
   */
  const nodeModulesImporter = {
    findFileUrl(url) {
      // 相対パス・絶対パスはスキップ
      if (url.startsWith('.') || url.startsWith('/') || url.startsWith('file:')) {
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
    loadPaths: [path.join(rootDir, 'src')],
    importers: [nodeModulesImporter],
  };

  // Vendor CSS files to copy into astro/public/assets/css/
  const vendorCssFiles = [
    { src: '@splidejs/splide/dist/css/splide-core.min.css', dest: 'splide-core.min.css' },
  ];

  // メインSCSSファイルのグロブパターン（パーシャル除外）
  const mainScssPattern = path.join(srcCssDir, '**/*.scss');
  const partialPattern = path.join(srcCssDir, '**/_*.scss');

  // 依存マップ: パーシャルパス → Set<メインSCSSパス>
  const depsMap = new Map();

  function ensureDir(filePath) {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  function compileSingleFile(filePath) {
    // パーシャルはスキップ
    if (path.basename(filePath).startsWith('_')) return;

    const relativePath = path.relative(srcCssDir, filePath);
    const outFile = path.join(outDir, relativePath).replace(/\.scss$/, '.css');

    try {
      const result = sass.compile(filePath, {
        style: 'expanded',
        ...sassOptions,
      });
      ensureDir(outFile);
      fs.writeFileSync(outFile, result.css);

      // 依存マップ更新: このメインSCSSが読み込んだパーシャルを記録
      for (const url of result.loadedUrls) {
        if (url.protocol !== "file:") continue;
        const depPath = url.pathname;
        if (depPath === filePath) continue;
        if (!depsMap.has(depPath)) {
          depsMap.set(depPath, new Set());
        }
        depsMap.get(depPath).add(filePath);
      }

      console.log(`[sass-compiler] Compiled: ${path.relative(rootDir, outFile)}`);
    } catch (error) {
      console.error(`[sass-compiler] Error compiling ${relativePath}:`, error.message);
    }
  }

  function compileAll() {
    depsMap.clear();
    const files = glob.sync(mainScssPattern, { ignore: partialPattern });
    files.forEach((file) => compileSingleFile(file));
    console.log(`[sass-compiler] Dependency map: ${depsMap.size} partials tracked`);
  }

  function compileAffected(changedPartial) {
    const affected = depsMap.get(changedPartial);
    if (affected && affected.size > 0) {
      console.log(
        `[sass-compiler] ${path.basename(changedPartial)} → ${affected.size} file(s) affected`
      );
      for (const mainFile of affected) {
        compileSingleFile(mainFile);
      }
    } else {
      // 依存マップにない場合（新規パーシャル等）→ 全再コンパイル
      console.log(
        `[sass-compiler] ${path.basename(changedPartial)} → not in dep map, recompile all`
      );
      compileAll();
    }
  }

  // 監視対象パターン
  const watchPatterns = [
    path.join(srcCssDir, '**/*.scss'),
    path.join(srcScssDir, '**/*.scss'),
  ];

  return {
    name: 'vite-sass-compiler',

    buildStart() {
      // Copy vendor CSS files from node_modules
      for (const { src, dest } of vendorCssFiles) {
        try {
          const srcPath = require.resolve(src);
          const destPath = path.join(outDir, dest);
          ensureDir(destPath);
          fs.copyFileSync(srcPath, destPath);
          console.log(`[sass-compiler] Copied vendor: ${dest}`);
        } catch (error) {
          console.warn(`[sass-compiler] Vendor CSS not found: ${src}`);
        }
      }

      // 初回: 全コンパイル
      compileAll();

    configureServer(server) {
      // Vite 内蔵 watcher に外部ディレクトリを追加
      server.watcher.add([srcCssDir, srcScssDir]);

      server.watcher.on("change", (filePath) => {
        if (!filePath.endsWith(".scss")) return;
        if (!filePath.startsWith(srcCssDir) && !filePath.startsWith(srcScssDir)) return;

      watcher.on('change', (filePath) => {
        const basename = path.basename(filePath);
        const isPartial = basename.startsWith('_');
        const isInScssDir = filePath.startsWith(srcScssDir);

        if (isPartial || isInScssDir) {
          compileAffected(filePath);
        } else {
          // メインSCSS変更 → そのファイルのみ
          compileSingleFile(filePath);
        }
      });

      watcher.on('add', (filePath) => {
        if (!path.basename(filePath).startsWith('_') && filePath.startsWith(srcCssDir)) {
          compileSingleFile(filePath);
        }
      });
    },

    handleHotUpdate({ server }) {
      server.ws.send({ type: 'full-reload', path: '*' });
    },
  };
}
