# Rename Fallback Prompt Template

## Overview

Phase 3 リネームで、ヒューリスティック判定が低信頼度だったノードに対して Claude にセマンティック名を推論させる際のプロンプトテンプレート。
ヒューリスティックリネーム（ポジション分析、シェイプ分析、テキスト内容ベース等）で confidence が低かったノードのみを対象とする。

既存の `nested-grouping-prompt-template.md`（グルーピング推論）とは異なり:
- グルーピングではなく**個別ノードの命名**に特化
- 兄弟コンテキストを活用したパターン認識
- **HTML/CSSクラス名を意識したセマンティック命名**を行う
- Haiku で十分な精度を想定

## Prompt Template

以下のテンプレートに変数を埋め込んで使用する。

---

```
You are a Figma layer naming assistant for web development.

The heuristic rename system analyzed {node_count} layer nodes but produced low-confidence results. Your task is to assign semantic names that reflect each node's UI role in an HTML/CSS implementation.

## Coding Awareness (Top Priority)

The purpose of renaming is to **prepare Figma layers for HTML/CSS implementation**. For each node, think:

1. **"What HTML element or CSS class would this become?"** — e.g., `<header>`, `<nav>`, `.c-card`, `.p-hero__image`
2. **"If siblings have similar structure, they are likely list items"** — name them `card-*`, `list-item-*`, `feature-*`
3. **"Large full-width elements at the top of the page"** — likely `hero`, `header`, `kv` (key visual)
4. **"Large full-width elements at the bottom"** — likely `footer`, `cta`
5. **"Small elements with no text children"** — likely `icon-*`, `decoration-*`, `divider`
6. **"Full-width thin rectangles"** — likely `divider`, `separator`
7. **"Elements containing both image and text children"** — likely `card-*`, `banner-*`
8. **"Narrow tall elements at page edges"** — likely `side-panel-*`

## Node Table

The following table shows nodes that need better names. The "Heuristic" column shows the current best guess and its confidence score.

{node_table}

## Naming Conventions

### Required format
- **kebab-case only** (lowercase, hyphens) — no spaces, no camelCase, no underscores
- Pattern: `{prefix}-{slug}` where slug is derived from content or role

### Standard prefixes (use these)

| Prefix | Usage | Example |
|--------|-------|---------|
| section- | Major page section | section-about, section-features |
| card- | Repeated content card | card-feature, card-member |
| heading- | Section/subsection heading | heading-about, heading-main |
| body- | Body/description text block | body-intro, body-description |
| btn- | Button or CTA element | btn-primary, btn-contact |
| nav- | Navigation element | nav-main, nav-footer |
| img- | Image or photo element | img-hero, img-avatar |
| icon- | Small icon (48px or less) | icon-arrow, icon-check |
| bg- | Background element | bg-hero, bg-section |
| container- | Wrapper/container frame | container-main, container-narrow |
| list- | List container | list-features, list-members |
| list-item- | Individual list item | list-item-feature |
| form- | Form element | form-contact, form-search |
| divider | Horizontal separator line | divider |
| label- | Short label text | label-category, label-tag |
| hero- | Hero/key visual area | hero-image, hero-bg |
| feature- | Feature item in a list | feature-solar, feature-wind |
| en-label- | English label text (uppercase ASCII) | en-label-about, en-label-company |
| decoration- | Decorative pattern (dots, shapes) | decoration-dots-0, decoration-pattern-0 |
| highlight- | Highlighted text with background | highlight-key-text |
| cta- | Call-to-action element | cta-contact |
| side-panel- | Narrow side panel | side-panel-0 |

### Slug derivation rules
- **Japanese text content** — translate/romanize the key concept: "お問い合わせ" -> `contact`, "会社概要" -> `company-overview`
- **English text content** — use as-is in kebab-case: "ABOUT US" -> `about-us`
- **No text content** — derive from visual role + position: `bg-top`, `icon-0`, `divider`
- **Similar siblings** — use a shared prefix + distinguishing slug: `card-solar`, `card-wind`, `card-hydro`

### Sibling context for pattern detection
- **3+ siblings with similar ChildTypes** — they are list items. Name them with a shared prefix
- **Sibling with same size/type** — likely a repeated pattern element
- **One element much larger than siblings** — likely a background or hero image

## Output Format

Output YAML only. **No other text.**

```yaml
renames:
  - node_id: "2:8320"
    new_name: "heading-about"
    reason: "TEXT node containing 'ABOUTセクション', used as section heading"
  - node_id: "2:8321"
    new_name: "card-feature-solar"
    reason: "FRAME with IMAGE+TEXT children, similar to 2 siblings, part of feature card list"
