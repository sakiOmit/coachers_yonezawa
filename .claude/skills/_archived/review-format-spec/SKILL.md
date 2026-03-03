---
name: review-format-spec
description: "Review Result Format Specification"
disable-model-invocation: true
allowed-tools:
  - Read
context: fork
agent: general-purpose
---

# Review Result Format Specification

レビューエージェントが出力すべき標準フォーマット仕様です。

## ファイル命名規則

```
.claude/reviews/{type}-{timestamp}.md

例:
.claude/reviews/php-20250124-143022.md
.claude/reviews/js-20250124-143530.md
.claude/reviews/scss-20250124-144015.md
```

## ファイル構造

### Front Matter (YAML)

```yaml
---
type: php|js|scss
scope: security|html|seo|accessibility|maintainability|testability|scalability|error-handling|documentation|consistency|architecture|dry|complexity|tech-debt|production|code-quality|all
status: pending  # pending|in_progress|completed|archived
timestamp: 2025-01-24T14:30:22+09:00
completed_at: null
reviewer: php-wordpress-reviewer|js-code-reviewer|scss-reviewer
files_reviewed: 42
total_issues: 15
completion_summary:
  fixed_issues: 0
  remaining_issues: 0
  fixed_issue_ids: []
issues_by_priority:
  critical: 2
  high: 5
  medium: 6
  low: 2
issues_by_classification:
  safe: 8
  risky: 7
issues_by_category:
  # Production Readiness Categories
  security: 3
  accessibility: 4
  seo: 2
  html: 3
  performance: 1
  code_quality: 2
  # Tech Lead / Code Quality Categories (🆕 NEW)
  maintainability: 5
  testability: 3
  scalability: 2
  error_handling: 4
  documentation: 6
  consistency: 3
  architecture: 2
  dry_violation: 4
  complexity: 3
---
```

### Body (Markdown)

```markdown
# {Type} Code Review

**Review Date:** 2025-01-24 14:30:22
**Scope:** {scope}
**Files Reviewed:** {count}

## Summary

**Total Issues:** {count}
- 🔴 Critical: {count}
- ⚠️ High: {count}
- 💡 Medium: {count}
- ℹ️ Low: {count}

**Auto-fixable (Safe):** {count}
**Manual Review (Risky):** {count}

---

## Issues

### Critical Issues 🔴

#### [{classification}] {icon} {title}

**Issue ID:** `{category}-{number}`
**File:** `{file_path}:{line_number}`
**Category:** {category}
**Priority:** Critical
**Classification:** Safe|Risky
**Impact:** {description}

**Current Code:**
```{lang}
{code_before}
```

**Suggested Fix:**
```{lang}
{code_after}
```

**Fix Command:**
```
/{type}-fix {issue_id}
```

**Why Risky:** (if Risky)
{explanation}

---

(繰り返し)

---

## Checklists

### Security Checklist 🔒
- [ ] All user output escaped
- [ ] All user input sanitized
- ...

### Accessibility Checklist ♿
- [ ] Alt attributes present
- [ ] Form labels associated
- ...

---

## Next Steps

1. **Fix Critical Issues:**
   ```
   /{type}-fix critical
   ```

2. **Auto-fix Safe Issues:**
   ```
   /{type}-fix auto
   ```

3. **Review Specific Issues:**
   ```
   /{type}-fix {issue_id}
   ```

4. **Re-review:**
   ```
   /{type}-review
   ```
```

## Issue ID 命名規則

### カテゴリプレフィックス

#### Production Readiness Categories

| カテゴリ | プレフィックス | 例 | 説明 |
|---------|--------------|-----|------|
| Security | `sec-` | sec-001 | セキュリティ脆弱性（XSS, SQL injection等） |
| Accessibility | `a11y-` | a11y-001 | アクセシビリティ違反（WCAG 2.1 AA） |
| SEO | `seo-` | seo-001 | SEO問題（meta tags, OGP等） |
| HTML Structure | `html-` | html-001 | HTML構造問題（semantic HTML等） |
| Performance | `perf-` | perf-001 | パフォーマンス問題（N+1 query等） |
| Code Quality | `quality-` | quality-001 | 一般的なコード品質問題 |
| WordPress | `wp-` | wp-001 | WordPress特有の問題 |

