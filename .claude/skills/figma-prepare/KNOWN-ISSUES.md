# /figma-prepare 既知の課題

実データテスト（米沢工機 1,236ノード）で検出。

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

## 根本原因

`get_metadata` が返すXMLには以下の情報**しか含まれない**:
- id, name, type, x, y, width, height

以下は**含まれない**:
- `layoutMode` (AutoLayout設定)
- `characters` (テキスト内容)
- `fills` (塗り)
- `strokes`, `effects`, `constraints` 等

## テストフィクスチャ対応 — 2026-03-04

- `fixture-metadata.json`: `layoutMode`, `characters`, `fills` を削除し、実API形式に統一
- `fixture-dirty.json`: 未命名レイヤー大量の汚いファイルを追加
- テストは全24件パス

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

| Issue | 状態 | 優先度 |
|-------|------|--------|
| 1 (deep_nesting過剰) | **FIXED** | — |
| 2 (AutoLayout誤判定) | **FIXED (workaround)** | — |
| 3 (リネーム精度) | **OPEN** | 中（Phase 2実用化時に対応） |
