---
name: figma-implement
description: "Implement Figma design as Astro static code (9-step). Trigger: 'implement design', 'Figma to code', 'create page from Figma'."
argument-hint: "{pc_url} [--sp {sp_url}] [--section {name}] [--resume]"
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
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_snapshot
  - mcp__playwright__browser_take_screenshot
model: opus
context: fork
agent: general-purpose
---

# Figma Implement Orchestrator

## Dynamic Context

```
Figma cache status:
!`ls .claude/cache/figma/ 2>/dev/null || echo "(empty)"`

Resume state:
!`cat .claude/cache/figma-implement-state.yaml 2>/dev/null || echo "No state"`
```

## Overview

Orchestration skill that manages the Figma to Astro static coding implementation workflow (9 steps).
WordPress conversion is handled separately by `/astro-to-wordpress`.
Provides state persistence, resume capability, and error recovery to maximize efficiency in large-scale page implementation.

### Key Features

- **Unified Management**: Automatic execution and progress tracking across 9 steps
- **State Persistence**: Save state to YAML on interruption
- **Resume Capability**: Continue from previous state with `--resume` option
- **Error Recovery**: Auto-retry and pause at human intervention points
- **Progress Reports**: Real-time progress display and completion report generation
- **Context Optimization**: Screenshot省略モードでトークン消費を削減

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | `/figma-analyze`（任意） |
| **後工程** | `/astro-to-wordpress`, `/review` |
| **呼び出し元** | ユーザー直接, `/figma-analyze` 出力から |
| **呼び出し先** | astro-component-engineer エージェント |

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
   - Refer to `.claude/rules/figma.md` for container width calculation rules

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
- `.claude/rules/figma.md` - Detailed calculation rules

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
│  ├─ 6-1. astro-component-engineer     │
│  │       (Task) + PC/SP specs         │
│  ├─ 6-2. Astro/SCSS implementation    │
│  ├─ 6-3. Build (npm run astro:build)  │
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
│  ├─ 8-1. npm run astro:build → BLOCK  │
│  ├─ 8-2. npm run lint:css → WARN only │
│  └─ 8-3. Astro pattern check (grep)   │
│          ├─ <img> → BLOCK             │
│          ├─ <style> scoped → BLOCK    │
│          └─ .astro SCSS/JS import     │
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

- **目的**: キャッシュの有効性を確認し、不正なキャッシュによる実装ミスを防止する
- **入力**: `.claude/cache/figma/{page-slug}` ディレクトリ
- **出力**: CACHE_VALID / CACHE_EXPIRED / CACHE_NOT_FOUND
- **成功条件**: Exit 0 でスクリプトが完了
- **詳細**: → references/workflow-steps.md の Step 0 セクション参照

```bash
bash .claude/skills/figma-implement/scripts/validate-cache.sh \
  .claude/cache/figma/{page-slug}
```

Exit code: 0 (PASS) → Step 1 へ / 1 (FAIL) → 停止、/figma-prefetch 実行を指示

### Error Handling

| 状況 | 対応 |
|------|------|
| サブエージェント起動失敗 | 3回リトライ後、手動確認を指示 |
| キャッシュパス不明 | URL から page-slug を抽出して検索 |

## Step 0.5: raw_jsx Validation (Mandatory for Cached Data)

- **目的**: キャッシュの raw_jsx が省略・抽象化されていないか検証する
- **入力**: `nodes/*.json` の `raw_jsx` フィールド
- **出力**: VALID / INVALID（検証条件 6 項目）
- **成功条件**: 全条件クリア（文字列長 >= 500、JSX構造あり、省略コメントなし）
- **詳細**: → references/workflow-steps.md の「Step 0.5 詳細」セクション参照

```bash
for node_file in .claude/cache/figma/{page-slug}/nodes/*.json; do
  bash .claude/skills/figma-implement/scripts/validate-raw-jsx.sh \
    "$node_file" "$(basename "$node_file" .json)"
done
```

## Memory Leak Mitigation (Lightweight Main Context)

| Step | Execution | Memory Impact |
|------|-----------|---------------|
| Step 1-5 | Direct execution | ✅ Low (main context) |
| Step 6 | Task → astro-component-engineer | ✅ Isolated (subagent fork) |
| Step 7-8 | Direct execution (lightweight checks) | ✅ Low (main context) |
| Step 9 | Direct execution | ✅ Low (main context) |

**Data Flow:**
```
Step 1-4: Cache design data to files
Step 5: Read specs, write to project-convention.yaml
Step 6: astro-component-engineer reads YAML directly (not via main context)
Step 7-9: Continue with lightweight main context
```

## Step 1: Node ID Extraction

- **目的**: Figma URL から fileKey と nodeId を抽出する
- **入力**: pc_url（および --sp オプションの sp_url）
- **出力**: pc_fileKey, pc_nodeId（, sp_fileKey, sp_nodeId）
- **成功条件**: 正規表現で両値が取得できた
- **詳細**: → references/workflow-steps.md の Step 1 セクション参照

## Step 2: Design Context Retrieval

- **目的**: Figma からデザインコンテキスト（raw_jsx, スタイル情報）を取得する
- **入力**: fileKey, nodeId（PC/SP）
- **出力**: design-context.json（PC/SP）、トークン制限時は H1 介入
- **成功条件**: raw_jsx を含む node データが取得でき、キャッシュに保存された
- **詳細**: → references/workflow-steps.md の Step 2 セクション参照

## Step 3: Visual Reference (Optional)

