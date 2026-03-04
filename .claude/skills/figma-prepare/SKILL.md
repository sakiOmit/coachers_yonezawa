---
name: figma-prepare
description: "Pre-process Figma design structure (analyze, rename, group, auto-layout) before implementation. Trigger: 'prepare', '整理', 'cleanup', 'リネーム', 'structure'."
argument-hint: "{url} [--phase 1-4] [--section {name}] [--dry-run] [--apply]"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
  - AskUserQuestion
  - mcp__figma__get_metadata
  - mcp__figma__get_screenshot
  - mcp__plugin_figma_figma__get_metadata
  - mcp__plugin_figma_figma__get_screenshot
  - mcp__figma-dev-mode-mcp-server__get_metadata
  - mcp__figma-dev-mode-mcp-server__get_screenshot
  - mcp__chrome-devtools__evaluate_script
  - mcp__chrome-devtools__take_screenshot
model: opus
context: fork
agent: general-purpose
---

# Figma Prepare

## Dynamic Context

```
Chrome DevTools MCP status:
!`grep -q 'chrome-devtools' .mcp.json 2>/dev/null && echo "registered" || echo "not registered"`

Existing prepare reports:
!`ls .claude/cache/figma/prepare-report*.yaml 2>/dev/null || echo "(none)"`

Figma cache:
!`ls .claude/cache/figma/ 2>/dev/null | head -5 || echo "(empty)"`
```

## Overview

Figmaデザインファイルの構造品質を分析し、レイヤー名整理・グループ化・Auto Layout適用を自動化するスキル。
`/figma-analyze` の前段として使用し、実装効率と再現精度を向上させる。

### Key Features

- **Phase 1**: 構造品質スコア（100点満点）で問題箇所を定量化（読み取り専用、リスクゼロ）
- **Phase 2**: 未命名レイヤーのセマンティックリネーム（Chrome DevTools MCP経由）
- **Phase 3**: 近接要素のグループ化・Frame化
- **Phase 4**: Auto Layout設定の自動推論・適用

### MVP

Phase 1 + 2 を先に完成・検証。Phase 3, 4 は2-3案件で検証後に本格利用。

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | なし（起点、またはクライアントからのデザイン受領後） |
| **後工程** | `/figma-analyze` → `/figma-implement` |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | なし |

```
/figma-prepare → /figma-analyze → /figma-implement → /astro-to-wordpress → /review
```

## Usage

```
/figma-prepare {url} [options]

Options:
  --phase {1-4}    Execute up to this phase (default: 1)
  --section {name} Target specific section only
  --dry-run        Generate plan without applying (default for Phase 2-4)
  --apply          Apply changes via Chrome DevTools MCP (Phase 2-4)
```

### Examples

```bash
# Phase 1 only: Structure analysis (safe, read-only)
/figma-prepare https://figma.com/design/abc/t?node-id=0-1

# Phase 1 + 2: Analyze + generate rename map (dry-run)
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 2

# Phase 1 + 2: Analyze + apply renames
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 2 --apply

# All phases with apply
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 4 --apply

# Target specific section
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --section hero --phase 2
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| url | Yes | Figma URL |
| --phase | No | Max phase to execute (1-4, default: 1) |
| --section | No | Target specific section by name |
| --dry-run | No | Plan only, no changes (default for Phase 2-4) |
| --apply | No | Apply changes to Figma (requires Chrome DevTools MCP) |

## Explicit Restrictions

### 禁止事項（厳守）

| 禁止項目 | 理由 | 代替手段 |
|---------|------|---------|
| メインブランチでの Phase 2-4 実行 | 復元不能のリスク | Figma ブランチ上でのみ実行 |
| レイヤーの削除 | デザイン情報の損失 | リネームまたはグループ化のみ |
| ビジュアルプロパティの変更 | デザイン崩れ | 構造変更のみ |
| コンポーネント Instance の detach | コンポーネント関係の破壊 | Instance はスキップ |
| 非表示レイヤーの操作 | 意図的な非表示の可能性 | visible: false はスキップ |
| `get_screenshot` を実装データ源として使用 | 構造データなし | `get_metadata` を使用 |

## Processing Flow

### Argument Parsing

```
入力: $ARGUMENTS
パース:
  - URL: Figma URL から fileKey と nodeId を抽出
  - --phase: 実行フェーズ上限 (1-4, default: 1)
  - --section: 対象セクション名 (optional)
  - --dry-run / --apply: 実行モード (default: dry-run)
