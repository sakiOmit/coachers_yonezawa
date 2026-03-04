# /figma-prepare 既知の課題

実データテスト（米沢工機 1,236ノード）で検出。
3デザイン追加テスト（2026-03-04）で Issue 4〜10 を追加。

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

## Issue 3: リネーム推論の精度不足 — OPEN

- **現象**: `group-6`, `frame-0` 等のフォールバック名が多い（305件中、大半がPriority 4-5）
- **原因**: `get_metadata` のXML出力に `characters`（テキスト内容）が含まれない。Priority 1（テキスト内容ベース推論）が全く効かない
- **影響**: リネーム後の名前がセマンティックでなく、実用性が低い
- **修正方針**: Phase 2 の開始時に `get_design_context` をセクション単位で取得し、テキスト内容を rename ロジックに注入する
- **ファイル**: `scripts/generate-rename-map.sh` + `SKILL.md` Phase 2 のフロー

## Issue 4: 小文字 `image` が未命名検出されない — OPEN

- **Phase**: 1
- **現象**: Figma自動生成の `image 1254`, `image 1347` が未命名パターンに引っかからない
- **原因**: 正規表現が `Image`（大文字I）のみマッチ。Figmaは小文字 `image` で自動命名する場合がある
- **影響**: unnamed_rate が過小評価される（実際より高スコアに）
- **修正方針**: 正規表現を大文字小文字無視 (`re.IGNORECASE`) にするか、パターンに `image` を追加
- **ファイル**: `scripts/analyze-structure.sh`, `scripts/generate-rename-map.sh`
- **テストデータ**: お知らせ一覧 (1-125) の `image 1254` ×5, 募集一覧 (1-4) の `image 1347`

## Issue 5: deep_nesting がノード単位で膨張 — OPEN

- **Phase**: 1
- **現象**: お知らせ記事 (1-306) で deep_nesting=90 / total=130 (69%)。記事コンテンツ（リスト・テーブル）の末端ノードが全てカウントされる
- **原因**: 深いパスが1本でも、そこに含まれる全ての子孫ノードがカウントされる
- **影響**: ペナルティ上限15で頭打ちのためスコアへの影響は限定的だが、メトリクスとしてミスリーディング
- **修正方針**: 案A: 深い「パス数」でカウント（深度>6のフレームの直接子が深い場合は1回だけカウント）。案B: メトリクスの説明を改善（「90ノードが深い構造に存在」）
- **ファイル**: `scripts/analyze-structure.sh`

## Issue 6: タブ/ボタンが text-block にリネームされる — OPEN

- **Phase**: 2
- **現象**: お知らせ一覧のタブ (Frame 94-98) → `text-block-0~4`。お知らせ記事のボタン (Frame 66 = 一覧に戻る) → `text-block-1`
- **原因**: 1テキスト子を持つフレーム = text-block と推論される。ボタン/タブの検出ロジックが弱い
- **影響**: Issue 3 の一部。テキスト内容があれば `btn-*` / `tab-*` と推論可能
- **修正方針**: Issue 3 の `get_design_context` テキスト注入で改善。加えて、サイズヒューリスティック（height < 70 & width < 300 → ボタン候補）を追加
- **ファイル**: `scripts/generate-rename-map.sh`

## Issue 7: グルーピング候補が多すぎる — OPEN

- **Phase**: 3
- **現象**: 全デザインで候補数がノード数の30%超（1-306: 44/130, 1-4: 34/106, 1-125: 48/141）
- **原因**: proximity (24px) + pattern + semantic の3アルゴリズムが独立に検出するため重複が多い。既にグループ化済みの要素も候補になる
- **影響**: dry-run 出力が大量でユーザーが確認しにくい
- **修正方針**:
  - 重複除去: 同じノードが複数候補に含まれる場合はマージ
  - 既にグループ化済み（=親フレームが名前付き）の場合はスキップ
  - proximity + pattern の両方で検出された場合は pattern を優先
- **ファイル**: `scripts/detect-grouping-candidates.sh`

## Issue 8: XML→JSON 座標変換バグ — OPEN (Critical)

- **Phase**: 3, 4
- **現象**: Phase 4 のパディング計算が `pad=[0,2220,2752,0]` 等の異常値を出力
- **原因**: `get_metadata` XML の座標値は**親相対座標**だが、スクリプトは `absoluteBoundingBox`（**絶対座標**）を期待。XML→JSON 変換時に座標系変換をしていない
- **影響**:
  - Phase 3: 距離計算 (`distance_between`) が不正確 → proximity グルーピングの精度低下
  - Phase 4: パディング計算が体系的に誤り。Gap推論は兄弟間差分なので影響なし
- **修正方針**: XML→JSON 変換スクリプトで親のオフセットを累積加算して絶対座標を計算
- **ファイル**: 変換スクリプト（現在は手動/インライン実行。共通ユーティリティ化を推奨）
- **備考**: 座標修正後は Phase 3, 4 を再テストが必要

## Issue 9: Phase 3 の二重検出 — OPEN

- **Phase**: 3
- **現象**: Job Cards が proximity グループと pattern グループの両方で検出される。同じ要素が2つの候補に含まれる
- **原因**: proximity, pattern, semantic の各検出が独立実行される
- **影響**: Issue 7 の一因
- **修正方針**: Issue 7 と統合対応（重複除去/マージロジック）
- **ファイル**: `scripts/detect-grouping-candidates.sh`

## Issue 10: Phase 4 Gap推論は正確だがPadding不正確 — OPEN

