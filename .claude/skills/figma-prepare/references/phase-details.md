# Phase Details

## Overview

`/figma-prepare` スキルの各フェーズの詳細ロジックと実行手順。
SKILL.md から参照される。

## Phase 1: 構造分析レポート

### 実行ツール

Figma MCP のみ（読み取り専用、リスクゼロ）

### 手順

1. `get_metadata` でページ構造を取得
2. メタデータ JSON を一時ファイルに保存
3. `analyze-structure.sh` でスコア計算
4. `prepare-report.yaml` を生成

### 検出項目

| 項目 | 検出方法 | 影響スコア |
|------|---------|-----------|
| 未命名レイヤー | 正規表現パターンマッチ | -0.5/% (上限-30) |
| フラット構造 | 直接子要素 > 15 | -5/件 + 超過子要素×0.5 (上限-40) |
| グルーピング候補 | 近接性 + 類似性 | -1/件 (上限-10) |
| 深いネスト | 6階層超 | -3/件 (上限-15) |
| AutoLayout未適用 | layoutMode 未設定 | 0 (計測不能のため除外) |

### 出力形式

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
  max_section_depth: 6  # Issue 71: セクションルートからの相対深度

score_breakdown:
  unnamed_penalty: 15.9
  flat_penalty: 10.0
  ungrouped_penalty: 5
  nesting_penalty: 9
  autolayout_penalty: 0  # unmeasurable via get_metadata — excluded from score

phases_executed: [1]
phases_recommended: [2]
```

### コンソール出力

```
╔══════════════════════════════════════════════╗
║         Figma Structure Quality Report       ║
╠══════════════════════════════════════════════╣

Score: 60 / 100  [Grade: B]

┌──────────────────────────────────────────────┐
│ Metrics                                       │
├───────────────────────────┬──────────────────┤
│ Total Nodes               │ 245              │
│ Unnamed Nodes             │ 78 (31.8%)       │
│ Flat Sections (>15 child) │ 2                │
│ Grouping Candidates       │ 5                │
│ Deep Nesting (>6)         │ 3                │
│ No Auto Layout Frames     │ 12 / 35          │
└───────────────────────────┴──────────────────┘

┌──────────────────────────────────────────────┐
│ Score Breakdown                               │
├───────────────────────────┬──────────────────┤
│ Unnamed penalty           │ -15.9            │
│ Flat structure penalty    │ -10.0            │
│ Ungrouped penalty         │ -5.0             │
│ Nesting penalty           │ -9.0             │
│ Auto Layout penalty       │ 0 (excluded)     │
└───────────────────────────┴──────────────────┘

Recommendation: Phase 2 (grouping) recommended

Next steps:
  /figma-prepare {url} --phase 2          # Grouping (dry-run)
  /figma-prepare {url} --phase 3          # Grouping + Rename (dry-run)
  /figma-prepare {url} --phase 3 --apply  # Grouping + Rename + apply
