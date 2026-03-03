---
name: figma-design-diff-checker
description: "QA report generation for final verification. Generates detailed comparison tables and client-ready reports. Use before delivery/acceptance testing."
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Write
  - Bash
  - Glob
  - mcp__figma__get_screenshot
  - mcp__figma__get_design_context
  - mcp__playwright__browser_resize
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_evaluate
  - mcp__playwright__browser_take_screenshot
context: fork
agent: general-purpose
---

# Figma Design Diff Checker

FigmaデザインとWordPress実装を比較し、項目別の詳細な差異を検出・レポートするスキル。
スクリーンショット比較に加え、**デザインコンテキストからの値抽出による精密比較**を実行。

## When to Use (使用場面)

### ✅ Use This Tool When:

| Scenario | Description |
|----------|-------------|
| **Final QA before delivery** | 納品前の最終確認 |
| **Client report generation** | クライアント向け報告書の作成 |
| **Acceptance testing** | 検収テスト時のエビデンス |
| **Detailed documentation** | 詳細な比較表が必要な場合 |
| **Code review evidence** | コードレビュー時の添付資料 |

### ❌ Do NOT Use When:

| Scenario | Use Instead |
|----------|-------------|
| **Development iteration** | `/figma-visual-diff-runner` |
| **Auto-fix needed** | `/figma-visual-diff-runner` |
| **CI/CD automated checks** | `/figma-visual-diff-runner` |
| **Rapid prototyping** | `/figma-visual-diff-runner` |

### Related Tool

**自動修正が必要な場合は `/figma-visual-diff-runner` を使用してください。**

- 差分検出・自動修正を最大5回イテレーション
- 開発中・CI/CD向け
- 素早くFigmaに近づけたい場合に最適

## Usage

```bash
# 基本使用（対話形式でURL入力）
/figma-design-diff-checker

# Figma URLと実装URLを指定
/figma-design-diff-checker --figma="https://figma.com/design/xxx?node-id=1-2" --url="http://localhost:8000/about"

# セクション単位で検証
/figma-design-diff-checker --figma="https://figma.com/design/xxx?node-id=1-2" --url="http://localhost:8000/about" --section="header"

# 厳密モード（許容差なし）
/figma-design-diff-checker --figma="..." --url="..." --strict

# PC/SP両方検証
/figma-design-diff-checker --figma="..." --url="..." --responsive
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--figma` | Yes | Figma URL (fileKeyとnodeIdを含む) |
| `--url` | Yes | 実装ページのURL |
| `--section` | No | 検証対象セクション (header, footer, hero等) |
| `--width` | No | ブラウザ幅 (デフォルト: 1440) |
| `--height` | No | ブラウザ高さ (デフォルト: 900) |
| `--strict` | No | 厳密モード（許容差0） |
| `--responsive` | No | PC/SP両方検証 |
| `--save` | No | レポートをファイル保存 |

## Difference from figma-implementation-verifier

| 項目 | figma-design-diff-checker | figma-implementation-verifier |
|------|---------------------------|------------------------------|
| **主な用途** | デザインQA・視覚検証 | コードレビュー・第三者検証 |
| **比較方法** | スクリーンショット + 値抽出 | コードファイル直接解析 |
| **出力形式** | 詳細比較表 + 差分画像 | 値比較レポート |
| **検証観点** | 視覚的一致 + 数値精度 | 実装コードの正確性 |
| **実行速度** | 中速（ブラウザ起動必要） | 高速（ファイル読み込みのみ） |
| **推奨シーン** | Figma実装後の最終確認 | 実装中のセルフチェック |

## Diff Detection Items

### 差異検出項目一覧

| 項目 | 抽出元（Figma） | 抽出元（実装） | 比較方法 |
|------|----------------|----------------|----------|
| 色 | fills, strokes | background, color, border-color | HEX/RGBA完全一致 |
| フォントサイズ | fontSize | font-size | 数値比較（1px許容） |
| フォントウェイト | fontWeight | font-weight | 完全一致 |
| 行間 | lineHeight | line-height | 数値比較（0.1許容） |
| 字間 | letterSpacing | letter-spacing | 数値比較（0.01em許容） |
| パディング | paddingTop/Right/Bottom/Left | padding | 数値比較（1px許容） |
| マージン | margin (計算値) | margin | 数値比較（1px許容） |
| ギャップ | itemSpacing | gap | 数値比較（1px許容） |
| 幅 | absoluteBoundingBox.width | width | 数値比較（1px許容） |
| 高さ | absoluteBoundingBox.height | height | 数値比較（1px許容） |
| 角丸 | cornerRadius | border-radius | 数値比較（1px許容） |
| ボーダー幅 | strokeWeight | border-width | 数値比較（0.5px許容） |
| 透明度 | opacity | opacity | 数値比較（0.01許容） |

