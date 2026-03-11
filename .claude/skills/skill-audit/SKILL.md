---
name: skill-audit
description: "Audit SKILL.md design quality using 5-dimension scoring. Distinct from official Skill Eval (trigger accuracy). Run when user says 'スキル監査', 'skill audit', 'スキル品質チェック'."
argument-hint: "[all|{skill-name}] [--compare {previous-report}] [--output yaml|markdown]"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
model: opus
context: fork
agent: general-purpose
---

# Skill Quality Auditor

## Dynamic Context

```
Target skills:
!`ls .claude/skills/*/SKILL.md | grep -v _archived`
```

SKILL.md の設計品質を5次元で定量評価し、改善提案を生成する。

**公式 Skill Eval との違い:**
- 公式 Skill Eval: トリガー精度テスト（pass@5 / pass^5）
- 本スキル（skill-audit）: SKILL.md の設計品質監査（5次元スコアリング）

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | スキル作成・改善完了後 |
| **後工程** | 改善提案に基づく修正作業 |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | なし |

## 使用方法

```bash
# 全スキルを監査
/skill-audit
/skill-audit all

# 特定スキルのみ監査
/skill-audit figma-implement
/skill-audit review

# 前回レポートとの比較付き再評価
/skill-audit all --compare .claude/reports/skill-audit-report.yaml

# 出力形式指定（デフォルト: yaml）
/skill-audit all --output markdown
```

## Input

| パラメータ | 必須 | 説明 |
|-----------|------|------|
| target | No | `all`（デフォルト）または特定スキル名 |
| `--compare` | No | 前回の評価レポートパス（差分表示用） |
| `--output` | No | `yaml`（デフォルト）または `markdown` |

## Output

| ファイル | 内容 |
|---------|------|
| `.claude/reports/skill-audit-report.yaml` | 全スキル監査結果（YAML） |
| `.claude/reports/skill-audit-report.md` | 全スキル監査結果（Markdown、--output markdown 時） |

## Processing Flow

### Step 1: スコアリングロジック読み込み

- **入力**: `.claude/reports/skill-scoring-methodology.yaml`
- **処理**: 5次元の定義、ランク基準、チェックリスト項目、採点 criteria を読み込む
- **出力**: 評価基準のコンテキスト
- **検証**: ファイルが存在し、dimensions セクションに5軸すべて定義されていること

### Step 2: 対象スキル収集

- **入力**: `$ARGUMENTS`（target）
- **処理**:
  - `all` または引数なし → `.claude/skills/*/SKILL.md` を全件 Glob
  - 特定スキル名 → `.claude/skills/{name}/SKILL.md` を Read
  - `_archived/` 配下は除外する
- **出力**: 評価対象の SKILL.md パスリスト
- **検証**: 対象が1件以上存在すること。0件の場合はエラー

### Step 3: 個別スキル評価（対象ごとに繰り返し）

各スキルに対して以下を実行する:

#### 3.1 ファイル読み取り

- SKILL.md 本体を Read
- `references/` ディレクトリがあれば Glob で全ファイルを Read
- `scripts/` ディレクトリがあれば Glob で全ファイルを確認
- 行数をカウント（`wc -l` で本体 + references 合計）

#### 3.2 チェックリスト判定

以下を true/false/N/A で判定する:

**frontmatter:**

| ID | 項目 | 判定方法 |
|----|------|---------|
| name | name フィールド | フロントマターに存在するか |
| description | description 品質 | 存在し、簡潔（1-2文）でトリガー意図が明確か。コンテキスト予算（16K文字制限）内で簡潔に収まっているか |
| invocation_control | 起動制御 | 用途に応じた設定か（ユーザー直接呼び出し: `disable-model-invocation: false`、内部専用: `true`、Claude専用: `user-invocable: false`） |
| context_fork | メモリ最適化 | `context: fork` が設定されているか |
| allowed_tools | ツール制限 | allowed-tools リストが存在し、最小権限原則に従っているか |
| argument_hint | 引数フォーマット | argument-hint が設定されているか |
| model_specified | モデル指定 | `model:` で適切なモデルが指定されているか（探索系: haiku/sonnet、実装系: opus）。未指定でも妥当なら N/A |
| skill_dependencies | 依存スキル | `skills:` で必要な依存スキルがプリロードされているか。不要なら N/A |

**body:**

| ID | 項目 | 判定方法 |
|----|------|---------|
| numbered_steps | 番号付きステップ | Processing Flow に番号付きリストがあるか |
| io_specified | 入出力定義 | Input/Output セクションが存在するか |
| error_handling | エラー処理 | Error Handling セクションが存在するか |
| variable_substitution | 引数パース | `$ARGUMENTS` または位置引数（`$0`, `$1`...`$N`）の使用があるか |
| dynamic_context | 動的コンテキスト | 動的コンテキスト注入（感嘆符+バッククォート構文）の使用があるか |
| skill_hooks | スキル固有フック | フロントマターに `hooks:` 定義があるか。不要なら N/A |

**structure:**

| ID | 項目 | 判定方法 |
|----|------|---------|
| supporting_files | サポートファイル | references/ または scripts/ が存在するか |
| under_1000_lines | 1000行以内 | SKILL.md 本体の行数 |
| agent_integration | エージェント連携 | Task tool でのサブエージェント呼び出し定義があるか |

#### 3.3 5次元スコアリング

methodology.yaml の `dimensions.{axis}.criteria` に照らして各軸を 0.0-10.0（0.5刻み）で採点する。

**採点ルール:**
- criteria の4段階（9.0-10.0 / 7.0-8.9 / 5.0-6.9 / 0.0-4.9）のうち、最も一致するレンジを選ぶ
- レンジ内の微調整は criteria との一致度で 0.5 刻みで決定
- チェックリスト結果は参考指標（直接的な加点/減点ではない）
- 同一プロジェクト内の相対比較も考慮する

#### 3.4 改善提案生成

- スコアが最も低い次元に関連する改善を最優先
- 具体的で実行可能なアクション（「改善すべき」ではなく「〇〇を追加する」）
- チェックリストで false の項目に対応する改善を含める
- 各スキル3項目

### Step 4: 横断分析

- **処理**:
  - 全スキルのスコア集計（平均、最高、最低）
  - strengths: プロジェクト全体で優れている点
  - weaknesses: 「N/M スキルで〇〇が未対応」の形式で定量化
  - recommendations: priority 付き（high/medium/low）の改善提案
- **出力**: best_practices_summary セクション

### Step 5: 前回比較（--compare 指定時のみ）

- **入力**: 前回の評価レポート
- **処理**: 各スキルのスコア差分を算出（+0.5, -1.0 等）
- **出力**: comparison セクション（前回→今回のスコア変化、ランク変動）

### Step 6: レポート出力

- **処理**: 全データを YAML（または Markdown）形式で整形
- **出力**: `.claude/reports/skill-audit-report.yaml`（上書き確認なし）
- **検証**: YAML として有効な構文であること

#### 6.1 YAML 構文検証（必須）

レポート出力後、以下のコマンドで YAML 構文を検証する:

```bash
bash .claude/skills/skill-audit/scripts/validate-yaml.sh {output-file}
```

例:
```bash
bash .claude/skills/skill-audit/scripts/validate-yaml.sh .claude/reports/skill-audit-report.yaml
```

- **入力**: 出力したレポートファイル
- **出力**: PASS/FAIL メッセージ
- **動作**: PASS であればそのまま終了。FAIL の場合は YAML 構文を修正し、再度 Write で出力してから再検証

### Step 7: サマリー表示

ユーザーに以下を表示:

```
## スキル監査完了

