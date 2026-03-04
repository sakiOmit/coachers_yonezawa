# /figma-prepare 解決済みの課題

KNOWN-ISSUES.md から移動した FIXED Issue のアーカイブ。

## Issue 1: deep_nesting の過剰検出 — FIXED

- **現象**: 673ノードが「深すぎるネスト」判定（実際はほとんどが正常な構造）
- **原因**: `analyze-structure.sh` がROOTノードからの絶対深度で計算していた
- **修正内容**: セクションルート（width≈1440のフレーム）からの相対深度で計算するよう変更
- **修正日**: 2026-03-04

## Issue 2: AutoLayout未適用の誤判定 — FIXED (workaround)

- **現象**: 全フレームが「AutoLayout未適用」判定（実際は適用済みフレームもある）
- **原因**: `get_metadata` のXML出力に `layoutMode` 属性が含まれない
- **修正内容**: Auto Layout指標をスコア計算から除外（計測不能として`autolayout_penalty: 0`固定）。メトリクスとしては残すが参考値扱い
- **修正日**: 2026-03-04
- **将来対応**: `get_design_context` でセクション単位に取得し、layoutModeを補完する案あり（トークン消費とのトレードオフ）

## Issue 4: 小文字 `image` が未命名検出されない — FIXED

- **Phase**: 1
- **現象**: Figma自動生成の `image 1254`, `image 1347` が未命名パターンに引っかからない
- **原因**: 正規表現が `Image`（大文字I）のみマッチ。Figmaは小文字 `image` で自動命名する場合がある
- **修正内容**: `UNNAMED_RE` に `re.IGNORECASE` フラグを追加。大文字小文字を問わず検出
- **修正日**: 2026-03-04
- **ファイル**: `scripts/analyze-structure.sh`, `scripts/generate-rename-map.sh`

## Issue 5: deep_nesting がノード単位で膨張 — FIXED

- **Phase**: 1
- **現象**: お知らせ記事 (1-306) で deep_nesting=90 / total=130 (69%)。記事コンテンツ（リスト・テーブル）の末端ノードが全てカウントされる
- **原因**: 深いパスが1本でも、そこに含まれる全ての子孫ノードがカウントされる
- **修正内容**: コンテナノード（FRAME/GROUP/COMPONENT/SECTION）のみをカウント対象に変更。TEXT/RECTANGLE等の末端ノードは除外
- **修正日**: 2026-03-04
- **ファイル**: `scripts/analyze-structure.sh`

## Issue 7: グルーピング候補が多すぎる — FIXED

- **Phase**: 3
- **現象**: 全デザインで候補数がノード数の30%超（1-306: 44/130, 1-4: 34/106, 1-125: 48/141）
- **原因**: proximity (24px) + pattern + semantic の3アルゴリズムが独立に検出するため重複が多い。既にグループ化済みの要素も候補になる
- **修正内容**: `deduplicate_candidates()` 関数を追加。pattern/proximity 重複時は pattern を優先。セマンティック名付き親の proximity 候補を除去
- **修正日**: 2026-03-04
- **ファイル**: `scripts/detect-grouping-candidates.sh`
- **効果**: フィクスチャテストで候補が 9 → 6 に削減（33%減）

## Issue 8: XML→JSON 座標変換バグ — FIXED

- **Phase**: 3, 4
- **現象**: Phase 4 のパディング計算が `pad=[0,2220,2752,0]` 等の異常値を出力
- **原因**: `get_metadata` XML の座標値は**親相対座標**だが、スクリプトは `absoluteBoundingBox`（**絶対座標**）を期待。XML→JSON 変換時に座標系変換をしていない
- **修正内容**: 全4スクリプトに `resolve_absolute_coords()` 関数を追加。データロード後に親オフセットを累積加算して絶対座標に変換。テストフィクスチャも親相対座標形式に統一
- **修正日**: 2026-03-04
- **ファイル**: 全4スクリプト (`analyze-structure.sh`, `generate-rename-map.sh`, `detect-grouping-candidates.sh`, `infer-autolayout.sh`)

## Issue 9: Phase 3 の二重検出 — FIXED

- **Phase**: 3
- **現象**: Job Cards が proximity グループと pattern グループの両方で検出される。同じ要素が2つの候補に含まれる
- **原因**: proximity, pattern, semantic の各検出が独立実行される
- **修正内容**: Issue 7 と統合対応。`deduplicate_candidates()` で pattern 優先の重複除去を実装
- **修正日**: 2026-03-04
- **ファイル**: `scripts/detect-grouping-candidates.sh`

## Issue 10: Phase 4 Gap推論は正確だがPadding不正確 — FIXED