### 許容差設定（Threshold）

| プリセット | 数値許容差 | 色許容差 | 用途 |
|-----------|-----------|---------|------|
| `strict` | 0 | 完全一致 | ピクセルパーフェクト必須 |
| `default` | 1px | 完全一致 | 標準（推奨） |
| `lenient` | 2px | RGB各±5 | レスポンシブ・フォント差許容 |

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

- `.claude/rules/figma-workflow.md` を必ず確認
- RULE-001〜003 を遵守

## Workflow

### Step 1: Figmaスクリーンショット取得

```
mcp__figma__get_screenshot
  fileKey: {extracted from URL}
  nodeId: {extracted from URL}
```

### Step 2: デザインコンテキスト取得（キャッシュ優先）

**2-1. キャッシュ確認**

```bash
# キャッシュファイルの存在確認
ls -la .claude/cache/figma/{page-name}/section-*.json
```

**2-2. キャッシュがある場合（API呼び出しスキップ）**

```
Read tool: .claude/cache/figma/{page-name}/section-{n}.json
```

キャッシュから design_context を読み込み、Step 3 へ進む。

**2-3. キャッシュがない場合のみAPI呼び出し**

```
mcp__figma__get_design_context
  fileKey: {extracted from URL}
  nodeId: {extracted from URL}
  clientLanguages: "php,scss,javascript"
  clientFrameworks: "wordpress"
```

取得後、キャッシュフォルダに保存:
```bash
mkdir -p .claude/cache/figma/{page-name}/
# 保存処理
```

### Step 3: Figma値の抽出

レスポンスから以下の値を構造化抽出:

```yaml
figma_values:
  colors:
    background: "rgba(255, 255, 255, 0.6)"
    text: "#333333"
    border: "#E0E0E0"
  typography:
    font_size: "16px"
    font_weight: "400"
    line_height: "1.75"
    letter_spacing: "0.05em"
  spacing:
    padding_top: "24px"
    padding_right: "32px"
    padding_bottom: "24px"
    padding_left: "32px"
    gap: "24px"
  sizes:
    width: "1200px"
    height: "auto"
  borders:
    radius: "8px"
    width: "1px"
  effects:
    opacity: "1"
```

### Step 4: 実装ページの値抽出

Playwrightで実装ページを開き、Computed Stylesを取得:

```
mcp__playwright__browser_resize
  width: {width or 1440}
  height: {height or 900}

mcp__playwright__browser_navigate
  url: {implementation URL}

mcp__playwright__browser_evaluate
  function: |
    () => {
      const element = document.querySelector('.{target-class}');
      const styles = window.getComputedStyle(element);
      return {
        background: styles.backgroundColor,
        color: styles.color,
        fontSize: styles.fontSize,
        fontWeight: styles.fontWeight,
        lineHeight: styles.lineHeight,
        letterSpacing: styles.letterSpacing,
        paddingTop: styles.paddingTop,
        paddingRight: styles.paddingRight,
        paddingBottom: styles.paddingBottom,
        paddingLeft: styles.paddingLeft,
        gap: styles.gap,
        width: styles.width,
        height: styles.height,
        borderRadius: styles.borderRadius,
        borderWidth: styles.borderWidth,
        opacity: styles.opacity
      };
    }
```

### Step 5: 項目別比較

各項目について差異を計算:

```javascript
// 色比較（HEX/RGBA完全一致）
function compareColor(figma, impl) {
  const figmaRgba = parseColor(figma);
  const implRgba = parseColor(impl);
  return figmaRgba.r === implRgba.r &&
         figmaRgba.g === implRgba.g &&
         figmaRgba.b === implRgba.b &&
         Math.abs(figmaRgba.a - implRgba.a) < 0.01;
}

// 数値比較（許容差あり）
function compareValue(figma, impl, threshold = 1) {
  const figmaNum = parseFloat(figma);
  const implNum = parseFloat(impl);
  return Math.abs(figmaNum - implNum) <= threshold;
}
```

### Step 6: 差異レポート生成

## Output Format

### 比較表形式（Markdown）

