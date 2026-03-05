# /figma-prepare OPEN Issues

FIXED 済みの課題は削除済み（コード・ルールに反映済み）。

| # | Phase | 概要 |
|---|-------|------|
| 194 | 2(arch) | Phase B Claude推論のネストレベル拡張 — Stage A 検出器の段階的置換 |
| 207 | 2(B) | `prepare-sectioning-context.sh` header cluster 検出マジックナンバー群 — `120`, `50`, `20`, `3`, `4` がハードコード（figma_utils から import すべき） |
| 208 | 2(B) | `prepare-sectioning-context.sh` consecutive pattern で `0.7` / `3` がハードコード — JACCARD_THRESHOLD / CONSECUTIVE_PATTERN_MIN を figma_utils から import すべき |
| 209 | 2(B) | `prepare-sectioning-context.sh` loose elements で `20` がハードコード — LOOSE_ELEMENT_MAX_HEIGHT を import すべき |
| 210 | 2 | `detect-grouping-candidates.sh` の14定数がローカル定義 — figma_utils.py に集約すべき（Issue 207-209 の根本原因） |
| 211 | 4 | `infer-autolayout.sh` の `VARIANCE_RATIO=1.5` がローカル定義 — figma_utils.py 未集約 |
| 212 | 2(C) | `generate-nested-grouping-context.sh` の `GRANDCHILD_THRESHOLD=5` が figma-prepare.md / figma_utils.py 未登録 |
| 213 | 全体 | `detect_consecutive_similar` のデフォルト `similarity_threshold=0.7` がインラインハードコード — JACCARD_THRESHOLD 定数参照すべき |
| 214 | 全体 | `compare_grouping_results` の `match_threshold=0.5` がローカル変数 — 定数化・閾値テーブル登録すべき |
| 215 | 3 | `generate-rename-map.sh` CTA検出 `parent_w * 0.8` — X位置閾値が figma-prepare.md 未登録 |
| 216 | 3 | `generate-rename-map.sh` サイドパネル検出 `parent_w * 0.9` / `0.1` — X位置閾値が figma-prepare.md 未登録 |
| 217 | 3 | `generate-rename-map.sh` footer テキスト比率 `0.3` — 設計意図コメント不足、figma-prepare.md 未登録 |
| 218 | 3 | `generate-rename-map.sh` `has_image_wrapper` 比率 `0.5` — figma-prepare.md 未登録 |
| 219 | 3 | `generate-rename-map.sh` heading vs body テキスト長 `50` — figma-prepare.md 未登録 |
| 220 | 2 | `detect-grouping-candidates.sh` `is_grid_like` サイズ類似度 `0.20` — 閾値テーブル独立エントリ未登録 |
