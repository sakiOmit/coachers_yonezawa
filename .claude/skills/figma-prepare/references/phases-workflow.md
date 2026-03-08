# Phases Workflow (Detailed)

SKILL.md の各 Phase の詳細手順。スコア計算式・閾値・リネームロジック・Auto Layout推論ロジックは `.claude/rules/figma-prepare.md` を参照。

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
Score: {score} / 100  [Grade: {grade}]

┌───────────────────────────┬──────────────────┐
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

### Phase 1 出力形式

```yaml
# .claude/cache/figma/prepare-report.yaml
meta:
  generated_at: "2026-03-04T12:00:00Z"
  figma_url: "https://figma.com/design/..."
  fileKey: "abc123"
  nodeId: "0:1"

quality:
  score: 60
  grade: "B"
  recommendation: "Phase 2 (grouping) recommended"

metrics:
  total_nodes: 245
  unnamed_nodes: 78
  unnamed_rate_pct: 31.8
  flat_sections: 2
  ungrouped_candidates: 5
  deep_nesting_count: 3
  no_autolayout_frames: 12
  total_frames: 35
  max_depth: 8
  max_section_depth: 6

score_breakdown:
  unnamed_penalty: 15.9
  flat_penalty: 10.0
  ungrouped_penalty: 5
  nesting_penalty: 9
  autolayout_penalty: 0  # unmeasurable via get_metadata — excluded from score

phases_executed: [1]
phases_recommended: [2]
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

### 1.5-5. 補完の効果

| Phase | 補完なし | 補完あり |
|-------|---------|---------|
| Phase 3 | RECTANGLE → bg-* | IMAGE fill → img-*, SOLID fill → bg-* |
| Phase 3 | GROUP → group-* (フォールバック) | 位置+構造 → header/footer |
| Phase 4 | 座標推論 (medium confidence) | layoutMode 実値 (exact confidence) |

## Phase 2: グループ化 + セクショニング

> **Stage A → Stage B → Stage C の3段階すべてが必須。Stage Cをスキップしてはならない。**

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

`--enriched-table` 指定時は、`generate_enriched_table()` によるリッチ形式テーブルを `enriched_children_table` キーに追加出力する（Issue 194）。

#### 2-2b. スクリーンショット取得

```
mcp__plugin_figma_figma__get_screenshot
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
```

スクリーンショット取得失敗時は Stage B をスキップし、Stage A のみで進行。
→ 詳細: [error-handling.md](error-handling.md)

#### 2-2c. Claude 推論

プロンプトテンプレート（`references/sectioning-prompt-template.md`）にコンテキスト JSON とスクリーンショットを組み合わせて Claude に送信。

#### 2-2d. セクショニング計画保存

```
.claude/cache/figma/sectioning-plan.yaml
```

### 2-3. Stage C: Claude ネストレベル推論（Haiku）

> **必須ステップ。スキップ禁止。**
> 出力: `nested-grouping-plan.yaml` — このファイルが生成されるまで次のステップ (2-4) に進まないこと。

#### 2-3a. ネストレベルコンテキスト生成

```bash
bash .claude/skills/figma-prepare/scripts/generate-nested-grouping-context.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  .claude/cache/figma/sectioning-plan.yaml \
  --output .claude/cache/figma/nested-context.json
```

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

#### 2-3e. Divider 吸収ポストプロセス（Issue #253）

```bash
bash .claude/skills/figma-prepare/scripts/postprocess-grouping-plan.sh \
  .claude/cache/figma/nested-grouping-plan.yaml \
  > .claude/cache/figma/nested-grouping-plan-postprocessed.yaml \
  && mv .claude/cache/figma/nested-grouping-plan-postprocessed.yaml \
       .claude/cache/figma/nested-grouping-plan.yaml
```

- Exit 0: 吸収あり（ファイル更新済み）
- Exit 2: 吸収対象なし（変更なし）

#### 2-3f. Stage C depth 再帰（Issue #257）

**必須実行ステップ** — 2-3e の後に実行すること。

```bash
python3 .claude/skills/figma-prepare/scripts/run-stage-c-depth-recursion.py \
  --metadata .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --plan .claude/cache/figma/nested-grouping-plan.yaml
```

- Exit 0: sub_groups 追加済み（plan ファイル更新）
- Exit 2: 分割対象なし（変更なし）
- 収束条件: 全グループが 3 未満の siblings → 自然終了（安全上限 10）
- 分割戦略: Col=L/R カラム分割 → 空間ギャップ (100px+) 分割

### 2-4. 結果統合（Stage A + Stage C 比較）

Stage B（トップレベル）は常に独立適用。Stage A と Stage C はセクションごとに比較。

```bash
bash .claude/skills/figma-prepare/scripts/compare-grouping.sh \
  .claude/cache/figma/grouping-plan.yaml \
  .claude/cache/figma/nested-grouping-plan.yaml \
  --output .claude/cache/figma/final-grouping-plan.yaml