```

## Phase 2: グループ化 + セクショニング

Phase 2 は3段階構成:
- **Stage A**: 既存ヒューリスティック（ネストレベルのグルーピング）
- **Stage B**: Claude セクショニング（トップレベル children のセクション分割）
- **Stage C**: Claude ネストレベル推論（Haiku でセクション内部をグルーピング）

### Stage A: ヒューリスティック（グルーピング候補検出）

#### 実行ツール

Chrome DevTools MCP (`evaluate_script`)

#### 手順

1. Phase 1 のメタデータ JSON を読み込み
2. `detect-grouping-candidates.sh` でグルーピング候補検出
3. **dry-run (デフォルト)**: `grouping-plan.yaml` を出力
4. **--apply**: Chrome DevTools MCP で Frame 作成 + 子要素移動

#### 検出アルゴリズム

##### 近接性ベース (Union-Find)

1. 兄弟要素の全ペアの距離を計算
2. 距離 ≤ 24px のペアを Union-Find で結合
3. 2 要素以上のグループ → 候補

##### パターン検出

1. 各要素の「構造ハッシュ」を計算
   - `TYPE:[CHILD_TYPE1,CHILD_TYPE2,...]`
2. 同一ハッシュが 3 回以上 → リストアイテム候補

**注意**: fills 依存のセマンティック検出は Stage A から削除（Issue 29/30）後、
fills 非依存の構造ベースセマンティック検出（Card/Nav/Grid + Header/Footer）として再追加された（Issue 81/85）。
詳細は下記「Stage A 検出メソッド」テーブル参照。

#### 実行スクリプト (evaluate_script)

→ `figma-plugin-api.md` の「Phase 2: グループ化」セクション参照

#### 注意事項

- グループ化は子要素の位置をフレーム内相対座標に変換する
- 視覚的な変更が生じないよう、フレームの fills を空配列に設定
- コンポーネントインスタンスは対象外（detach 禁止）

### Stage B: Claude セクショニング

#### 目的

ページ直下（トップレベル）の children を意味的なセクションに分割する。
Stage A のヒューリスティックではカバーできない「セクション境界の推論」を Claude が担当。

#### 実行ツール

- `prepare-sectioning-context.sh`（bash、Claude を呼ばない）
- `get_screenshot`（Figma MCP）
- Claude 推論（SKILL 実行レベル）

#### 手順

1. `prepare-sectioning-context.sh` でトップレベル children のサマリーを JSON 生成
2. `get_screenshot` でページ全体のスクリーンショット取得
3. プロンプトテンプレート（`references/sectioning-prompt-template.md`）に展開
4. Claude に送信（テキスト + スクリーンショット画像）
5. YAML レスポンスをパース → `sectioning-plan.yaml` に保存

#### prepare-sectioning-context.sh の出力

```json
{
  "page_name": "募集一覧",
  "page_id": "1:4",
  "page_size": {"width": 1440, "height": 3858},
  "top_level_children": [
    {
      "id": "1:106", "name": "Group 46165", "type": "FRAME",
      "bbox": {"x": 10, "y": 10, "w": 1420, "h": 60},
      "child_count": 4,
      "child_types_summary": "RECTANGLE:2, FRAME:2",
      "has_text_children": true,
      "text_children_preview": ["米沢工機について", "事業紹介"],
      "is_unnamed": true
    }
  ],
  "total_children": 9,
  "heuristic_hints": {
    "header_candidates": ["1:106"],
    "footer_candidates": ["1:300"],
    "gap_analysis": [
      {"between": ["1:106", "1:101"], "gap_px": 241},
      {"between": ["1:5", "1:6"], "gap_px": 86}
    ],
    "background_candidates": ["1:101"]
  }
}
```

#### ヒューリスティックヒント

スクリプトが事前に推定したアンカーポイント:

| ヒント | 検出条件 |
|--------|---------|
| header_candidates | 上部5%、幅>80%のフレーム |
| footer_candidates | 下部10%、幅>80%のフレーム |
| gap_analysis | 隣接 children 間のY方向ギャップ（px）。大きなギャップはセクション境界を示唆 |
| background_candidates | 高さ>=100のRECTANGLE（背景画像・背景色の可能性） |

Claude はこれらを参考にしつつ、スクリーンショットの視覚情報を優先して最終判断する。

#### Fallback

| 条件 | 対応 |
|------|------|
| スクリーンショット取得失敗 | Stage B をスキップし、Stage A のみで進行 |
| Claude レスポンスパース失敗 | Stage B スキップ → Stage A のみで進行 |
| node_ids の合計 ≠ total_children | 警告 + ユーザー確認 |

### Stage C: Claude ネストレベル推論（Haiku）

#### 目的

Stage B で分割されたセクション内部の children に対して、Haiku でパターン認識ベースのグルーピングを推論する。
Stage A のヒューリスティック（12+個のルールベース検出器）と対称的に動作し、新パターン出現時に検出器追加が不要になる。

#### 実行ツール

- `generate-nested-grouping-context.sh`（bash）
- Claude Haiku 推論（SKILL 実行レベル）

#### 前提条件

- Stage B が正常に完了し、`sectioning-plan.yaml` が存在すること
- Stage B 未実行/失敗の場合、Stage C はスキップ

#### 手順

1. `generate-nested-grouping-context.sh` で各セクションのエンリッチドテーブルを生成
2. 各セクションに対して:
   a. プロンプトテンプレート（`references/nested-grouping-prompt-template.md`）にコンテキスト展開
   b. Haiku に送信（テキストのみ、スクリーンショット不要）
   c. YAML レスポンスをパース
   d. 検証（node_ids の合計 == total_children、ID 実在性、pattern 値の妥当性）
3. 検証合格セクションの結果を `nested-grouping-plan.yaml` に統合保存

#### generate-nested-grouping-context.sh の出力

```json
{
  "sections": [
    {
      "section_name": "section-hero-area",
      "section_id": "2:8320",
      "section_width": 1440,
      "section_height": 800,
      "total_children": 11,
      "enriched_children_table": "| # | ID | Name | Type | X | Y | W x H | Leaf? | ChildTypes | Flags | Text |\n|---|...|...|..."
    },
    {
      "section_name": "section-business",
      "section_id": "2:8400",
      "section_width": 1440,
      "section_height": 1200,
      "total_children": 20,
      "enriched_children_table": "| # | ID | Name | Type | X | Y | W x H | Leaf? | ChildTypes | Flags | Text |\n|---|...|...|..."
    }
  ]
}
```

#### nested-grouping-plan.yaml の出力形式

```yaml
# .claude/cache/figma/nested-grouping-plan.yaml
meta:
  generated_at: "2026-03-05T12:00:00Z"
  model: "haiku"
  total_sections: 6
  successful_sections: 5
  fallback_sections: 1  # Haiku 失敗 → Stage A にフォールバック

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
      - name: "hero-cards"
        pattern: "card"
        node_ids: ["2:8325", "2:8326", "2:8327"]
    coverage: 1.0  # single 以外のグループに割り当てられた割合

  - section_id: "2:8500"
    section_name: "section-recruit"
    status: "fallback"  # Haiku 失敗 or 検証失敗
    fallback_reason: "YAML parse error"
