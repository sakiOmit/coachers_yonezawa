# サブエージェント連携フロー

このドキュメントでは、複数のサブエージェントを効果的に組み合わせて使用するベストプラクティスを示します。

## 🎯 基本原則

### 1. エージェント選択の判断基準

**単一エージェントで完結する場合:**
- タスクが明確に1つの専門領域に収まる
- 追加の検証・レビューが不要
- 実装のみで完了

**複数エージェントの連携が必要な場合:**
- 実装 + レビューが必要
- 複数の専門領域にまたがる（WordPress + SCSS + アニメーション）
- 品質保証が重要なタスク

### 2. 並列実行 vs 順次実行

**並列実行が適切:**
```
# 複数の独立したページを同時実装
Task tool: wordpress-professional-engineer (page A)
Task tool: wordpress-professional-engineer (page B)
→ 同時に実行可能
```

**順次実行が必要:**
```
# 実装 → レビューのフロー
1. Task tool: wordpress-professional-engineer (実装)
2. 結果を確認
3. Task tool: production-reviewer (レビュー)
→ 順次実行必須
```

## 📋 推奨連携パターン

### パターン1: 新規ページ実装 → 本番レビュー

**最も一般的なフロー**

```
ステップ1: WordPress実装
└─ Agent: wordpress-professional-engineer
   ├─ 読み込み: docs/coding-guidelines/05-checklist.md
   ├─ 読み込み: docs/coding-guidelines/03-wordpress-integration.md
   ├─ 読み込み: docs/coding-guidelines/02-scss-design.md
   └─ 実装: PHP + SCSS + vite.config.js更新

ステップ2: 本番レビュー
└─ Agent: production-reviewer
   ├─ 読み込み: docs/coding-guidelines/06-faq.md
   ├─ 読み込み: docs/coding-guidelines/05-checklist.md
   ├─ Serena: 規約違反パターンを検索
   └─ レポート: 本番準備状況

ステップ3: 修正（必要な場合）
└─ Agent: wordpress-professional-engineer
   └─ レビュー指摘事項を修正
```

**トークン効率:**
- 実装: ~15,000 tokens
- レビュー: ~12,000 tokens
- 合計: ~27,000 tokens

---

### パターン2: SCSS設計レビュー → ベーススタイル最適化

**ベーススタイル重複が懸念される場合**

```
ステップ1: SCSS設計レビュー
└─ Agent: production-reviewer
   ├─ 読み込み: docs/coding-guidelines/02-scss-design.md
   ├─ Serena: search_for_pattern("font-size: rv\\(16\\)")
   └─ 検出: ベーススタイル重複箇所

ステップ2: FLOCSS専門家による最適化
└─ Agent: flocss-base-specialist
   ├─ Serena: read_memory("base-styles-reference.md")
   ├─ 分析: 重複スタイルの整理方針
   └─ 推奨: 削除すべきスタイル、残すべきスタイル

ステップ3: WordPress実装者が修正
└─ Agent: wordpress-professional-engineer
   └─ FLOCSS専門家の指示に従って修正
```

**トークン効率:**
- レビュー: ~10,000 tokens
- FLOCSS分析: ~8,000 tokens
- 修正: ~5,000 tokens
- 合計: ~23,000 tokens

---

### パターン3: アニメーション実装 → 統合レビュー

**インタラクティブ要素を追加する場合**

```
ステップ1: UXエンジニアがアニメーション実装
└─ Agent: interactive-ux-engineer
   ├─ 読み込み: docs/coding-guidelines/02-scss-design.md (BEM命名のみ)
   ├─ Serena: find_symbol("animate", substring_matching=true)
   └─ 実装: GSAP + ScrollTrigger

ステップ2: WordPress統合
└─ Agent: wordpress-professional-engineer
   ├─ template-partsにアニメーション用クラス追加
   ├─ vite.config.jsにJSエントリー追加
   └─ enqueue.phpでスクリプト読み込み

ステップ3: 本番レビュー
└─ Agent: production-reviewer
   ├─ BEM命名規則チェック (kebab-case)
   ├─ パフォーマンス検証
   └─ アクセシビリティ確認 (prefers-reduced-motion)
```

**トークン効率:**
- アニメーション実装: ~12,000 tokens
- WordPress統合: ~8,000 tokens
- レビュー: ~10,000 tokens
- 合計: ~30,000 tokens

---

### パターン4: Figma実装 → セクション別レビュー

**Figmaデザインから実装する場合**

```
ステップ1: Figma解析 + WordPress実装
└─ Agent: wordpress-professional-engineer
   ├─ Figma MCP: get_design_context (セクション別)
   ├─ 読み込み: docs/coding-guidelines/03-wordpress-integration.md
   └─ 実装: セクション1, 2, 3...

ステップ2: セクション別レビュー (並列実行可能)
├─ Agent: production-reviewer (セクション1)
├─ Agent: production-reviewer (セクション2)
└─ Agent: production-reviewer (セクション3)
   ├─ Playwright MCP: browser_screenshot (セクション単位)
   ├─ Serena: search_for_pattern (規約違反検索)
   └─ レポート: 差分箇所

ステップ3: 修正後の最終レビュー
└─ Agent: production-reviewer
   ├─ 全セクション統合確認
   └─ フルページスクリーンショット
```

**トークン効率:**
- Figma解析 + 実装: ~20,000 tokens
- セクション別レビュー (3並列): ~10,000 tokens/セクション = ~30,000 tokens
- 最終レビュー: ~8,000 tokens
- 合計: ~58,000 tokens

---

## 🚀 高度な連携テクニック

