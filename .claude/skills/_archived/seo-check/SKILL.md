---
name: seo-check
description: "Check SEO quality: JSON-LD structured data and heading hierarchy. Use when user says 'check SEO', 'validate JSON-LD', 'check headings', or before delivery."
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# SEO Check

## Overview

Validates SEO-critical elements that All in One SEO plugin doesn't cover:
- JSON-LD structured data (JobPosting, Organization)
- Heading hierarchy (h1-h6 structure)

Generates actionable reports for fixing SEO issues before delivery.

## Prerequisites

None. This skill can be run independently or integrated into `/qa check`.

## Usage

```bash
# Check all pages
/seo-check

# Check specific page
/seo-check page-about.php

# Check with detailed output
/seo-check --verbose

# Generate report only (no fixes)
/seo-check --report-only
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| file | No | Specific PHP file to check (default: all pages) |
| --verbose | No | Show detailed validation results |
| --report-only | No | Generate report without suggesting fixes |

## Processing Flow

```
SEO CHECK START
      │
      ▼
┌─────────────────────────────────────┐
│  Step 1: File Discovery              │
│  ├─ Glob: themes/*/pages/*.php      │
│  └─ Filter: page-*.php only         │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Step 2: JSON-LD Validation          │
│  ├─ 2-1. Extract JSON-LD blocks     │
│  ├─ 2-2. Validate JSON syntax       │
│  ├─ 2-3. Check required schema      │
│  │       ├─ JobPosting (求人ページ) │
│  │       └─ Organization (会社情報)  │
│  └─ 2-4. Validate required props    │
│          ├─ title, description      │
│          ├─ datePosted              │
│          └─ hiringOrganization      │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Step 3: Heading Structure Check    │
│  ├─ 3-1. Extract all headings       │
│  ├─ 3-2. Count h1 per page          │
│  │       └─ Error if > 1            │
│  ├─ 3-3. Check hierarchy            │
│  │       └─ Error if skip (h2→h4)   │
│  └─ 3-4. Check empty headings       │
│          └─ Error if text empty     │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Step 4: Report Generation           │
│  ├─ 4-1. Create summary             │
│  ├─ 4-2. Generate JSON report       │
│  │       └─ reports/seo-report.json │
│  └─ 4-3. Generate Markdown report   │
│          └─ reports/seo-report.md   │
└─────────────────────────────────────┘
      │
      ▼
    COMPLETE
```

## Step 1: File Discovery

### Target Files

```
themes/{{THEME_NAME}}/pages/page-*.php
```

### Implementation

```bash
# Using Glob tool
pattern="themes/*/pages/page-*.php"
```

## Step 2: JSON-LD Validation (Script Required)

**MUST** run validation script for deterministic checks:

```bash
bash .claude/skills/seo-check/scripts/validate-jsonld.sh {file}
```

Exit code handling:
- Exit 0 (PASS) → Continue
- Exit 1 (FAIL) → Report issues

### Detection Logic

1. **Extract JSON-LD blocks**
   ```regex
   <script type="application/ld\+json">(.*?)</script>
   ```

2. **Validate JSON syntax**
   ```bash
   echo "$json_content" | jq empty
   ```

3. **Check @type**
   - 求人ページ: JobPosting required
   - 会社情報: Organization required

4. **Validate required properties**

   **JobPosting:**
   | Property | Required | Validation |
   |----------|----------|------------|
   | title | ✅ | Non-empty string |
   | description | ✅ | Min 50 chars |
   | datePosted | ✅ | ISO 8601 format |
   | hiringOrganization | ✅ | Object with name |
   | jobLocation | ✅ | Object with address |

   **Organization:**
   | Property | Required | Validation |
   |----------|----------|------------|
   | name | ✅ | Non-empty string |
   | url | ✅ | Valid URL |
   | logo | Recommended | Valid URL |
   | address | Recommended | Object |

### Error Examples

```
❌ JSON-LD validation failed: page-requirements.php
   - Missing @type: "JobPosting"
   - Missing required property: "datePosted"
   - Invalid datePosted format: "2024/01/01" (expected ISO 8601)
```

## Step 3: Heading Structure Check (Script Required)

**MUST** run heading check script:

```bash
bash .claude/skills/seo-check/scripts/check-headings.sh {file}
```

Exit code handling:
- Exit 0 (PASS) → Continue
- Exit 1 (FAIL) → Report issues

### Validation Rules

| Rule | Severity | Description |
|------|----------|-------------|
| h1 count = 1 | ERROR | Exactly one h1 per page |
| No hierarchy skip | ERROR | h2→h3→h4 (no h2→h4) |
| No empty headings | ERROR | Heading must have text |

### Detection Logic

1. **Extract headings**
   ```regex
   <h([1-6])[^>]*>(.*?)</h\1>
   ```

2. **Count h1**
   ```bash
   h1_count=$(grep -o '<h1[^>]*>' file | wc -l)
   if [ "$h1_count" -ne 1 ]; then
     echo "ERROR: h1 count = $h1_count (expected 1)"
   fi
   ```

3. **Check hierarchy**
   ```bash
   # Extract heading levels: 1, 2, 2, 3, 2, 4
   # Detect skip: 2 → 4 (skipped 3)
   ```

4. **Check empty headings**
   ```regex
   <h[1-6][^>]*>\s*</h[1-6]>
   ```

### Error Examples

```
❌ Heading structure issues: page-about.php

1. Multiple h1 detected (line 15, 47)
   → Only one h1 per page is allowed

2. Hierarchy skip (line 32)
   → h2 (line 25) → h4 (line 32)
   → Insert h3 between them

3. Empty heading (line 58)
   → <h3 class="c-heading"></h3>
   → Add text content
