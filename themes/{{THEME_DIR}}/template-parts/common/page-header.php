<?php

/**
 * ページヘッダーコンポーネント（見出し + 説明文 + パンくず）
 *
 * 使用方法:
 * <?php
 * get_template_part('template-parts/common/page-header', null, [
 *   'breadcrumbs' => [['href' => '/contact/', 'label' => 'お問い合わせ']],
 *   'ja_label' => 'お問い合わせフォーム',
 *   'en_heading' => 'Contact',
 *   'description' => 'お問い合わせに関する説明文がここに入ります。' // オプション
 * ]);
 * ?>
 *
 * @package {{PACKAGE_NAME}}
 */

// 引数を取得（デフォルト値つき）
$args = merge_template_defaults($args, [
  'breadcrumbs' => [],
  'ja_label' => '',
  'en_heading' => '',
  'catchphrase' => '', // キャッチコピー（オプション）
  'description' => '',
  'modifier_class' => '', // モディファイアクラス（例: 'horizontal', 'dark'）
  'breadcrumb_only' => false, // パンくずのみ表示モード
]);

$breadcrumbs     = $args['breadcrumbs'];
$ja_label        = $args['ja_label'];
$en_heading      = $args['en_heading'];
$catchphrase     = $args['catchphrase'];
$description     = $args['description'];
$modifier_class  = $args['modifier_class'];
$breadcrumb_only = $args['breadcrumb_only'];

// 引数バリデーション（開発環境のみ）
// breadcrumb_only モードの場合は en_heading は不要
if ( ! $breadcrumb_only && ! validate_template_args($args, [ 'en_heading', 'breadcrumbs' ], 'page-header') ) {
  return;
}

// クラス名を構築
$class_name = 'c-page-header js-hero';
if ( ! empty($modifier_class) ) {
  $class_name .= ' c-page-header--' . esc_attr($modifier_class);
}
if ( $breadcrumb_only ) {
  $class_name .= ' c-page-header--breadcrumb-only';
}
?>

<section class="<?php echo esc_attr( $class_name ); ?>">
  <div class="c-page-header__container">
    <?php if ( $breadcrumb_only ) : ?>
      <!-- パンくずのみ表示モード -->
      <div class="c-page-header__inner">
        <div class="c-page-header__breadcrumbs">
          <?php
          get_template_part('template-parts/common/breadcrumbs', null, array(
            'breadcrumbs' => $breadcrumbs
          ));
          ?>
        </div>
      </div>
    <?php else : ?>
      <!-- 通常モード（見出し + パンくず） -->
      <div class="c-page-header__inner">
        <div class="c-page-header__breadcrumbs">
          <?php
          // パンくずリストを表示（引数として渡す）
          get_template_part('template-parts/common/breadcrumbs', null, array(
            'breadcrumbs' => $breadcrumbs
          ));
          ?>
        </div>
        <div class="c-page-header__content">
          <div class="c-page-header__titles">
            <?php if ( ! empty($en_heading) ) : ?>
              <h1 class="c-page-header__heading">
                <?php echo wp_kses($en_heading, array( 'br' => array( 'class' => array() ) )); ?></h1>
            <?php endif; ?>
            <?php if ( ! empty($ja_label) ) : ?>
              <p class="c-page-header__label"><?php echo esc_html($ja_label); ?></p>
            <?php endif; ?>
          </div>
          <?php if ( ! empty($catchphrase) ) : ?>
            <p class="c-page-header__catchphrase"><?php echo wp_kses_post($catchphrase); ?></p>
          <?php endif; ?>
        </div>
      </div>
      <?php if ( ! empty($description) ) : ?>
        <p class="c-page-header__description">
          <?php echo wp_kses($description, array( 'br' => array( 'class' => array() ) )); ?></p>
      <?php endif; ?>
    <?php endif; ?>
  </div>
</section>