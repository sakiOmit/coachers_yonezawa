# Review Output Schema Documentation

## Overview

このドキュメントは、`/review` スキルの JSON 出力フォーマットを定義します。
`/fix` スキルがこの JSON スキーマを入力として受け取り、修正対象をパースして処理します。

## JSON Schema

### Root Object

```json
{
  "review_date": "YYYY-MM-DD",
  "review_time": "HH:MM:SS",
  "type": "scss|php|js|all",
  "issues": [...],
  "summary": {...},
  "verdict": "READY|NEEDS_REVISIONS"
}
```

### Properties

#### review_date

- **Type**: string (ISO 8601 date format)
- **Required**: Yes
- **Example**: "2026-03-03"
- **Description**: レビュー実行日

#### review_time

- **Type**: string (HH:MM:SS format)
- **Required**: No
- **Example**: "14:30:45"
- **Description**: レビュー実行時刻（タイムスタンプ）

#### type

- **Type**: string (enum)
- **Required**: Yes
- **Allowed Values**: `scss`, `php`, `js`, `all`
- **Description**: レビュー対象の種類

#### issues

- **Type**: array of Issue objects
- **Required**: Yes (may be empty array)
- **Description**: 検出された問題のリスト

#### summary

- **Type**: Summary object
- **Required**: Yes
- **Description**: 問題の統計サマリー

#### verdict

- **Type**: string (enum)
- **Required**: Yes
- **Allowed Values**: `READY`, `NEEDS_REVISIONS`
- **Description**: リリース可否の判定。Critical/High の問題が存在する場合は `NEEDS_REVISIONS`

---

## Issue Object

### Structure

```json
{
  "id": "string",
  "type": "scss|php|js|astro",
  "severity": "safe|risky",
  "priority": "critical|high|medium|low",
  "category": "string",
  "file": "string",
  "line": "integer|null",
  "column": "integer|null",
  "rule": "string",
  "description": "string",
  "suggestion": "string",
  "fix_type": "safe|risky|manual"
}
```

### Properties

#### id

- **Type**: string
- **Required**: Yes
- **Pattern**: `{type}-{number}` (e.g., `scss-001`, `php-042`, `js-015`, `astro-008`)
- **Description**: 一意の問題識別子。`/fix id` で指定可能

#### type

- **Type**: string (enum)
- **Required**: Yes
- **Allowed Values**: `scss`, `php`, `js`, `astro`
- **Description**: 問題の種別

#### severity

- **Type**: string (enum)
- **Required**: Yes
- **Allowed Values**: `safe`, `risky`
- **Description**: 修正の安全性。`safe` は自動修正可能、`risky` は人間の判断が必要

**定義:**
- **safe**: 機械的に修正可能で、修正前後の動作に影響がない問題
  - 例: console.log 削除、マジックナンバーの変数化、未使用 import の削除
- **risky**: 修正時にコンテキストの判断が必要、または修正による副作用がある可能性がある問題
  - 例: XSS 脆弱性修正、セキュリティ対応、設計変更

#### priority

- **Type**: string (enum)
- **Required**: Yes
- **Allowed Values**: `critical`, `high`, `medium`, `low`
- **Description**: 優先度（リリース前の対応が必須かどうか）

**定義:**
- **critical**: セキュリティ脆弱性、データ損失リスク（即時修正必須）
- **high**: 本番環境での不具合、規約違反（リリース前修正必須）
- **medium**: 保守性低下、ベストプラクティス違反（修正推奨）
- **low**: スタイル改善、任意の最適化（任意）

#### category

- **Type**: string
- **Required**: Yes
- **Examples**: `naming`, `security`, `performance`, `duplication`, `quality`, `accessibility`
- **Description**: 問題のカテゴリ。複数単語の場合はハイフンで区切る（kebab-case）

#### file

- **Type**: string
- **Required**: Yes
- **Example**: `src/scss/object/component/_c-button.scss`
- **Description**: 相対パス（プロジェクトルート基準）

