---
name: figma-analyze
description: "Analyze multiple Figma page URLs to detect shared components, determine split strategies, and plan implementation order. Use when user provides multiple Figma URLs, says 'analyze', '分析', 'compare pages', or wants pre-implementation planning."
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - mcp__figma__get_metadata
  - mcp__figma__get_variable_defs
context: fork
agent: general-purpose
---

# Figma Analyze

## Overview

複数ページのFigma URLを受け取り、コンポーネント共通化・ページ分割戦略・実装順序を決定する分析スキル。
`/figma-implement` の前段フェーズとして使用し、効率的な実装計画を立てる。

### Key Features

- **複数ページ横断分析**: ページ間で共通するコンポーネントを自動検出
- **複雑度ベース戦略判定**: セクションごとに NORMAL / SPLIT / SPLIT_REQUIRED を判定
- **カタログマッチング**: 既存コンポーネントとの再利用可能性をスコアリング
- **実装順序最適化**: 依存関係と共通コンポーネントに基づく最適な実装順序

## Usage

```
/figma-analyze {url1} [url2] [url3] ...
```

### Options

```
/figma-analyze {urls} [options]

Options:
  --tokens              Include design token extraction (Phase 5)
  --output {path}       Custom output path (default: .claude/cache/figma/analysis-report.yaml)
```

### Examples

```bash
# 複数ページ分析
/figma-analyze \
  https://figma.com/design/abc/t?node-id=1-2 \
  https://figma.com/design/abc/t?node-id=3-4 \
  https://figma.com/design/abc/t?node-id=5-6

# 単一ページ分析（分割戦略のみ）
/figma-analyze https://figma.com/design/abc/t?node-id=1-2

# デザイントークン取得を含む
/figma-analyze https://figma.com/design/abc/t?node-id=1-2 --tokens
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| urls | Yes | 1つ以上のFigma URL（スペース区切り） |
| --tokens | No | Phase 5 デザイントークン取得を実行 |
| --output | No | レポート出力先パス |

## Explicit Restrictions

### 禁止事項（厳守）

| 禁止項目 | 理由 | 代替手段 |
|---------|------|---------|
| `get_screenshot` を実装データ源として使用 | nodeデータなし、構造把握不可 | `get_metadata` + セクション分割 |
| `get_code_connect_map` の呼び出し | Enterprise/Team プラン限定 | `component-catalog.yaml` で管理 |
| `add_code_connect_map` の呼び出し | Enterprise/Team プラン限定 | `component-catalog.yaml` を更新 |
| サイズオーバー時のスクリーンショットフォールバック | 実装精度低下 | メタデータ + セクション分割で対処 |

## Processing Flow

```
Phase 1: URL解析 + カタログ読込
        │
        ▼
Phase 2: ページ別 get_metadata → 複雑度 → 戦略判定
        │
        ▼
Phase 3: ページ横断 共通コンポーネント検出
        │
        ▼
Phase 4: カタログマッチング
        │
        ▼
Phase 5: デザイントークン取得 (--tokens 指定時)
        │
        ▼
Phase 6: 実装順序決定
        │
        ▼
Phase 7: レポート生成 + コンソールサマリー
```

## Phase 1: URL解析 + カタログ読込

### 1-1. URL パース

各URLから `fileKey` と `nodeId` を抽出:

```
Input:  https://figma.com/design/{fileKey}/{fileName}?node-id={int1}-{int2}
Output: fileKey = "{fileKey}", nodeId = "{int1}:{int2}"
```

**Branch URL対応:**
```
https://figma.com/design/{fileKey}/branch/{branchKey}/{fileName}
→ fileKey = "{branchKey}"
```

### 1-2. カタログ読込

```bash
# 既存コンポーネントカタログを読込
Read .claude/data/component-catalog.yaml
```

カタログが存在しない場合は空リストとして続行。

### 1-3. 既存キャッシュ確認

```bash
ls -la .claude/cache/figma/
```

24時間以内の有効なキャッシュがあれば再利用候補として記録。

## Phase 2: ページ別メタデータ取得 + 複雑度分析

### 2-1. get_metadata 実行

各ページURLに対して `get_metadata` を実行:

```
mcp__figma__get_metadata
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
```

### 2-2. 複雑度スコア計算

各トップレベルフレーム（セクション）に対してスコアを算出:

```
complexity = min(children * 2, 40)
           + min(depth * 5, 30)
           + min(text_count, 20)
           + min(height / 1000, 10)
