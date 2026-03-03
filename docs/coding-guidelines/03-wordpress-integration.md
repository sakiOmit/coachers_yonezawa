# WordPress連携規約

このドキュメントは、WordPressテンプレート開発の規約をまとめたものです。

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

### 🚫 絶対禁止: セクションをBEM Elementにする

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

// ❌ 順序が逆
<section class="p-page-section">
  <div class="p-page-section__content">        <!-- NG: contentが先 -->
    <div class="p-page-section__container">    <!-- NG: containerが後 -->
```

**各要素の役割:**
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
  <p class="p-page-about__text">...</p>
</section>

// ❌ 間違い: 見出しがあるのにdiv
<div class="p-page-about">
  <h2 class="p-page-about__heading">About Us</h2>  <!-- sectionにすべき -->
</div>

// ✅ OK: 見出しがなければdivでOK
<div class="p-page__decoration">
  <!-- 装飾要素のみ -->
</div>
```

### 実装例

```php
<main class="p-company">
  <!-- Hero: 独立Block -->
  <section class="p-company-hero">
    <div class="p-company-hero__container">
      <h1 class="p-company-hero__heading">Company</h1>
      <p class="p-company-hero__lead">会社情報</p>
    </div>
  </section>

  <!-- About: 独立Block -->
  <section class="p-company-about">
    <div class="p-company-about__container">
      <div class="p-company-about__content">
        <h2 class="p-company-about__heading">About Us</h2>
        <p class="p-company-about__text">...</p>
      </div>
    </div>
  </section>

  <!-- History: 独立Block -->
  <section class="p-company-history">
    <div class="p-company-history__container">
      <h2 class="p-company-history__heading">History</h2>
      <ul class="p-company-history__list">
        <li class="p-company-history__item">...</li>
      </ul>
    </div>
  </section>
</main>
```

### 対応するSCSSファイル構成

```
src/scss/object/projects/company/
├── _p-company.scss           # ページルート（mainタグ）
├── _p-company-hero.scss      # Heroセクション
├── _p-company-about.scss     # Aboutセクション
└── _p-company-history.scss   # Historyセクション
```

## ページテンプレートの基本構造

**ファイル:** `themes/{{THEME_NAME}}/pages/page-[slug].php`

```php
<?php
/**
 * Template Name: ページ名
 */

get_header();

// パンくず配列
$breadcrumbs = array(
  array('href' => '/page-url/', 'label' => 'ページ名')
);
?>

<main class="p-[page-class]">
  <?php
  // 下層ページ共通ヘッダー
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

## template-partsの使い方と分割基準

### 分割の基本ルール

**200行以上のページテンプレート → セクションごとに分割必須**

**ただし、各セクションは20行以上を目安とする**

**理由:**
- 保守性向上（大きいファイルは修正時に迷子になる）
- SCSSとの粒度統一（SCSSがセクション分割されているならPHPも合わせる）
- 再利用性（セクション単位で他ページにも使える）
- Git差分の明確化（セクション変更時の影響範囲が明確）
- Figma実装の効率化（セクション単位で実装しやすい）
- 過度な分割の防止（10行程度の極小ファイルは逆に可読性を下げる）

**分割判断基準:**
- ✅ **200行以上のページ**: セクション単位で分割
- ✅ **各セクション20行以上**: template-partsに抽出
- ❌ **各セクション20行未満**: メインファイルに直接記述（過度な分割を避ける）

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

**対応するSCSS構成（完全一致）:**
```
src/scss/object/projects/company/
├── _p-company.scss              # ページルート
├── _p-company-hero.scss         # → template-parts/company/hero.php
├── _p-company-profile.scss      # → template-parts/company/profile.php
├── _p-company-history.scss      # → template-parts/company/history.php
└── _p-company-group.scss        # → template-parts/company/group.php
```

### template-partsの呼び出し方

```php
// 引数なし
get_template_part('template-parts/common/breadcrumbs');

// 引数あり（第3引数で配列を渡す）
get_template_part('template-parts/common/page-header', null, array(
  'breadcrumbs' => $breadcrumbs,
  'ja_label' => 'お問い合わせ',
  'en_heading' => 'Contact'
));

// セクションごとに分割する場合
get_template_part('template-parts/company/hero', null, array(
  'title' => get_field('hero_title'),
  'subtitle' => get_field('hero_subtitle')
));
```

### セクションファイルの独立性

各セクションファイルは独立した`<section>`を持つこと:

```php
<!-- ✅ 正しい: 独立したsectionタグ -->
<!-- template-parts/company/hero.php -->
<section class="p-company-hero">
  <div class="p-company-hero__container">
    <!-- コンテンツ -->
  </div>
