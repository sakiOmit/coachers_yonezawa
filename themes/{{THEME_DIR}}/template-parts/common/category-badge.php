<?php
/**
 * カテゴリーバッジコンポーネント
 *
 * 使用方法:
 * <?php get_template_part('template-parts/common/category-badge', null, [
 *   'label' => 'News',
 *   'class' => 'c-category-badge--dark' // オプション
 * ]); ?>
 *
 * @package {{PACKAGE_NAME}}
 */

// 引数バリデーション（開発環境のみ）
if ( ! validate_template_args($args, [ 'label' ], 'category-badge') ) {
    return;
}

// 引数を取得（デフォルト値つき）
$args = merge_template_defaults($args, [
    'label' => '',
    'class' => '',
]);

$label = $args['label'];
$class = $args['class'];
?>

<span class="c-category-badge <?php echo esc_attr($class); ?>">
  <?php echo esc_html($label); ?>
</span>
