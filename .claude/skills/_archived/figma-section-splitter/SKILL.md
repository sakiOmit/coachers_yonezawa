---
name: figma-section-splitter
description: "Split large Figma pages by section for parallel implementation by multiple workers, automating a 3-phase workflow (prep, section implementation, integration)."
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Task
  - mcp__figma__get_metadata
  - mcp__figma__get_design_context
  - mcp__figma__get_variable_defs
  - mcp__figma__get_code_connect_map
context: fork
agent: general-purpose
---

# Figma Section Splitter

## Overview

Split large Figma pages by section for parallel implementation by multiple workers. Automates a 3-phase workflow (Preparation → Section Implementation → Integration) to generate consistent SCSS/PHP code.

## Usage

```
/figma-section-splitter {Figma URL} [options]
```

or

```
/figma-section-splitter --file-key {fileKey} --node-id {nodeId} [options]
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| URL | Yes* | Figma page URL |
| --file-key | Yes* | Figma file key (alternative to URL) |
| --node-id | No | Page node ID |
| --parallel | No | Number of parallel workers (default: 4) |
| --output-dir | No | Output directory (default: `.claude/cache/figma/sections/`) |
| --page-name | No | Page name (used for SCSS/PHP naming) |
| --assign-workers | No | Auto-generate worker task files |

*Either URL or --file-key is required

## Output

### Phase 1: Preparation Phase Output

```yaml
# .claude/cache/figma/sections/{page-name}/manifest.yaml
metadata:
  file_key: "wbpri0A53IqL1KvkRBtvkl"
  page_node_id: "123:456"
  page_name: "interview-detail"
  timestamp: "2026-01-30T13:00:00"
  total_sections: 5

sections:
  - id: 1
    name: "hero"
    node_id: "1:100"
    normalized_class: "p-interview-hero"
    output_files:
      scss: "src/scss/object/projects/interview/_p-interview-hero.scss"
      php: "themes/{THEME}/template-parts/sections/interview/hero.php"
    assigned_to: null

global_context:
  variables_path: ".claude/cache/figma/sections/{page-name}/variables.yaml"
  component_map_path: ".claude/cache/figma/sections/{page-name}/component-map.yaml"

parallel_tasks:
  max_workers: 4
  estimated_per_section: "15-20 min"
```

### Phase 2: Section Data

```json
// .claude/cache/figma/sections/{page-name}/section_{id}.json
{
  "section_id": 1,
  "name": "hero",
  "node_id": "1:100",
  "design_context": { /* get_design_context result */ },
  "detected_components": [
    {
      "figma_name": "Button/Primary",
      "normalized_class": "c-link-button",
      "match_type": "code_connect",
      "match_score": 100,
      "existing_file": "template-parts/common/link-button.php"
    }
  ],
  "extracted_styles": {
    "colors": ["#d71218", "#111"],
    "fonts": ["Noto Sans JP", "Poppins"],
    "spacing": [80, 40, 24, 16]
  }
}
```

### Phase 3: Integration Task File

```yaml
# integration_{page-name}.yaml
task:
  task_id: "integration_{page-name}"
  type: "figma-section-integration"
  sections_completed: [1, 2, 3, 4, 5]
  actions:
    - "Integrate variables → _variables.scss"
    - "Add vite.config.js entry"
    - "Create page template"
    - "Playwright full page verification"
```

## Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Preparation                                        │
├─────────────────────────────────────────────────────────────┤
│ 1. get_metadata for entire page structure                   │
│ 2. Extract top-level Frames as sections                     │
│ 3. Create nodeId mapping for each section                   │
│ 4. get_variable_defs for global variables                   │
│ 5. get_code_connect_map to check existing components        │
│ 6. Generate manifest.yaml                                   │
│ 7. Output worker task allocation                            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Section Implementation (Parallelizable)            │
├─────────────────────────────────────────────────────────────┤
│ Each worker implements assigned sections:                   │
│ 1. get_design_context for section details                   │
│ 2. Normalize naming (Figma name → kebab-case)              │
│ 3. Match against component-catalog.yaml                     │
│ 4. Generate SCSS (FLOCSS + BEM compliant)                  │
│ 5. Generate PHP (WordPress compliant)                       │
│ 6. Section-level Playwright verification                    │
│ 7. Report completion (including new variables/components)   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Integration                                        │
├─────────────────────────────────────────────────────────────┤
│ Integration worker executes:                                │
│ 1. Merge new variables into _variables.scss                 │
│ 2. Register new components in Code Connect                  │
│ 3. Update component-catalog.yaml                            │
│ 4. Create page template (section loading)                   │
│ 5. Add vite.config.js entry                                 │
│ 6. Verify with npm run build                                │
│ 7. Playwright full page verification                        │
│ 8. Run production-reviewer                                  │
└─────────────────────────────────────────────────────────────┘
```

