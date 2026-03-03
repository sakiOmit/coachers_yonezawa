#!/usr/bin/env node

/**
 * BEM Nesting Checker
 *
 * Checks that BEM elements are properly nested within their block.
 * Detects when multiple elements of the same block are written independently.
 *
 * Usage:
 *   node scripts/check-bem-nesting.js
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m',
};

/**
 * Get all SCSS files in a directory recursively
 */
function getSCSSFiles(dir, fileList = []) {
  const files = readdirSync(dir);

  files.forEach(file => {
    const filePath = join(dir, file);
    const stat = statSync(filePath);

    if (stat.isDirectory()) {
      getSCSSFiles(filePath, fileList);
    } else if (file.endsWith('.scss') && !file.startsWith('_index')) {
      fileList.push(filePath);
    }
  });

  return fileList;
}

/**
 * Parse SCSS file and extract BEM blocks and elements
 */
function parseSCSSFile(content) {
  const lines = content.split('\n');
  const blocks = new Map(); // Map<blockName, { elements: Set<string>, lines: number[] }>
  const nestingViolations = []; // Array of { line, violation }

  // Match patterns like .p-xxx__yyy or .c-xxx__yyy or .l-xxx__yyy or .u-xxx__yyy
  // Supports all FLOCSS prefixes: p-, c-, l-, u-
  const bemPattern = /^\s*\.([pclu]-[a-z0-9-]+)(__[a-z0-9-]+|--[a-z0-9-]+)?\s*[{,]/;

  // Match &- pattern (PROHIBITED - should be &__)
  // IMPORTANT: &-- is allowed (BEM modifier), only &- followed by single hyphen is prohibited
  const ampersandHyphenPattern = /&-(?!-)[a-z0-9-]+/;

  lines.forEach((line, index) => {
    const match = line.match(bemPattern);
    if (match) {
      const fullSelector = match[0].trim();
      const blockName = match[1]; // e.g., 'p-top'
      const suffix = match[2]; // e.g., '__hero' or '--large' or undefined

      if (suffix && suffix.startsWith('__')) {
        // This is an element
        if (!blocks.has(blockName)) {
          blocks.set(blockName, { elements: new Set(), lines: [] });
        }
        blocks.get(blockName).elements.add(suffix);
        blocks.get(blockName).lines.push(index + 1);
      }
    }

    // Check for &- violations (should be &__)
    if (ampersandHyphenPattern.test(line)) {
      nestingViolations.push({
        line: index + 1,
        violation: line.trim(),
      });
    }
  });

  return { blocks, nestingViolations };
}

/**
 * Check if elements are properly nested
 */
function checkNesting(content, blocks) {
  const errors = [];

  blocks.forEach((data, blockName) => {
    if (data.elements.size <= 1) {
      // Only one element, no nesting issue
      return;
    }

    // Check if the block uses & nesting
    // Use [\s\S]* to match across multiple lines including closing braces
    const blockPattern = new RegExp(`\\.${blockName}\\s*\\{[\\s\\S]*?&__`, 's');
    const usesNesting = blockPattern.test(content);

    if (!usesNesting) {
      // Multiple elements written independently without & nesting
      errors.push({
        block: blockName,
        elements: Array.from(data.elements),
        lines: data.lines,
      });
    }
  });

  return errors;
}

/**
 * Main check function
 */
function checkBEMNesting() {
  const objectDir = join(rootDir, 'src/scss/object');

  if (!statSync(objectDir).isDirectory()) {
    console.error(`${colors.red}Error: ${objectDir} not found${colors.reset}`);
    process.exit(1);
  }

  // Check all subdirectories: projects, components, layout, utility
  const scssFiles = getSCSSFiles(objectDir);
  let totalErrors = 0;
  let totalViolations = 0;
  const fileErrors = [];
  const fileViolations = [];

  console.log(`${colors.cyan}${colors.bold}Checking BEM nesting in ${scssFiles.length} files...${colors.reset}\n`);

  scssFiles.forEach(filePath => {
    const content = readFileSync(filePath, 'utf8');
    const { blocks, nestingViolations } = parseSCSSFile(content);
    const errors = checkNesting(content, blocks);

    if (errors.length > 0) {
      const relativePath = relative(rootDir, filePath);
      fileErrors.push({ filePath: relativePath, errors });
      totalErrors += errors.length;
    }

    if (nestingViolations.length > 0) {
      const relativePath = relative(rootDir, filePath);
      fileViolations.push({ filePath: relativePath, violations: nestingViolations });
      totalViolations += nestingViolations.length;
    }
  });

  // Display &- violations first (higher priority)
  if (totalViolations > 0) {
    console.log(`${colors.red}${colors.bold}✗ Found ${totalViolations} &- nesting violation(s) (MUST use &__ instead):${colors.reset}\n`);

    fileViolations.forEach(({ filePath, violations }) => {
      console.log(`${colors.red}❌ ${filePath}${colors.reset}`);

      violations.forEach(({ line, violation }) => {
        console.log(`   ${colors.yellow}Line ${line}: ${violation}${colors.reset}`);
        console.log(`   ${colors.cyan}→ &-xxx は禁止。&__xxx を使用してください${colors.reset}`);
        console.log('');
      });
    });
  }

  // Display top-level element errors
  if (totalErrors > 0) {
    console.log(`${colors.red}${colors.bold}✗ Found ${totalErrors} BEM nesting issue(s):${colors.reset}\n`);

    fileErrors.forEach(({ filePath, errors }) => {
      console.log(`${colors.red}❌ ${filePath}${colors.reset}`);

      errors.forEach(({ block, elements, lines }) => {
        console.log(`   ${colors.yellow}Block: ${block}${colors.reset}`);
        console.log(`   ${colors.yellow}独立した要素: ${elements.join(', ')}${colors.reset}`);
        console.log(`   ${colors.yellow}行番号: ${lines.join(', ')}${colors.reset}`);
        console.log(`   ${colors.cyan}→ .${block} { ${elements.map(e => `&${e} { }`).join(' ')} } の形式にしてください${colors.reset}`);
        console.log('');
      });
    });
  }

  // Display results
  if (totalErrors === 0 && totalViolations === 0) {
    console.log(`${colors.green}${colors.bold}✓ All BEM elements are properly nested!${colors.reset}\n`);
    process.exit(0);
  } else {
    console.log(`${colors.red}${colors.bold}Total: ${totalErrors + totalViolations} issue(s) found${colors.reset}`);
    console.log(`${colors.yellow}Please fix:${colors.reset}`);
    if (totalViolations > 0) {
      console.log(`${colors.yellow}  - ${totalViolations} &- violation(s) → use &__ instead${colors.reset}`);
    }
    if (totalErrors > 0) {
      console.log(`${colors.yellow}  - ${totalErrors} top-level element(s) → nest with &__${colors.reset}`);
    }
    console.log('');

    process.exit(1);
  }
}

// Run the checker
checkBEMNesting();
