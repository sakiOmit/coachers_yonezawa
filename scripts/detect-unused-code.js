/**
 * detect-unused-code.js
 *
 * Detects unused code across the project:
 * - Unused SCSS classes (BEM classes not referenced in PHP/Astro/JS/SCSS)
 * - Base style duplicates (properties already defined in _reset.scss / _base.scss)
 * - Unused PHP functions (defined but never called)
 * - Unused template parts (not referenced by get_template_part())
 * - Unused JS exports (exported but never imported)
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

// ─── 1. Unused SCSS Classes ───

/**
 * Extract BEM class names from SCSS files, resolving &__ and &-- nesting.
 * Handles both nested patterns and standalone root-level selectors.
 */
function extractBEMClasses(scssFiles) {
  const classes = []; // { className, file, line }

  for (const file of scssFiles) {
    const rel = relativePath(file);
    // Skip foundation files (variables, mixins, reset, base, etc.)
    if (rel.includes('foundation/')) continue;
    // Skip _index.scss files (just @use forwards)
    if (path.basename(file) === '_index.scss') continue;

    const content = readFile(file);
    const lines = content.split('\n');

    // Track block context for resolving &__ and &--
    // Each entry: { name: string, depth: number }
    const blockStack = [];
    let braceDepth = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Remove strings and single-line comments for accurate brace counting
      const stripped = line.replace(/\/\/.*$/, '').replace(/'[^']*'|"[^"]*"/g, '');

      const openBraces = (stripped.match(/\{/g) || []).length;
      const closeBraces = (stripped.match(/\}/g) || []).length;

      // Detect class selectors at any level: .p-xxx, .c-xxx, .l-xxx, .u-xxx, .h-xxx
      // This catches both root-level and standalone modifier selectors (e.g. .c-button--cta)
      const classMatch = line.match(/^\s*\.((?:[pcluh])-[\w-]+)\s*[{,]/);
      if (classMatch) {
        const className = classMatch[1];

        if (braceDepth === 0) {
          // Root-level selector: set as the new block context
          blockStack.length = 0;
          blockStack.push({ name: className, depth: braceDepth });
        }
        // Always record the class regardless of depth
        classes.push({ className, file, line: i + 1 });
      }

      // Detect &__ (element) and &-- (modifier) nested selectors
      const nestedMatch = line.match(/^\s*&((?:__|--)[a-z][\w-]*)\s*[{,]/);
      if (nestedMatch && blockStack.length > 0) {
        const suffix = nestedMatch[1];
        // Resolve from the nearest parent block in the stack
        const parentBlock = blockStack[blockStack.length - 1].name;
        const fullClass = parentBlock + suffix;
        classes.push({ className: fullClass, file, line: i + 1 });
      }

      braceDepth += openBraces - closeBraces;

      // Pop block stack entries that are no longer in scope
      while (blockStack.length > 0 && braceDepth <= blockStack[blockStack.length - 1].depth) {
        blockStack.pop();
      }
    }
  }

  // Deduplicate by className+file (same class may appear in different contexts)
  const seen = new Set();
  return classes.filter(c => {
    const key = `${c.className}:${c.file}:${c.line}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/**
 * Find SCSS classes not referenced in any PHP/Astro/JS file.
 * Also searches other SCSS files (for cross-file references like
 * .c-button--cta .c-button__icon inside a modifier block).
 */
function findUnusedSCSSClasses(scssClasses, searchFiles, scssFiles) {
  const results = [];
  const allContent = {};

  // Pre-load all search file contents
  for (const file of [...searchFiles, ...scssFiles]) {
    if (!allContent[file]) {
      allContent[file] = readFile(file);
    }
  }

  for (const { className, file, line } of scssClasses) {
    let found = false;

    // Search in PHP/Astro/JS files
    for (const searchFile of searchFiles) {
      if (allContent[searchFile].includes(className)) {
        found = true;
        break;
      }
    }

    // If not found in templates, check other SCSS files for cross-references
    // (e.g. .c-button--cta { .c-button__icon { ... } } references c-button__icon)
    if (!found) {
      for (const scssFile of scssFiles) {
        if (scssFile === file) continue;
        if (allContent[scssFile].includes(className)) {
          found = true;
          break;
        }
      }
    }

    if (!found) {
      results.push({ className, file, line });
    }
  }

  return results;
}

// ─── 2. Base Style Duplicates ───

/**
 * Parse base/reset SCSS to extract element-level rules.
 * Handles multi-selector rules (e.g. "img,\npicture,\nvideo { ... }").
 */
function extractBaseStyles(baseFiles) {
  const baseRules = []; // { selectors: string[], property, value, file, line }

  for (const file of baseFiles) {
    const content = readFile(file);
    const lines = content.split('\n');
    let currentSelectors = [];
    let selectorBuffer = '';
    let inRule = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // Skip comments, @include, @use etc.
      if (line.startsWith('//') || line.startsWith('@') || line === '') continue;

      if (!inRule) {
        // Accumulate selector (may span multiple lines)
        if (line.includes('{')) {
          selectorBuffer += ' ' + line.replace(/\s*\{.*$/, '');
          currentSelectors = selectorBuffer
            .split(',')
            .map(s => s.trim())
            .filter(Boolean);
          inRule = true;
          selectorBuffer = '';

          // Check if property is on same line as {
          const afterBrace = line.split('{')[1]?.trim();
          if (afterBrace && afterBrace.includes(':') && !afterBrace.startsWith('//')) {
            const propMatch = afterBrace.match(/^([\w-]+)\s*:\s*(.+?)\s*;?\s*$/);
            if (propMatch) {
              baseRules.push({
                selectors: currentSelectors,
                property: propMatch[1],
                value: propMatch[2].replace(/;$/, '').trim(),
                file,
                line: i + 1,
              });
            }
          }
        } else {
          selectorBuffer += ' ' + line;
        }
      } else {
        // Inside a rule block
        if (line === '}' || line.includes('}')) {
          inRule = false;
          currentSelectors = [];
          continue;
        }

        // Skip nested blocks, @include etc
        if (line.startsWith('@') || line.includes('{')) continue;

        const propMatch = line.match(/^([\w-]+)\s*:\s*(.+?)\s*;?\s*$/);
        if (propMatch) {
          baseRules.push({
            selectors: currentSelectors,
            property: propMatch[1],
            value: propMatch[2].replace(/;$/, '').trim(),
            file,
            line: i + 1,
          });
        }
      }
    }
  }

  return baseRules;
}

/**
 * Find properties in component/project SCSS that duplicate what's
 * already defined in _base.scss / _reset.scss for the same element type.
 *
 * Focus: img/picture/video elements where max-width/height/display are
 * commonly redefined unnecessarily.
 */
function findBaseStyleDuplicates(baseRules, scssFiles) {
  const results = [];

  // Build a map of element -> { property -> { value, file, line } }
  const elementMap = {};
  for (const rule of baseRules) {
    for (const sel of rule.selectors) {
      const normalizedSel = sel.replace(/[*:[\]="]+/g, '').trim();
      if (!normalizedSel) continue;
      if (!elementMap[normalizedSel]) elementMap[normalizedSel] = {};
      elementMap[normalizedSel][rule.property] = {
        value: rule.value,
        file: rule.file,
        line: rule.line,
      };
    }
  }

  // Target elements whose styles are commonly duplicated
  const targetElements = ['img', 'picture', 'video', 'body', 'button'];

  // BEM element suffixes that correspond to HTML elements
  const suffixToElement = {
    img: 'img',
    image: 'img',
    photo: 'img',
    pic: 'img',
    logo: 'img',
    icon: 'img',
    video: 'video',
    picture: 'picture',
  };

  for (const file of scssFiles) {
    const rel = relativePath(file);
    if (rel.includes('foundation/')) continue;

    const content = readFile(file);
    const lines = content.split('\n');

    let currentContext = ''; // Track which BEM element we're inside

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // Track BEM element context
      const bemMatch = line.match(/&__([\w-]+)\s*\{/);
      if (bemMatch) {
        currentContext = bemMatch[1];
      }

      // Determine which HTML element this context maps to
      let targetElement = '';
      if (currentContext) {
        // Check if the BEM element name ends with a known suffix
        for (const [suffix, element] of Object.entries(suffixToElement)) {
          if (currentContext === suffix || currentContext.endsWith(`-${suffix}`)) {
            targetElement = element;
            break;
          }
        }
      }

      if (!targetElement) continue;

      // Check if the current property duplicates a base style for that element
      const propMatch = line.match(/^([\w-]+)\s*:\s*(.+?)\s*;?\s*$/);
      if (!propMatch) continue;

      const [, prop, val] = propMatch;
      const cleanVal = val.replace(/;$/, '').trim();

      // Look up the base rule
      const baseElementRules = elementMap[targetElement];
      if (!baseElementRules || !baseElementRules[prop]) continue;

      const baseRule = baseElementRules[prop];

      // Only report if the value is identical or equivalent
      if (cleanVal === baseRule.value) {
        results.push({
          property: `${prop}: ${cleanVal}`,
          file,
          line: i + 1,
          baseFile: baseRule.file,
          baseLine: baseRule.line,
          baseSelector: targetElement,
          context: currentContext,
        });
      }
    }
  }

  return results;
}

// ─── 3. Unused PHP Functions ───

function extractPHPFunctions(phpFiles) {
  const functions = []; // { name, file, line }

  for (const file of phpFiles) {
    // Only check inc/ directory and functions.php
    if (!file.includes('/inc/') && !file.endsWith('/functions.php')) continue;

    const content = readFile(file);
    const lines = content.split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const match = line.match(/^\s*function\s+([\w]+)\s*\(/);
      if (match) {
        functions.push({ name: match[1], file, line: i + 1 });
      }
    }
  }

  return functions;
}

function findUnusedPHPFunctions(functions, allPHPFiles) {
  const results = [];

  // Pre-load all PHP content
  const allContent = {};
  for (const file of allPHPFiles) {
    allContent[file] = readFile(file);
  }

  for (const { name, file, line } of functions) {
    let refCount = 0;
    let isHookCallback = false;

    for (const [searchFile, content] of Object.entries(allContent)) {
      const regex = new RegExp(`\\b${name}\\b`, 'g');
      const matches = content.match(regex) || [];

      if (searchFile === file) {
        // Check for add_action/add_filter callbacks
        if (
          content.includes(`'${name}'`) &&
          (content.includes('add_action') || content.includes('add_filter') ||
           content.includes('add_shortcode'))
        ) {
          isHookCallback = true;
        }
        // Subtract the definition line itself
        refCount += matches.length - 1;
      } else {
        refCount += matches.length;
      }
    }

    if (refCount === 0 && !isHookCallback) {
      results.push({ name, file, line });
    }
  }

  return results;
}

// ─── 4. Unused Template Parts ───

function findUnusedTemplateParts(templatePartsDir, allPHPFiles) {
  const results = [];
  const templateParts = getAllFiles(templatePartsDir, ['.php']);

  // Collect all get_template_part calls across PHP files
  const allCalls = [];
  for (const file of allPHPFiles) {
    const content = readFile(file);
    const matches = content.matchAll(/get_template_part\(\s*['"]([^'"]+)['"]/g);
    for (const match of matches) {
      allCalls.push(match[1]);
    }
  }

  for (const tpFile of templateParts) {
    const relPath = path.relative(THEME_DIR, tpFile).replace(/\.php$/, '');

    const isReferenced = allCalls.some(call => {
      const normalizedCall = call.replace(/^\//, '');
      return relPath === normalizedCall || relPath.endsWith(normalizedCall);
    });

    if (!isReferenced) {
      results.push({ file: tpFile });
    }
  }

  return results;
}

// ─── 5. Unused JS Exports ───

function extractJSExports(jsFiles) {
  const exports = []; // { name, file, line, type }

  // Skip example files
  const skipPatterns = ['.example.', '.test.', '.spec.'];

  for (const file of jsFiles) {
    if (skipPatterns.some(p => file.includes(p))) continue;

    const content = readFile(file);
    const lines = content.split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Skip default exports (usually the main entry point)
      if (/^\s*export\s+default\b/.test(line)) continue;

      const funcMatch = line.match(/^\s*export\s+(?:async\s+)?function\s+([\w]+)/);
      if (funcMatch) {
        exports.push({ name: funcMatch[1], file, line: i + 1, type: 'function' });
        continue;
      }

      const constMatch = line.match(/^\s*export\s+(?:const|let|var)\s+([\w]+)/);
      if (constMatch) {
        exports.push({ name: constMatch[1], file, line: i + 1, type: 'const' });
        continue;
      }

      const classMatch = line.match(/^\s*export\s+class\s+([\w]+)/);
      if (classMatch) {
        exports.push({ name: classMatch[1], file, line: i + 1, type: 'class' });
        continue;
      }
    }
  }

  return exports;
}

function findUnusedJSExports(jsExports, allJSFiles) {
  const results = [];

  // Pre-load all JS file contents
  const allContent = {};
  for (const file of allJSFiles) {
    allContent[file] = readFile(file);
  }

  for (const exp of jsExports) {
    let imported = false;

    for (const [searchFile, content] of Object.entries(allContent)) {
      if (searchFile === exp.file) continue;

      // Check for import statement that references this name
      if (content.includes(exp.name)) {
        // Look for import patterns
        const importRegex = new RegExp(
          `import\\s*\\{[^}]*\\b${exp.name}\\b[^}]*\\}\\s*from`
        );
        if (importRegex.test(content)) {
          imported = true;
          break;
        }
        // Also check for direct usage (e.g. re-export or dynamic import)
        const usageRegex = new RegExp(`\\b${exp.name}\\s*\\(`);
        if (usageRegex.test(content)) {
          imported = true;
          break;
        }
      }
    }

    if (!imported) {
      results.push(exp);
    }
  }

  return results;
}

// ─── Main ───

const JSON_MODE = process.argv.includes('--json');

function main() {
  // Gather files
  const scssFiles = getAllFiles(SCSS_DIR, ['.scss']);
  const phpFiles = getAllFiles(THEME_DIR, ['.php']);
  const jsFiles = getAllFiles(JS_DIR, ['.js']);
  const astroFiles = getAllFiles(ASTRO_DIR, ['.astro']);

  // Search targets for class name references (PHP + Astro + JS)
  const searchFiles = [...phpFiles, ...astroFiles, ...jsFiles];

  const issues = [];
  const categoryCounts = {
    unused_scss_classes: { warnings: 0, info: 0 },
    base_style_duplicates: { warnings: 0, info: 0 },
    unused_php_functions: { warnings: 0, info: 0 },
    unused_template_parts: { warnings: 0, info: 0 },
    unused_js_exports: { warnings: 0, info: 0 },
  };

  // ─── 1. Unused SCSS Classes ───
  if (!JSON_MODE) console.log('Scanning project for unused code...\n');
  if (!JSON_MODE) console.log('=== Unused SCSS Classes ===');
  const scssClasses = extractBEMClasses(scssFiles);
  const unusedClasses = findUnusedSCSSClasses(scssClasses, searchFiles, scssFiles);

  if (unusedClasses.length === 0) {
    if (!JSON_MODE) console.log('  No unused SCSS classes found.\n');
  } else {
    for (const { className, file, line } of unusedClasses) {
      categoryCounts.unused_scss_classes.warnings++;
      issues.push({
        category: 'unused_scss_classes',
        severity: 'warning',
        name: `.${className}`,
        file: relativePath(file),
        line,
        message: 'Not found in any PHP/Astro/JS/SCSS file',
      });
      if (!JSON_MODE) {
        console.log(`[WARNING] .${className} (${relativePath(file)}:${line})`);
        console.log(`  → Not found in any PHP/Astro/JS/SCSS file\n`);
      }
    }
  }

  // ─── 2. Base Style Duplicates ───
  if (!JSON_MODE) console.log('=== Base Style Duplicates ===');
  const baseFiles = [
    path.join(SCSS_DIR, 'foundation', '_reset.scss'),
    path.join(SCSS_DIR, 'foundation', '_base.scss'),
  ];
  const baseRules = extractBaseStyles(baseFiles);
  const duplicates = findBaseStyleDuplicates(baseRules, scssFiles);

  if (duplicates.length === 0) {
    if (!JSON_MODE) console.log('  No base style duplicates found.\n');
  } else {
    for (const dup of duplicates) {
      categoryCounts.base_style_duplicates.info++;
      issues.push({
        category: 'base_style_duplicates',
        severity: 'info',
        name: dup.property,
        file: relativePath(dup.file),
        line: dup.line,
        message: `Already defined in ${relativePath(dup.baseFile)}:${dup.baseLine} for <${dup.baseSelector}> (context: &__${dup.context})`,
      });
      if (!JSON_MODE) {
        console.log(`[INFO] ${dup.property} (${relativePath(dup.file)}:${dup.line})`);
        console.log(`  → Already defined in ${relativePath(dup.baseFile)}:${dup.baseLine} for <${dup.baseSelector}> (context: &__${dup.context})\n`);
      }
    }
  }

  // ─── 3. Unused PHP Functions ───
  if (!JSON_MODE) console.log('=== Unused PHP Functions ===');
  const phpFunctions = extractPHPFunctions(phpFiles);
  const unusedFunctions = findUnusedPHPFunctions(phpFunctions, phpFiles);

  if (unusedFunctions.length === 0) {
    if (!JSON_MODE) console.log('  No unused PHP functions found.\n');
  } else {
    for (const { name, file, line } of unusedFunctions) {
      categoryCounts.unused_php_functions.warnings++;
      issues.push({
        category: 'unused_php_functions',
        severity: 'warning',
        name: `${name}()`,
        file: relativePath(file),
        line,
        message: 'Not referenced anywhere',
      });
      if (!JSON_MODE) {
        console.log(`[WARNING] ${name}() (${relativePath(file)}:${line})`);
        console.log(`  → Not referenced anywhere\n`);
      }
    }
  }

  // ─── 4. Unused Template Parts ───
  if (!JSON_MODE) console.log('=== Unused Template Parts ===');
  const templatePartsDir = path.join(THEME_DIR, 'template-parts');
  const unusedTemplateParts = findUnusedTemplateParts(templatePartsDir, phpFiles);

  if (unusedTemplateParts.length === 0) {
    if (!JSON_MODE) console.log('  No unused template parts found.\n');
  } else {
    for (const { file } of unusedTemplateParts) {
      categoryCounts.unused_template_parts.warnings++;
      issues.push({
        category: 'unused_template_parts',
        severity: 'warning',
        name: relativePath(file),
        file: relativePath(file),
        line: null,
        message: 'No get_template_part() call found',
      });
      if (!JSON_MODE) {
        console.log(`[WARNING] ${relativePath(file)}`);
        console.log(`  → No get_template_part() call found\n`);
      }
    }
  }

  // ─── 5. Unused JS Exports ───
  if (!JSON_MODE) console.log('=== Unused JS Exports ===');
  const jsExports = extractJSExports(jsFiles);
  const unusedExports = findUnusedJSExports(jsExports, jsFiles);

  if (unusedExports.length === 0) {
    if (!JSON_MODE) console.log('  No unused JS exports found.\n');
  } else {
    for (const exp of unusedExports) {
      categoryCounts.unused_js_exports.warnings++;
      issues.push({
        category: 'unused_js_exports',
        severity: 'warning',
        name: exp.name,
        file: relativePath(exp.file),
        line: exp.line,
        message: 'Not imported anywhere',
      });
      if (!JSON_MODE) {
        console.log(`[WARNING] ${exp.name} (${relativePath(exp.file)}:${exp.line})`);
        console.log(`  → Not imported anywhere\n`);
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