```markdown
# Figma Design Diff Report

## Summary

| 項目 | 値 |
|------|-----|
| Figma URL | {fileKey}/{nodeId} |
| 実装URL | {url} |
| ブラウザ幅 | {width}px |
| 検証項目数 | {total_items} |
| 合格 | {passed} |
| 不合格 | {failed} |
| 合格率 | {pass_rate}% |

## Detailed Comparison

### 色 (Colors)

| 項目 | Figma値 | 実装値 | 差異 | 判定 |
|------|---------|--------|------|------|
| background | rgba(255,255,255,0.6) | rgba(255,255,255,0.6) | - | ✅ PASS |
| text color | #333333 | rgb(51,51,51) | - | ✅ PASS |
| border | #E0E0E0 | rgb(220,220,220) | RGB -4 | ❌ FAIL |

### フォント (Typography)

| 項目 | Figma値 | 実装値 | 差異 | 判定 |
|------|---------|--------|------|------|
| font-size | 16px | 16px | 0px | ✅ PASS |
| font-weight | 400 | 400 | - | ✅ PASS |
| line-height | 1.75 | 1.75 | 0 | ✅ PASS |
| letter-spacing | 0.05em | 0.05em | 0 | ✅ PASS |

### スペーシング (Spacing)

| 項目 | Figma値 | 実装値 | 差異 | 判定 |
|------|---------|--------|------|------|
| padding-top | 24px | 24px | 0px | ✅ PASS |
| padding-right | 32px | 30px | 2px | ❌ FAIL |
| gap | 24px | 24px | 0px | ✅ PASS |

### サイズ (Sizes)

| 項目 | Figma値 | 実装値 | 差異 | 判定 |
|------|---------|--------|------|------|
| width | 1200px | 1200px | 0px | ✅ PASS |
| height | auto | auto | - | ✅ PASS |

### ボーダー・角丸 (Borders)

| 項目 | Figma値 | 実装値 | 差異 | 判定 |
|------|---------|--------|------|------|
| border-radius | 8px | 8px | 0px | ✅ PASS |
| border-width | 1px | 1px | 0px | ✅ PASS |

## Issues Found (2)

### Issue #1: border color mismatch
- **項目**: border-color
- **Figma**: #E0E0E0 (rgb(224,224,224))
- **実装**: rgb(220,220,220)
- **差異**: RGB各 -4
- **推奨修正**: `border-color: #E0E0E0;`

### Issue #2: padding-right mismatch
- **項目**: padding-right
- **Figma**: 32px
- **実装**: 30px (rv(30))
- **差異**: 2px
- **推奨修正**: `padding-right: rv(32);`

## Recommended Fixes

```scss
// src/scss/layout/_header.scss

// Issue #1: border color
.l-header {
  // Before:
  border-color: rgb(220,220,220);

  // After:
  border-color: #E0E0E0;
}

// Issue #2: padding-right
.l-header__container {
  // Before:
  padding: rv(24) rv(30);

  // After:
  padding: rv(24) rv(32);
}
```

## Visual Diff

差分画像: `.claude/visual-diffs/diff-{timestamp}/diff.png`
（差分ピクセルはマゼンタでハイライト）

## Next Steps

