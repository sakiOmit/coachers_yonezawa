<?php
/**
 * セクション見出しコンポーネント
 *
 * 使用方法:
 * <?php get_template_part('template-parts/common/section-heading', null, [
 *   'ja_label' => '企業理念',
 *   'en_heading' => 'Corporate Philosophy',
 *   'wrapper_class' => 'c-section-heading__wrapper',  // オプション
 *   'ja_class' => 'c-section-heading__ja',            // オプション
 *   'en_class' => 'c-section-heading__en'             // オプション
 * ]); ?>
 *
 * @package {{PACKAGE_NAME}}
 */

// 引数バリデーション（開発環境のみ）
if ( ! validate_template_args($args, [ 'ja_label', 'en_heading' ], 'section-heading') ) {
    return;
}

// 引数を取得（デフォルト値つき）
$args = merge_template_defaults($args, [
    'ja_label' => '',
    'en_heading' => '',
    'wrapper_class' => 'c-section-heading__wrapper',
    'ja_class' => 'c-section-heading__ja',
    'en_class' => 'c-section-heading__en',
]);

$ja_label      = $args['ja_label'];
$en_heading    = $args['en_heading'];
$wrapper_class = $args['wrapper_class'];
$ja_class      = $args['ja_class'];
$en_class      = $args['en_class'];
?>

<div class="<?php echo esc_attr($wrapper_class); ?>">
  <p class="<?php echo esc_attr($ja_class); ?>"><?php echo wp_kses_post($ja_label); ?></p>
  <h2 class="<?php echo esc_attr($en_class); ?>"><?php echo wp_kses_post($en_heading); ?></h2>
</div>