</section>

<!-- ❌ 間違い: sectionタグがない -->
<!-- template-parts/company/hero.php -->
<div class="p-company-hero__container">
  <!-- コンテンツ -->
</div>
```

## PageHeaderコンポーネント

**用途:** パンくず + 見出しを含む下層ページ共通ヘッダー

**必須引数:**
- `breadcrumbs` (array) - パンくずリスト
- `ja_label` (string) - 日本語ラベル
- `en_heading` (string) - 英語見出し

**オプション:**
- `description` (string) - 説明文

## 画像出力の規約

### ⚠️ 画像ソースによる使い分け（必須）

画像の出力関数は、**画像のソース（保存場所）によって明確に使い分けてください。**

| 画像ソース | 使用関数 | 理由 |
|-----------|---------|------|
| **テーマ静的画像** (`/assets/images/`) | `render_responsive_image()` | ビルドプロセスでWebP・Retina対応済み |
| **WordPress投稿サムネイル** | `the_post_thumbnail()` | WordPress標準の画像最適化を活用 |
| **ACFアップロード画像** (Media Library) | `wp_get_attachment_image()` | WordPress標準の画像最適化を活用 |
| **noimage等のフォールバック** | `render_responsive_image()` | テーマ静的画像と同じ扱い |

**重要原則:**
- **テーマ静的画像**: `render_responsive_image()` のみ使用可能（ビルド済み画像）
- **WordPressアップロード画像**: `render_responsive_image()` 使用禁止（@2x.webpが存在せず404エラー）

### ❌ 禁止パターン

```php
// ❌ BAD: WordPressアップロード画像にrender_responsive_image()を使用
$thumbnail_url = get_the_post_thumbnail_url(get_the_ID(), 'large');
render_responsive_image([
  'src' => $thumbnail_url,  // ← /wp-content/uploads/の画像は@2x.webpが存在しない
  'alt' => 'サムネイル',
]);

// ❌ BAD: ACF Image FieldにURLベースで使用
$image = get_field('thumbnail');
render_responsive_image([
  'src' => $image['url'],  // ← /wp-content/uploads/の画像は@2x.webpが存在しない
  'alt' => 'サムネイル',
]);

// ❌ BAD: 直接imgタグを記述
<img src="<?php echo get_template_directory_uri(); ?>/assets/images/example.png" alt="説明">
```

### ✅ 正しいパターン

#### 1. テーマ静的画像（/assets/images/）

```php
// ✅ GOOD: テーマ内の静的画像（ビルドプロセスで最適化済み）
<?php
render_responsive_image([
  'src' => get_template_directory_uri() . '/assets/images/hero.png',
  'alt' => 'ヒーロー画像',
  'class' => 'p-page__hero-image',
  'loading' => 'eager'
]);
?>

// ✅ GOOD: PC/SP別画像
<?php
render_responsive_image([
  'src' => get_template_directory_uri() . '/assets/images/hero.png',
  'sp' => true,  // hero_sp.png, hero_sp@2x.webp等が自動生成される
  'alt' => 'ヒーロー画像',
  'class' => 'p-kv__image',
]);
?>
```

#### 2. WordPress投稿サムネイル

```php
// ✅ GOOD: the_post_thumbnail()を使用（自動的にsrcset生成）
<?php
if ( has_post_thumbnail() ) :
  the_post_thumbnail(
    'large',  // サイズ: thumbnail, medium, large, full
    [
      'class' => 'p-single__thumbnail-image',
      'loading' => 'eager',
    ]
  );
endif;
?>

// ✅ GOOD: 関連記事のサムネイル
<?php
if ( has_post_thumbnail() ) :
  the_post_thumbnail(
    'medium',
    [
      'class' => 'p-single__related-card-image',
      'loading' => 'lazy',
    ]
  );
endif;
?>
```

#### 3. ACFアップロード画像（Media Library）

```php
// ✅ GOOD: wp_get_attachment_image()を使用
<?php
$thumbnail_id = $brand['thumbnail_id'] ?? 0;
if ( $thumbnail_id ) :
  echo wp_get_attachment_image(
    $thumbnail_id,
    'full',
    false,
    [
      'alt' => $brand_name,
      'loading' => 'lazy',
    ]
  );
