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

# Phase 1 + 2 + 3: Analyze + grouping + rename (dry-run)
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 3

# Phase 1 + 2 + 3: Analyze + grouping + rename + apply
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 3 --apply

# All phases with apply
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --phase 4 --apply

# Phase 1 + 1.5: Analyze + enrich metadata (fills, layoutMode, characters)
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --enrich

# Target specific section
/figma-prepare https://figma.com/design/abc/t?node-id=0-1 --section hero --phase 2
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| url | Yes | Figma URL |
| --phase | No | Max phase to execute (1-4, default: 1) |
| --section | No | Target specific section by name |
| --enrich | No | Enrich metadata with fills, layoutMode, characters via get_design_context (Phase 1.5) |
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

### Argument Parsing (CRITICAL — 必ず最初に実行)

**$ARGUMENTS にはユーザーが渡した引数が含まれている。URL は必ず存在する。**
**「引数がない」「URLが提供されていない」と判断してはならない。$ARGUMENTS を必ずパースせよ。**

```
Step 1: $ARGUMENTS から Figma URL を正規表現で抽出する
  Pattern: https?://[^\s]*(figma\.com|figma\.design)[^\s]*
  ※ URL が見つからない場合のみユーザーに確認する

Step 2: URL から fileKey と nodeId を抽出する
  URL format: https://figma.com/design/{fileKey}/{fileName}?node-id={int1}-{int2}
  fileKey = URL path の 3番目セグメント
  nodeId = node-id パラメータの "-" を ":" に置換 (例: 2-5364 → 2:5364)
  ※ &m=dev 等の追加パラメータは無視する

Step 3: フラグを抽出する
  --phase {n}: 実行フェーズ上限 (1-4, default: 1)
  --section {name}: 対象セクション名 (optional)
  --enrich: メタデータ補完 (optional)
  --dry-run: 計画のみ (Phase 2-4 デフォルト)
  --apply: 変更を適用 (optional)
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
        │ → Stage C: generate-nested-grouping-context.sh + Haiku推論（ネストレベル）
        │ → 結果統合: compare-grouping.sh（Stage A/C 比較 → 採用判定）
        │ → dry-run: final-grouping-plan.yaml + sectioning-plan.yaml / --apply: evaluate_script
        │
        ├─ [--phase 2] → 終了
        │
        ▼ [--phase >= 3]
Gate: グルーピング結果をFigmaで確認
        │
        ▼
Phase 3: グルーピング適用 + セマンティックリネーム
        │ → dry-run: rename-map.yaml 出力
        │ → --apply:
        │     3-A. clone-artboard.js → 複製アートボード作成
        │     3-B. ID マッピングテーブル生成
        │     3-C. ★ Phase 2 グルーピングをクローンに適用（必須）
        │          sectioning-plan → apply-grouping.js（レベルごと）
        │          grouping-plan → apply-grouping.js（ネストレベル）
        │          verify-grouping.js → 構造検証
        │     3-D. リネームマップを複製 ID に変換
        │     3-E. apply-renames.js → バッチリネーム実行
        │     3-F. verify-structure.js → 構造 diff 検証
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
mcp__figma-dev-mode-mcp-server__get_metadata
  nodeId: "{nodeId}"
```

MCP レスポンスは XML 形式で返る（`<frame id="..." name="..." ...>`）。
レスポンスが大きい場合、ファイルに自動保存される。

### 1-2. メタデータ保存・変換

MCP レスポンス（XML/JSON いずれか）をそのままファイルに保存する。
`analyze-structure.sh` が XML/MCP wrapper/JSON を自動検出して変換するため、手動変換は不要。

```bash
# MCP レスポンスをそのまま保存（XML でも JSON でも可）
Write .claude/cache/figma/prepare-metadata-{nodeId}.json
```

**手動変換が必要な場合のみ:**
```bash
bash .claude/skills/figma-prepare/scripts/convert-metadata.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/prepare-metadata-{nodeId}.json
```

### 1-3. 品質スコア計算