```

#### コスト試算（Issue 194 Phase 1 実証結果）

```
モデル: Haiku
入力: ~500-1500 tokens/セクション（要素10-30個のエンリッチドテーブル）
出力: ~200-500 tokens/セクション（YAML グルーピング結果）
コスト: ~$0.001-0.003/セクション

典型的なページ（6セクション）:
  Haiku × 6 ≈ $0.009-0.018
  ≈ Opus 1回の約 3%（実証結果）
  ≈ Opus × 0.3 以下（当初試算を大幅に下回る）
```

#### ID ハルシネーション対策

Issue 194 Phase 1 で発見された課題への対策:
- プロンプトに「テーブルの ID 列をそのまま正確にコピーせよ」を強調
- ルール8「出力前に ID 照合」を追加
- 検証ステップで全 node_ids の実在性をチェック（1件でも不一致 → 該当セクションをフォールバック）

#### Fallback 条件

| 条件 | 対応 |
|------|------|
| Stage B 未実行/失敗 | Stage C 全体をスキップ → Stage A のみ |
| Haiku API エラー（個別セクション） | 該当セクションのみ Stage A にフォールバック |
| YAML パース失敗 | 該当セクションのみ Stage A にフォールバック |
| node_ids 検証失敗（合計不一致 or ID 不在） | 該当セクションのみ Stage A にフォールバック |
| Haiku API エラー（全セクション） | Stage C 全体をスキップ → Stage A のみ |

### 結果統合（Stage A / Stage C 比較）

Stage B（トップレベルセクショニング）は対象レベルが異なるため、常に独立して適用する。

Stage A（ヒューリスティック）と Stage C（Haiku 推論）はどちらもネストレベルのグルーピングを行うため、
セクションごとにどちらの結果を採用するかを判定する。

#### 比較メトリクス

| メトリクス | 定義 | 閾値 |
|-----------|------|------|
| カバレッジ | Stage C で `single` 以外のグループに割り当てられた node 数 / 全 node 数 | >= 80% で採用 |

#### 判定ロジック

```
セクションごとに:
  1. Stage C の status が "success" かつ coverage >= 0.8
     → Stage C 結果を採用（Stage A のネストレベル候補は該当セクション分を破棄）
  2. Stage C の status が "fallback" または coverage < 0.8
     → Stage A にフォールバック（従来動作）
  3. Stage C 未実行
     → Stage A をそのまま使用（従来動作と完全互換）

