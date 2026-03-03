#!/usr/bin/env node
/**
 * QA統合チェックスクリプト
 *
 * 全品質チェックを実行し、構造化されたqa-spec.jsonを生成
 * エージェントがこのspecを読んで修正作業を行う
 *
 * Usage:
 *   npm run qa:check
 *   npm run qa:check -- --base-url http://localhost:8000
 *   npm run qa:check -- --skip-crawl  # クローラーをスキップ（高速）
 */

import { execSync, spawnSync } from "child_process";
import fs from "fs";
import path from "path";
import { detectThemeName } from "../lib/detect-theme.js";

const THEME_NAME = detectThemeName();

const DEFAULT_BASE_URL = "http://localhost:8000";
const REPORTS_DIR = path.join(process.cwd(), "reports");

// ============================================
// 型定義
// ============================================

interface Issue {
  type: "error" | "warning";
  category: string;
  file?: string;
  line?: number;
  message: string;
  rule?: string;
  autoFixable: boolean;
}

interface CheckResult {
  name: string;
  command: string;
  success: boolean;
  duration: number;
  issues: Issue[];
}

interface QASpec {
  timestamp: string;
  baseUrl: string;
  summary: {
    totalChecks: number;
    passedChecks: number;
    failedChecks: number;
    totalIssues: number;
    errorCount: number;
    warningCount: number;
    autoFixableCount: number;
  };
  categories: {
    build: CheckResult;
    lint: {
      scss: CheckResult;
      js: CheckResult;
      php: CheckResult;
    };
    links: CheckResult;
    images: CheckResult;
    templates: CheckResult;
    html: {
      validate: CheckResult;
      semantic: CheckResult;
    };
    accessibility: {
      alt: CheckResult;
    };
  };
  issuesByFile: Record<string, Issue[]>;
  issuesByCategory: Record<string, Issue[]>;
}

// ============================================
// ユーティリティ関数
// ============================================

function ensureReportsDir(): void {
  if (!fs.existsSync(REPORTS_DIR)) {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
  }
}

function log(message: string, type: "info" | "success" | "error" | "section" = "info"): void {
  const icons = {
    info: "🔍",
    success: "✅",
    error: "❌",
    section: "═",
  };

  if (type === "section") {
    console.log(`\n${"═".repeat(70)}`);
    console.log(`  ${message}`);
    console.log(`${"═".repeat(70)}\n`);
  } else {
    console.log(`${icons[type]} ${message}`);
  }
}

/**
 * BEMネストエラーを解析してIssueに変換
 *
 * エラーフォーマット例:
 * ❌ src/scss/object/projects/404/_p-404-actions.scss
 *    Block: p-404
 *    独立した要素: __actions, __button
 *    行番号: 7, 19
 *    → .p-404 { &__actions { } } の形式にしてください
 */
