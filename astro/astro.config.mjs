import { defineConfig } from 'astro/config';
import path from 'path';
import { fileURLToPath } from 'url';
import sassCompiler from './plugins/vite-sass-compiler.mjs';
import jsBundler from './plugins/vite-js-bundler.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');

export default defineConfig({
  server: {
    host: true,
  },
  vite: {
    plugins: [
      sassCompiler({ rootDir }),
      jsBundler({ rootDir }),
    ],
    server: {
      watch: {
        usePolling: false,
        useFsEvents: false,
      },
    },
  },
});
