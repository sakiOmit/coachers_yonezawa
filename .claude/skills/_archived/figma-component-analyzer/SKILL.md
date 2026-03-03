---
name: figma-component-analyzer
description: "複数ページのFigmaデザインデータを解析し、共通コンポーネントを自動検出して実装優先順位を出力する"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - mcp__figma__get_metadata
  - mcp__figma__get_design_context
context: fork
agent: general-purpose
---

# Figma Component Analyzer

## Overview

複数ページのFigmaデザインデータを解析し、共通コンポーネントを自動検出するスキル。
実装優先順位付きでコンポーネント一覧を出力し、効率的な実装計画を支援する。

## Usage

```
/figma-component-analyzer [Figma URLs...]
/figma-component-analyzer --file-key {fileKey} --node-ids {nodeId1,nodeId2,...}
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| URLs | Yes* | FigmaのページURL（複数可） |
| --file-key | Yes* | Figmaファイルキー（URLの代わりに使用） |
| --node-ids | No | 解析対象のnodeID（カンマ区切り） |
| --output | No | 出力先パス（デフォルト: `.claude/cache/figma/component-analysis-{timestamp}.json`） |
| --format | No | 出力形式（json/markdown/yaml、デフォルト: json） |

*URLs または --file-key のいずれかが必須

## Output

### JSON Format (Default)

```json
{
  "metadata": {
    "file_key": "wbpri0A53IqL1KvkRBtvkl",
    "analyzed_pages": 9,
    "timestamp": "2026-01-30T12:00:00Z"
  },
  "common_components": [
    {
      "name": "l-header",
      "detection_rate": "100%",
      "pages_found": 9,
      "priority": "HIGH",
      "recommended_files": {
        "php": "template-parts/common/header.php",
        "scss": "src/scss/layout/_l-header.scss"
      },
      "figma_patterns": ["Frame 6366"],
      "structure": {
        "height": "80px",
        "width": "1440px",
        "background": "rgba(255,255,255,0.6)",
        "blur": "10px"
      },
      "variants": []
    }
  ],
  "global_styles": {
    "colors": {},
    "typography": {},
    "spacing": {}
  },
  "reusability_score": 90
}
```

### Markdown Format

```markdown
# Figma共通コンポーネント解析レポート

## 検出されたコンポーネント

### HIGH PRIORITY
1. **l-header** (100% - 9/9ページ)
...
```

## Processing Flow

```
1. 入力パース
   └─ URLからfileKey/nodeIdを抽出

2. Figmaデータ取得（並列処理）
   ├─ get_metadata で構造取得
   └─ 大規模ページは分割取得

3. コンポーネント検出
   ├─ 同一構造のFrameを特定
   ├─ 出現頻度をカウント
   └─ パターンマッチングで分類

4. 優先度計算
   ├─ HIGH: 80%以上のページで使用
   ├─ MEDIUM: 30-79%のページで使用
   └─ LOW: 30%未満

5. グローバルスタイル抽出
   ├─ カラーパレット
   ├─ タイポグラフィ
   └─ スペーシング

6. 出力生成
   └─ 指定形式でファイル出力
```

## Detection Algorithm

### Component Candidate Identification

1. **Position-based Detection**
   - 同一座標に配置されたFrame（ヘッダー、フッター）
   - 複数ページで一貫した位置関係

2. **Structure-based Detection**
   - 子要素の構成が類似
   - 同一のレイヤー名パターン

3. **Style-based Detection**
   - 同一のカラー/フォント使用
   - 同一のborder-radius/shadow

### Priority Score Calculation

```
score = (detection_rate * 0.6) + (complexity * 0.2) + (reuse_potential * 0.2)

- detection_rate: ページ出現率
- complexity: 実装の複雑さ（低いほど高スコア）
- reuse_potential: 他プロジェクトでの再利用可能性
```

## Error Handling

| Error | Response |
|-------|----------|
| Figma API タイムアウト | 3回リトライ後、部分結果を出力 |
| 大規模ページ | 自動分割取得 |
| 権限エラー | エラーメッセージと対象ページをスキップ |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/cache/figma/` | キャッシュ保存先 |
| `.claude/reports/figma-component-analysis-report.md` | 最新解析レポート |
| `.claude/rules/figma-workflow.md` | Figmaワークフロールール |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Author**: Auto-generated
**Approved**: 殿（上様）