```bash
# XML/MCP wrapper/JSON を自動検出（format-agnostic）
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

Phase 2 は3段階構成:
- **Stage A**: 既存ヒューリスティック（ネストレベルのグルーピング検出）
- **Stage B**: Claude セクショニング（トップレベル children をセクション単位に分割）
- **Stage C**: Claude ネストレベル推論（Haiku でセクション内部をグルーピング）

```
Phase 2: グループ化 + セクショニング
├── 2-1. Stage A: ヒューリスティック（9手法: proximity + pattern + spacing + semantic + zone + tuple + consecutive + heading-content + highlight）
├── 2-2. Stage B: Claude セクショニング
│   ├── 2-2a. prepare-sectioning-context.sh でコンテキスト生成（gap_analysis + background_candidates）
│   ├── 2-2b. get_screenshot でスクリーンショット取得
│   ├── 2-2c. プロンプトテンプレート + コンテキストで Claude 推論
│   └── 2-2d. sectioning-plan.yaml 保存
├── 2-3. Stage C: Claude ネストレベル推論（Haiku）
│   ├── 2-3a. generate-nested-grouping-context.sh でコンテキスト生成
│   ├── 2-3b. 各セクションで Haiku 推論
│   ├── 2-3c. 結果 YAML パース・検証
│   └── 2-3d. nested-grouping-plan.yaml 保存
├── 2-4. 結果統合（Stage A + Stage C 比較 → 採用判定）
│   ├── Stage C カバレッジ >= 80% → Stage C 結果を採用
│   └── Stage C カバレッジ < 80% → Stage A にフォールバック
└── 2-5. dry-run / --apply
```

### 2-1. Stage A: ヒューリスティック（グルーピング候補検出）

```bash
bash .claude/skills/figma-prepare/scripts/detect-grouping-candidates.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/grouping-plan.yaml
```

9手法（proximity + pattern + spacing + semantic + zone + tuple + consecutive + heading-content + highlight）によるネストレベルのグルーピングを行う。トップレベルのセクション境界推論は Stage B（Claude 推論）に委ねる。

### 2-2. Stage B: Claude セクショニング

トップレベル children をセクション単位に分割する。bash スクリプトは Claude を呼ばず、SKILL 実行レベルで推論する。

#### 2-2a. セクショニングコンテキスト生成

```bash
bash .claude/skills/figma-prepare/scripts/prepare-sectioning-context.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/sectioning-context.json \
  [--enriched-table]
```

トップレベル children のサマリー（Y座標昇順、ヒューリスティックヒント付き）を JSON 出力。

`--enriched-table` 指定時は、`generate_enriched_table()` によるリッチ形式テーブル（X座標、Leaf判定、ChildTypes、Flags）を `enriched_children_table` キーに追加出力する（Issue 194）。

#### 2-2b. スクリーンショット取得

```
mcp__plugin_figma_figma__get_screenshot
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
```

スクリーンショット取得失敗時は Stage B をスキップし、Stage A のみで進行。
その場合、以下の警告をユーザーに表示すること:

```
⚠️ Stage B (Claude sectioning) をスキップしました。
   原因: スクリーンショットの取得に失敗
   影響: トップレベルのセクション分割は行われません。
         Stage A（9手法: proximity + pattern + spacing + semantic + zone + tuple + consecutive + heading-content + highlight）によるネストレベルのグルーピングのみ適用されます。
   推奨: Figma上で手動でセクショニングを行うか、スクリーンショット取得の問題を解決して再実行してください。
```

#### 2-2c. Claude 推論

プロンプトテンプレート（`references/sectioning-prompt-template.md`）にコンテキスト JSON とスクリーンショットを組み合わせて Claude に送信。ヒューリスティックヒントでアンカリングし、YAML 形式の出力を制約。

#### 2-2d. セクショニング計画保存

```
.claude/cache/figma/sectioning-plan.yaml
```

### 2-3. Stage C: Claude ネストレベル推論（Haiku）

Stage B で分割されたセクション内部の children に対して、Haiku でグルーピングを推論する。
Stage A（ヒューリスティック）と対称的に動作し、ネストレベルのパターン認識を Claude に委ねる。

#### 2-3a. ネストレベルコンテキスト生成

```bash
bash .claude/skills/figma-prepare/scripts/generate-nested-grouping-context.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  .claude/cache/figma/sectioning-plan.yaml \
  --output .claude/cache/figma/nested-context.json
