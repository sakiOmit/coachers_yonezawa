---
name: fix
description: "Fix code issues (SCSS, PHP, JS) from review"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Edit
  - Glob
  - Grep
  - Bash
context: fork
agent: general-purpose
---

# Unified Code Fix Command

Fix code issues identified by `/review` or `/qa`.

## Usage

```bash
# Fix all auto-fixable (safe) issues
/fix auto

# Fix all issues for specific type
/fix scss         # SCSS only
/fix js           # JavaScript only
/fix php          # PHP/WordPress only

# Fix specific issue by ID
/fix name-001     # Fix naming violation
/fix sec-001      # Fix security issue (will ask approval)

# Fix all critical issues
/fix critical

# Fix all security issues (with approval)
/fix security
```

## What This Does

### `/fix auto`

Fixes all **safe** issues from the active review:
- SCSS: naming violations, empty blocks, unused classes
- JS: console.log, debugger, unused imports
- PHP: var_dump, unused functions, TODO comments

### `/fix {type}`

| Command | Focus |
|---------|-------|
| `/fix scss` | All SCSS issues from review |
| `/fix js` | All JavaScript issues from review |
| `/fix php` | All PHP/WordPress issues from review |

### `/fix {issue-id}`

Fix a specific issue by its ID (e.g., `name-001`, `sec-001`, `quality-003`).

**Risky issues will ask for approval before applying.**

### `/fix critical`

Fix all Critical priority issues. Risky issues still require approval.

### `/fix security`

Fix all security issues. **All security fixes require approval.**

## Safe vs Risky

| Classification | Behavior |
|----------------|----------|
| **Safe** | Executed immediately |
| **Risky** | Shows proposed change, waits for approval |

### Safe Issues (Auto-fixable)

- SCSS: naming (camelCase → kebab-case), empty blocks, &__ nesting
- JS: console.log, debugger, unused imports
- PHP: var_dump, unused functions, TODO removal

### Risky Issues (Require Approval)

- Security fixes (XSS, SQL injection, CSRF)
- Base style extraction
- Error handling additions
- Performance optimizations
- Refactoring changes

## Output

```markdown
## Fix Results

**Fixed:** 15 safe issues
**Files Modified:**
- SCSS: 5 files
- JS: 3 files
- PHP: 2 files

**Verification:**
- Lint (SCSS): Passed
- Lint (JS): Passed
- Build: Passed

**Remaining Risky:** 3 issues
- sec-001: XSS vulnerability
- ...

**Next Steps:**
- `/fix sec-001` to fix security issue
- `/qa verify` to re-check
```

## Prerequisite

A review must be completed first:
- `/review all` - Run code review
- `/qa check` - Run QA check

If no active review exists, you'll be prompted to run one.

---

**Instructions for Claude:**

Based on `$ARGUMENTS`, launch the code-fixer agent:

1. **Parse Arguments**
   - `auto` → Fix all safe issues
   - `scss` / `js` / `php` → Fix specific type
   - `{issue-id}` → Fix specific issue
   - `critical` → Fix critical priority issues
   - `security` → Fix security issues (with approval)

2. **Launch Agent**
   ```
   Task tool: subagent_type=code-fixer
   prompt: |
     引数: {$ARGUMENTS}

     対応するモードで修正を実行してください。
     - auto: 全ての Safe issues を修正
     - scss/js/php: 該当タイプのみ修正
     - issue-id: 指定 issue を修正
     - critical: Critical priority のみ
     - security: Security issues（承認必要）

     修正後は必ず検証（lint, build）を実行し、
     レビューファイルの completion_summary を更新してください。
   ```

3. **Report Results**
   - Show files modified
   - Show verification status
   - List remaining risky issues
   - Suggest next steps
