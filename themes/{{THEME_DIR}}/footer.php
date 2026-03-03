<?php
$footer_variant = isset($args['variant']) ? $args['variant'] : 'default';
$footer_class   = $footer_variant === 'light' ? 'l-footer l-footer--light' : 'l-footer';
?>
<footer class="<?php echo esc_attr($footer_class); ?>">
  <div class="l-footer__container">
    <div class="l-footer__inner">
      <div class="l-footer__grid">
        <!-- Left Column -->
        <div class="l-footer__left">
          <!-- Logo -->
          <div class="l-footer__logo-wrapper">
            <a href="<?php echo esc_url(home_url('/')); ?>" class="l-footer__logo-link">
              <?php
              render_responsive_image([
                'src' => get_template_directory_uri() . '/assets/images/common/logo.svg',
                'alt' => get_bloginfo('name'),
                'class' => 'l-footer__logo-image',
                'width' => 120,
                'height' => 24,
                'loading' => 'lazy'
              ]);
              ?>
            </a>
          </div>

          <!-- Company Info -->
          <div class="l-footer__company">
            <p class="l-footer__company-name">{{COMPANY_NAME}}</p>
            <p class="l-footer__company-address"><?php echo esc_html(get_site_info('address')); ?></p>
            <a href="<?php echo esc_url({{THEME_PREFIX}}_GOOGLE_MAPS_URL); ?>" target="_blank" rel="noopener noreferrer"
              class="l-footer__map-link">
              <?php
              render_responsive_image([
                'src' => get_template_directory_uri() . '/assets/images/common/icon-google-map.png',
                'alt' => '',
                'class' => 'l-footer__map-icon',
                'loading' => 'lazy',
                'sp' => false,
              ]);
              ?>
              Google Map
            </a>
            <a href="<?php echo esc_url(home_url('/privacy/')); ?>" class="l-footer__privacy-link">
              プライバシーポリシー
            </a>
          </div>
        </div>

        <!-- Right Column -->
        <div class="l-footer__right">
          <!-- Navigation -->
          <nav class="l-footer__nav">
            <ul class="l-footer__menu">
              <li class="l-footer__menu-item">
                <a href="<?php echo esc_url(home_url('/')); ?>" class="l-footer__menu-link">
                  Home
                </a>
              </li>
              <li class="l-footer__menu-item">
                <a href="<?php echo esc_url(home_url('/about/')); ?>" class="l-footer__menu-link">
                  About
                </a>
              </li>
              <li class="l-footer__menu-item">
                <a href="<?php echo esc_url(home_url('/contact/')); ?>" class="l-footer__menu-link">
                  Contact
                </a>
              </li>
            </ul>
          </nav>
        </div>
      </div>

      <!-- Copyright -->
      <p class="l-footer__copyright">
        &copy; {{COMPANY_NAME_EN}} All Rights Reserved.
      </p>
    </div>
  </div>
</footer>

<?php wp_footer(); ?>
</body>

</html>
