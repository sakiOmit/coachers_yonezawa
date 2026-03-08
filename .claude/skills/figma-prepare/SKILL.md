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
- **Phase 2**: 近接要素のグループ化・セクショニング（Stage A/B/C 3段階）
- **Phase 3**: 未命名レイヤーのセマンティックリネーム（Chrome DevTools MCP経由）
- **Phase 4**: Auto Layout設定の自動推論・適用

### MVP

Phase 1 + 2 + 3 を先に完成・検証。Phase 4 は2-3案件で検証後に本格利用。

### Adjacent Artboard 方式（--apply）

`--apply` 実行時、元のアートボードを直接変更するのではなく、**隣に複製アートボードを作成**し、そこに変更を適用する。Before/After を並べて視覚比較可能。Ctrl+Z または複製削除で即座に復元可能。

## Pipeline Position

```
/figma-prepare → /figma-analyze → /figma-implement → /astro-to-wordpress → /review
```

## Usage

```
/figma-prepare {url} [options]

Options:
  --phase {1-4}    Execute up to this phase (default: 1)
  --section {name} Target specific section only
  --enrich         Enrich metadata via get_design_context (Phase 1.5)
  --dry-run        Generate plan without applying (default for Phase 2-4)
  --apply          Apply changes via Chrome DevTools MCP (Phase 2-4)
```

### Examples

```bash
# Phase 1 only: Structure analysis (safe, read-only)
/figma-prepare https://figma.com/design/abc/t?node-id=0-1

# Phase 1 + 2: Analyze + grouping plan (dry-run)
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 2

# Phase 1 + 2 + 3: Analyze + grouping + rename + apply
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 3 --apply

# All phases with apply
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 4 --apply

# Phase 1 + 1.5: Analyze + enrich metadata
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --enrich
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| url | Yes | Figma URL |
| --phase | No | Max phase to execute (1-4, default: 1) |
| --section | No | Target specific section by name |
| --enrich | No | Enrich metadata with fills, layoutMode, characters (Phase 1.5) |
| --dry-run | No | Plan only, no changes (default for Phase 2-4) |
| --apply | No | Apply changes to Figma (requires Chrome DevTools MCP) |

## Explicit Restrictions

| 禁止項目 | 理由 | 代替手段 |
|---------|------|---------|
| 元アートボードの直接変更 | 復元不能のリスク | Adjacent Artboard 方式 |
| レイヤーの削除 | デザイン情報の損失 | リネームまたはグループ化のみ |
| ビジュアルプロパティの変更 | デザイン崩れ | 構造変更のみ |
| コンポーネント Instance の detach | コンポーネント関係の破壊 | Instance はスキップ |
| 非表示レイヤーの操作 | 意図的な非表示の可能性 | visible: false はスキップ |
| `get_screenshot` を実装データ源として使用 | 構造データなし | `get_metadata` を使用 |

## Argument Parsing (CRITICAL)

**$ARGUMENTS にはユーザーが渡した引数が含まれている。URL は必ず存在する。**
**「引数がない」「URLが提供されていない」と判断してはならない。$ARGUMENTS を必ずパースせよ。**

```
Step 1: $ARGUMENTS から Figma URL を正規表現で抽出
  Pattern: https?://[^\s]*(figma\.com|figma\.design)[^\s]*

Step 2: URL から fileKey と nodeId を抽出
  fileKey = URL path の 3番目セグメント
  nodeId = node-id パラメータの "-" を ":" に置換

Step 3: フラグを抽出
  --phase {n}, --section {name}, --enrich, --dry-run, --apply
```

## Processing Flow

```
Step 0: URL解析 + 環境チェック
        │
        ▼
Phase 1: 構造分析レポート（Figma MCP、読み取り専用）
        │ → prepare-report.yaml 出力
        │
        ├─ [--phase 1] → 終了 + 次ステップ提案
        │
        ▼ [--enrich 指定時]
Phase 1.5: メタデータ補完（オプション）
        │
        ▼ [--phase >= 2]
Phase 2: グループ化 + セクショニング
        │ → Stage A: detect-grouping-candidates.sh
        │ → Stage B: prepare-sectioning-context.sh + Claude推論
        │ → Stage C: generate-nested-grouping-context.sh + Haiku推論  ← 必須
        │ → 結果統合: compare-grouping.sh
        │
        ▼ [--phase >= 3]
Phase 3: グルーピング適用 + セマンティックリネーム
        │ → Adjacent Artboard 方式
        │
        ▼ [--phase >= 4]
Phase 4: Auto Layout適用
        │
        ▼
