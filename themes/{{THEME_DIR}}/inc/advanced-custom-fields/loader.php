<?php
/**
 * ACF フィールドグループローダー
 *
 * groups/config.php で定義されたPHPフィールドグループを読み込みます。
 * 通常のフィールドは acf-json/ で管理することを推奨します。
 *
 * @package {{PACKAGE_NAME}}
 */

if ( ! defined('ABSPATH') ) {
    exit;
}

add_action('acf/include_fields', function () {
    // ACF関数が利用可能かチェック
  if ( ! function_exists('acf_add_local_field_group') ) {
      return;
  }

    // 設定ファイルのパス
    $config_file = __DIR__ . '/groups/config.php';

  if ( ! file_exists($config_file) ) {
      return;
  }

    // 読み込むファイルのリストを取得
    $file_list = include $config_file;

  if ( ! is_array($file_list) || empty($file_list) ) {
      return;
  }

    // 設定ファイルで定義された順序で読み込み
  foreach ( $file_list as $relative_path ) {
      $file = __DIR__ . '/groups/' . $relative_path;

    if ( ! file_exists($file) ) {
        continue;
    }

      // ファイルを読み込んで配列を取得
      $group = include $file;

    if ( empty($group) || ! is_array($group) ) {
        continue;
    }

      // 単一グループの登録
    if ( isset($group['key'], $group['title'], $group['fields'], $group['location']) ) {
        acf_add_local_field_group($group);
    }
      // 複数グループの登録
    elseif ( isset($group[0]['key']) ) {
      foreach ( $group as $g ) {
        if ( isset($g['key'], $g['title'], $g['fields'], $g['location']) ) {
          acf_add_local_field_group($g);
        }
      }
    }
  }
});
