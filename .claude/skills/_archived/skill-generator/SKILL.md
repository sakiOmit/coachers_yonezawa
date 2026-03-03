---
name: skill-generator
description: "Interactive skill generator following Claude Code best practices. Use when user says 'create a skill', 'generate new skill', 'make a custom skill', or wants to scaffold a new SKILL.md file."
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
context: fork
agent: general-purpose
---

# Skill Generator

## Overview

Interactive skill generator that creates Claude Code skills following official SKILL.md format and project best practices.
Guides the user through a step-by-step process to define skill parameters, generates the complete SKILL.md file, and optionally creates supporting scripts.

### Key Features

- **Interactive Guidance**: Step-by-step parameter collection with intelligent defaults
- **Best Practice Templates**: Based on proven patterns from existing skills (figma-implement, figma-prefetch, etc.)
- **Validation**: Automatic validation of generated SKILL.md against project rules
- **Script Generation**: Optional Bash script generation for validation/automation steps
- **Documentation Integration**: Automatic catalog update and related file linking

## Usage

```
/skill-generator [skill-name]
```

### With Options

```
/skill-generator [skill-name] [options]

Options:
  --template {type}     Use predefined template (orchestrator|validator|transformer|simple)
  --with-scripts        Generate supporting Bash scripts
  --no-validation       Skip validation step (not recommended)
  --dry-run             Show generated content without writing files
  --interactive         Request confirmation at each step (default: true)
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| skill-name | No | Target skill name (kebab-case). If not provided, will prompt interactively |
| --template | No | Predefined template type (default: simple) |
| --with-scripts | No | Generate supporting Bash scripts |
| --no-validation | No | Skip validation step |
| --dry-run | No | Preview mode, no file creation |
| --interactive | No | Interactive mode (default: true) |

## Processing Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  Step 1: Skill Name & Type          │
│  ├─ Ask: Skill name (kebab-case)    │
│  ├─ Ask: Skill type (template)      │
│  └─ Validate: name uniqueness       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Step 2: YAML Frontmatter           │
│  ├─ Ask: Description (1 sentence)   │
│  ├─ Ask: Trigger phrases            │
│  ├─ Ask: Allowed tools              │
│  ├─ Ask: Context (fork/no-fork)     │
│  └─ Ask: Agent type                 │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Step 3: Content Structure          │
│  ├─ Overview section                │
│  ├─ Prerequisites (if needed)       │
│  ├─ Usage examples                  │
│  ├─ Input parameters table          │
│  ├─ Processing flow diagram         │
│  └─ Error handling catalog          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Step 4: Optional Components        │
│  ├─ Human intervention points       │
│  ├─ State management                │
│  ├─ Script generation               │
│  └─ Related files section           │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Step 5: File Generation            │
│  ├─ Create SKILL.md                 │
│  ├─ Create scripts/ directory       │
│  ├─ Generate validation scripts     │
│  └─ Create references/ directory    │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Step 6: Validation                 │
│  ├─ YAML frontmatter check          │
│  ├─ Required sections check         │
│  ├─ Best practices compliance       │
│  └─ Run skill-yaml-validator        │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│  Step 7: Integration                │
│  ├─ Update skill catalog            │
│  ├─ Add to related workflows        │
│  └─ Generate completion report      │
└─────────────────────────────────────┘
  │
  ▼
COMPLETE
```

## Skill Templates

### 1. Orchestrator (Complex Workflow)

For multi-step workflow skills like `figma-implement`.

**Features:**
- State management (YAML persistence)
- Resume capability
- Human intervention points
- Error recovery
- Progress tracking
- Step-by-step flow diagram

**Example Use Case:**
- Multi-step implementation workflows
- Long-running processes with checkpoints
- Complex coordination tasks

### 2. Validator (Quality Check)

For validation/quality check skills like `figma-cache-validator`.

**Features:**
- Exit code handling
- Validation criteria table
- Error catalog
- Script integration
- Pass/fail reporting

**Example Use Case:**
- Pre-flight checks
- Quality gates
- Data validation

### 3. Transformer (Data Processing)

For data transformation skills like `figma-design-tokens-extractor`.

**Features:**
- Input/output format specs
- Transformation rules
- Mapping tables
- Error handling

**Example Use Case:**
- Format conversion
- Data extraction
- Code generation

### 4. Simple (Single Task)

For straightforward single-purpose skills.

**Features:**
- Direct execution
- Minimal state
- Clear input/output
- Quick reference

**Example Use Case:**
- Single command execution
- Simple calculations
- Quick lookups

## Interactive Questions

### Question 1: Skill Name
```
スキル名を入力してください (kebab-case):
例: figma-implement, qa-agent, skill-generator

入力:
```

### Question 2: Skill Type
```
スキルタイプを選択してください:

1. orchestrator - 複数ステップのワークフロー (例: figma-implement)
2. validator - 検証・品質チェック (例: figma-cache-validator)
3. transformer - データ変換・抽出 (例: figma-design-tokens-extractor)
4. simple - シンプルな単一タスク

選択 (1-4):
```

