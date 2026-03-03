---
name: figma-implement
description: "Orchestrate Figma to WordPress implementation (9-step workflow). Use when user says 'implement this design', 'convert Figma to code', 'create page from Figma', or after /figma-prefetch. Supports --section option for precision implementation."
disable-model-invocation: true
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
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_snapshot
  - mcp__playwright__browser_take_screenshot
context: fork
agent: general-purpose
---

# Figma Implement Orchestrator

## Overview

Orchestration skill that manages the Figma to WordPress implementation workflow (9 steps).
Provides state persistence, resume capability, and error recovery to maximize efficiency in large-scale page implementation.

### Key Features

- **Unified Management**: Automatic execution and progress tracking across 9 steps
- **State Persistence**: Save state to YAML on interruption
- **Resume Capability**: Continue from previous state with `--resume` option
- **Error Recovery**: Auto-retry and pause at human intervention points
- **Progress Reports**: Real-time progress display and completion report generation
- **Context Optimization**: Screenshot省略モードでトークン消費を削減

## Prerequisites

Before using this skill, complete the following:

1. Run `/figma-analyze {pc_url} [additional_urls...]` (推奨)
   - ページ構造分析 + 複雑度スコア算出
   - 分割戦略判定 (NORMAL/SPLIT/SPLIT_REQUIRED)
   - 共通コンポーネント検出 + カタログマッチング
   - 実装順序の決定

分析レポートは `.claude/cache/figma/analysis-report.yaml` に出力される。

**Cache Verification:**
```bash
ls -la .claude/cache/figma/{page-name}/
```

**Required cache structure:**
```
.claude/cache/figma/{page-name}/
├── metadata.json          # get_metadata result
├── design-context.json    # get_design_context result
└── prefetch-info.yaml     # Prefetch metadata
```

2. **Container Width Calculation**
   - Manually apply the artboard margin-based formula (see below)
   - Refer to `.claude/rules/figma-workflow.md` for container width calculation rules

**Container Width Calculation Methods:**

Priority order (default: Method 1):

1. **Artboard Margin-Based (Default)**
   ```
   containerWidth = artboardWidth - (firstContentFrame.x * 2)
   ```
   - Recommended for most cases
   - Simple, consistent, low-risk

2. **Auto Layout max-width (Optional)**
   - Use when `node.layoutMode` && `node.maxWidth` exist
   - More accurate for Auto Layout designs
   - Requires fallback to Method 1

3. **Frame width attribute (Not Recommended)**
   - Avoid direct usage
   - Risk of inaccuracy with Auto Layout constraints

**See Also:**
- `/figma-container-width-calculator` - Automated calculation skill
- `.claude/rules/figma-workflow.md` - Detailed calculation rules

## Usage

```
/figma-implement {pc_url} [--sp {sp_url}]
```

### With Options

```
/figma-implement {pc_url} [options]

Options:
  --sp {sp_url}         SP version Figma URL (optional, for PC/SP dual implementation)
  --no-screenshot       Skip get_screenshot (recommended for token saving)
  --resume              Resume from previous interrupted state
  --step {step_name}    Start from specified step (debug use)
  --section {name}      Implement specific section only (recommended for precision)
  --dry-run             Show plan without execution
  --interactive         Request confirmation at each step
  --skip-approval       Skip human intervention points (advanced)
  --preset {name}       Validation preset (strict|default|lenient)
```

### PC/SP Dual Implementation

When `--sp` option is provided, both PC and SP designs are retrieved and compared:

```bash
# PC only (backward compatible)
/figma-implement https://figma.com/design/abc123/MyDesign?node-id=1-2

# PC + SP dual implementation
/figma-implement https://figma.com/design/abc123/MyDesign?node-id=1-2 \
  --sp https://figma.com/design/abc123/MyDesign?node-id=3-4
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| pc_url | Yes | Figma page URL for PC design |
| --sp | No | Figma page URL for SP design (enables PC/SP dual implementation) |
| --no-screenshot | No | Skip Step 3 get_screenshot (recommended for token saving) |
| --resume | No | Resume from previous state |
| --step | No | Start step (Step1-9) |
| --section | No | **Implement specific section only (recommended)** |
| --dry-run | No | Show plan only, no execution |
| --interactive | No | Request confirmation at each step |
| --skip-approval | No | Skip human intervention (dangerous) |
| --preset | No | Validation threshold preset (default: default) |

## Section-Based Implementation (Recommended)

**⚠️ 一括実装は精度が落ちる。セクション単位での実装を推奨。**

### Why Section-Based?

一度に全セクションを実装すると:
- raw_jsx を正しく解釈しない
- レイアウト構造を無視する
- 勝手な推測で実装する

### Usage

```bash
# 推奨: セクション単位で実装（各セクション完了後に確認）
/figma-implement --page interview --section hero
/figma-implement --page interview --section content
/figma-implement --page interview --section more-interview
/figma-implement --page interview --section footer

# 非推奨: 一括実装（精度低下リスク）
/figma-implement --page interview
```

### Section Names

セクション名は `prefetch-info.yaml` の `sections_sorted_by_y` から取得:

```yaml
sections_sorted_by_y:
  pc:
    - nodeId: "1:675"
      name: "Header"        # --section header
    - nodeId: "69:2515"
      name: "Hero"          # --section hero
    - nodeId: "1:701"
      name: "Content"       # --section content
```

### Workflow

```
1. /figma-prefetch → 確認
2. /figma-recursive-splitter → 確認
3. /figma-implement --section header → 確認
4. /figma-implement --section hero → 確認
5. /figma-implement --section content → 確認
6. ... (各セクションごとに確認)
7. 統合テスト
```

## Processing Flow

```
ORCHESTRATOR START
        │
        ▼
┌───────────────────────────────────────┐
│  ★ Step 0: Cache Validation (REQUIRED)│
│  │                                    │
│  │  Task ツールで強制実行:            │
│  │  subagent: figma-cache-validator   │
│  │  run_in_background: false          │
│  │                                    │
│  ├─ CACHE_VALID → Step 1 へ進む       │
│  ├─ CACHE_EXPIRED → 停止、再取得指示  │
│  └─ CACHE_NOT_FOUND → 停止、取得指示  │
│                                       │
│  ⚠️ このステップはスキップ不可        │
└───────────────────────────────────────┘
        │
        ▼ (CACHE_VALID の場合のみ)
