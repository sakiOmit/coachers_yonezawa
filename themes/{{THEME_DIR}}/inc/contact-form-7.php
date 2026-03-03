<?php
/**
 * Contact Form 7 Settings
 *
 * @package {{PACKAGE_NAME}}
 */

/**
 * CF7の自動挿入される<p>タグと<br>タグを除去
 */
add_filter('wpcf7_autop_or_not', '__return_false');
