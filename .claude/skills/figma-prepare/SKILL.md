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
- **Phase 2**: 近接要素のグループ化・セクショニング
- **Phase 3**: 未命名レイヤーのセマンティックリネーム（Chrome DevTools MCP経由）
- **Phase 4**: Auto Layout設定の自動推論・適用

### MVP

Phase 1 + 2 + 3 を先に完成・検証。Phase 4 は2-3案件で検証後に本格利用。

### Adjacent Artboard 方式（--apply）

`--apply` 実行時、元のアートボードを直接変更するのではなく、**隣に複製アートボードを作成**し、そこに変更を適用する。

- ブランチ不要（複製が独立に存在）
- Before/After を並べて視覚比較可能
- フィードバックループ（修正→再適用）が容易
- Ctrl+Z または複製削除で即座に復元可能

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

# Phase 1 + 2: Analyze + grouping plan (dry-run)
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 2

# Phase 1 + 2 + 3: Analyze + grouping + rename (dry-run)
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 3

# Phase 1 + 2 + 3: Analyze + grouping + rename + apply
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 3 --apply

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
| 元アートボードの直接変更 | 復元不能のリスク | Adjacent Artboard 方式（複製に適用） |
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
        ▼ [--phase >= 2, --enrich 指定時]
Phase 1.5: メタデータ補完（オプション）
        │ → get_design_context でセクション別に fills/layoutMode/characters 取得
        │ → enrich-metadata.sh でメタデータにマージ
        │ → enriched metadata を後続 Phase に使用
        │
        ▼ [--phase >= 2]
Phase 2: グループ化 + セクショニング
        │ → Stage A: detect-grouping-candidates.sh（ネストレベル）
        │ → Stage B: prepare-sectioning-context.sh + Claude推論（トップレベル）
        │ → dry-run: grouping-plan.yaml + sectioning-plan.yaml / --apply: evaluate_script
        │
        ├─ [--phase 2] → 終了
        │
        ▼ [--phase >= 3]
Gate: グルーピング結果をFigmaで確認
        │
        ▼
Phase 3: セマンティックリネーム
        │ → dry-run: rename-map.yaml 出力
        │ → --apply:
        │     3-A. clone-artboard.js → 複製アートボード作成
        │     3-B. ID マッピングテーブル生成
        │     3-C. リネームマップを複製 ID に変換
        │     3-D. apply-renames.js → バッチリネーム実行
        │     3-E. verify-structure.js → 構造 diff 検証
        │
        ├─ [--phase 3] → 終了
        │
        ▼ [--phase >= 4]
Gate: リネーム結果をFigmaで確認
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

Phase 2+ の自動セットアップ:
  bash .claude/skills/figma-prepare/scripts/start-chrome-debug.sh "{figma-url}"
  → Chrome 起動 + SSH トンネル + 接続確認を一括実行
  → 既に起動済みならスキップ（冪等）
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
  /figma-prepare {url} --phase 2           # Grouping (dry-run)
  /figma-prepare {url} --phase 3           # Grouping + Rename (dry-run)
  /figma-prepare {url} --phase 3 --apply   # Grouping + Rename + apply
  /figma-analyze {url}                     # Skip to analysis
```

## Phase 1.5: メタデータ補完（オプション）

`--enrich` フラグ指定時、`get_design_context` を使用してメタデータを補完する。
fills（画像判定）、layoutMode（AutoLayout実値）、characters（テキスト内容）が追加される。

### 1.5-1. セクションルート特定

Phase 1 のメタデータからセクションルート（width ~1440 のフレーム）の nodeId を抽出。

### 1.5-2. get_design_context 呼び出し

各セクションルートに対して：
```
mcp__figma__get_design_context
  fileKey: "{fileKey}"
  nodeId: "{sectionNodeId}"