endif;
?>
```

#### 4. ACF画像フィールド（PC/SP別画像グループ）

```php
// ✅ GOOD: ACFグループフィールド（acf_field指定）
<?php
render_responsive_image([
  'acf_field' => 'hero_image',  // ['pc' => image, 'sp' => image]形式
  'alt' => 'ヒーロー画像',
  'class' => 'p-kv__image',
  'loading' => 'eager'
]);
?>
```

### 関数リファレンス

**ファイル:** `themes/{{THEME_NAME}}/inc/image-helpers.php`

#### 1. render_responsive_image($args) - テーマ静的画像専用

**用途:** `/assets/images/` 内の静的画像出力（ビルドプロセスで最適化済み）

**主要な引数:**

| 引数 | 型 | 説明 | デフォルト |
|------|-----|------|-----------|
| `src` | string | 画像パス（`get_template_directory_uri() . '/assets/images/...'`） | '' |
| `sp` | bool | SP別画像を使用するか（`_sp.png`, `_sp@2x.webp`を自動生成） | true |
| `alt` | string | alt属性 | '' |
| `class` | string | img要素のclass属性 | なし |
| `wrapper_class` | string | picture要素のclass属性 | なし |
| `loading` | string | loading属性（'lazy' / 'eager'） | 'lazy' |
| `width` | int | width属性（メタデータから自動取得可能） | null |
| `height` | int | height属性（メタデータから自動取得可能） | null |
| `breakpoint` | int | SP/PC切り替えブレークポイント | 767 |

**注意:** WordPress Media Libraryの画像には使用不可（404エラー）

#### 2. the_post_thumbnail() - WordPress投稿サムネイル

**用途:** 投稿のアイキャッチ画像出力

**基本構文:**
```php
the_post_thumbnail( $size, $attr );
```

**引数:**
- `$size` (string): 画像サイズ (`thumbnail`, `medium`, `large`, `full`)
- `$attr` (array): 属性配列 (`class`, `alt`, `loading` 等)

**WordPress標準機能:**
- 自動的に`srcset`・`sizes`属性を生成
- レスポンシブ画像に自動対応
- WebP対応（環境・プラグインによる）

#### 3. wp_get_attachment_image() - ACFアップロード画像

**用途:** ACF Image Field等、Media Library画像のID指定出力

**基本構文:**
```php
echo wp_get_attachment_image( $attachment_id, $size, $icon, $attr );
```

**引数:**
- `$attachment_id` (int): 画像ID
- `$size` (string): 画像サイズ
- `$icon` (bool): アイコン表示（通常false）
- `$attr` (array): 属性配列

**WordPress標準機能:**
- `the_post_thumbnail()`と同じく`srcset`自動生成
- IDベースで柔軟に画像指定可能

#### 4. render_logo($args) - サイトロゴ専用

**用途:** ホームへのリンク付きロゴ出力

**主要な引数:**

| 引数 | 型 | 説明 | デフォルト |
|------|-----|------|-----------|
| `src` | string | ロゴ画像パス | '/assets/images/common/logo.png' |
| `alt` | string | alt属性 | サイト名 |
| `width` | int | width属性 | 200 |
| `height` | int | height属性 | 50 |
| `class` | string | img要素のclass | 'l-header__logo-image' |
| `link_class` | string | aタグのclass | 'l-header__logo-link' |
| `loading` | string | loading属性 | 'eager' |

### 実装例

#### 例1: 投稿一覧のサムネイル（WordPress標準）

```php
<?php
// 投稿ループ内
if ( has_post_thumbnail() ) :
?>
  <div class="p-topics__item-thumbnail">
    <?php
    the_post_thumbnail(
      'medium',
      [
        'class' => 'p-topics__item-image',
        'loading' => 'lazy',
      ]
    );
    ?>
  </div>
<?php else : ?>
  <div class="p-topics__item-thumbnail p-topics__item-thumbnail--noimage">
    <?php
    // フォールバック画像はテーマ静的画像なのでrender_responsive_image()使用
    render_responsive_image([
      'src' => get_template_directory_uri() . '/assets/images/common/noimage.png',
      'alt' => 'No Image',
      'class' => 'p-topics__item-image',
      'sp' => false,
    ]);
    ?>
  </div>