```

sectioning-plan.yaml の各セクションに対して、エンリッチドテーブル（`generate_enriched_table()`）を生成。
各セクションの children サマリー（ID, Name, Type, X, Y, W×H, Leaf?, ChildTypes, Flags, Text）を JSON 出力。

#### 2-3b. 各セクションで Haiku 推論

各セクションに対して:
1. プロンプトテンプレート（`references/nested-grouping-prompt-template.md`）にコンテキストを展開
2. Haiku に送信（テキストのみ、スクリーンショット不要）
3. YAML レスポンスを取得

**モデル**: Haiku（定型パターン認識タスク。コスト: 1セクションあたり ~$0.001-0.003）

#### 2-3c. 結果 YAML パース・検証

各セクションの Haiku レスポンスを検証:
- 全 node_ids の合計がセクションの total_children と一致すること
- 各 node_id がエンリッチドテーブル内の ID と一致すること（ID ハルシネーション検出）
- pattern フィールドが許可値（two-column, card, table, bg-content, heading-pair, decoration, list, single）であること

検証失敗時は該当セクションを Stage A にフォールバック。

#### 2-3d. ネストレベルグルーピング計画保存

```
.claude/cache/figma/nested-grouping-plan.yaml
```

#### Stage C のフォールバック動作

| 条件 | 対応 |
|------|------|
| Stage B が未実行/失敗 | Stage C をスキップ（セクション情報なし） |
| Haiku 推論失敗（個別セクション） | 該当セクションのみ Stage A にフォールバック |
| Haiku 推論失敗（全セクション） | Stage C 全体をスキップ → Stage A のみで進行 |
| YAML パース/検証失敗 | 該当セクションのみ Stage A にフォールバック |

### 2-4. 結果統合（Stage A + Stage C 比較）

Stage A（ヒューリスティック）と Stage C（Haiku 推論）はどちらもネストレベルのグルーピングを行う。
Stage B（トップレベルセクショニング）は対象レベルが異なるため、常に独立して適用する。

#### 比較判定ロジック

```bash
bash .claude/skills/figma-prepare/scripts/compare-grouping.sh \
  .claude/cache/figma/grouping-plan.yaml \
  .claude/cache/figma/nested-grouping-plan.yaml \
  --output .claude/cache/figma/final-grouping-plan.yaml
```

セクションごとに Stage C のカバレッジを計測:
- **カバレッジ** = Stage C で `single` 以外のグループに割り当てられた node 数 / 全 node 数
- カバレッジ >= 80% → **Stage C 結果を採用**（Stage A は無視）
- カバレッジ < 80% → **Stage A にフォールバック**（Stage C 結果は破棄）

Stage C が未実行の場合は Stage A をそのまま使用（従来動作と同一）。

### 2-5. dry-run / --apply

dry-run: grouping-plan.yaml（または final-grouping-plan.yaml）+ sectioning-plan.yaml を表示
--apply: `apply-grouping.js` テンプレートで evaluate_script 実行

**重要: Stage B の sectioning-plan.yaml は階層的（subsections あり）であるため、再帰的に全レベルのラッパーを作成する必要がある。**

#### 2-5a. Stage B 適用: 再帰的セクショニング（必須）

sectioning-plan.yaml の階層構造を**トップダウンで再帰的に**適用する。
各レベルで apply-grouping.js を実行し、作成されたラッパーIDを記録して次レベルの parent_id に使用する。

```
適用順序（トップダウン、外側から内側へ）:

Level 1: ルート直下のトップレベルセクション
  - l-header ラッパー（node_ids が2個以上の場合）
  - main-content ラッパー（subsections の全 node_ids をフラット収集）
  - l-footer ラッパー（node_ids が2個以上の場合）
  → apply-grouping.js 実行 → 各ラッパーの新IDを記録

Level 2: main-content 内の subsections
  - section-hero-area ラッパー（parent_id = main-content の新ID）
  - section-concept-area ラッパー（parent_id = main-content の新ID）
  - section-feature-grid ラッパー（parent_id = main-content の新ID）
  - ...（subsections を持つセクションのみ。node_ids のみのリーフは Level 1 で完了）
  → apply-grouping.js 実行 → 各ラッパーの新IDを記録

Level 3: さらにネストされた subsections（存在する場合）
  - section-concept-heading, section-concept-detail 等
  → apply-grouping.js 実行

