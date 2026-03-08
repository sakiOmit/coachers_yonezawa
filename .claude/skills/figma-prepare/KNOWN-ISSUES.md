# /figma-prepare OPEN Issues

FIXED 済みの課題は削除済み（コード・ルールに反映済み）。

| # | Phase | 概要 | Status |
|---|-------|------|--------|
| 250 | 2 | generate-nested-grouping-context.sh GROUPS mode line 206 hiddenフィルタ欠如 | DONE |
| 251 | 2 | detect_wrap() 丸め(round)による偽WRAP検出 → 距離ベースグルーピングに修正 | DONE |
| 252 | 2 | generate-nested-grouping-context.sh JSON解析エラーハンドリング + node_ids型検証 | DONE |
| 253 | 2 | Stage C divider単一要素グループを隣接list-itemグループに吸収（border-bottom解釈対応） | DONE |

| 254 | - | list-item内部構造の不整合＋リンク判定 → figma-implement側で対処（nested-grouping-plan.yaml読み込み+Claude総合推論） | figma-implement #1 に移管 |
| 255 | 2 | Stage C再帰: pattern="single"でも children>=3 なら depth 1 処理すべき（icon+title+description のcontent-block未検出） | DONE |
| 256 | 2 | Stage C左右カラムのクロス混入防止 — enriched tableにCol列追加+プロンプト制約+後検証 | DONE |

## Issue 255: Stage C 再帰条件の緩和 — content-block 粒度のグルーピング

### 現象

CSR ページの env-row-power（pattern: "single", children 4: icon + title + description + divider）が
Stage C 再帰処理でスキップされ、内部の icon+title+description が content-block として
グルーピングされない。

同様に env-row-solar（pattern: "two-column"）は再帰条件を満たすが、
depth 1 で右カラムの icon+title+description が sub-group 化されていない。

### 原因

SKILL.md 2-3e の再帰条件:
```
non_single_groups = [g for g in current_groups if g.pattern != "single"]
```
pattern="single" のグループは children 数に関わらず再帰スキップ。

### 修正方針

再帰条件を緩和:
```
# 旧: pattern != "single" のみ
non_single_groups = [g for g in current_groups if g.pattern != "single"]

# 新: pattern != "single" OR children >= 3
recursion_targets = [
    g for g in current_groups
    if g.pattern != "single" or len(g.node_ids) >= 3
]
```

children >= 3 の理由: icon + title + description の最小構成が 3 要素。
2 要素以下は再帰しても分割の余地がない。

### 影響範囲

- SKILL.md 2-3e の再帰ループ条件
- generate-nested-grouping-context.sh の --groups モード (pattern=="single" スキップを緩和)
- Stage C プロンプトに content-block パターン認識の追加

現在 OPEN Issue なし（#255 を除く）。新規課題は下記に追記する。