```

### Flow Diagram

```
Step 0: URL解析 + 環境チェック
        │
        ▼
Phase 1: 構造分析レポート（Figma MCP、読み取り専用）
        │ → prepare-report.yaml 出力 + コンソール品質スコア表示
        │
        ├─ [--phase 1] → 終了 + 次ステップ提案
        │
        ▼ [--phase >= 2]
Gate 1: ブランチ確認 [ユーザーがFigmaブランチ上であることを確認]
        │
        ▼
Phase 2: セマンティックリネーム
        │ → dry-run: rename-map.yaml / --apply: evaluate_script
        │
        ├─ [--phase 2] → 終了
        │
        ▼ [--phase >= 3]
Gate 2: リネーム結果をFigmaで確認
        │
        ▼
Phase 3: グループ化
        │ → dry-run: grouping-plan.yaml / --apply: evaluate_script
        │
        ├─ [--phase 3] → 終了
        │
        ▼ [--phase >= 4]
Gate 3: グループ化結果をFigmaで確認
        │
        ▼
Phase 4: Auto Layout適用
        │ → dry-run: autolayout-plan.yaml / --apply: evaluate_script
        │
        ▼
Summary: prepare-report.yaml 更新 + 次コマンド提案
```

## Step 0: URL解析 + 環境チェック

### 0-1. URL パース

```
Input:  https://figma.com/design/{fileKey}/{fileName}?node-id={int1}-{int2}
Output: fileKey = "{fileKey}", nodeId = "{int1}:{int2}"

Branch URL:
  https://figma.com/design/{fileKey}/branch/{branchKey}/{fileName}
  → fileKey = "{branchKey}"
```

### 0-2. 環境チェック

```
Phase 1: Figma MCP のみ必要（常に利用可能）
Phase 2+: Chrome DevTools MCP が必要
  → .mcp.json に "chrome-devtools" が存在するか確認
  → 未登録の場合: Phase 1 のみ実行 + セットアップ案内表示
```

### 0-3. キャッシュ確認

```bash
ls -la .claude/cache/figma/
```

## Phase 1: 構造分析レポート

**詳細**: → [references/phase-details.md](references/phase-details.md) の「Phase 1」セクション

### 1-1. メタデータ取得

```
mcp__figma__get_metadata (または figma-dev-mode-mcp-server)
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
```

### 1-2. メタデータ保存

```bash
# 一時ファイルに保存
Write .claude/cache/figma/prepare-metadata-{nodeId}.json
```

### 1-3. 品質スコア計算

```bash
bash .claude/skills/figma-prepare/scripts/analyze-structure.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json
```

### 1-4. レポート生成

`.claude/cache/figma/prepare-report.yaml` に出力。

### 1-5. コンソールサマリー

```
╔══════════════════════════════════════════════╗
║         Figma Structure Quality Report       ║
╠══════════════════════════════════════════════╣

Score: {score} / 100  [Grade: {grade}]

┌──────────────────────────────────────────────┐
│ Metrics                                       │
├───────────────────────────┬──────────────────┤
│ Total Nodes               │ {total}          │
│ Unnamed Nodes             │ {unnamed} ({%})  │
│ Flat Sections (>15 child) │ {flat}           │
│ Grouping Candidates       │ {ungrouped}      │
│ Deep Nesting (>6)         │ {deep}           │
│ No Auto Layout Frames     │ {no_al} / {fr}   │
└───────────────────────────┴──────────────────┘

Recommendation: {recommendation}

Next steps:
  /figma-prepare {url} --phase 2           # Rename (dry-run)
  /figma-prepare {url} --phase 2 --apply   # Rename + apply
  /figma-analyze {url}                     # Skip to analysis
```

## Phase 2: セマンティックリネーム

**詳細**: → [references/phase-details.md](references/phase-details.md) の「Phase 2」セクション
**API パターン**: → [references/figma-plugin-api.md](references/figma-plugin-api.md)

### 2-0. ブランチ確認（ヒューマンゲート）

AskUserQuestion で以下を確認:
- "Figmaブランチ上で作業していますか？Phase 2 はレイヤー名を変更します。"
- 選択肢: "はい、ブランチ上です" / "ブランチを作成してから戻ります"

### 2-1. リネームマップ生成

```bash
bash .claude/skills/figma-prepare/scripts/generate-rename-map.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/rename-map.yaml
```

### 2-2. dry-run 出力

rename-map.yaml の内容をサマリー表示:

```
Rename Plan: {total} layers to rename

