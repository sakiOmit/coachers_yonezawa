---
name: figma-text-extractor
description: "Extract text content from Figma get_design_context response and save to cache for implementation verification."
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Glob
  - mcp__figma__get_design_context
context: fork
agent: general-purpose
---

# Figma Text Extractor

## Overview

A skill that automatically extracts text content from Figma `get_design_context` responses, including position information and node IDs, and saves it to cache for implementation verification.

### Background

During Figma-to-code implementation, text content can be misread or misinterpreted:
- Button text "インタビューを見る" read as "インタビューー" (typo)
- Text position within sections not clearly identified
- Lack of reference data for implementation verification

This skill prevents these issues by:
- Extracting all text elements from Figma design context
- Recording accurate text content with node IDs
- Enabling cross-reference during implementation

## Usage

```
/figma-text-extractor --page thanks --fileKey wbpri0A53IqL1KvkRBtvkl --nodeId 1:2220
```

Or extract from existing cache:

```
/figma-text-extractor --cache-path .claude/cache/figma/thanks_pc_context.json
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| --page | Yes | Page name (e.g., "thanks", "home") |
| --fileKey | Conditional | Figma file key (required if fetching fresh) |
| --nodeId | Conditional | Figma node ID (required if fetching fresh) |
| --cache-path | Conditional | Path to existing cached get_design_context JSON |
| --output | No | Output path (default: .claude/cache/figma/{page}/text-extracted.json) |
| --format | No | Output format: `json`, `markdown`, `both` (default: json) |

**Note**: Either (`--fileKey` + `--nodeId`) OR `--cache-path` is required.

## Output

### text-extracted.json Format

```json
{
  "metadata": {
    "fileKey": "wbpri0A53IqL1KvkRBtvkl",
    "nodeId": "1:2220",
    "pageName": "thanks",
    "extractedAt": "2026-01-30T17:45:21",
    "totalTexts": 8
  },
  "texts": [
    {
      "nodeId": "1:2345",
      "text": "インタビューを見る",
      "type": "button",
      "parentSection": "CTA Section",
      "position": {
        "x": 560,
        "y": 820
      },
      "styles": {
        "fontSize": 16,
        "fontFamily": "Noto Sans JP",
        "fontWeight": 700
      }
    },
    {
      "nodeId": "1:2346",
      "text": "ご応募ありがとうございます",
      "type": "heading",
      "parentSection": "Main Content",
      "position": {
        "x": 120,
        "y": 200
      },
      "styles": {
        "fontSize": 36,
        "fontFamily": "Noto Serif JP",
        "fontWeight": 700
      }
    }
  ],
  "sections": [
    {
      "name": "CTA Section",
      "nodeId": "1:2340",
      "textCount": 1
    },
    {
      "name": "Main Content",
      "nodeId": "1:2200",
      "textCount": 4
    }
  ]
}
```

### Markdown Output Format

```markdown
# Figma Text Extraction Report

**Page**: thanks
**File Key**: wbpri0A53IqL1KvkRBtvkl
**Node ID**: 1:2220
**Extracted**: 2026-01-30T17:45:21
**Total Texts**: 8

## Text Elements

### CTA Section (1:2340)

| Node ID | Text | Type | Font | Size |
|---------|------|------|------|------|
| 1:2345 | インタビューを見る | button | Noto Sans JP | 16px |

### Main Content (1:2200)

| Node ID | Text | Type | Font | Size |
|---------|------|------|------|------|
| 1:2346 | ご応募ありがとうございます | heading | Noto Serif JP | 36px |
| 1:2347 | このたびはご応募いただき... | paragraph | Noto Sans JP | 16px |

---

**Note**: Use this reference during implementation to verify accurate text content.
```

## Processing Flow

```
1. Input Validation
   ├─ Validate required parameters (page + fileKey/nodeId OR cache-path)
   └─ Check cache directory exists

2. Design Context Acquisition
   ├─ If cache-path provided: Read existing JSON
   └─ If fileKey/nodeId provided: Call mcp__figma__get_design_context

3. Text Extraction
   ├─ Parse design context JSON
   ├─ Identify text nodes (type: TEXT, or text property exists)
   ├─ Extract text content
   ├─ Extract node ID
   ├─ Extract position (x, y)
   ├─ Extract styles (fontSize, fontFamily, fontWeight)
   └─ Identify parent section

4. Section Grouping
   ├─ Group text elements by parent frame
   ├─ Identify section names from parent frame names
   └─ Count texts per section

5. Data Structuring
   ├─ Build metadata object
   ├─ Build texts array
   └─ Build sections array

6. Output Generation
   ├─ If format=json: Write JSON file
   ├─ If format=markdown: Write Markdown file
   └─ If format=both: Write both formats

7. Verification
   ├─ Verify file written successfully
   ├─ Output file path
   └─ Display extraction summary

8. Exit Code
   ├─ 0: Success
   ├─ 1: Validation error (missing parameters)
   └─ 2: Extraction error (invalid JSON, API failure)
