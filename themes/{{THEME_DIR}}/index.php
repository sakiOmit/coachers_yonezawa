<?php
/**
 * Main Index Template
 *
 * @package {{PACKAGE_NAME}}
 */

get_header();
?>

<main class="p-archive">
  <div class="p-archive__content">
    <?php if ( have_posts() ) : ?>
      <?php
      while ( have_posts() ) :
        the_post();
        ?>
        <article id="post-<?php the_ID(); ?>" <?php post_class(); ?>>
          <h2><?php the_title(); ?></h2>
          <?php the_excerpt(); ?>
        </article>
      <?php endwhile; ?>

      <?php the_posts_pagination(); ?>
    <?php else : ?>
      <p><?php esc_html_e('No posts found.', '{{TEXT_DOMAIN}}'); ?></p>
    <?php endif; ?>
  </div>
</main>

<?php get_footer(); ?>
