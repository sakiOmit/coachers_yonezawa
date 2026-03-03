---
name: placeholder-detector
description: "Detect and analyze multiple placeholder formats in the project and identify inconsistencies for template quality assurance."
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
context: fork
agent: general-purpose
---

# Placeholder Detector

## Overview

A skill that detects multiple placeholder formats ({{PLACEHOLDER}} and {PLACEHOLDER}) in the project, analyzes their usage patterns, identifies inconsistencies, and outputs reports for template quality checks.

### Background

When converting a project into a reusable template, placeholders are essential for customization points. However, inconsistent placeholder formats cause:
- Template users to miss required replacements
- Errors during automated replacement scripts
- Maintenance difficulties

This skill prevents these issues by ensuring placeholder consistency before template distribution.

## Usage

```
/placeholder-detector
```

Or

```
/placeholder-detector --format {{}} --path src/
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| --format | No | Target format: `{{}}`, `{}`, `both` (default: both) |
| --path | No | Target directory path (default: project root) |
| --exclude | No | Exclude pattern (default: node_modules, .git, dist) |
| --output | No | Output path (default: stdout) |
| --strict | No | Strict mode: exit with error if inconsistencies found |

## Output

### Analysis Report (JSON Format)

```json
{
  "metadata": {
    "project_root": "/path/to/project",
    "scan_path": ".",
    "timestamp": "2026-01-30T15:00:00Z"
  },
  "formats": {
    "double_brace": {
      "count": 15,
      "files": 8,
      "placeholders": [
        {
          "name": "THEME_NAME",
          "occurrences": 12,
          "locations": [
            "package.json:2",
            "vite.config.js:10",
            "README.md:5"
          ]
        }
      ]
    },
    "single_brace": {
      "count": 3,
      "files": 2,
      "placeholders": [
        {
          "name": "PACKAGE_NAME",
          "occurrences": 3,
          "locations": [
            "composer.json:3",
            "composer.json:4"
          ]
        }
      ]
    }
  },
  "inconsistencies": {
    "found": true,
    "mixed_formats": [
      {
        "placeholder": "THEME_NAME",
        "formats": ["{{THEME_NAME}}", "{THEME_NAME}"],
        "locations": {
          "{{}}": ["package.json:2"],
          "{}": ["composer.json:5"]
        }
      }
    ]
  },
  "statistics": {
    "total_placeholders": 18,
    "unique_placeholders": 5,
    "files_with_placeholders": 10,
    "consistency_score": 83.3
  },
  "recommendations": [
    "Standardize THEME_NAME to use {{THEME_NAME}} format",
    "Add THEME_NAME to replacement checklist"
  ]
}
```

### Standard Output (Summary)

```
══════════════════════════════════════════════════════════
  Placeholder Detection Report
══════════════════════════════════════════════════════════

📊 STATISTICS
   Total Placeholders:   18
   Unique Placeholders:  5
   Files Scanned:        10
   Consistency Score:    83.3%

📋 DETECTED FORMATS

   {{DOUBLE_BRACE}}:  15 occurrences in 8 files
   ├─ {{THEME_NAME}}        (12 occurrences)
   ├─ {{SCREENSHOT_PATH}}   (2 occurrences)
   └─ {{PROJECT_ROOT}}      (1 occurrence)

   {SINGLE_BRACE}:    3 occurrences in 2 files
   └─ {PACKAGE_NAME}        (3 occurrences)

⚠️  INCONSISTENCIES FOUND

   ❌ Mixed formats for: THEME_NAME
      • {{THEME_NAME}} in package.json:2
      • {THEME_NAME}   in composer.json:5

💡 RECOMMENDATIONS

   1. Standardize THEME_NAME to use {{THEME_NAME}} format
   2. Replace {THEME_NAME} in composer.json:5
   3. Add THEME_NAME to replacement checklist

══════════════════════════════════════════════════════════
```

## Processing Flow

```
1. Input Parsing
   └─ Extract target path, format, exclude patterns

