# Production Review Output Style

本番レビュー結果の出力形式を定義します。

## 適用場面

- `production-reviewer` エージェントの出力
- `/review` コマンドの結果
- `/qa full` の Phase 3 レビュー結果

## 出力構成

### 1. ヘッダー

```markdown
# 本番レビュー結果

レビュー日時: YYYY-MM-DD HH:MM:SS
レビュー対象: [ファイル/ページ名]
レビュアー: [エージェント名]
```

### 2. サマリー

```markdown
## サマリー

| 重要度 | 件数 |
|:------:|:----:|
| 🚫 Critical | X件 |
| ⚠️ High | X件 |
| 📝 Medium | X件 |
| 💡 Low | X件 |

**判定**: ✅ PRODUCTION READY / ⚠️ NEEDS REVISIONS / 🚫 BLOCKERS FOUND
```

### 3. 詳細（重要度順）

```markdown
## 🚫 Critical Issues (X件)

### [C-001] 問題タイトル

- **ファイル:** `path/to/file.php:123`
- **カテゴリ:** Security / WordPress / SCSS / HTML
- **問題:** 問題の説明
- **修正:**

```php
// Before
問題のあるコード

// After
修正後のコード
```

---

## ⚠️ High Priority Issues (X件)

### [H-001] 問題タイトル
...

## 📝 Medium Priority Issues (X件)
...

## 💡 Low Priority / Suggestions (X件)
...
```

### 4. 次のアクション

```markdown
## 次のアクション

1. [ ] Critical issues を即座に修正
2. [ ] High priority issues を修正
3. [ ] `/qa verify` で再チェック
4. [ ] 修正完了後、本番デプロイ

## 推奨コマンド

- `/scss-fix auto` - SCSS の Safe issues を自動修正
- `/php-fix auto` - PHP の Safe issues を自動修正
- `/js-fix auto` - JS の Safe issues を自動修正
```

## フォーマットルール

### ファイル参照

- 必ず `file_path:line_number` 形式を使用
- 相対パス推奨（プロジェクトルートから）

```markdown
✅ 正しい: `themes/{{THEME_NAME}}/pages/page-about.php:45`
❌ 避ける: `page-about.php` （ファイル名のみ）
```

### コード例

- Before/After を必ず含める
- コピペ可能な形式で提示
- 言語を明示（```php, ```scss など）

### 言語

- **日本語**で出力
- 技術用語は英語のまま（BEM, FLOCSS, XSS など）

### 重要度の基準

| 重要度 | 基準 |
|--------|------|
| 🚫 Critical | セキュリティ脆弱性、ビルドエラー、致命的なバグ |
| ⚠️ High | 規約違反、パフォーマンス問題、アクセシビリティ問題 |
| 📝 Medium | ベストプラクティス違反、コード品質改善 |
| 💡 Low | リファクタリング提案、スタイル改善 |

## 分類ルール

### Safe vs Risky

| 分類 | 説明 | 自動修正 |
|------|------|:--------:|
| Safe | 機械的に修正可能、副作用なし | ✅ |
| Risky | 判断が必要、他に影響の可能性 | ❌ |

### カテゴリ

- `security` - セキュリティ関連
- `wordpress` - WordPress ベストプラクティス
- `scss` - SCSS/CSS 関連
- `html` - HTML セマンティクス
- `a11y` - アクセシビリティ
- `performance` - パフォーマンス
- `naming` - 命名規則
- `code-quality` - コード品質
