<?php
/**
 * パンくずリストコンポーネント
 *
 * 使用方法:
 * <?php get_template_part('template-parts/common/breadcrumbs', null, [
 *   'breadcrumbs' => [
 *     ['href' => '/about/', 'label' => '会社概要'],
 *     ['href' => '', 'label' => '現在のページ']  // hrefが空なら最終ページ
 *   ]
 * ]); ?>
 *
 * Schema.org BreadcrumbList 構造化マークアップ対応
 *
 * @package {{PACKAGE_NAME}}
 */

// 引数バリデーション（開発環境のみ）
if ( ! validate_template_args($args, [ 'breadcrumbs' ], 'breadcrumbs') ) {
    return;
}

// パンくずデータを取得
$breadcrumbs = $args['breadcrumbs'] ?? [];

// パンくずが空の場合は何も表示しない
if ( empty($breadcrumbs) ) {
    return;
}
?>

<div class="c-breadcrumbs">
  <nav class="c-breadcrumbs__nav" aria-label="Breadcrumb">
    <ol class="c-breadcrumbs__list" itemscope itemtype="https://schema.org/BreadcrumbList">
      <li
        class="c-breadcrumbs__item"
        itemprop="itemListElement"
        itemscope
        itemtype="https://schema.org/ListItem">
        <a class="c-breadcrumbs__link" itemprop="item" href="<?php echo esc_url(home_url('/')); ?>">
          <span class="c-breadcrumbs__text" itemprop="name">TOP</span>
        </a>
        <meta itemprop="position" content="1" />
      </li>

      <?php foreach ( $breadcrumbs as $index => $breadcrumb ) : ?>
        <li
          class="c-breadcrumbs__item"
          itemprop="itemListElement"
          itemscope
          itemtype="https://schema.org/ListItem">
          <?php if ( ! empty($breadcrumb['href']) ) : ?>
            <a class="c-breadcrumbs__link" itemprop="item" href="<?php echo esc_url($breadcrumb['href']); ?>">
              <span class="c-breadcrumbs__text" itemprop="name"><?php echo esc_html($breadcrumb['label']); ?></span>
            </a>
          <?php else : ?>
            <span class="c-breadcrumbs__text" itemprop="name"><?php echo esc_html($breadcrumb['label']); ?></span>
          <?php endif; ?>
          <meta itemprop="position" content="<?php echo esc_attr($index + 2); ?>" />
        </li>
      <?php endforeach; ?>
    </ol>
  </nav>
</div>
