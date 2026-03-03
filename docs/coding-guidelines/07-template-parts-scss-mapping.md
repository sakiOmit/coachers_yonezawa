# template-parts と SCSS の対応ルール

## 概要

WordPressの `template-parts/` と `src/scss/object/` の構造を1対1で対応させることで、コードの保守性と可読性を向上させます。

## 基本原則

### 1. ディレクトリ構造の対応

```
themes/{{THEME_NAME}}/template-parts/    →    src/scss/object/
├── common/                          →    ├── components/     (c-)
├── home/                            →    └── projects/
├── aboutus/                         →        ├── home/
├── recruitment/                     →        ├── aboutus/
└── header/                          →        ├── recruitment/
                                     →        └── ...
```

### 2. 命名規則の対応

| template-parts | SCSS                    | 説明                       |
| -------------- | ----------------------- | -------------------------- |
| `common/`      | `components/` (c-)      | 再利用可能なコンポーネント |
| `home/`        | `projects/home/` (p-)   | トップページ専用           |
| `{page}/`      | `projects/{page}/` (p-) | ページ固有スタイル         |
| `header/`      | `layout/` (l-)          | レイアウト要素             |

## 詳細ルール

### ルール1: common/ → components/ (c-プレフィックス)

**template-parts/common/** の各ファイルは **scss/object/components/** に対応するSCSSを持つ。

```
template-parts/common/           →    scss/object/components/
├── link-button.php              →    ├── _c-LinkButton.scss
├── section-heading.php          →    ├── _c-SectionHeading.scss
├── numbered-heading.php         →    ├── _c-NumberedHeading.scss
├── breadcrumbs.php              →    ├── _c-Breadcrumbs.scss
├── pagination.php               →    ├── _c-Pagination.scss
├── page-header.php              →    ├── _c-PageHeader.scss (または projects/_p-PageHeader.scss)
└── infinite-scroll-text.php     →    └── _c-InfiniteScrollText.scss
```

**命名変換ルール:**
- PHPファイル: `kebab-case.php` (例: `link-button.php`)
- SCSSファイル: `_c-PascalCase.scss` (例: `_c-LinkButton.scss`)
- CSSクラス: `.c-link-button` (BEM: kebab-case)

### ルール2: {page}/ → projects/{page}/ (p-プレフィックス)

**template-parts/{page}/** のセクションは **scss/object/projects/{page}/** に対応。

```
template-parts/home/              →    scss/object/projects/home/
├── section-kv.php                →    ├── _p-kv.scss
├── section-business.php          →    ├── _p-business.scss
├── section-about.php             →    ├── _p-about.scss
├── section-news.php              →    ├── _p-news.scss
├── section-message.php           →    ├── _p-message.scss
├── section-recruit.php           →    ├── _p-recruit.scss
└── top-heading.php               →    └── _p-top-heading.scss
```

**命名変換ルール:**
- PHPファイル: `section-{name}.php` (例: `section-kv.php`)
- SCSSファイル: `_p-{name}.scss` (例: `_p-kv.scss`)
- CSSクラス: `.p-{page}__{name}` (例: `.p-top__kv`)

### ルール3: ネストしたセクション

ページ内でさらにセクション分割がある場合、同じ階層構造を維持。

```
template-parts/recruitment/       →    scss/object/projects/recruitment/
├── top/                          →    ├── top/
│   ├── section-kv.php            →    │   ├── _p-recruitment-kv.scss
│   ├── section-message.php       →    │   ├── _p-recruitment-message.scss
│   └── section-interview.php     →    │   └── _p-recruitment-interview.scss
├── career/                       →    ├── career/
│   ├── section-hero.php          →    │   ├── _p-career-hero.scss
│   ├── section-paths.php         →    │   ├── _p-career-paths.scss
│   └── section-fields.php        →    │   └── _p-career-fields.scss
└── numbers/                      →    └── numbers/
    ├── section-growth.php        →        ├── _p-numbers-growth.scss (または _p-numbers.scss に統合)
    └── section-employee-data.php →        └── ...
```

### ルール4: header/ → layout/ (l-プレフィックス)

ヘッダー・フッター関連は `layout/` に配置。

```
template-parts/header/            →    scss/layout/
├── navigation.php                →    └── _header.scss (内部に .l-header__nav)

themes/{{THEME_NAME}}/header.php      →    scss/layout/_header.scss
themes/{{THEME_NAME}}/footer.php      →    scss/layout/_footer.scss
```

## ファイル分割の判断基準

### 1ファイルにまとめる場合

- セクションのスタイルが **100行以下**
- 他のセクションと **密結合** している
- **単独で再利用されない**

```scss
// _p-numbers.scss - セクションを1ファイルに統合
.p-numbers {
  &__growth { /* ... */ }
  &__employee-data { /* ... */ }
  &__corporate-scale { /* ... */ }
}
```

### 分割する場合

- セクションのスタイルが **100行以上**
- **複雑なコンポーネント** を含む
- **独立性が高い** セクション

```scss
// _p-career-hero.scss - 独立したファイル
.p-career__hero {
  /* 100行以上のスタイル */
}
```

## 対応表テンプレート

新規ページ作成時は以下の対応表を作成して管理:

```markdown
## {page-name} ページ対応表

| template-parts                            | SCSS                                | 備考                     |
| ----------------------------------------- | ----------------------------------- | ------------------------ |
| template-parts/{page}/section-hero.php    | projects/{page}/_p-{page}-hero.scss | ヒーローセクション       |
| template-parts/{page}/section-content.php | projects/{page}/_p-{page}.scss      | メインコンテンツ（統合） |
| template-parts/common/link-button.php     | components/_c-LinkButton.scss       | 共通コンポーネント使用   |
```

## エントリーポイントでの読み込み順序

```scss
// src/css/pages/{page}/style.scss

// 1. Foundation（関数・mixin）
@use "../../../scss/foundation/function" as *;
@use "../../../scss/foundation/mixins/responsive" as *;
@use "../../../scss/foundation/mixins/block" as *;

// 2. Projects - ページメイン
@use "../../../scss/object/projects/{page}/_p-{page}";

// 3. Projects - セクション別（分割している場合）
@use "../../../scss/object/projects/{page}/_p-{page}-hero";
@use "../../../scss/object/projects/{page}/_p-{page}-content";

// ※ Components (c-) は common.scss で読み込み済み
```

## チェックリスト

### 新規 template-part 作成時

- [ ] 対応する SCSS ファイルを作成
- [ ] FLOCSS プレフィックス（c- / p-）を正しく付与
- [ ] BEM 命名規則（kebab-case）を遵守
- [ ] エントリーポイントに @use を追加
- [ ] 対応表を更新（必要に応じて）

### レビュー時の確認項目

- [ ] template-parts と SCSS のディレクトリ構造が一致しているか
- [ ] 命名規則が統一されているか
- [ ] 不要な SCSS ファイルが残っていないか
- [ ] 共通コンポーネントは components/ に配置されているか

## アンチパターン

### ❌ NG: 対応関係が不明確

```
template-parts/home/section-hero.php
scss/object/projects/_p-HomeHero.scss  ← ディレクトリ構造が不一致
```

### ✅ OK: 明確な対応関係

```
template-parts/home/section-hero.php
scss/object/projects/home/_p-hero.scss  ← 階層構造が一致
```

### ❌ NG: 共通コンポーネントがページ固有に

```
template-parts/common/button.php
scss/object/projects/home/_p-button.scss  ← common なのに projects に
```

### ✅ OK: 共通コンポーネントは components へ

```
template-parts/common/button.php
scss/object/components/_c-Button.scss  ← 正しく components に配置
```