| スキル | ランク | 平均 | Prac | Clar | Auto | Qual | Impa | 変動 |
|--------|--------|------|------|------|------|------|------|------|
| figma-implement | S | 9.2 | 9.5 | 9.0 | 9.0 | 9.0 | 9.5 | +0.6 |
| ...    | ...    | ...  | ...  | ...  | ...  | ...  | ...  | ...  |

全体平均: 8.2 (A) ← 前回 7.5 (B) から +0.7
S: 1, A: 5, B: 3, C: 1, D: 0

レポート: .claude/reports/skill-audit-report.yaml
```

## YAML 出力テンプレート

```yaml
metadata:
  project: "{プロジェクト名}"
  total_skills: {N}
  evaluation_date: "YYYY-MM-DD"
  evaluator: "Claude {model}"
  scoring_system: "5-dimension (0.0-10.0)"
  methodology: ".claude/reports/skill-scoring-methodology.yaml"
  note: "設計品質監査（skill-audit）。公式 Skill Eval（トリガー精度テスト）とは別物。"

summary:
  average_score: {N.N}
  overall_rank: "{rank}"
  s_rank_count: {N}
  a_rank_count: {N}
  b_rank_count: {N}
  c_rank_count: {N}
  d_rank_count: {N}
  top_skill: "{name}"
  needs_improvement: "{name}"

# comparison セクション（--compare 指定時のみ）
comparison:
  previous_report: "{path}"
  previous_date: "YYYY-MM-DD"
  score_changes:
    - skill: "{name}"
      previous: {N.N}
      current: {N.N}
      delta: "{+/-N.N}"
      rank_change: "{B → A}"

