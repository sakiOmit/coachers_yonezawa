---
name: docs-evaluate
description: "Evaluate docs/ directory quality using 5-axis scoring (SSOT, Accuracy, Utility, Structure, Maintainability). Run when user says 'docs評価', 'docs evaluate', 'ドキュメント評価'."
argument-hint: "[all|{category}] [--compare {previous-report}] [--output yaml|markdown]"
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

# Documentation Quality Evaluator

## Dynamic Context

```
Target docs:
!`find docs/ -name "*.md" -type f | sort`

SSOT sources:
!`ls .claude/rules/*.md`
!`echo "CLAUDE.md"`
!`ls .claude/agents/README.md 2>/dev/null`
```

`docs/` ディレクトリの全ドキュメントを5軸で定量評価し、改善アクションを生成する。

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | ドキュメント作成・更新完了後 |
| **後工程** | 改善提案に基づくドキュメント修正 |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | なし |

## 使用方法

```bash
# 全ドキュメントを評価
/docs-evaluate
/docs-evaluate all

# カテゴリ単位で評価
/docs-evaluate coding-guidelines
/docs-evaluate claude-guide
/docs-evaluate setup

# 前回レポートとの比較付き
/docs-evaluate all --compare .claude/reports/docs-evaluation-report.yaml

# 出力形式指定（デフォルト: yaml）
/docs-evaluate all --output markdown
```

## Input

| パラメータ | 必須 | 説明 |
|-----------|------|------|
| target | No | `all`（デフォルト）またはカテゴリ名（docs/ 直下のディレクトリ名） |
| `--compare` | No | 前回の評価レポートパス（差分表示用） |
| `--output` | No | `yaml`（デフォルト）または `markdown` |

## Output

| ファイル | 内容 |
|---------|------|
| `.claude/reports/docs-evaluation-report.yaml` | 全ドキュメント評価結果（YAML） |

## 評価5軸

### 軸定義

| # | 軸 | 重み | 説明 |
|---|---|---|---|
| 1 | **SSOT整合性** (ssot) | ×1.5 | `.claude/rules/`やCLAUDE.mdとの重複・矛盾の有無 |
| 2 | **正確性** (accuracy) | ×1.5 | 記載パス・API・設定が現在のコードと一致 |
| 3 | **実用性** (utility) | ×1.0 | 開発タスクでの有用度、独自価値の有無 |
| 4 | **構造品質** (structure) | ×1.0 | 粒度・分類・ナビゲーション・可読性 |
| 5 | **保守性** (maintainability) | ×1.0 | 将来の更新コスト、壊れやすさ |

**加重合計: 30点満点**（各軸1-5点、重み適用後合計）

### スコアリング基準（各軸共通）

| Score | 定義 |
|---|---|
| 5 | 模範的。問題なし。他プロジェクトの参考になる |
| 4 | 良好。軽微な改善点のみ |
| 3 | 許容範囲。明確な改善点がある |
| 2 | 問題あり。早期対応が必要 |
| 1 | 深刻。根本的な見直しが必要 |

### 軸別の詳細基準

#### SSOT整合性 (ssot)

| Score | 基準 |
|---|---|
| 5 | SSOT参照のみで独自の重複なし。参照先が明示されている |
| 4 | 軽微な重複あるが参照元が明示されている |
| 3 | 部分的に重複し、参照元の明示がない |
| 2 | 大幅な重複があり、内容に矛盾がある |
| 1 | 完全なコピー。SSOT違反が明白 |

**SSOT参照先一覧:**

| docs/ ファイル | 正のソース (SSOT) |
|---|---|
| agents.md | `.claude/agents/README.md` |
| skills.md | `.claude/skills/*/SKILL.md` |
| 02-scss-design.md | `.claude/rules/scss.md` |
| 03-html-structure.md | `.claude/rules/wordpress.md` |
| 03-template-parts.md | `.claude/rules/wordpress.md` |
| 03-image-handling.md | `.claude/rules/wordpress.md` |
| 03-sanitization.md | `.claude/rules/security.md` |
| scss/naming.md | `.claude/rules/scss.md` |
| scss/responsive.md | `.claude/rules/scss.md` |
| scss/base-styles.md | `.claude/rules/scss.md` |

#### 正確性 (accuracy)

| Score | 基準 |
|---|---|
| 5 | 全てのパス・API・設定値が実在し、コードと一致 |
| 4 | 1-2件の軽微な不正確さ（タイポ等） |
| 3 | 一部のパスや設定が古いが、核心は正確 |
| 2 | 複数の不正確な記述がある |
| 1 | 大半の記述が実態と乖離 |

#### 実用性 (utility)

| Score | 基準 |
|---|---|
| 5 | 他のどこにもない独自価値がある。実タスクで頻繁に参照される |
| 4 | 有用だが、一部は他ドキュメントで代替可能 |
| 3 | 有用だが、SSOT元を読めば十分な内容が多い |
| 2 | 独自価値が薄い。ほぼ他ドキュメントの劣化コピー |
| 1 | 存在意義が不明。削除しても影響なし |

#### 構造品質 (structure)

| Score | 基準 |
|---|---|
| 5 | 適切な粒度、明確な見出し構造、コード例・表を効果的に使用 |
| 4 | 概ね良好だが、一部セクションの粒度にバラつき |
| 3 | 構造はあるが、長すぎる/短すぎるセクションがある |
| 2 | 構造が不明確、情報の探しにくさがある |
| 1 | 構造なし、テキストの羅列 |

#### 保守性 (maintainability)

| Score | 基準 |
|---|---|
| 5 | 変更に強い構造。SSOT参照で自動追従、ハードコード最小 |
| 4 | 概ね保守しやすいが、一部ハードコード値あり |
| 3 | 手動更新が必要な箇所が複数ある |
| 2 | 複数箇所の同時更新が必要、壊れやすい |
| 1 | 更新困難。修正時に矛盾が発生しやすい |

## Processing Flow

### Phase 1: 自動チェック（機械的検証）

#### Step 1: SSOT重複検出

- **入力**: `docs/` 全ファイル、`.claude/rules/*.md`、`CLAUDE.md`
- **処理**:
  1. 各 docs ファイルを Read
  2. 対応する SSOT ソースを Read
  3. 行単位で類似度を検出（完全一致行 / 部分一致行をカウント）
  4. 重複率（%）を算出
- **出力**: ファイルごとの重複率と重複箇所リスト
- **ツール**: Grep で共通フレーズ検索、Read で内容比較

```
重複率の算出方法:
- docs ファイルの各行から空行・見出し行を除外
- 残りの行を SSOT ソースと照合
- 完全一致行数 / 有効行数 × 100 = 重複率(%)
```

#### Step 2: パス存在検証

- **入力**: 各 docs ファイル内に記載されたファイルパス
- **処理**:
  1. 各ファイルからパスパターンを正規表現で抽出
     - `themes/`, `src/`, `.claude/`, `astro/`, `config/`, `scripts/`, `docker/` で始まるパス
     - `{{THEME_NAME}}` は実際のテーマディレクトリ名に置換して検証
  2. Glob / Bash で存在確認
  3. 存在しないパスをリスト化
- **出力**: 不在パスリスト（ファイル名 + 行番号 + パス）
- **除外**: URL（http/https）、wp-admin パス、動的パス（$variable）

#### Step 3: ファイルメトリクス収集

- **入力**: `docs/` 全ファイル
- **処理**:
  1. 各ファイルの行数カウント
  2. `git log -1 --format="%ai" -- {file}` で最終更新日取得
  3. 中央値・平均値・標準偏差を算出
  4. 外れ値検出（中央値の3倍以上 or 1/3以下）
- **出力**: ファイルメトリクステーブル

#### Step 4: 内部リンク検証

- **入力**: 各 docs ファイル内のマークダウンリンク `[text](path)`
- **処理**:
  1. docs 内の相互参照リンクを抽出
  2. リンク先ファイルの存在確認
- **出力**: リンク切れリスト

### Phase 2: AI評価（LLM判定）

#### Step 5: ファイル別スコアリング

各ファイルに対して以下を実行:

1. ファイル全文を Read
2. Phase 1 の自動チェック結果を参照
3. 5軸それぞれを 1-5 で採点
4. 加重合計を算出
5. 改善アクションを生成（最大3件）

**採点時の入力情報:**

| 情報 | ソース |
|---|---|
| 重複率 | Step 1 |
| 不在パス数 | Step 2 |
| 行数・更新日 | Step 3 |
| リンク切れ数 | Step 4 |
| ファイル全文 | Read |
| SSOT対応ソース | Read |

#### Step 6: カテゴリ別分析

- **処理**:
  - docs/ 直下のディレクトリ（カテゴリ）ごとに集計
  - カテゴリ平均スコア
  - カテゴリ内の問題パターン
- **出力**: カテゴリ別サマリー

#### Step 7: 全体分析

- **処理**:
  - 全ファイルのスコア集計（平均、最高、最低）
  - strengths: ドキュメント全体で優れている点
  - weaknesses: 「N/M ファイルで〇〇」の形式で定量化
  - recommendations: priority 付き（critical/high/medium/low）の改善提案
  - 判定: A/B/C/D/F ランク
- **出力**: overall_summary セクション

### Phase 3: レポート出力

#### Step 8: レポート生成

- **処理**: 全データを YAML 形式で整形
- **出力**: `.claude/reports/docs-evaluation-report.yaml`
- **検証**: YAML として有効な構文であること

```bash
python3 -c "import yaml; yaml.safe_load(open('.claude/reports/docs-evaluation-report.yaml'))" && echo "PASS" || echo "FAIL"
```

#### Step 9: サマリー表示

ユーザーに以下を表示:

```
## ドキュメント評価完了

| カテゴリ | ファイル数 | 平均 | SSOT | 正確 | 実用 | 構造 | 保守 |
|----------|-----------|------|------|------|------|------|------|
| coding-guidelines | 14 | 18.5 | 3.0 | 4.0 | 3.5 | 4.0 | 3.5 |
| ...      | ...       | ...  | ...  | ...  | ...  | ...  | ...  |

全体: {score}/30 ({rank})
ファイル数: {N}  行数: {total_lines}
Critical Issues: {N}件

ワースト3:
1. {file} - {score}/30 - {主要問題}
2. ...

レポート: .claude/reports/docs-evaluation-report.yaml
```

## YAML 出力テンプレート

```yaml
metadata:
  project: "{プロジェクト名}"
  total_files: {N}
  total_lines: {N}
  evaluation_date: "YYYY-MM-DD"
  evaluator: "Claude {model}"
  scoring_system: "5-axis weighted (30pt max)"
  axes:
    - name: ssot
      weight: 1.5
      label: "SSOT整合性"
    - name: accuracy
      weight: 1.5
      label: "正確性"
    - name: utility
      weight: 1.0
      label: "実用性"
    - name: structure
      weight: 1.0
      label: "構造品質"
    - name: maintainability
      weight: 1.0
      label: "保守性"

overall_summary:
  total_score: {N.N}
  max_score: 30.0
  rank: "{A|B|C|D|F}"
  average_per_file: {N.N}
  strengths:
    - "{強み}"
  weaknesses:
    - "{弱み（定量表現）}"
  recommendations:
    - priority: critical
      description: "{提案}"
      affected_files:
        - "{path}"

rank_thresholds:
  A: "25-30"
  B: "19-24"
  C: "13-18"
  D: "7-12"
  F: "0-6"

categories:
  - name: "{category}"
    file_count: {N}
    average_score: {N.N}
    rank: "{rank}"
    notes: "{所見}"

# comparison セクション（--compare 指定時のみ）
comparison:
  previous_report: "{path}"
  previous_date: "YYYY-MM-DD"
  overall_delta: "{+/-N.N}"
  file_changes:
    - path: "{file}"
      previous: {N.N}
      current: {N.N}
      delta: "{+/-N.N}"

automated_checks:
  ssot_duplicates:
    - file: "{path}"
      ssot_source: "{path}"
      duplicate_rate: "{N}%"
      duplicate_lines: {N}
  missing_paths:
    - file: "{path}"
      line: {N}
      path: "{missing_path}"
  broken_links:
    - file: "{path}"
      link: "{link}"
  size_outliers:
    - file: "{path}"
      lines: {N}
      type: "{too_large|too_small}"
      median: {N}

files:
  - path: "{relative_path}"
    category: "{category}"
    lines: {N}
    last_updated: "YYYY-MM-DD"
    scores:
      ssot: {N}
      accuracy: {N}
      utility: {N}
      structure: {N}
      maintainability: {N}
    weighted_total: {N.N}
    rank: "{A|B|C|D|F}"
    ssot_source: "{path or null}"
    duplicate_rate: "{N}%"
    missing_paths: {N}
    improvements:
      - action: "{具体的アクション}"
        priority: "{critical|high|medium|low}"
        reason: "{理由}"
    notes: |
      {所見}
```

## 判定基準

| 総合スコア | ランク | アクション |
|---|---|---|
| 25-30 | A（優良） | 維持 |
| 19-24 | B（良好） | 軽微な改善 |
| 13-18 | C（要改善） | 計画的リファクタ |
| 7-12 | D（問題あり） | 早期対応必須 |
| 0-6 | F（深刻） | 削除または全面書き直し |

## Error Handling

| Error | Recovery |
|-------|----------|
| docs/ が存在しない | エラーメッセージを表示して終了 |
| 指定カテゴリが存在しない | 利用可能なカテゴリ一覧を表示 |
| SSOT ソースが存在しない | ssot 軸を N/A とし、他4軸で評価 |
| git log が取得できない | last_updated を "unknown" とする |
| YAML 出力が構文エラー | python3 で検証し修正してから再出力 |
| 前回レポートが存在しない（--compare） | 比較なしで新規評価として実行 |

---

**Instructions for Claude:**

## 引数パース

`$ARGUMENTS` を以下のルールでパースする:

1. 引数なし → target=`all`, compare=`null`, output=`yaml`
2. 第1引数がカテゴリ名（`coding-guidelines`, `claude-guide`, `setup` 等）→ target に設定
3. `--compare {path}` → 前回レポートパスを設定
4. `--output yaml|markdown` → 出力形式を設定

## 実行手順

1. docs/ ディレクトリの全 .md ファイルを Glob で収集
2. target に応じてフィルタリング（カテゴリ指定時）
3. **Phase 1 を全ファイルに対して実行**（Step 1-4）
   - SSOT 重複検出: 対応する `.claude/rules/` ファイルと行単位比較
   - パス検証: `{{THEME_NAME}}` → 実際のテーマ名に置換して Glob
   - メトリクス: `wc -l` + `git log` で収集
   - リンク検証: マークダウンリンク `[](path)` を抽出して存在確認
4. **Phase 2 を全ファイルに対して実行**（Step 5-7）
   - 全ファイルを先に読み込んでから採点（相対比較のため）
   - 5軸スコアリング + 改善アクション生成
5. `--compare` が指定されていれば差分を算出
6. YAML レポートを Write で出力
7. python3 で YAML 構文検証
8. サマリーテーブルをユーザーに表示

## 採点時の注意

- **省略禁止**: 全ファイルの全5軸を採点する
- **具体的根拠**: notes に採点の根拠を記述。具体的な箇所を引用する
- **相対比較**: docs/ 内のファイル間で一貫した基準を適用する
- **改善提案は実行可能に**: 「改善すべき」ではなく「〇〇に置換する」のように具体的に
- **Phase 1 結果を活用**: 自動チェック結果は採点の客観的根拠として使用する

## 加重スコア算出

```
weighted_total = (ssot × 1.5) + (accuracy × 1.5) + (utility × 1.0) + (structure × 1.0) + (maintainability × 1.0)
max = 30.0
```

## 出力言語

- YAML のキー名: 英語
- notes / improvements / strengths / weaknesses / recommendations: 日本語
- サマリーテーブル: 日本語
