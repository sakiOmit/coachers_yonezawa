<?php
/**
 * Logo Component
 *
 * @package {{PACKAGE_NAME}}
 */
?>

<a href="<?php echo esc_url(home_url('/')); ?>" class="c-logo">
  <img
    src="<?php echo esc_url(get_template_directory_uri() . '/assets/images/common/logo.svg'); ?>"
    alt="<?php echo esc_attr(get_bloginfo('name')); ?>"
    width="145"
    height="50"
  >
</a>
