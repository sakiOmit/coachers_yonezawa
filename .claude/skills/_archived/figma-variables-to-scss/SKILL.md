---
name: figma-variables-to-scss
description: "Extract Figma Variables and convert to SCSS variables (CSS Custom Properties) with diff detection."
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
  - mcp__figma__get_variable_defs
  - mcp__figma__get_design_context
context: fork
agent: general-purpose
---

# Figma Variables to SCSS

Figma Variables API からデザイントークンを取得し、SCSS変数（CSS Custom Properties）に自動変換する。

## Usage

```
/figma-variables-to-scss [Figma URL]
/figma-variables-to-scss [Figma URL] --dry-run
/figma-variables-to-scss [Figma URL] --force
/figma-variables-to-scss [Figma URL] --output src/scss/foundation/_figma-tokens.scss
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| Figma URL | Yes | FigmaファイルのURL（省略時は対話式入力） |
| --dry-run | No | 差分レポートのみ表示（書き込みなし） |
| --force | No | 確認なしで全て適用 |
| --output | No | 出力先ファイルパス指定 |

## Processing Flow

### Step 1: URL解析

Figma URLからfileKeyとnodeIdを抽出:
```
https://figma.com/design/{fileKey}/{fileName}?node-id={nodeId}
→ fileKey: abc123xyz, nodeId: 1:2
```

ブランチURL: `branchKey` を `fileKey` として使用。

### Step 2: Figma Variables取得

```
mcp__figma__get_variable_defs
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
  clientLanguages: "scss"
  clientFrameworks: "wordpress"
```

### Step 3: 命名規則マッピング

| Figma変数名 | SCSS変数名 |
|-------------|------------|
| `color/primary` | `--color-primary` |
| `fontSize/body` | `--font-size-body` |
| `lineHeight/tight` | `--line-height-tight` |
| `spacing/8` | `--spacing-8` |

変換ルール:
1. スラッシュ `/` → ハイフン `-`
2. camelCase → kebab-case
3. `--` プレフィックス付与
4. 数値接尾辞は保持

### Step 4: 既存変数との差分検出

`src/scss/foundation/_variables.scss` を読み込み差分検出。
ユーザーに「全適用 / キャンセル / 選択適用」を提示。

### Step 5: SCSS出力

```scss
// ===== Figma Design Tokens (Auto-generated) =====
// Source: {fileKey} / {nodeId}
// Generated: {timestamp}
// ================================================

:root {
  --color-primary: #d71218;
  --spacing-section: 80px;
  --font-size-h1: 48px;
}

// ===== End Figma Design Tokens =====
```

マージ戦略:
1. 既存の手動定義変数は保持
2. 自動生成セクションは識別コメントで管理
3. 再実行時は自動生成セクションのみ更新

## Error Handling

| Error | Response |
|-------|----------|
| Variables empty | 手動抽出を提案（get_design_contextから） |
| Invalid variable name | 手動追加を案内 |
| File write error | パーミッション確認を案内 |

## Related Skills

- `/figma-implement` - Figmaデザインの完全実装（Step 4で内部使用）
- `/create-design-rules` - デザインシステムルール生成