最終結果 → final-grouping-plan.yaml に統合出力
```

#### compare-grouping.sh の出力

```yaml
# .claude/cache/figma/final-grouping-plan.yaml
meta:
  generated_at: "2026-03-05T12:00:00Z"
  stage_a_sections: 1
  stage_c_sections: 5
  total_sections: 6

groups:
  # Stage C 採用セクション（coverage >= 80%）
  - section_id: "2:8320"
    source: "stage_c"
    coverage: 1.0
    candidates:
      - node_ids: ["2:8321"]
        suggested_name: "bg-layer"
        pattern: "bg-content"
      - node_ids: ["2:8322", "2:8323", "2:8324"]
        suggested_name: "hero-content"
        pattern: "heading-pair"

  # Stage A フォールバックセクション
  - section_id: "2:8500"
    source: "stage_a"
    fallback_reason: "coverage 0.45 < 0.80"
    candidates:
      - node_ids: ["2:8501", "2:8502"]
        suggested_name: "group-0"
        method: "proximity"
```

### Stage A 検出メソッド

| メソッド | 優先度 | 説明 |
|---------|-------|------|
| semantic | 4 | 構造ベースのCard/Nav/Grid検出 + ヘッダー/フッター検出 + Bg-Content/Table/Horizontal-Bar検出（fills非依存） |
| highlight | 3.8 | RECTANGLE + TEXT 同位置ペア検出（Y重なり80%+、非ルートレベル、Issue 190） |
| heading-content | 3.5 | 見出し+コンテンツペア検出（`is_heading_like` + 高さ比率判定、Issue 166） |
| zone | 3 | Y座標範囲の重なりによる垂直ゾーンマージ（ルートレベル限定） |
| tuple | 2.8 | type列の繰り返しタプルパターン検出（3+回繰り返し、Issue 186） |
| consecutive | 2.5 | 連続する類似構造ハッシュ検出（Jaccard >= 0.7、3+連続、Issue 165） |
| pattern | 2 | Jaccard類似度 >= 0.7 のファジー構造ハッシュマッチング |
| spacing | 1 | 等間隔配置検出（Gap CoV < 0.25） |
| proximity | 0 | スコアリングベースの近接検出（距離×整列×サイズ類似） |

#### 追加セマンティック検出器（Issue 180-190）

| 検出タイプ | メソッド | 説明 |
|-----------|---------|------|
| Bg-Content | `detect_bg_content_layers()` | フル幅RECTANGLE(80%+) + 装飾 → bg-layer、残り → content-layer（Issue 180） |
| Table | `detect_table_rows()` | 3+フル幅RECTANGLE(90%+) + divider + TEXT → テーブル行単位グルーピング（Issue 181） |
| Horizontal-Bar | `detect_horizontal_bar()` | 狭Y帯域(<100px)に4+要素、RECTANGLE背景、水平分布 → news-bar等（Issue 184） |
| Highlight | `detect_highlight_text()` | RECTANGLE + TEXT 同位置ペア（Y重なり80%+） → highlight-{slug}（Issue 190） |
| Tuple | `detect_repeating_tuple()` | type列のN-タプル繰り返し(3+回) → card-list等（Issue 186） |
| Consecutive | `detect_consecutive_similar()` | 連続する類似構造ハッシュ(3+連続) → list等（Issue 165） |
| Heading-Content | `detect_heading_content_pairs()` | 見出し+コンテンツのペア検出 → section-{heading}（Issue 166） |
| Absorbable | `find_absorbable_elements()` | LINE/小要素を最近グループに吸収（Issue 167） |

#### 近接グルーピングスコア (Issue 78)

```
effective_distance = raw_distance × alignment_bonus × size_similarity_bonus
score = max(0, 1 - effective_distance / (gap × 2))
score > 0.5 → グループ化
```

- alignment_bonus: 左端/右端/中心X/上端/下端/中心Y が 2px 以内 → 0.5（距離半減）
- size_similarity_bonus: 幅・高さとも 20% 以内 → 0.7（距離 30% 減）

#### ファジーパターン検出 (Issue 79)

構造ハッシュの子要素リストを Multiset として Jaccard 類似度を計算:
```
similarity = |intersection| / |union|
similarity >= 0.7 → 同一パターン
```

#### セマンティック前検出 (Issue 81, 85, 180-190)

- Card: FRAME/COMPONENT/INSTANCE、子2-6個、IMAGE/RECTANGLE + TEXT (Issue 81)
- Navigation: 4+子要素、水平配置、各TEXT幅 < 200px (Issue 81)
- Grid: 2+行 × 2+列、要素サイズ類似（20%以内） (Issue 81)
- Header: 上部ゾーン + ナビTEXT + ロゴ要素 (Issue 85)
- Footer: 下部ゾーン + 2+要素 (Issue 85)
- Bg-Content: 全幅RECTANGLE(80%+) + 装飾 → bg-layer、残り → content-layer (Issue 180)
- Table: 3+全幅RECTANGLE(90%+) + divider + TEXT行メンバー (Issue 181)
- Horizontal-Bar: 狭Y帯域(<100px)に4+要素、RECTANGLE背景、水平分布 (Issue 184)
- Highlight: RECTANGLE + TEXT 同位置ペア（Y重なり80%+） (Issue 190)

## Phase 3: セマンティックリネーム

### 実行ツール

- dry-run: `generate-rename-map.sh`（ローカル Python、Chrome 不要）
- `--apply`: Chrome DevTools MCP (`evaluate_script`)

### 前提条件

- Chrome DevTools MCP が接続済みであること（`--apply` 時のみ）
- `typeof figma === 'object'` であること（`--apply` 時のみ）
- dry-run（デフォルト）では Chrome DevTools 不要

### 手順

1. Phase 1 のメタデータ JSON を読み込み（Phase 2 のグルーピング後のメタデータがあればそちらを使用）
2. `generate-rename-map.sh` でリネームマップ生成
3. **dry-run (デフォルト)**: `rename-map.yaml` を出力して終了
4. **--apply**: Chrome DevTools MCP でバッチ実行

### リネームロジック（優先順）

| 優先度 | 手法 | 判定条件 | 結果例 |
|-------|------|---------|-------|
| 0 | EN+JPラベルペア検出 | 大文字ASCII TEXT + 日本語TEXT兄弟、200px以内 | en-label-company, heading-company-info（Issue 185） |
| 1 | テキスト内容 | TEXT ノード | heading-about-us |
| 2 | シェイプ分析 | 幅/高さ比率、サイズ、fills | divider-0, bg-1, img-0 |
| 3 | 位置分析 | PAGE/CANVAS 直下の Y 座標 | section-header, section-footer |
| 3.1 | ヘッダー/フッター | 上端+幅広+ナビ子要素 / 下端+コンパクト+テキスト多 | header, footer |
| 3.15 | CTA正方形ボタン検出 | 略正方形(0.8-1.2比)+右上配置+CTAキーワード | cta-contact（Issue 193） |
| 3.16 | サイドパネル検出 | 幅80px以下+高さ/幅比3.0以上+ページ端配置 | side-panel-0（Issue 192） |
| 3.2 | 小アイコン | 子なし、48x48以下 | icon-0 |
| 3.5 | ナビゲーション | 4+短テキスト子要素 | nav-0 |
| 4.0 | 装飾パターン検出 | FRAME/GROUP、200px以下、60%+シェイプ葉ノード、3+シェイプ | decoration-dots-0, decoration-pattern-0（Issue 189） |
| 4 | 子構造分析 | 子要素のタイプ構成 | card-0, text-block-1 |
| 5 | フォールバック | 上記全て不可 | frame-3, rectangle-5 |

### バッチ実行

```
リネーム対象: N 件
バッチサイズ: 50 件/回
バッチ数: ceil(N / 50)

