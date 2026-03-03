<?php

/**
 * 404 Error Page
 *
 * @package {{PACKAGE_NAME}}
 */

get_header();
?>

<main class="p-404">
  <div class="p-404__content">
    <div class="p-404__wrapper">

      <!-- Error Code -->
      <div class="p-404__title">
        <h1 class="p-404__title-text">404<br class="u-visible-sp"> Page Not Found</h1>
      </div>

      <!-- Description -->
      <div class="p-404__description">
        <p class="p-404__description-heading">お探しのページは<br class="u-visible-sp">見つかりませんでした</p>
        <div class="p-404__description-text">
          <p>申し訳ございませんが、<br class="u-visible-sp">お探しのページは削除されたか、</p>
          <p>一時的にアクセスできない可能性があります。</p>
        </div>
      </div>

      <!-- Actions -->
      <div class="p-404__actions">
        <a href="<?php echo esc_url(home_url('/')); ?>" class="p-404__button p-404__button--primary">
          ホームに戻る
        </a>
        <button type="button" onclick="history.back();" class="p-404__button p-404__button--secondary">
          前のページへ
        </button>
      </div>

    </div>
  </div>
</main>

<?php
get_footer();