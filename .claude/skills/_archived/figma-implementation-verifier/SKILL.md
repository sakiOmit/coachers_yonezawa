---
name: figma-implementation-verifier
description: "Figma実装の第三者検証を自動化するスキル"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - mcp__figma__get_design_context
context: fork
agent: general-purpose
---

# Figma Implementation Verifier

Figma nodeのデザイン値と実装コード（SCSS/PHP）を比較し、実装の正確性を検証するスキル。
視覚的な比較ではなく、**コード値の検証**に特化。

## Usage

```bash
# 基本使用（対話形式でURL入力）
/figma-implementation-verifier

# Figma URLとファイルを指定
/figma-implementation-verifier --figma="https://figma.com/design/xxx?node-id=1-2" --files="src/scss/layout/_header.scss,themes/xxx/header.php"

# セクション名で自動検索
/figma-implementation-verifier --figma="https://figma.com/design/xxx?node-id=1-2" --section="header"

# production-reviewerから呼び出し
/figma-implementation-verifier --figma="..." --reviewer-mode
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--figma` | Yes | Figma URL (fileKeyとnodeIdを含む) |
| `--files` | No | 検証対象ファイル（カンマ区切り） |
| `--section` | No | セクション名（自動でファイル検索） |
| `--threshold` | No | 許容誤差 (デフォルト: 1px) |
| `--reviewer-mode` | No | production-reviewerとの連携モード |

## 検証対象と閾値（必須）

| 検証対象 | Figma Property | SCSS Property | 許容閾値 |
|---------|----------------|---------------|---------|
| 色 | fills, strokes, color | background, color, border-color | **完全一致** |
| フォントサイズ | fontSize | font-size | **±1px** |
| スペーシング | padding, itemSpacing | padding, margin, gap | **±1px** |
| サイズ | width, height | width, height | **±1px** |
| 角丸 | cornerRadius | border-radius | **±1px** |
| ボーダー幅 | strokeWeight | border-width | **±1px** |

**重要**: 1px以内の差異は許容。色は完全一致が必須。

## Difference from figma-design-diff-checker

| 項目 | figma-implementation-verifier | figma-design-diff-checker |
|------|------------------------------|---------------------------|
| 比較対象 | コード値 vs Figma node値 | スクリーンショット比較 |
| 出力 | 値の差異表 | 視覚的差異 |
| 用途 | コードレビュー、第三者検証 | 視覚的QA |
| 実行速度 | 高速（API + ファイル読み込み） | 中速（ブラウザ起動必要） |

## 前提条件（必須）

### キャッシュ確認

```bash
ls -la .claude/cache/figma/{page-name}/
```

**キャッシュ構造:**
```
.claude/cache/figma/{page-name}/
├── metadata.json
├── section-{n}.json
└── text-extracted.json
```

**キャッシュがない場合:**
- 実装・検証・修正の着手禁止
- 先に figma-recursive-splitter または figma-section-splitter を実行

### ルール参照

- `.claude/rules/figma.md` を必ず確認
- RULE-001〜003 を遵守

## 5-Step Workflow

### Step 1: Figma nodeId/fileKey取得

**1-1. URL解析**

```
URL: https://figma.com/design/{fileKey}/{fileName}?node-id={nodeId}
→ fileKey: {fileKey}
→ nodeId: {nodeId} (URLの 1-2 → 1:2 に変換)
```

### Step 2: デザインコンテキスト取得（キャッシュ優先）

**2-1. キャッシュ確認**

```bash
# ページ名からキャッシュディレクトリを確認
ls -la .claude/cache/figma/{page-name}/section-*.json
```

**2-2. キャッシュがある場合（API呼び出しスキップ）**

```
Read tool: .claude/cache/figma/{page-name}/section-{n}.json
```

キャッシュから design_context を読み込み、Step 3 へ進む。

**2-3. キャッシュがない場合の対応**

キャッシュがない場合は検証前にデータ取得を必須化:

```bash
# エラー表示
echo "エラー: Figmaキャッシュが見つかりません。"
echo "検証の前に、以下のコマンドでデータを取得してください:"
echo "/figma-recursive-splitter --figma='...' --page-name='{page-name}'"
echo ""
echo "または、キャッシュなしでAPI呼び出しを実行（非推奨）:"
```

**推奨**: 先に figma-recursive-splitter でデータ取得。

**緊急時のみ**: API呼び出し

```
mcp__figma__get_design_context
  fileKey: {extracted from URL}
  nodeId: {extracted from URL}
  clientLanguages: "php,scss"
  clientFrameworks: "wordpress"
```

**2-4. node値抽出**

レスポンスから以下の値を抽出:

| カテゴリ | 抽出項目 |
|---------|---------|
| 色 | fill, stroke, background |
| フォント | fontFamily, fontSize, fontWeight, lineHeight, letterSpacing |
| スペーシング | padding, margin, gap |
| サイズ | width, height |
| 角丸 | borderRadius |
| 透明度 | opacity |

