---
name: qa
description: "QA 統合チェック & 修正"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Bash
  - Write
  - Glob
context: fork
agent: general-purpose
---

# QA 統合チェック & 修正

納品前の品質チェックを実行し、問題を自動修正します。

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

完全なQAワークフロー（納品前推奨）:

1. **Phase 1**: 機械的チェック（npm run check:all）
2. **Phase 2**: 機械的修正（lint --fix）
3. **Phase 3**: 人間的レビュー（production-reviewer）
4. **Phase 4**: レビュー結果に基づく修正（code-fixer）
5. **Phase 5**: 最終検証
6. **Phase 6**: 本番判定
7. **Phase 7**: 納品チェックリスト生成

### `/qa verify`

修正後の確認。問題が0件なら「納品準備完了」。

## 出力

```
📊 QA Check Results

Total Issues: 15

By Category:
- SCSS (lint-scss): 5 issues
- JavaScript (lint-js): 3 issues
- Links: 4 issues
- Images: 2 issues
- Templates: 1 issue

Next Steps:
- /qa fix       # 自動修正を実行
- /qa fix scss  # SCSS のみ修正
- /qa full      # フルQA（納品前推奨）
```

## 関連コマンド

```bash
/review all    # 詳細なコードレビュー
/fix auto      # レビュー結果から自動修正
/delivery      # 納品品質チェック
```

---

**Instructions for Claude:**

## アーキテクチャ（メモリリーク対策）

**重要**: サブエージェントのネストを禁止。メインエージェントがオーケストレーターとして直接制御する。

```
メインエージェント（このコマンド実行者）
 │
 ├─ check/fix/verify: Bash直接実行
 │
 └─ full: フェーズごとに直接制御
     ├─ Phase 1-2: Bash直接
     ├─ Phase 3: production-reviewer (Task) ─┐
     ├─ Phase 4: code-fixer (Task)          ─┴─ 必要に応じて並列可
     └─ Phase 5-7: Bash直接
```

## 実行手順

### `/qa check`

```bash
npm run check:all
```

結果を読み取り、サマリーを報告。

### `/qa fix` / `/qa fix {type}`

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

**Phase 1-2: 機械的チェック・修正（Bash直接）**
```bash
npm run check:all
npm run lint:css:fix
npm run lint:js -- --fix
npm run check:all
```

**Phase 3: 人間的レビュー（サブエージェント）**
```
Task tool:
  subagent_type: production-reviewer
  prompt: |
    QA Phase 3: 人間的レビューを実行してください。

    reports/qa-spec.json の結果を踏まえ、
    コード品質・セキュリティ・ベストプラクティスを確認。

    レビュー結果は .claude/reviews/ に保存してください。
```

**Phase 4: レビュー結果に基づく修正（サブエージェント）**
```
Task tool:
  subagent_type: code-fixer
  prompt: |
    QA Phase 4: レビュー結果に基づく修正を実行してください。

    .claude/reviews/ の最新レビューファイルを読み、
    safe 分類の問題を自動修正してください。
```

**Phase 5: 最終検証（Bash直接）**
```bash
npm run check:all
npm run build
```

**Phase 6: 本番判定**
- エラー 0 → READY
- エラーあり → NEEDS REVISIONS

**Phase 7: 納品チェックリスト**
reports/delivery-checklist.md を生成。

### `/qa verify`

```bash
npm run check:all
```

問題が0件なら「納品準備完了」を報告。

## 禁止事項

| 禁止 | 理由 |
|------|------|
| qa-agent からサブエージェント起動 | メモリリーク |
| サブエージェントのネスト | コンテキスト累積 |
| 3つ以上のサブエージェント同時起動 | WSLメモリ制限 |

## 並列起動の条件

Phase 3 と Phase 4 を並列起動する場合：
- Phase 3 の結果に Phase 4 が依存しないこと
- WSL のメモリに余裕があること（8GB以上推奨）

通常は**順次実行を推奨**。
