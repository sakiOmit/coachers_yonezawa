---
name: delivery
description: "納品品質チェック・修正・検証・レポート"
argument-hint: "[check|fix|verify|report]"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Write
  - Edit
  - Bash
  - Glob
model: opus
context: fork
agent: general-purpose
---

# Delivery - 納品品質管理

## Dynamic Context

```
Existing delivery reports:
!`ls reports/delivery-*.md 2>/dev/null | head -3 || echo "(empty)"`
```

納品前の品質チェック、課題修正、手動検証、レポート生成を統合したコマンド。

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | `/qa full` 完了 |
| **後工程** | なし（終点） |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | delivery-checker, qa-agent エージェント |

## 使用方法

```bash
# 納品品質チェック
/delivery check

# 課題の対話的修正
/delivery fix

# 手動確認項目の検証
/delivery verify

# 納品レポート更新
/delivery report
```

## サブコマンド

| コマンド | 説明 |
|----------|------|
| `check` | 納品品質チェック（自動+手動項目生成） |
| `fix` | 納品課題を対話形式で修正 |
| `fix {issue-id}` | 特定課題を修正 |
| `verify` | 手動確認項目を対話形式で検証 |
| `report` | 納品レポートを更新・生成 |

### check
  - **前提条件**: なし（起点）
  - **入力**: プロジェクト全体のソースコード
  - **出力**: `reports/delivery-checklist-{YYYYMMDD}.md`, `reports/delivery-auto-{YYYYMMDD}.json`
  - **成功条件**: 自動チェック全項目 PASS
  - **後続**: `/delivery fix`（問題あり時）, `/delivery verify`（問題なし時）

### fix
  - **前提条件**: `/delivery check` 完了（チェックリスト存在）
  - **入力**: `reports/delivery-checklist-*.md` の未解決項目
  - **出力**: 修正されたソースファイル、更新されたチェックリスト
  - **成功条件**: 全 auto-fixable 項目が修正済み
  - **後続**: `/delivery verify`

### verify
  - **前提条件**: `/delivery fix` 完了（推奨）
  - **入力**: 手動確認項目リスト
  - **出力**: 確認済みチェックリスト（OK/NG マーク付き）
  - **成功条件**: 全手動項目が OK マーク
  - **後続**: `/delivery report`

### report
  - **前提条件**: `/delivery check` + `/delivery verify` 完了
  - **入力**: チェックリスト、QA レポート、レビュー結果
  - **出力**: `reports/delivery-report-{YYYYMMDD}.md`（社内用）, `reports/delivery-report-client-{YYYYMMDD}.md`（クライアント用）
  - **成功条件**: 全項目記載、ファイル生成済み
  - **後続**: なし（納品完了）

---

## `/delivery check`

納品前の包括的な品質チェックを実行。

### 自動チェック項目

- **リンク検証**: 内部・外部リンクの404チェック
- **画像検証**: 画像404、alt属性
- **コード品質**: FLOCSS + BEM、ベーススタイル重複
- **SEO**: title, meta description, OGP
- **パフォーマンス**: Core Web Vitals、画像最適化
- **アクセシビリティ**: 見出し構造、セマンティックHTML

### 手動チェックリスト生成

自動化できない項目のリストを生成:
- クロスブラウザテスト
- フォーム動作確認
- アニメーション確認
- コンテンツ精査

### 出力

- `reports/delivery-checklist-YYYYMMDD.md` - 社内用
- `reports/delivery-summary-YYYYMMDD.md` - クライアント提出用

---

## `/delivery fix`

納品チェックリストの未完了課題を対話形式で修正。

### 使い方

```bash
# 次の優先度の高い課題を修正
/delivery fix

# 特定の課題を指定
/delivery fix container-001

# 残存課題の一覧
/delivery fix --list

# 進捗確認
/delivery fix --status
```

### フロー

1. 最新チェックリストを読み込み
2. 優先度順に課題を表示
3. ユーザー承認後、適切なエージェントで修正
4. チェックリストを更新
5. 次の課題へ

### 注意

- **新規チャット推奨**: 大規模修正ではコンテキストが膨れるため
- **並列実行禁止**: 課題は一つずつ順番に

---

## `/delivery verify`

手動確認項目を対話形式で検証。

### 確認項目

- PC/SP表示確認（実機）
- クロスブラウザ（Safari/Firefox/Edge）
- フォーム送信テスト
- メール受信確認
- アニメーション動作
- コンテンツ最終確認

### フロー

1. チェックリストの手動項目を読み込み
2. 各項目を順番に提示
3. ユーザーが確認結果を入力
4. スクリーンショット・証跡を記録
5. チェックリストを更新

---

## `/delivery report`

納品レポートを更新・生成。

### 出力

- `reports/delivery-report-YYYYMMDD.md` - 社内用詳細レポート
- `reports/delivery-report-client-YYYYMMDD.md` - クライアント提出用

### 内容

- 品質保証報告書
- 自動チェック結果サマリー
- 手動確認結果
- 残存課題（あれば）
- 納品承認欄

---

## ワークフロー

```
/qa full
    ↓
/delivery check        # 納品品質チェック
    ↓
/delivery fix          # 課題を修正
    ↓
/delivery verify       # 手動確認
    ↓
/delivery report       # レポート生成
    ↓
クライアント提出
```

---

**Instructions for Claude:**

Based on `$ARGUMENTS`, execute the appropriate workflow:

### For `check`

check サブコマンドでは最初に `bash .claude/skills/delivery/scripts/delivery-check.sh` を実行する。スクリプトが Build・SCSS Lint・Image Size・SEO・Security・PHP Syntax の6項目を自動チェックし、`reports/delivery-auto-{TIMESTAMP}.json` に結果を保存する。スクリプト完了後にレポートを Read で読み込み、その結果を踏まえて delivery-checker エージェントへ引き渡す。

