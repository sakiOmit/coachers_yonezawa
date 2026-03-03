---
name: figma-analyze
description: "Analyze Figma pages to detect shared components, split strategies, and implementation order. Trigger: 'analyze', '分析'."
argument-hint: "{url1} [url2] [--tokens]"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - mcp__figma__get_metadata
  - mcp__figma__get_variable_defs
model: opus
context: fork
agent: general-purpose
---

# Figma Analyze

## Dynamic Context

```
Existing Figma cache:
!`ls .claude/cache/figma/ 2>/dev/null || echo "(empty)"`

Component catalog size:
!`wc -l < .claude/data/component-catalog.yaml 2>/dev/null || echo "0"`
```

## Overview

複数ページのFigma URLを受け取り、コンポーネント共通化・ページ分割戦略・実装順序を決定する分析スキル。
`/figma-implement` の前段フェーズとして使用し、効率的な実装計画を立てる。

### Key Features

- **複数ページ横断分析**: ページ間で共通するコンポーネントを自動検出
- **複雑度ベース戦略判定**: セクションごとに NORMAL / SPLIT / SPLIT_REQUIRED を判定
- **カタログマッチング**: 既存コンポーネントとの再利用可能性をスコアリング
- **実装順序最適化**: 依存関係と共通コンポーネントに基づく最適な実装順序

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | なし（起点） |
| **後工程** | `/figma-implement` |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | なし |

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

### Argument Parsing

```
入力: $ARGUMENTS
パース:
  - URL リスト: スペース区切りの Figma URL を配列として取得
  - --tokens フラグ: デザイントークン取得の有効化

例:
  /figma-analyze https://figma.com/design/abc/Page1?node-id=0-1 https://figma.com/design/abc/Page2?node-id=0-2
  /figma-analyze https://figma.com/design/abc/Page1?node-id=0-1 --tokens
```

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

各ページURLに対して `get_metadata` を実行し、トップレベルフレームごとに複雑度スコア（0-100）を算出。
スコアに基づき NORMAL / SPLIT / SPLIT_REQUIRED の戦略を判定する。

**詳細**: → [references/complexity-and-matching.md](references/complexity-and-matching.md) の「Phase 2」セクション

## Phase 3: ページ横断 共通コンポーネント検出

4つの手法（名前一致・位置一致・構造一致・Instance検出）で共通コンポーネントを検出。

**詳細**: → [references/complexity-and-matching.md](references/complexity-and-matching.md) の「Phase 3」セクション

## Phase 4: カタログマッチング

Phase 3 で検出した共通コンポーネントを `component-catalog.yaml` と照合し、
REUSE（70%+）/ EXTEND（40-69%）/ NEW（40%未満）を判定。

**詳細**: → [references/complexity-and-matching.md](references/complexity-and-matching.md) の「Phase 4」セクション

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

### Next Commands（自動生成）

分析結果から `/figma-implement` コマンドを自動生成してコンソールに表示する:

```
📋 推奨実装コマンド（コピー可能）:

# 1. {page_name} - {section_name} (complexity: {score})
/figma-implement {url} --section {section_name}

# 2. {page_name} - {section_name} (complexity: {score})
/figma-implement {url} --section {section_name}

# 共通コンポーネント（先に実装推奨）:
/figma-implement {url} --section {shared_component_name}
```

analysis-report.yaml にも `next_commands` フィールドとして出力する:
```yaml
next_commands:
  shared_components:
    - "/figma-implement {url} --section {name}"
  pages:
    - page: "{page_name}"
      commands:
        - "/figma-implement {url} --section {section}"
```

## Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Invalid Figma URL | Regex parse failure | エラーメッセージ + 正しいURL形式を表示 |
| get_metadata failure | MCP exception | 3回リトライ → 該当ページをスキップ |
| Figma auth error | HTTP 401/403 | 認証トークン確認を促す |
| カタログファイル未存在 | File not found | 空リストで続行（警告表示） |
| 全ページ取得失敗 | All pages failed | エラー終了 + 原因一覧を表示 |

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | 入力 | 出力 |
|-----------|------|------|------|
| `scripts/calculate-complexity.sh` | メタデータJSONから複雑度スコア計算 | Figma metadata JSON file | JSON (scores + strategy) |
| `scripts/detect-shared-components.sh` | ページ横断の共通コンポーネント自動検出 | 2+ metadata JSON files | JSON (shared components) |

### calculate-complexity.sh

```bash
bash .claude/skills/figma-analyze/scripts/calculate-complexity.sh <metadata.json>
```

- **入力**: `get_metadata` の出力を保存した JSON ファイル
- **出力**: セクション別スコア + 合計 + 分割戦略を JSON で出力
- **計算式**: `children×2 + depth×5 + text_count + height/1000`
- **戦略判定**: NORMAL (<100) / SPLIT (100-200) / SPLIT_REQUIRED (>200)
- **依存**: python3 + json モジュール（標準ライブラリ）
- **終了コード**: 0=成功, 1=エラー

### detect-shared-components.sh

```bash
bash .claude/skills/figma-analyze/scripts/detect-shared-components.sh <page1.json> <page2.json> [page3.json ...]
```

- **入力**: 2つ以上の `get_metadata` 出力 JSON ファイル（各ページ1ファイル）
- **出力**: 共通コンポーネント一覧を JSON で出力（名前・検出手法・出現ページ・推定タイプ）
- **検出手法**: 4種類
  1. **名前一致**: 同一レイヤー名が複数ページに出現
  2. **位置一致**: 同一相対位置（top/bottom）に同種要素が配置
  3. **構造一致**: 子要素の構成（タイプ・数）が類似
  4. **Instance検出**: 同一 componentId の Instance が複数ページに存在
- **重複排除**: 複数手法で検出された場合、優先度（instance > name > structure > position）で統合
- **依存**: python3 + json モジュール（標準ライブラリ）
- **終了コード**: 0=成功, 1=エラー

## Agent Integration

Phase 2-4（メタデータ取得 + 複雑度分析 + カタログマッチング）を Explore エージェントに委譲可能:

```
Task tool:
  subagent_type: Explore
  prompt: |
    以下の Figma ページのメタデータを分析してください:
    - URLs: {url_list}

    実行内容:
    1. 各 URL の get_metadata 結果を確認（キャッシュ .claude/cache/figma/ を優先参照）
    2. トップレベルフレームの子要素数・ネスト深度・テキスト要素数を集計
    3. 複雑度スコアを算出: children×2 + depth×5 + text_count + height/1000
    4. .claude/data/component-catalog.yaml と照合し REUSE/EXTEND/NEW を判定

    結果を構造化して返してください。
```

**委譲条件**: 分析対象ページ数 >= 3 の場合
**Fallback**: エージェント不在時は直接 Bash + Read で分析

## Related Files

| File | Purpose |
|------|---------|
| `.claude/data/component-catalog.yaml` | コンポーネントカタログ |
| `.claude/cache/figma/analysis-report.yaml` | 分析レポート出力先 |
| `.claude/rules/figma-workflow.md` | Figmaワークフロールール |
| `.claude/rules/figma.md` | Figma統合ルール |
| `.claude/skills/figma-implement/SKILL.md` | 実装スキル（後続） |
| `.claude/skills/scripts-standard.md` | スクリプト標準規約 |

---

**Version**: 1.0.0
**Created**: 2026-02-28