#### Tech Lead / Code Quality Categories

| カテゴリ | プレフィックス | 例 | 説明 |
|---------|--------------|-----|------|
| Maintainability | `maint-` | maint-001 | 保守性（ドキュメント、命名、マジックナンバー） |
| Testability | `test-` | test-001 | テスタビリティ（純粋関数、DI、テスト可能性） |
| Scalability | `scale-` | scale-001 | スケーラビリティ（キャッシュ、クエリ最適化） |
| Error Handling | `error-` | error-001 | エラーハンドリング（null check、fallback） |
| Documentation | `doc-` | doc-001 | ドキュメンテーション（DocBlock、コメント） |
| Consistency | `consist-` | consist-001 | 一貫性（命名規則、コーディング規約） |
| Architecture | `arch-` | arch-001 | アーキテクチャ（関心の分離、結合度） |
| DRY Violation | `dry-` | dry-001 | DRY違反（重複コード、重複ロジック） |
| Complexity | `complex-` | complex-001 | 複雑度（関数長、循環的複雑度、ネスト深度） |

#### Language-Specific Categories

| カテゴリ | プレフィックス | 例 | 説明 |
|---------|--------------|-----|------|
| JavaScript | `js-` | js-001 | JavaScript固有の問題 |
| SCSS/CSS | `css-` | css-001 | SCSS/CSS固有の問題（FLOCSS+BEM違反等） |
| CSS Duplication | `dup-` | dup-001 | SCSSベーススタイル重複 |
| CSS Naming | `name-` | name-001 | SCSS命名規則違反 |
| CSS Unused | `unused-` | unused-001 | 未使用CSSクラス |
| CSS Responsive | `resp-` | resp-001 | レスポンシブ関数使用問題 |
| Browser Compat | `compat-` | compat-001 | ブラウザ互換性問題 |

### 採番ルール

- カテゴリ内で連番（001, 002, 003...）
- 同一レビューセッション内でユニーク
- 3桁ゼロパディング

### 分類サフィックス (Optional)

```
{category}-{number}-{classification}

例:
sec-001-risky
a11y-002-safe
```

## Review Status Management

### Status Field

レビューファイルには `status` フィールドを使用して進行状態を管理します。

**利用可能なステータス:**

- **`pending`** - レビュー完了、修正待ち（デフォルト値）
- **`in_progress`** - 修正作業中（fixer agentが最初の修正を実行した時点で自動設定）
- **`completed`** - すべての修正完了（手動またはコマンドで設定）
- **`archived`** - アーカイブ済み（参照のみ）

**Fixer Agent の動作:**

1. **レビューファイル選択時:**
   - `status: pending` または `status: in_progress` のファイルのみを対象とする
   - `completed` または `archived` のファイルは無視
   - 複数の `pending`/`in_progress` がある場合、最新の `timestamp` を使用

2. **最初の修正実行時:**
   - `status` を `pending` → `in_progress` に自動更新
   - 以降の修正でも `in_progress` を維持

3. **Issue修正記録:**
   - 修正したIssue IDを `completion_summary.fixed_issue_ids` に追加
   - `completion_summary.fixed_issues` をインクリメント
   - `completion_summary.remaining_issues` をデクリメント

**Completion Summary:**

```yaml
completion_summary:
  fixed_issues: 3           # 修正完了したIssue数
  remaining_issues: 12      # 未修正Issue数
  fixed_issue_ids:          # 修正済みIssue IDリスト
    - sec-001
    - a11y-003
    - quality-005
```

**レビュー完了時:**

手動で `status: completed` に変更するか、completion commandを使用:
```bash
/php-review-complete
/js-review-complete
/scss-review-complete
```

これにより以下が自動設定されます:
- `status: completed`
- `completed_at: 2025-01-24T16:45:30+09:00`
- 最終的な `completion_summary` の確定

## Issue Classification

### Safe (自動修正可能)

**条件:**
- 機械的に修正可能
- 副作用のリスクが極めて低い
- ロジック変更を伴わない

**例:**
- console.log削除
- var_dump削除
- 未使用import削除
- フォーマット修正
- 簡単な命名修正（camelCase → kebab-case）

