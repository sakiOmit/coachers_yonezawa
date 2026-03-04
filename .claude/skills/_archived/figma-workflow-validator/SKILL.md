---
name: figma-workflow-validator
description: "Validates workflow compliance after Figma implementation tasks to prevent recurring issues like missing common component usage."
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# Figma Workflow Validator

## Overview

A skill that automatically validates workflow compliance after Figma implementation tasks are completed.
Prevents recurring issues such as missing common component usage by checking adherence to established Figma workflow rules.

### Background

Common issues in Figma implementation workflows:
- **component-catalog.yaml not referenced**: Missing existing components leads to duplicate implementations
- **Re-use judgment table not created**: No systematic component matching process
- **Matching score not calculated**: Subjective decisions instead of data-driven choices
- **text-extracted.json not created**: Text content not properly cached for reuse
- **Cache structure missing**: Inefficient repeated API calls
- **production-reviewer not executed**: Quality issues slip through to deployment

This skill automatically detects these workflow violations and provides remediation guidance.

## Usage

```
/figma-workflow-validator [task-id]
```

Or

```
/figma-workflow-validator --dir [implementation-directory]
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| task-id | Yes* | Task ID (e.g., cmd_005_page-requirements) |
| --dir | Yes* | Implementation directory path (e.g., themes/{{THEME_NAME}}/pages/) |
| --report | No | Report output path (default: stdout) |
| --fix | No | Auto-fix mode (suggests fixes) |

*Either task-id or --dir is required

## Output Format

### Standard Output

```
══════════════════════════════════════════════════════════
  Figma Workflow Validation Report
══════════════════════════════════════════════════════════

📋 Task: cmd_005_page-requirements
📂 Directory: themes/{{THEME_NAME}}/pages/

## 検証結果

| 項目 | 状態 | 備考 |
|------|------|------|
| component-catalog.yaml 参照 | ✅ | Catalog checked at Step 2 |
| 再利用判定表作成 | ✅ | Judgment table created |
| マッチングスコア計算 | ✅ | Scores calculated for 3 components |
| テキスト抽出・保存 | ❌ | text-extracted.json not found |
| キャッシュ存在 | ✅ | Cache found in .claude/cache/figma/ |
| production-reviewer 実行 | ❌ | No review report found |

### 違反項目
- テキスト抽出・保存が未実施（text-extracted.json not found）
- production-reviewer が未実行（No review report found）

### 推奨対応
1. テキスト抽出実施:
   - Figmaデザインコンテキストからテキスト要素を抽出
   - .claude/cache/figma/{fileKey}_{nodeId}_text.json に保存

2. production-reviewer 実行:
   - /review コマンドで統合レビュー実施
   - SCSS/PHP/JSの品質チェック
   - 本番デプロイ前の必須ステップ

══════════════════════════════════════════════════════════
```

### JSON Output (--report option)

```json
{
  "task_id": "cmd_005_page-requirements",
  "directory": "themes/{{THEME_NAME}}/pages/",
  "timestamp": "2026-01-30T17:50:00Z",
  "validation_results": {
    "component_catalog_referenced": {
      "status": "pass",
      "note": "Catalog checked at Step 2"
    },
    "reuse_judgment_table_created": {
      "status": "pass",
      "note": "Judgment table created"
    },
    "matching_score_calculated": {
      "status": "pass",
      "note": "Scores calculated for 3 components"
    },
    "text_extracted": {
      "status": "fail",
      "note": "text-extracted.json not found"
    },
    "cache_exists": {
      "status": "pass",
      "note": "Cache found in .claude/cache/figma/"
    },
    "production_reviewer_executed": {
      "status": "fail",
      "note": "No review report found"
    }
  },
  "violations": [
    {
      "item": "text_extracted",
      "severity": "medium",
      "message": "テキスト抽出・保存が未実施"
    },
    {
      "item": "production_reviewer_executed",
      "severity": "high",
      "message": "production-reviewer が未実行"
    }
  ],
  "recommendations": [
    {
      "priority": 1,
      "action": "テキスト抽出実施",
      "details": "Figmaデザインコンテキストからテキスト要素を抽出し、.claude/cache/figma/{fileKey}_{nodeId}_text.json に保存"
    },
    {
      "priority": 2,
      "action": "production-reviewer 実行",
      "details": "/review コマンドで統合レビュー実施し、SCSS/PHP/JSの品質チェック"
    }
  ],
  "overall_status": "needs_improvement"
}
```

## Processing Flow

```
1. Input Parsing
   └─ Extract task-id or directory path

2. File Discovery
   ├─ Locate implementation files (PHP, SCSS, JS)
   ├─ Find related cache files
   └─ Check for review reports

