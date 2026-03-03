---
name: suggest-rules
description: "/suggest-rules - ルール改善提案コマンド"
disable-model-invocation: true
allowed-tools:
  - mcp__serena__read_memory
  - Read
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# /suggest-rules - ルール改善提案コマンド

レビュー分析結果から、新しいLintルールやガイドライン更新を提案します。

## 実行手順

1. 最新の分析結果を取得:
```bash
cat .claude/metrics/latest-analysis.json
```

2. 分析結果がない場合は、まず `/analyze-project` を実行

3. 頻出パターンを確認し、以下を提案:
   - **Lintルール追加**: 自動検出可能なパターン
   - **ガイドライン更新**: 人間の判断が必要なパターン
   - **エージェント改善**: チェックロジックの強化

## 提案形式

### Lintルール提案の場合

```markdown
## 提案: [ルール名]

**対象パターン**: [検出されたパターン]
**発生件数**: X回
**推奨アクション**:

1. `.stylelintrc.json` に以下を追加:
   ```json
   "rules": { ... }
   ```

2. 動作確認: `npm run lint:css`
```

### ガイドライン更新提案の場合

```markdown
## 提案: [ガイドライン名]

**対象パターン**: [検出されたパターン]
**発生件数**: X回
**推奨アクション**:

1. `docs/coding-guidelines/XX.md` に以下を追記:
   - [新ルール内容]

2. CLAUDE.md のクイックリファレンスを更新
```

## 承認フロー

1. 提案を確認
2. ユーザーが承認 → 実装
3. 却下 → 理由を記録（今後の参考）

## Serenaメモリ連携

分析結果に加えて、Serenaメモリも参照:

```
# 頻出問題パターンを確認
read_memory("common-issues-patterns.md")

# 改善履歴を確認
read_memory("improvement-log.md")
```

メモリに蓄積されたパターンも提案の根拠として活用してください。

## 関連コマンド

- `/reflect` - メモリを含む包括的な振り返りと改善提案（上位コマンド）
- `/analyze-project` - レビュー履歴を分析
- `/qa full` - フルQAチェック

## 補足

`/suggest-rules` は `/reflect` のサブセットです。

- **`/suggest-rules`**: Lintルール・ガイドライン更新の具体的提案に特化
- **`/reflect`**: より包括的な振り返り（メモリ分析 + 承認フロー + 自動実装）

頻出パターンの分析や定期的な改善には `/reflect` を推奨します。