┌───────────────────────────────────────┐
│  ★ Step 0.5: raw_jsx Validation       │
│  │                                    │
│  │  キャッシュ nodes/*.json を検証:   │
│  │  ├─ 文字列長 >= 500文字            │
│  │  ├─ "export default function" 含む │
│  │  ├─ "return (" 含む                │
│  │  ├─ "className=" 含む              │
│  │  └─ 省略コメントを含まない         │
│  │                                    │
│  ├─ VALID → キャッシュ使用           │
│  └─ INVALID → get_design_context 再取得│
│                                       │
│  ⚠️ セクション単位実装時は必須        │
└───────────────────────────────────────┘
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
│  Step 1: Node ID Extraction           │
│  ├─ 1-1. URL parsing (regex)          │
│  └─ 1-2. Branch URL handling          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 2: Design Context Retrieval     │
│  ├─ 2-1. get_design_context (PC)      │
│  ├─ 2-1b. get_design_context (SP)     │
│  │        └─ If --sp provided         │
│  ├─ 2-2. Component catalog check      │
│  ├─ 2-2b. Container width calculation │
│  │        └─ figma-container-width-   │
│  │           calculator OR manual     │
│  ├─ 2-3. Token limit check            │
│  │       └─ Limit → [H1: Section URL] │
│  └─ 2-5. Design system rules (first)  │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 3: Visual Reference (Optional)  │
│  ├─ Skip if --no-screenshot           │
│  ├─ 3-1. get_screenshot (PC)          │
│  └─ 3-1b. get_screenshot (SP)         │
│          └─ If --sp provided          │
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
│  ├─ 5-1a. Auto-extract page title     │
│  │        ├─ Pattern 1: Large text    │
│  │        │   (fontSize ≥24px, top)   │
│  │        ├─ Pattern 2: Header text   │
│  │        │   (layer: header/title)   │
│  │        └─ Pattern 3: Breadcrumb    │
│  │            (last item in BC)       │
│  │  Logic:                            │
│  │    - JA: First heading w/ JP chars │
│  │    - EN: Pattern match keywords    │
│  │    - Slug: EN → kebab-case         │
│  ├─ 5-1b. [H3: Manual input]          │
│  │        └─ Only if auto-extract fail│
│  ├─ 5-2. Auto component matching      │
│  ├─ 5-3. Figma Node spec structure    │
│  │       └─ PC/SP diff table (if --sp)│
│  └─ 5-4. FLOCSS + BEM naming          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 6: Pixel-Perfect Implementation │
│  ├─ 6-1. wordpress-engineer (Task)    │
│  │       └─ PC/SP specs (if --sp)     │
│  ├─ 6-2. PHP/SCSS implementation      │
│  ├─ 6-3. Build (npm run dev)          │
│  └─ 6-4. SCSS Rule Compliance Check   │
│          ├─ npm run lint:css          │
│          ├─ Container rule auto-fix   │
│          └─ Loop until 0 violations   │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 7: Figma Validation             │
│  ├─ 7-1. Playwright page display      │
│  ├─ 7-2. Section extraction → [H4]    │
│  ├─ 7-3. Section screenshots (PC)     │
│  ├─ 7-4. visual-diff.js (PC)          │
│  ├─ 7-5. Diff fix iteration (max 5)   │
│  │       └─ >5 times → [H5: Judgment] │
│  ├─ 7-6. SP validation (direct Figma) │
│  │       └─ Compare with SP Figma URL │
│  │           (if --sp provided)       │
│  ├─ 7-7. Diff validation report       │
│  └─ 7-8. Full page screenshot         │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Step 8: Quick Quality Check (AUTO)   │
│  ├─ 8-1. npm run build → BLOCK on err │
│  ├─ 8-2. npm run lint:css → WARN only │
│  └─ 8-3. PHP pattern check (grep)     │
│          ├─ <img> → BLOCK             │
│          └─ the_field() → BLOCK       │
│  ⚠️ Error detected → Fix → Re-run     │
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

## Step 0: Cache Validation (Mandatory - SCRIPT REQUIRED)

**このステップはスキップ不可。検証スクリプトを実行して結果を確認する。**

### Implementation

**MUST** run validation script first:

```bash
bash .claude/skills/figma-implement/scripts/validate-cache.sh \
  .claude/cache/figma/{page-slug}
```

Exit code handling:
- Exit 0 (PASS) → Step 1 へ進む
- Exit 1 (FAIL) → 停止、/figma-prefetch 実行を指示

### Why Script Validation?

| Approach | Reliability |
|----------|-------------|
| Subagent task (LLM-based) | ❌ May skip checks |
| Script validation (exit code) | ✅ Deterministic |

コードは決定論的、言語解釈はそうではない。

### Why Mandatory?

| 問題 | 解決策 |
|------|--------|
| キャッシュ確認忘れ | サブエージェントが強制確認 |
| API無駄呼び出し | キャッシュ有効時は再利用 |
| トークン浪費 | 24時間以内のデータを活用 |

### Error Handling

| 状況 | 対応 |
|------|------|
| サブエージェント起動失敗 | 3回リトライ後、手動確認を指示 |
| キャッシュパス不明 | URL から page-slug を抽出して検索 |

## Step 0.5: raw_jsx Validation (Mandatory for Cached Data)

**キャッシュから読み込む際、raw_jsx の品質を必ず検証する。**

### Why This Step Exists

`figma-recursive-splitter` がキャッシュを作成する際に、raw_jsx が省略・抽象化される問題が発生した。
この検証により、不完全なキャッシュを使用することを防止する。

### Validation Criteria

キャッシュファイル `nodes/{nodeId}.json` の `raw_jsx` フィールドが以下を満たすか検証:

| # | 条件 | 理由 |
|---|------|------|
| 1 | 文字列長 >= 500文字 | 省略されていないか |
| 2 | `export default function` を含む | JSXコードか |
| 3 | `return (` を含む | JSX return文があるか |
| 4 | `className=` を含む | Tailwindクラスがあるか |
| 5 | `data-node-id=` を含む | Figmaノード対応があるか |
| 6 | 省略コメントを含まない | 抽象化されていないか |

### 省略コメントパターン（検出対象）

```
- "// Large JSX content"
- "// Section heading"
- "// Cards"
- "// Contains"
- "// Key styles:"
```

### Implementation Flow (SCRIPT REQUIRED)

**MUST** run validation script for each cached node:

```bash
# For each node in the cache
for node_file in .claude/cache/figma/{page-slug}/nodes/*.json; do
  node_id=$(basename "$node_file" .json)
  bash .claude/skills/figma-implement/scripts/validate-raw-jsx.sh \
    "$node_file" "$node_id"
done
```

Exit code handling:
- Exit 0 (PASS) → キャッシュを使用
- Exit 1 (FAIL) → get_design_context を直接呼び出し

Or manually:
```
1. キャッシュファイルを Read で読み込む
   nodes/{nodeId}.json

2. raw_jsx フィールドを抽出

3. 6つの検証条件をチェック

4. 検証結果に基づく分岐:
   ├─ ALL PASS → キャッシュを使用
   └─ ANY FAIL → 以下を実行:
       ├─ WARNING 出力
       ├─ get_design_context を直接呼び出し
       └─ 新しいデータで実装（キャッシュは使用しない）
```

### Example: Validation Failure

```
⚠️ raw_jsx validation FAILED for 5:2687 (MVV Section):
   - Too short: 423 chars (min: 500)
   - Missing 'export default function'
   - Contains abstraction comment: '// Key styles:'

→ キャッシュは使用せず、get_design_context を直接呼び出します。
```

### Example: Validation Success

```
✅ raw_jsx validated: 5:2687 (12,847 chars)
   - export default function: ✓
   - return statement: ✓
   - className attributes: ✓
   - data-node-id attributes: ✓
   - No abstraction comments: ✓

→ キャッシュからの読み込みを使用します。
```

## Memory Leak Mitigation (Lightweight Main Context)

このスキルは通常エージェント（fork なし）として動作し、メモリを節約：

| Step | Execution | Memory Impact |
|------|-----------|---------------|
| Step 1-5 | Direct execution | ✅ Low (main context) |
| Step 6 | Task → wordpress-professional-engineer | ✅ Isolated (subagent fork) |
| Step 7-8 | Direct execution (lightweight checks) | ✅ Low (main context) |
| Step 9 | Direct execution | ✅ Low (main context) |

### Architecture Comparison

**Before (Memory Leak):**
```
figma-implement (context: fork)
  ├─ Main context holds design-context.json (76KB) ❌
  │
  └─ Task → wordpress-professional-engineer (fork)
      └─ Double fork + large data in main ❌
      └─ Main context not released ❌
```

**After (Memory Optimized):**
```
figma-implement (no fork)
  ├─ Main context: state.yaml only (1.3KB) ✅
  ├─ design-context.json NOT loaded in main ✅
  │
  └─ Step 6: Task → wordpress-professional-engineer (fork)
      ├─ Reads project-convention.yaml directly ✅
      └─ Subagent context released after completion ✅
```

### Key Points

1. **Main Context = Lightweight**
   - Only state.yaml loaded (~1.3KB)
   - design-context.json read from file when needed, not held in memory

2. **Subagent = Isolated**
   - wordpress-professional-engineer runs in fork context
   - Auto-released after Step 6 completion

3. **Data Flow**
   ```
   Step 1-4: Cache design data to files
   Step 5: Read specs, write to project-convention.yaml
   Step 6: wordpress-engineer reads YAML directly (not via main context)
   Step 7-9: Continue with lightweight main context
   ```

### Completion Verification

| Step | Method | Blocking |
|------|--------|----------|
| Step 6 | Task tool (`wordpress-professional-engineer`) | ✅ Yes |
| Step 8 | Direct execution (lightweight checks) | ✅ Yes |

**Implementation:**
```
1. Task tool 呼び出し（wordpress-professional-engineer）
   - subagent_type: "wordpress-professional-engineer"
   - Passes: page_slug, specs location
   - run_in_background: false（ブロッキング）

2. 完了確認
   - Subagent の完了を待機
   - エラー時は state.yaml に記録して再試行

3. Step 8: Quick Quality Check（軽量）
   - npm run build
   - npm run lint:css
   - grep によるPHPパターン検出
   - サブエージェント不要 ✅
```

## Step 5 Details: Auto Title Extraction

### Extraction Patterns (Priority Order)

The skill automatically extracts page titles from `design-context.json` using the following patterns:

| Priority | Pattern | Criteria |
|----------|---------|----------|
| 1 | Large text element (h1 equivalent) | fontSize ≥ 24px AND positioned in top area |
| 2 | Page header text | Layer name contains "header", "title", or "heading" |
| 3 | Breadcrumb last item | Layer name contains "breadcrumb" or "パンくず" |

### Extraction Logic

```javascript
// Japanese Title
- First heading text containing Japanese characters (hiragana, katakana, kanji)
- Example: "募集要項一覧", "会社概要", "企業理念"

// English Title
- Pattern matching with English keywords
- Example: "Job Description", "Requirements", "About Us", "Philosophy"

// Slug
- English title converted to kebab-case
- Example: "Job Description" → "job-description"
```

### Extraction Success

When extraction succeeds, the skill automatically uses the extracted values:

```
✅ ページタイトルを自動抽出しました:
  - スラッグ: job-description
  - 日本語名: 募集要項一覧
  - 英語見出し: Job Description

※ 自動抽出値を使用します。変更が必要な場合はお知らせください。
```

### Fallback (Extraction Failed)

Only items that could not be extracted are requested from the user (H3 intervention):

```
⚠️ 以下の情報を自動抽出できませんでした。入力してください:

- ページスラッグ: [input required]
- ページの日本語名: [input required if not extracted]
- ページの英語見出し: [input required if not extracted]
```

## Step 6 Details: SCSS Implementation Quality Checklist

### 実装品質チェックリスト（必須）

#### コンテナ構造
- [ ] __container は @include container() のみ
- [ ] レイアウト（display, flex, gap）は __inner に分離
- [ ] __container 直下に __inner がある

#### BEM命名
- [ ] 全てのクラスが kebab-case
- [ ] 二重アンダースコアがない（__heading__en 禁止）
- [ ] ハイフン区切りで統一（__hero-container, __field-label）

#### プロパティ順序
- [ ] position 系が最初
- [ ] display, flex 系が次
- [ ] サイズ系（width, height, margin, padding）
- [ ] タイポグラフィ系（font, line-height, color）
- [ ] ビジュアル系（background, border）

## Step 7 Details: PHP Template Implementation Quality Checklist

### 実装品質チェックリスト（必須）

#### ACF出力
- [ ] 単一行フィールド: p + esc_html()
- [ ] 複数行フィールド: div + wp_kses_post(nl2br())
- [ ] nl2br() で改行を <br> に変換

#### ボタンコンポーネント
- [ ] c-button 使用（c-link-button 廃止）
- [ ] get_template_part('template-parts/common/button') で呼び出し
- [ ] variant を class パラメータで指定

## Step 8 Details: Quick Quality Check (Auto-Execute - SCRIPT REQUIRED)

**⚠️ このステップは自動実行。スキップ不可。**

Step 6 完了後、以下を自動で実行する。エラーがあれば停止し修正を促す。

### 自動実行内容 (SCRIPT REQUIRED)

**MUST** run quality check script:

```bash
bash .claude/skills/figma-implement/scripts/quality-check.sh \
  {実装したSCSSファイル} \
  {実装したPHPファイル}
```

Example:
```bash
bash .claude/skills/figma-implement/scripts/quality-check.sh \
  src/scss/object/project/_p-about.scss \
  themes/{{THEME_NAME}}/pages/page-about.php
```

Exit code handling:
- Exit 0 (PASS) → Step 9 へ進む
- Exit 1 (FAIL) → 修正してから再実行

### Additional Checks (after script)

```bash
# 1. Build check（必須）
npm run build
# → 失敗時: ビルドエラーを表示して停止

# 2. SCSS Lint（必須）
npm run lint:css
# → 警告のみ: 続行、エラー: 停止

# 3. PHP pattern check（対象ファイルのみ）
grep -rn '<img ' {実装したPHPファイル}
grep -rn 'the_field(' {実装したPHPファイル}
# → ヒット時: 修正を指示して停止
```

### 検出パターンと自動修正

| Pattern | Severity | Fix |
|---------|----------|-----|
| `<img src=` | **BLOCK** | `render_responsive_image()` に変更 |
| `the_field(` | **BLOCK** | `get_field()` + `esc_html()` に変更 |
| ビルドエラー | **BLOCK** | エラー内容に基づき修正 |
| Lint警告 | WARN | 次回修正（続行可） |

### エラー時のフロー

```
Step 8 実行
    ↓
エラー検出?
    ├─ YES → 修正を実行 → Step 8 再実行
    └─ NO  → Step 9 へ進む
```

### 重いレビューが必要な場合

ページ全体完成後または納品前のみ `/review` または `/delivery` を使用。

## Human Intervention Points (H1-H5)

The orchestrator automatically pauses at the following points and waits for human input.

| ID | Step | Trigger Condition | Required Input | Timeout |
|----|------|-------------------|----------------|---------|
| H1 | 2-4 | Token limit detected | Section Figma URLs | None (required) |
| H2 | 4-5 | Variable diff exists | Approval (Y/N/select) | 5min (default Y) |
| H3 | 5-1 | Auto-extraction failed | Only items that couldn't be extracted | None (required) |
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

### State Structure (PC/SP Dual Mode)

When `--sp` option is provided, the state file includes additional SP-related fields:

```yaml
# Standard fields
pc_url: "https://figma.com/design/..."
pc_file_key: "abc123"
pc_node_id: "1:2"
pc_cache: ".claude/cache/figma/{page-name}/pc/"

# SP fields (when --sp provided)
sp_url: "https://figma.com/design/..."
sp_file_key: "abc123"
sp_node_id: "3:4"
sp_cache: ".claude/cache/figma/{page-name}/sp/"

# Mode indicator
dual_mode: true  # false when --sp not provided

# Current step
current_step: "Step2"
step_status:
  Step2:
    pc: completed
    sp: in_progress
```

### State Save Timing

- Each step completion
- Human intervention point reached
- Error occurrence
- Explicit interruption (Ctrl+C)

### State Restore

```bash
# Resume from previous state
/figma-implement --resume

# Start from specific step (with state file)
/figma-implement --resume --step Step4
```

### State File Size Management

状態ファイルの肥大化を防止:

| ルール | 内容 |
|--------|------|
| 最大サイズ目安 | 50KB |
| ログ圧縮 | 完了ステップの詳細ログは削除、サマリのみ保持 |
| アーカイブ | 実装完了後、状態ファイルを `.claude/archive/` に移動 |

**--resume 時の処理:**
1. 状態ファイルサイズを確認
2. 50KB超過の場合、古いログを自動削除
3. 警告メッセージを表示

**ログ圧縮の例:**
```yaml
# 圧縮前（詳細ログ）
step_status:
  Step2:
    status: completed
    details: |
      - get_design_context 実行
      - レスポンスサイズ: 77,000 tokens
      - セクション数: 8
      - 各セクションの詳細ログ...（長文）

# 圧縮後（サマリのみ）
step_status:
  Step2:
    status: completed
    summary: "Design context retrieved (8 sections)"
```

**アーカイブ手順（実装完了後）:**
```bash
mkdir -p .claude/archive/
mv .claude/cache/figma-implement-state.yaml \
   .claude/archive/figma-implement-state-{page-name}-{timestamp}.yaml
```

## References

For detailed information, see the following reference documents:

| File | Content |
|------|---------|
| [references/workflow-steps.md](references/workflow-steps.md) | Detailed 9-step workflow instructions |
| [references/state-management.md](references/state-management.md) | State file structure and resume capability |
| [references/error-catalog.md](references/error-catalog.md) | Comprehensive error handling catalog |
| [references/pc-sp-dual-mode.md](references/pc-sp-dual-mode.md) | PC/SP dual implementation details |

## Related Files

| File | Purpose |
|------|---------|
| [workflow-steps.md](workflow-steps.md) | Detailed 9-step workflow instructions |
| `.claude/cache/figma-implement-state.yaml` | State persistence file |
| `.claude/cache/figma-implement-report-*.yaml` | Completion reports |
| `.claude/cache/figma/` | Figma cache directory |
| `.claude/cache/visual-diff/` | Diff validation images |
| `.claude/rules/figma-workflow.md` | Figma workflow rules |
| `.claude/catalogs/component-catalog.yaml` | Component catalog |

## Examples

### Basic Usage (New Implementation)

```bash
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2
```

### Resume from Interruption

```bash
# Check previous state
cat .claude/cache/figma-implement-state.yaml

# Resume
/figma-implement --resume
```

### Dry Run (Plan Confirmation)

```bash
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --dry-run
```

### Interactive Mode

```bash
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --interactive
```

### Strict Validation Mode

```bash
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --preset strict
```

### PC/SP Dual Implementation

```bash
# Implement with both PC and SP Figma designs
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2 \
  --sp https://www.figma.com/design/abc123/MyDesign?node-id=5-6
```

This mode:
- Retrieves both PC and SP design contexts in Step 2
- Captures screenshots for both versions in Step 3
- Generates PC/SP diff table in Step 5
- Implements responsive styles based on actual SP specs in Step 6
- Validates SP against Figma SP (not just resize) in Step 7

### Token-Saving Mode (Recommended)

```bash
# Skip screenshots for faster, token-efficient implementation
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --no-screenshot
```

This mode:
- Skips Step 3 (get_screenshot) entirely
- Relies on JSX code from get_design_context for accurate implementation
- Recommended when design has proper Auto Layout

## Design Prerequisites

For high implementation accuracy, ensure the Figma design meets these conditions:

### Required

| Condition | Reason |
|-----------|--------|
| Auto Layout properly used | Accurate spacing and alignment in JSX output |
| Semantic layer naming | AI can infer element purposes from names |
| Flattened vector groups | Prevents multiple `<img>` tags per element |

### High Accuracy Elements

When prerequisites are met, these are accurately reproduced:

- Font family, weight, size, line-height
- Text/background/border colors
- Auto Layout based positioning and margins

### May Need Adjustment

| Element | Reason |
|---------|--------|
| Absolute positioned elements | May need manual CSS adjustments |
| Complex vector graphics | Consider placeholders or SVG export |

## Research Reference

Implementation based on Figma MCP best practices research.
See: `.shogun/reports/figma-mcp-research.md`

## Troubleshooting

### Error: "Cache not found"

**Cause**: `/figma-prefetch` was not run before implementation.

**Solution**:
1. Run `/figma-prefetch {url}` first
2. Verify cache:
   ```bash
   bash .claude/skills/figma-implement/scripts/validate-cache.sh \
     .claude/cache/figma/{page-name}
   ```
3. Then run `/figma-implement`

### Error: "raw_jsx validation failed"

**Cause**: Cached raw_jsx is abstracted or incomplete.

**Solution**:
1. Check the specific node:
   ```bash
   cat .claude/cache/figma/{page}/nodes/{nodeId}.json | jq '.raw_jsx | length'
   ```
2. If length < 500 or contains "// Section", re-fetch:
   ```bash
   /figma-recursive-splitter {url} --force
   ```
3. Or use `get_design_context` directly for that section

### Error: "Token limit exceeded"

**Cause**: Page is too large for single retrieval.

**Solution**:
1. Use `/figma-recursive-splitter` for split retrieval
2. Or use `--section` option to implement one section at a time:
   ```bash
   /figma-implement --page {page} --section hero
   ```

### Error: "Build failed" (Step 8)

**Cause**: SCSS/PHP syntax error or missing import.

**Solution**:
1. Run build manually to see detailed error:
   ```bash
   npm run build
   ```
2. Check SCSS imports in `src/css/pages/{page}.css`
3. Verify PHP file has `Template Name:` comment
4. Fix errors and re-run Step 8

### Error: "Playwright connection failed"

**Cause**: Browser not installed or Docker network issue.

**Solution**:
1. Check Playwright installation:
   ```bash
   npx playwright install chromium
   ```
2. Verify Docker is running if using containerized browser
3. Check MCP Playwright server is connected

### Error: "Container width incorrect"

**Cause**: Wrong calculation method or missing artboard info.

**Solution**:
1. Use `/figma-container-width-calculator` for accurate calculation
2. Verify artboard margin-based formula:
   ```
   containerWidth = artboardWidth - (firstContentFrame.x * 2)
   ```
3. Check metadata.json for artboard dimensions

### Error: "Design tokens extraction failed"

**Cause**: Figma Variables not defined or API error.

**Solution**:
1. Check if Figma file has Variables defined
2. If Variables are empty, manually extract from design-context:
   - Colors: Look for `fill` and `stroke` properties
   - Fonts: Look for `fontFamily`, `fontSize`, `fontWeight`
   - Spacing: Look for `gap`, `padding`, `margin` values
3. Add extracted values to `foundation/_variables.scss`

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma/` | Figma cache directory |
| `.claude/rules/figma-workflow.md` | Workflow rules |
| `.claude/rules/figma.md` | Figma integration rules |
| `scripts/validate-cache.sh` | Cache validation script |
| `scripts/validate-raw-jsx.sh` | raw_jsx validation script |
| `scripts/quality-check.sh` | Quality check script |

---

**Version**: 2.3.0
**Created**: 2026-01-30
**Updated**: 2026-02-02
**Changes**:
- v2.3.0: 公式スキルガイド準拠の改修
  - scripts/ ディレクトリ追加（validate-cache.sh, validate-raw-jsx.sh, quality-check.sh）
  - Step 0, 0.5, 8 にスクリプト検証を明示的に追加
  - Troubleshooting セクション追加
  - description にトリガーフレーズ追加
- v2.2.0: Step 0.5 追加 - キャッシュ読み込み時の raw_jsx 検証
  - 不完全なキャッシュを検出して API 再取得
  - recruit-info/mvv の省略問題を防止
- v2.1.0: Step 8 を軽量チェックに変更（production-reviewer 削除）
- v2.0.0: Phase 0 を `/figma-prefetch` スキルに分離
