# QA Full Workflow Phases

## `/qa full` 7フェーズ詳細

完全なQAワークフロー（納品前推奨）:

### Phase 1: 機械的チェック（npm run check:all）

- **成功条件**: exit code 0 かつ reports/qa-spec.json 生成済み
- **失敗条件**: ビルドエラー → エラー内容を表示して停止

### Phase 2: 機械的修正（lint --fix）

- **成功条件**: --fix 実行後に再チェックで問題減少
- **失敗条件**: fix 実行不可 → Phase 3 に進み手動修正を指示

### Phase 3: 人間的レビュー（production-reviewer）

- **成功条件**: レビューレポート生成（.claude/reviews/ に保存）
- **失敗条件**: production-reviewer 不在 → Fallback で直接レビュー

### Phase 4: レビュー結果に基づく修正（code-fixer）

- **成功条件**: Safe issues 全件修正完了
- **失敗条件**: code-fixer 不在 → Fallback で直接修正

### Phase 5: 最終検証

- **成功条件**: check:all が exit code 0
- **失敗条件**: 残存問題あり → Phase 3 に戻る（最大2回）

### Phase 6: 本番判定

- **成功条件**: READY 判定
- **失敗条件**: NEEDS REVISIONS → 残課題リストをユーザーに提示

### Phase 7: 納品チェックリスト生成

- **成功条件**: reports/qa-checklist.md 生成済み
- **失敗条件**: なし（常に生成可能）

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

## 禁止事項

| 禁止 | 理由 |
|------|------|
| qa-agent からサブエージェント起動 | メモリリーク |
| サブエージェントのネスト | コンテキスト累積 |
| 3つ以上のサブエージェント同時起動 | WSLメモリ制限 |

## 並列起動の条件

Phase 3 と Phase 4 を並列起動する場合：
- Phase 3 の結果に Phase 4 が依存しないこと
- **WSL メモリ確認**: 以下コマンドで確認
  ```bash
  free -m | awk '/Mem:/ {print $7}'
  ```
  - **> 512MB**: 並列実行可能（Phase 3 と Phase 4 を同時起動）
  - **<= 512MB**: **順次実行に変更**（Phase 3 完了後に Phase 4 を実行）

通常は**順次実行を推奨**（メモリ保護のため）。

## `/qa full` 実行手順（Instructions for Claude）

**Phase 1-2: 機械的チェック・修正（Bash直接）**

最初に `bash .claude/skills/qa/scripts/qa-pipeline.sh --fix` を実行する。

```bash
bash .claude/skills/qa/scripts/qa-pipeline.sh --fix
```

スクリプトが利用できない場合のフォールバック:
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

## Output Examples

### `/qa check` Output

```bash
$ /qa check

🔍 QA Check Phase 1: Starting checks...
✓ Build successful (0 errors)
⚠ SCSS Lint: 2 warnings in src/scss/object/project/
✓ JS Lint: No issues found
✓ PHP Syntax: All files OK
📊 QA Check Complete
  • Total Issues: 2
  • Reports saved to: reports/qa-spec.json
  • Recommendation: /qa fix scss
```

### `/qa fix` Output

```bash
$ /qa fix

🔍 QA Check Phase 1: Starting checks...
✓ Build successful
⚠ Found 2 SCSS issues
🔧 QA Fix Phase 2: Auto-fixing...
✓ SCSS fixed: 2 issues resolved
✓ JS Lint: No fixes needed
✓ PHP: No fixes needed
✅ Final verification: All checks passed
  • Fixed issues: 2
  • Reports: reports/qa-spec.json
```