<?php endif; ?>
```

#### 例2: ACFアップロード画像（ブランドカード）

```php
<?php
$thumbnail_id = $brand['thumbnail_id'] ?? 0;
$brand_name = $brand['name'] ?? '';
?>
<div class="c-brand-card__image-wrapper">
  <?php if ( $thumbnail_id ) :
    echo wp_get_attachment_image(
      $thumbnail_id,
      'full',
      false,
      [
        'alt' => $brand_name,
        'loading' => 'lazy',
      ]
    );
  endif; ?>
</div>
```

#### 例3: メインビジュアル（テーマ静的画像、eager loading）

```php
<?php
// ファーストビューの画像はloading="eager"を使用
render_responsive_image([
  'src' => get_template_directory_uri() . '/assets/images/hero.png',
  'alt' => 'キービジュアル',
  'class' => 'p-kv__image',
  'loading' => 'eager',  // 重要: ファーストビューはeager
  'sp' => true,  // PC/SP別画像
  'wrapper_class' => 'p-kv__image-wrapper'
]);
?>
```

#### 例4: ロゴ出力（専用関数）

```php
<?php
// デフォルト設定（header.phpで使用）
render_logo();

// カスタム設定
render_logo([
  'width' => 200,
  'height' => 60,
  'class' => 'custom-logo'
]);
?>
```

### 出力されるHTML例

```html
<!-- render_responsive_image() の出力例 -->
<picture>
  <!-- SP用WebP（767px以下） -->
  <source
    type="image/webp"
    media="(max-width: 767px)"
    srcset="/assets/images/hero_sp.webp 1x, /assets/images/hero_sp@2x.webp 2x"
  />
  <!-- PC用WebP -->
  <source
    type="image/webp"
    srcset="/assets/images/hero.webp 1x, /assets/images/hero@2x.webp 2x"
  />
  <!-- SP用フォールバック（767px以下） -->
  <source
    type="image/png"
    media="(max-width: 767px)"
    srcset="/assets/images/hero_sp.png 1x, /assets/images/hero_sp@2x.png 2x"
  />
  <!-- PC用フォールバック -->
  <img
    src="/assets/images/hero.png"
    srcset="/assets/images/hero.png 1x, /assets/images/hero@2x.png 2x"
    width="1440"
    height="800"
    alt="ヒーロー画像"
    loading="lazy"
    class="p-page__hero-image"
  />
</picture>
```

### メリット

1. **WebP対応**: 最新ブラウザで自動的にWebP形式を使用、ファイルサイズを削減
2. **Retina対応**: 高解像度ディスプレイで自動的に@2x画像を使用
3. **レスポンシブ対応**: PC/SP別画像の自動切り替え
4. **パフォーマンス最適化**: `loading="lazy"` で遅延読み込み、`width`/`height`でCLS防止
5. **保守性向上**: 画像処理ロジックを一元管理
6. **メタデータ自動取得**: `images-meta.php`から自動でwidth/heightを取得

### 例外ケース

以下の場合のみ、`render_responsive_image()`を使わず直接`<img>`タグ使用可能：

#### 1. SVG画像（インラインSVG推奨）

```php
// ✅ OK: SVGはそのまま記述
<img src="<?php echo get_template_directory_uri(); ?>/assets/images/icon.svg" alt="アイコン">
```

#### 2. 外部URL画像

```php
// ✅ OK: 外部URL（CDN等）
<img src="https://cdn.example.com/image.jpg" alt="外部画像" loading="lazy">
```

#### 3. CSS background-image

```php
// ✅ OK: 装飾的な背景画像
<div class="p-section__bg" style="background-image: url(...)"></div>
```

### loading属性の使い分け

| 用途 | loading値 | 理由 |
|------|-----------|------|
| **ファーストビュー画像** | `eager` | LCPスコア向上、すぐに表示 |
| **スクロール後の画像** | `lazy` | 初期ロード高速化、帯域節約 |
| **ギャラリー画像** | `lazy` | 必要時に読み込み |
| **ロゴ** | `eager` | すぐに表示が必要 |

### チェックリスト

画像実装時は以下を確認：

- [ ] **画像ソースを確認**: `/assets/images/` or `/wp-content/uploads/` ?
- [ ] **関数選択**:
  - テーマ静的画像 → `render_responsive_image()`
  - 投稿サムネイル → `the_post_thumbnail()`
  - ACF画像ID → `wp_get_attachment_image()`
- [ ] **404エラー回避**: WordPressアップロード画像に`render_responsive_image()`を使っていないか
- [ ] `loading` 属性を適切に設定しているか（lazy/eager）
- [ ] `alt` 属性を設定しているか（アクセシビリティ）
- [ ] `class` 属性でBEM命名規則を守っているか
- [ ] 存在チェック（`has_post_thumbnail()`, `if ($thumbnail_id)` 等）をしているか
- [ ] ファーストビュー画像は `loading="eager"` を使用しているか

## HTML出力のサニタイズ規約

ACFフィールドやユーザー入力を出力する際は、適切なエスケープ関数を使用してください。

### エスケープ関数の使い分け

| フィールドタイプ | 関数 | 用途 |
|----------------|------|------|
| **WYSIWYG** | `wp_kses_post()` | HTMLタグを許可しつつ危険なタグを除去 |
| **テキストエリア（HTML含む）** | `wp_kses_post()` | `<br>`等のHTMLを含む場合 |
| **テキストエリア（プレーン）** | `esc_html()` + `nl2br()` | 改行のみ変換する場合 |
| **テキスト（単行）** | `esc_html()` | HTMLタグを許可しない |
| **URL** | `esc_url()` | リンク先URL |
| **属性値** | `esc_attr()` | HTML属性値（class, id等） |
| **メールアドレス** | `sanitize_email()` | メールアドレス |

### 実装パターン

#### WYSIWYGフィールドの出力

```php
// ✅ GOOD: wp_kses_postでサニタイズ
<?php echo wp_kses_post($wysiwyg_content); ?>

