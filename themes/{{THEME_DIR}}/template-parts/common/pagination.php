<?php
/**
 * ページネーションコンポーネント
 *
 * 使用方法:
 * <?php get_template_part('template-parts/common/pagination', null, [
 *   'custom_query' => $custom_query  // オプション: カスタムクエリを使用する場合
 * ]); ?>
 *
 * @package {{PACKAGE_NAME}}
 */

global $wp_query;
$custom_query = isset($args['custom_query']) ? $args['custom_query'] : $wp_query;
$pages_num    = (int) $custom_query->max_num_pages;
$paged        = ( get_query_var('paged') ) ? get_query_var('paged') : 1;

// 1ページのみの場合は表示しない
if ( $pages_num <= 1 ) {
  return;
}
?>

<div class="c-pagination">
  <?php
  $page_links = paginate_links(array(
    'base'      => str_replace(999999999, '%#%', esc_url(get_pagenum_link(999999999))),
    'format'    => '?paged=%#%',
    'mid_size'  => 1,
    'end_size'  => 1,
    'current'   => max(1, get_query_var('paged', 1)),
    'total'     => $pages_num,
    'prev_next' => true,
    'prev_text' => '<svg width="6" height="13" viewBox="0 0 6 13" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4.48886 12.6731C4.78604 13.0817 5.29237 13.1119 5.61928 12.7405C5.94618 12.369 5.97034 11.736 5.67318 11.3274L2.1624 6.50022L5.67318 1.67308C5.97034 1.26442 5.94618 0.631482 5.61928 0.25999C5.29237 -0.11147 4.78604 -0.0812684 4.48886 0.327373L0 6.50023L4.48886 12.6731Z" fill="currentColor"/></svg>',
    'next_text' => '<svg width="6" height="13" viewBox="0 0 6 13" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1.39395 12.6731C1.09677 13.0817 0.590447 13.1119 0.263535 12.7405C-0.0633635 12.369 -0.0875239 11.736 0.209631 11.3274L3.72041 6.50022L0.209631 1.67308C-0.0875236 1.26442 -0.0633634 0.631482 0.263535 0.25999C0.590447 -0.11147 1.09677 -0.0812684 1.39395 0.327373L5.88281 6.50023L1.39395 12.6731Z" fill="currentColor"/></svg>',
    'type'      => 'array',
  ));

  if ( $page_links ) {
    foreach ( $page_links as $link ) {
      $class = 'c-pagination__item';

      if ( strpos($link, 'prev') !== false ) {
        $class .= ' c-pagination__item--prev';
      } elseif ( strpos($link, 'next') !== false ) {
        $class .= ' c-pagination__item--next';
      } elseif ( strpos($link, 'current') !== false ) {
        $class .= ' c-pagination__item--current';
      } elseif ( strpos($link, 'dots') !== false ) {
        $class .= ' c-pagination__item--dots';
      }

      // クラスを追加してリンクを出力
      $link = str_replace('class="', 'class="' . $class . ' ', $link);
      // class属性がない場合は追加
      if ( strpos($link, 'class="') === false ) {
        $link = str_replace('<a ', '<a class="' . $class . '" ', $link);
        $link = str_replace('<span ', '<span class="' . $class . '" ', $link);
      }

      echo wp_kses_post( $link );
    }
  }
  ?>
</div>
