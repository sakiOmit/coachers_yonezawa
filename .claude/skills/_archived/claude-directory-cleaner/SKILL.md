---
name: claude-directory-cleaner
description: "Detects and removes obsolete files in .claude directory including legacy skill formats and duplicate cache files."
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
context: fork
agent: general-purpose
---

# Claude Directory Cleaner

## Overview

A skill that automatically detects and cleans up obsolete files in the `.claude` directory.
Identifies legacy skill formats, duplicate cache files, and other unnecessary files to maintain a clean project structure.

## Usage

```
/claude-directory-cleaner [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--dry-run` | List files without deleting (default) |
| `--execute` | Actually delete detected files |
| `--category <type>` | Filter by category: `skills`, `cache`, `all` |

## Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| mode | No | dry-run | `dry-run` or `execute` |
| category | No | all | `skills`, `cache`, or `all` |

## Processing Flow

```
1. Scan Phase
   ├─ Scan .claude/skills/ for legacy format files
   │   ├─ Detect skill.json files
   │   ├─ Detect instructions.md files
   │   └─ Check if SKILL.md exists (migration complete)
   │
   ├─ Scan .claude/cache/figma/ for duplicates
   │   ├─ Group by nodeId
   │   ├─ Identify older versions
   │   └─ Flag debug.log files
   │
   └─ Scan .claude/prompts/ for redundant files
       └─ Compare with .claude/rules/ content

2. Report Phase
   ├─ Generate deletion candidate list
   ├─ Calculate space savings
   └─ Display categorized results

3. Confirmation Phase (execute mode only)
   ├─ Ask user confirmation via AskUserQuestion
   └─ List exact files to be deleted

4. Execution Phase (execute mode only)
   ├─ Delete confirmed files
   ├─ Verify deletion
   └─ Report results
```

## Detection Rules

### Legacy Skill Files

| Condition | Action |
|-----------|--------|
| SKILL.md exists + skill.json exists | Flag skill.json for deletion |
| SKILL.md exists + instructions.md exists | Flag instructions.md for deletion |
| Only skill.json + instructions.md (no SKILL.md) | Warn: migration needed |

### Duplicate Cache Files

| Condition | Action |
|-----------|--------|
| Same nodeId, multiple timestamps | Keep newest, flag others |
| debug.log in cache directory | Flag for deletion |
| Files older than 24 hours | Flag for deletion (respect TTL) |

### Redundant Prompts

| Condition | Action |
|-----------|--------|
| Content duplicated in rules/ | Flag for review |

## Output Format

### Dry-run Mode

```markdown
# Claude Directory Cleanup Report

## Summary
| Category | Files | Size |
|----------|-------|------|
| Legacy Skills | X | XX KB |
| Duplicate Cache | X | XX KB |
| Debug Files | X | XX KB |
| **Total** | **X** | **XX KB** |

## Details

### Legacy Skill Files (X files)
- .claude/skills/xxx/skill.json
- .claude/skills/xxx/instructions.md

### Duplicate Cache Files (X files)
- .claude/cache/figma/xxx_20260129.json (older)

### Debug Files (X files)
- .claude/cache/figma/debug.log

## Next Steps
Run `/claude-directory-cleaner --execute` to delete these files.
```

### Execute Mode

```markdown
# Deletion Complete

Deleted X files (XX KB freed)

## Deleted Files
- [path1]
- [path2]
```

## Error Handling

| Error | Response |
|-------|----------|
| Permission denied | Report error, continue with others |
| File not found | Skip (may have been deleted) |
| SKILL.md missing | Warn user, do not delete legacy files |

## Safety Features

1. **Dry-run by default**: Never deletes without explicit `--execute`
2. **User confirmation**: Always asks before deletion in execute mode
3. **SKILL.md check**: Never deletes legacy files if migration incomplete
4. **Backup suggestion**: Recommends git commit before deletion

## Examples

### Example 1: Check for obsolete files

```
/claude-directory-cleaner
```

Output:
```
Found 8 obsolete files (45 KB)
- 3 legacy skill files
- 4 duplicate cache files
- 1 debug file

Run with --execute to delete.
```

### Example 2: Delete obsolete files

```
/claude-directory-cleaner --execute
```

Output:
```
The following files will be deleted:
[list of files]

Proceed? [Yes/No]
```

### Example 3: Clean only cache

```
/claude-directory-cleaner --category cache --execute
```

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/skill.md` | SKILL.md format specification |
| `.claude/rules/figma.md` | Cache TTL rules |

---

**Version**: 1.0.0
**Created**: 2026-01-30
