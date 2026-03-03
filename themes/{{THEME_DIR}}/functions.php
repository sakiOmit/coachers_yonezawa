<?php
/**
 * Theme functions and definitions
 *
 * @package {{PACKAGE_NAME}}
 */

// テーマバージョン
define('THEME_VERSION', '1.0.0');

// ============================================
// コア機能（必須）
// ============================================
require_once get_template_directory() . '/inc/constants.php';
require_once get_template_directory() . '/inc/setup.php';
require_once get_template_directory() . '/inc/enqueue.php';
require_once get_template_directory() . '/inc/helpers.php';
require_once get_template_directory() . '/inc/image-helpers.php';
require_once get_template_directory() . '/inc/template-validation.php';

// ============================================
// ACF（Advanced Custom Fields）
// ============================================
require_once get_template_directory() . '/inc/acf-auto-import.php';
require_once get_template_directory() . '/inc/advanced-custom-fields/loader.php';

// ============================================
// カスタム投稿タイプ（プロジェクトに応じて編集）
// ============================================
require_once get_template_directory() . '/inc/custom-post-types.php';

// ============================================
// プラグイン連携（必要に応じて有効化）
// ============================================
require_once get_template_directory() . '/inc/contact-form-7.php';

// ============================================
// ACF JSON保存パス設定
// 管理画面でフィールドを編集する場合は以下を有効化
// ============================================
// add_filter('acf/settings/save_json', function($path) {
//     return get_template_directory() . '/acf-json';
// });

// add_filter('acf/settings/load_json', function($paths) {
//     unset($paths[0]);
//     $paths[] = get_template_directory() . '/acf-json';
//     return $paths;
// });
