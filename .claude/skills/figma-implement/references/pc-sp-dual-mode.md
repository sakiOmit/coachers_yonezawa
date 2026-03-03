# PC/SP Dual Implementation Mode

Detailed documentation for implementing both PC and SP designs from Figma.

## Overview

When `--sp` option is provided, the skill retrieves and implements both PC and SP designs, ensuring SP styles are based on actual Figma SP specs rather than guesswork.

## Usage

```bash
/figma-implement {pc_url} --sp {sp_url}
```

## Workflow Differences

### Standard Mode (PC only)

```
Step 2: get_design_context (PC)
Step 3: get_screenshot (PC)
Step 5: Generate specs (PC only)
Step 6: Implement with PC values
        → SP values are GUESSED based on conventions
Step 7: Validate against PC Figma
        → SP validation uses "lenient" preset
```

### Dual Mode (PC + SP)

```
Step 2: get_design_context (PC)
Step 2b: get_design_context (SP)
Step 3: get_screenshot (PC)
Step 3b: get_screenshot (SP)
Step 5: Generate specs (PC)
Step 5b: Generate PC/SP diff table
Step 6: Implement with PC values
        → SP values from ACTUAL Figma SP specs
Step 7: Validate against PC Figma
Step 7b: Validate against SP Figma (direct comparison)
```

## PC/SP Diff Table

Generated in Step 5b:

```markdown
## PC/SP 差分仕様

| 要素 | PC | SP | 差分タイプ |
|------|----|----|-----------|
| .p-hero__title | font-size: 48px | font-size: 24px | サイズ変更 |
| .p-hero__container | max-width: 1200px | max-width: 100% | レイアウト変更 |
| .p-cards | grid-template-columns: repeat(3, 1fr) | grid-template-columns: 1fr | カラム変更 |
| .p-nav | display: flex | display: none | 表示切替 |
```

### Diff Types

| Type | Description | SCSS Pattern |
|------|-------------|--------------|
| サイズ変更 | font-size, width, height, padding, margin | `@include sp { font-size: svw(24); }` |
| レイアウト変更 | max-width, flex-direction, grid | `@include sp { max-width: 100%; }` |
| カラム変更 | grid-template-columns | `@include sp { grid-template-columns: 1fr; }` |
| 表示切替 | display: none/block | `@include sp { display: none; }` |
| 順序変更 | flex order | `@include sp { order: 2; }` |

## Implementation Example

### With Dual Mode (Recommended)

```scss
.p-hero__title {
  font-size: rv(48);    // PC: from Figma PC

  @include sp {
    font-size: svw(24); // SP: from Figma SP (NOT guessed)
  }
}

.p-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);  // PC: from Figma PC

  @include sp {
    grid-template-columns: 1fr;  // SP: from Figma SP (NOT guessed)
  }
}
```

### Without Dual Mode (Standard)

```scss
.p-hero__title {
  font-size: rv(48);    // PC: from Figma PC

  @include sp {
    font-size: svw(28); // SP: GUESSED (may be wrong)
  }
}
```

## Validation Differences

### Standard Mode SP Validation

```bash
# Compare WordPress SP against PC Figma (lenient)
node scripts/visual-diff.js \
  figma_section_pc.png \
  wp_section_sp.png \
  --preset lenient  # Higher tolerance because comparing PC design
```

### Dual Mode SP Validation

```bash
# Compare WordPress SP against SP Figma (default)
node scripts/visual-diff.js \
  figma_section_sp.png \
  wp_section_sp.png \
  --preset default  # Standard tolerance for accurate comparison
```

## Cache Structure

### Standard Mode

```
.claude/cache/figma/{page}/
├── metadata.json
├── design-context.json
└── prefetch-info.yaml
```

### Dual Mode

```
.claude/cache/figma/{page}/
├── pc/
│   ├── metadata.json
│   ├── design-context.json
│   └── text-extracted.json
├── sp/
│   ├── metadata.json
│   ├── design-context.json
│   └── text-extracted.json
├── pc-sp-diff.json
└── prefetch-info.yaml
```

## State File Structure

### Dual Mode State

```yaml
pc_url: "https://figma.com/design/..."
pc_file_key: "abc123"
pc_node_id: "1:2"
pc_cache: ".claude/cache/figma/{page}/pc/"

sp_url: "https://figma.com/design/..."
sp_file_key: "abc123"
sp_node_id: "3:4"
sp_cache: ".claude/cache/figma/{page}/sp/"

dual_mode: true

current_step: "Step2"
step_status:
  Step2:
    pc: completed
    sp: in_progress
```

## Benefits

| Aspect | Standard Mode | Dual Mode |
|--------|--------------|-----------|
| SP accuracy | Guessed from conventions | Exact from Figma SP |
| SP validation | Compared against PC | Compared against SP |
| Diff detection | Manual review | Automatic |
| Implementation time | Faster | Slightly slower |
| Quality | Good | Excellent |

## When to Use Dual Mode

| Situation | Recommendation |
|-----------|---------------|
| Designer provided both PC and SP | ✅ Use dual mode |
| SP significantly differs from PC | ✅ Use dual mode |
| SP has unique elements | ✅ Use dual mode |
| SP is simple responsive | Standard mode OK |
| Quick prototype | Standard mode OK |

## Troubleshooting

### Error: "SP cache not found"

The SP URL was provided but cache is missing.

**Solution:**
```bash
/figma-prefetch {pc_url} --sp {sp_url} --force
```

### Error: "PC/SP structure mismatch"

Different number of sections in PC and SP.

**Solution:**
1. Verify SP URL is correct version
2. Map sections manually if intentionally different
3. Use `--ignore-structure-diff` flag if acceptable

### Error: "SP validation failing"

SP implementation doesn't match Figma SP.

**Solution:**
1. Check the diff image at `.claude/cache/visual-diff/diff_*_sp.png`
2. Verify SP values in SCSS match diff table
3. Common cause: Using PC values instead of SP values
