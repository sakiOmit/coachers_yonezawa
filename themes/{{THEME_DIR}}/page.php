<?php
/**
 * Default Page Template
 *
 * @package {{PACKAGE_NAME}}
 */

get_header();
?>

<main class="p-page">
  <div class="p-page__content">
    <?php
    while ( have_posts() ) :
      the_post();
      ?>
    <article id="page-<?php the_ID(); ?>" <?php post_class(); ?>>
      <h1><?php the_title(); ?></h1>
      <?php the_content(); ?>
    </article>
    <?php endwhile; ?>
  </div>
</main>

<?php get_footer(); ?>