---
name: acf-field-generator
description: "Interactive ACF field group generator that collects field types, names, and labels through dialogue and generates PHP code."
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
context: fork
agent: general-purpose
---

# ACF Field Generator

## Overview

A skill that interactively generates Advanced Custom Fields (ACF) field group definitions.
Collects field information through dialogue and outputs PHP code following WordPress/ACF conventions.

## Usage

```
/acf-field-generator
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| (interactive) | Yes | All information is collected through dialogue |

### Information Collected

**Basic Information:**
- Field group name (Japanese)
- Field group key (e.g., `group_example`)
- Location (custom post type, page template, options page, taxonomy)

**Field Information (repeated):**
- Field label (Japanese)
- Field name (English, snake_case)
- Field type (text, textarea, image, select, etc.)
- Required flag
- Placeholder (optional)
- Instructions (optional)

## Output

### Generated Files

PHP field group definition file saved to appropriate directory:

| Location Type | Output Path |
|---------------|-------------|
| Custom Post Type | `themes/{THEME}/inc/advanced-custom-fields/groups/post-types/` |
| Options Page | `themes/{THEME}/inc/advanced-custom-fields/groups/options/` |
| Taxonomy | `themes/{THEME}/inc/advanced-custom-fields/groups/taxonomies/` |
| Page Template | `themes/{THEME}/inc/advanced-custom-fields/groups/pages/` |

### config.php Update

Automatically adds the new file to `themes/{THEME}/inc/advanced-custom-fields/groups/config.php`.

## Processing Flow

```
1. Information Collection (Interactive)
   ├─ Field group name input
   ├─ Field group key input
   ├─ Location selection
   └─ Field definitions (repeated)

2. Template-Based Code Generation
   └─ Use templates/field-group.php.template

3. File Output
   └─ Save to appropriate directory

4. config.php Update
   └─ Add new file to config

5. Verification
   ├─ PHP syntax check
   └─ Guide user to next steps
```

## Supported Field Types (ACF Free)

| Type | Description |
|------|-------------|
| `text` | Single line text |
| `textarea` | Multi-line text |
| `number` | Number |
| `email` | Email address |
| `url` | URL |
| `password` | Password |
| `wysiwyg` | Rich text editor |
| `image` | Image upload |
| `file` | File upload |
| `select` | Select dropdown |
| `checkbox` | Checkbox |
| `radio` | Radio button |
| `true_false` | Toggle switch |
| `date_picker` | Date picker |
| `color_picker` | Color picker |
| `message` | Message display |
| `tab` | Tab separator |

**Pro Version Only (Not Supported):**
- `repeater` - Repeater field
- `flexible_content` - Flexible content
- `gallery` - Gallery
- `clone` - Clone field

## Error Handling

| Error | Response |
|-------|----------|
| Key duplication | Check existing files, prompt for new key |
| PHP syntax error | Run syntax check, display error |
| config.php syntax | Validate before update |

## Template Variables

The `templates/field-group.php.template` uses the following variables:

| Variable | Description |
|----------|-------------|
| `{{GROUP_KEY}}` | Field group key |
| `{{GROUP_TITLE}}` | Field group name |
| `{{FIELDS}}` | Field array (JSON format) |
| `{{LOCATION_PARAM}}` | Location parameter |
| `{{LOCATION_VALUE}}` | Location value |

## Related Files

| File | Purpose |
|------|---------|
| `templates/field-group.php.template` | PHP template for field groups |
| `themes/{THEME}/inc/advanced-custom-fields/groups/config.php` | ACF groups configuration |

## Examples

### Step 1: Start Skill

```
/acf-field-generator
```

### Step 2: Interactive Input

**Agent:**
```
Creating ACF field group.

1. What is the field group name (Japanese)?
Example: Product Information
```

**User:**
```
Job Details
```

**Agent:**
```
2. Enter the field group key (alphanumeric and underscore)
Recommended: group_job_detail
```

**User:**
```
group_job_detail
```

(Continues with location and field definitions...)

### Step 3: Completion

```
✅ ACF field group created!

📁 File: themes/{THEME}/inc/advanced-custom-fields/groups/post-types/job-detail.php
📝 Added to config.php

Next steps:
1. Log in to WordPress admin
2. Verify fields appear on the post type edit screen
3. Add validation rules as needed
```

## Future Enhancements

- Field preset feature (commonly used field sets)
- Auto-generate validation rules
- Template part reference feature

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Migrated from**: skill.json + instructions.md