- **目的**: 視覚的参照用スクリーンショットを取得する（--no-screenshot でスキップ推奨）
- **入力**: fileKey, nodeId（PC/SP）
- **出力**: figma_{section}_pc.png（, figma_{section}_sp.png）
- **成功条件**: スクリーンショットが保存された、またはスキップ指定
- **詳細**: → references/workflow-steps.md の Step 3 セクション参照

## Step 4: Assets + Design Tokens

- **目的**: アセットをダウンロードし、Figma Variables を SCSS 変数に変換する
- **入力**: design-context.json のアセット URL、mcp__figma__get_variable_defs
- **出力**: assets/images/ 配置済みファイル、_variables.scss 差分（H2 確認後に適用）
- **成功条件**: アセット配置完了・変数差分ユーザー確認済み
- **詳細**: → references/workflow-steps.md の Step 4 セクション参照

## Step 5: Project Convention Translate

- **目的**: デザイン情報をプロジェクト規約（FLOCSS + BEM, ページ情報）に変換する
- **入力**: design-context.json、component-catalog.yaml
- **出力**: project-convention.yaml（ページスラッグ・Node 仕様・PC/SP 差分表）
- **成功条件**: ページタイトル確定・コンポーネント照合完了・Node 仕様書生成
- **詳細**: → references/workflow-steps.md の「Step 5 詳細」セクション参照

## Step 6: Pixel-Perfect Implementation

- **目的**: astro-component-engineer エージェントを使い Astro/SCSS を実装する
- **入力**: project-convention.yaml（Node 仕様、PC/SP 差分表）
- **出力**: Astro ページ・セクションコンポーネント・モックデータ・SCSS ファイル
- **成功条件**: npm run astro:build 成功・lint:css 違反 0 件
- **詳細**: → references/workflow-steps.md の「Step 6 詳細」セクション参照

## Step 7: Figma Validation

- **目的**: Playwright + visual-diff.js でピクセルパーフェクトを検証・修正する
- **入力**: Astro 開発サーバー（localhost:4321）、Figma スクリーンショット
- **出力**: diff_{section}.png、差分検証レポート、最終フルページ PNG
- **成功条件**: 全セクション passed: true（または H5 で人間承認）
- **詳細**: → references/workflow-steps.md の「Step 7 詳細」セクション参照

## Step 8: Quick Quality Check (Auto-Execute - SCRIPT REQUIRED)

- **目的**: 実装ファイルの Astro/SCSS パターン違反を自動検出・修正する
- **入力**: 実装済み .scss ファイル、.astro ファイル
- **出力**: チェック結果（PASS / BLOCK エラー一覧）
- **成功条件**: quality-check.sh が Exit 0 で完了
- **詳細**: → references/workflow-steps.md の「Step 8 詳細」セクション参照

```bash
bash .claude/skills/figma-implement/scripts/quality-check.sh \
  {実装したSCSSファイル} \
  {実装したAstroファイル}
```

## Step 9: Token Efficiency Report

- **目的**: トークン使用量・キャッシュ効果・検証イテレーション回数をレポートする
- **入力**: 各ステップの実行ログ・キャッシュ利用状況
- **出力**: 効率レポート（キャッシュ利用状況・削減率・コンポーネント照合結果）
- **成功条件**: レポート出力完了
- **詳細**: → references/workflow-steps.md の Step 9 セクション参照

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

| ルール | 内容 |
|--------|------|
| 最大サイズ目安 | 50KB |
| ログ圧縮 | 完了ステップの詳細ログは削除、サマリのみ保持 |
| アーカイブ | 実装完了後、状態ファイルを `.claude/archive/` に移動 |

## References

For detailed information, see the following reference documents:

| File | Content |
|------|---------|
| [references/workflow-steps.md](references/workflow-steps.md) | 9ステップ詳細手順（検証条件・チェックリスト・フロー含む） |
| [references/state-management.md](references/state-management.md) | State file structure and resume capability |
| [references/error-catalog.md](references/error-catalog.md) | Comprehensive error handling catalog |
| [references/pc-sp-dual-mode.md](references/pc-sp-dual-mode.md) | PC/SP dual implementation details |
| [references/troubleshooting.md](references/troubleshooting.md) | エラー別トラブルシューティング |
| [CHANGELOG.md](CHANGELOG.md) | バージョン履歴 |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma-implement-state.yaml` | State persistence file |
| `.claude/cache/figma-implement-report-*.yaml` | Completion reports |
| `.claude/cache/figma/` | Figma cache directory |
| `.claude/cache/visual-diff/` | Diff validation images |
| `.claude/rules/figma.md` | Figma implementation rules |
| `.claude/catalogs/component-catalog.yaml` | Component catalog |

## Examples

### Basic Usage (New Implementation)

```bash
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2
```

### Resume from Interruption

```bash
cat .claude/cache/figma-implement-state.yaml
/figma-implement --resume
```

### PC/SP Dual Implementation

```bash
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2 \
  --sp https://www.figma.com/design/abc123/MyDesign?node-id=5-6
```

### Token-Saving Mode (Recommended)

```bash
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --no-screenshot
```

### Strict Validation Mode

```bash
/figma-implement https://www.figma.com/design/abc123/MyDesign?node-id=1-2 --preset strict
```

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | exit code |
|-----------|------|-----------|
| `scripts/validate-cache.sh` | Figmaキャッシュ検証 | 0=PASS, 1=FAIL |
| `scripts/validate-raw-jsx.sh` | Figma生成コード検証 | 0=PASS, 1=FAIL |
| `scripts/quality-check.sh` | 実装品質チェック | 0=PASS, 1=FAIL |
