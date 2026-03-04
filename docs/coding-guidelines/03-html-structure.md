# HTML構造・セマンティック規約

このドキュメントは、WordPressテーマにおけるHTML構造パターンとセマンティック規約を定義します。

**SSOT**: `.claude/rules/wordpress.md`（セクション設計の基本原則）

## HTML構造パターン（必須）

### ページ全体の構造

```
<main class="p-{page}">                    ← ページルート（独立Block）
  <section class="p-{page}-{section}">     ← 各セクション（独立Block）
    <div class="p-{page}-{section}__container">  ← container
      <div class="p-{page}-{section}__content">  ← content（必要に応じて）
        <!-- コンテンツ -->
      </div>
    </div>
  </section>
</main>
```

### 絶対禁止: セクションをBEM Elementにする

```php
// ❌ 禁止: セクションを__でつなぐ
<main class="p-top">
  <section class="p-top__hero">      <!-- NG -->
  <section class="p-top__about">     <!-- NG -->
</main>

// ✅ 正しい: セクションは独立Block（-でつなぐ）
<main class="p-top">
  <section class="p-top-hero">       <!-- OK -->
  <section class="p-top-about">      <!-- OK -->
</main>
```

**理由:**
- セクションごとにSCSSファイルを分割しやすい
- 各セクションが独立したコンポーネントとして扱える
- ファイル構成と命名が一致する（`_p-top-hero.scss`）

### 構造要素の順序（container → content → wrapper）

```php
// ✅ 正しい順序
<section class="p-page-section">
  <div class="p-page-section__container">      <!-- 1. container: 幅制御 -->
    <div class="p-page-section__content">      <!-- 2. content: 内部レイアウト -->
      <div class="p-page-section__wrapper">    <!-- 3. wrapper: さらに内部（必要時のみ） -->
        <!-- 実際のコンテンツ -->
      </div>
    </div>
  </div>
</section>
```

| 要素 | 役割 | SCSS |
|------|------|------|
| `__container` | 最大幅・左右余白制御 | `@include container()` のみ |
| `__content` | Flexbox/Grid等の内部レイアウト | `display`, `gap` 等 |
| `__wrapper` | さらに内側のグルーピング（必要時のみ） | 任意 |

### 見出しがある場合は `<section>` 必須

```php
// ✅ 正しい: 見出しがあればsection
<section class="p-page-about">
  <h2 class="p-page-about__heading">About Us</h2>
</section>

// ❌ 間違い: 見出しがあるのにdiv
<div class="p-page-about">
  <h2 class="p-page-about__heading">About Us</h2>
</div>

// ✅ OK: 見出しがなければdivでOK
<div class="p-page__decoration">
  <!-- 装飾要素のみ -->
</div>
```

### 対応するSCSSファイル構成

```
src/scss/object/projects/company/
├── _p-company.scss           # ページルート（mainタグ）
├── _p-company-hero.scss      # Heroセクション
├── _p-company-about.scss     # Aboutセクション
└── _p-company-history.scss   # Historyセクション
```

## HTMLセマンティック規約

### 1. section要素には必ず見出しを含める

```html
<!-- ❌ NG: sectionに見出しがない -->
<section class="p-page__content">
  <p>テキスト</p>
</section>

<!-- ✅ OK: 見出しを含む -->
<section class="p-page__content">
  <h2>見出し</h2>
  <p>テキスト</p>
</section>

<!-- ✅ OK: 見出しがない場合はdivを使用 -->
<div class="p-page__decoration">
  <p>装飾要素</p>
</div>
```

### 2. 繰り返し要素はリストにする

同じ構造の要素が3個以上連続する場合、`<ul>` または `<ol>` を使用。

```html
<!-- ❌ NG -->
<div class="p-news__item">...</div>
<div class="p-news__item">...</div>
<div class="p-news__item">...</div>

<!-- ✅ OK -->
<ul class="p-news__list">
  <li class="p-news__item">...</li>
  <li class="p-news__item">...</li>
  <li class="p-news__item">...</li>
</ul>
```

### 3. 記事/カードは article を使用

```html
<!-- ✅ OK: カード形式 -->
<ul class="p-cards__list">
  <li class="p-cards__item">
    <article class="c-card">
      <h3 class="c-card__title">カードタイトル</h3>
      <p class="c-card__text">カード本文</p>
    </article>
  </li>
</ul>
```

**判定基準:**
- ✅ ブログ投稿、ニュース記事、商品カード、レビュー
- ❌ ナビゲーション、サイドバー、装飾要素

### 4. ボタンとリンクの使い分け

| 要素 | 用途 | href属性 |
|------|------|---------|
| `<a>` | ページ遷移、アンカーリンク、外部リンク | 必須 |
| `<button>` | フォーム送信、モーダル表示、アコーディオン等 | 不要 |

```html
<!-- ❌ 禁止 -->
<a href="#" class="c-button" onclick="doSomething()">クリック</a>
<a href="javascript:void(0)" class="c-button">クリック</a>

<!-- ✅ 正しい -->
<button type="button" class="c-button" onclick="doSomething()">クリック</button>
<a href="/contact/" class="c-button">お問い合わせ</a>
```

### 自動チェック

```bash
npm run check:html            # HTML構造チェック（W3C準拠）
npm run check:html:semantic   # HTMLセマンティックチェック
npm run check:templates       # 統合チェック
```

### チェックリスト

- [ ] `<section>` には見出し（h1-h6）が含まれているか
- [ ] 3個以上の繰り返し要素は `<ul>` または `<ol>` を使用
- [ ] ブログ投稿・カード要素には `<article>` を使用
- [ ] ページ遷移は `<a>`、JS操作は `<button>` を使用
- [ ] `<a href="#">` を使用していないか
- [ ] セクションは独立Block（`p-page__section` 禁止）
- [ ] container → content → wrapper の順序
