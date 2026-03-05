# Nested Grouping Prompt Template

## Overview

Phase B のネストレベル（セクション内部）で Claude にグルーピングを推論させる際のプロンプトテンプレート。
Issue 194: Phase B Claude推論のネストレベル拡張

ルートレベルの `sectioning-prompt-template.md` とは異なり:
- セクション内部の要素を対象とする
- header/footer検出は不要
- パターン認識（カード、テーブル行、背景+コンテンツ等）に特化
- Haiku で十分な精度を想定

## Prompt Template

以下のテンプレートに変数を埋め込んで使用する。

---

```
あなたは Figma デザインの**セクション内部構造分析**アシスタントです。

以下のセクション内の要素を、意味的なグループに分類してください。

## セクション情報

- セクション名: {section_name}
- セクションID: {section_id}
- サイズ: {section_width} x {section_height}
- 子要素数: {total_children}

## 子要素テーブル

{enriched_children_table}

## 認識すべきパターン

以下のパターンを検出し、グループ化してください:

### 1. カードパターン
- 同じ構造（ChildTypes）の要素が3つ以上並んでいる
- 典型的: IMAGE(RECTANGLE) + TEXT群(FRAME) のペアが繰り返される
- X座標が等間隔で並ぶ場合、横並びカード

### 2. テーブル行パターン
- 同じY帯に複数の要素が水平に並ぶ
- 各行の構造が類似している（RECTANGLE + TEXT の繰り返し）
- 行間が等間隔

### 3. 背景 + コンテンツ分離
- Leaf? = Y かつ Flags に bg-full/bg-wide がある要素 → 背景レイヤー
- 同じ座標範囲に重なる他の要素 → そのコンテンツ
- 背景はグループの最背面要素として扱う

### 4. 見出し + コンテンツペア
- EN見出し（大文字ASCII短テキスト）+ JP見出し（日本語）が近接
- 直後に関連コンテンツが続く

### 5. 装飾・ルーズ要素
- Flags に tiny/decoration がある要素 → 最も近いグループに吸収
- LINE型要素や区切り線 → 隣接するグループに吸収

### 6. ボタン・CTA
- INSTANCE型で小さい要素 → 直前のコンテンツグループに含める
- 「arrow」のような小INSTANCEは装飾

## 出力形式

以下の YAML 形式で出力してください。**他のテキストは出力しないでください。**

```yaml
groups:
  - name: "group-name"
    description: "グループの説明"
    pattern: "card|table|bg-content|heading-pair|list|single"
    node_ids: ["2:8320", "2:8321"]
    notes: "任意のメモ（省略可）"
```

## ルール

1. **全要素を漏れなく1つのグループに割り当てる**（余りなし、重複なし）
2. **node_ids はテーブルの ID 列をそのまま正確にコピーすること**（⚠️ 1文字でも異なるとエラーになります。テーブルの ID を改変・推測・補完しないでください）
3. **name は kebab-case** (例: blog-card-1, recruit-heading, bg-layer)
4. **pattern は検出したパターン種別**: card, table, bg-content, heading-pair, list, single
5. **single はどのパターンにも属さない単独要素**
6. **Flags を積極的に活用**: bg-full → 背景、tiny → 装飾、off-canvas → 除外候補
7. **ChildTypes の類似性でカード/リスト検出**: 同じ ChildTypes が3回以上 → カード/リストパターン
8. **ID の正確性を最終確認**: 出力前に、全 node_ids がテーブルの ID 列に存在するか照合すること
```

---

## Variables

| 変数 | 値の取得元 |
|------|-----------|
| `{section_name}` | セクション名（sectioning-plan.yaml から） |
| `{section_id}` | セクションの Figma node ID |
| `{section_width}` | セクションの幅 |
| `{section_height}` | セクションの高さ |
| `{total_children}` | セクション内の子要素数 |
| `{enriched_children_table}` | `generate_enriched_table()` の出力 |

## Output YAML Schema

```yaml
groups:
  - name: string         # kebab-case group name
    description: string   # Japanese description
    pattern: string       # card|table|bg-content|heading-pair|list|single
    node_ids: [string]    # list of Figma node IDs
    notes: string         # optional notes (omit if not needed)
```

**Validation rules:**
- Every child ID from the enriched table must appear in exactly one group's `node_ids`
- `pattern` must be one of: card, table, bg-content, heading-pair, list, single
- Groups are flat (no nesting within nested prompt)

## Cost Model

- Model: Haiku (十分な精度が期待できる定型パターン認識タスク)
- 入力: ~500-1500 tokens (セクション内要素10-30個のテーブル)
- 出力: ~200-500 tokens (YAML形式のグルーピング結果)
- 1セクションあたり: ~$0.001-0.003

## Validation

結果の検証方法:
1. 全 node_ids の合計が total_children と一致すること
2. 各 group の node_ids がテーブル内の ID と一致すること
3. pattern フィールドが許可値のいずれかであること
