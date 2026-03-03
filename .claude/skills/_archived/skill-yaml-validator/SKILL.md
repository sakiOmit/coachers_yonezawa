---
name: skill-yaml-validator
description: "Validate SKILL.md YAML frontmatter to detect missing required and recommended fields for quality assurance."
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
context: fork
agent: general-purpose
---

# Skill YAML Validator

## Overview

A skill that validates SKILL.md YAML frontmatter, ensuring all required and recommended fields are present and properly formatted. This prevents runtime errors and ensures consistent skill definitions across the project.

### Background

SKILL.md files require specific YAML frontmatter fields to function correctly. Missing or malformed fields cause:
- Skill invocation failures
- Inconsistent skill behavior
- Poor developer experience
- CI/CD pipeline failures

This skill prevents these issues by validating all SKILL.md files before deployment.

## Usage

```
/skill-yaml-validator
```

Or

```
/skill-yaml-validator --path .claude/skills/my-skill/ --strict
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| --path | No | Target skill directory path (default: .claude/skills/) |
| --skill | No | Specific skill name to validate (default: all skills) |
| --output | No | Output report path (default: stdout) |
| --strict | No | Strict mode: exit with error if recommended fields missing |
| --fix | No | Auto-fix mode: add missing recommended fields with defaults |

## Output

### Validation Report (JSON Format)

```json
{
  "metadata": {
    "scan_path": ".claude/skills",
    "total_skills": 18,
    "timestamp": "2026-01-30T15:00:00Z"
  },
  "results": {
    "passed": 16,
    "failed": 2,
    "warnings": 3
  },
  "skills": [
    {
      "name": "skill-yaml-validator",
      "path": ".claude/skills/skill-yaml-validator/SKILL.md",
      "status": "passed",
      "required_fields": {
        "name": "✓",
        "description": "✓",
        "allowed-tools": "✓"
      },
      "recommended_fields": {
        "context": "✓",
        "agent": "✓"
      },
      "issues": []
    },
    {
      "name": "broken-skill",
      "path": ".claude/skills/broken-skill/SKILL.md",
      "status": "failed",
      "required_fields": {
        "name": "✓",
        "description": "✗ Missing",
        "allowed-tools": "✓"
      },
      "recommended_fields": {
        "context": "✗ Missing",
        "agent": "✗ Missing"
      },
      "issues": [
        {
          "severity": "error",
          "field": "description",
          "message": "Required field 'description' is missing"
        },
        {
          "severity": "warning",
          "field": "context",
          "message": "Recommended field 'context' is missing (default: fork)"
        },
        {
          "severity": "warning",
          "field": "agent",
          "message": "Recommended field 'agent' is missing (default: general-purpose)"
        }
      ]
    }
  ],
  "summary": {
    "total_errors": 2,
    "total_warnings": 3,
    "compliance_rate": 88.9
  }
}
```

### Standard Output (Summary)

```
══════════════════════════════════════════════════════════
  SKILL.md YAML Validation Report
══════════════════════════════════════════════════════════

📊 STATISTICS
   Total Skills:         18
   Passed:               16
   Failed:               2
   Warnings:             3
   Compliance Rate:      88.9%

✅ PASSED SKILLS (16)
   ├─ skill-yaml-validator
   ├─ placeholder-detector
   ├─ figma-page-analyzer
   └─ ... (13 more)

❌ FAILED SKILLS (2)

   broken-skill (.claude/skills/broken-skill/SKILL.md)
   ├─ ✗ Missing required field: description
   ├─ ⚠ Missing recommended field: context
   └─ ⚠ Missing recommended field: agent

   incomplete-skill (.claude/skills/incomplete-skill/SKILL.md)
   └─ ✗ Missing required field: allowed-tools

⚠️  WARNINGS (3)
   ├─ 2 skills missing 'context' field (default: fork)
   └─ 1 skill missing 'agent' field (default: general-purpose)

💡 RECOMMENDATIONS
   1. Add 'description' field to broken-skill/SKILL.md
   2. Add 'allowed-tools' field to incomplete-skill/SKILL.md
   3. Run with --fix flag to auto-add recommended fields

══════════════════════════════════════════════════════════
```

## Processing Flow

```
1. Input Parsing
   └─ Extract target path, skill name, validation mode