※ 各レベル適用後に新ラッパーIDが発生するため、次レベルの parent_id は
  前レベルの apply-grouping.js 出力 wrappers[].id から取得する。
```

#### 2-5b. sectioning-plan → grouping-plan 変換ロジック

```python
def flatten_sectioning_plan(sections, parent_id, clone_mapping):
    """sectioning-plan.yaml を apply-grouping.js 用の grouping-plan に変換。
    レベルごとにグループ化して返す。"""
    levels = {}  # {depth: [grouping_entry, ...]}

    def recurse(section_list, parent, depth):
        for section in section_list:
            if 'subsections' in section:
                # コンテナセクション: subsections の全 node_ids をフラット収集
                all_ids = collect_all_leaf_ids(section['subsections'])
                # clone_mapping で変換
                clone_ids = [clone_mapping[orig] for orig in all_ids if orig in clone_mapping]
                if len(clone_ids) >= 2:
                    entry = {
                        'node_ids': clone_ids,
                        'suggested_name': section['name'],
                        'parent_id': parent
                    }
                    levels.setdefault(depth, []).append(entry)
                # subsections を次のレベルで再帰
                # ※ parent は このラッパーの新ID（適用後に判明）
                recurse(section['subsections'], section['name'], depth + 1)
            else:
                # リーフセクション: node_ids が2個以上ならラッパー作成
                clone_ids = [clone_mapping[orig] for orig in section.get('node_ids', []) if orig in clone_mapping]
                if len(clone_ids) >= 2:
                    entry = {
                        'node_ids': clone_ids,
                        'suggested_name': section['name'],
                        'parent_id': parent
                    }
                    levels.setdefault(depth, []).append(entry)

    recurse(sections, parent_id, 0)
    return levels

def collect_all_leaf_ids(subsections):
    """subsections ツリーから全リーフ node_ids をフラットに収集"""
    ids = []
    for sub in subsections:
        if 'subsections' in sub:
            ids.extend(collect_all_leaf_ids(sub['subsections']))
        else:
            ids.extend(sub.get('node_ids', []))
    return ids
```

#### 2-5c. レベル間の parent_id 再マッピング

```
Level N の apply-grouping.js 実行後:
  result.wrappers = [{ id: "61:500", name: "main-content" }, ...]

Level N+1 の grouping-plan で parent_id が "main-content"（名前参照）の場合:
  → result.wrappers から name が一致する wrapper の id を取得
  → parent_id = "61:500" に置換

※ node_ids が1個のみのセクションはラッパー不要。
  代わりにリネーム（node.name = section_name）で対応する。
```

#### 2-5d. apply-grouping.js 実行（各レベル）

```
使用手順（レベルごとに繰り返す）:
1. scripts/apply-grouping.js を読み込み
2. __GROUPING_PLAN__ を該当レベルの候補JSONに置換（node_ids, suggested_name, parent_id）
3. __BATCH_INFO__ をバッチ情報に置換（例: "1/3"）
4. evaluate_script で実行 → ラッパーFrame作成 + 子要素移動
5. 結果の wrappers[].id を記録（次レベルの parent_id に使用）
```

#### 2-5e. Stage A / Stage C 適用

結果統合（2-4）で採用されたネストレベルグルーピング候補（Stage C 採用 or Stage A フォールバック）を適用。
Stage B 適用後に parent が変わっている可能性があるため、各候補の parent_id を現在のノード親から再取得する。

```
使用手順:
1. scripts/apply-grouping.js を読み込み
2. __GROUPING_PLAN__ を最終グルーピング候補JSON（final-grouping-plan.yaml）に置換
   ※ Stage C 採用セクションは nested-grouping-plan.yaml から、フォールバックセクションは grouping-plan.yaml から
   ※ parent_id は evaluate_script で node.parent.id を動的取得して設定
3. evaluate_script で実行
```

### 2-6. --apply 後の構造 diff 検証

`--apply` 実行後、`verify-grouping.js` で**全レベルの**ラッパーFRAME・子要素移動・bbox整合性を検証する。

```
使用手順:
1. scripts/verify-grouping.js を読み込み
2. __VERIFICATION_PLAN__ を検証データJSONに置換（全レベルのラッパーを含む）:
   [
     {
       "wrapper_id": "61:467",           // Level 1: main-content ラッパー
       "expected_name": "main-content",
       "expected_child_ids": ["61:500", "61:501", "61:266", ...]  // Level 2 ラッパー + リーフ
     },
     {
       "wrapper_id": "61:500",           // Level 2: section-hero-area ラッパー
       "expected_name": "section-hero-area",
       "expected_child_ids": ["61:255", "61:256", "61:261", "61:265"]
     },
     ...
   ]
