# /figma-prepare OPEN Issues

FIXED 済みの課題は削除済み（コード・ルールに反映済み）。

| # | Phase | 概要 | Status |
|---|-------|------|--------|
| 258 | 2 | detect_repeating_tuple() に hidden children フィルタ欠如 | DONE |
| 259 | 2 | detect_bg_content_layers() に hidden children フィルタ欠如 | DONE |
| 260 | 2 | validate_column_consistency() が hidden nodes を含めてCol計算 | DONE |
| 261 | 2 | generate_enriched_table() x_span==0 時の2カラム誤検出（既にガード済み確認、回帰テスト追加） | DONE |
| 262 | 2 | run-stage-c-depth-recursion.py node ID空文字ガード欠如（2箇所修正） | DONE |
| 263 | - | SKILL.md 整合性問題5件（Phase tree/Stage C範囲/Scripts表/参照ファイル/重複行） | DONE |
| 264 | - | absorb_stage_c_dividers / validate_column_consistency / detect_repeating_tuple / detect_bg_content_layers エッジケーステスト追加（7テスト） | DONE |
| 265 | 2 | detect-grouping-candidates.sh off-canvas フィルタで root_y 未渡し（is_off_canvas に root_y パラメータ追加） | DONE |
| 266 | 1 | prepare-sectioning-context.sh ヘッダーゾーンマージンに FOOTER_ZONE_MARGIN を誤用（HEADER_ZONE_MARGIN 新設） | DONE |
| 267 | 2 | postprocess-grouping-plan.sh + run-stage-c-depth-recursion.py JSON パースエラー時のサイレント消失に警告追加 | DONE |
| 268 | 2 | run-stage-c-depth-recursion.py 再帰ターゲット判定の冗長な外側条件を簡素化 | DONE |
| 269 | 2 | run-stage-c-depth-recursion.py MAX_STAGE_C_DEPTH off-by-one → 調査の結果 range() で正しく制御済み、変更不要 | DONE (no change) |
| 270 | - | Reference テンプレート2ファイル（sectioning-prompt-template.md, phase-details.md）の enriched table に Col 列追加 | DONE |
| 271 | - | Col 列テスト4件（L/R/F/C/-）+ Flag テスト2件（overflow-y, bg-wide）追加 | DONE |

## OPEN Issues

| # | Phase | 概要 | Status |
|---|-------|------|--------|
| 272 | 4 | resolve_absolute_coords() がXMLメタデータの絶対座標を二重加算 — Phase 4のpadding推論が壊れる（方向・gapは兄弟相対距離なので影響なし）。ISOベンチマークで崩壊を確認済み | OPEN |
| 273 | 2 | build_pattern_registry() がroot_children(リスト)を受け取ると .get() エラー — 非クリティカル | OPEN |
| 274 | 2 | 1:N heading-content グルーピング未対応 — CSRベンチマークで発覚。topic見出しの下に複数活動アイテムがネストされず兄弟のまま放置。方針: (1) Stage Cプロンプト改善（1:Nパターン例示+enriched tableにヒント追加） (2) grouping_llm_fallback新設 — Stage C後にLLMがグルーピング結果をレビュー・補正（rename_llm_fallbackと対称的な設計）。ヒューリスティック拡張はばらつくため避けLLM推論で介入 | OPEN |

新規課題は上記テーブルに追記する。

## ベンチマークテスト（必須）

figma-prepare のロジック変更時は、実務デザインベンチマークで回帰テストを行うこと。

### データセット

| ページ | ファイル | ノード数 | 特徴 |
|--------|---------|---------|------|
| /iso | `tests/figma-prepare/benchmark/data/iso.xml` | 167 | シンプル、EN+JPペア、section-bg |
| /csr | `tests/figma-prepare/benchmark/data/csr.xml` | 302 | 複雑、127直下子要素、1:Nヘディング、2カラムレイアウト |

### 実行方法

```bash
# 全ベンチマーク実行
python3 tests/figma-prepare/benchmark/run_benchmark.py --all

# 個別実行
python3 tests/figma-prepare/benchmark/run_benchmark.py tests/figma-prepare/benchmark/data/iso.xml
python3 tests/figma-prepare/benchmark/run_benchmark.py tests/figma-prepare/benchmark/data/csr.xml
```

### ベースライン結果

- `tests/figma-prepare/benchmark/results/iso-benchmark.yaml` — before（分析のみ）
- `tests/figma-prepare/benchmark/results/iso-benchmark-after.yaml` — after（Phase 2-3適用後）
- `tests/figma-prepare/benchmark/results/csr-benchmark.yaml` — before
- `tests/figma-prepare/benchmark/results/csr-benchmark-after.yaml` — after

### 回帰チェック項目

ロジック変更後、以下の指標がベースラインから悪化していないことを確認:

- グルーピング候補数（method別）
- リネーム信頼度分布（high/medium/low）
- EN+JPペア検出数（ISO: 4, CSR: 10）
- bullet検出数（ISO: 6, CSR: 18）
- section-bg検出数（両ページ: 12）