```

### 1.5-3. エンリッチメントデータ抽出

レスポンスから fills, layoutMode, itemSpacing, padding*, characters を抽出し、
フラットマップ（`{ nodeId: { fills, layoutMode, ... } }`）を構築。

### 1.5-4. メタデータマージ

```bash
bash .claude/skills/figma-prepare/scripts/enrich-metadata.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  .claude/cache/figma/enrichment-{nodeId}.json \
  --output .claude/cache/figma/prepare-metadata-{nodeId}.json
```

マージ後のメタデータは Phase 2-4 で自動的に使用される。

### 1.5-5. 補完の効果

| Phase | 補完なし | 補完あり |
|-------|---------|---------|
| Phase 3 | RECTANGLE → bg-* | IMAGE fill → img-*, SOLID fill → bg-* |
| Phase 3 | GROUP → group-* (フォールバック) | 位置+構造 → header/footer |
| Phase 4 | 座標推論 (medium confidence) | layoutMode 実値 (exact confidence) |

## Phase 2: グループ化 + セクショニング

**詳細**: → [references/phase-details.md](references/phase-details.md) の「Phase 2」セクション

Phase 2 は2段階構成:
- **Stage A**: 既存ヒューリスティック（ネストレベルのグルーピング検出）
- **Stage B**: Claude セクショニング（トップレベル children をセクション単位に分割）

```
Phase 2: グループ化 + セクショニング
├── 2-1. Stage A: ヒューリスティック（proximity + pattern のみ）
├── 2-2. Stage B: Claude セクショニング
│   ├── 2-2a. prepare-sectioning-context.sh でコンテキスト生成（gap_analysis + background_candidates）
│   ├── 2-2b. get_screenshot でスクリーンショット取得
│   ├── 2-2c. プロンプトテンプレート + コンテキストで Claude 推論
│   └── 2-2d. sectioning-plan.yaml 保存
├── 2-3. 結果統合（Stage A はネストレベル、Stage B はトップレベル。それぞれ独立して適用）
└── 2-4. dry-run / --apply
```

### 2-1. Stage A: ヒューリスティック（グルーピング候補検出）

```bash
bash .claude/skills/figma-prepare/scripts/detect-grouping-candidates.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/grouping-plan.yaml
```

プロキシミティ/パターン検出のみ。ネストレベルのグルーピングを行う。セマンティック理解は Stage B（Claude 推論）に委ねる。

### 2-2. Stage B: Claude セクショニング

トップレベル children をセクション単位に分割する。bash スクリプトは Claude を呼ばず、SKILL 実行レベルで推論する。

#### 2-2a. セクショニングコンテキスト生成

```bash
bash .claude/skills/figma-prepare/scripts/prepare-sectioning-context.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/sectioning-context.json
```

トップレベル children のサマリー（Y座標昇順、ヒューリスティックヒント付き）を JSON 出力。

#### 2-2b. スクリーンショット取得

```
mcp__plugin_figma_figma__get_screenshot
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
```

スクリーンショット取得失敗時は Stage B をスキップし、Stage A のみで進行。

#### 2-2c. Claude 推論

プロンプトテンプレート（`references/sectioning-prompt-template.md`）にコンテキスト JSON とスクリーンショットを組み合わせて Claude に送信。ヒューリスティックヒントでアンカリングし、YAML 形式の出力を制約。

#### 2-2d. セクショニング計画保存

```
.claude/cache/figma/sectioning-plan.yaml
```

### 2-3. 結果統合

Stage A のグルーピング候補はネストレベル、Stage B はトップレベルセクショニング。それぞれ独立して適用する（対象レベルが異なるため重複しない）。

### 2-4. dry-run / --apply

dry-run: grouping-plan.yaml + sectioning-plan.yaml を表示
--apply: evaluate_script で Frame 作成 + 子要素移動

### 2-5. --apply 後の構造 diff 検証

`--apply` 実行後、verify-structure.js でクローンのツリーを読み戻し、計画との整合性を検証する。

```
1. グルーピング計画の name と実際のフレーム名を比較
   - __EXPECTED_NAMES__: { "cloneChildId": "planName", ... }（グルーピング/セクショニング計画のフレーム名）