- **Phase**: 4
- **現象**: Gap推論は正確（Job Cards gap=24px, Tabs gap=0 等）。しかしPadding値は不正確（Issue 8 の座標バグに起因）
- **修正内容**: Issue 8 の `resolve_absolute_coords()` 適用により自動的に解消
- **修正日**: 2026-03-04
- **ファイル**: `scripts/infer-autolayout.sh`

## Issue 3: リネーム推論の精度不足 — FIXED

- **Phase**: 2
- **現象**: `group-6`, `frame-0` 等のフォールバック名が多い（大半がPriority 4-5）。Priority 1（テキスト内容ベース推論）が全く効かない
- **原因**: `node.get('characters', '')` は常に空文字（`get_metadata` に `characters` フィールドがない）。しかし TEXT ノードは `name` フィールドにテキスト内容を保持している
- **修正内容**:
  1. Priority 1: TEXT ノードの `name` をテキスト内容として使用（`characters` → `name`）
  2. `to_kebab()` に `JP_KEYWORD_MAP` 追加（日本語テキスト → 英語slug変換）
  3. `get_text_children_content()` ヘルパー追加（子TEXTノードの名前を収集）
  4. Priority 3.2: 小さい空フレーム（48x48以下）→ `icon-*`
  5. Priority 3.5: ナビゲーション検出（4+短テキスト子 → `nav-*`）
  6. Priority 4: ボタン/アイコン/見出し検出を分化（`text-block` catch-all を改善）
  7. `infer_text_role()` にボタンキーワード追加（`見る`, `戻る`, `詳細` 等）
- **効果**: 実データ3件でフォールバック率 95% → 20-38%（目標50%以下を達成）
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `tests/run-tests.sh`（5テスト追加）

## Issue 6: タブ/ボタンが text-block にリネームされる — FIXED

- **Phase**: 2
- **現象**: お知らせ一覧のタブ (Frame 94-98) → `text-block-0~4`。1テキスト子を持つフレームがすべて `text-block-*` に分類
- **原因**: Priority 4 の `text-block` catch-all がサイズや文脈を考慮せずに適用されていた
- **修正内容**: Issue 3 と統合対応。サイズヒューリスティック（h≤70 & w<300 & children≤2 → `btn-*`）を追加。TEXT子の名前からスラグ生成
- **効果**: Frame 94-98 → `btn-all`, `btn-news`, `btn-event`, `btn-category`
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`

## Issue 11: テストフィクスチャが実データの特徴を反映していない — FIXED

- **Phase**: 全フェーズ
- **修正内容**: 募集一覧 (1-4) から67ノードのサブセットを `fixture-realistic.json` として追加。`run-tests.sh` に9テスト追加。キャリブレーションにもケース追加
- **修正日**: 2026-03-04
- **ファイル**: `tests/fixture-realistic.json`, `tests/run-tests.sh`, `.claude/data/figma-prepare-calibration.yaml`

## テスト履歴

### テストフィクスチャ対応 — 2026-03-04

- `fixture-metadata.json`: `layoutMode`, `characters`, `fills` を削除し、実API形式に統一
- `fixture-dirty.json`: 未命名レイヤー大量の汚いファイルを追加
- 座標を親相対座標に変換（実APIと統一）
- テストは全24件パス（Issue 3+6 修正後37件）

### 3デザイン追加テスト — 2026-03-04

テスト対象:
- お知らせ記事 (1:306) — 130ノード、記事コンテンツ（リスト・テーブル・引用）
- 募集一覧 (1:4) — 106ノード、タブ+カードリスト
- お知らせ一覧 (1:125) — 141ノード、カードグリッド+ページネーション

### 初回キャリブレーション — 2026-03-04

| ID | Expected | Actual | Score (range) | Status |
|----|----------|--------|---------------|--------|
| fixture-metadata | B | B | 68.0 (60-80) | PASS |
| fixture-dirty | N/A | B | 67.0 (50-80) | PASS |
| real-dirty | D | D | 25.0 (15-35) | PASS |
| real-clean | B | B | 61.8 (55-70) | PASS |

**ペナルティ寄与率**: unnamed 66%, ungrouped 14%, flat 11%, nesting 8%

## 根本原因（参考）

`get_metadata` が返すXMLには以下の情報**しか含まれない**:
- id, name, type, x, y, width, height

以下は**含まれない**:
- `layoutMode` (AutoLayout設定)
- `characters` (テキスト内容) — ただしTEXTノードの `name` がテキスト内容を保持（Issue 3 で発見）
- `fills` (塗り)
- `strokes`, `effects`, `constraints` 等

座標値は**親相対座標**（Issue 8 の `resolve_absolute_coords()` で対処済み）。
