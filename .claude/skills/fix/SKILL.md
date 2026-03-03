---
name: fix
description: "Fix code issues (SCSS, PHP, JS) from review"
argument-hint: "[auto|scss|php|js|{issue-id}|critical|security]"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Edit
  - Glob
  - Grep
  - Bash
model: opus
context: fork
agent: general-purpose
---

# Unified Code Fix Command

## Dynamic Context

```
Recent review files:
!`ls -t .claude/reviews/*.json 2>/dev/null | head -3 || echo "No review found"`
```

Fix code issues identified by `/review` or `/qa`.

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | `/review`, `/qa` |
| **後工程** | `/qa verify`（検証） |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | code-fixer エージェント |

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

### Safe（自動修正可）の具体パターン

| # | パターン | 修正内容 |
|---|---------|---------|
| 1 | `&-` ネスト → `&__` | BEM 要素の記法修正 |
| 2 | `the_field()` → `get_field()` + エスケープ | ACF 出力関数の置換 |
| 3 | console.log 削除 | デバッグコード除去 |
| 4 | debugger 削除 | デバッグコード除去 |
| 5 | var_dump / print_r 削除 | デバッグコード除去 |
| 6 | 未使用 @use 削除 | 不要 import 除去 |
| 7 | `&:hover` → `@include hover` | タッチデバイス対応 |
| 8 | px 値 → rv()/svw() | マジックナンバー解消 |

### Risky（承認必要）の具体パターン

| # | パターン | リスク |
|---|---------|--------|
| 1 | エスケープ関数の追加 | 出力フォーマットが変わる可能性 |
| 2 | HTML 構造の変更 | レイアウト崩れの可能性 |
| 3 | ACF ロジックの変更 | データ取得パターンが変わる |
| 4 | CSS クラス名の変更 | JS との連携が壊れる可能性 |
| 5 | テンプレート分割 | include パスの整合性 |

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

Based on `$ARGUMENTS`, execute the fix workflow:

### Step 0: Run Auto-Fix Script (Safe Issues)

`auto`, `scss`, `js`, `php` の場合はまずスクリプトで機械的修正を実行:

```bash
# auto or 全タイプ
bash .claude/skills/fix/scripts/auto-fix.sh all

# 特定タイプ
bash .claude/skills/fix/scripts/auto-fix.sh scss
bash .claude/skills/fix/scripts/auto-fix.sh js
bash .claude/skills/fix/scripts/auto-fix.sh php
```

スクリプトは以下を自動実行:
- stylelint --fix / eslint --fix
- console.log, debugger, var_dump, print_r の削除
- &- → &__ の BEM 修正
- 修正後のビルド検証

**出力**: `reports/fix-{TYPE}-{TIMESTAMP}.json`

### Step 1: Parse Script Results

```
1. Read reports/fix-*.json の最新ファイル
2. fixed / skipped の件数を確認
3. skipped-risky 項目があれば Step 2 へ
4. 全て fixed なら Step 3 へ
```

### Step 2: LLM Handles Risky/Complex Issues

`{issue-id}`, `critical`, `security` の場合、または Step 1 で skipped-risky がある場合:

```
Task tool: subagent_type=code-fixer
prompt: |
  引数: {$ARGUMENTS}

  【自動修正結果】
  reports/fix-{TYPE}-{TIMESTAMP}.json を参照してください。
  機械的修正はスクリプトで完了済みです。

  残りの Risky/Complex issues のみを修正してください:
  - security: XSS, CSRF 等（承認必要）
  - the_field→get_field: ACFロジック変更（承認必要）
  - &:hover→@include hover: 複数行の変換（承認必要）

  修正後は必ず lint + build を実行して検証してください。
```

### Step 3: Auto-Verify and Report Results

**Verification (Auto-executed):**

```bash
# For SCSS fixes
npm run lint:fix -- src/scss/ --report-unused-disable-directives

# For PHP fixes
php -l themes/{{THEME_NAME}}/

# For JS fixes
npm run lint:fix -- src/js/
```

**Success Condition:** Zero lint errors on all modified files.

**If verification fails:**
- Identify parse/lint errors
- Revert problematic changes
- Display error context to user

**Report:**
- Show files modified (script + LLM)
- Show verification status (pass/fail with details)
- List remaining risky issues
- Suggest next steps

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | exit code |
|-----------|------|-----------|
| `scripts/auto-fix.sh [scss\|js\|php\|all] [--dry-run]` | Safe issues の機械的修正 | 0=PASS(Build OK), 1=BUILD_FAIL |

**出力**: `reports/fix-{TYPE}-{TIMESTAMP}.json`

## Error Handling

| Error | Recovery |
|-------|----------|
| レビューファイルが存在しない | `/review` を先に実行するよう案内し、`.claude/reviews/` 配下にファイルがあるか確認を促す |
| code-fixer エージェント不在 | `.claude/agents/` を確認し、エージェント定義がなければ Claude が直接 Edit ツールで修正を実行する |
| 修正後のビルドが失敗 | 修正した変更を元に戻し（変更前のコードを再適用）、エラー内容を提示して手動修正を案内する |

### Fallback

code-fixer エージェントが利用できない場合、または Task tool が失敗した場合は、Claude 自身が直接以下を実行する:
1. 最新の `.claude/reviews/` レポートを Read で読み込み、対象 issue を特定
2. Glob/Grep で対象ファイルを検索
3. Edit ツールで Safe issues を直接修正
4. Risky issues は変更内容をユーザーに提示し、承認を得てから適用
5. Bash で lint・build を実行して検証し、結果を報告する