2. 子ノードの移動先が正しいか確認
   - 新フレーム内の子ノード数が計画と一致するか
3. matchRate >= 0.98 → 成功、< 0.98 → 警告 + mismatch 一覧

パターン: references/figma-plugin-api.md「構造検証」参照
```

## Phase 3: セマンティックリネーム

**詳細**: → [references/phase-details.md](references/phase-details.md) の「Phase 3」セクション
**API パターン**: → [references/figma-plugin-api.md](references/figma-plugin-api.md)

### 3-1. リネームマップ生成

```bash
bash .claude/skills/figma-prepare/scripts/generate-rename-map.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/rename-map.yaml
```

### 3-2. dry-run 出力（デフォルト）

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

### 3-3. --apply 実行（Adjacent Artboard 方式）

`--apply` 指定時、元アートボードの複製を作成し、複製側にリネームを適用する。

#### 3-3a. Chrome DevTools MCP 接続確認

```
mcp__chrome-devtools__evaluate_script
  function: () => typeof figma
→ "object" 以外の場合: プラグイン開閉を案内して中止

セットアップ: references/chrome-devtools-setup.md 参照
```

#### 3-3b. アートボード複製

```
mcp__chrome-devtools__evaluate_script の function パラメータにインラインで渡す:
  - figma.getNodeById(sourceNodeId) でソース取得
  - source.clone() で深い複製
  - clone.x = source.x + source.width + 100 で右隣に配置
  - buildMapping() で並行DFS → IDマッピング生成

結果: { clone: { id, name }, mapping: {...}, total: N, nameMatchRate }
nameMatchRate < 0.95 の場合: 警告表示 + 続行確認

パターン: references/figma-plugin-api.md「Adjacent Artboard」参照
```

#### 3-3c. リネームマップの ID 変換

```
rename-map.yaml の各 nodeId を mapping テーブルで変換:
  元 ID (例: "1:10") → 複製 ID (例: "23:55")

変換できない ID は警告としてスキップ。
```

#### 3-3d. バッチリネーム実行

```
1. 変換済みリネームマップを 50件/バッチ に分割
2. 各バッチごとに:
   mcp__chrome-devtools__evaluate_script の function パラメータで実行:
     - renameMap オブジェクトをインライン埋め込み
     - figma.getNodeById() → node.name = newName
   結果: { renamed: N, skipped: N, errors: [...] }
3. 全バッチの結果を集計

パターン: references/figma-plugin-api.md「Phase 3: リネーム」参照
```

#### 3-3e. 構造 diff 検証

```
1. verify-structure.js でクローンのツリーを読み戻し
   - __CLONE_NODE_ID__ にクローンID、__EXPECTED_NAMES__ にリネームマップ（クローン側ID→期待名）を埋め込み
   - mcp__chrome-devtools__evaluate_script で実行

2. リネームマップの期待名と actual name を比較
   結果: { total, matched, mismatched, missing, matchRate }

3. 判定:
   - matchRate >= 0.98 → 成功
   - matchRate < 0.98 → 警告 + mismatch 一覧表示

4. 補助: スクリーンショットでビジュアル崩れがないか確認（任意）
   mcp__plugin_figma_figma__get_screenshot
     fileKey: "{fileKey}"
     nodeId: "{cloneId}"

パターン: references/figma-plugin-api.md「構造検証」参照
```

#### 3-3f. 結果サマリー

```
╔══════════════════════════════════════════════╗
║         Phase 3: Rename Applied             ║
╠══════════════════════════════════════════════╣

Method: Adjacent Artboard (clone + rename)

Clone: "{cloneName}" (ID: {cloneId})
  Position: x={x}, y={y}

Results:
  Renamed: {renamed} layers
  Skipped: {skipped} layers
  Errors:  {errorCount}

