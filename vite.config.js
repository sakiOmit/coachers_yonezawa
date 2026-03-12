import { defineConfig, loadEnv } from "vite";
import liveReload from "vite-plugin-live-reload";
import path from "path";
import { fileURLToPath } from "url";
import chokidar from "chokidar";
import { globSync } from "glob";
import autoprefixer from "autoprefixer";
import cssnano from "cssnano";
import purgecss from "@fullhuman/postcss-purgecss";
import { THEME_NAME } from "./config/theme.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Auto-discover page entries from src/css/pages/ and src/js/pages/
function discoverPageEntries() {
  const entries = {};

  // ページ別CSS: style.scss / archive.scss / single.scss を検出
  // style.scss   → "style-{pageName}"
  // archive.scss → "style-{pageName}-archive"
  // single.scss  → "style-{pageName}-single"
  const cssFiles = globSync("src/css/pages/*/{style,archive,single}.scss", { cwd: __dirname });
  for (const file of cssFiles) {
    const pageName = file.split("/")[3]; // src/css/pages/{pageName}/...
    const baseName = path.basename(file, ".scss"); // style, archive, or single
    const entryKey = baseName === "style" ? `style-${pageName}` : `style-${pageName}-${baseName}`;
    entries[entryKey] = path.resolve(__dirname, file);
  }

  // ページ別JS: src/js/pages/{pageName}/index.js → "page-{pageName}"
  const jsFiles = globSync("src/js/pages/*/index.js", { cwd: __dirname });
  for (const file of jsFiles) {
    const pageName = file.split("/")[3]; // src/js/pages/{pageName}/index.js
    entries[`page-${pageName}`] = path.resolve(__dirname, file);
  }

  return entries;
}

// カスタムログプラグイン（リロード回数をカウント + debounce）
const logReloadPlugin = () => {
  let reloadCount = 0;
  let reloadTimeout = null;

  return {
    name: "log-reload",
    handleHotUpdate({ file, server }) {
      if (file.endsWith(".php")) {
        reloadCount++;
        console.log(`[Reload #${reloadCount}] PHP file changed: ${path.relative(__dirname, file)}`);

        // debounce: 200ms以内の連続変更をまとめる
        if (reloadTimeout) {
          console.log("  → Debouncing reload...");
          clearTimeout(reloadTimeout);
        }

        reloadTimeout = setTimeout(() => {
          console.log("  → Executing full reload");
          server.ws.send({ type: "full-reload" });
          reloadTimeout = null;
        }, 200);

        // デフォルトのリロードをキャンセル
        return [];
      }
    },
  };
};

