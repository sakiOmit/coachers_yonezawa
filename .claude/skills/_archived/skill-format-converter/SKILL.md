---
name: skill-format-converter
description: "Convert legacy skill format (skill.json + instructions.md) to official SKILL.md format with YAML frontmatter."
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash
context: fork
agent: general-purpose
---

# Skill Format Converter

## Overview

A skill that converts legacy format skills (skill.json + instructions.md dual-file structure) to the official SKILL.md format (single file with YAML frontmatter).

This skill automates the migration of existing skills, improving skill management centralization and maintainability.

**Key Features:**
- Automated JSON → YAML frontmatter conversion
- Markdown content integration
- Backup creation before conversion
- Template directory preservation
- Batch conversion support

## Usage

### Convert Single Skill

```
/skill-format-converter convert {skill-name}
```

### Batch Convert All Skills

```
/skill-format-converter convert-all [--dry-run]
```

### List Convertible Skills

```
/skill-format-converter list
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| mode | Yes | `convert`, `convert-all`, or `list` |
| skill-name | No | Target skill name (for convert mode) |
| --dry-run | No | Preview only, do not convert |
| --backup | No | Create backups (default: true) |
| --output | No | Output destination (default: same directory) |

## Output

### Conversion Result (JSON)

```json
{
  "status": "success",
  "skill_name": "scss-component-generator",
  "input_files": {
    "json": ".claude/skills/scss-component-generator/skill.json",
    "instructions": ".claude/skills/scss-component-generator/instructions.md"
  },
  "output_file": ".claude/skills/scss-component-generator/SKILL.md",
  "backup_files": {
    "json": ".claude/skills/scss-component-generator/skill.json.bak",
    "instructions": ".claude/skills/scss-component-generator/instructions.md.bak"
  },
  "templates_preserved": [
    "templates/component.scss.template",
    "templates/project.scss.template"
  ]
}
```

### List Mode Output (JSON)

```json
{
  "convertible_skills": [
    {
      "name": "scss-component-generator",
      "path": ".claude/skills/scss-component-generator/",
      "has_templates": true
    },
    {
      "name": "acf-field-generator",
      "path": ".claude/skills/acf-field-generator/",
      "has_templates": false
    }
  ],
  "already_converted": [
    "skill-format-converter"
  ],
  "total_convertible": 3
}
```

## Processing Flow

```
1. Input Parsing
   └─ Parse mode, skill-name, options

2. Skill Directory Validation
   ├─ Check skill.json exists
   ├─ Check instructions.md exists
   └─ Check existing SKILL.md (warn if overwrite)

3. JSON Reading & Parsing
   ├─ Extract name, version, description
   ├─ Extract mcp configuration
   └─ Extract allowed-tools

4. instructions.md Reading
   └─ Get Markdown content

5. SKILL.md Generation
   ├─ Generate YAML frontmatter
   │   ├─ name: {name}
   │   ├─ description: "{description}"
   │   ├─ allowed-tools: {tools}
   │   ├─ context: fork
   │   └─ agent: general-purpose
   │
   ├─ Add separator (---)
   │
   └─ Integrate content
       ├─ # {name} → title
       ├─ ## Overview → from description
       └─ Migrate sections from instructions.md

6. Backup Creation (optional)
   ├─ skill.json → skill.json.bak
   └─ instructions.md → instructions.md.bak

7. SKILL.md Output

8. templates/ Directory Handling
   └─ Preserve as-is (no move/change)

9. Result Report Output
```

## Field Mapping

### skill.json → YAML Frontmatter

| skill.json Field | SKILL.md Mapping |
|------------------|------------------|
| `name` | `name: {value}` |
| `description` | `description: "{value}"` |
| `allowed-tools` | `allowed-tools: [...]` |
| `mcp` | Add to Overview if present |
| `version` | Add at end of file |
| `instructions` | Reference to .md file to integrate |

### instructions.md Section Migration

| instructions.md | SKILL.md |
|-----------------|----------|
| `# {Title}` | Remove (use name from skill.json) |
| `## 目的` | Merge into `## Overview` |
| `## 実行フロー` | → `## Processing Flow` |
| `## 使用例` | → `## Examples` |
| `## エラーハンドリング` | → `## Error Handling` |
| `## 関連ドキュメント` | → `## Related Files` |
| Other sections | Preserve as-is |

## templates/ Directory Handling

- **No Changes**: templates/ directory is not moved or deleted
- **No Reference Updates**: Relative path references in SKILL.md remain valid
- **Reason**: Template files are maintained as independent resources

```
.claude/skills/{skill-name}/
├── SKILL.md              # Newly created
├── skill.json.bak        # Backup
├── instructions.md.bak   # Backup
└── templates/            # Preserved as-is
    ├── component.scss.template
    └── project.scss.template
```

## Error Handling

| Error | Response |
|-------|----------|
| skill.json not found | Exit with error, output message |
| JSON parse failure | Output error details and file path |
| instructions.md not found | Warning, generate from description only |
| SKILL.md already exists | Warning, require `--force` to overwrite |
| Write permission error | Exit with error, suggest checking permissions |
| Template file corruption | Warning, continue conversion |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/skills/` | Skill storage directory |
| `.claude/rules/skill.md` | Skill creation rules |
| `CLAUDE.md` | Project guide |

## Examples

### Example 1: Single Skill Conversion

```bash
/skill-format-converter convert scss-component-generator

# Output:
# === Converting scss-component-generator ===
#
# Reading skill.json... ✓
# Reading instructions.md... ✓
# Generating SKILL.md... ✓
# Creating backups... ✓
# Preserving templates/... ✓
#
# === Complete ===
# Output: .claude/skills/scss-component-generator/SKILL.md
# Backups:
#   - skill.json.bak
#   - instructions.md.bak
```

### Example 2: Dry Run

```bash
/skill-format-converter convert scss-component-generator --dry-run

# Output:
# === Dry Run: scss-component-generator ===
#
# Would generate SKILL.md with:
#   - Title: scss-component-generator
#   - Version: 1.0.0
#   - Sections: 8
#
# Would create backups:
#   - skill.json → skill.json.bak
#   - instructions.md → instructions.md.bak
#
# Run without --dry-run to apply changes.
```

### Example 3: List Convertible Skills

```bash
/skill-format-converter list

# Output:
# === Convertible Skills ===
#
# 1. scss-component-generator (has templates)
# 2. acf-field-generator
# 3. wordpress-page-generator (has templates)
#
# Total: 3 skills can be converted
#
# Run '/skill-format-converter convert-all' to convert all.
```

### Example 4: Batch Convert All

```bash
/skill-format-converter convert-all

# Output:
# === Converting All Skills ===
#
# [1/3] scss-component-generator... ✓
# [2/3] acf-field-generator... ✓
# [3/3] wordpress-page-generator... ✓
#
# === Summary ===
# Converted: 3
# Failed: 0
# Skipped: 0
```

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Converted from**: Design document (skill-format-converter/SKILL.md)