```

## Text Node Identification

### Detection Logic

```
1. Check node type:
   - node.type === "TEXT"
   - node.characters exists (Figma text property)

2. Extract text content:
   - Use node.characters as primary source
   - Fallback to node.name if characters unavailable

3. Determine text type:
   - Check parent node name for keywords:
     - "Button" → type: "button"
     - "Heading", "Title", "h1", "h2" → type: "heading"
     - "Paragraph", "Text", "Body" → type: "paragraph"
     - "Label" → type: "label"
   - Default: type: "text"

4. Parent section identification:
   - Traverse up node tree
   - Find first FRAME or SECTION node
   - Use frame name as section name
```

## Error Handling

| Error | Response |
|-------|----------|
| Missing required parameters | Output error message and exit with code 1 |
| Cache file not found | Output error message and exit with code 2 |
| Invalid JSON in cache | Output parse error with line number and exit with code 2 |
| Figma API failure | Output API error message and exit with code 2 |
| Permission denied (write) | Output permission error and exit with code 2 |
| Empty text extraction | Warning only, write empty texts array |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma/` | Figma design context cache directory |
| `.claude/rules/figma.md` | Figma implementation workflow rules |
| `figma-implement.md` | Figma implementation command |

## Examples

### Extract from Fresh API Call

```bash
/figma-text-extractor \
  --page thanks \
  --fileKey wbpri0A53IqL1KvkRBtvkl \
  --nodeId 1:2220
```

### Extract from Existing Cache

```bash
/figma-text-extractor \
  --page thanks \
  --cache-path .claude/cache/figma/thanks_pc_context.json
```

### Extract with Markdown Output

```bash
/figma-text-extractor \
  --page thanks \
  --fileKey wbpri0A53IqL1KvkRBtvkl \
  --nodeId 1:2220 \
  --format both
```

### Batch Extraction for Multiple Pages

```bash
# Extract PC version
/figma-text-extractor --page thanks --nodeId 1:2220 --fileKey xxx

# Extract SP version
/figma-text-extractor --page thanks-sp --nodeId 1:5895 --fileKey xxx
```

## Use Cases

### 1. Pre-Implementation Reference

```bash
# Before implementing /thanks page
/figma-text-extractor --page thanks --nodeId 1:2220 --fileKey xxx

# Review extracted text in markdown
cat .claude/cache/figma/thanks/text-extracted.md

# Implement page with accurate text reference
```

### 2. Post-Implementation Verification

```bash
# Extract Figma text
/figma-text-extractor --page thanks --cache-path .claude/cache/figma/thanks_pc.json

# Compare with implemented code
grep "インタビューを見る" themes/{{THEME_NAME}}/pages/page-thanks.php

# Expected: Exact match
```

### 3. Text Content Changelog

```bash
# Extract current version
/figma-text-extractor --page thanks --nodeId 1:2220 --fileKey xxx \
  --output .claude/cache/figma/thanks/text-v1.json

# After Figma update, extract again
/figma-text-extractor --page thanks --nodeId 1:2220 --fileKey xxx \
  --output .claude/cache/figma/thanks/text-v2.json

# Compare versions
diff .claude/cache/figma/thanks/text-v{1,2}.json
```

### 4. Multi-Language Content Extraction

```bash
# Extract Japanese version
/figma-text-extractor --page thanks-ja --nodeId 1:2220 --fileKey xxx

# Extract English version
/figma-text-extractor --page thanks-en --nodeId 1:8000 --fileKey xxx

# Compare text content for translation QA
```

## Integration with Workflow

### Recommended Integration Points

| Workflow Step | Action |
|---------------|--------|
| After get_design_context | Run figma-text-extractor to cache text |
| Before PHP/SCSS implementation | Review text-extracted.md for reference |
| After implementation | Compare extracted text with code |
| During code review | Use as verification checklist |

### Example Workflow

```
1. Figma implementation task assigned
2. Run get_design_context (PC/SP)
3. ✅ Run figma-text-extractor (PC/SP)
4. Review text-extracted.md
5. Implement PHP template with accurate text
6. Verify text matches extracted reference
7. Run production-reviewer
```

## Output Directory Structure

```
.claude/cache/figma/
├── thanks/
│   ├── text-extracted.json      # Primary output
│   ├── text-extracted.md        # Markdown format (optional)
│   └── pc_context.json          # Original design context
├── home/
│   ├── text-extracted.json
│   └── sp_context.json
└── interview/
    └── text-extracted.json
```

## Related Skills

| Skill | Integration |
|-------|-------------|
| figma-implement | Run text-extractor before implementation |
| production-reviewer | Use extracted text for verification |
| figma-visual-diff-runner | Complement text verification with visual diff |

## Limitations

| Limitation | Workaround |
|------------|------------|
| Cannot detect text in images | Manual verification required |
| Rich text formatting may be simplified | Check Figma design for complex formatting |
| Nested text elements may be flattened | Review parent-child relationships manually |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Author**: Auto-generated
**Purpose**: Prevent text content misreading during Figma-to-code implementation