### Question 3: Description
```
1行の説明を入力してください (Claudeの自動呼び出し判断用):

NG例: "このスキルは〇〇を行います。"（冗長）
OK例: "Figma to WordPress implementation (9-step workflow)."

入力:
```

### Question 4: Trigger Phrases
```
自動呼び出しのトリガーフレーズを入力してください (カンマ区切り):

例: implement this design, convert Figma to code, create page from Figma

入力:
```

### Question 5: Allowed Tools
```
使用可能なツールを選択してください (スペース区切りで複数選択):

基本ツール:
  Read Write Edit Glob Grep Bash Task AskUserQuestion

MCP (Figma):
  mcp__figma__get_design_context mcp__figma__get_metadata
  mcp__figma__get_screenshot mcp__figma__get_variable_defs

MCP (Playwright):
  mcp__playwright__browser_navigate mcp__playwright__browser_snapshot
  mcp__playwright__browser_take_screenshot

MCP (Serena):
  mcp__serena__find_symbol mcp__serena__search_for_pattern

選択:
```

### Question 6: Context
```
実行コンテキストを選択してください:

1. fork - サブエージェント実行 (メモリ分離、推奨)
2. main - メインコンテキスト実行 (軽量タスク向け)

選択 (1-2):
```

### Question 7: Agent Type
```
エージェントタイプを選択してください:

1. general-purpose - 汎用タスク
2. Explore - コードベース探索
3. Plan - 実装計画立案
4. Bash - コマンド実行専門

選択 (1-4):
```

### Question 8: Prerequisites
```
前提条件はありますか？ (Y/N):

例: 他のスキルを先に実行する必要がある
例: 特定のファイルが存在する必要がある

入力:
```

### Question 9: State Management
```
状態管理が必要ですか？ (Y/N):

- 中断・再開機能
- 進捗トラッキング
- YAML 状態ファイル

入力:
```

### Question 10: Scripts
```
検証・自動化スクリプトを生成しますか？ (Y/N):

生成される内容:
- scripts/validate-*.sh
- scripts/quality-check.sh
- Exit code handling

入力:
```

## Generated File Structure

```
.claude/skills/{skill-name}/
├── SKILL.md                    # Main skill definition
├── scripts/                    # Optional scripts
│   ├── validate-*.sh          # Validation scripts
│   └── quality-check.sh       # Quality check scripts
├── references/                 # Optional references
│   ├── workflow-steps.md      # Detailed step docs
│   ├── error-catalog.md       # Error handling catalog
│   └── state-management.md    # State persistence docs
└── examples/                   # Optional examples
    └── basic-usage.sh         # Usage examples
```

## YAML Frontmatter Template

```yaml
---
name: {skill-name}
description: "{1-sentence description with trigger phrases}"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  # ... (user selected tools)
context: fork  # or omit for main context
agent: general-purpose  # or Explore, Plan, Bash
---
```

## Best Practices Applied