```

## Step 4: Report Generation

### JSON Report Structure

```json
{
  "timestamp": "2026-02-05T10:30:00Z",
  "summary": {
    "totalFiles": 15,
    "passedFiles": 12,
    "failedFiles": 3,
    "totalIssues": 8,
    "jsonldIssues": 5,
    "headingIssues": 3
  },
  "issues": [
    {
      "type": "jsonld",
      "severity": "error",
      "file": "themes/{{THEME_NAME}}/pages/page-requirements.php",
      "line": 45,
      "message": "Missing required property: datePosted",
      "context": "JobPosting schema",
      "fix": "Add datePosted in ISO 8601 format (e.g., \"2024-01-01T00:00:00+09:00\")"
    },
    {
      "type": "heading",
      "severity": "error",
      "file": "themes/{{THEME_NAME}}/pages/page-about.php",
      "line": 32,
      "message": "Heading hierarchy skip: h2 → h4",
      "context": "h2 at line 25, h4 at line 32",
      "fix": "Insert h3 between lines 25-32"
    }
  ],
  "byFile": {
    "page-requirements.php": {
      "passed": false,
      "issues": 3
    }
  }
}
```

### Markdown Report

```markdown
# SEO チェックレポート

**実行日時**: 2026-02-05 10:30:00
**チェック対象**: 15ファイル

---

## 📊 サマリー

| 項目 | 値 |
|------|-----|
| チェックファイル | 15 |
| 成功 | 12 |
| 失敗 | 3 |
| **総問題数** | **8** |
| JSON-LD問題 | 5 |
| 見出し構造問題 | 3 |

---

## ❌ 問題一覧

### page-requirements.php (3件)

#### JSON-LD

- **[ERROR]** Line 45: Missing required property: datePosted
  - Context: JobPosting schema
  - Fix: Add datePosted in ISO 8601 format

#### 見出し構造

- **[ERROR]** Line 32: Heading hierarchy skip: h2 → h4
  - Fix: Insert h3 between lines 25-32

---

## ✅ 成功ファイル (12件)

- page-home.php
- page-about.php
- ...

---

**次のアクション**:

1. JSON-LD問題を修正
2. 見出し階層を修正
3. /seo-check で再検証
```

## Integration with /qa

This skill is automatically called by `/qa check`:

```typescript
// scripts/qa/check.ts
const seoResult = runSeoCheck();
spec.categories.seo = seoResult;
```

## Error Handling

| Error Type | Detection | Auto Recovery | Fallback |
|------------|-----------|---------------|----------|
| Invalid JSON | jq parse fail | - | Report syntax error |
| File not found | Glob empty | - | Warning message |
| Script exec fail | Exit code 127 | - | Show script path |
| Empty heading | Regex match | - | Report line number |

## Output Files

| File | Purpose |
|------|---------|
| `reports/seo-check-report.json` | Structured report for automation |
| `reports/seo-check-report.md` | Human-readable report |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/skills/seo-check/scripts/validate-jsonld.sh` | JSON-LD validation script |
| `.claude/skills/seo-check/scripts/check-headings.sh` | Heading structure check script |
| `scripts/seo/check.ts` | Main check orchestrator (TypeScript) |
| `scripts/qa/check.ts` | QA integration |

## Examples

### Basic Check

```bash
/seo-check
```

Output:
```
🔍 SEOチェック開始...

✅ page-home.php: OK
✅ page-about.php: OK
❌ page-requirements.php: 3 issues
   - Missing JSON-LD property: datePosted
   - Heading hierarchy skip: h2 → h4
   - Empty heading at line 58

📊 総問題数: 3
📄 詳細: reports/seo-check-report.md
```

### Check Specific File

```bash
/seo-check themes/{{THEME_NAME}}/pages/page-requirements.php
```

### Verbose Mode

```bash
/seo-check --verbose
```

Shows detailed validation results for each check.

## Troubleshooting

### Error: "jq: command not found"

**Cause**: jq is not installed.

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq
```

### Error: "No JSON-LD found"

**Cause**: Page doesn't have structured data yet.

**Solution**:
1. Add JSON-LD script tag to PHP template
2. Example for JobPosting:
   ```php
   <script type="application/ld+json">
   {
     "@context": "https://schema.org",
     "@type": "JobPosting",
     "title": "<?php echo esc_js(get_field('job_title')); ?>",
     "datePosted": "<?php echo esc_js(get_field('posted_date')); ?>",
     "hiringOrganization": {
       "@type": "Organization",
       "name": "会社名"
     }
   }
   </script>
   ```

### Error: "Multiple h1 found"

**Cause**: Page has multiple h1 elements.

**Solution**:
1. Keep only one h1 (page title)
2. Change other h1 to h2 or appropriate level

### Error: "Heading hierarchy skip"

**Cause**: Heading level skipped (e.g., h2 → h4).

**Solution**:
1. Insert missing level (h3 in this case)
2. Or change h4 to h3

## Best Practices

### JSON-LD

1. **Use PHP variables for dynamic content**
   ```php
   "datePosted": "<?php echo esc_js(get_field('posted_date')); ?>"
   ```

2. **Validate with Google Rich Results Test**
   - https://search.google.com/test/rich-results

3. **Use ISO 8601 format for dates**
   ```php
   "datePosted": "2024-01-01T00:00:00+09:00"
   ```

### Heading Structure

1. **One h1 per page** (page title)
2. **Sequential hierarchy** (h2 → h3 → h4, no skips)
3. **Meaningful text** (not empty, not "Title")

---

**Version**: 1.0.0
**Created**: 2026-02-05
**Updated**: 2026-02-05
