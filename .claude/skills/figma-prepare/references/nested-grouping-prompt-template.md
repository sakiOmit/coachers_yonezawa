# Nested Grouping Prompt Template

## Overview

Phase B のネストレベル（セクション内部）で Claude にグルーピングを推論させる際のプロンプトテンプレート。
Issue 194: Phase B Claude推論のネストレベル拡張
Issue #223: コーディングアウェアネス追加

ルートレベルの `sectioning-prompt-template.md` とは異なり:
- セクション内部の要素を対象とする
- header/footer検出は不要
- パターン認識（カード、テーブル行、背景+コンテンツ等）に特化
- **HTML/CSS実装を意識したグルーピング**を行う
- Haiku で十分な精度を想定

## Prompt Template

以下のテンプレートに変数を埋め込んで使用する。

---

```
あなたは Figma デザインの**セクション内部構造分析**アシスタントです。

以下のセクション内の要素を、**HTML/CSSコーディングを意識して**意味的なグループに分類してください。

## コーディングアウェアネス（最重要）

グルーピングの目的は、**このデザインをHTMLに変換する際のDOM構造を先取りする**ことです。
以下の視点で判断してください:

1. **「このグループは1つのdiv/sectionとしてコーディングするか？」** → Yes なら1グループ
2. **「CSSのflexbox/gridで横並びにする要素か？」** → 横並び要素は同じグループ
3. **「装飾（背景、ドット、区切り線）は別レイヤーか？」** → 装飾は分離してグループ化
4. **「既存のGROUPノードは、デザイナーが意図的にまとめたもの」** → 既存GROUPの内部構造は尊重し、分解しない

## セクション情報

- セクション名: {section_name}
- セクションID: {section_id}
- サイズ: {section_width} x {section_height}
- 子要素数: {total_children}

## 子要素テーブル

{enriched_children_table}

## 認識すべきパターン（優先度順）

### 1. 2カラムレイアウト（★ Issue #223 + #256）
- テキスト要素群（TEXT, FRAME with text）が片側に集中し、画像（RECTANGLE, IMAGE, GROUP with image）がもう片側にある
- **Col 列を使って判定**: `L` = 左カラム、`R` = 右カラム、`F` = 全幅（divider等）、`C` = 中央/跨ぎ
- **⚠️ Col が異なる要素（L と R）を同一グループに混ぜないこと**（Issue #256）
- 同じ Y 座標帯にあっても、Col=L と Col=R は別グループにする
- → 左カラム要素を1グループ、右カラム要素を1グループとしてグルーピング
- Col=F の全幅要素（divider, 背景）は独立グループか最も近いグループに吸収
- **CSS実装: `display: flex` で2カラムレイアウトになる**
- 例: About セクションで「タイトル + 説明文 + サブテキスト」(Col=L) が左、「メイン画像」(Col=R) が右

### 2. カードパターン（リピーティングコンポーネント）
- 同じ構造（ChildTypes）の FRAME/GROUP/INSTANCE が3つ以上並んでいる
- 各カードは「画像 + テキスト」や「アイコン + テキスト + ボタン」等の内部構造を持つ
- X座標が等間隔 → 横並びカード（`display: flex` / `grid`）
- Y座標が等間隔 → 縦並びカード
- **重要**: テキスト+画像の「ペア」を1つのカードとして認識する。テキストだけ、画像だけでグルーピングしない
- **CSS実装: `.card` コンポーネント × N 個のリスト**

### 3. 装飾パターン分離（★ 強化 Issue #223）
- 装飾要素は**コンテンツと分離してグルーピング**する:
  - ドットグリッド（Dot Grid等の名前付きFRAME、小さいELLIPSE/RECTANGLE群）→ `decoration` パターン
  - 背景RECTANGLE（bg-full/bg-wide フラグ）→ `bg-content` パターン
  - 区切り線（細いLINE/RECTANGLE）→ 最も近いコンテンツグループに吸収
- **CSS実装: `position: absolute` で配置する装飾は、コンテンツの`div`とは別要素**
- 装飾をコンテンツグループに混ぜない。ただし区切り線(divider)のような小さい要素は隣接グループに吸収してよい

### 4. テーブル行パターン
- 同じY帯に複数の要素が水平に並ぶ
- 各行の構造が類似している（RECTANGLE + TEXT の繰り返し）
- 行間が等間隔

### 5. 背景 + コンテンツ分離
- Leaf? = Y かつ Flags に bg-full/bg-wide がある要素 → 背景レイヤー
- 同じ座標範囲に重なる他の要素 → そのコンテンツ
- 背景はグループの最背面要素として扱う

### 6. 見出し + コンテンツペア
- EN見出し（大文字ASCII短テキスト）+ JP見出し（日本語）が近接
- 直後に関連コンテンツが続く

### 6b. トピック + 活動セット（★ Issue #258）
- **見出し/トピック要素**の直後に、関連する**複数の活動/詳細要素**が縦に続くパターン
- 例: 「気候変動対策」(トピック見出し) → 「太陽光パネル設置」(活動1) → 「発電結果の共有」(活動2)
- これらは**1つのセットとしてグルーピング**する（トピック + 全活動を同一グループ）
- Y座標が連続し、dividerで区切られた範囲内の要素を1セットとする
- **CSS実装: 1つの `<section>` or `<div>` としてコーディングされる単位**
- ⚠️ トピックと活動を別々のグループにしない。トピック単独グループ + 活動単独グループではなく、セットで1グループ

### 7. ボタン・CTA
- INSTANCE型で小さい要素 → 直前のコンテンツグループに含める
- 「arrow」のような小INSTANCEは装飾

### 8. 既存GROUP保護（★ 新規 Issue #221）
- type = GROUP で意味のある名前（Group 1, Group 2等の自動名ではないもの）→ **そのまま single として出力**
- 既存GROUPの内部を分解・再構築しない
- 自動名のGROUP（Group 1等）は通常通りパターン分析の対象

## 出力形式

以下の YAML 形式で出力してください。**他のテキストは出力しないでください。**

```yaml
groups:
  - name: "group-name"
    description: "グループの説明"
    pattern: "two-column|card|table|bg-content|heading-pair|decoration|list|single"
    node_ids: ["2:8320", "2:8321"]
    notes: "任意のメモ（省略可）"
