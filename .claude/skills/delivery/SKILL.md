---
name: delivery
description: "納品品質チェック・修正・検証・レポート"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Write
  - Bash
  - Glob
context: fork
agent: general-purpose
---

# Delivery - 納品品質管理

納品前の品質チェック、課題修正、手動検証、レポート生成を統合したコマンド。

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
