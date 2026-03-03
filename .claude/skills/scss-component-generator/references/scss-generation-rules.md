# SCSS Generation Rules

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

## BEM Naming Rules

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

## Responsive Rules

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

## Base Style Duplication Prohibited

The following are defined in base styles - **DO NOT write**:
- `font-size: rv(16)` - body default
- `line-height: 1.6` - body default
- `letter-spacing: 0.08em` - body default

## Container Rules

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
