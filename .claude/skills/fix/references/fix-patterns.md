# Fix Patterns Reference

## Safe パターン（自動修正可）

### SCSS パターン

| # | パターン | 検出正規表現 | 修正方法 |
|---|---------|-------------|---------|
| 1 | `&-` ネスト → `&__` | `&-[a-z]` | `&-` を `&__` に置換 |
| 2 | `:hover` 直書き → `@include hover` | `&:hover\s*\{` | `&:hover { ... }` を `@include hover { ... }` に変換 |
| 3 | px 値 → `rv()`/`svw()` | `\d+px` (font-size, padding, margin 等) | 数値を `rv()` に変換、`@include sp` 内は `svw()` |
| 4 | 未使用 `@use` | `@use` 宣言のうち、ファイル内で参照されていないもの | 行削除 |
| 5 | 空ブロック | `\{\s*\}` | ブロックごと削除 |

#### Before/After Examples

**Pattern 1: SCSS camelCase → kebab-case**

Before:
```scss
.p-jobCard {
  &__sectionTitle {
    font-size: 18px;
  }
}
```

After:
```scss
.p-job-card {
  &__section-title {
    font-size: rv(18);
  }
}
```

**Pattern 2: JS console.log removal**

Before:
```javascript
export function initializeModule() {
  console.log('Module initialized');
  const config = { timeout: 5000 };
  console.warn('Config:', config);
  setupHandlers();
}
```

After:
```javascript
export function initializeModule() {
  const config = { timeout: 5000 };
  setupHandlers();
}
```

**Pattern 3: PHP var_dump removal**

Before:
```php
function render_job_card($job) {
  var_dump($job);
  $title = get_field('job_title', $job->ID);
  print_r($title);
  echo esc_html($title);
}
```

After:
```php
function render_job_card($job) {
  $title = get_field('job_title', $job->ID);
  echo esc_html($title);
}
```

### JavaScript パターン

| # | パターン | 検出正規表現 | 修正方法 |
|---|---------|-------------|---------|
| 1 | `console.log` | `console\.log\(` | 行削除 |
| 2 | `console.warn` | `console\.warn\(` | 行削除 |
| 3 | `console.error` | `console\.error\(` | 行削除 |
| 4 | `debugger` | `^\s*debugger;?\s*$` | 行削除 |
| 5 | 未使用 import | `import .* from` で参照先が未使用 | 行削除 |

### PHP パターン

| # | パターン | 検出正規表現 | 修正方法 |
|---|---------|-------------|---------|
| 1 | `var_dump` | `var_dump\(` | 行削除 |
| 2 | `print_r` | `print_r\(` | 行削除 |
| 3 | `error_log` | `error_log\(` | 行削除 |
| 4 | `dd()` | `\bdd\(` | 行削除 |

## Risky パターン（承認必要）

### セキュリティ修正

| # | パターン | 検出方法 | リスク |
|---|---------|---------|--------|
| 1 | エスケープ漏れ | `echo \$` without `esc_*` | 出力フォーマットが変わる可能性 |
| 2 | `the_field()` → `get_field()` | `the_field\(` | ACF ロジック変更 |
| 3 | SQL直接埋め込み | `\$wpdb->` without `prepare` | クエリ結果が変わる可能性 |
| 4 | CSRF 未対策 | フォーム処理で `wp_nonce` なし | フォーム動作に影響 |

### 構造修正

| # | パターン | 検出方法 | リスク |
|---|---------|---------|--------|
| 1 | HTML 構造変更 | セマンティクス違反 | レイアウト崩れの可能性 |
| 2 | CSS クラス名変更 | BEM 命名違反 | JS との連携が壊れる可能性 |
| 3 | テンプレート分割 | 単一ファイル 200行超 | include パスの整合性 |

## パターン-スクリプトマッピング

| パターンカテゴリ | スクリプトコマンド |
|-----------------|------------------|
| SCSS Safe | `bash scripts/auto-fix.sh scss` |
| JS Safe | `bash scripts/auto-fix.sh js` |
| PHP Safe | `bash scripts/auto-fix.sh php` |
| All Safe | `bash scripts/auto-fix.sh all` |
| Risky/Security | LLM (code-fixer エージェント) |
| Specific Issue | LLM (code-fixer エージェント + issue-id) |

## スクリプト実行フロー

```
1. auto-fix.sh がパターンマッチで Safe issues を検出
2. sed/awk で機械的に修正
3. stylelint --fix / eslint --fix を補助実行
4. 修正後のビルド検証 (npm run build)
5. 結果を reports/fix-{TYPE}-{TIMESTAMP}.json に出力
6. skipped-risky 項目があれば LLM に引き渡し
```
