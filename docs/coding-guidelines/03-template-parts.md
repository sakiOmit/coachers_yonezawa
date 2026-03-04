# テンプレートパーツ設計規約

このドキュメントは、WordPressテーマにおけるページテンプレートとtemplate-partsの設計規約を定義します。

**SSOT**: `.claude/rules/wordpress.md`（テンプレート構成の基本原則）

## ページテンプレートの基本構造

**ファイル:** `themes/{{THEME_NAME}}/pages/page-[slug].php`

```php
<?php
/**
 * Template Name: ページ名
 */

get_header();

$breadcrumbs = array(
  array('href' => '/page-url/', 'label' => 'ページ名')
);
?>

<main class="p-[page-class]">
  <?php
  get_template_part('template-parts/common/page-header', null, array(
    'breadcrumbs' => $breadcrumbs,
    'ja_label' => '日本語ラベル',
    'en_heading' => 'English Heading'
  ));
  ?>

  <div class="p-[page-class]__content">
    <!-- ページコンテンツ -->
  </div>
</main>

<?php get_footer(); ?>
```

## 分割基準

### 基本ルール

**200行以上のページテンプレート → セクションごとに分割必須**
**各セクションは20行以上を目安**

| 条件 | 判断 |
|------|------|
| 200行以上のページ | セクション単位で分割 |
| 各セクション20行以上 | template-partsに抽出 |
| 各セクション20行未満 | メインファイルに直接記述 |

### ファイル構成例

**メインファイル:** `themes/{{THEME_NAME}}/pages/page-company.php`
```php
<?php
/**
 * Template Name: 会社情報
 */
get_header();
?>

<main class="p-company">
  <?php get_template_part('template-parts/company/hero'); ?>
  <?php get_template_part('template-parts/company/profile'); ?>
  <?php get_template_part('template-parts/company/history'); ?>
  <?php get_template_part('template-parts/company/group'); ?>
</main>

<?php get_footer(); ?>
```

**セクションファイル:** `themes/{{THEME_NAME}}/template-parts/company/hero.php`
```php
<section class="p-company-hero">
  <div class="p-company-hero__container">
    <h1 class="p-company-hero__heading">Company</h1>
    <p class="p-company-hero__lead">会社情報</p>
  </div>
</section>
```

## 切り出し基準（判定表）

| 条件 | 切り出し | 配置先 | 例 |
|------|---------|--------|-----|
| **2箇所以上で使用** | ✅ 必須 | `common/` | page-header, link-button |
| **大型セクション（70行以上）** | ✅ 推奨 | `{page}/section-*` | section-kv |
| **セクション内の繰り返し要素** | ✅ 推奨 | `{page}/top-*` | top-heading |
| **100行以上の複雑なマークアップ** | ✅ 推奨 | 分割検討 | - |
| **ページ固有の1回のみ使用** | ❌ 不要 | ページ内に記述 | - |
| **単純な30行未満の要素** | ❌ 不要 | インライン記述 | - |

**原則**: 「迷ったら切り出さない」

### 配置ルール

```
template-parts/
├── common/              # 汎用コンポーネント（2箇所以上で使用）
│   ├── page-header.php
│   ├── link-button.php
│   ├── breadcrumbs.php
│   └── pagination.php
├── home/                # トップページ専用
│   ├── section-*.php    # 大型セクション（70行以上）
│   └── top-*.php        # セクション内の繰り返し要素
├── {page}/              # 特定ページ専用
│   └── {page}-*.php
└── header/              # ヘッダー専用
    └── navigation.php
```

## 呼び出しパターン

### パターン1: 引数なし

```php
get_template_part('template-parts/header/navigation');
```

### パターン2: 配列引数（推奨）

```php
get_template_part('template-parts/common/page-header', null, [
  'breadcrumbs' => [['href' => '/company/', 'label' => '会社情報']],
  'ja_label' => '会社情報',
  'en_heading' => 'Company',
]);

// コンポーネント側での受け取り
$breadcrumbs = $args['breadcrumbs'] ?? [];
$ja_label = $args['ja_label'] ?? '';
```

### page_id の受け渡しルール

ACFフィールドを使用するtemplate-partsでは、親から`page_id`を引数で渡す。

```php
// ❌ 禁止: template-parts内で直接ID取得
$page_id = get_option('page_on_front');
$page_id = get_the_ID();

// ✅ 推奨: 親テンプレートから渡す
$page_id = get_the_ID();
get_template_part('template-parts/home/section-recruit', null, [
  'page_id' => $page_id
]);
```

## 引数設計

### 良い設計

```php
// シンプル（3-4個）
['ja_text' => '見出し', 'en_text' => 'Heading', 'align' => 'center']

// 中程度（6-7個）
[
  'tag' => 'a',
  'ja_text' => '詳しく見る',
  'en_text' => 'View More',
  'href' => '/page/',
  'external' => false,
  'variant' => 'primary',
]
```

### 悪い設計

```php
// ❌ 引数が多すぎる（10個以上）
// ❌ 深いネスト
// ❌ 用途不明な引数名（data1, option, flag）
```

## PageHeaderコンポーネント

**用途:** パンくず + 見出しを含む下層ページ共通ヘッダー

| 引数 | 型 | 必須 | 説明 |
|------|---|------|------|
| `breadcrumbs` | array | ✅ | パンくずリスト |
| `ja_label` | string | ✅ | 日本語ラベル |
| `en_heading` | string | ✅ | 英語見出し |
| `description` | string | - | 説明文 |

## セクションファイルの独立性

```php
<!-- ✅ 正しい: 独立したsectionタグ -->
<section class="p-company-hero">
  <div class="p-company-hero__container">
    <!-- コンテンツ -->
  </div>
</section>

<!-- ❌ 間違い: sectionタグがない -->
<div class="p-company-hero__container">
  <!-- コンテンツ -->
</div>
```

## チェックリスト

- [ ] Template Nameコメントが記述されている
- [ ] 200行以上のテンプレートはセクション分割
- [ ] 分割されたセクションは独立した `<section>` を持つ
- [ ] 引数は3-5個以内、深いネストがない
- [ ] page_id は親テンプレートから渡している
- [ ] 既存コンポーネントの再利用を確認した
