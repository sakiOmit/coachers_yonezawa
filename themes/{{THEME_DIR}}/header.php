<!DOCTYPE html>
<html lang="ja">

<head>
  <meta charset="<?php bloginfo('charset'); ?>">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload"
    href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100..900&family=Poppins:wght@400;500;600;700&display=swap"
    as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript>
    <link rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100..900&family=Poppins:wght@400;500;600;700&display=swap">
  </noscript>

  <?php wp_head(); ?>
</head>

<body <?php body_class(); ?>>
  <?php wp_body_open(); ?>

  <header class="l-header<?php echo is_front_page() ? ' l-header--home' : ''; ?>">
    <div class="l-header__container">
      <div class="l-header__inner">
        <!-- Logo -->
        <a href="<?php echo esc_url(home_url('/')); ?>" class="l-header__logo-link">
          <?php
          render_responsive_image([
            'src' => get_template_directory_uri() . '/assets/images/common/logo.svg',
            'alt' => get_bloginfo('name'),
            'class' => 'l-header__logo-image',
            'width' => 183,
            'height' => 63,
            'loading' => 'eager'
          ]);
          ?>
        </a>

        <!-- Navigation -->
        <nav class="l-header__nav">
          <ul class="l-header__menu">
            <li class="l-header__menu-item">
              <a href="<?php echo esc_url(home_url('/')); ?>" class="l-header__menu-link">
                Home
              </a>
            </li>
            <li class="l-header__menu-item">
              <a href="<?php echo esc_url(home_url('/about/')); ?>" class="l-header__menu-link">
                About
              </a>
            </li>
            <li class="l-header__menu-item">
              <a href="<?php echo esc_url(home_url('/contact/')); ?>" class="l-header__menu-link">
                Contact
              </a>
            </li>
          </ul>
        </nav>

        <!-- Hamburger Menu -->
        <button type="button" class="c-hamburger l-header__hamburger" aria-label="メニューを開く" aria-expanded="false">
          <span class="c-hamburger__line"></span>
          <span class="c-hamburger__line"></span>
        </button>
      </div>
    </div>

    <!-- Hamburger Menu Overlay -->
    <div class="l-hamburger-menu" role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="menu-title">
      <h2 id="menu-title" class="u-sr-only">ナビゲーションメニュー</h2>
      <div class="l-hamburger-menu__overlay" tabindex="-1" aria-label="メニューを閉じる">
      </div>
      <div class="l-hamburger-menu__content">
        <!-- Menu Items -->
        <nav class="l-hamburger-menu__nav">
          <div class="l-hamburger-menu__item">
            <a href="<?php echo esc_url(home_url('/')); ?>" class="l-hamburger-menu__link">
              <span class="l-hamburger-menu__title">Home</span>
            </a>
          </div>

          <div class="l-hamburger-menu__item">
            <a href="<?php echo esc_url(home_url('/about/')); ?>" class="l-hamburger-menu__link">
              <span class="l-hamburger-menu__title">About</span>
            </a>
          </div>

          <div class="l-hamburger-menu__item">
            <a href="<?php echo esc_url(home_url('/contact/')); ?>" class="l-hamburger-menu__link">
              <span class="l-hamburger-menu__title">Contact</span>
            </a>
          </div>
        </nav>
      </div>
    </div>
  </header>
