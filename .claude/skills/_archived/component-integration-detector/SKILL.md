---
name: component-integration-detector
description: "Detects discrepancies between planned components and actual implementation, identifies integrations and deletions."
disable-model-invocation: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
context: fork
agent: general-purpose
---

# Component Integration Detector

## Overview

A skill that automatically detects discrepancies between planned components (in Figma caches, task files) and actual implementation.
Identifies when planned components were integrated into existing ones or deleted, and suggests documentation updates.

## Usage

```
/component-integration-detector [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--source <type>` | Source to check: `figma-cache`, `task-files`, `all` (default) |
| `--update-docs` | Auto-update documentation to reflect integrations |
| `--report <format>` | Output format: `text`, `yaml`, `json` (default: text) |

## Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| source | No | all | Source type to check |
| update-docs | No | false | Enable auto-update |
| report | No | text | Output format |

## Processing Flow

```
1. Discovery Phase
   ├─ Scan Figma Caches
   │   ├─ Read .claude/cache/figma/*/component-matching.yaml
   │   ├─ Extract planned component names
   │   └─ Extract matched_component references
   │
   ├─ Scan Task Files
   │   ├─ Read .claude/tasks/*.md
   │   ├─ Extract component references in tables
   │   └─ Extract "実装済み" status claims
   │
   └─ Scan Component Catalog
       ├─ Read .claude/catalogs/component-catalog.yaml
       └─ Extract registered component names

2. Implementation Scan Phase
   ├─ Scan PHP Templates
   │   ├─ Find template-parts/**/*.php
   │   └─ Extract component file names
   │
   └─ Scan SCSS Files
       ├─ Find src/scss/**/*.scss
       └─ Extract class names (BEM blocks)

3. Comparison Phase
   ├─ Compare Figma Cache vs Implementation
   │   ├─ Check: Planned component exists in filesystem
   │   ├─ Check: Planned component registered in catalog
   │   └─ Detect: Integration into other component
   │
   ├─ Compare Task Files vs Implementation
   │   ├─ Check: "実装済み" components exist
   │   └─ Detect: Status mismatch
   │
   └─ Detect Integration Patterns
       ├─ Pattern 1: Variant integration (c-link-button → c-button --cyan)
       ├─ Pattern 2: Feature merge (component A absorbed by B)
       └─ Pattern 3: Deprecation (component removed entirely)

4. Report Generation Phase
   ├─ List discrepancies by type
   ├─ Suggest documentation updates
   └─ Generate update patches (if --update-docs)
```

## Detection Patterns

### 1. Variant Integration

**Scenario**: Planned component became a variant of existing component.

**Example**:
```yaml
# Figma cache planned:
- matched_component: "c-link-button"

# Actual implementation:
- component: "c-button"
  variant: "--cyan"
```

**Detection**:
- c-link-button.php does not exist
- c-button.php exists with variant class
- Usage found: `class="c-button--cyan"`

### 2. Feature Merge

**Scenario**: Planned component's features absorbed by existing component.

**Example**:
```yaml
# Planned:
- name: "c-search-box"

# Actual:
- name: "c-input"
  new_features: ["search", "icon-support"]
```

**Detection**:
- c-search-box.php does not exist
- c-input.php has enhanced features
- No references to c-search-box in codebase

### 3. Deprecation

**Scenario**: Planned component removed entirely (no longer needed).

**Example**:
```yaml
# Planned:
- name: "c-legacy-button"

# Actual:
- <component does not exist>
- <no references in codebase>
```

## Output Format

### Text Report (Default)