2. Skill Discovery
   ├─ Glob .claude/skills/*/SKILL.md
   └─ Filter by --skill parameter if specified

3. YAML Frontmatter Extraction
   ├─ Read SKILL.md file
   ├─ Extract YAML frontmatter (between --- markers)
   └─ Parse YAML to object

4. Required Fields Validation
   ├─ Check 'name' field presence and format
   ├─ Check 'description' field presence (single sentence)
   └─ Check 'allowed-tools' field presence and array format

5. Recommended Fields Validation
   ├─ Check 'context' field presence (default: fork)
   ├─ Check 'agent' field presence (default: general-purpose)
   └─ Check 'disable-model-invocation' (default: false)

6. Issue Aggregation
   ├─ Classify issues by severity (error, warning)
   ├─ Calculate compliance rate
   └─ Generate recommendations

7. Report Generation
   ├─ Generate JSON report
   ├─ Generate summary report
   └─ Output recommendations

8. Auto-fix (if --fix enabled)
   ├─ Add missing recommended fields with defaults
   └─ Write updated SKILL.md

9. Exit Code
   ├─ 0: All validations passed
   ├─ 1: Required field missing
   └─ 2: Recommended field missing (only if --strict)
```

## Validation Rules

### Required Fields

| Field | Type | Validation |
|-------|------|------------|
| name | string | Must match directory name, kebab-case |
| description | string | Single sentence, ends with period |
| allowed-tools | array | Non-empty array of tool names |

### Recommended Fields

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| context | string | fork | Must be 'fork' or 'inline' |
| agent | string | general-purpose | Valid agent type |
| disable-model-invocation | boolean | false | Must be boolean |

### Format Validation

```yaml
# ✅ Valid
---
name: my-skill
description: "This is a valid description."
allowed-tools:
  - Read
  - Write
context: fork
agent: general-purpose
---

# ❌ Invalid - Missing description
---
name: my-skill
allowed-tools:
  - Read
---

# ❌ Invalid - Description not a sentence
---
name: my-skill
description: "no period at end"
allowed-tools:
  - Read
---

# ⚠️ Warning - Missing recommended fields
---
name: my-skill
description: "Valid description."
allowed-tools:
  - Read
# Missing: context, agent
---
```

## Error Handling

| Error | Response |
|-------|----------|
| SKILL.md not found | Skip skill and continue, add to warnings |
| Invalid YAML syntax | Report error with line number, exit with code 1 |
| Malformed frontmatter | Report error, exit with code 1 |
| Permission denied | Skip file and continue, add to warnings |
| Invalid tool name | Report error in allowed-tools validation |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/skill.md` | Skill creation rules |
| `.claude/skills/*/SKILL.md` | Skill definition files |
| `docs/claude-guide/skills.md` | Skill documentation |

## Examples

### Basic Usage (Validate All Skills)

```bash
/skill-yaml-validator
```

### Validate Specific Skill

```bash
/skill-yaml-validator --skill placeholder-detector
```

### Strict Mode (Exit on Warnings)

```bash
/skill-yaml-validator --strict
```

### Auto-fix Missing Recommended Fields

```bash
/skill-yaml-validator --fix
```

### JSON Output

```bash
/skill-yaml-validator --output ./reports/skill-validation.json
```

### Validate Custom Path

```bash
/skill-yaml-validator --path ~/.claude/skills/
```

## Use Cases

### 1. CI/CD Quality Gate

```yaml
# .github/workflows/skill-validation.yml
- name: Validate SKILL.md Files
  run: /skill-yaml-validator --strict
```

### 2. Pre-commit Hook

```bash
# .git/hooks/pre-commit
/skill-yaml-validator --strict || exit 1
```

### 3. Skill Development Workflow

```bash
# After creating new skill
/skill-yaml-validator --skill my-new-skill

# Expected output:
# ✅ All validations passed. Skill is ready.
```

### 4. Batch Fix Missing Fields

```bash
# Auto-add recommended fields to all skills
/skill-yaml-validator --fix

# Review changes
git diff .claude/skills/
```

### 5. Generate Compliance Report

```bash
# Before release
/skill-yaml-validator --output ./docs/skill-compliance.json

# Share report with team
```

## Auto-fix Behavior

When `--fix` flag is enabled, the validator will:

1. **Add missing recommended fields with defaults:**
   ```yaml
   context: fork
   agent: general-purpose
   disable-model-invocation: false
   ```

2. **Preserve existing values:**
   - Never overwrite existing fields
   - Only add missing recommended fields

3. **Maintain formatting:**
   - Preserve original YAML structure
   - Keep comments and spacing

4. **Generate backup:**
   - Create `.backup` file before modification

## Related Skills

| Skill | Integration |
|-------|-------------|
| directory-structure-analyzer | Verify skill directory structure |
| docs-sync-checker | Ensure skill documentation is synced |
| skill-migrator | Migrate legacy skills before validation |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Author**: Auto-generated
