# /figma-prepare OPEN Issues

FIXED 済みの課題は削除済み（コード・ルールに反映済み）。

| # | Phase | 概要 |
|---|-------|------|
| 194 | 2(arch) | Phase B Claude推論のネストレベル拡張 — Stage A 検出器の段階的置換 |
| 201 | 2(B) | `prepare-sectioning-context.sh` ヘッダー/フッター検出に複数マジックナンバー — `page_h * 0.05`, `page_h * 0.9`, `page_w * 0.8` 等がハードコード |
| 202 | 4 | `infer-autolayout.sh` の `CENTER_ALIGN_VARIANCE=4` / `ALIGN_TOLERANCE=2` が figma-prepare.md 閾値テーブルに未登録 |
| 203 | 全体 | `_compute_flags` 内マジックナンバー — `1.05`, `1.02`, `0.95`, `50` がハードコード |
| 204 | 2 | `detect_bg_content_layers` left-overflow 判定の `parent_bb['w'] * 0.5` が figma-prepare.md 未登録 |
| 205 | 2 | `detect_heading_content_pairs` 40-80% 中間ゾーンの設計意図をコメントに明記すべき |
| 206 | 2 | `_split_by_spatial_gap` 非リーフ6要素の閾値がハードコード — figma-prepare.md 未登録 |
