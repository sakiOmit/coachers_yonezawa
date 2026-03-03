---
name: scss-component-generator
description: "Generate FLOCSS-compliant SCSS components interactively, collecting component type (component/project/layout), BEM naming, and responsive settings to create standard-compliant SCSS files."
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - mcp__serena__read_memory
  - mcp__serena__search_for_pattern
context: fork
agent: general-purpose
---

# SCSS Component Generator

## Overview

Generate FLOCSS + BEM compliant SCSS components interactively. This skill collects component information through dialogue and automatically generates SCSS files following project conventions.

## Usage

```
/scss-component-generator
```

The skill will guide you through an interactive process to collect necessary information.

## Input Parameters

Collected interactively:

| Parameter | Required | Description |
|-----------|----------|-------------|
| Component Type | Yes | `component` (c-), `project` (p-), or `layout` (l-) |
| Component Name | Yes | kebab-case name |
| Page Name | Yes* | Page name for project components |
| Elements | Yes | BEM elements (comma-separated, kebab-case) |
| Modifiers | No | BEM modifiers (optional) |
| Responsive | Yes | Whether responsive styles are needed (yes/no) |

*Required only for `project` type

## Output

### File Locations

| Type | Output Path |
|------|-------------|
| Component | `src/scss/object/components/_c-{name}.scss` |
| Project | `src/scss/object/projects/{page}/_p-{page}-{name}.scss` |
| Layout | `src/scss/layout/_l-{name}.scss` |

### Entry File Update

Automatically adds `@use` to:
- `src/css/pages/{page}/style.scss`

## Processing Flow

```
1. Information Collection
   ├─ Component type (component / project / layout)
   ├─ Component name (kebab-case)
   ├─ Page name (for project type)
   ├─ Elements list (BEM Elements)
   ├─ Modifiers (optional)
   └─ Responsive requirement

2. Base Style Check
   └─ Use Serena MCP read_memory("base-styles-reference.md")
      to check for styles to avoid duplicating

3. Template-Based Code Generation
   └─ Use templates/ for SCSS code generation

4. File Output
   └─ Save to appropriate directory

5. Entry File Update
   └─ Add @use to style.scss if needed

6. Verification
   ├─ Run Stylelint check (npm run lint:css)
   └─ Guide user to next steps
```

## Component Types

### Component (c-)

Reusable generic components:

```scss
// Example: _c-button.scss
.c-button {
  // Base styles

  &__icon {
    // Element
  }

  &--primary {
    // Modifier
  }
}
```

### Project (p-)

Page-specific components:

```scss
// Example: _p-top-hero.scss
.p-top-hero {
  // Section-specific styles

  &__title {
    // Element
  }

  &__description {
    // Element
  }
}
```

### Layout (l-)

Layout-related components:

```scss
// Example: _l-header.scss
.l-header {
  // Layout styles

  &__container {
    @include container();
  }
}
```

## Generation Rules (Mandatory)

### BEM Naming Rules

- **Always use kebab-case** (camelCase, PascalCase prohibited)
- **Elements must use `&__` nesting** (top-level definition prohibited)
- **`&-` nesting prohibited**

```scss
// ✅ Correct
.p-example {
  &__main-visual {
    // styles
  }

  &__content-area {
    // styles
  }
}

// ❌ Prohibited
.p-example__mainVisual { }  // camelCase
.p-example { &-item { } }   // &- nesting
```

### Responsive

- **Default: PC styles**
- **Use `@include sp` for SP override**

```scss
.p-example {
  &__title {
    font-size: rv(32);

    @include sp {
      font-size: svw(24);
    }
  }
}
```

### Base Style Duplication Prohibited

The following are defined in base styles - **DO NOT write**:
- `font-size: rv(16)` - body default
- `line-height: 1.6` - body default
- `letter-spacing: 0.08em` - body default

### Container Rules

Classes containing `container` may **only** have `@include container()`:

```scss
.p-example {
  &__container {
    @include container(1200px);
    // Other properties prohibited
  }

  &__inner {
    // Layout properties go here
    display: flex;
    padding: rv(40);
  }
}
```

## Interactive Example

### Step 1: Start Skill

```
/scss-component-generator
```

### Step 2: Interactive Input

**Agent:**
```
Creating an SCSS component.

1. Select component type:
   - component (c-) - Reusable generic component
   - project (p-) - Page-specific section
   - layout (l-) - Layout related
```

**User:** `project`

**Agent:**
```
2. Enter page name (kebab-case)
Example: top, about, contact
```

**User:** `top`

**Agent:**
```
3. Enter component name (kebab-case)
Example: hero, news-list, contact-form
```

**User:** `hero`

**Agent:**
```
4. Enter elements (comma-separated, kebab-case)
Example: title, description, background-image, cta-button
```

**User:** `title, catch-copy, background, scroll-indicator`

**Agent:**
```
5. Do you need responsive support? (yes/no)
```

**User:** `yes`

### Step 3: Code Generation

Agent automatically generates SCSS file and saves to appropriate directory.

### Step 4: Completion Notification

```
✅ SCSS component created!

📁 File: src/scss/object/projects/top/_p-top-hero.scss
📝 Added @use to style.scss

Next steps:
1. Run npm run dev to verify build
2. Create corresponding PHP template
3. Adjust styles as needed
```

## Error Handling

| Error | Response |
|-------|----------|
| Filename conflict | Check existing files before creation |
| Invalid kebab-case | Validate input format |
| Stylelint error | Run check and report issues |
| Base style duplication | Warn user about redundant styles |

## Related Files

| File | Purpose |
|------|---------|
| `templates/` | SCSS templates for code generation |
| `docs/coding-guidelines/02-scss-design.md` | SCSS design guidelines |
| `.claude/rules/scss.md` | SCSS rules |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Original Author**: Team
**Migrated by**: Auto-generated