#### line

- **Type**: integer or null
- **Required**: Yes
- **Example**: 42
- **Description**: 問題が発生した行番号。検出不可の場合は `null`

#### column

- **Type**: integer or null
- **Required**: No
- **Example**: 12
- **Description**: 問題が発生した列番号（オプション）

#### rule

- **Type**: string
- **Required**: Yes
- **Example**: `BEM命名違反`, `XSS脆弱性`, `console.log残留`
- **Description**: 違反したルール名

#### description

- **Type**: string
- **Required**: Yes
- **Example**: `クラス名 '.c-button-primary' は BEM 命名規則に違反しています。'&-' ネストではなく '&__' を使用してください。`
- **Description**: 問題の詳細説明

#### suggestion

- **Type**: string
- **Required**: Yes
- **Example**: `.c-button { &__primary { ... } }`
- **Description**: 修正案またはベストプラクティス。コード例を含むことが推奨

#### fix_type

- **Type**: string (enum)
- **Required**: Yes
- **Allowed Values**: `safe`, `risky`, `manual`
- **Description**: 修正の実現方法

**定義:**
- **safe**: `/fix auto` で自動修正可能（決定論的なテキスト置換）
- **risky**: `/fix {id}` で code-fixer エージェントが対話的に修正（人間の確認推奨）
- **manual**: `/fix {id}` で修正案を提示するのみ（手動修正が必須）

---

## Summary Object

### Structure

```json
{
  "total": "integer",
  "critical": "integer",
  "high": "integer",
  "medium": "integer",
  "low": "integer",
  "safe_count": "integer",
  "risky_count": "integer",
  "by_type": {
    "scss": "integer",
    "php": "integer",
    "js": "integer",
    "astro": "integer"
  },
  "by_category": {
    "category_name": "integer",
    ...
  }
}
```

### Properties

#### total

- **Type**: integer
- **Description**: 検出された問題の総数

#### critical / high / medium / low

- **Type**: integer
- **Description**: 優先度別の問題数

#### safe_count

- **Type**: integer
- **Description**: `severity: safe` の問題数（`/fix auto` で修正可能）

#### risky_count

- **Type**: integer
- **Description**: `severity: risky` の問題数（manual review required）

#### by_type

- **Type**: object with string keys
- **Keys**: `scss`, `php`, `js`, `astro`
- **Values**: count (integer)
- **Description**: コードタイプ別の問題数

#### by_category

- **Type**: object with category name keys
- **Example keys**: `naming`, `security`, `duplication`, `performance`
- **Values**: count (integer)
- **Description**: カテゴリ別の問題数（分類できない場合はオプション）

---

## Complete Example