3. evaluate_script で実行 → 検証結果を取得

検証項目:
  a. ラッパーFRAMEの存在・名前一致
  b. 期待される子要素がラッパー内に存在
  c. ラッパーbbox ≈ 子要素union bbox（±2px許容）

判定:
  - matchRate >= 0.98 → 成功
  - matchRate < 0.98 → 警告 + issues 一覧表示
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

#### 3-3c. グルーピング適用（Phase 2 結果をクローンに反映 — 必須）

**Phase 2 のグルーピング計画（sectioning-plan.yaml + grouping-plan.yaml）を、クローンしたアートボードに適用する。**
**このステップを飛ばすと、フラット構造のままリネームだけが行われ、構造化が一切されない。**

```
手順:
1. sectioning-plan.yaml と grouping-plan.yaml（または final-grouping-plan.yaml）を読み込む
2. 2-5b の flatten_sectioning_plan() ロジックで、sectioning-plan をレベル別の grouping-plan に変換
   ※ node_ids を clone_mapping で変換（元ID → クローンID）
3. レベルごとにトップダウンで apply-grouping.js を実行:
   - Level 1: ルート直下（l-header, main-content, l-footer）
   - Level 2: main-content 内の subsections
   - Level N: さらにネストがあれば再帰
4. 各レベル適用後、wrappers[].id を記録して次レベルの parent_id に使用
5. Stage A / Stage C のネストレベルグルーピングも同様に適用
6. verify-grouping.js で構造 diff 検証
```

#### 3-3d. リネームマップの ID 変換

```
rename-map.yaml の各 nodeId を mapping テーブルで変換:
  元 ID (例: "1:10") → 複製 ID (例: "23:55")

変換できない ID は警告としてスキップ。
※ 3-3c でグルーピングにより新しいラッパーFrameが追加されているため、
  clone_mapping に存在しない新規IDはスキップして問題ない。
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
--apply: `apply-autolayout.js` テンプレートで evaluate_script 実行

```
使用手順:
1. scripts/apply-autolayout.js を読み込み
2. __AUTOLAYOUT_PLAN__ をレイアウトJSON配列に置換（node_id, direction, gap, padding, etc.）
3. __BATCH_INFO__ をバッチ情報に置換（例: "1/2"）
4. __MIN_CONFIDENCE__ を最低信頼度に置換（"medium" 推奨 — exact+high+medium を適用、low はスキップ）
5. evaluate_script で実行 → layoutMode/itemSpacing/padding/counterAxisAlignItems 設定
```

### 4-3. --apply 後の Auto Layout 検証

`--apply` 実行後、`verify-autolayout.js` で設定値を読み戻し、計画との整合性を検証する。

```
使用手順:
1. scripts/verify-autolayout.js を読み込み
2. __VERIFICATION_PLAN__ を検証データJSONに置換:
   [
     {
       "node_id": "23:55",
       "expected_direction": "VERTICAL",
       "expected_gap": 24,
       "expected_padding": { "top": 16, "right": 16, "bottom": 16, "left": 16 },
       "expected_primary_align": "MIN",
       "expected_counter_align": "CENTER"
     },
     ...
   ]
3. evaluate_script で実行 → 検証結果を取得

検証項目:
  a. ノードの存在確認
  b. layoutMode / layoutWrap が期待方向と一致
  c. itemSpacing（gap）が期待値と一致（±1px許容）
  d. padding 4辺が期待値と一致（±1px許容）
  e. primaryAxisAlignItems / counterAxisAlignItems が期待値と一致

判定:
  - matchRate >= 0.98 → 成功
  - matchRate < 0.98 → 警告 + issues 一覧表示
