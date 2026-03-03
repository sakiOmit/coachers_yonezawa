---
name: figma-implement-orchestrator
description: "Figma to WordPress implementation workflow orchestrator with state persistence, resume capability, and error recovery for large-scale page implementation."
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - mcp__figma__get_design_context
  - mcp__figma__get_metadata
  - mcp__figma__get_screenshot
  - mcp__figma__get_variable_defs
  - mcp__figma__get_code_connect_map
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_snapshot
  - mcp__playwright__browser_take_screenshot
context: fork
agent: general-purpose
---

# Figma Implement Orchestrator

## Overview

Orchestration skill that manages the Figma to WordPress implementation workflow (9 steps + Phase 0).
Provides state persistence, resume capability, and error recovery to maximize efficiency in large-scale page implementation.

### Key Features

- **Unified Management**: Automatic execution and progress tracking across 10 phases
- **State Persistence**: Save state to YAML on interruption
- **Resume Capability**: Continue from previous state with `--resume` option
- **Error Recovery**: Auto-retry and pause at human intervention points
- **Progress Reports**: Real-time progress display and completion report generation

## Usage

```
/figma-implement-orchestrator {figma_url}
```

### With Options

```
/figma-implement-orchestrator {figma_url} [options]

Options:
  --resume              Resume from previous interrupted state
  --step {step_name}    Start from specified step (debug use)
  --dry-run             Show plan without execution
  --interactive         Request confirmation at each step
  --skip-approval       Skip human intervention points (advanced)
  --preset {name}       Validation preset (strict|default|lenient)
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| figma_url | Yes | Figma page URL |
| --resume | No | Resume from previous state |
| --step | No | Start step (Phase0, Step1-9) |
| --dry-run | No | Show plan only, no execution |
| --interactive | No | Request confirmation at each step |
| --skip-approval | No | Skip human intervention (dangerous) |
| --preset | No | Validation threshold preset (default: default) |

## Processing Flow

```
ORCHESTRATOR START
        │
        ▼
┌───────────────────────────────────────┐
│  State Check: --resume option         │
│  └─ State file exists → Restore       │
│  └─ New execution → Initialize        │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Phase 0: Preparation                 │
│  ├─ 0-1. Cache check (24h TTL)        │
│  └─ 0-2. Existing component check     │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 1: Node ID Extraction           │
│  ├─ 1-1. URL parsing (regex)          │
│  └─ 1-2. Branch URL handling          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 2: Design Context Retrieval     │
│  ├─ 2-1. get_design_context           │
│  ├─ 2-2. Code Connect check           │
│  ├─ 2-3. Token limit check            │
│  │       └─ Limit → [H1: Section URL] │
│  └─ 2-5. Design system rules (first)  │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 3: Visual Reference             │
│  └─ 3-1. get_screenshot               │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 4: Assets + Design Tokens       │
│  ├─ 4-1. Asset download (2x size)     │
│  ├─ 4-2. Figma Variables fetch        │
│  ├─ 4-3. Naming convention mapping    │
│  ├─ 4-4. Existing variable diff       │
│  ├─ 4-5. [H2: Diff confirm] → SCSS    │
│  └─ 4-6. Node info supplement         │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 5: Project Convention Translate │
│  ├─ 5-1. [H3: Page info input]        │
│  ├─ 5-2. Auto component matching      │
│  ├─ 5-3. Figma Node spec structure    │
│  └─ 5-4. FLOCSS + BEM naming          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 6: Pixel-Perfect Implementation │
│  ├─ 6-1. wordpress-engineer agent     │
│  ├─ 6-2. Task definition              │
│  └─ 6-3. Build (npm run dev)          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 7: Figma Validation             │
│  ├─ 7-1. Playwright page display      │
│  ├─ 7-2. Section extraction → [H4]    │
│  ├─ 7-3. Section screenshots          │
│  ├─ 7-4. visual-diff.js execution     │
│  ├─ 7-5. Diff fix iteration (max 5)   │
│  │       └─ >5 times → [H5: Judgment] │
│  ├─ 7-6. Responsive validation        │
│  ├─ 7-7. Diff validation report       │
│  └─ 7-8. Full page screenshot         │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 8: Final Review                 │
│  └─ 8-1. production-reviewer          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 9: Token Efficiency Report      │
│  ├─ 9-1. Report output                │
│  └─ 9-2. Efficiency retrospective     │
└───────────────────────────────────────┘
        │
        ▼
       COMPLETE
```

## Human Intervention Points (H1-H5)

The orchestrator automatically pauses at the following points and waits for human input.

| ID | Step | Trigger Condition | Required Input | Timeout |
|----|------|-------------------|----------------|---------|
| H1 | 2-4 | Token limit detected | Section Figma URLs | None (required) |
| H2 | 4-5 | Variable diff exists | Approval (Y/N/select) | 5min (default Y) |
| H3 | 5-1 | Always | Slug, JP name, EN name | None (required) |
| H4 | 7-2 | Section detected | Section name confirm/edit | 3min (default approve) |
| H5 | 7-5 | >5 iterations | Continue/Stop/Manual fix | None (required) |

## Error Handling

| Error Type | Detection | Auto Recovery | Fallback |
|------------|-----------|---------------|----------|
| Token limit | Response warning | Section split proposal | H1: URL request |
| MCP connection | Exception catch | 3 retries (exponential) | Auth check prompt |
| Figma auth | HTTP 401/403 | - | Token recheck |
| Asset DL fail | HTTP 4xx/5xx | 3 retries | Manual DL request |
| Build error | npm exit code | Error analysis → auto-fix | Error log display |
| Diff validation fail | passed: false | Max 5 iterations | H5: Diff judgment |
| Figma Variables empty | Empty object | Extract from Node info | Warning + continue |
| Playwright fail | MCP exception | 3 retries | Manual validation request |

## State Management

### State File Location

```
.claude/cache/figma-implement-state.yaml
```

### State Save Timing

- Each step completion
- Human intervention point reached
- Error occurrence
- Explicit interruption (Ctrl+C)

### State Restore

```bash
# Resume from previous state
/figma-implement-orchestrator --resume

# Start from specific step (with state file)
/figma-implement-orchestrator --resume --step Step4
```

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma-implement-state.yaml` | State persistence file |
| `.claude/cache/figma-implement-report-*.yaml` | Completion reports |
| `.claude/cache/figma/` | Figma cache directory |
| `.claude/cache/visual-diff/` | Diff validation images |
| `.claude/skills/figma-implement/SKILL.md` | Original workflow definition |
| `.claude/rules/figma-workflow.md` | Figma workflow rules |
| `.claude/data/component-catalog.yaml` | Component catalog |

## Examples

### Basic Usage (New Implementation)

```bash
/figma-implement-orchestrator https://www.figma.com/design/abc123/MyDesign?node-id=1-2
```

### Resume from Interruption

```bash
# Check previous state
cat .claude/cache/figma-implement-state.yaml

# Resume
/figma-implement-orchestrator --resume
```

### Dry Run (Plan Confirmation)

```bash
/figma-implement-orchestrator https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --dry-run
```

### Interactive Mode

```bash
/figma-implement-orchestrator https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --interactive
```

### Strict Validation Mode

```bash
/figma-implement-orchestrator https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --preset strict
```

---

**Version**: 1.0.0
**Created**: 2026-01-30
