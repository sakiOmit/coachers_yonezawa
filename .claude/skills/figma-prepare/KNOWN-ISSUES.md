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

現在 OPEN Issue なし。新規課題は下記に追記する。
