# Grouping Fallback Prompt Template

## Overview

Phase 2 Stage C 後の LLM フォールバックで、1:N heading-content グルーピングが不足しているセクションに対して Claude にグルーピング修正を推論させる際のプロンプトテンプレート。

既存の `rename-fallback-prompt-template.md`（リネーム LLM フォールバック）とは異なり:
- 個別ノードの命名ではなく**セクション内のグルーピング修正**に特化
- heading→複数コンテンツのパターン認識
- ルース（未グループ化）ノードの構造ハッシュ類似性を活用
- Haiku で十分な精度を想定

Issue #274: 1:N heading-content grouping via LLM fallback intervention.

## Prompt Template

以下のテンプレートに変数を埋め込んで使用する。

---

```
You are a Figma design grouping assistant for web development.

Stage C grouping analyzed {section_count} sections but left some items ungrouped. Your task is to identify heading→multiple-content patterns and propose grouping corrections.

## Target Patterns

### 1:N Heading-Content Pattern (Primary Target)
A heading-like node (TEXT type or small text-heavy FRAME, marked with [H]) followed by multiple siblings with similar structure:
→ Group the heading + all related content items together

Example:
- "気候変動対策" (heading, TEXT) → parent of:
  - 太陽光パネル設置 (FRAME, card-like)
  - 省エネ活動 (FRAME, card-like)
  - 資源リサイクル (FRAME, card-like)
→ All 4 items form one "climate-action-area" group with pattern "heading-content"

### List/Card Pattern
3+ consecutive nodes with the same StructHash (structure hash):
→ Group as a list or card collection

### Background-Content Separation
A single full-width RECTANGLE + remaining content nodes:
→ Separate into bg-layer and content-layer

## How to Read the Tables

### StructHash Column
- Format: `TYPE:[CHILD_TYPE1,CHILD_TYPE2,...]` or `TYPE:[...]|GC:N:DOMINANT`
- **Same hash = same internal structure** → these are likely list items
- `[H]` suffix = heading candidate (text-heavy, small height)

### ChildTypes Column
- Format: `2TEX+1REC` = 2 TEXT + 1 RECTANGLE children
- Helps identify card-like structures (IMAGE + TEXT combos)

## Sections

{sections_detail}

## Output Format

Output YAML only. **No other text.**

```yaml
corrections:
  - section_id: "2:8320"
    groups:
      - name: "climate-action-area"
        pattern: "heading-content"
        heading_id: "2:8321"
        node_ids: ["2:8321", "2:8322", "2:8323", "2:8324"]
        reason: "見出し '気候変動対策' + 3つの活動アイテム"
        confidence: 高
      - name: "activity-list"
        pattern: "list"
        node_ids: ["2:8325", "2:8326", "2:8327"]
        reason: "同一StructHashの3連続アイテム"
        confidence: 高
```

## Rules

1. **node_ids must exactly match the table's ID column** — do not modify, guess, or invent IDs
2. **Include heading node in node_ids** — the heading is part of the group
3. **Do NOT overlap with existing groups** — only use loose (ungrouped) node IDs
4. **name must be kebab-case** (e.g., `climate-action-area`, `feature-list`)
5. **pattern must be one of**: `heading-content`, `list`, `card`, `bg-content`
6. **confidence**: 高 (high, very certain), 中 (medium, likely correct), 低 (low, uncertain)
7. **reason**: single-line Japanese explanation of the grouping logic
8. **heading_id is optional** — only for heading-content pattern
9. **Verify all node_ids before output** — every ID must exist in the table
10. **Do NOT create single-item groups** — minimum 2 nodes per group
```

---

## Variables

| 変数 | 値の取得元 |
|------|-----------|
| `{section_count}` | 対象セクション数（undergrouped セクションのフィルタ後） |
| `{sections_detail}` | 以下の Section Detail Format で生成したセクション情報 |

## Section Detail Format

各セクションは以下の形式で展開する:

```
### Section: section-name (`section_id`)

- Total children: N
- Loose (ungrouped): M
- Heading candidates: `id1`, `id2`

**Existing groups:**
  - group-name (pattern, N nodes)

**Similar structure runs (potential list items):**
  - 5 items with hash `FRAME:[TEXT,RECTANGLE]`: `id1`, `id2`, `id3`, `id4`, `id5`

**Loose nodes:**

| # | ID | Type | Size | Children | ChildTypes | Text | StructHash |
|----|-----|------|------|----------|------------|------|------------|
| 1 | 2:8320 | TEXT | 200x24 | 0 | - | 気候変動対策 | TEXT [H] |
| 2 | 2:8321 | FRAME | 320x400 | 3 | 1IMG+2TEX | 太陽光パネル | FRAME:[IMAGE,TEXT,TEXT] |
```

## Output YAML Schema

```yaml
corrections:
  - section_id: string      # Section ID from the input
    groups:
      - name: string         # kebab-case group name
        pattern: string       # heading-content | list | card | bg-content
        heading_id: string    # Optional: heading node ID (for heading-content)
        node_ids: [string]    # All node IDs in the group (including heading)
        reason: string        # 1-line Japanese explanation
        confidence: string    # 高 | 中 | 低
```

**Validation rules:**
- Every `node_id` in the output must exist in the input section's loose nodes table
- `node_ids` must not overlap with any existing group's node_ids
- Each group must have at least 2 node_ids
- `name` must be kebab-case (regex: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`)
- `pattern` must be one of: `heading-content`, `list`, `card`, `bg-content`

## Cost Model

- Model: Haiku（パターン認識 + 構造推論タスク）
- 入力: ~500-2000 tokens（undergrouped セクションのテーブル + コンテキスト）
- 出力: ~200-800 tokens（YAML 形式のグルーピング修正）
- 1バッチあたり: ~$0.002-0.005

## Usage

```
1. Phase 2 Stage C 完了後
2. collect_undergrouped_sections() で候補セクション抽出
3. build_grouping_fallback_context() でコンテキスト構築
4. format_grouping_fallback_prompt() でプロンプト生成
5. Claude に送信（テキストのみ、スクリーンショット不要）
6. YAML レスポンスをパース → parse_llm_grouping_suggestions()
7. merge_grouping_suggestions() で nested-grouping-plan に統合
8. Validate: 全 node_ids が既存グループと重複しないこと
```

## Fallback

- Claude レスポンスパース失敗時: 修正なし（Stage C 結果をそのまま維持）
- node_ids 重複検出時: 該当グループを無視
- undergrouped セクションなし: LLM フォールバック不要（スキップ）
