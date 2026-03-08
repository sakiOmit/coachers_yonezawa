# Sectioning Prompt Template

## Overview

Phase 2 Stage B で Claude にセクション分割を推論させる際のプロンプトテンプレート。
SKILL.md の Phase 2 Stage B Step 2-2c から参照される。

## Prompt Template

以下のテンプレートに `{context_json}` と `{screenshot}` を埋め込んで使用する。

---

```
あなたは Figma デザインの**階層的セクション分割**アシスタントです。

以下のページの**トップレベル children**を意味的なセクションに**階層的に**分割してください。

## ページ情報

- ページ名: {page_name}
- ページID: {page_id}
- サイズ: {page_width} x {page_height}
- 子要素数: {total_children}

## 標準ページパターン

ほとんどのWebページは3層のトップレベル構造を持ちます:

1. **l-header** -- ページ上部のナビゲーションバー
2. **main-content** -- すべてのボディコンテンツを包む1つのコンテナ
3. **l-footer** -- ページ下部のフッター

main-content の中では、関連するセクションをグループ化します:
- **ヒーローエリア**: キービジュアル + パンくず + ページタイトル + リード文
- **コンテンツエリア**: セクション見出し + 詳細コンテンツ + 関連画像
- **繰り返しセクション**: メニュー行、カードグリッドなど → 1つのラッパーにまとめる
- **CTA**: コールトゥアクションは単独でもよいし、隣接コンテンツとグループ化してもよい

## トップレベル children

{children_table}

## ヒューリスティックヒント（参考）

以下はスクリプトによる推定結果です。参考にしつつ、スクリーンショットの視覚情報を優先してください。

- ヘッダー候補: {header_candidates}
- ヘッダークラスター: {header_cluster_ids}
  ※ フラット構造でヘッダーが分解されている場合、これらの要素を l-header にまとめる
- フッター候補: {footer_candidates}
- 背景画像候補: {background_candidates}
- 要素間ギャップ（px）: {gap_analysis}
  ※ 大きなギャップ（100px+）はセクション境界の可能性が高い

### 追加ヒント

- 連続類似パターン: {consecutive_patterns}
  ※ 構造が似た連続要素は1つのリスト/グリッドセクションにまとめる
- 見出し候補: {heading_candidates}
  ※ 小さくテキスト中心のフレームは、直後のコンテンツフレームとペアでグループ化する
- ルーズ要素: {loose_elements}
  ※ LINE要素や小さな装飾要素は、最も近いセクションに吸収する

## スクリーンショット

（ここにスクリーンショット画像が添付される）

## 出力形式

以下の YAML 形式で**階層的に**出力してください。**他のテキストは出力しないでください。**

### リーフセクション（子セクションなし）

```yaml
  - name: "l-header"
    description: "ヘッダー"
    node_ids: ["1:106"]
```

### コンテナセクション（子セクションあり）

```yaml
  - name: "main-content"
    description: "メインコンテンツ全体"
    subsections:
      - name: "section-hero-area"
        description: "ヒーローエリア（KV + パンくず + タイトル）"
        node_ids: ["1:102", "1:105", "1:101"]
      - name: "section-concept-area"
        description: "コンセプトエリア（見出し + 詳細 + メニュー）"
        subsections:
          - name: "section-concept-heading"
            description: "コンセプト見出し"
            node_ids: ["1:6"]
          - name: "section-concept-detail"
            description: "コンセプト詳細"
            node_ids: ["1:15", "1:16"]