各バッチ:
  1. evaluate_script で 50 件のリネームを実行
  2. 結果を確認（renamed / errors）
  3. エラーがあればスキップして次へ
```

### ヒューマンゲート

Phase 3 完了後、ユーザーに以下を確認:
- Figma デスクトップ/Web でリネーム結果を確認
- 問題があれば Ctrl+Z で Undo 可能
- 確認後に Phase 4 に進行

## Phase 4: Auto Layout 適用

### 実行ツール

Chrome DevTools MCP (`evaluate_script`)

### 手順

1. Phase 1 のメタデータ JSON を読み込み
2. `infer-autolayout.sh` で設定推論
3. **dry-run (デフォルト)**: `autolayout-plan.yaml` を出力
4. **--apply**: Chrome DevTools MCP で Auto Layout 適用

### 推論ロジック

#### 方向判定

```
2要素の場合 (Issue 82):
  dx = |center_x1 - center_x2|
  dy = |center_y1 - center_y2|
  dx > dy → HORIZONTAL, それ以外 → VERTICAL

3要素以上:
  X座標の分散 vs Y座標の分散
  X分散 > Y分散 × 1.5 → HORIZONTAL
  それ以外 → VERTICAL
```

#### WRAP検出 (Issue 83)

```
方向判定後:
  HORIZONTAL + 4+要素 + Y座標が2+行に分かれる → WRAP
  WRAP時はdirectionを'WRAP'に上書き
