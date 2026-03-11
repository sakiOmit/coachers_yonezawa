/**
 * detect-redundant-comments.js
 *
 * Detects redundant comments across the project:
 * - Commented-out code (PHP, SCSS, JS)
 * - WHAT comments (repeating what code already says)
 * - Decorative separator lines (pure decoration with no content)
 *
 * Theme directory is auto-detected from themes/{name}/functions.php.
 */

import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(import.meta.dirname, '..');

// ─── Theme Auto-Detection ───

function detectThemeDir() {
  const themesDir = path.join(ROOT, 'themes');
  if (!fs.existsSync(themesDir)) {
    console.error('Error: themes/ directory not found.');
    process.exit(1);
  }
  const themeDirs = fs.readdirSync(themesDir).filter(d =>
    fs.existsSync(path.join(themesDir, d, 'functions.php'))
  );
  if (themeDirs.length === 0) {
    console.error('Error: No theme with functions.php found in themes/.');
    process.exit(1);
  }
  return path.join(themesDir, themeDirs[0]);
}

const THEME_DIR = detectThemeDir();
const SCSS_DIR = path.join(ROOT, 'src', 'scss');
const JS_DIR = path.join(ROOT, 'src', 'js');
const ASTRO_DIR = path.join(ROOT, 'astro', 'src');

// ─── Utilities ───

function getAllFiles(dir, exts, result = []) {
  if (!fs.existsSync(dir)) return result;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (['node_modules', 'vendor', '.git', 'dist', 'build', 'public'].includes(entry.name)) continue;
      getAllFiles(full, exts, result);
    } else if (exts.some(ext => entry.name.endsWith(ext))) {
      result.push(full);
    }
  }
  return result;
}

function readFile(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf-8');
  } catch {
    return '';
  }
}

function relativePath(filePath) {
  return path.relative(ROOT, filePath);
}

// ─── 1. Commented-Out Code Detection ───

/**
 * Patterns that indicate commented-out CODE (not documentation).
 *
 * Strategy: match lines where a comment marker is immediately followed by
 * syntax tokens that only appear in executable code.
 */