## Naming Normalization Algorithm

### Figma Name → SCSS Class Name Conversion

```javascript
function normalizeToKebabCase(figmaName) {
  return figmaName
    .replace(/[\s\/]+/g, '-')          // Spaces/slashes → hyphen
    .replace(/([a-z])([A-Z])/g, '$1-$2') // camelCase → kebab-case
    .toLowerCase()
    .replace(/-+/g, '-')               // Multiple hyphens → single
    .replace(/^-|-$/g, '');            // Trim leading/trailing hyphens
}

function generateClassName(pageName, sectionName, figmaName, isReusable) {
  const normalized = normalizeToKebabCase(figmaName);
  if (isReusable) {
    return `c-${normalized}`;          // component (reusable)
  } else {
    return `p-${pageName}-${sectionName}`; // project (page-specific)
  }
}
```

### Conversion Examples

| Figma Name | Result | Type |
|------------|--------|------|
| `Button/Primary` | `c-button--primary` | component |
| `SectionHeading` | `c-section-heading` | component |
| `HeroSection` | `p-{page}-hero` | project |
| `ContentArea/Main` | `p-{page}-content-main` | project |

## Component Reuse Scoring

### Matching Score Calculation

```
score = (code_connect_match * 100) +  // Registered → instant 100%
        (type_match * 40) +           // Type match
        (props_coverage * 30) +       // Props coverage rate
        (variant_available * 20) +    // Variant support
        (pattern_match * 10)          // figma_patterns match
```

### Score Thresholds

| Score | Judgment | Action |
|-------|----------|--------|
| 100% | Code Connect registered | Use as-is |
| 80-99% | High match | Existing + add Modifier |
| 50-79% | Medium match | Existing base + custom styles |
| 0-49% | Low match | Create new component |

## Parallel Implementation Conflict Avoidance

### File Write Rules

| File Type | Write Permission |
|-----------|-----------------|
| Assigned section SCSS | Assigned worker only |
| Assigned section PHP | Assigned worker only |
| `_variables.scss` | Integration worker only (Phase 3) |
| `component-catalog.yaml` | Integration worker only (Phase 3) |
| `vite.config.js` | Integration worker only (Phase 3) |

### Playwright Exclusion Control

```yaml
# Record Playwright status
playwright_status:
  in_use: true
  section: "hero"
  started_at: "2026-01-30T13:00:00"
```

## Error Handling

| Error | Response |
|-------|----------|
| Section count > 8 | Warning + recommend manual split |
| Token limit exceeded | Split section further |
| Code Connect API error | Use cache + warning |
| Naming rule violation detected | Auto-fix + output warning |
| Conflicting file detected | Set task to blocked |

## Quality Verification Checklist

### Phase 2 Completion (Each Worker)

- [ ] SCSS is FLOCSS + BEM compliant
- [ ] Class names are kebab-case
- [ ] `@include container()` only (no other properties)
- [ ] Using `@include hover`
- [ ] PHP is WordPress compliant
- [ ] Output is escaped
- [ ] Section-level Playwright passes

### Phase 3 Completion (Integration Worker)

- [ ] New variables added to `_variables.scss`
- [ ] New components registered in Code Connect
- [ ] `component-catalog.yaml` updated
- [ ] `vite.config.js` entry added
- [ ] `npm run build` succeeds
- [ ] Playwright full page verification passes
- [ ] production-reviewer executed

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma/sections/` | Section-level cache |
| `.claude/data/component-catalog.yaml` | Component catalog |
| `.claude/rules/figma-workflow.md` | Figma workflow rules |
| `.claude/rules/scss.md` | SCSS naming rules |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Author**: Auto-generated
**Status**: Pending Approval
