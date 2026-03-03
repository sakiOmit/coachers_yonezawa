---
name: qa
description: "QA 統合チェック & 修正"
argument-hint: "[check|fix|full|verify]"
disable-model-invocation: false
allowed-tools:
  - Task
  - Read
  - Bash
  - Write
  - Glob
  - Grep
  - Edit
model: opus
context: fork
agent: general-purpose
---

# QA 統合チェック & 修正

## Dynamic Context

```
QA scripts available:
!`ls scripts/qa/ 2>/dev/null || echo "(empty)"`
```

納品前の品質チェックを実行し、問題を自動修正します。

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | `/review` → `/fix` 完了後（推奨） |
| **後工程** | `/delivery` |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | qa-agent, production-reviewer, code-fixer エージェント |

## 使用方法

```bash
# チェックのみ（修正しない）
/qa check

# チェック + 機械的修正
/qa fix

# チェック + 修正（特定タイプのみ）
/qa fix scss     # SCSS のみ
/qa fix js       # JavaScript のみ
/qa fix php      # PHP のみ

# フルQA（機械的 + 人間的レビュー + 修正）← 納品前推奨
/qa full

# 再チェック（修正後の確認）
/qa verify
```

## サブコマンド

| コマンド | 説明 |
|----------|------|
| `check` | チェックのみ、qa-spec.json を生成 |
| `fix` | チェック後、機械的な自動修正を実行 |
| `fix {type}` | 特定タイプ（scss/js/php）のみ修正 |
| `full` | 完全QA（機械的 + 人間的レビュー + 修正） |
| `verify` | 修正後の再チェック |

## 何をするか

### `/qa check`

`npm run qa:check` を実行し、以下をチェック:
- Build (vite build)
- Lint SCSS (stylelint + BEM nesting)
- Lint JS (eslint)
- Lint PHP (phpcs)
- HTML構造・セマンティック
- リンクチェック
- 画像チェック

結果は `reports/qa-spec.json` と `reports/qa-report.md` に保存。

### `/qa fix`

1. `npm run qa:check` を実行
2. `reports/qa-spec.json` を読み込み
3. 問題カテゴリに応じて修正:
   - SCSS: `npm run lint:css:fix`
   - JS: `npm run lint:js -- --fix`
   - PHP: 自動修正可能な問題を修正
4. 再度 `npm run qa:check` で検証

### `/qa full`

完全なQAワークフロー（納品前推奨）: Phase 1-7 の7段階で機械的チェック→修正→人間的レビュー→最終検証→納品判定を実施。

**詳細**: → [references/full-workflow-phases.md](references/full-workflow-phases.md)（7フェーズ詳細 + 禁止事項 + 出力例）

### `/qa verify`

修正後の確認。問題が0件なら「納品準備完了」。

## 関連コマンド

```bash
/review all    # 詳細なコードレビュー
/fix auto      # レビュー結果から自動修正
/delivery      # 納品品質チェック
```

---

**Instructions for Claude:**

## 実行手順

### `/qa check`

Phase 1 では最初に `bash .claude/skills/qa/scripts/qa-pipeline.sh` を実行する。スクリプトが SCSS Lint・JS Lint・PHP Syntax・Build の4項目を自動チェックし、`reports/qa-spec-{TIMESTAMP}.json` に結果を保存する。スクリプト終了後に結果 JSON を読み取り、サマリーを報告する。

```bash
bash .claude/skills/qa/scripts/qa-pipeline.sh
```

スクリプトが利用できない場合のフォールバック:
```bash
npm run check:all
```

結果を読み取り、サマリーを報告。

### `/qa fix` / `/qa fix {type}`

Phase 1 では `bash .claude/skills/qa/scripts/qa-pipeline.sh --fix` を実行する。`--fix` フラグにより自動修正まで実行される。

```bash
bash .claude/skills/qa/scripts/qa-pipeline.sh --fix
```

スクリプトが利用できない場合のフォールバック:
```bash
# Phase 1: チェック
npm run check:all

# Phase 2: 自動修正
npm run lint:css:fix   # SCSS
npm run lint:js -- --fix  # JS

# Phase 3: 再検証
npm run check:all
```

結果を報告。

### `/qa full`（フラットなオーケストレーション）

**詳細**: → [references/full-workflow-phases.md](references/full-workflow-phases.md)（Phase 1-7 実行手順 + サブエージェント委譲 + フォールバック）

### `/qa verify`

```bash
npm run check:all
```

問題が0件なら「納品準備完了」を報告。

## Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| `npm run check:all` 失敗 | exit code != 0 | 個別コマンド (`npm run lint:css`, `npm run lint:js`, `npm run build`) を順番に実行して問題を特定 |
| qa-pipeline.sh が存在しない | File not found | フォールバックとして `npm run check:all` を直接実行 |
| production-reviewer 不在 | Task tool 失敗 | Claude が直接 Read/Grep でコードレビューを実行し、`.claude/reviews/` にレポートを Write |
| code-fixer 不在 | Task tool 失敗 | Claude が直接 Edit ツールで Safe issues を修正 |
| WSL メモリ不足 | サブエージェント起動失敗 / OOM | サブエージェントを使用せず、Bash 直接実行のみで処理。Phase 3-4 をスキップし Phase 5 へ |
| Phase 3-4 ループ超過 | 2回目の Phase 5 でも問題残存 | ループを停止し、残存課題リストをユーザーに提示。手動修正を案内 |
| レポートディレクトリ不在 | `reports/` が存在しない | `mkdir -p reports` で自動作成 |

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | exit code |
|-----------|------|-----------|
| `scripts/qa-pipeline.sh [--fix]` | Lint + Build 統合チェック | 0=PASS, 1=FAIL |

**出力**: `reports/qa-spec-{TIMESTAMP}.json`
