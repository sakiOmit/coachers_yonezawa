---
name: figma-prepare-eval
description: "/figma-prepareスコアリング精度をキャリブレーションデータセットで評価"
argument-hint: "[--add {source.json}] [--report] [--verbose]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
context: fork
agent: general-purpose
model: sonnet
---

# /figma-prepare-eval

## Overview

`/figma-prepare` のスコアリング式（品質スコア計算・グレード判定）の精度を、
キャリブレーションデータセットを使って定量的に評価するメタスキル。

スコアリング式を変更したとき、全テストケースで精度が落ちていないか回帰テストできる。

## Usage

```bash
/figma-prepare-eval              # 全ケース実行 → 精度レポート（デフォルト）
/figma-prepare-eval --report     # 同上
/figma-prepare-eval --verbose    # 詳細ブレイクダウン付き
/figma-prepare-eval --add <path> # 新規ケース追加（対話的）
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| --report | No | 全ケース実行（デフォルト） |
| --verbose | No | ペナルティ詳細を表示 |
| --add \<path\> | No | 新規ケースを対話的に追加 |

## Processing Flow

### --report モード（デフォルト）

```
1. .claude/data/figma-prepare-calibration.yaml を読み込み
2. 各ケースの source ファイル存在確認
3. analyze-structure.sh を各ケースに実行
4. 実績 vs 期待を比較:
   - expected_grade が null → スコア範囲のみチェック
   - expected_grade が指定 → グレード一致 + スコア範囲チェック
5. 集計メトリクス算出:
   - グレード一致率（accuracy）
   - スコア範囲内率
   - 混同行列（5x5: A/B/C/D/F）
   - ペナルティ寄与率分析
6. レポート出力（stdout + YAML）
```

### --add モード

```
1. 指定された JSON ファイルに analyze-structure.sh を実行
2. 結果を表示し、ユーザーに確認:
   - expected_grade（A/B/C/D/F/null）
   - expected_score_range
   - tags
   - notes
3. figma-prepare-calibration.yaml に追記
```

## Output

### stdout レポート

```
=== /figma-prepare Calibration Report ===
Cases: 4 | Evaluated: 3 | Pass: 3 | Skip: 1
Grade Accuracy: 100%

ID               Expected  Actual  Score (range)   Status
fixture-metadata        B       B    68.0 (60-80)   PASS
real-dirty              D       D    25.0 (15-35)   PASS
real-clean              B       B    61.8 (55-70)   PASS
fixture-dirty         N/A       B    67.0 (50-80)   PASS

Penalty Contribution:
  unnamed:   45%  ████████████████████████
  flat:      25%  █████████████
  ungrouped: 12%  ██████
  nesting:   18%  █████████
```

### YAML結果ファイル

`.claude/cache/figma/calibration-result-{timestamp}.yaml`

## Data Files

| ファイル | 用途 |
|---------|------|
| `.claude/data/figma-prepare-calibration.yaml` | キャリブレーションデータセット（永続） |
| `.claude/cache/figma/calibration-result-*.yaml` | 実行結果（一時） |

## Script

```bash
bash .claude/skills/figma-prepare-eval/scripts/run-calibration.sh [--verbose]
```

## Error Handling

| Error | Response |
|-------|----------|
| calibration.yaml not found | エラー終了 |
| analyze-structure.sh not found | エラー終了 |
| source JSON not found | 該当ケースを SKIP |
| analyze-structure.sh エラー | 該当ケースを SKIP |

## Related

- `/figma-prepare` — スコアリング対象のスキル
- `.claude/rules/figma-prepare.md` — スコア計算式の定義
- `.claude/skills/figma-prepare/KNOWN-ISSUES.md` — 既知の課題
