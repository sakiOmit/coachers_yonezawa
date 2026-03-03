# Skills ガイド

## 概要

スキルは、特定のタスクを自動化する再利用可能なワークフローです。
スラッシュコマンド（例: `/skill-name`）で呼び出すことができます。

## スキル一覧

### Figma関連

| スキル | 説明 | 使用方法 |
|--------|------|---------|
| figma-implement-orchestrator | Figma → WordPress実装ワークフローのオーケストレーター。状態永続化、再開機能、エラー回復を備えた大規模ページ実装向け | `/figma-implement-orchestrator <figma-url>` |
| figma-page-analyzer | Figmaページの規模（高さ、要素数、複雑度）を事前分析し、MCP制限を考慮した最適な取得戦略を提案 | `/figma-page-analyzer <figma-url>` |
| figma-recursive-splitter | トークン制限を超える大規模Figmaページを BFS アルゴリズムで再帰的に分割・取得 | `/figma-recursive-splitter <figma-url>` |
| figma-section-splitter | 大規模Figmaページをセクション単位で分割し、複数ワーカーによる並列実装を支援（3フェーズワークフロー） | `/figma-section-splitter <figma-url>` |
| figma-visual-diff-runner | PlaywrightとpixelmatchでFigmaデザインと実装ページの視覚的差分を自動検証 | `/figma-visual-diff-runner <figma-url> <local-url>` |
| figma-component-analyzer | 複数ページのFigmaデザインを解析し、共通コンポーネントを自動検出して実装優先順位を出力 | `/figma-component-analyzer <figma-urls>` |
| figma-design-tokens-extractor | Figma Variablesからデザイントークンを抽出し、SCSS変数（CSS Custom Properties）に変換 | `/figma-design-tokens-extractor <figma-url>` |

### WordPress関連

| スキル | 説明 | 使用方法 |
|--------|------|---------|
| wordpress-page-generator | WordPressページテンプレートをインタラクティブに生成（PHPテンプレート、SCSS構造、ビルド設定） | `/wordpress-page-generator <page-name>` |
| acf-field-generator | ACFフィールドグループをインタラクティブに生成。フィールドタイプ、名前、ラベルを対話で収集しPHPコード生成 | `/acf-field-generator <field-group-name>` |

### SCSS関連

| スキル | 説明 | 使用方法 |
|--------|------|---------|
| scss-component-generator | FLOCSS準拠SCSSコンポーネントをインタラクティブに生成。コンポーネントタイプ、BEM命名、レスポンシブ設定を収集 | `/scss-component-generator <component-name>` |
| scss-naming-normalizer | Figmaレイヤー名からkebab-case + FLOCSS準拠のSCSSクラス名を自動生成し、命名規則違反を検出・修正 | `/scss-naming-normalizer <figma-url>` |

### プラグイン/スキル関連

| スキル | 説明 | 使用方法 |
|--------|------|---------|
| plugin-scaffold | Claude Codeプラグインの雛形ディレクトリ構造を自動生成 | `/plugin-scaffold <plugin-name>` |
| skill-format-converter | 旧形式スキル（skill.json + instructions.md）を公式SKILL.md形式に変換 | `/skill-format-converter <skill-name>` |

### ユーティリティ

| スキル | 説明 | 使用方法 |
|--------|------|---------|
| claude-directory-cleaner | .claudeディレクトリ内の不要ファイル（旧形式スキル、重複キャッシュ等）を検出・削除 | `/claude-directory-cleaner` |
| directory-structure-analyzer | 設定ディレクトリ構造を分析し、壊れた参照、命名の不整合を検出、改善提案を出力 | `/directory-structure-analyzer <directory>` |
| docs-sync-checker | ドキュメントと実装ファイルの同期状態を確認（.claude/agents, .claude/skills と docs/claude-guide） | `/docs-sync-checker` |
| placeholder-detector | プロジェクト内のプレースホルダー形式（{{}}と{}）を検出・分析し、混在を警告。一貫性スコア算出と置換チェックリスト生成 | `/placeholder-detector [--format {{}}|{}|both]` |

## スキルの使い方

### 基本構文

```
/<skill-name> [arguments]
```

### 例

```bash
# Figmaページを分析
/figma-page-analyzer https://figma.com/design/xxx/yyy?node-id=1-2

# WordPressページテンプレートを生成
/wordpress-page-generator about

# SCSSコンポーネントを生成
/scss-component-generator button
```

## スキル開発

### スキルの場所

```
.claude/skills/<skill-name>/
└── SKILL.md           # スキル定義ファイル（必須）
```

### SKILL.md フォーマット

```yaml
---
name: skill-name
description: "スキルの説明（1文）"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
context: fork
agent: general-purpose
---

# Skill Name

## Overview
...

## Usage
/skill-name [args]
```

詳細: `.claude/rules/skill.md`

## 関連ドキュメント

- [エージェント](agents.md) - エージェント一覧と使用方法
- [MCP使用ガイド](mcp-usage.md) - MCPツールの使用方法
