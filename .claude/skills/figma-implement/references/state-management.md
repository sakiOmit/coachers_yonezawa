# State Management

Detailed documentation for figma-implement state persistence and resume capability.

## State File Location

```
.claude/cache/figma-implement-state.yaml
```

## State Structure

### Standard Mode (PC only)

```yaml
pc_url: "https://figma.com/design/..."
pc_file_key: "abc123"
pc_node_id: "1:2"
pc_cache: ".claude/cache/figma/{page-name}/"

dual_mode: false

current_step: "Step2"
step_status:
  Step0:
    status: completed
    timestamp: "2026-01-30T12:00:00"
  Step1:
    status: completed
    timestamp: "2026-01-30T12:01:00"
  Step2:
    status: in_progress
    timestamp: "2026-01-30T12:02:00"
```

### PC/SP Dual Mode

```yaml
pc_url: "https://figma.com/design/..."
pc_file_key: "abc123"
pc_node_id: "1:2"
pc_cache: ".claude/cache/figma/{page-name}/pc/"

sp_url: "https://figma.com/design/..."
sp_file_key: "abc123"
sp_node_id: "3:4"
sp_cache: ".claude/cache/figma/{page-name}/sp/"

dual_mode: true

current_step: "Step2"
step_status:
  Step2:
    pc: completed
    sp: in_progress
```

## State Save Timing

State is automatically saved at:

1. **Step completion** - After each step finishes successfully
2. **Human intervention points** - Before waiting for user input
3. **Error occurrence** - When an error is caught
4. **Explicit interruption** - When user sends Ctrl+C

## State Restore

### Resume from Previous State

```bash
/figma-implement --resume
```

This reads the state file and continues from `current_step`.

### Resume from Specific Step

```bash
/figma-implement --resume --step Step4
```

This reads the state file but starts from the specified step.

### Resume Validation

Before resuming, the skill validates:

1. State file exists
2. Cache directory exists
3. Cache files are not corrupted
4. TTL has not expired (24h)

If validation fails, the skill prompts for a fresh start.

## State File Size Management

To prevent state file bloat:

| Rule | Description |
|------|-------------|
| Max size target | 50KB |
| Log compression | Keep summary only for completed steps |
| Archive on complete | Move to `.claude/archive/` after implementation |

### Log Compression

**Before (detailed log):**
```yaml
step_status:
  Step2:
    status: completed
    details: |
      - get_design_context 実行
      - レスポンスサイズ: 77,000 tokens
      - セクション数: 8
      - 各セクションの詳細ログ...（長文）
```

**After (summary only):**
```yaml
step_status:
  Step2:
    status: completed
    summary: "Design context retrieved (8 sections)"
```

### Archive Procedure

After implementation completes:

```bash
mkdir -p .claude/archive/
mv .claude/cache/figma-implement-state.yaml \
   .claude/archive/figma-implement-state-{page-name}-{timestamp}.yaml
```

## Step Status Values

| Status | Description |
|--------|-------------|
| `pending` | Not yet started |
| `in_progress` | Currently executing |
| `completed` | Successfully finished |
| `failed` | Failed with error |
| `skipped` | Intentionally skipped |
| `blocked` | Waiting for human intervention |

## Recovery from Failure

When a step fails:

1. State is saved with `failed` status
2. Error details are recorded
3. User is prompted with options:
   - Retry the step
   - Skip to next step
   - Abort and save state

### Retry Logic

```yaml
step_status:
  Step4:
    status: failed
    error: "Asset download failed: HTTP 503"
    retries: 2
    max_retries: 3
```

After 3 retries, the step is marked as `blocked` for human intervention.
