# Scripts Standard - スキルスクリプト標準規約

## Overview

全スキルの `scripts/` ディレクトリに配置するスクリプトの共通規約。
figma-implement の scripts/ パターンを基準とし、プロジェクト全体で一貫した自動化パターンを実現する。

## ディレクトリ構造

```
.claude/skills/{skill-name}/
├── SKILL.md              # スキル定義
├── scripts/              # 自動化スクリプト
│   ├── {action}.sh       # メインスクリプト
│   └── ...
├── references/           # 参照ドキュメント（任意）
└── templates/            # テンプレートファイル（任意）
```

## スクリプト規約

### 1. Exit Code

| Code | 意味 | LLM の対応 |
|------|------|-----------|
| 0 | PASS（成功） | 次のステップに進む |
| 1 | FAIL（失敗） | エラー内容を分析し、修正または停止 |

### 2. 出力フォーマット

スクリプトの結果は **JSON** で `reports/` に保存する:

```json
{
  "timestamp": "YYYYMMDD-HHMMSS",
  "type": "スクリプト種別",
  "verdict": "PASS|FAIL|NEEDS_REVIEW",
  "...": "スキル固有のデータ"
}
```

### 3. ヘッダー規約

```bash
#!/bin/bash
# {Script Name} - {1行の説明}
# Usage: bash {script-name}.sh [args]

set -uo pipefail  # 必須: 未定義変数エラー + パイプ失敗検知
```

### 4. PROJECT_ROOT の取得

```bash
PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
```

`.claude/skills/{skill}/scripts/` から3階層上がプロジェクトルート。

### 5. レポート保存先

```bash
REPORT_DIR="${PROJECT_ROOT}/reports"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$REPORT_DIR"
```

### 6. コンソール出力

```
[Phase N] Phase Name
-----------------------
  ✅ Check: PASS
  ❌ Check: FAIL
  ⚠️  Check: WARN

==================
 Summary
==================
  Report: reports/{name}-{TIMESTAMP}.json
```

### 7. LLM との連携パターン

SKILL.md での呼び出し記述:

```markdown
### Step 0: Automated Check (Script)

```bash
bash .claude/skills/{skill}/scripts/{script}.sh [args]
```

スクリプトが {items} を自動チェックし、`reports/{name}-{TIMESTAMP}.json` に結果を保存する。
スクリプト完了後にレポートを Read で読み込み、結果を踏まえて次のステップに進む。
```

## 既存スクリプト一覧

| スキル | スクリプト | 目的 |
|--------|----------|------|
| figma-implement | validate-cache.sh | キャッシュ検証 |
| figma-implement | validate-raw-jsx.sh | JSX検証 |
| figma-implement | quality-check.sh | 品質チェック |
| qa | qa-pipeline.sh | Lint + Build 統合 |
| review | automated-review.sh | 機械的レビュー |
| delivery | delivery-check.sh | 納品品質チェック |
| delivery | delivery-verify.sh | 半自動検証 |
| fix | auto-fix.sh | Safe issues 自動修正 |
| astro-to-wordpress | convert-astro-to-php.sh | 半自動変換 |
| figma-analyze | calculate-complexity.sh | 複雑度スコア計算 |
| figma-analyze | detect-shared-components.sh | 共通コンポーネント検出 |

## 未作成（Phase 2 で対応予定）

| スキル | 予定スクリプト | 提案ID |
|--------|--------------|--------|
| astro-page-generator | generate-astro-page.sh | apg-02 |
| scss-component-generator | generate-scss.sh | scg-01 |
| scss-component-generator | validate-scss-component.sh | scg-02 |
| wordpress-page-generator | generate-wp-page.sh | wpg-01 |