```

| 要素 | 最大スコア | 計算方法 |
|------|-----------|---------|
| 子要素数 | 40 | children × 2 |
| ネスト深度 | 30 | depth × 5 |
| テキスト要素数 | 20 | text_count × 1 |
| フレーム高さ | 10 | height / 1000 |
| **合計** | **100** | |

### 2-3. 戦略判定

各セクションに戦略を割り当て:

| 条件 | 戦略 | アクション |
|------|------|----------|
| height < 5000 AND score < 50 | `NORMAL` | 通常取得（get_design_context 1回） |
| height >= 8000 OR score >= 70 | `SPLIT` | 分割取得推奨 |
| height >= 10000 | `SPLIT_REQUIRED` | 分割取得必須 |
| それ以外 | `NORMAL` | 通常取得 |

### 2-4. 除外条件

- `visible: false` のフレームはスキップ
- hidden レイヤーは複雑度計算から除外

## Phase 3: ページ横断 共通コンポーネント検出

4つの手法で共通コンポーネントを検出:

### 3-1. 名前一致検出

メタデータのレイヤー名が複数ページで一致するものを抽出:

```
例: "Header", "Footer", "CTA Section" が3ページに出現
→ 共通コンポーネント候補
```

### 3-2. 位置一致検出

同一の相対位置（top/bottom）に同種の要素が配置されているものを検出:

```
例: 全ページの最上部に "Header" (y=0, height≈80)
→ 共通ヘッダー
```

### 3-3. 構造一致検出

子要素の構成が類似するフレームを検出:

```
例: Page A の "Card" と Page B の "Card" が同じ子要素構造
→ 共通カードコンポーネント
```

### 3-4. Instance検出

Figma Component Instance（`type: "INSTANCE"`）を検出:

```
例: 同一 componentId を持つ Instance が複数ページに存在
→ Figma上で既にコンポーネント化済み
```

### 検出結果

各コンポーネント候補に以下を記録:

| フィールド | 説明 |
|-----------|------|
| name | コンポーネント名 |
| detection_method | 検出手法（name/position/structure/instance） |
| pages | 出現ページリスト |
| occurrence_count | 出現回数 |
| suggested_type | 推定タイプ（header/footer/card/button/etc） |

## Phase 4: カタログマッチング

### 4-1. 既存カタログとの照合

Phase 3 で検出した共通コンポーネントを `component-catalog.yaml` と照合:

### 4-2. マッチングスコア計算

| 条件 | スコア |
|------|--------|
| type 一致 | +40% |
| 必須props充足 | +30% |
| variant対応可能 | +20% |
| figma_patterns一致 | +10% |

**注意**: Code Connect は使用しない。カタログのみで判定。

### 4-3. 判定閾値

| スコア | 判定 | アクション |
|--------|------|----------|
| 70%以上 | `REUSE` | 既存コンポーネントをそのまま使用 |
| 40-69% | `EXTEND` | 既存ベース + カスタムスタイル |
| 40%未満 | `NEW` | 新規コンポーネント作成 |

### 4-4. 再利用判定表

各コンポーネントの判定結果を表形式で出力:

```
| Component | Score | Decision | Existing Match | Action |
|-----------|-------|----------|----------------|--------|
| Header    | 85%   | REUSE    | c-page-header  | Use as-is |
| CTA Card  | 55%   | EXTEND   | c-card         | Add variant |
| Hero      | 20%   | NEW      | -              | Create new |
```

## Phase 5: デザイントークン取得（任意）

`--tokens` オプション指定時のみ実行。

### 5-1. get_variable_defs 実行

```
mcp__figma__get_variable_defs
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
```

### 5-2. 空レスポンス対応

`get_variable_defs` が空オブジェクト `{}` を返した場合:

1. 「Variables未定義」として記録
2. Phase 2 の get_metadata から色・フォント情報を手動抽出可能と注記
3. 後続の `/figma-implement` で `get_design_context` から抽出する旨を記載

### 5-3. SCSS変数マッピング

取得したトークンを SCSS 変数名に変換（参考情報として記録）:

```
color/primary → --color-primary
fontSize/body → --font-size-body
spacing/section → --spacing-section
```

## Phase 6: 実装順序決定

### 6-1. 依存関係グラフ

共通コンポーネントの依存関係から実装順序を決定:

```
1. 共通コンポーネント（他ページが依存）
2. 最も多くのセクションを持つページ（効率最大化）
3. 独立したページ（依存なし）
```

### 6-2. 優先度計算

| 要素 | 重み | 説明 |
|------|------|------|
| 共通コンポーネント数 | ×3 | 他ページへの影響度 |
| セクション数 | ×1 | 実装ボリューム |
| 複雑度平均 | ×0.5 | 難易度 |

### 6-3. 実装順序出力

```
Recommended Implementation Order:
1. Common Components (Header, Footer, CTA) → 基盤として先に実装
2. Page: Top (5 sections, avg complexity: 45) → 最多セクション
3. Page: About (3 sections, avg complexity: 30) → 中程度
4. Page: Contact (2 sections, avg complexity: 20) → 最少
```

## Phase 7: レポート生成

### 7-1. YAML レポート出力

`.claude/cache/figma/analysis-report.yaml` に出力:

```yaml
# Figma Analysis Report
# Generated: {timestamp}

