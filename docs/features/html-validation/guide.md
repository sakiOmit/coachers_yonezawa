# HTML バリデーション機能ガイド

## 概要

WordPress テンプレートファイルの HTML 構造とセマンティック品質を厳密にチェックするシステムです。

## 実装済みチェック項目

### 1. 機械的チェック (html-validate)

**ツール**: `html-validate` npm パッケージ

**検出項目**:
- `<img>` に alt 属性がない
- 見出しレベルのスキップ（h1 → h3）
- 必須属性の不足（`element-required-attributes`）
- 重複 ID（`no-dup-id`）
- ARIA 属性の誤用（`aria-label-misuse`）
- 要素の不正な親子関係（`element-permitted-content`）

**実行方法**:
```bash
npm run check:html
```

**設定ファイル**: `.htmlvalidate.json`

**対象ファイル**:
- `themes/{{THEME_NAME}}/pages/**/*.php`
- `themes/{{THEME_NAME}}/template-parts/**/*.php`
- `themes/{{THEME_NAME}}/{front-page,header,footer,404,index,archive,single,page}.php`

### 2. セマンティック構造チェック (html-semantic.ts)

**ツール**: カスタム TypeScript スクリプト

**検出項目**:

#### 2.1 セクションに見出しがない
```html
<!-- NG -->
<section class="p-page__content">
  <p>テキスト</p>
</section>

<!-- OK -->
<section class="p-page__content">
  <h2>見出し</h2>
  <p>テキスト</p>
</section>
```

#### 2.2 リスト候補（同じクラスの要素が3つ以上連続）
```html
<!-- NG: リストにすべき -->
<div class="p-news__item">...</div>
<div class="p-news__item">...</div>
<div class="p-news__item">...</div>

<!-- OK -->
<ul class="p-news">
  <li class="p-news__item">...</li>
  <li class="p-news__item">...</li>
  <li class="p-news__item">...</li>
</ul>
```

#### 2.3 article候補（__post/__card/__entryなのに<div>）
```html
<!-- NG -->
<div class="p-blog__post">
  <h2>タイトル</h2>
  <time>2024-01-01</time>
</div>

<!-- OK -->
<article class="p-blog__post">
  <h2>タイトル</h2>
  <time>2024-01-01</time>
</article>
```

#### 2.4 ボタン vs リンクの誤用
```html
<!-- NG: ページ遷移しないのに<a> -->
<a href="#" class="c-button">送信</a>

<!-- OK -->
<button class="c-button">送信</button>

<!-- リンクの場合はOK -->
<a href="/contact/" class="c-button">お問い合わせ</a>
```

**実行方法**:
```bash
npm run check:html:semantic
```

**レポート出力**: `reports/html-semantic-report.json`

## 統合チェック

### templates-quality.ts への統合

`npm run check:templates` で以下のチェックを一括実行:

1. **Step 1**: PHP テンプレート品質チェック
   - WordPress 規約違反
   - BEM 命名規則
   - アクセシビリティ
   - コード品質

2. **Step 2**: HTML 構造バリデーション
   - `html-validate` による機械的チェック

3. **Step 3**: セマンティック構造チェック
   - カスタムスクリプトによる意味的チェック

### QA統合チェック (qa/check.ts) への統合

`npm run qa:check` で全品質チェックを実行し、`qa-spec.json` に統合:

```json
{
  "categories": {
    "build": { ... },
    "lint": { ... },
    "links": { ... },
    "images": { ... },
    "templates": { ... },
    "html": {
      "validate": {
        "name": "HTML構造バリデーション",
        "success": false,
        "issues": [ ... ]
      },
      "semantic": {
        "name": "セマンティック構造",
        "success": true,
        "issues": [ ... ]
      }
    }
  }
}
```

## レポート形式

### html-semantic-report.json

```json
{
  "timestamp": "2025-01-08T12:00:00.000Z",
  "totalFiles": 104,
  "totalIssues": 10,
  "issues": [
    {
      "file": "themes/{{THEME_NAME}}/pages/page-top.php",
      "line": 25,
      "type": "semantic-structure",
      "severity": "warning",
      "message": "<section> に見出し要素がありません",
      "content": "<section class=\"p-top__hero\">",
      "suggestion": "<section> 内に <h2>～<h6> の見出しを追加するか、意味的に <div> に変更してください"
    }
  ],
  "summary": {
    "errors": 0,
    "warnings": 7,
    "info": 3,
    "byType": {
      "semantic-structure": 5,
      "button-vs-link": 2,
      "article-candidate": 3
    }
  }
}
```

## 設定カスタマイズ

### .htmlvalidate.json

厳密度の調整:

```json
{
  "rules": {
    "element-required-attributes": "error",  // エラー（ビルド失敗）
    "heading-level": "warn",                 // 警告（ビルド成功）
    "no-inline-style": "off"                 // 無効
  }
}
```

### html-semantic.ts

検出パターンの追加:

```typescript
// 新しいチェック関数を追加
function checkCustomPattern(content: string, filePath: string): SemanticIssue[] {
  // 実装
}

// checkFile() 関数内で呼び出し
const issues: SemanticIssue[] = [
  ...checkSectionHeadings(htmlContent, filePath),
  ...checkCustomPattern(htmlContent, filePath), // 追加
];
```

## 除外設定

### 特定ファイルを除外

**package.json**:
```json
{
  "check:html": "html-validate 'themes/{{THEME_NAME}}/{pages,template-parts}/**/*.php' --ignore '**/legacy/**'"
}
```

### 特定ルールを無効化

**PHP テンプレート内で一時的に無効化**:
```html
<!-- html-validate-disable-next element-required-attributes -->
<img src="dynamic.jpg">
```

## トラブルシューティング

### PHP構文エラーで html-validate が失敗する

**原因**: PHP コードが HTML パーサーを混乱させる

**対処**:
1. `.htmlvalidate.json` で `"parser-error": "off"` を設定済み
2. 対象ファイルを純粋なテンプレートファイルのみに制限

### 誤検出が多い

**セマンティックチェック**:
- `html-semantic.ts` のパターンを調整
- 除外クラス名を追加（WordPress 標準クラス等）

**html-validate**:
- `.htmlvalidate.json` でルールを `"warn"` または `"off"` に変更

## 納品前チェックリスト

```bash
# 1. 全QAチェック実行
npm run qa:check

# 2. レポート確認
cat reports/qa-report.md

# 3. HTML問題の確認
cat reports/html-semantic-report.json

# 4. エラーがあれば修正
# （自動修正可能なものは npm run lint:fix）

# 5. 再チェック
npm run qa:check
```

## 今後の拡張案

- [ ] `<form>` 要素の適切な `method` 属性チェック
- [ ] `<table>` の `<thead>`, `<tbody>` 構造チェック
- [ ] ランドマークロール（`role="navigation"` 等）の重複チェック
- [ ] 連続する `<br>` タグの検出（CSS margin で対応すべき）
- [ ] 空の要素（`<p></p>`）の検出

## 参考資料

- [html-validate 公式ドキュメント](https://html-validate.org/)
- [WCAG 2.1 ガイドライン](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN: HTML 要素リファレンス](https://developer.mozilla.org/ja/docs/Web/HTML/Element)
- [セマンティック HTML ベストプラクティス](https://web.dev/learn/html/semantic-html/)