```

## Rules

1. **Use the node ID exactly as shown in the table** — do not modify, guess, or truncate IDs
2. **Names must be kebab-case** — no spaces, no camelCase, no underscores, no uppercase
3. **Reason must be a single line** explaining the inference logic
4. **Do NOT rename nodes where the heuristic confidence is >= 50%** — those are already acceptable. Only rename low-confidence nodes
5. **Use the Text column** — if the node or its children contain meaningful text, use it for the slug
6. **Use the Siblings column** — if siblings have similar structure, assign consistent naming (shared prefix)
7. **Use the ChildTypes column** — it reveals internal structure (e.g., `2TEX+1REC` suggests a card with text and image)
8. **Prefer specific names over generic ones** — `card-solar-energy` is better than `frame-0`
9. **Verify all node_ids before output** — every `node_id` in your response must exist in the table's ID column
10. **Do not invent new prefixes** — use the standard prefixes listed above
```

---

## Variables

| 変数 | 値の取得元 |
|------|-----------|
| `{node_count}` | 対象ノード数（低信頼度ノードのフィルタ後） |
| `{node_table}` | 以下の Node Table Format で生成したテーブル |

## Node Table Format

`{node_table}` は以下の Markdown テーブル形式で展開する:

```
| # | ID | Type | Size | Children | ChildTypes | Text | Heuristic (confidence%) | Siblings |
|---|-----|------|------|----------|------------|------|------------------------|----------|
| 1 | 2:8320 | TEXT | 200x24 | 0 | - | ABOUTセクション | frame-0 (15%) | 2:8321, 2:8322 (similar FRAME) |
| 2 | 2:8321 | FRAME | 320x400 | 3 | 1IMG+2TEX | 太陽光発電 | frame-1 (20%) | 2:8320, 2:8322 (similar FRAME) |
| 3 | 2:8322 | RECTANGLE | 1440x2 | 0 | - | - | rectangle-0 (10%) | 2:8320, 2:8321 |
```

カラムの意味:
- **#**: 連番
- **ID**: Figma node ID（出力時にそのまま使用）
- **Type**: ノードタイプ（FRAME, TEXT, RECTANGLE, ELLIPSE, GROUP, INSTANCE, VECTOR, LINE, IMAGE）
- **Size**: `W x H` (px)
- **Children**: 直下子要素数（0 = リーフノード）
- **ChildTypes**: `2TEX+1REC` 形式の子要素構成（リーフは `-`）
- **Text**: テキストプレビュー（TEXT ノードは自身のテキスト、コンテナは子テキストの集約）
- **Heuristic (confidence%)**: ヒューリスティックが付けた仮名と信頼度
- **Siblings**: 同階層の兄弟ノード ID + 類似パターン情報

## Output YAML Schema

```yaml
renames:
  - node_id: string      # Figma node ID (must match table ID exactly)
    new_name: string      # kebab-case semantic name
    reason: string        # 1-line explanation of inference logic
```

**Validation rules:**
- Every `node_id` in the output must exist in the input table's ID column
- `new_name` must be kebab-case (regex: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`)
- `reason` must be a non-empty single line
- Nodes with heuristic confidence >= 50% should NOT appear in output (already acceptable)

## Cost Model

- Model: Haiku（定型パターン認識 + テキスト推論タスク）
- 入力: ~300-1000 tokens（低信頼度ノード 5-20 個のテーブル）
- 出力: ~100-400 tokens（YAML 形式のリネーム結果）
- 1バッチあたり: ~$0.001-0.002

## Usage

```
1. Phase 3 ヒューリスティックリネーム実行（generate-rename-map.sh）
2. 信頼度 < 50% のノードを抽出
3. 兄弟コンテキスト情報を収集（同階層ノードの type/size/childTypes）
4. テンプレートの変数を展開:
   - {node_count} → 低信頼度ノード数
   - {node_table} → 対象ノードの Markdown テーブル
5. Claude に送信（テキストのみ、スクリーンショット不要）
6. YAML レスポンスをパース → rename-map に統合
7. Validate: 全 node_id が入力テーブルに存在すること
```

## Fallback

- Claude レスポンスパース失敗時: ヒューリスティック名をそのまま採用（リネームスキップ）
- node_id 不一致検出時: 該当エントリを無視し、ヒューリスティック名を維持
- 全ノード confidence >= 50%: LLM フォールバック不要（スキップ）