- 差異が0件の場合: `✅ Design diff check passed! Run /review for production review`
- 差異がある場合: `上記の修正を適用後、再度 /figma-design-diff-checker を実行してください`
```

## Output Directory

検証結果は `.claude/visual-diffs/` に保存:

```
.claude/visual-diffs/
├── diff-YYYYMMDD-HHMMSS/
│   ├── figma.png           # Figmaスクリーンショット
│   ├── implementation.png  # 実装スクリーンショット
│   ├── diff.png            # 差分画像
│   ├── report.md           # 詳細レポート
│   └── context.json        # 抽出した値のJSON
```

## Integration with /review

production-reviewer から呼び出し可能:

```
/review コマンド実行時:
1. Figma URL が指定されている場合
2. /figma-design-diff-checker を自動実行
3. 差異があれば Issues に追加
4. 差異がなければ「Figmaデザイン検証: ✅」
```

## Integration Workflow

```bash
# 実装後のフルワークフロー
/figma-implement                    # Figmaから実装
/figma-design-diff-checker          # 視覚差分 + 値検証
/fix auto                           # 自動修正可能な問題を修正
/review                             # 本番レビュー
```

## 関連ファイル

- `.claude/rules/figma-workflow.md` - Figmaワークフロールール（RULE-001〜003）
- `.claude/skills/figma-implement/SKILL.md` - Figma実装スキル
- `.claude/skills/figma-implementation-verifier/SKILL.md` - コード値検証スキル
- `.claude/catalogs/component-catalog.yaml` - コンポーネントカタログ

---

**Instructions for Claude:**

Based on `$ARGUMENTS`, execute visual diff verification:

1. **Parse Arguments**
   - Extract `--figma` URL → parse fileKey and nodeId
   - Extract `--url` → implementation page URL
   - Extract optional `--section`, `--width`, `--height`, `--strict`, `--responsive`
   - If arguments missing, ask user interactively

2. **URL Parsing for Figma**
   ```
   https://figma.com/design/{fileKey}/{fileName}?node-id={nodeId}
   → fileKey: {fileKey}
   → nodeId: {nodeId} (replace - with :)
   ```

3. **Execute Verification Steps**

   a. **Get Figma Screenshot**
   ```
   mcp__figma__get_screenshot
     fileKey: {fileKey}
     nodeId: {nodeId}
   ```
   → Save to `.claude/visual-diffs/diff-{timestamp}/figma.png`

   b. **Get Design Context (キャッシュ優先)**

   **Check cache first:**
   ```bash
   ls .claude/cache/figma/{page-name}/section-*.json
   ```

   **If cache exists (24時間以内):**
   ```
   Read tool: .claude/cache/figma/{page-name}/section-{n}.json
   ```
   Use cached data → skip API call

   **If no cache (緊急時のみ):**
   ```
   mcp__figma__get_design_context
     fileKey: {fileKey}
     nodeId: {nodeId}
     clientLanguages: "php,scss,javascript"
     clientFrameworks: "wordpress"
   ```
   → Save to cache: `.claude/cache/figma/{page-name}/section-{n}.json`

   c. **Extract Figma Values**

   From response, extract all style values into structured format:
   - Colors: background, text, border (convert to HEX and RGBA)
   - Typography: font-size, font-weight, line-height, letter-spacing
   - Spacing: padding (all sides), margin, gap
   - Sizes: width, height
   - Borders: border-radius, border-width
   - Effects: opacity, box-shadow

   d. **Setup Playwright**
   ```
   mcp__playwright__browser_resize
     width: {width or 1440}
     height: {height or 900}
   ```

   e. **Navigate to Implementation**
   ```
   mcp__playwright__browser_navigate
     url: {implementation URL}
   ```

   f. **Extract Implementation Values**
   ```
   mcp__playwright__browser_evaluate
     function: // JavaScript to get computed styles
   ```

   g. **Take Implementation Screenshot**
   ```
   mcp__playwright__browser_take_screenshot
     type: png
     filename: ".claude/visual-diffs/diff-{timestamp}/implementation.png"
   ```

4. **Compare Values Item by Item**

   For each property category:

   **Colors:**
   - Parse both HEX (#RRGGBB) and RGBA (rgba(r,g,b,a))
   - Convert to common format for comparison
   - Exact match required (no threshold)

   **Numeric Values (font-size, padding, margin, gap, width, height):**
   - Parse values removing 'px' suffix
   - Apply threshold: default 1px, strict 0px, lenient 2px
   - Calculate absolute difference

   **Border Radius:**
   - Parse values (may be shorthand: "8px" or "8px 4px 8px 4px")
   - Compare each corner value
   - Apply threshold: 1px

   **Opacity:**
   - Parse as float (0-1)
   - Apply threshold: 0.01

5. **Generate Visual Diff Image**

   Use node scripts/visual-diff.js if available:
   ```bash
   node scripts/visual-diff.js \
     .claude/visual-diffs/diff-{timestamp}/figma.png \
     .claude/visual-diffs/diff-{timestamp}/implementation.png \
     --preset default \
     --output .claude/visual-diffs/diff-{timestamp}/diff.png
   ```

6. **Generate Detailed Report**

   Create markdown report with:
   - Summary statistics (total, passed, failed, pass rate)
   - Detailed comparison tables by category
   - Each issue with Figma value, implementation value, difference
   - Specific file:line references for fixes
   - SCSS code snippets for recommended fixes

7. **Save Results**

   ```bash
   mkdir -p .claude/visual-diffs/diff-{timestamp}/
   # Save: figma.png, implementation.png, diff.png, report.md, context.json
   ```

8. **Display Results**

   - Show summary: "X/Y items passed (Z%)"
   - If all passed: "✅ Figmaデザインとの差異なし！/review で本番レビューを実行してください"
   - If issues found:
     - List each issue with category, values, and difference
     - Show recommended fixes with code
     - Suggest: "修正後、再度 /figma-design-diff-checker を実行してください"

**Value Conversion Rules:**

```
Figma → CSS Conversion:
- fills[0].color {r,g,b,a} → rgba(r*255, g*255, b*255, a)
- fontSize → font-size (px)
- fontWeight → font-weight (number)
- lineHeight (auto/px/%) → line-height (unitless/px)
- letterSpacing → letter-spacing (em)
- paddingTop/Right/Bottom/Left → padding shorthand
- itemSpacing → gap
- cornerRadius → border-radius

SCSS → px Conversion:
- rv(x) → x px
- svw(x) → x/375*100 vw
- pvw(x) → x/1440*100 vw
```

**Error Handling:**

- Figma API失敗: "Figma APIエラー。URLを確認してください。"
- Playwright起動失敗: "ブラウザを起動できませんでした。"
- 要素が見つからない: "対象要素が見つかりません: {selector}"
- 値の解析失敗: "値を解析できませんでした: {value}"

**Output Language:** Japanese