3. Validation Checks
   ├─ component-catalog.yaml reference check
   │  └─ Search for "component-catalog" in implementation notes/comments
   │
   ├─ Re-use judgment table check
   │  └─ Look for judgment table in reports or implementation docs
   │
   ├─ Matching score calculation check
   │  └─ Search for score calculations in workflow artifacts
   │
   ├─ text-extracted.json check
   │  └─ Check .claude/cache/figma/ for text extraction files
   │
   ├─ Cache structure check
   │  └─ Verify .claude/cache/figma/{fileKey}_{nodeId}_*.json exists
   │
   └─ production-reviewer execution check
      └─ Search for review reports in .shogun/queue/reports/

4. Violation Detection
   └─ Identify failed checks and categorize by severity

5. Recommendation Generation
   ├─ Generate specific remediation steps
   └─ Prioritize by severity

6. Report Output
   └─ Format as table (stdout) or JSON (--report)
```

## Validation Algorithm

### Check 1: component-catalog.yaml Reference

```
Search patterns:
- "component-catalog.yaml" in implementation notes
- "catalog" AND "component" in task reports
- References to existing components in code comments

Status:
- ✅ Pass: At least one reference found
- ❌ Fail: No references found
```

### Check 2: Re-use Judgment Table

```
Search patterns:
- Tables with columns: component, match_score, decision
- "再利用判定" OR "reuse judgment" in reports
- Markdown tables in implementation artifacts

Status:
- ✅ Pass: Judgment table found
- ❌ Fail: No table found
```

### Check 3: Matching Score Calculation

```
Search patterns:
- Numerical scores (e.g., "80%", "score: 75")
- "マッチングスコア" OR "matching score"
- Score calculation formulas

Status:
- ✅ Pass: Scores found
- ❌ Fail: No scores found
```

### Check 4: text-extracted.json

```
Check:
- .claude/cache/figma/{fileKey}_{nodeId}_text.json exists
- File is non-empty
- Valid JSON structure

Status:
- ✅ Pass: File exists and valid
- ❌ Fail: File missing or invalid
```

### Check 5: Cache Structure

```
Check:
- .claude/cache/figma/{fileKey}_{nodeId}_*.json exists
- File created within 24 hours
- Valid JSON structure with design_context

Status:
- ✅ Pass: Cache exists and valid
- ❌ Fail: Cache missing or expired
```

### Check 6: production-reviewer Execution

```
Search:
- .shogun/queue/reports/ashigaru*_report.yaml
- Look for "production-reviewer" or "review" in status
- Check for review artifacts in recent commits

Status:
- ✅ Pass: Review report found
- ❌ Fail: No review found
```

## Error Handling

| Error | Response |
|-------|----------|
| Task ID not found | Output error and exit |
| Directory not found | Output error and exit |
| Permission denied | Output error and suggest running with proper permissions |
| Invalid report format | Output partial results with warning |

## Severity Levels

| Item | Severity | Impact |
|------|----------|--------|
| component-catalog.yaml 参照 | High | Duplicate implementations |
| 再利用判定表作成 | Medium | Inconsistent decisions |
| マッチングスコア計算 | Medium | Subjective choices |
| テキスト抽出・保存 | Low | Inefficient text reuse |
| キャッシュ存在 | Low | Extra API calls |
| production-reviewer 実行 | High | Quality issues |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/figma.md` | Workflow rules definition |
| `.claude/catalogs/component-catalog.yaml` | Component catalog |
| `.claude/cache/figma/` | Figma cache storage |
| `.shogun/queue/reports/` | Task reports |

## Examples

### Basic Usage (Task ID)

```bash
/figma-workflow-validator cmd_005_page-requirements
```

### Directory-based Validation

```bash
/figma-workflow-validator --dir themes/{{THEME_NAME}}/pages/
```

### JSON Report Output

```bash
/figma-workflow-validator cmd_005_page-requirements --report ./validation-report.json
```

### Auto-fix Mode (Suggests Fixes)

```bash
/figma-workflow-validator cmd_005_page-requirements --fix
```

## Integration with Workflow

### When to Use

- **After Figma implementation**: Immediately after completing a Figma→WordPress implementation
- **Before production-reviewer**: As a pre-review quality gate
- **In CI/CD pipeline**: Automated checks before deployment

### Recommended Workflow

```
1. Complete Figma implementation
2. Run /figma-workflow-validator
3. Fix violations if any
4. Run /review (production-reviewer)
5. Commit changes
```

## Related Skills

| Skill | Integration |
|-------|-------------|
| figma-implement | Validate after orchestrator completion |
| production-reviewer | Run validator before reviewer |
| delivery-checker | Validate as part of delivery checks |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Purpose**: Prevent Figma workflow violations through automated validation