### Risky (要承認)

**条件:**
- ロジック変更を伴う
- 複数ファイルに影響
- 動作に影響する可能性
- セキュリティ修正（重要だが慎重に）

**例:**
- セキュリティ修正（エスケープ追加等）
- アクセシビリティ修正（alt追加、label追加等）
- ベーススタイル抽出
- リファクタリング
- パフォーマンス最適化

## Priority Levels

### Critical 🔴

**定義:** 本番環境で即座に問題を引き起こす

**例:**
- セキュリティ脆弱性（XSS, SQLインジェクション等）
- 法的要件違反（アクセシビリティLevel A）
- ビルドエラーを引き起こすコード

**対応:** 即座に修正必須

### High ⚠️

**定義:** 重大なビジネスインパクトまたは高リスク

**例:**
- パフォーマンス重大問題（N+1クエリ等）
- SEO重要問題（OGPタグ欠如等）
- アクセシビリティLevel AA違反
- メモリリーク

**対応:** デプロイ前推奨

### Medium 💡

**定義:** 改善推奨、中期的に対応

**例:**
- コード品質問題
- 保守性の低下
- 軽微なパフォーマンス問題
- ベストプラクティス違反

**対応:** 次のスプリントで計画的に

### Low ℹ️

**定義:** Nice to have、長期的改善

**例:**
- コメント不足
- 命名の一貫性
- 微細なリファクタリング機会

**対応:** バックログ

## Category Icons

レポート内で使用するアイコン:

### Production Readiness Categories
- 🔒 Security
- ♿ Accessibility
- 🔍 SEO
- 📄 HTML Structure
- ⚡ Performance
- 💻 Code Quality
- 🔧 WordPress

### Tech Lead / Code Quality Categories
- 📚 Maintainability
- 🧪 Testability
- 📈 Scalability
- 🛡️ Error Handling
- 📝 Documentation
- 🔄 Consistency
- 🏗️ Architecture
- ♻️ DRY Violations
- 📊 Complexity

### Language-Specific Categories
- 🎨 SCSS/CSS
- ⚙️ JavaScript

## Example: 完全な Issue 定義

```markdown
#### [RISKY] 🔒 XSS Vulnerability: Unescaped Output

**Issue ID:** `sec-001`
**File:** `themes/{{THEME_NAME}}/pages/page-vision.php:34`
**Category:** security
**Priority:** Critical
**Classification:** Risky
**Impact:** User data displayed without escaping. XSS attack possible if $title contains malicious JavaScript.

**Current Code:**
```php
<h2><?php echo $title; ?></h2>
```

**Suggested Fix:**
```php
<h2><?php echo esc_html($title); ?></h2>
```

**Fix Command:**
```
/php-fix sec-001
```

**Why Risky:**
While this is a straightforward fix, security changes require careful review to ensure:
1. The correct escaping function is used (esc_html vs esc_url vs esc_attr)
2. The variable is not already escaped elsewhere
3. The change doesn't break intended HTML rendering

**Security Risk:** HIGH - Direct XSS vulnerability. Malicious users can inject JavaScript code.
```

## Example: YAML Front Matter

```yaml
---
type: php
scope: all
status: pending
timestamp: 2025-01-24T14:30:22+09:00
completed_at: null
reviewer: php-wordpress-reviewer
files_reviewed: 42
total_issues: 15
completion_summary:
  fixed_issues: 0
  remaining_issues: 15
  fixed_issue_ids: []
issues_by_priority:
  critical: 2
  high: 5
  medium: 6
  low: 2
issues_by_classification:
  safe: 8
  risky: 7
issues_by_category:
  security: 3
  accessibility: 4
  seo: 2
  html: 3
  performance: 1
  code_quality: 2
issues:
  - id: sec-001
    classification: risky
    priority: critical
    category: security
    file: themes/{{THEME_NAME}}/pages/page-vision.php
    line: 34
    title: "XSS Vulnerability: Unescaped Output"
  - id: sec-002
    classification: risky
    priority: critical
    category: security
    file: themes/{{THEME_NAME}}/inc/custom-queries.php
    line: 23
    title: "SQL Injection Risk: Unprepared Query"
  - id: quality-001
    classification: safe
    priority: low
    category: code_quality
    file: themes/{{THEME_NAME}}/functions.php
    line: 67
    title: "Debug Output Left in Production"
  # ... more issues
---
```