```json
{
  "review_date": "2026-03-03",
  "review_time": "14:30:45",
  "type": "all",
  "issues": [
    {
      "id": "scss-001",
      "type": "scss",
      "severity": "safe",
      "priority": "high",
      "category": "naming",
      "file": "src/scss/object/component/_c-button.scss",
      "line": 5,
      "column": null,
      "rule": "BEM命名違反",
      "description": "クラス名 '.c-button-primary' は BEM 命名規則に違反しています。'&-' ネストではなく '&__' を使用してください。",
      "suggestion": ".c-button { &__primary { color: #fff; } }",
      "fix_type": "safe"
    },
    {
      "id": "php-001",
      "type": "php",
      "severity": "risky",
      "priority": "critical",
      "category": "security",
      "file": "themes/test-theme/pages/page-top.php",
      "line": 24,
      "column": 8,
      "rule": "XSS（エスケープ漏れ）",
      "description": "ユーザー入力の $title がエスケープされていません。XSS 脆弱性のリスク。",
      "suggestion": "<?php echo esc_html(get_field('title')); ?>",
      "fix_type": "risky"
    },
    {
      "id": "js-001",
      "type": "js",
      "severity": "safe",
      "priority": "high",
      "category": "quality",
      "file": "src/js/modules/slider.js",
      "line": 42,
      "column": 2,
      "rule": "console.log残留",
      "description": "本番環境に console.log が残留しています。",
      "suggestion": "console.log() を削除してください。",
      "fix_type": "safe"
    },
    {
      "id": "astro-001",
      "type": "astro",
      "severity": "risky",
      "priority": "high",
      "category": "design-system",
      "file": "astro/src/pages/index.astro",
      "line": 8,
      "column": null,
      "rule": ".astro内SCSS/JSインポート違反",
      "description": ".astro ファイル内で直接 SCSS をインポートしています。SCSS/JS は Vite プラグインで独立プリコンパイルされ、<link>/<script> で読み込むルールに違反。",
      "suggestion": "<link rel=\"stylesheet\" href=\"/assets/css/pages/index/style.css\" slot=\"addCSS\" /> を使用してください。",
      "fix_type": "risky"
    }
  ],
  "summary": {
    "total": 4,
    "critical": 1,
    "high": 3,
    "medium": 0,
    "low": 0,
    "safe_count": 2,
    "risky_count": 2,
    "by_type": {
      "scss": 1,
      "php": 1,
      "js": 1,
      "astro": 1
    },
    "by_category": {
      "naming": 1,
      "security": 1,
      "quality": 1,
      "design-system": 1
    }
  },
  "verdict": "NEEDS_REVISIONS"
}
```

---

## /fix スキルとの連携

### 基本フロー

```
1. /review → review-YYYYMMDD-HHMMSS.json を生成
2. User: /fix auto
   → issues のうち severity: safe かつ fix_type: safe のみを自動修正
3. User: /fix {id}
   → issue[id] に対して code-fixer による対話的修正
4. User: /fix astro
   → type: astro の全問題に対して修正
```

### /fix の入力ファイルパース

```bash
# Step 1: review JSON を読み込む
REVIEW_FILE="latest review JSON path"
ISSUES=$(jq '.issues[]' "$REVIEW_FILE")

# Step 2: 対象フィルタリング（引数に応じて）
# /fix auto → severity: safe AND fix_type: safe のみ
# /fix {id} → id が一致するもののみ
# /fix {type} → type が一致するもののみ

# Step 3: 各 issue に対して修正実行
```

---

## Tips for Producers (/review)

### 問題 ID の採番規則

- `{type}-{number:03d}` 形式（e.g., `scss-001`, `php-042`）
- 同一セッション内では通し番号で採番
- 同一タイプ内で重複しないこと

### severity と priority の使い分け

| severity | priority | 例 |
|----------|----------|-----|
| safe | critical | デバッグコード残留（var_dump） |
| safe | high | console.log 残留 |
| safe | medium | マジックナンバー |
| risky | critical | XSS 脆弱性 |
| risky | high | ACF 空チェック漏れ |
| risky | medium | セマンティクスHTML違反 |

### fix_type の選択基準

- **safe**: grep/sed で確定的な置換が可能
  - console.log 削除
  - マジックナンバーの変数化
  - 未使用 import 削除
- **risky**: コンテキスト判断が必要
  - エスケープ関数の選択（esc_html vs esc_url）
  - BEM 命名修正（クラス名の変更が含まれる）
  - セキュリティ対応
- **manual**: 自動化不可、提案のみ
  - アーキテクチャ変更
  - 大幅なリファクタリング

---

## Related Files

- `.claude/skills/review/SKILL.md` - Review スキル本体
- `.claude/skills/fix/SKILL.md` - Fix スキル（このスキーマを入力として使用）
- `.claude/skills/review/scripts/automated-review.sh` - 機械的スキャン実装
- `.claude/rules/security.md` - セキュリティルール
- `.claude/rules/scss.md` - SCSS ルール
- `.claude/rules/wordpress.md` - WordPress ルール