```

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
| Stage B スクリーンショット失敗 | get_screenshot MCP exception | Stage B スキップ + 警告表示 + 手動セクショニング推奨 |
| Stage C Haiku 推論失敗（個別） | Haiku API エラー or YAML パース失敗 | 該当セクションのみ Stage A にフォールバック |
| Stage C Haiku 推論失敗（全体） | 全セクションで Haiku 失敗 | Stage C スキップ → Stage A のみで進行 |
| Stage C ID 検証失敗 | node_ids 合計不一致 or ID 不在 | 該当セクションのみ Stage A にフォールバック |
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
| `scripts/prepare-sectioning-context.sh` | Stage B: セクショニングコンテキスト生成 | metadata JSON [--enriched-table] | JSON (top-level children summary + hints [+ enriched table]) |
| `scripts/generate-nested-grouping-context.sh` | Stage C: ネストレベルコンテキスト生成 | metadata JSON + sectioning-plan YAML | JSON (per-section enriched children tables) |
| `scripts/compare-grouping.sh` | Stage A/C 比較・採用判定 | grouping-plan YAML + nested-grouping-plan YAML | YAML (final-grouping-plan) |
| `scripts/infer-autolayout.sh` | Auto Layout推論 | metadata JSON | JSON/YAML (autolayout plan) |
| `scripts/start-chrome-debug.sh` | Chrome 起動 + SSH トンネル + 接続確認 | Figma URL (optional) | stdout (接続状態) |
| `scripts/clone-artboard.js` | アートボード複製 + IDマッピング | `() => { ... }` 形式、`__SOURCE_NODE_ID__` 置換 | object (clone info, mapping) |
| `scripts/apply-renames.js` | バッチリネーム実行 | `() => { ... }` 形式、`__RENAME_MAP__` / `__BATCH_INFO__` 置換 | object (renamed, errors) |
| `scripts/apply-grouping.js` | グルーピング適用 | `() => { ... }` 形式、`__GROUPING_PLAN__` / `__BATCH_INFO__` 置換 | object (applied, wrappers, errors) |
| `scripts/apply-autolayout.js` | Auto Layout 適用 | `() => { ... }` 形式、`__AUTOLAYOUT_PLAN__` / `__BATCH_INFO__` / `__MIN_CONFIDENCE__` 置換 | object (applied, skipped, errors) |
| `scripts/verify-structure.js` | リネーム diff 検証 | `() => { ... }` 形式、`__CLONE_NODE_ID__` / `__EXPECTED_NAMES__` 置換 | object (matched, mismatched, matchRate) |
| `scripts/verify-grouping.js` | グルーピング適用検証 | `() => { ... }` 形式、`__VERIFICATION_PLAN__` 置換 | object (verified, issues, matchRate) |
| `scripts/verify-autolayout.js` | Auto Layout 適用検証 | `() => { ... }` 形式、`__VERIFICATION_PLAN__` 置換 | object (verified, issues, matchRate) |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/figma-prepare.md` | 命名規約・閾値・品質スコア計算式 |
| `.claude/cache/figma/prepare-report.yaml` | 分析レポート出力先 |
| `.claude/cache/figma/grouping-plan.yaml` | Phase 2 Stage A グルーピング計画 |
| `.claude/cache/figma/sectioning-context.json` | Phase 2 Stage B コンテキスト |
| `.claude/cache/figma/sectioning-plan.yaml` | Phase 2 Stage B セクショニング計画 |
| `.claude/cache/figma/nested-context.json` | Phase 2 Stage C ネストレベルコンテキスト |
| `.claude/cache/figma/nested-grouping-plan.yaml` | Phase 2 Stage C ネストレベルグルーピング計画 |
| `.claude/cache/figma/final-grouping-plan.yaml` | Phase 2 結果統合後の最終グルーピング計画 |
| `.claude/cache/figma/rename-map.yaml` | Phase 3 リネームマップ |
| `.claude/cache/figma/autolayout-plan.yaml` | Phase 4 AutoLayout計画 |
| `references/*.md` | 参照ドキュメント（**必要時に Read で遅延読み込み**、自動読み込み不要） |
| `tests/figma-prepare/` | テスト・フィクスチャ（プロジェクトルート、スキル外） |
| `lib/figma_utils.py` | 共通ユーティリティ（座標変換・bbox・ルートノード・未命名判定） |
| `.claude/skills/figma-analyze/SKILL.md` | 後続スキル |

---

**Version**: 1.0.0
**Created**: 2026-03-04
