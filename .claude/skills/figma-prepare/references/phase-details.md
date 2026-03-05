# Phase Details

SKILL.md および `.claude/rules/figma-prepare.md` を補完する詳細情報のみ記載。
スコア計算式・閾値・リネームロジック・Auto Layout推論は `figma-prepare.md` を参照。

## Phase 1: 出力形式

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

## Phase 2: Stage C — Claude ネストレベル推論（Haiku）

Stage B で分割されたセクション内部の children に対して、Haiku でグルーピングを推論。
Stage A ヒューリスティック（12+検出器）と対称的に動作し、新パターン出現時に検出器追加が不要。

### 前提条件

- Stage B 完了済み + `sectioning-plan.yaml` 存在
- 未実行/失敗時は Stage C スキップ

### 手順

1. `generate-nested-grouping-context.sh` で各セクションのエンリッチドテーブル生成
2. 各セクションに対して Haiku 推論（テキストのみ、スクショ不要）
3. 検証: node_ids 合計 == total_children、ID 実在性、pattern 妥当性
4. 合格セクションを `nested-grouping-plan.yaml` に統合保存

### generate-nested-grouping-context.sh の出力

```json
{
  "sections": [
    {
      "section_name": "section-hero-area",
      "section_id": "2:8320",
      "section_width": 1440,
      "section_height": 800,
      "total_children": 11,
      "enriched_children_table": "| # | ID | Name | Type | X | Y | W x H | Leaf? | ChildTypes | Flags | Text |"
    }
  ]
}
```

### nested-grouping-plan.yaml の出力形式

```yaml
meta:
  generated_at: "2026-03-05T12:00:00Z"
  model: "haiku"
  total_sections: 6
  successful_sections: 5
  fallback_sections: 1

sections:
  - section_id: "2:8320"
    section_name: "section-hero-area"
    status: "success"
    groups:
      - name: "bg-layer"
        pattern: "bg-content"
        node_ids: ["2:8321"]
      - name: "hero-content"
        pattern: "heading-pair"
        node_ids: ["2:8322", "2:8323", "2:8324"]
    coverage: 1.0
```

### コスト試算

```
Haiku: ~500-1500 tokens入力/セクション、~200-500 tokens出力
コスト: ~$0.001-0.003/セクション
6セクション ≈ $0.009-0.018 ≈ Opus 1回の約3%
```

### ID ハルシネーション対策

- プロンプトに「ID 列をそのまま正確にコピーせよ」を強調
- 検証ステップで全 node_ids の実在性チェック（1件不一致 → フォールバック）

### Fallback 条件

| 条件 | 対応 |
|------|------|
| Stage B 未実行/失敗 | Stage C 全体スキップ → Stage A のみ |
| Haiku API エラー（個別） | 該当セクションのみ Stage A フォールバック |
| YAML パース/検証失敗 | 該当セクションのみ Stage A フォールバック |

## Phase 2: 結果統合（Stage A / Stage C 比較）

Stage B（トップレベル）は常に独立適用。Stage A と Stage C はセクションごとに比較。

```
セクションごとに:
  1. Stage C status=success + coverage >= 0.8 → Stage C 採用
  2. Stage C fallback or coverage < 0.8 → Stage A フォールバック
  3. Stage C 未実行 → Stage A そのまま使用
```

### compare-grouping.sh 出力

```yaml
meta:
  stage_a_sections: 1
  stage_c_sections: 5
  total_sections: 6

groups:
  - section_id: "2:8320"
    source: "stage_c"
    coverage: 1.0
    candidates:
      - node_ids: ["2:8321"]
        suggested_name: "bg-layer"
        pattern: "bg-content"
  - section_id: "2:8500"
    source: "stage_a"
    fallback_reason: "coverage 0.45 < 0.80"
```

## Phase 4: 信頼度

| 条件 | 信頼度 |
|------|-------|
| enriched layoutMode あり | exact（実データ由来） |
| 3+要素, gap CoV < 0.15 | high |
| 3+要素, gap CoV 0.15-0.35 | medium |
| 2要素 | medium |
| gap CoV >= 0.35 | low |

gap CoV = 標準偏差 / 平均。0に近いほど均一。

## フェーズ間の依存関係

```
Phase 1 → Phase 2 → Phase 3 → Phase 4
  (必須)    (任意)     (任意)     (任意)
```

- Phase 2 のグルーピングはノード名に依存しないため、リネーム前でも動作
- Phase 3 のリネームはグループ化後のコンテキスト（子構造）を利用でき精度向上
- Phase 4 はグループ化+リネーム後に実行すると適用対象が適切
