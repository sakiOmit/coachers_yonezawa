---
name: directory-structure-analyzer
description: "Analyzes configuration directory structure to detect broken references, naming inconsistencies, and provides improvement suggestions."
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - mcp__serena__list_dir
  - mcp__serena__search_for_pattern
context: fork
agent: general-purpose
---

# Directory Structure Analyzer

## Overview

A skill that analyzes configuration directories (`.claude`, etc.) to identify structural issues, broken references, and naming inconsistencies.
Provides actionable improvement suggestions for maintaining a clean and consistent project structure.

## Usage

```
/directory-structure-analyzer [target] [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `target` | Directory to analyze (default: `.claude`) |

### Options

| Option | Description |
|--------|-------------|
| `--format <type>` | Output format: `tree`, `report`, `json` |
| `--check <type>` | Specific check: `references`, `naming`, `all` |
| `--verbose` | Include detailed findings |

## Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| target | No | .claude | Target directory path |
| format | No | report | Output format |
| check | No | all | Check type to run |

## Processing Flow

```
1. Structure Analysis Phase
   ├─ Scan target directory recursively
   ├─ Build file/directory tree
   ├─ Categorize by type (md, yaml, json, etc.)
   └─ Calculate statistics

2. Reference Check Phase
   ├─ Extract file references from documents
   │   ├─ Markdown links: [text](path)
   │   ├─ YAML references: file: "path"
   │   └─ Import statements
   │
   ├─ Verify each reference exists
   └─ Flag broken references

3. Naming Consistency Check Phase
   ├─ Check file naming conventions
   │   ├─ kebab-case for skills
   │   ├─ UPPER_CASE for constants
   │   └─ Consistent extensions
   │
   ├─ Check directory naming
   └─ Identify outliers

4. Duplicate Content Check Phase
   ├─ Compare file contents
   ├─ Identify similar files (>80% match)
   └─ Flag potential consolidation

5. Report Generation Phase
   ├─ Generate structured report
   ├─ Prioritize issues
   └─ Provide recommendations
```

## Check Types

### Reference Check

Detects broken references in documentation and configuration files.

| Reference Type | Pattern | Example |
|----------------|---------|---------|
| Markdown Link | `[text](path)` | `[rules](./rules/scss.md)` |
| YAML File | `file: "path"` | `file: "templates/base.php"` |
| Include | `@use`, `@import` | `@use '../foundation/mixins'` |
| Command Ref | `/command` | `/figma-implement` |

### Naming Check

Validates naming conventions across the project.

| Category | Expected Pattern | Example |
|----------|-----------------|---------|
| Skill directories | kebab-case | `claude-directory-cleaner` |
| SKILL files | SKILL.md (exact) | `SKILL.md` |
| Rule files | kebab-case.md | `coding-style.md` |
| Cache files | {key}_{id}_{timestamp}.json | `abc_1-2_20260130.json` |

### Duplicate Check

Identifies files with similar content that may be consolidated.

| Similarity | Classification |
|------------|----------------|
| 100% | Exact duplicate |
| 80-99% | Near duplicate (review) |
| 50-79% | Partial overlap (info) |

## Output Format

### Tree Format

```
.claude/
├── agents/                    (9 files)
│   ├── README.md
│   └── ...
├── cache/
│   └── figma/                 (19 files)
├── commands/                  (21 files)
├── rules/                     (8 files)
├── skills/                    (14 dirs)
│   ├── claude-directory-cleaner/
│   │   └── SKILL.md
│   └── ...
└── [total: 85 files, 14 dirs]
```

### Report Format

```markdown
# Directory Structure Analysis Report

**Target**: .claude
**Analyzed**: 2026-01-30T14:30:00
**Files**: 85 | **Directories**: 14

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| References | ⚠️ | 3 broken |
| Naming | ✅ | 0 issues |
| Duplicates | ⚠️ | 2 candidates |

## Broken References (3)

| File | Reference | Status |
|------|-----------|--------|
| commands/README.md:15 | `./deprecated-cmd.md` | Not found |
| rules/scss.md:42 | `../docs/old-guide.md` | Not found |
| agents/README.md:8 | `#deprecated-section` | Anchor not found |

## Naming Inconsistencies (0)

All files follow naming conventions.

## Duplicate Candidates (2)

| File 1 | File 2 | Similarity |
|--------|--------|------------|
| prompts/figma-cache.md | rules/figma.md | 85% |
| ... | ... | ... |

## Recommendations

1. **Fix broken references** (Priority: High)
   - Update or remove invalid links

2. **Review duplicate content** (Priority: Medium)
   - Consider consolidating similar files

3. **Add missing documentation** (Priority: Low)
   - Some directories lack README.md
```

### JSON Format

```json
{
  "target": ".claude",
  "timestamp": "2026-01-30T14:30:00",
  "statistics": {
    "files": 85,
    "directories": 14,
    "totalSize": "256KB"
  },
  "issues": {
    "brokenReferences": [...],
    "namingIssues": [...],
    "duplicates": [...]
  },
  "recommendations": [...]
}
```

## Error Handling

| Error | Response |
|-------|----------|
| Directory not found | Exit with error message |
| Permission denied | Skip file, report in warnings |
| Large directory (>1000 files) | Warn user, offer to limit depth |

## Examples

### Example 1: Analyze .claude directory

```
/directory-structure-analyzer
```

### Example 2: Check only broken references

```
/directory-structure-analyzer --check references
```

### Example 3: Full analysis with verbose output

```
/directory-structure-analyzer --verbose
```

## Integration

This skill works well with:

| Skill | Integration |
|-------|-------------|
| `claude-directory-cleaner` | Use analysis results to clean up |
| `skill-format-converter` | Fix naming issues in skills |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/skill.md` | Naming conventions for skills |
| `.claude/rules/coding-style.md` | General naming conventions |

---

**Version**: 1.0.0
**Created**: 2026-01-30