```

- **カバレッジ** = Stage C で `single` 以外のグループに割り当てられた node 数 / 全 node 数
- カバレッジ >= 80% → **Stage C 結果を採用**
- カバレッジ < 80% → **Stage A にフォールバック**

### 2-5. dry-run / --apply

> **前提条件チェック**: --apply 実行前に以下のファイルが存在することを確認せよ。
>
> | ファイル | 生成元 | 必須 |
> |---------|--------|------|
> | `grouping-plan.yaml` | Stage A (2-1) | Yes |
> | `sectioning-plan.yaml` | Stage B (2-2) | Yes |
> | `nested-grouping-plan.yaml` | Stage C (2-3) | **Yes — 未生成なら Stage C (2-3a〜2-3e) を実行せよ** |

dry-run: grouping-plan.yaml（または final-grouping-plan.yaml）+ sectioning-plan.yaml を表示
--apply: `apply-grouping.js` テンプレートで evaluate_script 実行

### 2-5a〜2-5e: 適用の詳細手順

→ [apply-workflow.md](apply-workflow.md) を参照

### 2-6. --apply 後の構造 diff 検証

→ [apply-workflow.md](apply-workflow.md) の「検証」セクションを参照

### Stage A/C Integration Strategy（Issue #230）

Stage C（Claude推論）が十分なカバレッジを達成したセクションでは、Stage A の対応する検出器を無効化して重複を排除できる。

#### 推奨ワークフロー

```
1. Phase 2 通常実行（Stage A + B + C 全て実行）
2. compare-grouping.sh で Stage A/C 比較
3. カバレッジ結果を確認:
   - セクション coverage >= 80% → Stage C 採用
   - セクション coverage < 80% → Stage A フォールバック
4. [オプション] --disable-detectors を使用
```

#### 検出器互換性マトリクス

| Stage C pattern | 対応する Stage A method | 無効化可否 |
|----------------|----------------------|-----------|
| bg-content | bg-content | 可（STAGE_C_COVERABLE） |
| table | table | 可（STAGE_C_COVERABLE） |
| card / list | tuple, consecutive | 可（STAGE_C_COVERABLE） |
| heading-pair | heading-content | 可（STAGE_C_COVERABLE） |
| two-column | — (Stage A に対応なし) | — |
| decoration | highlight | 可（STAGE_C_COVERABLE） |
| single | — | — |
| — | header-footer | 不可（STAGE_A_ONLY） |
| — | horizontal-bar | 不可（STAGE_A_ONLY） |
| — | zone | 不可（STAGE_A_ONLY） |
| — | semantic | 不可（STAGE_A_ONLY） |
| — | proximity | 不可（STAGE_A_ONLY） |
| — | spacing | 不可（STAGE_A_ONLY） |
| — | pattern | 不可（STAGE_A_ONLY） |

## Phase 3: セマンティックリネーム

**API パターン**: → [figma-plugin-api.md](figma-plugin-api.md)

### 3-1. リネームマップ生成

```bash
bash .claude/skills/figma-prepare/scripts/generate-rename-map.sh \
  .claude/cache/figma/prepare-metadata-{nodeId}.json \
  --output .claude/cache/figma/rename-map.yaml
```

### 3-2. dry-run 出力（デフォルト）

```
Rename Plan: {total} layers to rename

Sample (first 10):
  "Rectangle 1"  →  "bg-hero"
  "Frame 23"     →  "card-feature-0"
  "Text 5"       →  "heading-about-us"

Full map: .claude/cache/figma/rename-map.yaml
```

### 3-3. --apply 実行（Adjacent Artboard 方式）

→ [apply-workflow.md](apply-workflow.md) の「Phase 3 適用」セクションを参照

### 3-4. ヒューマンゲート

"Figmaで Before/After を確認してください。複製アートボードが不要な場合は Ctrl+Z または手動削除で復元できます。"

## Phase 4: Auto Layout 適用

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
2. __AUTOLAYOUT_PLAN__ をレイアウトJSON配列に置換
3. __BATCH_INFO__ をバッチ情報に置換
4. __MIN_CONFIDENCE__ を最低信頼度に置換（"medium" 推奨）
5. evaluate_script で実行
```

### 4-3. --apply 後の Auto Layout 検証

→ [apply-workflow.md](apply-workflow.md) の「Phase 4 検証」セクションを参照

### Phase 4 信頼度

| 条件 | 信頼度 |
|------|-------|
| enriched layoutMode あり | exact（実データ由来） |
| 3+要素, gap CoV < 0.15 | high |
| 3+要素, gap CoV 0.15-0.35 | medium |
| 2要素 | medium |
| gap CoV >= 0.35 | low |

## Summary

全フェーズ完了後:

1. `prepare-report.yaml` を更新（実行済みフェーズを記録）
2. 次コマンドを提案

## フェーズ間の依存関係

```
Phase 1 → Phase 2 → Phase 3 → Phase 4
  (必須)    (任意)     (任意)     (任意)
```

- Phase 2 のグルーピングはノード名に依存しないため、リネーム前でも動作
- Phase 3 のリネームはグループ化後のコンテキスト（子構造）を利用でき精度向上
- Phase 4 はグループ化+リネーム後に実行すると適用対象が適切