### Step 3: 対象ファイル（SCSS/PHP）を読み込み

**3-1. 対象ファイル特定**

優先順位:
1. `--files` で指定されたファイル
2. `--section` からの自動検索
3. Figma node名から推測（例: "header" → `_header.scss`）

**3-2. SCSSからの値抽出**

```scss
.l-header {
  background: rgba(255, 255, 255, 0.6);  // → background抽出
  padding: rv(16) rv(24);                // → padding抽出
  font-size: rv(16);                     // → font-size抽出
}
```

**3-3. PHPからのクラス名確認**

```php
<header class="l-header">  // → クラス名確認
```

### Step 4: node値と実装値を比較

**4-1. 比較表生成**

| 項目 | Figma値 | 実装値 | 差異 | 判定 |
|------|---------|--------|------|------|
| background | rgba(255,255,255,0.6) | rgba(255,255,255,0.6) | 0 | ✅ |
| font-size | 16px | rv(16) → 16px | 0 | ✅ |
| padding-top | 24px | rv(24) → 24px | 0 | ✅ |
| gap | 24px | rv(20) → 20px | 4px | ❌ |

**4-2. 閾値判定ルール**

```
差異 = |Figma値 - 実装値|

if 検証対象 == "色":
    判定 = (差異 == 0) ? ✅ : ❌
else:
    判定 = (差異 <= 1px) ? ✅ : ❌
```

### Step 5: 差異レポートを生成

```markdown
## Implementation Verification Report

### Summary
- Figma: {fileKey}/{nodeId}
- Files: _header.scss, header.php
- Total Items: 15
- Passed: 14
- Failed: 1

### Comparison Results

| # | Property | Figma | Implementation | Diff | Status |
|---|----------|-------|----------------|------|--------|
| 1 | background | rgba(255,255,255,0.6) | rgba(255,255,255,0.6) | 0 | ✅ |
| 2 | font-size | 16px | 16px | 0 | ✅ |
| 3 | gap | 24px | 20px | 4px | ❌ |

### Issues Found

1. **gap mismatch** (src/scss/layout/_header.scss:25)
   - Figma: 24px
   - Implementation: rv(20) = 20px
   - Fix: Change to rv(24)

### Recommended Fixes

\`\`\`scss
// src/scss/layout/_header.scss:25
// Before:
gap: rv(20);

// After:
gap: rv(24);
\`\`\`
```

## Verification Categories

### 色 (Colors)

| Figma Property | SCSS Property |
|----------------|---------------|
| fills[0].color | background, background-color |
| strokes[0].color | border-color |
| style.color | color |

**変換ルール:**
- Figma RGBA {r,g,b,a} → CSS rgba(r*255, g*255, b*255, a)
- 透明度1の場合 → HEX形式に変換可

### フォント (Typography)

| Figma Property | SCSS Property |
|----------------|---------------|
| fontSize | font-size |
| fontWeight | font-weight |
| lineHeight | line-height |
| letterSpacing | letter-spacing |
| fontFamily | font-family |

**変換ルール:**
- Figma lineHeight (%) → CSS (値/100)
- Figma letterSpacing (%) → CSS em (値/100)

### スペーシング (Spacing)

| Figma Property | SCSS Property |
|----------------|---------------|
| paddingTop/Right/Bottom/Left | padding |
| itemSpacing | gap |
| absoluteBoundingBox | width, height |

**変換ルール:**
- rv(x) → x px（PC固定値）
- svw(x) → x/375*100vw（SP可変値）

## Threshold Rules

| Property Type | Default Threshold | Note |
|---------------|-------------------|------|
| サイズ (px) | 1px | 小数点以下の差異は許容 |
| 色 | 完全一致 | HEX/RGBA完全一致 |
| 透明度 | 0.01 | 小数点2桁まで |
| 角丸 | 1px | 小数点以下の差異は許容 |

## Output

検証結果は標準出力に表示。保存オプション:

```bash
/figma-implementation-verifier --figma="..." --save
```

保存先: `.claude/verification-reports/verify-{timestamp}.md`

## Integration

### production-reviewer との連携

production-reviewer エージェントからの呼び出しパターン:

**呼び出し方法:**

```
Task tool: subagent_type=production-reviewer
prompt: |
  Figma実装の検証を含むレビューを実行してください。

  【Figma検証を先に実行】
  /figma-implementation-verifier --figma="{figma_url}" --reviewer-mode

  【検証結果の統合】
  - Figma検証でIssueがあれば、通常レビューのIssuesに追加
  - 差異がなければ「Figma実装: ✅」をサマリーに記載

  【通常レビュー】
  FLOCSS + BEM, セキュリティ, コード品質をチェック
```

**reviewer-mode の動作:**
- 標準出力を簡潔に（サマリーのみ）
- 詳細は `.claude/reviews/` に保存
- Issue形式で出力（production-reviewerが統合しやすい形式）