2. File Discovery
   ├─ Glob all files in target path
   └─ Apply exclude patterns

3. Placeholder Detection
   ├─ Search for {{PLACEHOLDER}} pattern (regex: \{\{([A-Z_]+)\}\})
   ├─ Search for {PLACEHOLDER} pattern (regex: \{([A-Z_]+)\})
   └─ Record file path and line number

4. Pattern Analysis
   ├─ Count occurrences per placeholder
   ├─ Group by format type
   └─ Identify unique placeholder names

5. Consistency Check
   ├─ Detect placeholders with multiple formats
   └─ Calculate consistency score

6. Report Generation
   ├─ Generate JSON report
   ├─ Generate summary report
   └─ Output recommendations

7. Exit Code
   ├─ 0: No issues or --strict not set
   └─ 1: Inconsistencies found and --strict set
```

## Detection Algorithm

### Pattern Matching

```
1. Double Brace Format: {{PLACEHOLDER}}
   Regex: \{\{([A-Z_]+)\}\}

2. Single Brace Format: {PLACEHOLDER}
   Regex: \{([A-Z_]+)\}

3. Exclusions:
   - CSS/SCSS variables: --variable-name
   - JavaScript template literals: ${variable}
   - Comments containing braces
```

### Consistency Score Calculation

```
consistency_score = (placeholders_with_single_format / total_unique_placeholders) × 100

Example:
- Total unique placeholders: 6
- Placeholders with single format: 5
- Placeholders with mixed formats: 1
- Consistency score: (5/6) × 100 = 83.3%
```

## Error Handling

| Error | Response |
|-------|----------|
| Path not found | Output error message and exit with code 1 |
| Permission denied | Skip file and continue scanning |
| Binary file detected | Skip file automatically |
| Invalid regex pattern | Output error message and exit with code 1 |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/coding-style.md` | Project coding style rules |
| `CLAUDE.md` | Project template documentation |
| `package.json` | Common placeholder location |

## Examples

### Basic Usage (Scan Entire Project)

```bash
/placeholder-detector
```

### Scan Specific Directory

```bash
/placeholder-detector --path .claude/
```

### Detect Only Double Brace Format

```bash
/placeholder-detector --format {{}}
```

### Strict Mode (Exit with Error on Inconsistencies)

```bash
/placeholder-detector --strict
```

### JSON Output

```bash
/placeholder-detector --output ./reports/placeholder-report.json
```

### Custom Exclude Pattern

```bash
/placeholder-detector --exclude "node_modules,dist,vendor"
```

## Use Cases

### 1. Template Quality Check Before Distribution

```bash
# Before publishing project as template
/placeholder-detector --strict

# Expected output:
# ✅ No inconsistencies found. Template is ready for distribution.
```

### 2. Generate Replacement Checklist

```bash
# Output to file for documentation
/placeholder-detector --output ./docs/placeholder-checklist.md

# Use the list to create replacement instructions
```

### 3. CI/CD Integration

```yaml
# .github/workflows/template-check.yml
- name: Check Placeholder Consistency
  run: /placeholder-detector --strict
```

### 4. Pre-commit Hook

```bash
# .git/hooks/pre-commit
/placeholder-detector --strict || exit 1
```

## Recommendations Output Examples

| Scenario | Recommendation |
|----------|----------------|
| Mixed formats | "Standardize {PLACEHOLDER} to use {{PLACEHOLDER}} format" |
| Single occurrence | "Verify if {PLACEHOLDER} should be replaced or is intentional" |
| Many occurrences | "Add {PLACEHOLDER} to replacement checklist (15 locations)" |
| No inconsistencies | "All placeholders use consistent format. Template is ready." |

## Related Skills

| Skill | Integration |
|-------|-------------|
| directory-structure-analyzer | Run after placeholder check to verify structure |
| docs-sync-checker | Verify placeholder usage matches documentation |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Author**: Auto-generated
