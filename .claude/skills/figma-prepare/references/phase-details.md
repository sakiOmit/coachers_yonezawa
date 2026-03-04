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
| フラット構造 | 直接子要素 > 15 | -5/件 (上限-20) |
| グルーピング候補 | 近接性 + 類似性 | -2/件 (上限-20) |
| 深いネスト | 6階層超 | -3/件 (上限-15) |
| AutoLayout未適用 | layoutMode 未設定 | -1/件 (上限-15) |

### 出力形式

```yaml
# .claude/cache/figma/prepare-report.yaml
meta:
  generated_at: "2026-03-04T12:00:00Z"
  figma_url: "https://figma.com/design/..."
  fileKey: "abc123"
  nodeId: "0:1"

quality:
  score: 65
  grade: "B"
  recommendation: "Phase 2 (rename) recommended"

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

score_breakdown:
  unnamed_penalty: 15.9
  flat_penalty: 10
  ungrouped_penalty: 10
  nesting_penalty: 9
  autolayout_penalty: 12

phases_executed: [1]
phases_recommended: [2]
```

### コンソール出力

```
╔══════════════════════════════════════════════╗
║         Figma Structure Quality Report       ║
╠══════════════════════════════════════════════╣

Score: 65 / 100  [Grade: B]

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
│ Ungrouped penalty         │ -10.0            │
│ Nesting penalty           │ -9.0             │
│ Auto Layout penalty       │ -12.0            │
└───────────────────────────┴──────────────────┘

Recommendation: Phase 2 (rename) recommended

Next steps:
  /figma-prepare {url} --phase 2          # Rename layers
  /figma-prepare {url} --phase 2 --apply  # Rename + apply
```

## Phase 2: セマンティックリネーム

### 実行ツール

Chrome DevTools MCP (`evaluate_script`)

### 前提条件

- Figma ブランチ上であること（ユーザー確認）
- Chrome DevTools MCP が接続済みであること
- `typeof figma === 'object'` であること

### 手順

1. Phase 1 のメタデータ JSON を読み込み
2. `generate-rename-map.sh` でリネームマップ生成
3. **dry-run (デフォルト)**: `rename-map.yaml` を出力して終了
4. **--apply**: Chrome DevTools MCP でバッチ実行

### リネームロジック（優先順）

| 優先度 | 手法 | 判定条件 | 結果例 |
|-------|------|---------|-------|
| 1 | テキスト内容 | TEXT ノード | heading-about-us |
| 2 | シェイプ分析 | 幅/高さ比率、サイズ | divider-0, bg-1 |
| 3 | 位置分析 | ページ内 Y 座標 | section-header, section-footer |
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

Phase 2 完了後、ユーザーに以下を確認:
- Figma デスクトップ/Web でリネーム結果を確認
- 問題があれば Ctrl+Z で Undo 可能
- 確認後に Phase 3 に進行

## Phase 3: グループ化

### 実行ツール

Chrome DevTools MCP (`evaluate_script`)

### 手順

1. Phase 1 のメタデータ JSON を読み込み
2. `detect-grouping-candidates.sh` でグルーピング候補検出
3. **dry-run (デフォルト)**: `grouping-plan.yaml` を出力
4. **--apply**: Chrome DevTools MCP で Frame 作成 + 子要素移動

### 検出アルゴリズム

#### 近接性ベース (Union-Find)

1. 兄弟要素の全ペアの距離を計算
2. 距離 ≤ 24px のペアを Union-Find で結合
3. 2 要素以上のグループ → 候補

#### パターン検出

1. 各要素の「構造ハッシュ」を計算
   - `TYPE:[CHILD_TYPE1,CHILD_TYPE2,...]`
2. 同一ハッシュが 3 回以上 → リストアイテム候補

#### セマンティック検出

| 子要素構成 | 推論名 |
|-----------|-------|
| IMAGE + TEXT + FRAME(btn) | card |
| IMAGE + TEXT | media-object |
| TEXT(large) + TEXT(small) | text-block |
| FRAME × N (同構造) | list |

### 実行スクリプト (evaluate_script)

→ `figma-plugin-api.md` の「Phase 3: グループ化」セクション参照

### 注意事項

- グループ化は子要素の位置をフレーム内相対座標に変換する
- 視覚的な変更が生じないよう、フレームの fills を空配列に設定
- コンポーネントインスタンスは対象外（detach 禁止）

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
X座標の分散 vs Y座標の分散
  X分散 > Y分散 × 1.5 → HORIZONTAL
  それ以外 → VERTICAL
```

#### Gap 推論

```
隣接要素間のスペーシングを計算
中央値を取得
4px 刻みにスナップ
```

#### Padding 推論

```
上 = min(子Y) - 親Y
左 = min(子X) - 親X
下 = (親Y + 親H) - max(子Y + 子H)
右 = (親X + 親W) - max(子X + 子W)
各値を 4px 刻みにスナップ
```

#### Counter Axis Alignment

```
VERTICAL layout:
  子要素の中央X が同じ → CENTER
  子要素の左端X が同じ → MIN
  それ以外 → MIN (デフォルト)

HORIZONTAL layout:
  子要素の中央Y が同じ → CENTER
  それ以外 → MIN
```

### 信頼度

| 条件 | 信頼度 |
|------|-------|
| 子要素 3+ & Gap 均一 | high |
| 子要素 2 | medium |
| Gap ばらつき大 | low |

信頼度 `low` の場合は dry-run で警告を表示。

## フェーズ間の依存関係

```
Phase 1 → Phase 2 → Phase 3 → Phase 4
  (必須)    (任意)     (任意)     (任意)

Phase 1: メタデータ取得（全フェーズの基盤）
Phase 2: リネーム（Phase 3, 4 の前に実行推奨）
Phase 3: グループ化（Phase 4 の前に実行推奨）
Phase 4: Auto Layout（グループ化済みフレームに最も効果的）
```

- Phase 1 は常に実行（必須）
- Phase 2-4 は `--phase` オプションで指定
- Phase 3 はリネーム後に実行すると、グループ名がセマンティックになる
- Phase 4 はグループ化後に実行すると、適用対象が適切になる
