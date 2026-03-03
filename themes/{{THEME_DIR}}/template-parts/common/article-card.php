<?php
/**
 * 記事カードコンポーネント
 *
 * 使用方法:
 * <?php get_template_part('template-parts/common/article-card', null, [
 *   'thumbnail' => ['url' => 'https://example.com/image.jpg', 'alt' => '画像説明'],
 *   'date' => '2025.02.01',
 *   'category' => 'News',
 *   'title' => 'これはデザインを自然に見せるためのダミーテキストです',
 *   'link' => '/news/article-slug/',
 *   'is_tall' => false // オプション: 縦長カード
 * ]); ?>
 *
 * @package {{PACKAGE_NAME}}
 */

// 引数バリデーション（開発環境のみ）
if ( ! validate_template_args($args, [ 'date', 'category', 'title', 'link' ], 'article-card') ) {
    return;
}

// 引数を取得（デフォルト値つき）
$args = merge_template_defaults($args, [
    'thumbnail' => null,
    'date' => '',
    'category' => '',
    'title' => '',
    'link' => '',
    'is_tall' => false,
]);

$thumbnail  = $args['thumbnail'];
$date       = $args['date'];
$category   = $args['category'];
$title      = $args['title'];
$link       = $args['link'];
$is_tall    = $args['is_tall'];
$card_class = $is_tall ? 'c-article-card--tall' : '';
?>

<article class="c-article-card <?php echo esc_attr($card_class); ?>">
  <a href="<?php echo esc_url($link); ?>" class="c-article-card__link">
    <?php if ( $thumbnail ) : ?>
      <div class="c-article-card__thumbnail">
        <?php
        // render_responsive_image() を使用して画像を表示
        if ( isset($thumbnail['id']) ) {
          // ACF画像配列の場合（IDのみ）
          render_responsive_image([
            'src' => wp_get_attachment_url($thumbnail['id']),
            'alt' => $thumbnail['alt'] ?? '',
            'sp'  => false,
          ]);
        } elseif ( isset($thumbnail['url']) ) {
          // URLの場合
          render_responsive_image([
            'src' => $thumbnail['url'],
            'alt' => $thumbnail['alt'] ?? '',
            'sp'  => false,
          ]);
        }
        ?>
      </div>
    <?php endif; ?>

    <div class="c-article-card__content">
      <div class="c-article-card__meta">
        <time class="c-article-card__date" datetime="<?php echo esc_attr(str_replace('.', '-', $date)); ?>">
          <?php echo esc_html($date); ?>
        </time>
        <?php
        get_template_part('template-parts/common/category-badge', null, [
          'label' => $category
        ]);
        ?>
      </div>
      <h3 class="c-article-card__title"><?php echo esc_html($title); ?></h3>
    </div>
  </a>
</article>