### 1. Naming Conventions
- Skill name: kebab-case (e.g., `skill-generator`)
- Variables: snake_case (e.g., `skill_name`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`)

### 2. Description Guidelines
- Single sentence, concise
- Include trigger phrases
- Focus on "what" not "how"
- Active voice

### 3. Allowed Tools Selection
- Only include tools actually used
- Group by category (basic, MCP)
- Minimize for security

### 4. Processing Flow
- Use ASCII flow diagram
- Show decision points clearly
- Include error paths
- Mark human intervention points (H1, H2, etc.)

### 5. Error Handling
- Catalog format table
- Detection method
- Auto-recovery strategy
- Fallback action

### 6. Script Integration
- Exit code 0 = PASS
- Exit code 1 = FAIL
- Clear error messages
- Deterministic validation

### 7. Documentation Structure
```
# Skill Name

## Overview
## Prerequisites (if needed)
## Usage
## Input Parameters
## Processing Flow
## Step Details (for each step)
## Human Intervention Points (if any)
## State Management (if needed)
## Error Handling
## Related Files
## Examples
## Troubleshooting
```

## Validation Checklist

After generation, the following validation is performed:

- [ ] YAML frontmatter is valid
- [ ] `name` is kebab-case
- [ ] `description` is 1 sentence
- [ ] `allowed-tools` are valid tool names
- [ ] Required sections exist (Overview, Usage, Input Parameters)
- [ ] Processing flow diagram is present
- [ ] Error handling catalog exists
- [ ] Related files section is included
- [ ] Examples section is included
- [ ] Version/changelog is at the bottom

## Error Handling

| Error Type | Detection | Recovery | Fallback |
|------------|-----------|----------|----------|
| Skill name conflict | File existence check | Suggest alternative name | Prompt user for new name |
| Invalid YAML | YAML parser error | Syntax correction guide | Manual editing prompt |
| Missing required section | Section header check | Template insertion | Warn and continue |
| Invalid tool name | Tool catalog lookup | Suggest similar tools | Remove invalid tool |
| Script generation failed | Bash exit code | Retry with simpler template | Skip script generation |

## Integration Points

### After Successful Generation

1. **Skill Catalog Update**
   - Add to `.claude/skills/README.md`
   - Update skill index

2. **Workflow Integration**
   - Check related workflows in `docs/workflows/`
   - Add skill reference if applicable

3. **Testing Guide**
   - Suggest manual testing steps
   - Generate test command examples

## Examples

### Example 1: Simple Validator Skill

```bash
/skill-generator cache-validator --template validator --with-scripts

# Interactive prompts:
# Name: cache-validator
# Type: validator
# Description: "Validate Figma cache freshness (24h TTL)."
# Trigger: validate cache, check cache, verify Figma cache
# Tools: Read Bash Glob
# Context: fork
# Agent: general-purpose
# Prerequisites: Y (requires cache directory)
# State: N
# Scripts: Y
```

**Generated:**
```
.claude/skills/cache-validator/
├── SKILL.md
└── scripts/
    └── validate-cache.sh
```

### Example 2: Complex Orchestrator Skill

```bash
/skill-generator data-pipeline --template orchestrator --with-scripts

# Interactive prompts:
# Name: data-pipeline
# Type: orchestrator
# Description: "Multi-stage data processing pipeline (5 steps)."
# Trigger: run pipeline, process data, transform data
# Tools: Read Write Bash Task
# Context: fork
# Agent: general-purpose
# Prerequisites: Y (requires input files)
# State: Y (for resume capability)
# Scripts: Y
```

**Generated:**
```
.claude/skills/data-pipeline/
├── SKILL.md
├── scripts/
│   ├── validate-input.sh
│   ├── quality-check.sh
│   └── cleanup.sh
└── references/
    ├── workflow-steps.md
    ├── state-management.md
    └── error-catalog.md
```

### Example 3: Simple Transformer Skill

```bash
/skill-generator json-to-yaml --template transformer

# Interactive prompts:
# Name: json-to-yaml
# Type: transformer
# Description: "Convert JSON to YAML format with validation."
# Trigger: convert JSON, json to yaml
# Tools: Read Write Bash
# Context: fork
# Agent: general-purpose
# Prerequisites: N
# State: N
# Scripts: N
```

**Generated:**
```
.claude/skills/json-to-yaml/
└── SKILL.md
```

## Advanced Features

### Custom Template Sections

You can define custom sections during generation:

```
カスタムセクションを追加しますか？ (Y/N):

例:
- Memory Management
- Performance Optimization
- Security Considerations
```

### Metadata Generation

Automatically generates:
- Version number (default: 1.0.0)
- Created timestamp
- Updated timestamp
- Changelog placeholder

### Script Template Options

When `--with-scripts` is enabled:

```bash
# Validation script template
#!/bin/bash
set -euo pipefail

# Constants
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXIT_SUCCESS=0
EXIT_FAILURE=1

# Validation logic
validate() {
  # Your validation here
  return $EXIT_SUCCESS
}

main() {
  validate
}

main "$@"
```

## Troubleshooting

### Error: "Skill name already exists"

**Cause**: Skill with the same name already exists.

**Solution**:
1. List existing skills:
   ```bash
   ls .claude/skills/
   ```
2. Choose a different name
3. Or use `--force` to overwrite (dangerous)

### Error: "Invalid tool name"

**Cause**: Tool name not in allowed tools list.

**Solution**:
1. Check available tools:
   ```bash
   cat .claude/rules/skill.md | grep "allowed-tools"
   ```
2. Use exact tool name (case-sensitive)
3. For MCP tools, use format: `mcp__{server}__{tool}`

### Error: "YAML validation failed"

**Cause**: Generated YAML frontmatter is malformed.

**Solution**:
1. Check YAML syntax:
   ```bash
   head -20 .claude/skills/{skill-name}/SKILL.md
   ```
2. Ensure proper indentation (2 spaces)
3. Ensure list items have `- ` prefix
4. Re-run generator with `--dry-run` to preview

### Error: "Script generation failed"

**Cause**: Missing `scripts/` directory or permission issues.

**Solution**:
1. Create directory manually:
   ```bash
   mkdir -p .claude/skills/{skill-name}/scripts
   ```
2. Check permissions:
   ```bash
   ls -la .claude/skills/{skill-name}/
   ```
3. Ensure write permissions (755 for directories)

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/skill.md` | Skill creation rules and best practices |
| `.claude/skills/README.md` | Skill catalog and index |
| `.claude/skills/skill-yaml-validator/SKILL.md` | YAML validation skill |
| `docs/claude-guide/skills.md` | Skill usage documentation |

## Changelog

**Version**: 1.0.0
**Created**: 2026-02-02
**Updated**: 2026-02-02

**Changes**:
- v1.0.0: Initial release
  - Interactive skill generation
  - 4 template types (orchestrator, validator, transformer, simple)
  - Script generation support
  - YAML frontmatter validation
  - Best practices integration
