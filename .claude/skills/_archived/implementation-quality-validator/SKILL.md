---
name: implementation-quality-validator
description: "Validates implementation quality: container structure, BEM naming, property order, ACF output patterns."
disable-model-invocation: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
context: fork
agent: general-purpose
---

# Implementation Quality Validator

## Overview

A skill that automatically validates WordPress + FLOCSS + BEM implementation quality.
Checks container structure, BEM naming conventions, SCSS property order, and ACF output patterns against project standards.

## Usage

```
/implementation-quality-validator [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--target <path>` | Target file or directory (default: all SCSS/PHP files) |
| `--check <type>` | Specific check: `container`, `bem`, `property-order`, `acf`, `variables`, or `all` (default) |
| `--fix` | Auto-fix simple issues (BEM naming, property order) |
| `--report <format>` | Output format: `text`, `json`, `yaml` (default: text) |

## Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| target | No | all | File/directory path to validate |
| check | No | all | Validation type |
| fix | No | false | Enable auto-fix |
| report | No | text | Output format |

## Processing Flow

```
1. Discovery Phase
   ├─ Find SCSS files: src/scss/**/*.scss
   ├─ Find PHP files: themes/**/*.php
   └─ Filter by target parameter if specified

2. Validation Phase
   ├─ Container Structure Check (SCSS)
   │   ├─ Find classes with "container" in name
   │   ├─ Check: @include container() present
   │   ├─ Check: No other properties (display, flex, gap, etc.)
   │   └─ Check: Corresponding __inner exists
   │
   ├─ BEM Naming Check (SCSS)
   │   ├─ Extract all class definitions
   │   ├─ Check: kebab-case format
   │   ├─ Check: No double underscores (__heading__en)
   │   └─ Check: Proper &__ nesting
   │
   ├─ Property Order Check (SCSS)
   │   ├─ Parse each ruleset
   │   ├─ Validate order: position → display → size → typography → visual
   │   └─ Compare against Stylelint rules
   │
   ├─ ACF Output Check (PHP)
   │   ├─ Find ACF get_field() calls
   │   ├─ Check single-line: <p> + esc_html()
   │   ├─ Check multi-line: <div> + wp_kses_post(nl2br())
   │   └─ Verify proper escaping
   │
   └─ CSS Variables Check (SCSS)
       ├─ Extract all hardcoded color values (#xxx, rgb(), rgba(), hsl())
       ├─ Count occurrences of each color across all SCSS files
       ├─ Check: Colors used 3+ times must use var(--color-*)
       ├─ Check: Colors used ≤2 times are allowed as hardcoded
       ├─ Extract all hardcoded font-family declarations
       └─ Check: All font-family must use var(--font-*)

3. Report Generation Phase
   ├─ Aggregate all issues by severity
   ├─ Generate fix suggestions
   └─ Output in requested format
```

## Validation Rules

### 1. Container Structure

**Rule**: `__container` class must have `@include container()` only.

**Valid**:
```scss
&__hero-container {
  @include container(1228px);
}

&__hero-inner {
  display: flex;
  gap: rv(80);
}
```

**Invalid**:
```scss
&__hero-container {
  @include container(1228px);
  display: flex;        // ❌ Not allowed
  gap: rv(80);          // ❌ Not allowed
}
```

### 2. BEM Naming

**Rule**: kebab-case with `&__` nesting, no double underscores.

**Valid**:
```scss
.p-section {
  &__hero-container {}
  &__hero-inner {}
  &__heading-en {}
  &__heading-title {}
}
```

**Invalid**:
```scss
.p-section {
  &__heading {
    &__en {}           // ❌ Creates __heading__en
  }
  &__heroContainer {}  // ❌ camelCase
  &__hero_inner {}     // ❌ snake_case
}
```

### 3. Property Order

**Rule**: Follow Stylelint order.

**Order**:
1. position, z-index, top, right, bottom, left
2. display, flex-*, gap, align-*, justify-*
3. width, height, margin, padding
4. font-*, line-height, letter-spacing, color
5. background, border, box-shadow
6. transition, transform, other

### 4. ACF Output Pattern

**Rule**: Use appropriate HTML tag and escaping function.

**Single-line fields**:
```php
<p class="__field-value"><?php echo esc_html($work_location); ?></p>
```

**Multi-line fields**:
```php
<div class="__field-value"><?php echo wp_kses_post(nl2br($job_description)); ?></div>
```

### 5. CSS Variables Usage

**Rule**: Colors used 3+ times must use CSS Custom Properties. Font-family must always use variables.

**Detection**:
1. Grep all SCSS files for hardcoded colors: `#[0-9a-fA-F]{3,8}`, `rgb(`, `rgba(`, `hsl(`
2. Count occurrences of each unique color value across the project
3. Colors with count >= 3 that don't use `var(--color-*)` → Error
4. Grep all `font-family:` declarations
5. Any `font-family` not using `var(--font-*)` → Error

**Valid**:
```scss
.p-card__title {
  color: var(--color-primary);
  font-family: var(--font-secondary);
}

.p-special__accent {
  border-color: #e8d5a3;  // ✅ Used only once in project
}
```