```

## ルール

1. **全要素を漏れなく1つのグループに割り当てる**（余りなし、重複なし）
2. **node_ids はテーブルの ID 列をそのまま正確にコピーすること**（⚠️ 1文字でも異なるとエラーになります。テーブルの ID を改変・推測・補完しないでください）
3. **name は kebab-case** (例: text-column, image-column, feature-cards, dot-decoration)
4. **pattern は検出したパターン種別**: two-column, card, table, bg-content, heading-pair, decoration, list, single
5. **single はどのパターンにも属さない単独要素、または既存の名前付きGROUP**
6. **Flags を積極的に活用**: bg-full → 背景、tiny → 装飾、off-canvas → 除外候補
7. **ChildTypes の類似性でカード/リスト検出**: 同じ ChildTypes が3回以上 → カード/リストパターン
8. **ID の正確性を最終確認**: 出力前に、全 node_ids がテーブルの ID 列に存在するか照合すること
9. **コーディングを意識**: グルーピングの結果がHTML/CSSの構造として自然かを常に確認
10. **過剰グルーピングしない**: グルーピングしても実装上のメリットがなければ single のまま残す
11. **Col 列の制約（Issue #256）**: Col=L の要素と Col=R の要素を同一グループに混ぜない。同じ Y 帯でも左右カラムは別グループにする
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
    pattern: string       # two-column|card|table|bg-content|heading-pair|decoration|list|single
    node_ids: [string]    # list of Figma node IDs
    notes: string         # optional notes (omit if not needed)
```

**Validation rules:**
- Every child ID from the enriched table must appear in exactly one group's `node_ids`
- `pattern` must be one of: two-column, card, table, bg-content, heading-pair, decoration, list, single
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