// ❌ BAD: 直接出力（XSS脆弱性の可能性）
<?php echo $wysiwyg_content; ?>
```

#### テキストエリア（HTML含む）の出力

```php
// ✅ GOOD: brタグ等を含む場合
<?php echo wp_kses_post($textarea_with_html); ?>

// ✅ GOOD: フォールバック付きヘルパー関数との組み合わせ
<?php echo wp_kses_post(get_acf_field_with_fallback('field_name', 'デフォルト<br>テキスト', $page_id)); ?>
```

#### テキストフィールドの出力

```php
// ✅ GOOD: 単行テキスト
<?php echo esc_html($text_field); ?>

// ✅ GOOD: 属性値として使用
<div class="<?php echo esc_attr($class_name); ?>">

// ✅ GOOD: URL
<a href="<?php echo esc_url($link_url); ?>">
```

### 禁止パターン

```php
// ❌ BAD: ACFフィールドを直接出力
<?php echo get_field('wysiwyg_field'); ?>

// ❌ BAD: 変数を直接出力
<?php echo $content; ?>

// ❌ BAD: the_field()の使用（エスケープなし）
<?php the_field('wysiwyg_field'); ?>
```

### チェックリスト

WYSIWYG/テキストエリア出力時は以下を確認：

- [ ] `wp_kses_post()` でサニタイズしているか
- [ ] `the_field()` を使用していないか（`get_field()` + エスケープを推奨）
- [ ] フォールバック値もHTMLを含む場合は `wp_kses_post()` を使用しているか

## template-parts 切り分けルール

WordPressテーマで再利用可能なコンポーネントを適切に設計するための規約です。

### 切り出し基準（判定表）

以下の表に従って、コードをtemplate-partに切り出すか判断してください。

| 条件 | 切り出し | 配置先 | 例 |
|------|---------|--------|-----|
| **2箇所以上で使用** | ✅ 必須 | `common/` | page-header, link-button |
| **トップの大型セクション（70行以上）** | ✅ 推奨 | `home/section-*` | section-kv, section-business |
| **セクション内の繰り返し要素** | ✅ 推奨 | `home/top-*` | top-heading |
| **100行以上の複雑なマークアップ** | ✅ 推奨 | 分割検討 | section-kv（222行） |
| **ページ固有の1回のみ使用** | ❌ 不要 | ページ内に記述 | page-vision本文 |
| **単純な30行未満の要素** | ❌ 不要 | インライン記述 | 小さなテキストブロック |

**重要**: 「迷ったら切り出さない」を基本原則とし、明確な再利用性がある場合のみ切り出す。

### 配置ルール

```
template-parts/
├── common/              # 汎用コンポーネント（2箇所以上で使用）
│   ├── page-header.php
│   ├── link-button.php
│   ├── breadcrumbs.php
│   └── pagination.php
│
├── home/                # トップページ専用
│   ├── section-*.php    # 大型セクション（70行以上）
│   └── top-*.php        # セクション内の繰り返し要素
│
├── [page]/              # 特定ページ専用（今後追加される可能性）
│   └── [page]-*.php     # ページ固有コンポーネント
│
└── header/              # ヘッダー専用
    └── navigation.php
