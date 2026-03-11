---
name: rules-evaluate
description: "Evaluate .claude/rules/ effectiveness using 5-axis scoring (Effectiveness, Verifiability, Clarity, Coverage, Maintainability). Run when user says 'ルール評価', 'rules evaluate', 'ルール品質チェック'."
argument-hint: "[all|{rule-file}] [--compare {previous-report}] [--output yaml|markdown]"
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

# Rules Quality Evaluator

## Dynamic Context

```
Target rules:
!`ls .claude/rules/*.md | grep -v README`

Codebase scope:
!`echo "SCSS: $(find src/scss -name '*.scss' 2>/dev/null | wc -l) files"`
!`echo "PHP:  $(find themes -name '*.php' 2>/dev/null | wc -l) files"`
!`echo "JS:   $(find src/js -name '*.js' 2>/dev/null | wc -l) files"`
!`echo "Astro: $(find astro/src -name '*.astro' 2>/dev/null | wc -l) files"`
```

`.claude/rules/` のルールファイルを5軸で定量評価する。
ルールの「品質」ではなく「**実効性**」に焦点を当て、コードベースとの突合せで準拠率を算出する。

**docs-evaluate との違い:**
- docs-evaluate: ドキュメントの品質（SSOT整合性、正確性）
- rules-evaluate: ルールの実効性（コード準拠率、検証可能性）

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | ルール作成・更新完了後、またはコード実装完了後 |
| **後工程** | 違反修正、Lintルール化 |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | なし |

## 使用方法

```bash
# 全ルールファイルを評価
/rules-evaluate
/rules-evaluate all

# 特定ルールファイルのみ評価
/rules-evaluate scss
/rules-evaluate wordpress
/rules-evaluate security

# 前回レポートとの比較付き
/rules-evaluate all --compare .claude/reports/rules-evaluation-report.yaml

# 出力形式指定（デフォルト: yaml）
/rules-evaluate all --output markdown
```

## Input

| パラメータ | 必須 | 説明 |
|-----------|------|------|
| target | No | `all`（デフォルト）またはルールファイル名（拡張子なし） |
| `--compare` | No | 前回の評価レポートパス（差分表示用） |
| `--output` | No | `yaml`（デフォルト）または `markdown` |

## Output

| ファイル | 内容 |
|---------|------|
| `.claude/reports/rules-evaluation-report.yaml` | 全ルール評価結果（YAML） |

## 評価5軸

### 軸定義

| # | 軸 | 重み | 説明 |
|---|---|---|---|
| 1 | **実効性** (effectiveness) | ×2.0 | コードベースでの実際の準拠率 |
| 2 | **検証可能性** (verifiability) | ×1.5 | ルールが機械的にチェック可能か |
| 3 | **明確性** (clarity) | ×1.0 | コード例の充実度、曖昧さのなさ |
| 4 | **網羅性** (coverage) | ×1.0 | コードパターンがルールでカバーされているか |
| 5 | **保守性** (maintainability) | ×1.0 | ルール間の重複なし、更新しやすさ |

**加重合計: 32.5点満点**（各軸1-5点、重み適用後合計）

**N/A ルール**: 適用対象コードが5ファイル未満の場合、実効性を N/A とし、他4軸のみで評価（最大22.5点満点に調整）。

### スコアリング基準

#### 1. 実効性 (effectiveness) — 重み ×2.0

コードベースでの準拠率。Phase 1 の違反検出結果から算出。

| Score | 基準 |
|---|---|
| 5 | 準拠率95%以上。違反ゼロまたは例外的なもののみ |
| 4 | 準拠率80-94%。軽微な違反が散見 |
| 3 | 準拠率60-79%。一部ルールが形骸化 |
| 2 | 準拠率40-59%。守られていないルールが複数 |
| 1 | 準拠率40%未満。ルールが機能していない |
| N/A | 適用対象コードが5ファイル未満（信頼度不足） |

#### 2. 検証可能性 (verifiability) — 重み ×1.5

ルールが Grep / Lint で機械的にチェックできるかどうか。

| Score | 基準 |
|---|---|
| 5 | 全ルールが Grep パターンで自動検出可能 |
| 4 | 80%以上のルールが機械チェック可能 |
| 3 | 50-79%が機械チェック可能 |
| 2 | 一部のみ機械チェック可能、大半は目視依存 |
| 1 | ほぼ全てが主観判断に依存 |

#### 3. 明確性 (clarity) — 重み ×1.0

ルールの記述品質。コード例の量と質。

| Score | 基準 |
|---|---|
| 5 | 全ルールに ✅/❌ コード例ペア。曖昧さゼロ |
| 4 | 大半にコード例。1-2件曖昧な表現あり |
| 3 | コード例はあるが不足。一部ルールが解釈次第 |
| 2 | コード例少ない。複数ルールが曖昧 |
| 1 | コード例なし。自然言語のみ |

#### 4. 網羅性 (coverage) — 重み ×1.0

コードベースのパターンがルールでカバーされているか（逆方向チェック）。

| Score | 基準 |
|---|---|
| 5 | コードベースの全パターンがルールでカバー |
| 4 | 主要パターンはカバー。エッジケース1-2件未対応 |
| 3 | 基本はカバーだが、重要な領域に穴がある |
| 2 | カバー範囲が限定的。多くのパターンが未定義 |
| 1 | ほぼ未カバー。ルールが少なすぎる |

#### 5. 保守性 (maintainability) — 重み ×1.0

ルールファイル間の重複・矛盾リスクと更新コスト。

| Score | 基準 |
|---|---|
| 5 | ルール間の重複なし。変更時の影響範囲が明確 |
| 4 | 軽微な重複あるが一貫性は保持 |
| 3 | 一部重複。更新時に複数箇所の修正が必要 |
| 2 | 重複が多い。矛盾リスクが高い |
| 1 | 構造的に破綻。更新するたびに矛盾が生まれる |

## Processing Flow

### Phase 1: 自動チェック（機械的検証）

#### Step 1: ルール抽出

- **入力**: `.claude/rules/*.md`（README.md 除外）
- **処理**:
  1. 各ルールファイルを Read
  2. 「禁止」「必須」「使用」「避ける」「✅」「❌」キーワードでルールを抽出
  3. 各ルールに ID を割り当て（`{file}:{line}` 形式）
  4. ルールごとの適用対象（SCSS/PHP/JS/Astro）を判定
  5. コード例（✅/❌ペア）の数をカウント
- **出力**: ルールリスト（ID, 説明, 適用対象, コード例有無）

#### Step 2: 違反検出（実効性チェック）

- **入力**: Step 1 のルールリスト
- **処理**:
  各ルールに対して Grep パターンを動的生成し、コードベースを検査。

  **代表的な検出パターン:**

  | ルール | Grep パターン | 対象 glob |
  |---|---|---|
  | `:hover` 直接記述禁止 | `&:hover\|\.[\w-]+:hover` | `src/scss/**/*.scss` |
  | `the_field()` 禁止 | `the_field\(` | `themes/**/*.php` |
  | `<img>` 直接記述禁止 | `<img\s` | `themes/**/*.php`, `astro/**/*.astro` |
  | `echo \$` エスケープ漏れ | `echo\s+\$` | `themes/**/*.php` |
  | `echo get_field` エスケープ漏れ | `echo\s+get_field` | `themes/**/*.php` |
  | camelCase クラス名 | `\.[a-z]+[A-Z]` in class context | `src/scss/**/*.scss` |
  | `console.log` 残留 | `console\.log\(` | `src/js/**/*.js` |
  | `eval()` 使用 | `eval\(` | `themes/**/*.php` |
  | `extract()` 使用 | `extract\(` | `themes/**/*.php` |
  | .astro 内 SCSS import | `import.*\.scss` | `astro/**/*.astro` |
  | .astro 内 `<style>` | `<style` | `astro/**/*.astro` |
  | container 余計プロパティ | container クラスに `@include container` 以外 | `src/scss/**/*.scss` |

  - Grep 不能なルール（主観的、構造的）は `not_verifiable` としてマーク
  - 各ルールの違反数をカウント
  - 準拠率 = (チェック対象ファイル数 - 違反ファイル数) / チェック対象ファイル数 × 100

- **出力**: ルールごとの違反数、違反箇所（ファイル:行番号）、準拠率

#### Step 3: カバレッジ分析（網羅性チェック）

- **入力**: コードベースの実パターン
- **処理**:
  1. SCSS: 使用中の mixin / 関数 / パターンを Grep で収集
  2. PHP: 使用中の WordPress 関数 / ACF パターンを収集
  3. JS: 使用中の API / パターンを収集
  4. 収集パターンとルール定義を突合せ
  5. ルールに書かれていないパターンを `uncovered` としてリスト化
- **出力**: 未カバーパターンリスト

#### Step 4: ルール間重複検出（保守性チェック）

- **入力**: 全ルールファイル
- **処理**:
  1. ファイル間で同一トピック（画像処理、BEM命名、エスケープ等）の記述を検出
  2. 内容が同一 → `duplicate`
  3. 内容が異なる → `potential_contradiction`（AI判定へ）
  4. 補完的（異なるコンテキスト）→ `complementary`
- **出力**: 重複ペアリスト（タイプ付き）

#### Step 5: README.md 整合性

- **入力**: `.claude/rules/README.md`
- **処理**:
  1. README に記載されたファイル一覧を抽出
  2. 実際の `.claude/rules/*.md` と突合せ
  3. 不一致を検出（記載あり/ファイルなし、ファイルあり/記載なし）
- **出力**: 不一致リスト

### Phase 2: AI評価（LLM判定）

#### Step 6: ファイル別スコアリング

各ルールファイルに対して:

1. Phase 1 の自動チェック結果を集約
2. 5軸それぞれを 1-5 で採点
3. **実効性**: Phase 1 Step 2 の準拠率から直接算出。適用対象5ファイル未満は N/A
4. **検証可能性**: Grep 化できたルール数 / 全ルール数 から算出 + 質の判定
5. **明確性**: コード例ペア数、曖昧表現の有無を評価
6. **網羅性**: Step 3 の未カバーパターンを考慮
7. **保守性**: Step 4 の重複結果を考慮
8. 加重合計を算出
9. 改善アクションを生成（最大3件）

**N/A 時の採点:**

```
実効性が N/A の場合:
  weighted_total = (verifiability × 1.5) + (clarity × 1.0) + (coverage × 1.0) + (maintainability × 1.0)
  max_score = 22.5
  normalized_score = weighted_total / 22.5 × 32.5  # 32.5点満点に正規化
```

#### Step 7: 横断分析

- **処理**:
  - 全ファイルのスコア集計
  - 違反の多いルールカテゴリ TOP 3
  - Lint ルール化推奨リスト（検証可能性が高いルール）
  - `figma.md` の内容整合性評価
  - strengths / weaknesses / recommendations 生成
- **出力**: overall_summary セクション

### Phase 3: レポート出力

#### Step 8: レポート生成

- **処理**: 全データを YAML 形式で整形
- **出力**: `.claude/reports/rules-evaluation-report.yaml`
- **検証**: YAML 構文検証

```bash
python3 -c "import yaml; yaml.safe_load(open('.claude/reports/rules-evaluation-report.yaml'))" && echo "PASS" || echo "FAIL"
```

#### Step 9: サマリー表示

```
## ルール評価完了

| ファイル | ルール数 | 準拠率 | 効果 | 検証 | 明確 | 網羅 | 保守 | 合計 |
|----------|---------|--------|------|------|------|------|------|------|
| scss.md | 9 | 100% | 5.0 | 4.0 | 5.0 | 4.0 | 4.5 | 30.5 |
| ...     | ... | ... | ... | ... | ... | ... | ... | ... |

全体: {score}/32.5 ({rank})
ルール総数: {N}  違反総数: {N}
Lint化推奨: {N}件

違反 TOP 3:
1. {rule_id} - {違反数}件 - {説明}
2. ...

レポート: .claude/reports/rules-evaluation-report.yaml
```

## YAML 出力テンプレート

```yaml
metadata:
  project: "{プロジェクト名}"
  total_rule_files: {N}
  total_rules: {N}
  total_lines: {N}
  evaluation_date: "YYYY-MM-DD"
  evaluator: "Claude {model}"
  scoring_system: "5-axis weighted (32.5pt max)"
  axes:
    - name: effectiveness
      weight: 2.0
      label: "実効性"
    - name: verifiability
      weight: 1.5
      label: "検証可能性"
    - name: clarity
      weight: 1.0
      label: "明確性"
    - name: coverage
      weight: 1.0
      label: "網羅性"
    - name: maintainability
      weight: 1.0
      label: "保守性"

overall_summary:
  total_score: {N.N}
  max_score: 32.5
  rank: "{S|A|B|C|D}"
  total_violations: {N}
  overall_compliance_rate: "{N}%"
  strengths:
    - "{強み}"
  weaknesses:
    - "{弱み（定量表現）}"
  recommendations:
    - priority: critical
      description: "{提案}"
      type: "{violation_fix|lint_rule|consolidation|coverage_gap}"
      affected_files:
        - "{path}"
  lint_candidates:
    - rule_id: "{id}"
      description: "{ルール説明}"
      grep_pattern: "{pattern}"
      target_glob: "{glob}"
      current_violations: {N}

rank_thresholds:
  S: "29.3-32.5 (90%+)"
  A: "24.4-29.2 (75-89%)"
  B: "19.5-24.3 (60-74%)"
  C: "13.0-19.4 (40-59%)"
  D: "0-12.9 (<40%)"

# comparison セクション（--compare 指定時のみ）
comparison:
  previous_report: "{path}"
  previous_date: "YYYY-MM-DD"
  overall_delta: "{+/-N.N}"
  violation_delta: "{+/-N}"
  file_changes:
    - file: "{rule_file}"
      previous: {N.N}
      current: {N.N}
      delta: "{+/-N.N}"

automated_checks:
  violations:
    - rule_id: "{file}:{line}"
      rule_description: "{ルール説明}"
      grep_pattern: "{pattern}"
      violation_count: {N}
      violation_locations:
        - file: "{path}"
          line: {N}
          content: "{該当行}"
  not_verifiable_rules:
    - rule_id: "{file}:{line}"
      rule_description: "{ルール説明}"
      reason: "{Grep化できない理由}"
  uncovered_patterns:
    - pattern: "{コードで使用されているがルール未定義のパターン}"
      found_in: "{path}"
      suggested_rule_file: "{対象ルールファイル}"
  cross_file_overlaps:
    - topic: "{トピック}"
      files: ["{file1}", "{file2}"]
      type: "{duplicate|complementary|potential_contradiction}"
      detail: "{説明}"
  readme_mismatches:
    - type: "{file_not_listed|listed_not_found}"
      file: "{path}"

files:
  - file: "{rule_file_name}"
    lines: {N}
    rule_count: {N}
    code_example_pairs: {N}
    checklist_items: {N}
    target_scope: "{SCSS|PHP|JS|Astro|all}"
    target_file_count: {N}
    verifiable_rules: {N}
    not_verifiable_rules: {N}
    violations_found: {N}
    compliance_rate: "{N}%"
    effectiveness_na: {true|false}
    scores:
      effectiveness: {N}
      verifiability: {N}
      clarity: {N}
      coverage: {N}
      maintainability: {N}
    weighted_total: {N.N}
    max_possible: {N.N}
    rank: "{S|A|B|C|D}"
    uncovered_patterns:
      - "{パターン}"
    improvements:
      - action: "{具体的アクション}"
        priority: "{critical|high|medium|low}"
        type: "{violation_fix|lint_rule|add_example|add_rule|consolidate}"
        reason: "{理由}"
    notes: |
      {所見}
```

## 判定基準

| 総合スコア (%) | ランク | アクション |
|---|---|---|
| 90%+ (29.3-32.5) | S（模範的） | 維持。Lintルール化を推進 |
| 75-89% (24.4-29.2) | A（優良） | 軽微な改善 |
| 60-74% (19.5-24.3) | B（良好） | 違反修正・ルール補強 |
| 40-59% (13.0-19.4) | C（要改善） | 計画的な違反是正 |
| <40% (0-12.9) | D（問題あり） | ルール見直しまたは廃止検討 |

## Error Handling

| Error | Recovery |
|-------|----------|
| ルールファイルが存在しない | エラーメッセージを表示して終了 |
| 指定ファイル名が見つからない | 利用可能なファイル一覧を表示 |
| 適用対象コードが0件 | 全軸 N/A とし、ルール自体の品質のみ評価 |
| Grep パターンが false positive を多数出す | パターンを調整し、再実行。notes に記録 |
| YAML 出力が構文エラー | python3 で検証し修正してから再出力 |
| 前回レポートが存在しない（--compare） | 比較なしで新規評価として実行 |

---

**Instructions for Claude:**

## 引数パース

`$ARGUMENTS` を以下のルールでパースする:

1. 引数なし → target=`all`, compare=`null`, output=`yaml`
2. 第1引数がルールファイル名（`scss`, `wordpress`, `security` 等）→ `.claude/rules/{name}.md` を対象に
3. `--compare {path}` → 前回レポートパスを設定
4. `--output yaml|markdown` → 出力形式を設定

## 実行手順

1. `.claude/rules/` の全 .md ファイルを Glob（README.md 除外）
2. target に応じてフィルタリング
3. **Phase 1 を実行**（Step 1-5）
   - Step 1: 各ルールファイルを Read し、具体的ルールを抽出
   - Step 2: ルールごとに Grep パターンを生成 → コードベースで違反検出
     - **重要**: false positive に注意。コメント内やテンプレート文字列を除外
     - 違反が見つかったらファイル:行番号を記録
   - Step 3: コードベースのパターンをGrepで収集 → ルールとの突合せ
   - Step 4: ルールファイル間の重複トピックを検出
   - Step 5: README.md のファイル一覧と実ファイルを突合せ
4. **Phase 2 を実行**（Step 6-7）
   - 全ファイルの Phase 1 結果を先に集約してから採点（相対比較のため）
   - 5軸スコアリング + 改善アクション生成
5. `--compare` が指定されていれば差分を算出
6. YAML レポートを Write で出力
7. python3 で YAML 構文検証
8. サマリーテーブルをユーザーに表示

## 採点時の注意

- **省略禁止**: 全ファイルの全5軸を採点する（N/A は明示的にマーク）
- **具体的根拠**: notes に違反の具体例や未カバーパターンを引用する
- **false positive 除外**: Grep 結果からコメント行・テンプレート例を手動除外
- **相対比較**: ルールファイル間で一貫した基準を適用する
- **改善提案は実行可能に**: 「Lint化すべき」ではなく「stylelint ルール `selector-class-pattern` で検出可能」のように具体的に
- **Lint化推奨**: 検証可能性4以上のルールには `lint_candidates` に具体パターンを出力

## 加重スコア算出

```
# 通常（実効性あり）
weighted_total = (effectiveness × 2.0) + (verifiability × 1.5) + (clarity × 1.0) + (coverage × 1.0) + (maintainability × 1.0)
max = 32.5

# 実効性 N/A の場合
weighted_total = (verifiability × 1.5) + (clarity × 1.0) + (coverage × 1.0) + (maintainability × 1.0)
max = 22.5
normalized = weighted_total / 22.5 × 32.5
```

## 出力言語

- YAML のキー名: 英語
- notes / improvements / strengths / weaknesses / recommendations: 日本語
- サマリーテーブル: 日本語