meta:
  generated_at: "2026-02-28T12:00:00Z"
  page_count: 3
  total_sections: 15

pages:
  - name: "Top"
    url: "https://figma.com/design/..."
    fileKey: "abc123"
    nodeId: "1:2"
    sections:
      - name: "Header"
        nodeId: "1:10"
        height: 80
        complexity: 15
        strategy: "NORMAL"
      - name: "Hero"
        nodeId: "1:20"
        height: 800
        complexity: 45
        strategy: "NORMAL"
      - name: "Features"
        nodeId: "1:30"
        height: 12000
        complexity: 85
        strategy: "SPLIT_REQUIRED"

shared_components:
  - name: "Header"
    detection_method: "name+position"
    pages: ["Top", "About", "Contact"]
    catalog_match:
      component: "c-page-header"
      score: 85
      decision: "REUSE"
  - name: "CTA Card"
    detection_method: "structure"
    pages: ["Top", "About"]
    catalog_match:
      component: "c-card"
      score: 55
      decision: "EXTEND"

implementation_order:
  - step: 1
    type: "common"
    items: ["Header", "Footer", "CTA Card"]
    reason: "Shared across multiple pages"
  - step: 2
    type: "page"
    name: "Top"
    sections: 8
    avg_complexity: 52
  - step: 3
    type: "page"
    name: "About"
    sections: 4
    avg_complexity: 35

design_tokens:
  status: "extracted"  # or "empty" or "skipped"
  variables_count: 24

strategies_summary:
  NORMAL: 10
  SPLIT: 3
  SPLIT_REQUIRED: 2
```

### 7-2. コンソールサマリー

分析完了後、以下の表形式でサマリーを出力:

```
╔══════════════════════════════════════════════════════════════╗
║                    Figma Analysis Report                     ║
╠══════════════════════════════════════════════════════════════╣

📄 Pages Analyzed: 3
📦 Total Sections: 15
🔗 Shared Components: 4

┌─────────────────────────────────────────────────────────────┐
│ Page Strategies                                              │
├──────────┬──────────┬──────────┬────────────────────────────┤
│ Page     │ Sections │ Avg Score│ Strategy                   │
├──────────┼──────────┼──────────┼────────────────────────────┤
│ Top      │ 8        │ 52       │ 5 NORMAL / 2 SPLIT / 1 REQ│
│ About    │ 4        │ 35       │ 4 NORMAL                   │
│ Contact  │ 3        │ 20       │ 3 NORMAL                   │
└──────────┴──────────┴──────────┴────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Shared Components                                            │
├────────────┬──────────┬──────────┬──────────┬───────────────┤
│ Component  │ Pages    │ Match    │ Score    │ Decision      │
├────────────┼──────────┼──────────┼──────────┼───────────────┤
│ Header     │ 3        │ c-header │ 85%      │ REUSE         │
│ Footer     │ 3        │ c-footer │ 90%      │ REUSE         │
│ CTA Card   │ 2        │ c-card   │ 55%      │ EXTEND        │
│ Hero       │ 1        │ -        │ -        │ NEW           │
└────────────┴──────────┴──────────┴──────────┴───────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Implementation Order                                         │
├─────┬────────────────────────────────────────────────────────┤
│ 1   │ Common: Header, Footer, CTA Card                      │
│ 2   │ Page: Top (8 sections)                                 │
│ 3   │ Page: About (4 sections)                               │
│ 4   │ Page: Contact (3 sections)                             │
└─────┴────────────────────────────────────────────────────────┘

📁 Full report: .claude/cache/figma/analysis-report.yaml

Next steps:
  /figma-implement {url} --section {section}
```

## Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Invalid Figma URL | Regex parse failure | エラーメッセージ + 正しいURL形式を表示 |
| get_metadata failure | MCP exception | 3回リトライ → 該当ページをスキップ |
| Figma auth error | HTTP 401/403 | 認証トークン確認を促す |
| カタログファイル未存在 | File not found | 空リストで続行（警告表示） |
| 全ページ取得失敗 | All pages failed | エラー終了 + 原因一覧を表示 |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/data/component-catalog.yaml` | コンポーネントカタログ |
| `.claude/cache/figma/analysis-report.yaml` | 分析レポート出力先 |
| `.claude/rules/figma-workflow.md` | Figmaワークフロールール |
| `.claude/rules/figma.md` | Figma統合ルール |
| `.claude/skills/figma-implement/SKILL.md` | 実装スキル（後続） |

---

**Version**: 1.0.0
**Created**: 2026-02-28