```

**命名規則:**
- `common/`: プレフィックスなしの汎用名詞（`page-header`, `link-button`）
- `home/`: `section-*`（大セクション）、`top-*`（小コンポーネント）
- ページ専用: `[page]-*` でプレフィックス付与

### page_id の受け渡しルール

**重要**: ACFフィールドを使用するtemplate-partsでは、親テンプレートから`page_id`を引数で渡してください。

#### ❌ 禁止パターン

```php
// template-parts内で直接IDを取得しない
$page_id = get_option('page_on_front');  // ❌
$page_id = get_the_ID();                  // ❌
```

#### ✅ 推奨パターン

```php
// 親テンプレート（page-home.php）
$page_id = get_the_ID();

get_template_part('template-parts/home/section-recruit', null, [
  'page_id' => $page_id
]);

// template-parts側（section-recruit.php）
$page_id = $args['page_id'];

$ja_label = get_field('home_recruit_ja_label', $page_id);
```

**理由**:
- DRY原則: `get_option()`や`get_the_ID()`の重複呼び出しを排除
- 明示的な依存関係: コンポーネントが何に依存しているか明確
- 再利用性: 将来的に別ページでも同じセクションを再利用可能
- テスト容易性: 任意のpage_idを渡してテスト可能

### 呼び出しパターン

#### パターン1: 引数なしシンプル呼び出し

**用途**: ACFを使用しない自己完結型セクション

```php
<?php
// ACF不使用のコンポーネント
get_template_part('template-parts/header/navigation');
?>
```

**適用例**: グローバルナビなど、ACFに依存しないコンポーネント

#### パターン2: 配列引数による柔軟な呼び出し（推奨）

**用途**: 汎用コンポーネント、再利用性の高い要素

```php
<?php
get_template_part('template-parts/common/page-header', null, [
  'breadcrumbs' => [
    ['href' => '/company/', 'label' => '会社情報']
  ],
  'ja_label' => '会社情報',
  'en_heading' => 'Company',
  'description' => '説明文（オプション）'
]);
?>
```

**引数設計のポイント:**
- 必須引数は3-5個以内に抑える
- オプション引数は`description`, `class_name`等の追加要素のみ
- 配列はフラット構造を優先（深いネストを避ける）

**コンポーネント側での受け取り:**
```php
<?php
// template-parts/common/page-header.php
$breadcrumbs = $args['breadcrumbs'] ?? [];
$ja_label = $args['ja_label'] ?? '';
$en_heading = $args['en_heading'] ?? '';
$description = $args['description'] ?? null;
?>
```

#### パターン3: グローバル変数を介した呼び出し（非推奨）

**用途**: 配列が深くネストする場合の回避策（できる限り避ける）

```php
<?php
// 送信側
$GLOBALS['custom_breadcrumbs'] = $breadcrumbs;
get_template_part('template-parts/common/breadcrumbs');
unset($GLOBALS['custom_breadcrumbs']);

// 受信側（breadcrumbs.php）
$breadcrumbs = $GLOBALS['custom_breadcrumbs'] ?? [];
?>
```

**注意**: グローバル変数は副作用が大きいため、配列引数で対応できる場合は使用しない。

### 引数設計のベストプラクティス

#### ✅ 良い引数設計

```php
// 例1: top-heading（シンプル、3-4個）
['ja_text' => '(　見出し　)', 'en_text' => 'Heading', 'align' => 'center']

// 例2: link-button（中程度、6-7個）
[
  'tag' => 'a',              // 'a' or 'button'
  'ja_text' => '詳しく見る',
  'en_text' => 'View More',
  'href' => '/page/',
  'external' => false,       // 外部リンクか
  'variant' => 'primary',    // デザインバリエーション
  'class_name' => ''         // 追加クラス（オプション）
]
```

**ポイント:**
- `tag`で`<a>`/`<button>`を切り替え可能
- `variant`でデザインパターンを制御
- `class_name`で柔軟にカスタマイズ可能

#### ❌ 悪い引数設計

```php
// ❌ 引数が多すぎる（10個以上）
['arg1' => '', 'arg2' => '', ... 'arg10' => '']

// ❌ 深いネスト
['section' => ['title' => ['ja' => '', 'en' => ''], 'items' => [...]]]