Sample (first 10):
  "Rectangle 1"  →  "bg-hero"
  "Frame 23"     →  "card-feature-0"
  "Text 5"       →  "heading-about-us"
  ...

Full map: .claude/cache/figma/rename-map.yaml
```

### 2-3. --apply 実行

```
1. Chrome DevTools MCP 接続確認
   evaluate_script: typeof figma === 'object'

2. nodeId 存在チェック（バッチ）
   evaluate_script: 全 nodeId の存在確認

3. バッチ実行（50件/回）
   evaluate_script: リネーム実行スクリプト
   → 結果: { renamed: N, errors: [...] }

4. 結果サマリー表示
```

### 2-4. ヒューマンゲート

"Figmaでリネーム結果を確認してください。問題があればCtrl+Zで復元できます。"

## Phase 3: グループ化

**詳細**: → [references/phase-details.md](references/phase-details.md) の「Phase 3」セクション

### 3-1. グルーピング候補検出

```bash
bash .claude/skills/figma-prepare/scripts/detect-grouping-candidates.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/grouping-plan.yaml
```

### 3-2. dry-run / --apply

dry-run: grouping-plan.yaml を表示
--apply: evaluate_script で Frame 作成 + 子要素移動

## Phase 4: Auto Layout 適用

**詳細**: → [references/phase-details.md](references/phase-details.md) の「Phase 4」セクション

### 4-1. Auto Layout 推論

```bash
bash .claude/skills/figma-prepare/scripts/infer-autolayout.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/autolayout-plan.yaml
```

### 4-2. dry-run / --apply

dry-run: autolayout-plan.yaml を表示
--apply: evaluate_script で Auto Layout 適用

## Summary

全フェーズ完了後:

1. `prepare-report.yaml` を更新（実行済みフェーズを記録）
2. 次コマンドを提案:

```
Preparation complete!

Executed phases: 1, 2
Quality score: 65 → 82 (improved)

Next steps:
  /figma-analyze {url}    # Proceed to analysis
```

## Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Invalid Figma URL | Regex parse failure | URL形式を表示 |
| get_metadata failure | MCP exception | 3回リトライ → エラー表示 |
| Chrome DevTools MCP 未登録 | .mcp.json チェック | Phase 1のみ実行 + セットアップ案内 |
| `figma` グローバル未初期化 | `typeof figma !== 'object'` | プラグイン開閉を案内 |
| Node ID not found | evaluate_script 結果 | 個別スキップ + 警告 |
| バッチタイムアウト | evaluate_script タイムアウト | バッチサイズ縮小して再試行 |
| メインブランチでの実行 | ユーザー回答 | Phase 2+ を中止 |

## Scripts

| スクリプト | 目的 | 入力 | 出力 |
|-----------|------|------|------|
| `scripts/analyze-structure.sh` | 構造品質分析 | metadata JSON | JSON (score, grade, metrics) |
| `scripts/generate-rename-map.sh` | リネームマップ生成 | metadata JSON | JSON/YAML (rename map) |
| `scripts/detect-grouping-candidates.sh` | グルーピング候補検出 | metadata JSON | JSON/YAML (grouping plan) |
| `scripts/infer-autolayout.sh` | Auto Layout推論 | metadata JSON | JSON/YAML (autolayout plan) |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/figma-prepare.md` | 命名規約・閾値・品質スコア計算式 |
| `.claude/cache/figma/prepare-report.yaml` | 分析レポート出力先 |
| `.claude/cache/figma/rename-map.yaml` | Phase 2 リネームマップ |
| `.claude/cache/figma/grouping-plan.yaml` | Phase 3 グルーピング計画 |
| `.claude/cache/figma/autolayout-plan.yaml` | Phase 4 AutoLayout計画 |
| `references/chrome-devtools-setup.md` | Chrome DevTools MCP セットアップ |
| `references/figma-plugin-api.md` | Figma Plugin API パターン集 |
| `references/phase-details.md` | 各フェーズ詳細ロジック |
| `.claude/skills/figma-analyze/SKILL.md` | 後続スキル |

---

**Version**: 1.0.0
**Created**: 2026-03-04
