---
name: usage-analyzer
description: "Analyze Claude Code skill usage statistics from JSONL conversation logs"
disable-model-invocation: false
allowed-tools:
  - Bash
  - Read
context: fork
agent: general-purpose
---

# Usage Analyzer

JONLログを解析してスキル使用率をレポートする。

## Usage

```
/usage [command] [options]
```

## Commands

| Command | Description |
|---------|-------------|
| skills | スキル使用状況（デフォルト） |

## Options

| Option | Description |
|--------|-------------|
| --days N | 過去N日間を分析（デフォルト: 30） |
| --sort X | ソート順: count, name, date（デフォルト: count） |
| --csv | CSV形式で出力 |
| --report | Markdownレポートを `.claude/reports/` に保存 |

## Examples

```bash
# スキル使用状況（デフォルト）
/usage
/usage skills

# 過去7日間の分析
/usage skills --days 7

# 名前順ソート
/usage skills --sort name

# CSV出力
/usage skills --csv

# Markdownレポート保存
/usage skills --report
```

## Data Sources

- **会話ログ**: `~/.claude/projects/-home-sakiomit-proj-wordpress-template/*.jsonl`
- **検出対象**:
  1. `Skill` ツール呼び出し（assistant メッセージ内の `tool_use`）
  2. ユーザーメッセージの `/skill-name` パターン（組み込みコマンド除外）
- **スキル定義**: `.claude/skills/*/SKILL.md` から全スキル名を取得

## Output Files

| コマンド | 出力先 |
|----------|--------|
| --report | `.claude/reports/skill-usage_{timestamp}.md` |
| --csv | 標準出力（リダイレクトで保存可能） |

## Processing Flow

1. `.claude/skills/*/SKILL.md` から定義済みスキル一覧を取得
2. 全JONLログファイルをスキャン
3. Skill tool_use と /slash-command を抽出
4. 定義済みスキルと照合して使用/未使用を判定
5. レポート出力

## Implementation

```bash
# Default: skills report
python3 .claude/scripts/analyze-usage.py

# With options
python3 .claude/scripts/analyze-usage.py skills --days 7 --sort name

# CSV output
python3 .claude/scripts/analyze-usage.py skills --csv

# Save markdown report
python3 .claude/scripts/analyze-usage.py skills --report
```