// ❌ 用途不明な引数名
['data1' => '', 'option' => '', 'flag' => true]
```

**理由**: 可読性が低下し、保守が困難になる

### 既存コンポーネント一覧

| コンポーネント | 用途 | 使用箇所 | 引数 |
|--------------|------|---------|------|
| **common/** | | | |
| `page-header` | ページヘッダー | 14箇所（下層ページ） | breadcrumbs, ja_label, en_heading, description(opt) |
| `link-button` | 汎用リンクボタン | 2箇所 | tag, ja_text, en_text, href, external, variant, class_name(opt) |
| `breadcrumbs` | パンくずリスト | 3箇所 | breadcrumbs配列 |
| `pagination` | ページネーション | 1箇所（archive） | category(opt) |
| **home/** | | | |
| `top-heading` | セクション見出し | 4箇所（home内） | ja_text, en_text, align, class_name(opt) |
| `section-kv` | キービジュアル | 1箇所（top） | page_id |
| `section-business` | 事業紹介 | 1箇所（top） | page_id |
| `section-about` | About us | 1箇所（top） | page_id |
| `section-news` | ニュース | 1箇所（top） | page_id |
| `section-message` | メッセージ | 1箇所（top） | page_id |
| `section-recruit` | 採用 | 1箇所（top） | page_id |
| **header/** | | | |
| `navigation` | グローバルナビ | 1箇所（header） | なし（自己完結） |

### 新規コンポーネント作成チェックリスト

新規でtemplate-partを作成する際は、以下を確認してください。

- [ ] **再利用性**: 2箇所以上で使用される予定があるか
- [ ] **サイズ**: 70行以上の大型セクション、または複雑なマークアップか
- [ ] **配置**: `common/` か `[page]/` のどちらに配置すべきか判断した
- [ ] **命名**: 規約に沿った名前か（section-*, top-*, 汎用名詞）
- [ ] **引数**: 必須引数が3-5個以内、深いネストがない
- [ ] **ドキュメント**: 用途・引数をコメントで記載した
- [ ] **既存確認**: 同じ機能のコンポーネントが既に存在しないか確認した

```php
<?php
/**
 * Component Name: リンクボタン
 *
 * 用途: 汎用的なリンクボタン（内部/外部リンク対応）
 *
 * 引数:
 * - tag (string): 'a' または 'button'
 * - ja_text (string): 日本語テキスト（必須）
 * - en_text (string): 英語テキスト（必須）
 * - href (string): リンク先URL（tagが'a'の場合必須）
 * - external (bool): 外部リンクか（デフォルト: false）
 * - variant (string): デザインバリエーション（primary, secondary等）
 * - class_name (string): 追加CSSクラス（オプション）
 */

$tag = $args['tag'] ?? 'a';
$ja_text = $args['ja_text'] ?? '';
// ...
?>
```

---

## HTMLセマンティック規約

### 必須ルール

#### 1. section要素には必ず見出しを含める

`<section>` タグを使用する場合、必ず見出し（h1-h6）を含めてください。見出しがない場合は `<div>` を使用すること。

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

**理由:**
- セマンティックHTML: `<section>` は明確なテーマを持つコンテンツのまとまり
- アクセシビリティ: スクリーンリーダーがセクションの内容を理解しやすくなる
- SEO: 検索エンジンがコンテンツ構造を正しく認識

#### 2. 繰り返し要素はリストにする

同じ構造の要素が3個以上連続する場合、`<ul>` または `<ol>` を使用してください。

```html
<!-- ❌ NG: 同じ構造が3個以上 -->
<div class="p-news__item">...</div>
<div class="p-news__item">...</div>
<div class="p-news__item">...</div>

<!-- ✅ OK: ul/ol使用 -->
<ul class="p-news__list">
  <li class="p-news__item">...</li>
  <li class="p-news__item">...</li>
  <li class="p-news__item">...</li>
</ul>

<!-- ✅ OK: 順序がある場合はol -->
<ol class="p-steps__list">
  <li class="p-steps__item">ステップ1</li>
  <li class="p-steps__item">ステップ2</li>
  <li class="p-steps__item">ステップ3</li>
</ol>
```

**理由:**
- セマンティックHTML: リストは関連項目のグループであることを示す
- アクセシビリティ: スクリーンリーダーが項目数を読み上げる
- CSS: リストマーカーを利用したスタイリングが可能

**例外:**
- 2個以下の繰り返しは `<div>` でも可
- グリッドレイアウト等、視覚的に分離されている場合は個別判断

#### 3. 記事/カードは article を使用

ブログ投稿、ニュース記事、カード要素など、**独立したコンテンツ**には `<article>` を使用してください。

```html
<!-- ❌ NG: divを使用 -->
<div class="p-blog__post">
  <h2>タイトル</h2>
  <time>2024-01-01</time>
  <p>本文</p>
