---
name: create-design-rules
description: "デザインシステムルール生成"
disable-model-invocation: true
allowed-tools:
  - mcp__figma__create_design_system_rules
  - mcp__figma__get_variable_defs
  - Read
  - Write
  - Edit
  - Glob
context: fork
agent: general-purpose
---

# デザインシステムルール生成

Figmaデザインからプロジェクト固有のデザインシステムルールを自動生成します。

## 概要

`mcp__figma__create_design_system_rules` ツールを活用し、Figmaで定義されたデザイントークン（カラー、タイポグラフィ、スペーシング等）を既存のSCSS変数構成にマッピングするルールを生成します。

### 目的

- Figmaデザインとコードベースの一貫性確保
- デザイントークンの自動同期
- 実装時の変換ルール明確化

## ワークフロー

### 1. デザイントークン取得

```
mcp__figma__create_design_system_rules を実行
↓
Figma変数・スタイルを解析
↓
トークン一覧を取得
```

### 2. 既存SCSS変数との対応付け

プロジェクトの既存変数（`src/scss/foundation/_variables.scss`）と照合:

| Figmaトークン | SCSS変数 |
|--------------|----------|
| primary/main | --color-primary |
| text/default | --color-text |
| font/heading | --font-secondary |
| font/body | --font-primary |

### 3. マッピングルール生成

Figma値とSCSS出力の変換ルールを定義:

```scss
// Figma: 32px (PC), 24px (SP)
// 出力:
font-size: rv(32);
@include sp {
  font-size: svw(24);
}
```

## 出力形式

### SCSSファイル

`src/scss/foundation/_figma-tokens.scss` として生成:

```scss
// Figma Design Tokens - Auto Generated
// Generated at: YYYY-MM-DD

// カラートークン
$figma-color-primary: var(--color-primary);
$figma-color-accent: var(--color-accent-red);

// タイポグラフィトークン
$figma-font-heading: var(--font-secondary);
$figma-font-body: var(--font-primary);

// スペーシングトークン（rv()変換済み）
$figma-spacing-sm: rv(8);
$figma-spacing-md: rv(16);
$figma-spacing-lg: rv(24);
$figma-spacing-xl: rv(40);
```

### ドキュメント

`.claude/docs/design-tokens-map.md` として生成:

- Figma ↔ SCSS対応表
- 変換ルール説明
- 使用例

## 使用方法

```
/create-design-rules [Figma URL]
```

### 実行例

```
/create-design-rules https://figma.com/design/xxx/ProjectName?node-id=0-1
```

### 引数

| 引数 | 説明 | 必須 |
|------|------|------|
| Figma URL | デザインファイルのURL | ○ |

## プロジェクト固有の考慮

### FLOCSS構成との整合性

- 生成ファイルは `foundation/` レイヤーに配置
- 既存の `_variables.scss` を上書きせず、別ファイルとして生成
- `main.scss` で適切な順序でインポート

### 既存変数との連携

```scss
// 既存: src/scss/foundation/_variables.scss
:root {
  --color-primary: #d71218;
  --font-primary: "Noto Sans JP", sans-serif;
}

// 生成: src/scss/foundation/_figma-tokens.scss
// 既存変数を参照し、Figmaトークン名でエイリアス化
```

### サイズ関数との組み合わせ

| Figma値 | PC出力 | SP出力 |
|---------|--------|--------|
| 32px | rv(32) | svw(24) |
| 16px | rv(16) | svw(14) |
| auto計算 | pvw() | svw() |

## 注意事項

- Figma Dev Modeへのアクセス権限が必要
- 初回実行時にデザイントークンの命名規則を確認
- 生成後は手動でレビューし、必要に応じて調整
- 既存の `_variables.scss` は編集せず、新規ファイルとして生成

## 関連コマンド

- `/figma-implement` - Figma → WordPress完全実装
