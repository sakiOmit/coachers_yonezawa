# /figma-prepare OPEN Issues

FIXED 済みの課題は削除済み（コード・ルールに反映済み）。

| # | Phase | 概要 | Status |
|---|-------|------|--------|
| 250 | 2 | generate-nested-grouping-context.sh GROUPS mode line 206 hiddenフィルタ欠如 | DONE |
| 251 | 2 | detect_wrap() 丸め(round)による偽WRAP検出 → 距離ベースグルーピングに修正 | DONE |
| 252 | 2 | generate-nested-grouping-context.sh JSON解析エラーハンドリング + node_ids型検証 | DONE |
| 253 | 2 | Stage C divider単一要素グループを隣接list-itemグループに吸収（border-bottom解釈対応） | DONE |

| 254 | - | list-item内部構造の不整合＋リンク判定 → figma-implement側で対処（nested-grouping-plan.yaml読み込み+Claude総合推論） | figma-implement #1 に移管 |
| 255 | 2 | Stage C再帰: pattern="single"でも children>=3 なら depth 1 処理すべき（再帰条件緩和） | DONE |
| 256 | 2 | Stage C左右カラムのクロス混入防止 — enriched tableにCol列追加+プロンプトRule 11+validate_column_consistency() | DONE |

| 257 | 2 | Stage C depth recursion — 収束ベース再帰的サブグルーピング（Col分割/空間ギャップ/Y-bandクラスタリング）。run-stage-c-depth-recursion.py スクリプト化 | DONE |

**Note**: validate_column_consistency() は Layer 3 防御として実装済みだが、自動 postprocess パイプラインへの統合は未実施。現状は手動呼び出しで使用可能。

現在 OPEN Issue なし。新規課題は下記に追記する。
