---
name: figma-prepare-improve
description: "Interactive feedback loop for figma-prepare quality improvement — detect, fix, and document issues automatically"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
  - AskUserQuestion
context: fork
agent: general-purpose
---

# figma-prepare-improve

## Overview

`/figma-prepare` のコード品質を対話的に改善するフィードバックループスキル。
自動検出 → 修正 → 文書化の3ステップを繰り返し、全テスト・QAがグリーンになるまで継続する。

## Usage

```
/figma-prepare-improve [--max-rounds N]
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| --max-rounds | No | 5 | 最大ループ反復数 |

## Processing Flow

### ループ構造

```
for round in 1..max_rounds:
  Step 1: 自動検出（Automated Detection）
  Step 2: 修正（Fix）
  Step 3: 文書化（Document）
  → 全クリーンなら終了
```

### Step 1: 自動検出（Automated Detection）

2つの検出レイヤーを実行する。

#### Layer 1: feedback-loop.sh（既存QA + テスト）

```bash
cd .claude/skills/figma-prepare
bash tests/feedback-loop.sh --max-rounds 1
```

QA 5項目 + テストスイートの結果を収集。

#### Layer 2: 深層コード解析（新規）

feedback-loop.sh に含まれない以下の品質チェックを実行:

1. **コード重複検出**
   - 全スクリプト（`scripts/*.sh`）間で同一関数・ロジックの重複を検出
   - `figma_utils.py` に統合すべき共通ロジックを特定
   - 検出方法: Grep で関数定義を抽出し、類似パターンを比較

2. **ドキュメント整合性チェック**
   - `phase-details.md` / `SKILL.md` の記述と実コードの乖離を検出
   - ステップ数、ファイルパス、関数名の不一致
   - 検出方法: ドキュメント内の参照パスを Glob で存在確認

3. **エッジケース分析**
   - 空入力、巨大入力、特殊文字（Unicode、制御文字）での挙動
   - テストで未カバーの境界条件を特定
   - 検出方法: テストケースと関数シグネチャの突合

4. **テストカバレッジ**
   - `figma_utils.py` の全 public 関数がテストされているか
   - 各スクリプトの主要分岐がテストされているか
   - 検出方法: Grep で関数定義を抽出し、テストファイルでの参照を確認

5. **figma_utils.py 統合漏れ**
   - 各スクリプト内で直接定義されている共通ロジック
   - `figma_utils.py` へ移動すべき関数を特定
   - 検出方法: スクリプト内の Python インライン定義を解析

#### 検出結果の出力形式

```
=== Round N: Detection Results ===

[feedback-loop.sh]
  QA: X issues found
  Tests: Y passed, Z failed

[Deep Analysis]
  Code Duplication: N items
  Doc Inconsistency: N items
  Edge Cases: N items
  Test Coverage Gaps: N items
  Utils Integration: N items

Total: XX issues detected
```

### Step 2: 修正（Fix）

検出された課題を1件ずつ修正する。

#### 修正フロー

```
for each issue:
  1. 課題の詳細を表示
  2. 修正方針を決定
     - 自動修正可能 → 修正実行
     - 設計判断が必要 → AskUserQuestion でユーザーに確認
     - 修正不可 → スキップし理由を記録
  3. 修正後に回帰テスト実行
     bash tests/run-tests.sh
  4. 回帰あり → 修正をロールバック、別アプローチを検討
```

#### 修正の優先順位

| 優先度 | カテゴリ | 例 |
|--------|---------|-----|
| 1 (最高) | テスト失敗 | アサーション不一致 |
| 2 | QA エラー | ShellCheck警告、未使用変数 |
| 3 | コード重複 | 共通ロジックの統合 |
| 4 | ドキュメント乖離 | パス不一致、ステップ数ズレ |
| 5 (最低) | カバレッジ改善 | テスト追加 |

### Step 3: 文書化（Document）

#### KNOWN-ISSUES.md 更新

- 新規発見 → Issue 起票（次の Issue 番号を自動採番）
- 修正済み → `FIXED` マーク付与

#### RESOLVED-ISSUES.md 更新

- `FIXED` マークの Issue → 詳細を RESOLVED-ISSUES.md に移動
- 原因、修正内容、影響範囲を記録

#### 終了条件

```
if tests: all passed AND qa: all clean:
  → ループ終了、サマリー出力
else:
  → 次のラウンドへ
```

### 終了時サマリー

```
=== Feedback Loop Complete ===

Rounds: N
Issues Found: XX
Issues Fixed: YY
Issues Skipped: ZZ (with reasons)

Tests: 68 passed, 0 failed
QA: All clean

Updated Files:
  - KNOWN-ISSUES.md (N new issues)
  - RESOLVED-ISSUES.md (M resolved)
  - [modified source files]
```

## Error Handling

| Error | Response |
|-------|----------|
| feedback-loop.sh not found | エラー終了、パスを確認 |
| テスト実行クラッシュ | スタックトレース表示、修正を試行 |
| max-rounds 超過 | 残課題をサマリー表示して終了 |
| 修正による回帰 | ロールバックし別アプローチを検討 |

## Working Directory

```
.claude/skills/figma-prepare/
```

## Related Files

| File | Purpose |
|------|---------|
| tests/run-tests.sh | テストスイート |
| tests/feedback-loop.sh | QA + テスト自動実行 |
| KNOWN-ISSUES.md | 既知の課題一覧 |
| RESOLVED-ISSUES.md | 解決済み課題一覧 |
| lib/figma_utils.py | 共通ユーティリティ |
| scripts/*.sh | 各フェーズスクリプト |