### テクニック1: メモリ駆動型連携

**エージェント間でSerenaメモリを活用**

```
フロー:
1. flocss-base-specialist
   └─ write_memory("scss-refactor-plan.md", plan)

2. wordpress-professional-engineer
   ├─ read_memory("scss-refactor-plan.md")
   └─ プランに従って実装

3. production-reviewer
   ├─ read_memory("scss-refactor-plan.md")
   └─ プラン通りに実装されているか検証
```

**メリット:**
- エージェント間で設計意図を共有
- 一貫性のある実装
- レビューの精度向上

---

### テクニック2: 段階的品質向上

**Draft → Review → Polish のサイクル**

```
サイクル1: Draft実装
└─ Agent: wordpress-professional-engineer (model: haiku)
   └─ 高速で叩き台を作成

サイクル2: 初回レビュー
└─ Agent: production-reviewer (model: sonnet)
   └─ 致命的な問題のみ指摘

サイクル3: Polish実装
└─ Agent: wordpress-professional-engineer (model: sonnet)
   └─ レビュー指摘を反映 + 細部を磨く

サイクル4: 最終レビュー
└─ Agent: production-reviewer (model: sonnet)
   └─ 本番準備完了を確認
```

**トークン効率 & コスト最適化:**
- Haiku draft: ~5,000 tokens (低コスト)
- Sonnet review: ~10,000 tokens
- Sonnet polish: ~8,000 tokens
- Sonnet final: ~7,000 tokens
- 合計: ~30,000 tokens (適切なモデル選択で コスト削減)

---

### テクニック3: 専門家チーム編成

**複雑なタスクを複数専門家で分担**

```
タスク: 新規ランディングページ (アニメーション多用、複雑なレイアウト)

Phase 1: 設計 (並列)
├─ Agent: wordpress-professional-engineer
│  └─ WordPress構造設計
├─ Agent: flocss-base-specialist
│  └─ SCSS設計 + ベーススタイル確認
└─ Agent: interactive-ux-engineer
   └─ アニメーション戦略策定

Phase 2: 実装 (順次)
1. wordpress-professional-engineer
   └─ テンプレート + 基本SCSS

2. interactive-ux-engineer
   └─ アニメーション実装

3. wordpress-professional-engineer
   └─ 統合 + ビルド設定

Phase 3: レビュー
└─ production-reviewer
   └─ 全体検証
```

**トークン効率:**
- Phase 1 (3並列): ~10,000 tokens/agent = ~30,000 tokens
- Phase 2 (順次): ~35,000 tokens
- Phase 3: ~12,000 tokens
- 合計: ~77,000 tokens (複雑タスクに対して効率的)

---

## ⚠️ アンチパターン（避けるべき連携）

### ❌ アンチパターン1: 過剰なエージェント起動

```
# 悪い例: 些細な修正に複数エージェント
Task: クラス名のtypo修正 (.p-page__titel → .p-page__title)

❌ NG:
1. wordpress-professional-engineer でtypo修正
2. production-reviewer で検証
3. flocss-base-specialist でBEM確認

✅ OK:
→ メインエージェントが直接修正 (サブエージェント不要)
```

**理由:** トークン浪費、時間増加、複雑性の増加

---

### ❌ アンチパターン2: 規約を読まずにレビュー

```
# 悪い例: レビュアーが規約を知らない
❌ NG:
production-reviewer を起動
→ 規約ファイルを読まない
→ 独自判断でレビュー

✅ OK:
production-reviewer を起動
→ docs/coding-guidelines/06-faq.md を読む
→ プロジェクト規約に基づいてレビュー
```

**理由:** プロジェクト固有の規約違反を見逃す

---

### ❌ アンチパターン3: 並列実行できるのに順次実行

```
# 悪い例: 独立した3ページを順次実装
❌ NG:
1. wordpress-professional-engineer (page A)
2. 完了を待つ
3. wordpress-professional-engineer (page B)
4. 完了を待つ
5. wordpress-professional-engineer (page C)

✅ OK:
同時に3つのTask toolを起動 (並列実行)
→ 3倍高速
```

**理由:** 実装時間が無駄に長くなる

---

## 💡 ベストプラクティスまとめ

### 1. エージェント起動前のチェックリスト

- [ ] このタスクは本当にサブエージェントが必要か？
- [ ] 必要な規約ファイルは何か明確か？
- [ ] Serenaツールで事前調査すべきことはないか？
- [ ] 並列実行できる部分はないか？
- [ ] 適切なmodelを選択しているか？ (haiku vs sonnet)

### 2. トークン効率化のコツ

- **Just-in-Time読み込み**: 全規約を読まず、必要な部分のみ
- **Serenaメモリ活用**: 繰り返し参照する情報はメモリに保存
- **段階的実装**: Draft (haiku) → Review (sonnet) → Polish (sonnet)
- **並列実行**: 独立タスクは同時起動

### 3. 品質保証のポイント

- **実装後は必ずレビュー**: production-reviewer で検証
- **規約遵守を最優先**: FAQとチェックリストを必読
- **Serenaで自動検出**: 規約違反パターンを検索
- **段階的修正**: 致命的問題 → 重要な問題 → 細かい改善

### 4. コスト最適化

| タスク | 推奨Model | 理由 |
|--------|----------|------|
| 叩き台作成 | haiku | 高速・低コスト |
| 本実装 | sonnet | 品質重視 |
| レビュー | sonnet | 精度重視 |
| 簡単な修正 | haiku | 高速・低コスト |

---

このフローに従うことで、サブエージェントを最大限活用し、高品質な実装を効率的に実現できます。
