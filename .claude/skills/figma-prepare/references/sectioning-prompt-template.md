# Sectioning Prompt Template

## Overview

Phase 3 Stage B で Claude にセクション分割を推論させる際のプロンプトテンプレート。
SKILL.md の Phase 3 Stage B Step 3-2c から参照される。

## Prompt Template

以下のテンプレートに `{context_json}` と `{screenshot}` を埋め込んで使用する。

---

```
あなたは Figma デザインのセクション分割アシスタントです。

以下のページの**トップレベル children**を意味的なセクションに分割してください。

## ページ情報

- ページ名: {page_name}
- ページID: {page_id}
- サイズ: {page_width} x {page_height}
- 子要素数: {total_children}

## トップレベル children

{children_table}

## ヒューリスティックヒント（参考）

以下はスクリプトによる推定結果です。参考にしつつ、スクリーンショットの視覚情報を優先してください。

- ヘッダー候補: {header_candidates}
- フッター候補: {footer_candidates}
- 背景画像候補: {background_candidates}
- 要素間ギャップ（px）: {gap_analysis}
  ※ 大きなギャップはセクション境界の可能性あり

## スクリーンショット

（ここにスクリーンショット画像が添付される）

## 出力形式

以下の YAML 形式で出力してください。**他のテキストは出力しないでください。**

```yaml
sections:
  - name: "l-header"
    description: "ヘッダー"
    node_ids: ["1:106"]

  - name: "section-page-kv"
    description: "ページキービジュアル（見出し+パンくず+装飾画像+リード文）"
    node_ids: ["1:102", "1:105", "1:101", "1:5"]

  - name: "section-xxx"
    description: "セクションの説明"
    node_ids: ["1:6", "1:15"]

  - name: "l-footer"
    description: "フッター"
    node_ids: ["1:300"]
```

## ルール

1. **全 children を漏れなく1つのセクションに割り当てる**（余りなし）
2. **node_ids はページ情報の id をそのまま使用**（新規 ID を作らない）
3. **セクション名は kebab-case**:
   - ヘッダー: `l-header`
   - フッター: `l-footer`
   - KV: `section-page-kv`
   - その他: `section-{purpose}` (例: `section-job-listing`, `section-about`)
4. **ヒューリスティックヒントは参考**。背景画像候補やギャップ情報を活用しつつ、スクリーンショットで明らかに異なる場合は修正可
5. **隣接する関連要素はまとめる**:
   - パンくず + 見出しフレーム + 背景画像 + リード文 → `section-page-kv`
   - タブUI + カード一覧 → `section-job-listing`
6. **description は日本語で簡潔に**
```

---

## Children Table Format

`{children_table}` は以下の Markdown テーブル形式で展開する:

```
| # | ID | Name | Type | Y | W x H | Children | Unnamed | Text Preview |
|---|-----|------|------|---|-------|----------|---------|--------------|
| 1 | 1:106 | Group 46165 | FRAME | 10 | 1420x60 | 4 | Yes | - |
| 2 | 1:102 | Frame 46405 | FRAME | 162 | 808x186 | 2 | Yes | job description, 募集要項 |
```

## Usage in SKILL.md

```
1. prepare-sectioning-context.sh でコンテキスト JSON 生成
2. get_screenshot でページスクリーンショット取得
3. テンプレートの変数を展開:
   - {context_json} → prepare-sectioning-context.sh の出力
   - {children_table} → top_level_children を Markdown テーブルに変換
   - {header/footer/background_candidates, gap_analysis} → heuristic_hints から展開
4. Claude に送信（テキスト + スクリーンショット画像）
5. YAML レスポンスをパース → sectioning-plan.yaml に保存
```

## Fallback

- スクリーンショット取得失敗時: テキストのみでプロンプト送信（精度低下を警告）
- Claude レスポンスパース失敗時: Stage B スキップ → Stage A のみで進行
- node_ids の合計が total_children と不一致: 警告表示 + ユーザー確認
