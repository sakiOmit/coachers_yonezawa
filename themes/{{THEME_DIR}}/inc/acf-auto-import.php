<?php
/**
 * ACF フィールドグループ自動インポート
 *
 * acf-json ディレクトリからフィールドグループを自動的にインポート
 *
 * @package {{PACKAGE_NAME}}
 */

/**
 * ACFフィールドグループを自動インポート
 *
 * 初回アクセス時にacf-jsonからフィールドグループをインポート
 */
function {{THEME_PREFIX}}_acf_auto_import_field_groups() {
    // ACFがインストールされていない場合は何もしない
  if ( ! function_exists('acf_add_local_field_group') ) {
      return;
  }

    // 既にインポート済みかチェック
    $imported = get_option('{{THEME_PREFIX}}_acf_imported', false);
  if ( $imported ) {
      return;
  }

    $json_dir = get_template_directory() . '/acf-json';

    // acf-jsonディレクトリが存在しない場合
  if ( ! is_dir($json_dir) ) {
      return;
  }

    // JSONファイルを取得
    $json_files = glob($json_dir . '/*.json');

  if ( empty($json_files) ) {
      return;
  }

    $imported_count = 0;

  foreach ( $json_files as $file ) {
      $json_data   = file_get_contents($file);
      $field_group = json_decode($json_data, true);

    if ( ! $field_group || ! isset($field_group['key']) ) {
        continue;
    }

      // 既存のフィールドグループをチェック
      $existing = acf_get_field_group($field_group['key']);

    if ( ! $existing ) {
        // 新規インポート
        acf_import_field_group($field_group);
        ++$imported_count;
    }
  }

  if ( $imported_count > 0 ) {
      // インポート完了フラグを設定
      update_option('{{THEME_PREFIX}}_acf_imported', true);

      // 管理画面に通知（開発環境のみ）
    if ( defined('WP_DEBUG') && WP_DEBUG ) {
        add_action('admin_notices', function () use ( $imported_count ) {
            echo '<div class="notice notice-success is-dismissible">';
            echo '<p>' . sprintf(__('%d個のACFフィールドグループをインポートしました。', '{{TEXT_DOMAIN}}'), $imported_count) . '</p>';
            echo '</div>';
        });
    }
  }
}

// init時に実行（管理画面のみ）
if ( is_admin() ) {
    add_action('init', '{{THEME_PREFIX}}_acf_auto_import_field_groups', 999);
}

/**
 * ACFインポートフラグをリセット（開発用）
 *
 * クエリパラメータ ?reset_acf_import=1 でフラグをリセット
 * Nonce付きURLを生成: wp_nonce_url(admin_url('admin.php?reset_acf_import=1'), 'reset_acf_import_action', 'reset_nonce')
 */
function {{THEME_PREFIX}}_reset_acf_import_flag() {
  if ( isset($_GET['reset_acf_import']) && $_GET['reset_acf_import'] === '1' ) {
      // Nonce verification
      check_admin_referer('reset_acf_import_action', 'reset_nonce');

      // Capability check
    if ( ! current_user_can('manage_options') ) {
        wp_die('権限がありません');
    }

      delete_option('{{THEME_PREFIX}}_acf_imported');
      wp_redirect(remove_query_arg(array('reset_acf_import', 'reset_nonce', '_wpnonce')));
      exit;
  }
}
add_action('admin_init', '{{THEME_PREFIX}}_reset_acf_import_flag');