```

#### Gap 推論

```
通常: 隣接要素間のスペーシングを計算、中央値、4px刻みスナップ
WRAP: 行内のみでgap計算（行境界の大きなgapを除外）
```

#### Padding 推論

```
上 = min(子Y) - 親Y
左 = min(子X) - 親X
下 = (親Y + 親H) - max(子Y + 子H)
右 = (親X + 親W) - max(子X + 子W)
各値を 4px 刻みにスナップ
```

#### Primary Axis Alignment (Issue 83)

```
SPACE_BETWEEN:
  先頭要素が親の開始端に接触(4px以内) + 末尾要素が終了端に接触
  → primaryAxisAlignItems = 'SPACE_BETWEEN'
それ以外 → MIN
```

#### Counter Axis Alignment

```
VERTICAL layout:
  子要素の中央X が同じ → CENTER
  子要素の右端X が同じ → MAX
  子要素の左端X が同じ → MIN
  それ以外 → MIN (デフォルト)

HORIZONTAL/WRAP layout:
  子要素の中央Y が同じ → CENTER
  子要素の下端Y が同じ → MAX
  子要素の上端Y が同じ → MIN
  それ以外 → MIN
```

注: Figma Plugin API の counterAxisAlignItems は MIN/CENTER/MAX のみ受け付ける（Issue 104）。

### 信頼度 (Issue 84)

| 条件 | 信頼度 |
|------|-------|
| enriched layoutMode あり | exact（実 Figma データ由来） |
| 3+要素, gap CoV < 0.15 | high |
| 3+要素, gap CoV 0.15-0.35 | medium |
| 2要素 | medium |
| gap CoV >= 0.35 | low |

enriched metadata に `layoutMode` が含まれる場合、推論ではなく実データから直接取得するため
信頼度 `exact` が付与される（Issue 18）。

gap CoV (Coefficient of Variation) = 標準偏差 / 平均。0に近いほどgapが均一。

## フェーズ間の依存関係

```
Phase 1 → Phase 2 → Phase 3 → Phase 4
  (必須)    (任意)     (任意)     (任意)

Phase 1: メタデータ取得（全フェーズの基盤）
Phase 2: グループ化（構造確定。Phase 3 の前に実行推奨）
Phase 3: リネーム（確定構造に対してセマンティック命名）
Phase 4: Auto Layout（グループ化+リネーム済みフレームに最も効果的）
```

- Phase 1 は常に実行（必須）
- Phase 2-4 は `--phase` オプションで指定
- Phase 2 のグルーピングはノード名に依存しないため、リネーム前でも動作する
- Phase 3 のリネームはグループ化後のコンテキスト（子構造）を利用でき、精度が向上する
- Phase 4 はグループ化+リネーム後に実行すると、適用対象が適切になる
