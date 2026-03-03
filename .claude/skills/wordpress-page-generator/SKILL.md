---
name: wordpress-page-generator
description: "Generate WordPress page templates interactively with PHP template, SCSS structure, and build configuration"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - mcp__serena__read_memory
  - mcp__serena__search_for_pattern
  - mcp__serena__find_symbol
context: fork
agent: general-purpose
---

# WordPress Page Generator

## Overview

Generate WordPress fixed page templates interactively. This skill collects page name, section structure, and ACF fields through dialogue, then generates PHP templates, SCSS structure, and build configuration in compliance with project conventions.

## Usage

```
/wordpress-page-generator
```

The skill will guide you through an interactive dialogue to collect:
- Page name (Japanese)
- Page slug (kebab-case)
- Section list
- Estimated line count (for split decision)

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| (interactive) | Yes | Page name in Japanese |
| (interactive) | Yes | Page slug in kebab-case (e.g., about, contact) |
| (interactive) | Yes | Section list (comma-separated) |
| (interactive) | Yes | Estimated line count (200+ triggers split) |

## Output

### Generated Files

**PHP Templates:**
- `themes/{{THEME_NAME}}/pages/page-{slug}.php`
- `themes/{{THEME_NAME}}/template-parts/{slug}/` (if 200+ lines)

**SCSS Structure:**
- `src/scss/object/projects/{slug}/` directory
- `_p-{slug}.scss` - main file
- `_p-{slug}-{section}.scss` - section files

**Entry Point:**
- `src/css/pages/{slug}/style.scss`

### Updated Files

- `vite.config.js` - entry addition
- `themes/{{THEME_NAME}}/inc/enqueue.php` - conditional enqueue

## Processing Flow

```
1. Information Collection (Interactive)
   ├─ Page name (Japanese)
   ├─ Page slug (kebab-case)
   ├─ Section list
   └─ Estimated line count

2. Existing Pattern Check
   ├─ find_symbol: Check existing page structure
   └─ read_memory: Confirm base styles

3. File Generation
   ├─ PHP templates (single or split)
   ├─ SCSS directory structure
   └─ Entry point file

4. Build Configuration Update
   ├─ vite.config.js entry
   └─ enqueue.php conditional

5. Verification
   ├─ PHP syntax check
   ├─ Directory structure confirmation
   └─ Next steps guidance
```

## Generation Rules (Mandatory)

### Section Naming Convention

**Independent Block naming required:** `p-{page}-{section}`

```php
// ✅ Correct
<section class="p-about-hero">
<section class="p-about-mission">

// ❌ Forbidden
<section class="p-about__hero">
<section class="p-about__mission">
```

### Page Template Structure

```php
<?php
/**
 * Template Name: Page Name
 *
 * @package Theme
 */

get_header();
?>

<main class="l-main">
  <section class="p-{slug}-hero">
    <div class="p-{slug}-hero__container">
      <!-- Content -->
    </div>
  </section>
</main>

<?php get_footer(); ?>
```

### SCSS File Structure

```
src/scss/object/projects/{slug}/
├── _p-{slug}.scss           # Import only (@use)
├── _p-{slug}-hero.scss      # hero section
├── _p-{slug}-about.scss     # about section
└── _p-{slug}-contact.scss   # contact section
```

### Entry File

```scss
// src/css/pages/{slug}/style.scss
@use "../../../scss/object/projects/{slug}/p-{slug}";
```

## Error Handling

| Error | Response |
|-------|----------|
| Slug duplicate | Check existing files, prompt for different slug |
| Invalid kebab-case | Validate and prompt correction |
| PHP syntax error | Run syntax check, report issues |
| vite.config.js syntax error | Validate before update |
| Permission error | Set file permissions to 644 |

## Related Files

| File | Purpose |
|------|---------|
| `docs/coding-guidelines/05-checklist.md` | New page checklist |
| `docs/coding-guidelines/03-wordpress-integration.md` | WordPress conventions |
| `docs/coding-guidelines/04-build-configuration.md` | Build settings |

## Examples

### Example: Creating a Recruit Page

**Step 1: Start skill**
```
/wordpress-page-generator
```

**Step 2: Interactive input**
```
Agent: Enter page name (Japanese):
User: 採用情報

Agent: Enter page slug (kebab-case):
User: recruit

Agent: Enter sections (comma-separated):
User: hero, message, positions, benefits, faq, entry

Agent: Estimated line count?
User: 300
```

**Step 3: Confirmation**
```
Agent: Will generate with template-parts split:

📁 themes/{{THEME_NAME}}/pages/page-recruit.php
📁 themes/{{THEME_NAME}}/template-parts/recruit/
   ├── hero.php
   ├── message.php
   ├── positions.php
   ├── benefits.php
   ├── faq.php
   └── entry.php
📁 src/scss/object/projects/recruit/ (7 files)
📁 src/css/pages/recruit/style.scss

Continue? (yes/no)
```

**Step 4: Generation complete**
```
✅ WordPress page template created!

Next steps:
1. Run npm run dev to verify build
2. Create fixed page in WordPress, select template
3. Implement each section PHP/SCSS
4. Use /acf-field-generator for ACF fields if needed
```

## Related Skills

| Skill | Purpose |
|-------|---------|
| `acf-field-generator` | Generate ACF fields |
| `scss-component-generator` | Add SCSS components |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Original Author**: Theme Development Team