**Invalid**:
```scss
// ❌ #195162 appears 5 times across project → must use var(--color-primary)
.p-hero__title {
  color: #195162;
}

// ❌ font-family must always use variable
.p-section__heading {
  font-family: "Georgia", serif;
}
```

**Severity**:
| Condition | Severity |
|-----------|----------|
| Color used 3+ times, hardcoded | Error |
| Font-family hardcoded | Error |
| Color used ≤2 times, hardcoded | OK (no issue) |

**Exclusions**:
- `_variables.scss` (variable definitions themselves)
- Comments
- `#fff`, `#000`, `transparent`, `inherit`, `currentColor` (common keywords)

## Output Format

### Text Report (Default)

```markdown
# Implementation Quality Validation Report

## Summary

| Check | Passed | Failed | Total |
|-------|--------|--------|-------|
| Container Structure | 8 | 2 | 10 |
| BEM Naming | 15 | 5 | 20 |
| Property Order | 12 | 3 | 15 |
| ACF Output | 10 | 0 | 10 |
| CSS Variables | 18 | 4 | 22 |

**Overall**: 45/55 checks passed (82%)

---

## Issues by Severity

### 🔴 Error (10 issues)

#### Container Structure (2)

1. `src/scss/object/project/_p-about.scss:25`
   - Issue: `&__hero-container` has `display: flex` property
   - Expected: Only `@include container()` allowed
   - Fix: Move layout properties to `&__hero-inner`

2. `src/scss/object/project/_p-about.scss:26`
   - Issue: `&__hero-container` has `gap: rv(80)` property
   - Expected: Only `@include container()` allowed
   - Fix: Move layout properties to `&__hero-inner`

#### BEM Naming (5)

1. `src/scss/object/components/_c-card.scss:15`
   - Issue: `&__heading__title` (double underscore)
   - Expected: `&__heading-title`
   - Fix: Use hyphen instead of nesting

### ⚠️ Warning (0 issues)

---

## Auto-fix Available

The following issues can be auto-fixed with `--fix`:

- BEM naming (5 issues)
- Property order (3 issues)

Run: `/implementation-quality-validator --fix`
```

### JSON Report

```json
{
  "summary": {
    "total_checks": 55,
    "passed": 45,
    "failed": 10,
    "pass_rate": 0.82
  },
  "by_check": {
    "container_structure": { "passed": 8, "failed": 2 },
    "bem_naming": { "passed": 15, "failed": 5 },
    "property_order": { "passed": 12, "failed": 3 },
    "acf_output": { "passed": 10, "failed": 0 }
  },
  "issues": [
    {
      "severity": "error",
      "check": "container_structure",
      "file": "src/scss/object/project/_p-about.scss",
      "line": 25,
      "issue": "&__hero-container has display: flex property",
      "expected": "Only @include container() allowed",
      "fix": "Move layout properties to &__hero-inner"
    }
  ]
}
```

## Error Handling

| Error | Response |
|-------|----------|
| Target file not found | Report error, skip file |
| Permission denied | Report error, skip file |
| Invalid SCSS syntax | Report parsing error, continue |
| Stylelint not installed | Skip property order check, warn |
| Empty directory | Report 0 files, no error |

## Auto-fix Capabilities

### BEM Naming

- Double underscore → Hyphen: `&__heading__en` → `&__heading-en`
- camelCase → kebab-case: `&__heroContainer` → `&__hero-container`
- snake_case → kebab-case: `&__hero_inner` → `&__hero-inner`

### Property Order

- Reorder properties according to Stylelint rules
- Preserve comments and grouping where possible

### Limitations

- Cannot auto-fix: Container structure issues (requires manual refactoring)
- Cannot auto-fix: ACF output patterns (requires context understanding)

## Examples

### Example 1: Full validation

```
/implementation-quality-validator
```

Validates all SCSS and PHP files in the project.

### Example 2: Specific file

```
/implementation-quality-validator --target src/scss/object/project/_p-about.scss
```

### Example 3: Container check only

```
/implementation-quality-validator --check container
```

### Example 4: Auto-fix BEM issues

```
/implementation-quality-validator --check bem --fix
```

### Example 5: JSON output

```
/implementation-quality-validator --report json
```

## Integration

### With production-reviewer

Use as pre-check before `production-reviewer`:

```
1. /implementation-quality-validator --fix
2. /production-reviewer
```

### With Figma workflow

Add to `figma-implement` Step 8 (Verification):

```
1. /implementation-quality-validator --target {generated-files}
2. Fix issues
3. production-reviewer
```

### CI/CD Integration

```bash
# .github/workflows/quality-check.yml
- name: Implementation Quality Check
  run: |
    claude-code skill implementation-quality-validator \
      --report json > quality-report.json
```

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/commit-records/2026-01-31_requirements-single-reference.json` | Reference implementation patterns |
| `.claude/rules/scss.md` | SCSS coding standards |
| `.claude/rules/wordpress.md` | WordPress/ACF standards |
| `.stylelintrc.json` | Property order configuration |

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `production-reviewer` | Comprehensive review (includes this + more) |
| `code-fixer` | Auto-fixes issues detected by this skill |
| `figma-implement` | Uses this for Step 8 validation |

---

**Version**: 1.0.0
**Created**: 2026-01-31
**Proposer**: Ashigaru 1 (cmd_008, task_cmd007_1)