function parseBemErrors(output: string): Issue[] {
  const issues: Issue[] = [];

  // ANSI カラーコードを除去
  const cleanOutput = output.replace(/\x1b\[[0-9;]*m/g, "");

  // BEM エラーブロックを抽出（❌ から次の ❌ または文末まで）
  const errorBlocks = cleanOutput.split(/(?=❌ src\/scss\/)/);

  for (const block of errorBlocks) {
    if (!block.includes("❌ src/scss/")) continue;

    // ファイルパスを抽出
    const fileMatch = block.match(/❌ (src\/scss\/[^\s\n]+\.scss)/);
    if (!fileMatch) continue;
    const file = fileMatch[1];

    // Block名を抽出
    const blockMatch = block.match(/Block: ([^\s\n]+)/);
    const blockName = blockMatch ? blockMatch[1] : "unknown";

    // 独立した要素を抽出
    const elementsMatch = block.match(/独立した要素: ([^\n]+)/);
    const elements = elementsMatch ? elementsMatch[1].trim() : "";

    // 行番号を抽出
    const linesMatch = block.match(/行番号: ([^\n]+)/);
    const lineNumbers = linesMatch ? linesMatch[1].trim() : "";
    const firstLine = lineNumbers.split(",")[0]?.trim();

    // Issue作成
    issues.push({
      type: "error",
      category: "lint-scss",
      file,
      line: firstLine ? parseInt(firstLine, 10) : undefined,
      message: `BEM要素が独立して定義されています: ${blockName} (${elements})`,
      rule: "bem-nesting-required",
      autoFixable: true, // 手動修正推奨（SCSSファイル構造の変更が必要）
    });
  }

  return issues;
}

// ============================================
// チェック実行関数
// ============================================

function runBuildCheck(): CheckResult {
  const startTime = Date.now();
  log("ビルドチェック実行中...");

  try {
    execSync("npm run build", { stdio: "pipe", cwd: process.cwd() });
    return {
      name: "ビルド",
      command: "npm run build",
      success: true,
      duration: Date.now() - startTime,
      issues: [],
    };
  } catch (error: unknown) {
    const stderr =
      error instanceof Error && "stderr" in error
        ? String((error as { stderr: unknown }).stderr)
        : "";
    return {
      name: "ビルド",
      command: "npm run build",
      success: false,
      duration: Date.now() - startTime,
      issues: [
        {
          type: "error",
          category: "build",
          message: `ビルドエラー: ${stderr.slice(0, 500)}`,
          autoFixable: true,
        },
      ],
    };
  }
}

function runLintCheck(type: "scss" | "js" | "php"): CheckResult {
  const startTime = Date.now();
  const commandMap = {
    scss: "npm run lint:css",
    js: "npm run lint:js",
    php: "npm run lint:php",
  };
  const command = commandMap[type];
  log(`Lint (${type.toUpperCase()}) チェック実行中...`);

  const result = spawnSync("npm", ["run", `lint:${type === "scss" ? "css" : type}`], {
    cwd: process.cwd(),
    encoding: "utf-8",
    shell: true,
  });

  const output = result.stdout + result.stderr;
  const issues: Issue[] = [];

  // BEM nesting errors (SCSS only)
  if (type === "scss") {
    const bemIssues = parseBemErrors(output);
    issues.push(...bemIssues);
  }

  if (type === "php") {
    // phpcs の出力をパース
    const lines = output.split("\n");
    let currentFile = "";

    for (const line of lines) {
      // ファイルパスの検出 (例: FILE: /path/to/file.php)
      const fileMatch = line.match(/^FILE:\s+(.+\.php)$/);
      if (fileMatch) {
        currentFile = fileMatch[1].replace(new RegExp(`^.*/(themes/${THEME_NAME}/.+)$`), "$1");
        continue;
      }

      // エラー/警告行の検出 (例: 12 | ERROR | Missing doc comment)
      const issueMatch = line.match(/^\s*(\d+)\s*\|\s*(ERROR|WARNING)\s*\|\s*(.+)$/);
      if (issueMatch && currentFile) {
        const [, lineNum, severity, message] = issueMatch;
        issues.push({
          type: severity === "ERROR" ? "error" : "warning",
          category: "lint-php",
          file: currentFile,
          line: parseInt(lineNum, 10),
          message: message.trim(),
          autoFixable: message.includes("[x]") || message.toLowerCase().includes("fixable"),
        });
      }
    }
  } else {
    // Stylelint/ESLint の出力をパース
    const lines = output.split("\n");
    let currentFile = "";

    for (const line of lines) {
      // ファイルパスの検出
      const fileMatch = line.match(/^(src\/[^\s]+\.(scss|js|ts))$/);
      if (fileMatch) {
        currentFile = fileMatch[1];
        continue;
      }

      // エラー/警告行の検出
      const issueMatch = line.match(/^\s*(\d+):(\d+)\s+(✖|⚠|error|warning)\s+(.+?)\s{2,}(\S+)?$/);
      if (issueMatch && currentFile) {
        const [, lineNum, , severity, message, rule] = issueMatch;
        issues.push({
          type: severity.includes("✖") || severity === "error" ? "error" : "warning",
          category: type === "scss" ? "lint-scss" : "lint-js",
          file: currentFile,
          line: parseInt(lineNum, 10),
          message: message.trim(),
          rule: rule || undefined,
          autoFixable:
            message.includes("--fix") ||
            ["quotes", "indent", "semi"].some((r) => rule?.includes(r)),
        });
      }
    }
  }

  return {
    name: `Lint (${type.toUpperCase()})`,
    command,
    success: result.status === 0,
    duration: Date.now() - startTime,
    issues,
  };
}

function runLinksCheck(baseUrl: string, skipCrawl: boolean): CheckResult {
  const startTime = Date.now();
  log("リンクチェック実行中...");

  const issues: Issue[] = [];

  // 静的解析
  try {
    execSync("npm run check:links", { stdio: "pipe", cwd: process.cwd() });
  } catch {
    // エラーでも続行
  }

  // レポート読み込み
  const staticReportPath = path.join(REPORTS_DIR, "link-check-report.json");
  if (fs.existsSync(staticReportPath)) {
    try {
      const report = JSON.parse(fs.readFileSync(staticReportPath, "utf-8"));
      if (report.issues) {
        for (const issue of report.issues) {
          issues.push({
            type: "error",
            category: "links",
            file: issue.file,
            line: issue.line,
            message: `リンク切れ: ${issue.url} (${issue.status || "not found"})`,
            autoFixable: false,
          });
        }
      }
    } catch {
      // パースエラーは無視
    }
  }

  // クローラーベース（オプション）
  if (!skipCrawl) {
    try {
      execSync(`npm run check:links:crawl -- --base-url ${baseUrl}`, {
        stdio: "pipe",
        cwd: process.cwd(),
        timeout: 120000,
      });
    } catch {
      // タイムアウトやエラーでも続行
    }

    const crawlReportPath = path.join(REPORTS_DIR, "link-crawl-report.json");
    if (fs.existsSync(crawlReportPath)) {
      try {
        const report = JSON.parse(fs.readFileSync(crawlReportPath, "utf-8"));
        if (report.brokenLinks) {
          for (const link of report.brokenLinks) {
            // 重複チェック
            const exists = issues.some((i) => i.message.includes(link.url));
            if (!exists) {
              issues.push({
                type: "error",
                category: "links",
                file: link.foundOn,
                message: `リンク切れ: ${link.url} (${link.status})`,
                autoFixable: true,
              });
            }
          }
        }
      } catch {
        // パースエラーは無視
      }
    }
  }

  return {
    name: "リンクチェック",
    command: "npm run check:links",
    success: issues.length === 0,
    duration: Date.now() - startTime,
    issues,
  };
}

function runImagesCheck(baseUrl: string): CheckResult {
  const startTime = Date.now();
  log("画像チェック実行中...");

  const issues: Issue[] = [];

  try {
    execSync(`npm run check:images -- --base-url ${baseUrl}`, {
      stdio: "pipe",
      cwd: process.cwd(),
      timeout: 60000,
    });
  } catch {
    // エラーでも続行
  }

  const reportPath = path.join(REPORTS_DIR, "image-check-report.json");
  if (fs.existsSync(reportPath)) {
    try {
      const report = JSON.parse(fs.readFileSync(reportPath, "utf-8"));
      if (report.missingImages) {
        for (const img of report.missingImages) {
          issues.push({
            type: "error",
            category: "images",
            file: img.referencedIn,
            message: `画像404: ${img.src}`,
            autoFixable: true,
          });
        }
      }
    } catch {
      // パースエラーは無視
    }
  }

  return {
    name: "画像チェック",
    command: "npm run check:images",
    success: issues.length === 0,
    duration: Date.now() - startTime,
    issues,
  };
}

function runTemplatesCheck(): CheckResult {
  const startTime = Date.now();
  log("テンプレート品質チェック実行中...");

  const issues: Issue[] = [];

  try {
    execSync("npm run check:templates", { stdio: "pipe", cwd: process.cwd() });
  } catch {
    // エラーでも続行
  }

  const reportPath = path.join(REPORTS_DIR, "template-quality-report.json");
  if (fs.existsSync(reportPath)) {
    try {
      const report = JSON.parse(fs.readFileSync(reportPath, "utf-8"));
      if (report.issues) {
        for (const issue of report.issues) {
          issues.push({
            type: issue.severity === "error" ? "error" : "warning",
            category: "templates",
            file: issue.file,
            line: issue.line,
            message: issue.message,
            rule: issue.rule,
            autoFixable: true,
          });
        }
      }
    } catch {
      // パースエラーは無視
    }
  }

  return {
    name: "テンプレート品質",
    command: "npm run check:templates",
    success: issues.length === 0,
    duration: Date.now() - startTime,
    issues,
  };
}

function runHtmlValidateCheck(): CheckResult {
  const startTime = Date.now();
  log("HTML構造バリデーション実行中...");

  const result = spawnSync("npm", ["run", "check:html"], {
    cwd: process.cwd(),
    encoding: "utf-8",
    shell: true,
  });

  const output = result.stdout + result.stderr;
  const issues: Issue[] = [];

  // html-validate の出力をパース
  // Format: themes/${THEME_NAME}/pages/page-top.php
  //         12:5  error  Element <img> is missing required "alt" attribute  element-required-attributes
  const lines = output.split("\n");
  let currentFile = "";

  for (const line of lines) {
    // ファイルパスの検出
    const fileMatch = line.match(new RegExp(`^(themes/${THEME_NAME}/.+\\.php)$`));
    if (fileMatch) {
      currentFile = fileMatch[1];
      continue;
    }

    // エラー/警告の検出
    const issueMatch = line.match(/^\s*(\d+):(\d+)\s+(error|warning)\s+(.+?)\s{2,}(\S+)?$/);
    if (issueMatch && currentFile) {
      const [, lineNum, , severity, message, rule] = issueMatch;
      issues.push({
        type: severity === "error" ? "error" : "warning",
        category: "html-validate",
        file: currentFile,
        line: parseInt(lineNum, 10),
        message: message.trim(),
        rule: rule || undefined,
        autoFixable: true, // HTML構造は手動修正が必要
      });
    }
  }

  return {
    name: "HTML構造バリデーション",
    command: "npm run check:html",
    success: result.status === 0,
    duration: Date.now() - startTime,
    issues,
  };
}

function runHtmlSemanticCheck(): CheckResult {
  const startTime = Date.now();
  log("セマンティック構造チェック実行中...");

  const issues: Issue[] = [];

  try {
    execSync("npm run check:html:semantic", { stdio: "pipe", cwd: process.cwd() });
  } catch {
    // エラーでも続行
  }

  const reportPath = path.join(REPORTS_DIR, "html-semantic-report.json");
  if (fs.existsSync(reportPath)) {
    try {
      const report = JSON.parse(fs.readFileSync(reportPath, "utf-8"));
      if (report.issues) {
        for (const issue of report.issues) {
          issues.push({
            type: issue.severity === "error" ? "error" : "warning",
            category: "html-semantic",
            file: issue.file,
            line: issue.line,
            message: issue.message,
            autoFixable: true, // セマンティック構造は手動修正が必要
          });
        }
      }
    } catch {
      // パースエラーは無視
    }
  }

  return {
    name: "セマンティック構造",
    command: "npm run check:html:semantic",
    success: issues.length === 0,
    duration: Date.now() - startTime,
    issues,
  };
}

function runAltAttributeCheck(): CheckResult {
  const startTime = Date.now();
  log("alt属性詳細チェック実行中...");

  const issues: Issue[] = [];

  try {
    execSync("npm run check:alt", { stdio: "pipe", cwd: process.cwd() });
  } catch {
    // エラーでも続行
  }

  const reportPath = path.join(REPORTS_DIR, "alt-attribute-report.json");
  if (fs.existsSync(reportPath)) {
    try {
      const report = JSON.parse(fs.readFileSync(reportPath, "utf-8"));
      if (report.issues) {
        for (const issue of report.issues) {
          // alt-attribute.ts の AltIssue 型に合わせる
          issues.push({
            type: issue.severity === "error" ? "error" : "warning",
            category: "alt-attribute",
            file: issue.file,
            line: issue.line,
            message: issue.message,
            rule: issue.type, // 'missing', 'empty', 'meaningless', 'filename'
            autoFixable: false, // alt属性は内容理解が必要なため手動修正
          });
        }
      }
    } catch {
      // パースエラーは無視
    }
  }

  return {
    name: "alt属性詳細",
    command: "npm run check:alt",
    success: issues.length === 0,
    duration: Date.now() - startTime,
    issues,
  };
}

// ============================================
// QA Spec 生成
// ============================================

function generateQASpec(
  buildResult: CheckResult,
  scssResult: CheckResult,
  jsResult: CheckResult,
  phpResult: CheckResult,
  linksResult: CheckResult,
  imagesResult: CheckResult,
  templatesResult: CheckResult,
  htmlValidateResult: CheckResult,
  htmlSemanticResult: CheckResult,
  altAttributeResult: CheckResult,
  baseUrl: string
): QASpec {
  const allIssues = [
    ...buildResult.issues,
    ...scssResult.issues,
    ...jsResult.issues,
    ...phpResult.issues,
    ...linksResult.issues,
    ...imagesResult.issues,
    ...templatesResult.issues,
    ...htmlValidateResult.issues,
    ...htmlSemanticResult.issues,
    ...altAttributeResult.issues,
  ];

  // ファイル別に分類
  const issuesByFile: Record<string, Issue[]> = {};
  for (const issue of allIssues) {
    const file = issue.file || "_global";
    if (!issuesByFile[file]) {
      issuesByFile[file] = [];
    }
    issuesByFile[file].push(issue);
  }

  // カテゴリ別に分類
  const issuesByCategory: Record<string, Issue[]> = {};
  for (const issue of allIssues) {
    if (!issuesByCategory[issue.category]) {
      issuesByCategory[issue.category] = [];
    }
    issuesByCategory[issue.category].push(issue);
  }

  const checks = [
    buildResult,
    scssResult,
    jsResult,
    phpResult,
    linksResult,
    imagesResult,
    templatesResult,
    htmlValidateResult,
    htmlSemanticResult,
    altAttributeResult,
  ];

  return {
    timestamp: new Date().toISOString(),
    baseUrl,
    summary: {
      totalChecks: checks.length,
      passedChecks: checks.filter((c) => c.success).length,
      failedChecks: checks.filter((c) => !c.success).length,
      totalIssues: allIssues.length,
      errorCount: allIssues.filter((i) => i.type === "error").length,
      warningCount: allIssues.filter((i) => i.type === "warning").length,
      autoFixableCount: allIssues.filter((i) => i.autoFixable).length,
    },
    categories: {
      build: buildResult,
      lint: {
        scss: scssResult,
        js: jsResult,
        php: phpResult,
      },
      links: linksResult,
      images: imagesResult,
      templates: templatesResult,
      html: {
        validate: htmlValidateResult,
        semantic: htmlSemanticResult,
      },
      accessibility: {
        alt: altAttributeResult,
      },
    },
    issuesByFile,
    issuesByCategory,
  };
}

// ============================================
// Markdown レポート生成
// ============================================

function generateMarkdownReport(spec: QASpec): string {
  const { summary, categories } = spec;

  let md = `# QA チェックレポート

**実行日時**: ${new Date(spec.timestamp).toLocaleString("ja-JP")}
**ベースURL**: ${spec.baseUrl}

---

## 📊 サマリー

| 項目 | 値 |
|------|-----|
| チェック項目 | ${summary.totalChecks} |
| 成功 | ${summary.passedChecks} |
| 失敗 | ${summary.failedChecks} |
| **総問題数** | **${summary.totalIssues}** |
| エラー | ${summary.errorCount} |
| 警告 | ${summary.warningCount} |
| 自動修正可能 | ${summary.autoFixableCount} |

---

## ✅ チェック結果

| チェック項目 | ステータス | 問題数 | 実行時間 |
|-------------|:--------:|:------:|:--------:|
| ビルド | ${categories.build.success ? "✅" : "❌"} | ${categories.build.issues.length} | ${(categories.build.duration / 1000).toFixed(1)}s |
| Lint (SCSS) | ${categories.lint.scss.success ? "✅" : "❌"} | ${categories.lint.scss.issues.length} | ${(categories.lint.scss.duration / 1000).toFixed(1)}s |
| Lint (JS) | ${categories.lint.js.success ? "✅" : "❌"} | ${categories.lint.js.issues.length} | ${(categories.lint.js.duration / 1000).toFixed(1)}s |
| Lint (PHP) | ${categories.lint.php.success ? "✅" : "❌"} | ${categories.lint.php.issues.length} | ${(categories.lint.php.duration / 1000).toFixed(1)}s |
| リンク | ${categories.links.success ? "✅" : "❌"} | ${categories.links.issues.length} | ${(categories.links.duration / 1000).toFixed(1)}s |
| 画像 | ${categories.images.success ? "✅" : "❌"} | ${categories.images.issues.length} | ${(categories.images.duration / 1000).toFixed(1)}s |
| テンプレート | ${categories.templates.success ? "✅" : "❌"} | ${categories.templates.issues.length} | ${(categories.templates.duration / 1000).toFixed(1)}s |
| HTML構造 | ${categories.html.validate.success ? "✅" : "❌"} | ${categories.html.validate.issues.length} | ${(categories.html.validate.duration / 1000).toFixed(1)}s |
| セマンティック | ${categories.html.semantic.success ? "✅" : "❌"} | ${categories.html.semantic.issues.length} | ${(categories.html.semantic.duration / 1000).toFixed(1)}s |
| alt属性詳細 | ${categories.accessibility.alt.success ? "✅" : "❌"} | ${categories.accessibility.alt.issues.length} | ${(categories.accessibility.alt.duration / 1000).toFixed(1)}s |

---

## 🔧 カテゴリ別問題

`;

  // カテゴリ別の問題一覧
  for (const [category, issues] of Object.entries(spec.issuesByCategory)) {
    if (issues.length === 0) continue;

    md += `### ${category} (${issues.length}件)\n\n`;

    const errors = issues.filter((i) => i.type === "error");
    const warnings = issues.filter((i) => i.type === "warning");

    if (errors.length > 0) {
      md += `**エラー (${errors.length}件)**\n\n`;
      for (const issue of errors.slice(0, 20)) {
        const location = issue.file ? `\`${issue.file}${issue.line ? `:${issue.line}` : ""}\`` : "";
        const fixable = issue.autoFixable ? " 🔧" : "";
        md += `- ${location} ${issue.message}${fixable}\n`;
      }
      if (errors.length > 20) {
        md += `- ... 他 ${errors.length - 20} 件\n`;
      }
      md += "\n";
    }

    if (warnings.length > 0) {
      md += `**警告 (${warnings.length}件)**\n\n`;
      for (const issue of warnings.slice(0, 10)) {
        const location = issue.file ? `\`${issue.file}${issue.line ? `:${issue.line}` : ""}\`` : "";
        md += `- ${location} ${issue.message}\n`;
      }
      if (warnings.length > 10) {
        md += `- ... 他 ${warnings.length - 10} 件\n`;
      }
      md += "\n";
    }
  }

  md += `---

## 📋 次のアクション

`;

  if (summary.autoFixableCount > 0) {
    md += `### 自動修正可能 (${summary.autoFixableCount}件)

\`\`\`bash
npm run qa:fix
\`\`\`

`;
  }

  if (summary.totalIssues - summary.autoFixableCount > 0) {
    md += `### 手動修正が必要 (${summary.totalIssues - summary.autoFixableCount}件)

詳細は \`reports/qa-spec.json\` を確認してください。

`;
  }

  if (summary.totalIssues === 0) {
    md += `🎉 **問題なし！納品準備完了です。**\n`;
  }

  md += `
---

**生成**: ${new Date().toLocaleString("ja-JP")}
`;

  return md;
}

// ============================================
// メイン処理
// ============================================

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const baseUrlIndex = args.indexOf("--base-url");
  const baseUrl =
    baseUrlIndex !== -1 && args[baseUrlIndex + 1] ? args[baseUrlIndex + 1] : DEFAULT_BASE_URL;
  const skipCrawl = args.includes("--skip-crawl");

  log("QA統合チェック開始", "section");
  log(`ベースURL: ${baseUrl}`);
  if (skipCrawl) {
    log("クローラーをスキップします");
  }

  ensureReportsDir();

  // Phase 1: 全チェック実行
  log("Phase 1: チェック実行", "section");

  const buildResult = runBuildCheck();
  log(
    buildResult.success ? "ビルド: 成功" : "ビルド: 失敗",
    buildResult.success ? "success" : "error"
  );

  const scssResult = runLintCheck("scss");
  log(`Lint (SCSS): ${scssResult.issues.length}件の問題`, scssResult.success ? "success" : "error");

  const jsResult = runLintCheck("js");
  log(`Lint (JS): ${jsResult.issues.length}件の問題`, jsResult.success ? "success" : "error");

  const phpResult = runLintCheck("php");
  log(`Lint (PHP): ${phpResult.issues.length}件の問題`, phpResult.success ? "success" : "error");

  const linksResult = runLinksCheck(baseUrl, skipCrawl);
  log(`リンク: ${linksResult.issues.length}件の問題`, linksResult.success ? "success" : "error");

  const imagesResult = runImagesCheck(baseUrl);
  log(`画像: ${imagesResult.issues.length}件の問題`, imagesResult.success ? "success" : "error");

  const templatesResult = runTemplatesCheck();
  log(
    `テンプレート: ${templatesResult.issues.length}件の問題`,
    templatesResult.success ? "success" : "error"
  );

  const htmlValidateResult = runHtmlValidateCheck();
  log(
    `HTML構造: ${htmlValidateResult.issues.length}件の問題`,
    htmlValidateResult.success ? "success" : "error"
  );

  const htmlSemanticResult = runHtmlSemanticCheck();
  log(
    `セマンティック: ${htmlSemanticResult.issues.length}件の問題`,
    htmlSemanticResult.success ? "success" : "error"
  );

  const altAttributeResult = runAltAttributeCheck();
  log(
    `alt属性詳細: ${altAttributeResult.issues.length}件の問題`,
    altAttributeResult.success ? "success" : "error"
  );

  // Phase 2: QA Spec 生成
  log("Phase 2: レポート生成", "section");

  const spec = generateQASpec(
    buildResult,
    scssResult,
    jsResult,
    phpResult,
    linksResult,
    imagesResult,
    templatesResult,
    htmlValidateResult,
    htmlSemanticResult,
    altAttributeResult,
    baseUrl
  );

  // JSON出力
  const specPath = path.join(REPORTS_DIR, "qa-spec.json");
  fs.writeFileSync(specPath, JSON.stringify(spec, null, 2));
  log(`qa-spec.json を生成: ${specPath}`, "success");

  // Markdown出力
  const mdReport = generateMarkdownReport(spec);
  const mdPath = path.join(REPORTS_DIR, "qa-report.md");
  fs.writeFileSync(mdPath, mdReport);
  log(`qa-report.md を生成: ${mdPath}`, "success");

  // 最終サマリー
  log("最終結果", "section");

  const { summary } = spec;
  console.log(`
  チェック項目:     ${summary.totalChecks}
  成功:            ${summary.passedChecks}
  失敗:            ${summary.failedChecks}

  総問題数:        ${summary.totalIssues}
  ├─ エラー:       ${summary.errorCount}
  ├─ 警告:         ${summary.warningCount}
  └─ 自動修正可能: ${summary.autoFixableCount}
  `);

  if (summary.totalIssues === 0) {
    log("🎉 問題なし！納品準備完了です。", "success");
  } else {
    log(`⚠️  ${summary.totalIssues}件の問題があります。`, "error");
    log("詳細は reports/qa-report.md を確認してください。");
  }

  // 問題があれば終了コード1
  if (summary.errorCount > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error("エラーが発生しました:", error);
  process.exit(1);
});