## Fixer Agent Requirements

Fixer エージェントは以下を実装する必要があります:

1. **レビューファイルの読み込み**
   - `.claude/reviews/` から `status: pending` または `status: in_progress` のファイルを検索
   - `completed` または `archived` のファイルは無視
   - 複数ある場合、最新の `timestamp` のファイルを使用
   - または、ユーザー指定のレビューファイルを読み込み

2. **Issue ID による検索**
   - Front Matter の `issues` リストから該当 Issue を特定
   - Body 内の該当セクションを抽出

3. **修正内容の理解**
   - Current Code と Suggested Fix を解析
   - Why Risky の内容を理解してユーザーに説明

4. **修正実行**
   - Safe: 即座に実行
   - Risky: 変更内容を表示 → ユーザー承認 → 実行

5. **修正記録とステータス更新**
   - **最初の修正時:** `status: pending` → `status: in_progress` に更新
   - **各修正後:** 修正したIssue IDを `completion_summary.fixed_issue_ids` に追加
   - `completion_summary.fixed_issues` をインクリメント
   - `completion_summary.remaining_issues` をデクリメント
   - レビューファイルのYAML Front Matterを更新

## Implementation Notes

### Reviewer Agent 側の実装

各レビューエージェントの `Report Generation` セクションに追加:

```markdown
### Report Generation (Updated)

**Step 1: Generate Front Matter**
- Calculate all summary statistics
- Create issues array with structured data
- **Initialize status tracking:**
  - `status: pending`
  - `completed_at: null`
  - `completion_summary.fixed_issues: 0`
  - `completion_summary.remaining_issues: {total_issues}`
  - `completion_summary.fixed_issue_ids: []`

**Step 2: Generate Body**
- Follow standard format spec
- Include all required fields for each issue
- Use correct Issue ID format ({category}-{number})

**Step 3: Save to File**
- Create `.claude/reviews/` directory if not exists
- Save as `{type}-{timestamp}.md`
- Inform user of file location

**Step 4: Display Summary**
- Show summary to user
- Provide next steps commands
```

### Fixer Agent 側の実装

各フィクサーエージェントの `Validate Input` セクションに追加:

```markdown
### Validate Input (Updated)

**Required Checks:**
- [ ] Do I have a review file path or Issue ID?
- [ ] If Issue ID provided, can I find the latest active review file?
- [ ] Can I parse the Front Matter?
- [ ] Can I locate the specific issue in the body?
- [ ] Is the review status `pending` or `in_progress`?

**Finding Active Review:**
1. Check for review files in `.claude/reviews/{type}-*.md`
2. **Filter by status:** Only consider `status: pending` or `status: in_progress`
3. **Ignore completed:** Skip files with `status: completed` or `status: archived`
4. **Select latest:** If multiple active reviews, use the one with latest `timestamp`
5. If no active review found, ask user to run `/{type}-review` first

**Status Update Logic:**
1. **On first fix execution:**
   - Read current review file YAML Front Matter
   - If `status: pending`, update to `status: in_progress`
   - Write updated YAML back to file

2. **After each fix:**
   - Add fixed Issue ID to `completion_summary.fixed_issue_ids`
   - Increment `completion_summary.fixed_issues`
   - Decrement `completion_summary.remaining_issues`
   - Write updated YAML back to file
```

## Validation Rules

レビューファイルは以下を満たす必要があります:

1. **Valid YAML Front Matter**
   - 必須フィールドが全て存在
   - issues 配列が正しい構造

2. **Consistent Issue IDs**
   - Front Matter と Body で一致
   - 重複なし

3. **Required Fields per Issue**
   - Issue ID
   - File path
   - Line number (if applicable)
   - Category
   - Priority
   - Classification
   - Current Code (if applicable)
   - Fix Command

4. **Valid Categories**
   - 定義されたカテゴリのみ使用

5. **Valid Priorities**
   - critical, high, medium, low のみ