- **Phase**: 4
- **現象**: Gap推論は正確（Job Cards gap=24px, Tabs gap=0 等）。しかしPadding値は不正確（Issue 8 の座標バグに起因）
- **確認済みの正確なGap**:
  - Job Cards: gap=24 ← 正しい（Card 1 bottom=272, Card 2 top=296, diff=24）
  - Frame 97 tabs: gap=16 ← 妥当
  - Articles Grid: gap=0（密着グリッド、間隔はrow単位のY差で表現）
- **修正方針**: Issue 8 の座標修正後に自動的に改善
- **ファイル**: `scripts/infer-autolayout.sh`

## 根本原因

`get_metadata` が返すXMLには以下の情報**しか含まれない**:
- id, name, type, x, y, width, height

以下は**含まれない**:
- `layoutMode` (AutoLayout設定)
- `characters` (テキスト内容)
- `fills` (塗り)
- `strokes`, `effects`, `constraints` 等

加えて、座標値は**親相対座標**であり、Figma REST API の `absoluteBoundingBox` とは異なる。

## テストフィクスチャ対応 — 2026-03-04

- `fixture-metadata.json`: `layoutMode`, `characters`, `fills` を削除し、実API形式に統一
- `fixture-dirty.json`: 未命名レイヤー大量の汚いファイルを追加
- テストは全24件パス

## 3デザイン追加テスト — 2026-03-04

テスト対象:
- お知らせ記事 (1:306) — 130ノード、記事コンテンツ（リスト・テーブル・引用）
  https://www.figma.com/design/LoSe3INOuPV02kBttJFDSO/figma-prepare?node-id=1-306&m=dev
- 募集一覧 (1:4) — 106ノード、タブ+カードリスト
  https://www.figma.com/design/LoSe3INOuPV02kBttJFDSO/figma-prepare?node-id=1-4&m=dev
- お知らせ一覧 (1:125) — 141ノード、カードグリッド+ページネーション
  https://www.figma.com/design/LoSe3INOuPV02kBttJFDSO/figma-prepare?node-id=1-125&m=dev

### Phase 1 結果

| デザイン | Score | Grade | Unnamed | Deep Nesting |
|---------|-------|-------|---------|-------------|
| お知らせ記事 | 65.3 | B | 33 (25.4%) | 90 |
| 募集一覧 | 79.2 | B | 6 (5.7%) | 6 |
| お知らせ一覧 | 76.4 | B | 13 (9.2%) | 45 |

### Phase 2 結果

| デザイン | リネーム数 | Priority 4-5 率 |
|---------|-----------|----------------|
| お知らせ記事 | 33 | ~95% (group/text-block/frame) |
| 募集一覧 | 6 | 100% (ヘッダー部のみ) |
| お知らせ一覧 | 13 | ~100% |

### Phase 3 結果

| デザイン | 候補数 | ノード比 | ノイズ度 |
|---------|--------|---------|---------|
| お知らせ記事 | 44 | 33.8% | 高 |
| 募集一覧 | 34 | 32.1% | 高 |
| お知らせ一覧 | 48 | 34.0% | 高 |

### Phase 4 結果

| デザイン | フレーム数 | Gap精度 | Padding精度 |
|---------|-----------|---------|------------|
| お知らせ記事 | 43 | 良好 | 不正確 (Issue 8) |
| 募集一覧 | 32 | 良好 | 不正確 (Issue 8) |
| お知らせ一覧 | 44 | 良好 | 不正確 (Issue 8) |

## キャリブレーション結果 — 2026-03-04

`/figma-prepare-eval` による初回キャリブレーション実行結果:

| ID | Expected | Actual | Score (range) | Status |
|----|----------|--------|---------------|--------|
| fixture-metadata | B | B | 68.0 (60-80) | PASS |
| fixture-dirty | N/A | B | 67.0 (50-80) | PASS |
| real-dirty | D | D | 25.0 (15-35) | PASS |
| real-clean | B | B | 61.8 (55-70) | PASS |

- **Grade Accuracy**: 100% (3/3)
- **全ケース**: スコア範囲内

**ペナルティ寄与率**:
| 指標 | 寄与率 |
|------|--------|
| unnamed | 66% |
| ungrouped | 14% |
| flat | 11% |
| nesting | 8% |

**所見**: unnamed（未命名率）が支配的（66%）。フィクスチャでは flat/nesting が軽微なため、
実データ（real-dirty）でのみこれらが有意に効く。現在のスコア式は安定。

## 優先度

| Issue | Phase | 状態 | 優先度 | 概要 |
|-------|-------|------|--------|------|
| 1 (deep_nesting過剰) | 1 | **FIXED** | — | セクション相対深度に修正済み |
| 2 (AutoLayout誤判定) | 1 | **FIXED (workaround)** | — | スコアから除外済み |
| 3 (リネーム精度) | 2 | **OPEN** | 中 | characters 不足で Priority 1 不可 |
| 4 (小文字image未検出) | 1 | **OPEN** | 低 | 正規表現に小文字追加 |
| 5 (nesting膨張) | 1 | **OPEN** | 低 | メトリクスがミスリーディング |
| 6 (タブ/ボタン誤推論) | 2 | **OPEN** | 中 | Issue 3 と関連 |
| 7 (候補過多) | 3 | **OPEN** | 中 | 重複除去・フィルタ必要 |
| 8 (座標変換バグ) | 3,4 | **OPEN** | **高** | Phase 3,4 の根本 |
| 9 (二重検出) | 3 | **OPEN** | 中 | Issue 7 と統合対応 |
| 10 (Padding不正確) | 4 | **OPEN** | 高 | Issue 8 修正で解消 |
