<?php
/**
 * Template Name: Single Post (Topics Detail)
 *
 * 通常投稿の詳細ページテンプレート
 */

get_header();

// カテゴリー取得
$categories    = get_the_category();
$category_name = ! empty($categories) ? esc_html($categories[0]->name) : '';
$category_link = ! empty($categories) ? esc_url(get_category_link($categories[0]->term_id)) : '';

// パンくず配列
$breadcrumbs = array(
    array(
'href' => get_post_type_archive_link('post'),
'label' => 'トピックス'
),
    array(
'href' => '',
'label' => get_the_title()
)
);
?>

<main class="p-single">
    <?php
    // PageHeader コンポーネント
    get_template_part('template-parts/common/page-header', null, array(
        'breadcrumbs' => $breadcrumbs,
        'ja_label' => 'トピックス',
        'en_heading' => 'Topics'
    ));
    ?>

    <?php
    while ( have_posts() ) :
      the_post();
      ?>

        <!-- 記事ヘッダーセクション -->
        <section class="p-single__header">
            <div class="p-single__header-wrapper">
                <?php if ( has_post_thumbnail() ) : ?>
                    <div class="p-single__thumbnail">
                        <?php
                        the_post_thumbnail(
                            'large',
                            [
                                'class' => 'p-single__thumbnail-image',
                                'loading' => 'eager',
                            ]
                        );
                        ?>
                    </div>
                <?php endif; ?>

                <div class="p-single__meta">
                    <?php if ( ! empty($category_name) ) : ?>
                        <a href="<?php echo esc_url( $category_link ); ?>" class="p-single__category">
                            <?php echo esc_html( $category_name ); ?>
                        </a>
                    <?php endif; ?>

                    <h1 class="p-single__title"><?php echo esc_html(get_the_title()); ?></h1>

                    <time class="p-single__date" datetime="<?php echo esc_attr(get_the_date('c')); ?>">
                        <?php echo esc_html(get_the_date('Y.m.d')); ?>
                    </time>
                </div>
            </div>
        </section>

        <!-- 記事本文エリア -->
        <div class="p-single__content">
            <?php the_content(); ?>
        </div>

        <!-- 一覧へ戻るボタン -->
        <div class="p-single__back-button">
            <a href="<?php echo esc_url(get_post_type_archive_link('post')); ?>" class="p-single__back-link">
                一覧へ戻る
            </a>
        </div>

    <?php endwhile; ?>

    <!-- 関連記事セクション -->
    <?php
    $categories = get_the_category();
    if ( $categories ) {
        $category_ids = array();
      foreach ( $categories as $category ) {
          $category_ids[] = $category->term_id;
      }

        $args = array(
            'category__in' => $category_ids,
            'post__not_in' => array( get_the_ID() ),
            'posts_per_page' => 3,
            'orderby' => 'date',
            'order' => 'DESC'
        );

        $related_query = new WP_Query($args);

        if ( $related_query->have_posts() ) :
          ?>
        <section class="p-single__related">
            <div class="p-single__related-header">
                <p class="p-single__related-title-en">Related News</p>
                <h2 class="p-single__related-title-ja">関連記事</h2>
            </div>

            <div class="p-single__related-grid">
                <?php
                while ( $related_query->have_posts() ) :
                  $related_query->the_post();
                  ?>
                    <?php
                    $card_categories    = get_the_category();
                    $card_category_name = ! empty($card_categories) ? esc_html($card_categories[0]->name) : '';
                    ?>

                    <article class="p-single__related-card">
                        <a href="<?php the_permalink(); ?>" class="p-single__related-card-link">
                            <?php if ( has_post_thumbnail() ) : ?>
                                <div class="p-single__related-card-thumbnail">
                                    <?php
                                    the_post_thumbnail(
                                        'medium',
                                        [
                                            'class' => 'p-single__related-card-image',
                                            'loading' => 'lazy',
                                        ]
                                    );
                                    ?>
                                </div>
                            <?php endif; ?>

                            <div class="p-single__related-card-meta">
                                <?php if ( ! empty($card_category_name) ) : ?>
                                    <span class="p-single__related-card-category">
                                        <?php echo esc_html( $card_category_name ); ?>
                                    </span>
                                <?php endif; ?>

                                <h3 class="p-single__related-card-title">
                                    <?php echo esc_html(get_the_title()); ?>
                                </h3>

                                <time class="p-single__related-card-date" datetime="<?php echo esc_attr(get_the_date('c')); ?>">
                                    <?php echo esc_html(get_the_date('Y.m.d')); ?>
                                </time>
                            </div>
                        </a>
                    </article>

                <?php endwhile; ?>
            </div>
        </section>
          <?php
        endif;
        wp_reset_postdata();
    }
    ?>

</main>

<?php get_footer(); ?>
