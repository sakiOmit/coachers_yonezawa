---
name: scss-naming-normalizer
description: "Figmaレイヤー名からkebab-case + FLOCSS準拠のSCSSクラス名を自動生成し、命名規則違反を検出・修正する"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# SCSS Naming Normalizer

## Overview

Figmaレイヤー名からkebab-case + FLOCSS準拠のSCSSクラス名を自動生成し、
既存SCSSファイルの命名規則違反を検出・修正するスキル。

プロジェクト全体の命名一貫性を保証し、コードレビュー工数を削減する。

## Usage

```
/scss-naming-normalizer check [path]
/scss-naming-normalizer convert "FigmaLayerName" [--type component|project]
/scss-naming-normalizer fix [path] [--dry-run]
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| mode | Yes | `check`, `convert`, `fix` のいずれか |
| path | No | 対象パス（デフォルト: `src/scss/`） |
| --type | No | FLOCSS prefix判定（`component` → `c-`, `project` → `p-`） |
| --dry-run | No | 修正せずに変更内容のみ表示 |
| --output | No | レポート出力先（デフォルト: stdout） |
| --format | No | 出力形式（`text`, `json`, `markdown`） |

## Output

### check モード

```json
{
  "summary": {
    "total_files": 120,
    "violations_found": 8,
    "violation_types": {
      "camelCase": 6,
      "PascalCase": 2,
      "snake_case": 0
    }
  },
  "violations": [
    {
      "file": "src/scss/object/component/_c-CategoryBadge.scss",
      "current": "_c-CategoryBadge.scss",
      "expected": "_c-category-badge.scss",
      "violation_type": "PascalCase",
      "auto_fixable": true
    }
  ]
}
```

### convert モード

```json
{
  "input": "SectionHeading",
  "output": {
    "class_name": "c-section-heading",
    "file_name": "_c-section-heading.scss",
    "block_name": "section-heading"
  },
  "transformations_applied": [
    "PascalCase → kebab-case",
    "FLOCSS prefix: c-"
  ]
}
```

### fix モード

```json
{
  "files_renamed": 8,
  "changes": [
    {
      "from": "src/scss/object/component/_c-CategoryBadge.scss",
      "to": "src/scss/object/component/_c-category-badge.scss",
      "status": "success"
    }
  ],
  "import_updates": [
    {
      "file": "src/scss/object/component/_index.scss",
      "changes": 8
    }
  ]
}
```

## Processing Flow

```
1. 入力パース
   └─ mode, path, オプション解析

2. 対象ファイル収集
   ├─ glob パターン: **/*.scss
   └─ 除外: node_modules, vendor

3. 命名規則チェック
   ├─ ファイル名チェック
   │   ├─ camelCase検出: /[a-z][A-Z]/
   │   ├─ PascalCase検出: /^_?[A-Z]/
   │   └─ snake_case検出: /_[a-z]/（FLOCSSプレフィックス後）
   │
   └─ クラス名チェック（ファイル内）
       └─ セレクタ解析

4. 変換処理（fix/convert時）
   ├─ 名前変換アルゴリズム適用
   ├─ ファイルリネーム
   └─ @use/@forward文の自動更新

5. レポート生成
   └─ 指定形式で出力
```

## Conversion Algorithm

### Figma Name → kebab-case

```javascript
function normalizeToKebabCase(name) {
  return name
    // 1. スペース・スラッシュをハイフンに
    .replace(/[\s\/]+/g, '-')
    // 2. camelCase/PascalCase → kebab-case
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    // 3. 連続大文字対応（例: XMLParser → xml-parser）
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1-$2')
    // 4. 小文字化
    .toLowerCase()
    // 5. 連続ハイフンを単一に
    .replace(/-+/g, '-')
    // 6. 先頭・末尾ハイフン削除
    .replace(/^-|-$/g, '');
}
```

### FLOCSS Prefix Detection

```javascript
function getFLOCSSPrefix(name, context) {
  // 明示的指定があれば使用
  if (context.type === 'component') return 'c-';
  if (context.type === 'project') return 'p-';

  // 自動判定
  const componentPatterns = [
    /button/i, /card/i, /badge/i, /tag/i,
    /heading/i, /list/i, /link/i, /icon/i,
    /breadcrumb/i, /pagination/i, /modal/i
  ];

  return componentPatterns.some(p => p.test(name)) ? 'c-' : 'p-';
}
```

### Conversion Examples

| Input (Figma) | Output (SCSS Class) | Output (File) |
|---------------|---------------------|---------------|
| `CategoryBadge` | `c-category-badge` | `_c-category-badge.scss` |
| `SectionHeading` | `c-section-heading` | `_c-section-heading.scss` |
| `HeroSection` | `p-hero-section` | `_p-hero-section.scss` |
| `Button/Primary` | `c-button-primary` | `_c-button-primary.scss` |

## Error Handling

| Error | Response |
|-------|----------|
| ファイル権限エラー | 警告出力、スキップして続行 |
| 名前衝突（リネーム先が既存） | エラー出力、手動対応を要求 |
| @use/@forward更新失敗 | ロールバック、元のファイル名を復元 |
| 不正なFigma名（数字のみ等） | 警告出力、`unnamed-{index}` として処理 |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/scss.md` | SCSS命名規則ルール |
| `src/scss/` | チェック対象ディレクトリ |
| `.claude/reports/naming-violations.json` | 違反レポート保存先 |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Author**: Auto-generated