```

### 完全な出力例

```yaml
sections:
  - name: "l-header"
    description: "ヘッダー（ロゴ + ナビゲーション）"
    node_ids: ["1:106"]

  - name: "main-content"
    description: "メインコンテンツ全体"
    subsections:
      - name: "section-hero-area"
        description: "ヒーローエリア（KV + 背景画像 + パンくず + タイトル + リード文）"
        node_ids: ["1:102", "1:105", "1:101", "1:5"]

      - name: "section-concept-area"
        description: "コンセプトエリア"
        subsections:
          - name: "section-concept-heading"
            description: "コンセプトセクション見出し（装飾 + タイトル）"
            node_ids: ["1:6"]
          - name: "section-concept-detail"
            description: "コンセプト詳細（テキスト + 画像 + 哲学）"
            node_ids: ["1:15", "1:16"]
          - name: "section-menu-grid"
            description: "メニューカード一覧（3列グリッド）"
            node_ids: ["1:20", "1:21", "1:22"]

      - name: "section-features"
        description: "特徴セクション（特徴 + 区切り線）"
        node_ids: ["1:30", "1:31", "1:32"]

      - name: "section-cta"
        description: "コールトゥアクション"
        node_ids: ["1:40"]

  - name: "l-footer"
    description: "フッター"
    node_ids: ["1:300"]
```

## ルール

### 基本ルール
1. **全 children を漏れなく1つのセクションに割り当てる**（余りなし、重複なし）
2. **node_ids はテーブルの ID 列をそのまま正確にコピーすること**（⚠️ 1文字でも異なるとエラーになります。ID を改変・推測・補完しないでください。出力前に全 node_ids がテーブルの ID 列に存在するか必ず照合してください）
3. **セクション名は kebab-case**:
   - ヘッダー: `l-header`
   - フッター: `l-footer`
   - メインラッパー: `main-content`
   - サブセクション: `section-{purpose}` (例: `section-hero-area`, `section-concept-detail`)
4. **description は日本語で簡潔に**

### 階層グルーピングルール
1. **main-content ラッパーを必ず作成**: l-header と l-footer 以外のすべてを main-content の中に入れる
2. **関連セクションをグループ化**:
   - セクション見出し（小さいテキスト中心のフレーム）+ そのコンテンツセクション → 1つのラッパー
   - 連続する類似構造の要素 → 1つのラッパー（例: メニュー行、カードグリッド）
   - 視覚的に同じ背景色や区切りで囲まれたエリア → 1つのラッパー
3. **ルーズ要素を吸収**: 区切り線、セパレーター、小さな装飾要素 → 最も近いセクションに吸収
4. **最大2レベルのネスト**: main-content > エリアラッパー > 個別セクション
5. **リーフセクションには node_ids、コンテナセクションには subsections**（両方同時には持たない）

### コーディングアウェアネス（Issue #223）
6. **HTMLセクション単位でグルーピング**: 各セクションが `<section class="p-section-name">` として実装されることを意識する
7. **装飾要素はコンテンツと同じセクションに含める**: 背景RECTANGLE、ドットグリッド等の装飾要素は、そのセクション内に配置される。セクション分割時に装飾要素を別セクションにしない
8. **既存の名前付きGROUPを尊重**: デザイナーが意図的に作成したGROUP（"Group 1" 等の自動名ではないもの）はそのままの単位で1つのセクションに含める。GROUPを分解して複数セクションに分散しない

### ヒント活用ルール
6. **ヒューリスティックヒントは参考**。背景画像候補やギャップ情報を活用しつつ、スクリーンショットで明らかに異なる場合は修正可
7. **連続類似パターン**のヒントがある場合、それらの要素を1つのセクションにまとめることを強く推奨
8. **見出し候補**のヒントがある場合、直後のコンテンツ要素とペアにしてサブセクションにまとめることを推奨
9. **ルーズ要素**のヒントがある場合、最も近いセクションの node_ids に含める
```

---

## Children Table Format

### Standard format (default)

`{children_table}` は以下の Markdown テーブル形式で展開する:

```
| # | ID | Name | Type | Y | W x H | Children | Unnamed | Text Preview |
|---|-----|------|------|---|-------|----------|---------|--------------|
| 1 | 1:106 | Group 46165 | FRAME | 10 | 1420x60 | 4 | Yes | - |
| 2 | 1:102 | Frame 46405 | FRAME | 162 | 808x186 | 2 | Yes | job description, 募集要項 |
```