**統合レポート例:**

```markdown
## Production Readiness Review

### Figma Implementation (from figma-implementation-verifier)
- ✅ 色: 5/5 一致
- ⚠️ スペーシング: 4/5 一致 (1件差異あり)
- ✅ フォントサイズ: 3/3 一致

### SCSS Issues (from standard review)
- [SAFE] name-001: CamelCase class name
...
```

### figma-implement との連携

**figma-implement Step 7 での使用:**

```markdown
## Step 7: Figmaとの検証

### 7-1. コード値検証（自動）

実装完了後、figma-implementation-verifierを実行:

/figma-implementation-verifier --figma="{figma_url}" --section="{section_name}"

### 7-2. 差異があれば修正

レポートの「Recommended Fixes」に従って修正。

### 7-3. 視覚差分検証へ進む

コード値検証パス後、figma-design-diff-checkerで視覚確認。
```

**フルワークフロー:**

```bash
# 1. Figmaから実装
/figma-implement

# 2. コード値検証（本スキル）
/figma-implementation-verifier

# 3. 視覚差分検証
/figma-design-diff-checker

# 4. 本番レビュー
/review
```

## 関連ファイル

- `.claude/rules/figma.md` - Figmaワークフロールール（RULE-001〜003）
- `.claude/skills/figma-implement/SKILL.md` - Figma実装スキル
- `.claude/skills/figma-design-diff-checker/SKILL.md` - 視覚差分検証スキル
- `.claude/catalogs/component-catalog.yaml` - コンポーネントカタログ

---

**Instructions for Claude:**

Based on `$ARGUMENTS`, execute implementation verification:

1. **Parse Arguments**
   - Extract `--figma` URL → parse fileKey and nodeId
   - Extract `--files` or `--section` → determine target files
   - If `--section` provided, search for related files:
     - `header` → `_header.scss`, `header.php`
     - `footer` → `_footer.scss`, `footer.php`
     - etc.
   - If arguments missing, ask user interactively

2. **URL Parsing for Figma**
   ```
   https://figma.com/design/{fileKey}/{fileName}?node-id={nodeId}
   → fileKey: {fileKey}
   → nodeId: {nodeId} (replace - with :)
   ```

3. **Get Figma Design Context (キャッシュ優先)**

   **Check cache first:**
   ```bash
   ls .claude/cache/figma/{page-name}/section-*.json
   ```

   **If cache exists (24時間以内):**
   ```
   Read tool: .claude/cache/figma/{page-name}/section-{n}.json
   ```
   Use cached data → skip API call → proceed to Step 4

   **If no cache:**
   - Display error: "Figmaキャッシュが見つかりません"
   - Recommend: "先に /figma-recursive-splitter を実行してください"
   - Emergency only: call API
   ```
   mcp__figma__get_design_context
     fileKey: {fileKey}
     nodeId: {nodeId}
     clientLanguages: "php,scss"
     clientFrameworks: "wordpress"
   ```
   → Save to cache: `.claude/cache/figma/{page-name}/section-{n}.json`

4. **Extract Figma Values**

   From the response, extract:
   - Colors: background, text color, border color
   - Typography: font-size, font-weight, line-height, letter-spacing
   - Spacing: padding, margin, gap
   - Sizes: width, height
   - Border: border-radius, border-width

   Note: Response is React+Tailwind format. Convert:
   - `bg-[rgba(255,255,255,0.6)]` → `rgba(255,255,255,0.6)`
   - `text-[16px]` → `16px`
   - `gap-[24px]` → `24px`

5. **Read Implementation Files**

   For each target file:
   ```
   Read tool: {file_path}
   ```

   Extract SCSS values:
   - Parse property: value pairs
   - Convert rv(x) → x px
   - Convert svw(x) → x/375*100 vw

6. **Compare Values**

   For each property:
   ```
   diff = abs(figma_value - implementation_value)
   status = diff <= threshold ? "✅" : "❌"
   ```

7. **Generate Report**

   Create markdown report with:
   - Summary (total, passed, failed)
   - Comparison table
   - Issues list with file:line references
   - Recommended fixes with code snippets

8. **Display Results**

   - Show summary: "X/Y items passed"
   - If all passed: "✅ Implementation matches Figma design"
   - If issues found:
     - List each issue
     - Show fix suggestions
     - Suggest: "Run fixes and re-verify"

**Value Extraction Patterns:**

SCSS patterns to match:
```
background: {value};
background-color: {value};
color: {value};
font-size: {value};
padding: {value};
margin: {value};
gap: {value};
width: {value};
height: {value};
border-radius: {value};
```

rv() conversion:
```
rv(16) → 16px
rv(24) → 24px
```

**Output Language:** Japanese

**Error Handling:**
- If Figma API fails: "Figma APIエラー。URLを確認してください。"
- If files not found: "ファイルが見つかりません: {path}"
- If no values to compare: "比較可能な値が見つかりませんでした。"