```markdown
# Component Integration Detection Report

## Summary

| Source | Planned | Implemented | Integrated | Missing | Match Rate |
|--------|---------|-------------|------------|---------|------------|
| Figma Cache | 12 | 10 | 2 | 0 | 100% |
| Task Files | 8 | 6 | 2 | 0 | 100% |
| **Total** | **20** | **16** | **4** | **0** | **100%** |

**Status**: All planned components accounted for (integration detected)

---

## Integration Details

### 🔄 Variant Integration (2 cases)

#### 1. c-link-button → c-button --cyan

**Planned**:
- Source: `.claude/cache/figma/requirements/component-matching.yaml:96`
- Component: `c-link-button`
- Status: "既存使用"

**Actual Implementation**:
- Component: `c-button` (template-parts/common/button.php)
- Variant: `--cyan`
- Usage: `single-requirements.php:224`

**Evidence**:
- ❌ c-link-button.php does not exist
- ✅ c-button.php exists
- ✅ c-button--cyan found in usage

**Recommendation**:
- Update `.claude/cache/figma/requirements/component-matching.yaml:96`
  Change: `matched_component: "c-link-button"` → `matched_component: "c-button"`
  Add note: `variant: "--cyan"`

- Update `.claude/tasks/common-components-task.md:20, 94`
  Remove: c-link-button references
  Add: c-button with cyan variant

#### 2. c-primary-button → c-button (default)

**Planned**:
- Source: `.claude/tasks/page-implementation-task.md:42`
- Component: `c-primary-button`

**Actual Implementation**:
- Component: `c-button` (default variant)

**Recommendation**:
- Update task file reference

---

### 📦 Feature Merge (1 case)

#### c-search-box → c-input (enhanced)

**Planned**: Standalone search box component

**Actual**: c-input component with search support

**Recommendation**:
- Update component catalog
- Document feature merge in CHANGELOG.md

---

### ⚠️ Missing Documentation Updates

The following files reference integrated/deprecated components:

1. `.claude/tasks/common-components-task.md`
   - Line 20: References `c-link-button` (should be `c-button`)
   - Line 94: Lists `c-link-button` in catalog (should be `c-button`)

2. `.claude/cache/figma/requirements/component-matching.yaml`
   - Line 96: References `c-link-button` (should be `c-button --cyan`)

---

## Recommended Actions

### Priority: High (Breaking discrepancies)

None detected.

### Priority: Medium (Documentation sync)

1. Update `.claude/tasks/common-components-task.md`
   - Replace c-link-button → c-button
   - Add variant information

2. Update Figma cache notes
   - Add integration comments

### Priority: Low (Informational)

1. Update component catalog comments
   - Document integration history

---

## Auto-update Available

Run with `--update-docs` to automatically apply:

- Documentation file updates (2 files)
- Catalog comment additions (1 entry)
- Task file corrections (2 references)

Estimated changes: 5 edits across 3 files
```

### YAML Report

```yaml
summary:
  total_planned: 20
  implemented: 16
  integrated: 4
  missing: 0
  match_rate: 1.0

integrations:
  - type: variant_integration
    planned_component: c-link-button
    actual_component: c-button
    variant: --cyan
    sources:
      - file: .claude/cache/figma/requirements/component-matching.yaml
        line: 96
    evidence:
      planned_exists: false
      actual_exists: true
      variant_found: true
      usage_locations:
        - file: themes/{{THEME_NAME}}/single-requirements.php
          line: 224

documentation_updates:
  - file: .claude/tasks/common-components-task.md
    line: 20
    current: "c-link-button"
    should_be: "c-button"
    reason: "Component integrated as variant"

  - file: .claude/cache/figma/requirements/component-matching.yaml
    line: 96
    current: "matched_component: c-link-button"
    should_be: "matched_component: c-button"
    add_note: "variant: --cyan"
```

## Error Handling

| Error | Response |
|-------|----------|
| Figma cache not found | Skip Figma checks, warn |
| Task file not found | Skip task checks, warn |
| Component catalog missing | Report error, cannot proceed |
| Permission denied | Report error for specific file |
| Invalid YAML format | Report parsing error, skip file |

## Auto-update Capabilities

### Documentation Files

Updates the following types:

- **Task files** (.claude/tasks/*.md)
  - Component references in tables
  - Status descriptions

- **Figma caches** (.claude/cache/figma/*/component-matching.yaml)
  - matched_component values
  - Add integration notes

- **Component catalog** (.claude/catalogs/component-catalog.yaml)
  - Add deprecation comments
  - Update integration history

### Safety

- Creates backup before editing: `{file}.backup-{timestamp}`
- Dry-run mode: Shows changes without applying
- Preserves original formatting and comments

## Examples

### Example 1: Full detection

```
/component-integration-detector
```

Scans all sources (Figma caches, task files, catalog).

### Example 2: Figma cache only

```
/component-integration-detector --source figma-cache
```

### Example 3: Auto-update documentation

```
/component-integration-detector --update-docs
```

Creates backups and updates documentation files.

### Example 4: YAML output

```
/component-integration-detector --report yaml
```

## Integration with Workflow

### Post-Figma Implementation

Add to `figma-implement` Step 9 (Post-implementation):

```
1. /figma-implement (complete)
2. /component-integration-detector
3. Review integration report
4. /component-integration-detector --update-docs (if approved)
```

### Periodic Maintenance

Run monthly to detect accumulated inconsistencies:

```bash
# CI job
/component-integration-detector --report yaml > integration-report.yaml
```

## Related Files

| File | Purpose |
|------|---------|
| `.claude/catalogs/component-catalog.yaml` | Component registry (source of truth) |
| `.claude/cache/figma/*/component-matching.yaml` | Figma implementation plans |
| `.claude/tasks/*.md` | Task planning documents |
| `.claude/rules/coding-style.md` | Component lifecycle guidelines |

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `figma-implement` | Uses this for post-implementation validation |
| `docs-sync-checker` | Complementary (checks agents/skills sync) |
| `component-catalog-updater` | (Future) Auto-maintains catalog |

---

**Version**: 1.0.0
**Created**: 2026-01-31
**Proposer**: Ashigaru 1 (cmd_004, task_cmd004_1)
**Background**: Discovered c-link-button integration during requirements page investigation
