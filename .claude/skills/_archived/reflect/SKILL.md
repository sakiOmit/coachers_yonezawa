---
name: reflect
description: "/reflect - 自動振り返りと改善実行"
disable-model-invocation: true
allowed-tools:
  - mcp__serena__read_memory
  - mcp__serena__edit_memory
  - mcp__serena__search_for_pattern
  - Read
  - Edit
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# /reflect - 自動振り返りと改善実行

蓄積された知見を分析し、閾値を超えたパターンは**自動で改善を実行**します。

## 自動実行モード（--dangerously 対応）

**ユーザー確認なしで以下を自動実行:**
- 検出3回以上のパターン → Lintルール自動追加
- ガイドライン未記載の頻出問題 → ドキュメント自動更新
- 全ての変更 → improvement-log.md に自動記録

## 処理フロー

### Phase 1: 知見の収集（自動）

```
read_memory("common-issues-patterns.md")
read_memory("improvement-log.md")
read_memory("base-styles-reference.md")

# レビュー履歴があれば追加で分析
Read(".claude/metrics/latest-analysis.json")
```

### Phase 2: パターン分析（自動）

メモリから検出回数3回以上のパターンを抽出:

```
# 正規表現で検出回数を抽出
search_for_pattern("検出回数.*: ([3-9]|\\d{2,})",
  relative_path=".serena/memories/common-issues-patterns.md")
```

### Phase 3: 自動改善実行

**閾値超過パターンは確認なしで即実行:**

#### タイプ A: Lint ルール自動追加

```
# 自動検出可能 = Yes のパターン
Edit(".stylelintrc.json",
  old_string='"rules": {',
  new_string='"rules": {\n    "[検出した新ルール]": "error",'
)
```

#### タイプ B: ガイドライン自動更新

```
# 自動検出可能 = No のパターン
Edit("docs/coding-guidelines/[適切なファイル].md",
  old_string="## [関連セクション]",
  new_string="## [関連セクション]\n\n### [新規パターン名]\n- [問題内容]\n- [推奨対応]\n"
)
```

#### タイプ C: CLAUDE.md 自動更新（頻出5回以上）

```
Edit("CLAUDE.md",
  old_string="### SCSS（必須）",
  new_string="### SCSS（必須）\n\n- **[新ルール]**: [説明]"
)
```

### Phase 4: 変更記録（自動）

```
edit_memory("improvement-log.md", mode="literal",
  needle="## 承認済み改善\n\n| 日付 |",
  repl="## 承認済み改善\n\n| 日付 | 改善内容 | タイプ | 実装状況 | 対象ファイル |\n|------|----------|--------|----------|-------|\n| [今日] | [改善内容] | 自動実行 | 完了 | [ファイル] |\n| 日付 |"
)
```

## 出力フォーマット

```markdown
# 自動振り返りレポート - [日付]

## 分析サマリー
- 蓄積パターン数: [N]件
- 閾値超過（3回+）: [N]件
- 自動実行した改善: [N]件

## 自動実行した改善

### 1. [パターン名] → [実行したアクション]
- **検出回数**: [N]回
- **実行内容**: [Lintルール追加 / ガイドライン更新]
- **対象ファイル**: [ファイルパス]
- **ステータス**: ✅ 完了

## 未処理パターン（閾値未満）

| パターン | 検出回数 | 残り |
|---------|---------|------|
| [名前] | 2 | あと1回で自動化 |
```

## 自動更新の範囲（確認不要）

| 改善タイプ | 更新先 | 閾値 |
|-----------|--------|------|
| Lint ルール追加 | `.stylelintrc.json`, `.eslintrc.json` | 3回 |
| コーディング規約 | `docs/coding-guidelines/*.md` | 3回 |
| CLAUDE.md 更新 | `CLAUDE.md` クイックリファレンス | 5回 |
| エージェント強化 | `.claude/agents/*.md` | 3回 |
| ベーススタイル | Serena メモリ | 1回（即時） |

## 関連コマンド

- `/analyze-project` - レビュー履歴を分析
- `/suggest-rules` - 具体的なルール提案（手動確認モード）
- `/qa full` - フルQAチェック

## 注意事項

- **--dangerously モード完全対応**
- **ユーザー確認なし** - 閾値ベースで自動実行
- **ロールバック可能** - improvement-log.md に全変更を記録
- **冪等性保証** - 同じ改善は重複実行されない