Summary: prepare-report.yaml 更新 + 次コマンド提案
```

**各 Phase の詳細手順**: → [references/phases-workflow.md](references/phases-workflow.md)

## Phase 2 Quick Reference

> **Stage A → Stage B → Stage C の3段階すべてが必須。Stage Cをスキップしてはならない。**

```
Phase 2 構造:
├── 2-1. Stage A: ヒューリスティック（9手法）
├── 2-2. Stage B: Claude セクショニング（トップレベル分割）
├── 2-3. Stage C: Haiku ネストレベル推論 ← 必須
│   ├── 2-3a. generate-nested-grouping-context.sh
│   ├── 2-3b. 各セクション Haiku 推論
│   ├── 2-3c. YAML パース・検証
│   ├── 2-3d. nested-grouping-plan.yaml 保存
│   ├── 2-3e. postprocess-grouping-plan.sh（divider 吸収）
│   └── 2-3f. run-stage-c-depth-recursion.py（depth 再帰）
├── 2-4. 結果統合（coverage >= 80% → Stage C、< 80% → Stage A）
└── 2-5. dry-run / --apply
```

**前提条件チェック** (--apply 前):

| ファイル | 生成元 | 必須 |
|---------|--------|------|
| `grouping-plan.yaml` | Stage A (2-1) | Yes |
| `sectioning-plan.yaml` | Stage B (2-2) | Yes |
| `nested-grouping-plan.yaml` | Stage C (2-3) | **Yes** |

**適用の詳細手順**: → [references/apply-workflow.md](references/apply-workflow.md)

## Phase 3 Quick Reference

1. `generate-rename-map.sh` → rename-map.yaml
2. dry-run: サマリー表示
3. --apply: clone artboard → グルーピング適用 → ID変換 → バッチリネーム → 検証

**適用の詳細手順**: → [references/apply-workflow.md](references/apply-workflow.md)

## Phase 4 Quick Reference

1. `infer-autolayout.sh` → autolayout-plan.yaml
2. dry-run: 計画表示
3. --apply: evaluate_script → 検証

**適用の詳細手順**: → [references/apply-workflow.md](references/apply-workflow.md)

## Error Handling

→ [references/error-handling.md](references/error-handling.md)

## Scripts

| スクリプト | 目的 | 入力 | 出力 |
|-----------|------|------|------|
| `analyze-structure.sh` | 構造品質分析 | metadata JSON | JSON (score, grade, metrics) |
| `enrich-metadata.sh` | メタデータ補完 | metadata + enrichment JSON | enriched metadata JSON |
| `generate-rename-map.sh` | リネームマップ生成 | metadata JSON | JSON/YAML (rename map) |
| `detect-grouping-candidates.sh` | Stage A: グルーピング検出 | metadata JSON | YAML (grouping plan) |
| `prepare-sectioning-context.sh` | Stage B: セクショニングコンテキスト | metadata JSON | JSON (summary + hints) |
| `generate-nested-grouping-context.sh` | Stage C: ネストコンテキスト | metadata + sectioning YAML | JSON (per-section tables) |
| `compare-grouping.sh` | Stage A/C 比較 | grouping + nested YAML | YAML (final plan) |
| `postprocess-grouping-plan.sh` | Divider 吸収 | nested-grouping YAML | YAML (postprocessed) |
| `run-stage-c-depth-recursion.py` | Depth 再帰 | metadata + plan YAML | YAML (with sub_groups) |
| `infer-autolayout.sh` | Auto Layout推論 | metadata JSON | YAML (autolayout plan) |
| `start-chrome-debug.sh` | Chrome 起動 + SSH | Figma URL | stdout (接続状態) |
| `convert-metadata.sh` | メタデータ変換 | metadata JSON | JSON (normalized) |
| `clone-artboard.js` | アートボード複製 | `__SOURCE_NODE_ID__` | object (clone, mapping) |
| `apply-renames.js` | バッチリネーム | `__RENAME_MAP__` | object (renamed, errors) |
| `apply-grouping.js` | グルーピング適用 | `__GROUPING_PLAN__` | object (wrappers, errors) |
| `apply-autolayout.js` | Auto Layout適用 | `__AUTOLAYOUT_PLAN__` | object (applied, errors) |
| `verify-structure.js` | リネーム検証 | `__CLONE_NODE_ID__` | object (matchRate) |
| `verify-grouping.js` | グルーピング検証 | `__VERIFICATION_PLAN__` | object (matchRate) |
| `verify-autolayout.js` | Auto Layout検証 | `__VERIFICATION_PLAN__` | object (matchRate) |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/figma-prepare.md` | 命名規約・閾値・品質スコア計算式 |
| `.claude/cache/figma/prepare-report.yaml` | 分析レポート出力先 |
| `.claude/cache/figma/grouping-plan.yaml` | Stage A グルーピング計画 |
| `.claude/cache/figma/sectioning-plan.yaml` | Stage B セクショニング計画 |
| `.claude/cache/figma/nested-grouping-plan.yaml` | Stage C ネストレベル計画 |
| `.claude/cache/figma/final-grouping-plan.yaml` | 結果統合後の最終計画 |
| `.claude/cache/figma/rename-map.yaml` | Phase 3 リネームマップ |
| `.claude/cache/figma/autolayout-plan.yaml` | Phase 4 AutoLayout計画 |
| `lib/figma_utils.py` | 共通ユーティリティ |
| `tests/figma-prepare/` | テスト・フィクスチャ |

## Satellite Documents

詳細は必要時に Read で遅延読み込みすること（自動読み込み不要）。

| Document | Content |
|----------|---------|
| [references/phases-workflow.md](references/phases-workflow.md) | 全 Phase の詳細手順（Step 0 〜 Phase 4） |
| [references/apply-workflow.md](references/apply-workflow.md) | --apply 実行の詳細（ID マッピング、検証、変換ロジック） |
| [references/error-handling.md](references/error-handling.md) | エラーシナリオ、フォールバック、リカバリー |
| [references/phase-details.md](references/phase-details.md) | Phase 出力形式、Stage C 詳細、コスト試算 |
| [references/figma-plugin-api.md](references/figma-plugin-api.md) | Figma Plugin API パターン |
| [references/sectioning-prompt-template.md](references/sectioning-prompt-template.md) | Stage B プロンプトテンプレート |
| [references/nested-grouping-prompt-template.md](references/nested-grouping-prompt-template.md) | Stage C プロンプトテンプレート |

---

**Version**: 2.0.0
**Created**: 2026-03-04
**Restructured**: 2026-03-08 (split into SKILL.md + satellite docs)
