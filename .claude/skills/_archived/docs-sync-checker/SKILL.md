---
name: docs-sync-checker
description: "Checks synchronization between documentation and implementation files (.claude/agents, .claude/skills vs docs/claude-guide)."
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
context: fork
agent: general-purpose
---

# Docs Sync Checker

## Overview

A skill that automatically checks the synchronization between documentation and implementation.
Detects discrepancies between `.claude/agents/`, `.claude/skills/` directories and their corresponding documentation in `docs/claude-guide/`.

## Usage

```
/docs-sync-checker [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--target <type>` | Check specific target: `agents`, `skills`, or `all` (default) |
| `--fix-suggestions` | Include detailed fix suggestions in output |
| `--verbose` | Show detailed matching information |

## Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| target | No | all | `agents`, `skills`, or `all` |
| fix-suggestions | No | false | Include fix suggestions |
| verbose | No | false | Verbose output |

## Processing Flow

```
1. Discovery Phase
   ├─ Scan .claude/agents/*.md
   │   └─ Extract agent names (excluding README.md)
   │
   ├─ Scan .claude/skills/*/SKILL.md
   │   └─ Extract skill names from directory names
   │
   └─ Check docs/claude-guide/ existence
       ├─ agents.md
       └─ skills.md

2. Documentation Parse Phase
   ├─ Parse docs/claude-guide/agents.md
   │   └─ Extract referenced agent names
   │
   └─ Parse docs/claude-guide/skills.md (if exists)
       └─ Extract referenced skill names

3. Comparison Phase
   ├─ Compare agents: implementation vs documentation
   │   ├─ Find undocumented agents (in code, not in docs)
   │   └─ Find missing agents (in docs, not in code)
   │
   └─ Compare skills: implementation vs documentation
       ├─ Find undocumented skills
       └─ Find missing skills

4. Report Generation Phase
   ├─ Generate sync status summary
   ├─ List discrepancies by category
   └─ Provide recommended actions
```

## Detection Rules

### Agents Sync Check

| Source | Target | Match Criteria |
|--------|--------|----------------|
| `.claude/agents/{name}.md` | `docs/claude-guide/agents.md` | Filename (without .md) mentioned in docs |

### Skills Sync Check

| Source | Target | Match Criteria |
|--------|--------|----------------|
| `.claude/skills/{name}/SKILL.md` | `docs/claude-guide/skills.md` | Directory name mentioned in docs |

### Discrepancy Types

| Type | Description | Severity |
|------|-------------|----------|
| Undocumented | Implementation exists, documentation missing | Warning |
| Missing Implementation | Documentation exists, implementation missing | Error |
| Doc File Missing | Target documentation file does not exist | Error |

## Output Format

### Summary Report

```markdown
# Documentation Sync Check Report

## Summary

| Category | In Code | In Docs | Synced | Issues |
|----------|---------|---------|--------|--------|
| Agents   | X       | X       | X      | X      |
| Skills   | X       | X       | X      | X      |

## Status: [SYNCED / OUT_OF_SYNC]

---

## Agents Sync Status

### Synced (X items)
- architecture-consultant
- code-fixer
- ...

### Undocumented (X items)
| Agent | File | Recommended Action |
|-------|------|-------------------|
| new-agent | .claude/agents/new-agent.md | Add to docs/claude-guide/agents.md |

### Missing Implementation (X items)
| Agent | Referenced In | Recommended Action |
|-------|---------------|-------------------|
| old-agent | docs/claude-guide/agents.md | Remove from documentation or implement |

---

## Skills Sync Status

### Documentation File Status
- docs/claude-guide/skills.md: [EXISTS / MISSING]

### Synced (X items)
- figma-page-analyzer
- ...

### Undocumented (X items)
| Skill | Directory | Recommended Action |
|-------|-----------|-------------------|
| new-skill | .claude/skills/new-skill/ | Add to docs/claude-guide/skills.md |

### Missing Implementation (X items)
| Skill | Referenced In | Recommended Action |
|-------|---------------|-------------------|
| old-skill | docs/claude-guide/skills.md | Remove from documentation or implement |

---

## Recommended Actions

1. [Priority: High] Create docs/claude-guide/skills.md
2. [Priority: Medium] Document X undocumented agents
3. [Priority: Medium] Document X undocumented skills
4. [Priority: Low] Review X missing implementations
```

## Error Handling

| Error | Response |
|-------|----------|
| docs/claude-guide/ not found | Report error, suggest creating directory |
| agents.md not found | Report warning, skip agents check |
| skills.md not found | Report warning, suggest creation |
| Permission denied | Report error for specific file |
| Empty directory | Report as 0 items, no error |

## Implementation Notes

### Agent Name Extraction

```
File: .claude/agents/code-fixer.md
Extracted Name: code-fixer
```

### Skill Name Extraction

```
Directory: .claude/skills/figma-page-analyzer/SKILL.md
Extracted Name: figma-page-analyzer
```

### Documentation Reference Detection

Search patterns in documentation files:
- Markdown headers containing the name
- Table rows with the name
- Inline code blocks with the name
- Bullet points mentioning the name

## Examples

### Example 1: Full sync check

```
/docs-sync-checker
```

Output:
```
Documentation Sync Check Report

Summary:
- Agents: 8 in code, 8 in docs, all synced
- Skills: 16 in code, 0 in docs (skills.md missing)

Status: OUT_OF_SYNC

Recommended Actions:
1. Create docs/claude-guide/skills.md
2. Document 16 skills
```

### Example 2: Check agents only

```
/docs-sync-checker --target agents
```

### Example 3: With fix suggestions

```
/docs-sync-checker --fix-suggestions
```

Output includes specific markdown snippets to add to documentation files.

## Related Files

| File | Purpose |
|------|---------|
| `.claude/agents/README.md` | Agent overview (not checked) |
| `.claude/rules/skill.md` | Skill format specification |
| `docs/claude-guide/agents.md` | Agent documentation |
| `docs/claude-guide/skills.md` | Skill documentation |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Proposer**: Auto-generated