export default defineConfig(({ mode }) => {
  // 環境変数を読み込み
  const env = loadEnv(mode, process.cwd(), "");
  const VITE_PORT = parseInt(env.VITE_PORT || "3000", 10);

  console.log(`📦 Theme: ${THEME_NAME}`);
  const isProduction = mode === "production";

  return {
    plugins: [
      liveReload(
        // PHPファイルの変更を監視（テーマディレクトリのみ）
        path.resolve(__dirname, `themes/${THEME_NAME}/**/*.php`)
      ),
      // デバッグ用のログプラグイン
      !isProduction && logReloadPlugin(),
      // WSL2でsrc/scss/パーシャル変更時にCSSを再コンパイルさせる
      {
        name: "watch-scss",
        configureServer(server) {
          const scssDir = path.resolve(__dirname, "src/scss");

          const watcher = chokidar.watch(scssDir, {
            usePolling: true,
            interval: 300,
            ignoreInitial: true,
          });

          let debounceTimer = null;
          watcher.on("change", (filePath) => {
            if (debounceTimer) return;
            debounceTimer = setTimeout(() => {
              debounceTimer = null;
              console.log(`[watch-scss] Change: ${path.relative(__dirname, filePath)}`);
              for (const [, mod] of server.moduleGraph.idToModuleMap) {
                if (mod.file?.endsWith(".scss")) {
                  server.moduleGraph.invalidateModule(mod);
                }
              }
              server.ws.send({ type: "full-reload" });
            }, 100);
          });
        },
      },
    ].filter(Boolean),

    css: {
      preprocessorOptions: {
        scss: {
          api: "modern-compiler", // 新しいSass APIを使用
          loadPaths: [path.resolve(__dirname, "src")], // SCSSのインポートパスを解決
        },
      },
      postcss: {
        plugins: [
          autoprefixer,
          // 本番環境でのみPurgeCSSとcssnanoを適用
          ...(isProduction
            ? [
                purgecss.default({
                  content: [
                    `./themes/${THEME_NAME}/**/*.php`,
                    "./src/js/**/*.js",
                    "./src/scss/**/*.scss",
                  ],
                  safelist: {
                    // WordPress標準クラス
                    standard: [
                      /^wp-/,
                      /^post-/,
                      /^page-/,
                      /^menu-/,
                      /^widget-/,
                      /^screen-reader/,
                      /^alignnone/,
                      /^aligncenter/,
                      /^alignleft/,
                      /^alignright/,
                    ],
                    // FLOCSS接頭辞（動的クラス対応）
                    deep: [/^l-/, /^c-/, /^p-/, /^u-/, /^is-/, /^has-/, /^js-/],
                    // Contact Form 7, Splide, GSAP, その他プラグイン
                    greedy: [/^wpcf7/, /^splide/, /^gsap/, /^swiper/],
                  },
                  defaultExtractor: (content) => content.match(/[\w-/:]+(?<!:)/g) || [],
                }),
              ]
            : []),
          ...(isProduction
            ? [
                cssnano({
                  preset: [
                    "default",
                    {
                      discardComments: {
                        removeAll: true,
                      },
                      normalizeWhitespace: true,
                      mergeRules: false, // @mediaルールのマージを無効化
                    },
                  ],
                }),
              ]
            : []),
        ],
      },
    },

    build: {
      manifest: true,
      outDir: path.resolve(__dirname, `themes/${THEME_NAME}/assets`),
      emptyOutDir: false, // 画像ファイルを保持するため false
      sourcemap: !isProduction,
      minify: "esbuild",
      cssCodeSplit: true,
      assetsInlineLimit: 4096, // 4KB以下は base64 inline化
      rollupOptions: {
        input: {
          // 共通アセット（必須）
          main: path.resolve(__dirname, "src/js/main.js"),
          style: path.resolve(__dirname, "src/css/common.scss"),

          // ページ別アセット（自動検出）
          // CSS: src/css/pages/{page}/style.scss   → css/{page}/style.css
          //      src/css/pages/{cpt}/archive.scss  → css/{cpt}/archive.css
          //      src/css/pages/{cpt}/single.scss   → css/{cpt}/single.css
          // JS:  src/js/pages/{page}/index.js      → js/{page}/index.js
          ...discoverPageEntries(),
        },
        output: {
          entryFileNames: (chunkInfo) => {
            const name = chunkInfo.name;

            // ページ別JSは階層構造で出力
            if (name.startsWith("page-")) {
              const pageName = name.replace(/^page-/, "");
              return `js/${pageName}/index.js`;
            }

            // その他のJSファイル
            return "js/[name].js";
          },
          chunkFileNames: "js/[name].js",
          assetFileNames: (assetInfo) => {
            const fileName = assetInfo.names?.[0] || "";
            if (fileName.endsWith(".css")) {
              const name = fileName.replace(/^style-/, "").replace(/\.css$/, "");
              // archive/single 対応: style-{page}-{type} → css/{page}/{type}.css
              const archiveMatch = name.match(/^(.+)-(archive|single)$/);
              if (archiveMatch) {
                return `css/${archiveMatch[1]}/${archiveMatch[2]}.css`;
              }
              // 通常ページ: style-{page} → css/{page}/style.css
              return `css/${name}/style.css`;
            }
            return "[name][extname]";
          },
          // ベンダーライブラリを分離
          manualChunks: (id) => {
            if (id.includes("node_modules")) {
              if (id.includes("gsap")) {
                return "vendor-gsap";
              }
              if (id.includes("@splidejs")) {
                return "vendor-splide";
              }
              return "vendor";
            }
          },
        },
        treeshake: {
          moduleSideEffects: false,
          propertyReadSideEffects: false,
          tryCatchDeoptimization: false,
        },
      },
      chunkSizeWarningLimit: 300, // パフォーマンスバジェット: 300KB超で警告
    },

    optimizeDeps: {
      include: ["gsap", "@splidejs/splide"],
      exclude: [],
    },

    server: {
      host: "0.0.0.0",
      port: VITE_PORT,
      strictPort: true,
      cors: true,
      hmr: {
        host: "localhost",
        protocol: "ws",
      },
      watch: {
        usePolling: true,
        interval: 100,
      },
    },
  };
});