skills:
  - name: "{skill-name}"
    rank: "{S|A|B|C|D}"
    scores:
      practicality: {N.N}
      clarity: {N.N}
      automation: {N.N}
      quality: {N.N}
      impact: {N.N}
    average: {N.N}
    line_count: {N}
    checklist:
      frontmatter:
        name: {true|false}
        description: {true|false}
        invocation_control: {true|false}
        context_fork: {true|false}
        allowed_tools: {true|false}
        argument_hint: {true|false}
        model_specified: {true|false|"N/A"}
        skill_dependencies: {true|false|"N/A"}
      body:
        numbered_steps: {true|false}
        io_specified: {true|false}
        error_handling: {true|false}
        variable_substitution: {true|false}
        dynamic_context: {true|false}
        skill_hooks: {true|false|"N/A"}
      structure:
        supporting_files: {true|false}
        under_1000_lines: {true|false}
        agent_integration: {true|false}
    improvements:
      - "{改善提案1}"
      - "{改善提案2}"
      - "{改善提案3}"
    notes: |
      {所見}

best_practices_summary:
  strengths:
    - "{強み1}"
  weaknesses:
    - "{弱み1}"
  recommendations:
    - priority: high
      description: "{提案}"
```

## Agent Integration

Step 2（対象スキル収集）で大量のファイル読み取りが必要な場合、Explore エージェントに委譲可能:

```
Task tool:
  subagent_type: Explore
  prompt: |
    以下のスキルの SKILL.md を全件読み取り、構造情報を収集してください:
    - パス: .claude/skills/*/SKILL.md（_archived/ 除外）

    各スキルについて以下を抽出:
    1. フロントマター全フィールド
    2. references/ ディレクトリの有無とファイル一覧
    3. scripts/ ディレクトリの有無とファイル一覧
    4. SKILL.md 本体の行数
    5. Processing Flow の有無
    6. Error Handling の有無
    7. Agent Integration の有無

    結果を JSON 形式で返してください。
```

**委譲条件**: 対象スキル数 >= 8 の場合（全件監査時）
**Fallback**: エージェント不在時は直接 Glob + Read で順次収集

## Error Handling

| Error | Recovery |
|-------|----------|
| methodology.yaml が存在しない | エラーメッセージを表示し、先にメソドロジーファイルの作成を促す |
| 指定スキルが存在しない | 利用可能なスキル一覧を表示する |
| _archived/ のスキルが指定された | アーカイブ済みであることを通知し、評価対象外とする |
| 前回レポートが存在しない（--compare） | 比較なしで新規評価として実行する |
| YAML 出力が構文エラー | Bash で `python3 -c "import yaml; yaml.safe_load(open(...))"` で検証し修正 |

---

**Instructions for Claude:**

## 引数パース

`$ARGUMENTS` を以下のルールでパースする:

1. 引数なし → target=`all`, compare=`null`, output=`yaml`
2. 第1引数が `all` またはスキル名 → target に設定
3. `--compare {path}` → 前回レポートパスを設定
4. `--output yaml|markdown` → 出力形式を設定

## 実行手順

1. `.claude/reports/skill-scoring-methodology.yaml` を Read で読み込む
   - 存在しない場合: エラーメッセージを表示して終了
2. target に応じて `.claude/skills/*/SKILL.md` を Glob + Read
   - `_archived/` は除外
3. 各スキルに対して Step 3.1〜3.4 を順次実行
   - **重要**: 全スキルの SKILL.md を先に全件読み込んでから採点に入る（相対比較のため）
   - references/ や scripts/ があれば Glob で確認
4. Step 4 の横断分析を実行
5. `--compare` が指定されていれば Step 5 を実行
6. レポートを Write で出力
   - **Step 6.1 で validate-yaml.sh を実行**: `bash .claude/skills/skill-audit/scripts/validate-yaml.sh {出力ファイル}`
   - FAIL の場合は YAML 構文を修正し、再度出力
7. Step 7 のサマリーテーブルをユーザーに表示

## 採点時の注意

- **省略禁止**: 全スキルの全5軸を採点する。「前回と同じ」で省略しない
- **具体的根拠**: notes に採点の根拠を記述する。「良い」「悪い」だけではなく、具体的な箇所を引用する
- **相対比較**: 同一プロジェクト内のスキル間で一貫した基準を適用する
- **改善提案は実行可能に**: 「〇〇を改善すべき」ではなく「〇〇を追加する」のように具体的に

## 出力言語

- YAML のキー名: 英語
- notes / improvements / strengths / weaknesses / recommendations: 日本語
- サマリーテーブル: 日本語

## Scripts

| スクリプト | 目的 | 入力 | 出力 |
|-----------|------|------|------|
| `scripts/validate-yaml.sh` | 出力 YAML の構文検証 | YAML file path | Validation result (text) |

### validate-yaml.sh

```bash
bash .claude/skills/skill-audit/scripts/validate-yaml.sh <yaml-file>
# Example:
bash .claude/skills/skill-audit/scripts/validate-yaml.sh .claude/reports/skill-audit-report.yaml
```

- **入力**: YAML ファイルパス
- **出力**: PASS/FAIL + トップレベルキー一覧
- **依存**: python3 + PyYAML（なければ基本チェックにフォールバック）
- **終了コード**: 0=VALID, 1=INVALID
