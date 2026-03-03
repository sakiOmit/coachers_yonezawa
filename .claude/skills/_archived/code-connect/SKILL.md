---
name: code-connect
description: "Connect Figma components to WordPress template-parts via Code Connect API for design-to-code consistency."
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
  - mcp__figma__get_code_connect_map
  - mcp__figma__add_code_connect_map
  - mcp__figma__get_metadata
context: fork
agent: general-purpose
---

# Code Connect

Figmaコンポーネントとコードベースのコンポーネントを紐付け、デザイン→実装の効率化と一貫性を実現する。

## Usage

```
/code-connect [Figma URL]
```

- `Figma URL`: 対象のFigmaコンポーネントURL（省略時は対話式で入力）

## Overview

Code Connectは、Figmaのコンポーネントとプロジェクトのコードコンポーネントをマッピングする機能。

### メリット

1. **再利用性向上**: Figmaでコンポーネントを見た際、対応するコードが即座に分かる
2. **実装の一貫性**: 既存コンポーネントの再利用を促進し、重複実装を防止
3. **オンボーディング**: 新メンバーがデザイン⇔コードの対応を素早く把握

## MCP Functions

### get_code_connect_map

```
mcp__figma__get_code_connect_map
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
```

### add_code_connect_map

```
mcp__figma__add_code_connect_map
  nodeId: "{nodeId}"
  fileKey: "{fileKey}"
  source: "template-parts/components/{component-name}.php"
  componentName: "c-{component-name}"
  label: "PHP"
```

## Processing Flow

1. Figma URLからfileKey/nodeIdを抽出
2. `get_code_connect_map` で既存登録を確認
3. プロジェクトの `template-parts/` をスキャンして再利用可能コンポーネントを列挙
4. ユーザーにマッピング対象を選択させる
5. `add_code_connect_map` で登録
6. `component-catalog.yaml` を更新

## Registration Format

```
source: "template-parts/common/link-button.php"
componentName: "c-link-button"
label: "PHP"
```

## Error Handling

| Error | Response |
|-------|----------|
| Figma URL invalid | URLの再入力を求める |
| Code Connect API error | プラン制限の可能性を通知 |
| Component not found | 新規作成を提案 |

## Related Skills

- `/figma-implement` - Figma → WordPress完全実装
- `/figma-to-code` - Figmaから静的コード生成
- `/create-design-rules` - デザインシステムルール生成