### Enriched format (--enriched-table)

`--enriched-table` フラグ使用時は、`generate_enriched_table()` (Issue 194) で生成されるリッチ形式を使用:

```
| # | ID | Name | Type | X | Y | Col | W x H | Leaf? | ChildTypes | Flags | Text |
|---|-----|------|------|---|---|-----|-------|-------|------------|-------|------|
| 1 | 1:106 | Group 46165 | FRAME | 0 | 10 | - | 1420x60 | N | 2TEX+1VEC | - | メニュー |
| 2 | 1:101 | Rectangle 4 | RECTANGLE | 0 | 0 | - | 1440x400 | Y | - | bg-full | - |
```

追加カラムの意味:
- **X**: X座標（横並び・グリッド検出に有用）
- **Col**: 2カラムレイアウト検出時の列位置（L=左, R=右, F=全幅, C=中央, -=非2カラム）
- **Leaf?**: Y=リーフ（子なし）、N=コンテナ（背景RECTとコンテナFRAMEの区別）
- **ChildTypes**: `2REC+1TEX` 形式の子要素構成（構造パターン検出用）
  - **同じ ChildTypes が3+回連続** → カード/リストパターンの可能性大
  - **TEXT型の直後に同じ ChildTypes が複数続く** → 1:N heading-content パターン（Issue #274）
- **Flags**: `bg-full`, `overflow`, `tiny`, `decoration` 等の機械的フラグ
- **Text**: テキストプレビュー（セマンティック推論用）

`{children_table}` を enriched 形式に置き換える場合は、`sectioning-context.json` の `enriched_children_table` フィールドをそのまま使用する。

## Output YAML Schema

```yaml
# Top level
sections:
  - name: string        # kebab-case section name
    description: string  # Japanese description
    # EITHER node_ids (leaf) OR subsections (container), never both
    node_ids: [string]   # list of Figma node IDs (leaf section)
    subsections:         # nested sections (container section)
      - name: string
        description: string
        node_ids: [string]
        # Can nest one more level (max 2 levels under main-content)
        subsections:
          - name: string
            description: string
            node_ids: [string]
```

**Validation rules:**
- Every child ID from the children table must appear in exactly one leaf section's `node_ids`
- A section has EITHER `node_ids` OR `subsections`, never both
- Maximum nesting depth: 3 levels (root > main-content > area > section)
- `l-header` and `l-footer` are always at root level (not inside main-content)

## Usage in SKILL.md

```
1. prepare-sectioning-context.sh でコンテキスト JSON 生成
2. get_screenshot でページスクリーンショット取得
3. テンプレートの変数を展開:
   - {context_json} → prepare-sectioning-context.sh の出力
   - {children_table} → top_level_children を Markdown テーブルに変換
   - {header/footer/background_candidates, gap_analysis} → heuristic_hints から展開
   - {consecutive_patterns, heading_candidates, loose_elements} → heuristic_hints から展開
4. Claude に送信（テキスト + スクリーンショット画像）
5. YAML レスポンスをパース → sectioning-plan.yaml に保存
6. Validate: 全 node_ids の合計が total_children と一致すること
```

## Fallback

- スクリーンショット取得失敗時: テキストのみでプロンプト送信（精度低下を警告）
- Claude レスポンスパース失敗時: Stage B スキップ → Stage A のみで進行
- node_ids の合計が total_children と不一致: 警告表示 + ユーザー確認
- subsections パース失敗時: フラットな sections として扱う（後方互換）

## Migration from Flat to Hierarchical

既存のフラットな sectioning-plan.yaml との後方互換性を維持:

- `subsections` キーがない sections はリーフセクション（従来と同じ）
- apply-grouping.js は `subsections` を再帰的に処理する必要がある（別タスク）
- フラットな出力もバリデーション合格として扱う