const CODE_PATTERNS_SINGLE = [
  // PHP statements
  /^\s*\/\/\s*\$\w+\s*=/,                          // // $var =
  /^\s*\/\/\s*function\s+\w+\s*\(/,                // // function xxx(
  /^\s*\/\/\s*return\s+[\$'"\w\[({]/,                // // return $var / return '...' / return func(
  /^\s*\/\/\s*if\s*\(/,                             // // if (
  /^\s*\/\/\s*echo\s+/,                             // // echo ...
  /^\s*\/\/\s*get_template_part\s*\(/,              // // get_template_part(
  /^\s*\/\/\s*include\s+['"/]/,                     // // include '...'
  /^\s*\/\/\s*require\s+['"/]/,                     // // require '...'
  /^\s*\/\/\s*add_action\s*\(/,                     // // add_action(
  /^\s*\/\/\s*add_filter\s*\(/,                     // // add_filter(
  /^\s*\/\/\s*while\s*\(/,                          // // while (
  /^\s*\/\/\s*foreach\s*\(/,                        // // foreach (
  /^\s*\/\/\s*\}\s*$/,                              // // }
  /^\s*\/\/\s*<\?php/,                              // // <?php
  // SCSS rules (commented-out styles)
  /^\s*\/\/\s*&__[\w-]+\s*\{/,                     // // &__element {
  /^\s*\/\/\s*&--[\w-]+\s*\{/,                     // // &--modifier {
  /^\s*\/\/\s*\.[pcluh]-[\w-]+\s*\{/,              // // .p-xxx {
  /^\s*\/\/\s*@include\s+\w+/,                     // // @include mixin
  /^\s*\/\/\s*@extend\s+/,                         // // @extend
  /^\s*\/\/\s*@mixin\s+/,                          // // @mixin
  // JS statements
  /^\s*\/\/\s*const\s+\w+\s*=/,                    // // const xxx =
  /^\s*\/\/\s*let\s+\w+\s*=/,                      // // let xxx =
  /^\s*\/\/\s*var\s+\w+\s*=/,                      // // var xxx =
  /^\s*\/\/\s*import\s+\{/,                        // // import {
  /^\s*\/\/\s*export\s+/,                          // // export
  /^\s*\/\/\s*document\.\w+/,                      // // document.xxx
  /^\s*\/\/\s*window\.\w+/,                        // // window.xxx
  /^\s*\/\/\s*console\.\w+/,                       // // console.xxx
];

/**
 * SCSS-specific: a block of consecutive commented-out CSS property lines.
 * Single property lines in comments are usually spec references (Figma etc.),
 * so we only flag sequences of 3+ consecutive commented-out properties.
 */
function detectCommentedOutSCSSBlocks(file, lines) {
  const results = [];
  // Strict CSS property pattern: must look like "property-name: value" with valid CSS syntax
  // Excludes natural language (e.g. "PC: breadcrumbs", "SP: 1カラム")
  const propertyPattern = /^\s*\/\/\s{0,4}[\w-]+\s*:\s*(?:[\w#$'".,()\/%\s+-]+|rv\(|svw\(|pvw\(|var\(|rgb\(|rgba\().*[;)\w%]?\s*$/;
  const blockOpenPattern = /^\s*\/\/\s{0,2}\.[pcluh]-[\w-]+\s*\{/;
  const blockClosePattern = /^\s*\/\/\s{0,2}\}\s*$/;
  const includePattern = /^\s*\/\/\s{0,2}@include\s+/;
  // Lines that should NOT be treated as code (natural language descriptions)
  const naturalLanguageExclude = /^\s*\/\/\s*(PC|SP|Tab|Figma|WordPress|Source|Note|TODO|FIXME|HACK)\s*:/i;

  let blockStart = -1;
  let blockLength = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Skip natural language comments that happen to contain ":"
    const isNaturalLang = naturalLanguageExclude.test(line);
    const isCodeLine = !isNaturalLang && (
      propertyPattern.test(line) ||
      blockOpenPattern.test(line) ||
      blockClosePattern.test(line) ||
      includePattern.test(line)
    );

    if (isCodeLine) {
      if (blockStart === -1) blockStart = i;
      blockLength++;
    } else {
      if (blockLength >= 3) {
        // Report the block
        for (let j = blockStart; j < blockStart + blockLength; j++) {
          results.push({
            file,
            line: j + 1,
            content: lines[j].trim(),
          });
        }
      }
      blockStart = -1;
      blockLength = 0;
    }
  }

  // Handle trailing block
  if (blockLength >= 3) {
    for (let j = blockStart; j < blockStart + blockLength; j++) {
      results.push({
        file,
        line: j + 1,
        content: lines[j].trim(),
      });
    }
  }

  return results;
}

// Patterns to EXCLUDE from single-line detection (legitimate comments)
const EXCLUDE_PATTERNS = [
  /^\s*\/\/\s*@ts-/,                            // TypeScript directives
  /^\s*\/\/\s*eslint-/,                         // ESLint directives
  /^\s*\/\/\s*stylelint-/,                      // Stylelint directives
  /^\s*\/\/\s*phpcs:/,                          // PHPCS directives
  /^\s*\/\/\s*TODO:/i,                          // TODO comments
  /^\s*\/\/\s*FIXME:/i,                         // FIXME comments
  /^\s*\/\/\s*NOTE:/i,                          // NOTE comments
  /^\s*\/\/\s*HACK:/i,                          // HACK comments
  /^\s*\/\/\s*IMPORTANT:/i,                     // IMPORTANT comments
  /^\s*\/\/\s*WARNING:/i,                       // WARNING comments
  /^\s*\/\/\s*Figma/i,                          // Figma spec references
  /^\s*\/\/\s*WordPress:/i,                     // WordPress file references
  /^\s*\/\/\s*Source:/i,                        // Source references
  /^\s*\/\/\s*(PC|SP|Tab)\s*:/i,               // Responsive context descriptions
  /^\s*\/\/\s*[-=]{3,}/,                        // Section separators (with text nearby)
];

function detectCommentedOutCode(files) {
  const results = [];

  for (const file of files) {
    const content = readFile(file);
    const lines = content.split('\n');
    const isScss = file.endsWith('.scss');

    // For SCSS files, detect commented-out blocks (3+ consecutive lines)
    if (isScss) {
      const blockResults = detectCommentedOutSCSSBlocks(file, lines);
      results.push(...blockResults);
      // Skip single-line property detection for SCSS
      // (single commented properties are usually Figma specs)
    }

    // Detect single-line commented-out code (PHP, JS, and SCSS statements)
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Skip excluded patterns
      if (EXCLUDE_PATTERNS.some(p => p.test(line))) continue;

      // For SCSS: only flag statement-level patterns (not CSS property: value)
      // CSS properties are handled by block detection above
      const patterns = isScss
        ? CODE_PATTERNS_SINGLE.filter(p => {
            // Exclude CSS property patterns for SCSS (handled by block detection)
            const src = p.source;
            return !src.includes('[\\/w-]+\\s*:');
          })
        : CODE_PATTERNS_SINGLE;

      if (patterns.some(p => p.test(line))) {
        // Skip if inside a PHPDoc block
        let inDocBlock = false;
        for (let j = i - 1; j >= Math.max(0, i - 20); j--) {
          const prevLine = lines[j].trim();
          if (prevLine.startsWith('/**')) { inDocBlock = true; break; }
          if (prevLine.startsWith('*/') || prevLine === '') break;
          if (!prevLine.startsWith('*') && !prevLine.startsWith('//')) break;
        }
        if (inDocBlock) continue;

        // Avoid duplicate with SCSS block results
        if (isScss && results.some(r => r.file === file && r.line === i + 1)) continue;

        results.push({
          file,
          line: i + 1,
          content: line.trim(),
        });
      }
    }
  }

  return results;
}

// ─── 2. WHAT Comments (Redundant Comments) ───

// Japanese WHAT comment patterns paired with their code patterns
const WHAT_COMMENT_MAP = [
  {
    comment: /タイトルを(?:取得|セット|設定)/,
    code: /get_the_title|get_field\(['"]title['"]\)|->post_title|\$title\s*=/,
  },
  {
    comment: /画像を(?:取得|セット|設定|出力|表示)/,
    code: /get_field\(['"].*image.*['"]\)|render_responsive_image|wp_get_attachment/,
  },
  {
    comment: /URLを(?:取得|セット|設定)/,
    code: /get_permalink|get_field\(['"].*url.*['"]\)|home_url|esc_url/,
  },
  {
    comment: /日付を(?:取得|表示|出力)/,
    code: /get_the_date|the_date|date\(|get_field\(['"].*date/,
  },
  {
    comment: /(?:ループ|繰り返し)(?:開始|処理)/,
    code: /while\s*\(|foreach\s*\(|\.map\s*\(/,
  },
  {
    comment: /(?:条件|判定)(?:分岐|チェック)/,
    code: /if\s*\(/,
  },
  {
    comment: /テンプレート(?:読み込み|呼び出し|パーツ)/,
    code: /get_template_part/,
  },
  {
    comment: /(?:エスケープ|サニタイズ)/,
    code: /esc_html|esc_attr|esc_url|wp_kses|sanitize/,
  },
  {
    comment: /クラス名を(?:設定|取得|定義)/,
    code: /\$class|\bclass\b.*=/,
  },
  {
    comment: /変数を(?:定義|初期化|宣言)/,
    code: /\$\w+\s*=|const\s+\w+|let\s+\w+/,
  },
  {
    comment: /引数を(?:取得|受け取)/,
    code: /\$args\[|extract\(/,
  },
  {
    comment: /^\/\/\s*出力$/,
    code: /echo\s|print\s/,
  },
];

function detectWHATComments(files) {
  const results = [];

  for (const file of files) {
    const content = readFile(file);
    const lines = content.split('\n');

    for (let i = 0; i < lines.length - 1; i++) {
      const commentLine = lines[i].trim();
      const nextLine = lines[i + 1]?.trim() || '';

      // Match PHP-style single-line comments
      if (!commentLine.match(/^\/\/\s+/)) continue;

      // Skip section headers and separators
      if (/^\/\/\s*[-=]{3,}/.test(commentLine)) continue;

      // Skip empty or comment next lines
      if (!nextLine || nextLine.startsWith('//') || nextLine.startsWith('/*') || nextLine.startsWith('*')) continue;

      for (const { comment, code } of WHAT_COMMENT_MAP) {
        if (comment.test(commentLine) && code.test(nextLine)) {
          results.push({
            file,
            line: i + 1,
            comment: commentLine,
            code: nextLine,
          });
          break;
        }
      }
    }
  }

  return results;
}

// ─── 3. Decorative Separator Lines ───

function detectDecorativeSeparators(files) {
  const results = [];

  // Pure separator lines: only repeated punctuation, no meaningful text
  const separatorPatterns = [
    /^\s*\/\/\s*[=]{10,}\s*$/,                   // // ============
    /^\s*\/\/\s*[-]{10,}\s*$/,                   // // ------------
    /^\s*\/\/\s*[*]{10,}\s*$/,                   // // ************
    /^\s*\/\/\s*[#]{10,}\s*$/,                   // // ############
    /^\s*\/\*\s*[=]{10,}\s*\*\/\s*$/,            // /* ============ */
    /^\s*\/\*\s*[-]{10,}\s*\*\/\s*$/,            // /* ------------ */
  ];

  for (const file of files) {
    const content = readFile(file);
    const lines = content.split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (!separatorPatterns.some(p => p.test(line))) continue;

      // Check surrounding context: if adjacent to a title comment, it's a legitimate header
      const prevLine = i > 0 ? lines[i - 1].trim() : '';
      const nextLine = i < lines.length - 1 ? lines[i + 1].trim() : '';

      // A "title comment" is a // line with actual text (not just punctuation)
      const isTitleComment = (l) => /^\/\/\s+\S/.test(l) && !/^\/\/\s*[-=*#]{5,}\s*$/.test(l);

      // If the separator frames a section title, it's legitimate
      if (isTitleComment(prevLine) || isTitleComment(nextLine)) continue;

      results.push({
        file,
        line: i + 1,
        content: line.trim(),
      });
    }
  }

  return results;
}

// ─── Main ───

const JSON_MODE = process.argv.includes('--json');

function main() {
  const phpFiles = getAllFiles(THEME_DIR, ['.php']);
  const scssFiles = getAllFiles(SCSS_DIR, ['.scss']);
  const jsFiles = getAllFiles(JS_DIR, ['.js']);
  const astroFiles = getAllFiles(ASTRO_DIR, ['.astro']);
  const allFiles = [...phpFiles, ...scssFiles, ...jsFiles, ...astroFiles];

  const issues = [];
  const categoryCounts = {
    commented_out_code: { warnings: 0, info: 0 },
    redundant_comments: { warnings: 0, info: 0 },
    decorative_separators: { warnings: 0, info: 0 },
  };

  // ─── 1. Commented-Out Code ───
  if (!JSON_MODE) console.log('Scanning project for redundant comments...\n');
  if (!JSON_MODE) console.log('=== Commented-Out Code ===');
  const commentedCode = detectCommentedOutCode(allFiles);

  if (commentedCode.length === 0) {
    if (!JSON_MODE) console.log('  No commented-out code found.\n');
  } else {
    for (const item of commentedCode) {
      categoryCounts.commented_out_code.warnings++;
      issues.push({
        category: 'commented_out_code',
        severity: 'warning',
        name: item.content,
        file: relativePath(item.file),
        line: item.line,
        message: 'Commented-out code detected',
      });
      if (!JSON_MODE) {
        console.log(`[WARNING] ${relativePath(item.file)}:${item.line}`);
        console.log(`  ${item.content}\n`);
      }
    }
  }

  // ─── 2. Redundant (WHAT) Comments ───
  if (!JSON_MODE) console.log('=== Redundant Comments ===');
  const whatComments = detectWHATComments(allFiles);

  if (whatComments.length === 0) {
    if (!JSON_MODE) console.log('  No redundant WHAT comments found.\n');
  } else {
    for (const item of whatComments) {
      categoryCounts.redundant_comments.info++;
      issues.push({
        category: 'redundant_comments',
        severity: 'info',
        name: item.comment,
        file: relativePath(item.file),
        line: item.line,
        message: `WHAT comment repeats what code says: ${item.code}`,
      });
      if (!JSON_MODE) {
        console.log(`[INFO] ${relativePath(item.file)}:${item.line}`);
        console.log(`  ${item.comment}`);
        console.log(`  ${item.code}\n`);
      }
    }
  }

  // ─── 3. Decorative Separators ───
  if (!JSON_MODE) console.log('=== Decorative Separator Lines ===');
  const separators = detectDecorativeSeparators(allFiles);

  if (separators.length === 0) {
    if (!JSON_MODE) console.log('  No standalone decorative separators found.\n');
  } else {
    for (const item of separators) {
      categoryCounts.decorative_separators.info++;
      issues.push({
        category: 'decorative_separators',
        severity: 'info',
        name: item.content,
        file: relativePath(item.file),
        line: item.line,
        message: 'Standalone decorative separator with no adjacent title',
      });
      if (!JSON_MODE) {
        console.log(`[INFO] ${relativePath(item.file)}:${item.line}`);
        console.log(`  ${item.content}\n`);
      }
    }
  }

  // ─── Summary ───
  const totalWarnings = issues.filter(i => i.severity === 'warning').length;
  const totalInfo = issues.filter(i => i.severity === 'info').length;

  if (JSON_MODE) {
    const output = {
      summary: {
        total_warnings: totalWarnings,
        total_info: totalInfo,
        categories: categoryCounts,
      },
      issues,
    };
    console.log(JSON.stringify(output, null, 2));
  } else {
    console.log('─'.repeat(50));
    console.log(`Total: ${totalWarnings} warnings, ${totalInfo} info`);
  }

  if (totalWarnings > 0) {
    process.exit(1);
  }
}

main();