```bash
bash .claude/skills/delivery/scripts/delivery-check.sh
```

スクリプト実行後に delivery-checker を使う場合:

```
Task tool: subagent_type=delivery-checker
prompt: |
  納品品質チェックを実行してください。

  【自動チェック結果】
  reports/delivery-auto-{TIMESTAMP}.json を参照してください。
  機械的チェックはスクリプトで完了済みです。

  以下を実行:
  1. 自動チェック結果を分析
  2. 社内用チェックリストを生成: reports/delivery-checklist-YYYYMMDD.md
  3. クライアント用サマリーを生成: reports/delivery-summary-YYYYMMDD.md
  4. 手動確認項目を提示

  【重要】すべての出力は日本語で行ってください。
```

スクリプトが利用できない場合のフォールバック:

```
Task tool: subagent_type=delivery-checker
prompt: |
  納品品質チェックを実行してください。

  以下を実行:
  1. npm run check:all で自動チェック
  2. 結果を分析
  3. 社内用チェックリストを生成: reports/delivery-checklist-YYYYMMDD.md
  4. クライアント用サマリーを生成: reports/delivery-summary-YYYYMMDD.md
  5. 手動確認項目を提示

  【重要】すべての出力は日本語で行ってください。
```

### For `fix`

```
1. Read latest reports/delivery-checklist-*.md
2. Present next priority issue to user
3. On approval, launch appropriate fixer:
   - SCSS issues → code-fixer with scss mode
   - PHP issues → code-fixer with php mode
   - JS issues → code-fixer with js mode
   - Structure issues → wordpress-professional-engineer
4. Update checklist
5. Present next issue
```

### For `verify`

verify サブコマンドでは最初に `bash .claude/skills/delivery/scripts/delivery-verify.sh` を実行する。スクリプトが HTTP レスポンス確認・パーミッション検証・アセット確認を自動チェックし、`reports/delivery-verify-{TIMESTAMP}.json` に結果を保存する。スクリプト完了後にレポートを Read で読み込み、手動確認項目をユーザーに提示する。

```bash
# 基本実行
bash .claude/skills/delivery/scripts/delivery-verify.sh

# URL指定
bash .claude/skills/delivery/scripts/delivery-verify.sh --url http://localhost:8000

# ページ指定
bash .claude/skills/delivery/scripts/delivery-verify.sh --url http://localhost:3000 --pages top,about,recruit
```

スクリプト実行後:

```
1. Read reports/delivery-verify-{TIMESTAMP}.json
2. 自動チェック結果を確認（PASS/FAIL/WARN）
3. FAIL があれば修正を促す
4. 手動確認項目を順番にユーザーに提示
5. ユーザーの確認結果を記録（OK/NG）
6. Playwright MCP でスクリーンショット取得（オプション）
7. チェックリストを更新
8. 検証サマリーを生成
```

スクリプトが利用できない場合のフォールバック:

```
1. Read manual check items from delivery-checklist
2. Present each item to user
3. Record user's confirmation
4. Optionally take screenshots (Playwright MCP)
5. Update checklist with results
6. Generate verification summary
```

### For `report`

```
Task tool: subagent_type=delivery-checker
prompt: |
  納品レポートを生成してください。

  入力:
  - reports/delivery-checklist-*.md（最新）
  - .claude/reviews/*.md（レビュー結果）
  - reports/qa-spec.json

  出力:
  - reports/delivery-report-YYYYMMDD.md（社内用）
  - reports/delivery-report-client-YYYYMMDD.md（クライアント用）

  【重要】すべての出力は日本語で行ってください。
```

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | exit code |
|-----------|------|-----------|
| `scripts/delivery-check.sh` | 納品品質自動チェック（6項目） | 0=PASS, 1=FAIL |
| `scripts/delivery-verify.sh` | 半自動検証（HTTP + パーミッション + アセット） | 0=PASS, 1=FAIL |

**出力**:
- `reports/delivery-auto-{TIMESTAMP}.json`
- `reports/delivery-verify-{TIMESTAMP}.json`

## 自動チェック定量的基準

delivery-check.sh が Build, SCSS Lint, Image Size, SEO, Security, PHP Syntax の6項目を自動チェック。

**詳細**: → [references/checklist-criteria.md](references/checklist-criteria.md)（定量的基準テーブル + 出力例）

## Error Handling

| Error | Recovery |
|-------|----------|
| delivery-checker エージェント不在 | `.claude/agents/` を確認し、qa-agent で代替するか、Claude が直接チェックを実行する |
| npm run check:all 失敗 | 個別チェックコマンド（`npm run lint:css`、`npm run lint:js`、`npm run build` 等）を順番に実行し、問題を特定する |
| レポートテンプレート不在 | テンプレートファイルを探さず、デフォルトのマークダウンフォーマットで `reports/` にレポートを直接 Write する |

### Fallback

delivery-checker エージェントが利用できない場合、または Task tool が失敗した場合は、Claude 自身が直接以下を実行する:
1. **check**: Bash で個別チェックコマンドを実行し、結果を分析してチェックリストを Write で生成
2. **fix**: 最新チェックリストを Read で読み込み、Edit ツールで直接課題を修正
3. **verify**: 手動確認項目をユーザーに順番に提示し、確認結果をチェックリストに Edit で記録
4. **report**: `.claude/reviews/` と `reports/` の既存ファイルを Read で読み込み、デフォルトフォーマットでレポートを Write で生成する