</div>

<!-- ✅ OK: article使用 -->
<article class="p-blog__post">
  <h2>タイトル</h2>
  <time datetime="2024-01-01">2024-01-01</time>
  <p>本文</p>
</article>

<!-- ✅ OK: カード形式の場合も同様 -->
<ul class="p-cards__list">
  <li class="p-cards__item">
    <article class="c-card">
      <h3 class="c-card__title">カードタイトル</h3>
      <p class="c-card__text">カード本文</p>
    </article>
  </li>
</ul>
```

**判定基準（articleを使うべき要素）:**
- ✅ ブログ投稿、ニュース記事
- ✅ 商品カード、サービス紹介カード
- ✅ レビュー、コメント
- ✅ SNS投稿
- ❌ ナビゲーション、サイドバー
- ❌ 装飾的な要素、レイアウト要素

**BEM命名との組み合わせ:**
- `__post`, `__card`, `__article` を含むクラス名 → `<article>` を使用
- 例: `p-blog__post`, `c-news-card`, `p-review__article`

#### 4. ボタンとリンクの使い分け

アクション実行には `<button>`、ページ遷移には `<a>` を使用してください。

```html
<!-- ❌ NG: ページ遷移しないのに <a> -->
<a href="#" class="c-button" onclick="submitForm()">送信</a>

<!-- ✅ OK: アクション = button -->
<button type="button" class="c-button" onclick="submitForm()">送信</button>
<button type="submit" class="c-button">送信</button>

<!-- ✅ OK: ページ遷移 = a -->
<a href="/contact/" class="c-button">お問い合わせ</a>

<!-- ✅ OK: モーダル表示 = button -->
<button type="button" class="c-button" data-modal="contact">お問い合わせ</button>

<!-- ✅ OK: アンカーリンク = a -->
<a href="#section-about" class="c-button">詳しく見る</a>
```

**判定基準:**
| 要素 | 用途 | href属性 | type属性 |
|------|------|---------|---------|
| `<a>` | ページ遷移、アンカーリンク、外部リンク | 必須 | なし |
| `<button>` | フォーム送信、モーダル表示、アコーディオン等 | 不要 | button/submit |

**理由:**
- セマンティックHTML: 要素が持つ本来の意味を正しく使用
- アクセシビリティ: キーボード操作（Enterキー）の動作が適切
- SEO: 検索エンジンがリンクを正しく認識

**禁止パターン:**
```html
<!-- ❌ href="#" は禁止（JavaScriptでの操作のみ） -->
<a href="#" class="c-button" onclick="doSomething()">クリック</a>

<!-- ❌ aタグでJavaScript操作 -->
<a href="javascript:void(0)" class="c-button">クリック</a>

<!-- ✅ 正しい修正 -->
<button type="button" class="c-button" onclick="doSomething()">クリック</button>
```

### 自動チェック

HTMLセマンティック規約は自動チェックツールで検証できます。

```bash
# HTML構造チェック（W3C準拠、見出しレベル等）
npm run check:html

# HTMLセマンティックチェック（プロジェクト規約）
npm run check:html:semantic

# 統合チェック（構造 + セマンティック + テンプレート品質）
npm run check:templates
```

**詳細:** `docs/html-validation-guide.md` を参照

### チェックリスト

HTML実装時は以下を確認：

- [ ] `<section>` には見出し（h1-h6）が含まれているか
- [ ] 3個以上の繰り返し要素は `<ul>` または `<ol>` を使用しているか
- [ ] ブログ投稿・カード要素には `<article>` を使用しているか
- [ ] ページ遷移するボタンは `<a>` を使用しているか
- [ ] JavaScript操作のみのボタンは `<button>` を使用しているか
- [ ] `<a href="#">` を使用していないか
- [ ] `<time>` タグに `datetime` 属性を設定しているか

### 参考

**W3C仕様:**
- [HTML Living Standard - Sections](https://html.spec.whatwg.org/multipage/sections.html)
- [HTML Living Standard - Grouping content](https://html.spec.whatwg.org/multipage/grouping-content.html)

**アクセシビリティ:**
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WCAG 2.1 - Guideline 1.3 Adaptable](https://www.w3.org/WAI/WCAG21/Understanding/adaptable)
