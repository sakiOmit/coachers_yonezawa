# エージェント使用ガイド

## 自動起動の仕組み

コーディングタスクを検出すると、Claudeが**自動的に専門エージェントを起動**します。
ユーザーが明示的に「エージェントを起動して」と指示する必要はありません。

| ユーザーの指示例 | 自動起動されるエージェント |
| ---------------- | -------------------------- |
| 「このページを実装して」 | `wordpress-professional-engineer` |
| 「SCSSを修正して」 | `wordpress-professional-engineer` |
| 「アニメーションを追加」 | `interactive-ux-engineer` |
| 「コードをレビューして」 | `production-reviewer` |
| 「QAチェックして」 | `qa-agent` |
| （実装完了時） | `production-reviewer`（proactive） |

**メインエージェント（Claude本体）が直接コードを書くことは禁止。** 理由：

- 専門エージェントはコーディング規約を熟知
- レビュー・修正のワークフローが確立
- 品質の一貫性を担保

## エージェント一覧

| エージェント | 責任範囲 | 主なツール |
|-------------|---------|-----------|
| wordpress-professional-engineer | WordPress・SCSS実装 | 全ツール |
| production-reviewer | 統合レビュー（SCSS/JS/PHP） | Read, Grep, Serena |
| code-fixer | 統合修正（SCSS/JS/PHP） | Edit, Write |
| qa-agent | QA統合チェック・修正 | Read, Grep, Edit |
| flocss-base-specialist | SCSS設計相談 | Read, Serena |
| interactive-ux-engineer | GSAP・Lottie・アニメーション | 全ツール |
| architecture-consultant | アーキテクチャ第三者レビュー | Read, Grep, Serena |
| delivery-checker | 納品品質チェック・レポート生成 | Read, Grep, Playwright |

## 使用判断フローチャート

```
タスク開始
    │
    ├─ 単純な修正（typo等）
    │   └→ サブエージェント不要、直接修正
    │
    ├─ 新規ページ実装
    │   └→ wordpress-professional-engineer
    │       └→ production-reviewer（本番前）
    │
    ├─ SCSS設計相談
    │   └→ flocss-base-specialist
    │
    ├─ アニメーション実装
    │   └→ interactive-ux-engineer
    │       └→ wordpress-professional-engineer（統合）
    │
    ├─ コードレビュー
    │   └→ production-reviewer（SCSS/JS/PHP統合）
    │
    ├─ レビュー指摘修正
    │   └→ code-fixer（SCSS/JS/PHP統合）
    │
    ├─ QAチェック
    │   └→ qa-agent（Lint + リンク + 画像チェック）
    │
    ├─ 納品前チェック
    │   └→ production-reviewer → delivery-checker
    │
    └─ アーキテクチャ評価
        └→ architecture-consultant
```

## スラッシュコマンドとの対応

| コマンド | 起動エージェント |
|----------|-----------------|
| `/review` | production-reviewer |
| `/fix` | code-fixer |
| `/qa` | qa-agent |
| `/delivery` | delivery-checker |
| `/architecture-review` | architecture-consultant |

## 連携パターン

### パターン1: 新規ページ実装（基本）

```
1. wordpress-professional-engineer
   ├─ 読み込み: docs/coding-guidelines/05-checklist.md
   ├─ 読み込み: docs/coding-guidelines/03-html-structure.md + 03-template-parts.md
   └─ 実装: PHP + SCSS + vite.config.js

2. production-reviewer
   ├─ 読み込み: docs/coding-guidelines/06-faq.md
   └─ レポート出力
```

**トークン効率:** ~27,000

### パターン2: Figma実装

```
1. wordpress-professional-engineer
   ├─ Figma MCP: get_design_context
   └─ 実装: セクション単位

2. production-reviewer（並列可）
   └─ Playwright MCP: セクション別検証
```

**トークン効率:** ~58,000

### パターン3: アニメーション追加

```
1. interactive-ux-engineer
   └─ GSAP + ScrollTrigger実装

2. wordpress-professional-engineer
   ├─ template-parts統合
   └─ vite.config.js更新

3. production-reviewer
   └─ パフォーマンス・アクセシビリティ確認
```

**トークン効率:** ~30,000

### パターン4: コード品質改善

```
1. production-reviewer
   └─ 規約違反・重複検出

2. flocss-base-specialist（SCSS最適化の場合）
   └─ 最適化方針策定

3. code-fixer
   └─ 修正実行
```

**トークン効率:** ~23,000

### パターン5: 納品前チェック

```
1. production-reviewer
   └─ 統合レビュー

2. qa-agent
   └─ Lint + リンク + 画像チェック

3. delivery-checker
   └─ 納品品質レポート生成
```

**トークン効率:** ~35,000

## 各エージェントの詳細

### wordpress-professional-engineer

WordPress/SCSS実装の主力エージェント。
- 新規ページ作成（page-*.php + SCSS + vite.config.js）
- SCSS実装（FLOCSS + BEM準拠）
- ACFフィールド実装
- 画像出力（render_responsive_image()使用）

### production-reviewer

コード品質を統合レビュー。
- FLOCSS + BEM命名規則チェック
- セキュリティ（XSS, SQLi）チェック
- ベーススタイル重複検出
- 未使用コード検出

### code-fixer

レビュー結果に基づく修正実行。
- Safe issues: 自動修正
- Risky issues: 承認後修正
- SCSS/JS/PHP統合対応

### qa-agent

QA統合チェックと修正。
- Lint（SCSS/JS/PHP）
- リンクチェック
- 画像チェック
- 自動修正対応

### flocss-base-specialist

SCSS設計相談。
- ベーススタイル抽出提案
- FLOCSS構造最適化
- 変数・mixin改善

### interactive-ux-engineer

アニメーション・インタラクション実装。
- GSAP + ScrollTrigger
- Lottie
- CSS Animation
- パフォーマンス最適化

### architecture-consultant

アーキテクチャの第三者レビュー。
- 設計一貫性評価
- 技術的負債検出
- スケーラビリティ評価

### delivery-checker

納品品質チェック・レポート生成。
- 自動チェック（リンク、画像、パフォーマンス、SEO）
- コード品質検証
- レポート生成

## 並列実行ルール

### 並列可能

- 独立したページの同時実装
- 複数セクションの検証

### 順次実行必須

- 実装 → レビュー
- レビュー → 修正
- 設計相談 → 実装

## Model選択ガイド

| タスク | 推奨Model | 理由 |
|--------|----------|------|
| 叩き台作成 | haiku | 高速・低コスト |
| 本実装 | sonnet | 品質重視 |
| レビュー | sonnet | 精度重視 |
| 簡単な修正 | haiku | 高速・低コスト |

## アンチパターン

### ❌ 過剰なエージェント起動

```
# NG: typo修正に3エージェント
1. wordpress-professional-engineer でtypo修正
2. production-reviewer で検証
3. flocss-base-specialist でBEM確認

# OK: 直接修正
→ メインエージェントが直接修正
```

### ❌ 規約を読まずにレビュー

```
# NG
production-reviewer → 規約読まない → 独自判断

# OK
production-reviewer → docs/coding-guidelines/06-faq.md読む → 規約準拠レビュー
```

### ❌ 並列可能なのに順次実行

```
# NG: 3ページを順次
Page A → 完了待ち → Page B → 完了待ち → Page C

# OK: 3ページを並列
Page A + Page B + Page C 同時起動
```

## 関連ドキュメント

- `.claude/agents/README.md` - エージェント詳細ガイド（正の情報源）
- `CLAUDE.md` - プロジェクトガイド