Verification:
  Structure diff: {matched}/{total} matched ({matchRate}%)
  Mismatches: {mismatchCount}
  Visual check: screenshot available (supplementary)

Original artboard: unchanged ✓

Next:
  - Figma で Before/After を並べて確認
  - 問題なければ元アートボードを削除し複製を採用
  - 修正が必要な場合は複製を削除して再実行
╚══════════════════════════════════════════════╝
```

### 3-4. ヒューマンゲート

"Figmaで Before/After を確認してください。複製アートボードが不要な場合は Ctrl+Z または手動削除で復元できます。"

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

Executed phases: 1, 2, 3
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
| clone() 失敗 | evaluate_script 結果 success=false | エラー表示 + 中止 |
| IDマッピング不整合 | nameMatchRate < 0.95 | 警告表示 + 続行確認（AskUserQuestion） |
| リネームマップ ID 変換失敗 | mapping に存在しない ID | 個別スキップ + 警告 |

## Scripts

| スクリプト | 目的 | 入力 | 出力 |
|-----------|------|------|------|
| `scripts/analyze-structure.sh` | 構造品質分析 | metadata JSON | JSON (score, grade, metrics) |
| `scripts/enrich-metadata.sh` | メタデータ補完 | metadata JSON + enrichment JSON | enriched metadata JSON |
| `scripts/generate-rename-map.sh` | リネームマップ生成 | metadata JSON | JSON/YAML (rename map) |
| `scripts/detect-grouping-candidates.sh` | Stage A: グルーピング候補検出 | metadata JSON | JSON/YAML (grouping plan) |
| `scripts/prepare-sectioning-context.sh` | Stage B: セクショニングコンテキスト生成 | metadata JSON | JSON (top-level children summary + hints) |
| `scripts/infer-autolayout.sh` | Auto Layout推論 | metadata JSON | JSON/YAML (autolayout plan) |
| `scripts/start-chrome-debug.sh` | Chrome 起動 + SSH トンネル + 接続確認 | Figma URL (optional) | stdout (接続状態) |
| `scripts/clone-artboard.js` | アートボード複製 + IDマッピング | `() => { ... }` 形式、`__SOURCE_NODE_ID__` 置換 | object (clone info, mapping) |
| `scripts/apply-renames.js` | バッチリネーム実行 | `() => { ... }` 形式、`__RENAME_MAP__` / `__BATCH_INFO__` 置換 | object (renamed, errors) |
| `scripts/verify-structure.js` | 構造 diff 検証 | `() => { ... }` 形式、`__CLONE_NODE_ID__` / `__EXPECTED_NAMES__` 置換 | object (matched, mismatched, matchRate) |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/figma-prepare.md` | 命名規約・閾値・品質スコア計算式 |
| `.claude/cache/figma/prepare-report.yaml` | 分析レポート出力先 |
| `.claude/cache/figma/grouping-plan.yaml` | Phase 2 Stage A グルーピング計画 |
| `.claude/cache/figma/sectioning-context.json` | Phase 2 Stage B コンテキスト |
| `.claude/cache/figma/sectioning-plan.yaml` | Phase 2 Stage B セクショニング計画 |
| `.claude/cache/figma/rename-map.yaml` | Phase 3 リネームマップ |
| `.claude/cache/figma/autolayout-plan.yaml` | Phase 4 AutoLayout計画 |
| `references/chrome-devtools-setup.md` | Chrome DevTools MCP セットアップ |
| `references/figma-plugin-api.md` | Figma Plugin API パターン集 |
| `references/phase-details.md` | 各フェーズ詳細ロジック |
| `references/sectioning-prompt-template.md` | Stage B Claude プロンプトテンプレート |
| `lib/figma_utils.py` | 共通ユーティリティ（座標変換・bbox・ルートノード・未命名判定） |
| `.claude/skills/figma-analyze/SKILL.md` | 後続スキル |

---

**Version**: 1.0.0
**Created**: 2026-03-04
