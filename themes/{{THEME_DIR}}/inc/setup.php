<?php
/**
 * Theme Setup
 *
 * @package {{PACKAGE_NAME}}
 */

/**
 * テーマの基本セットアップ
 */
function theme_setup() {
  // タイトルタグのサポート
  add_theme_support('title-tag');

  // アイキャッチ画像のサポート
  add_theme_support('post-thumbnails');

  // HTML5マークアップのサポート
  add_theme_support('html5', array(
    'search-form',
    'comment-form',
    'comment-list',
    'gallery',
    'caption',
    'style',
    'script',
  ));

  // ナビゲーションメニューの登録
  register_nav_menus(array(
    'primary' => __('Primary Menu', 'your-theme'),
    'footer'  => __('Footer Menu', 'your-theme'),
  ));
}
add_action('after_setup_theme', 'theme_setup');

/**
 * SVGファイルのアップロードを許可
 */
function allow_svg_upload( $mimes ) {
  $mimes['svg'] = 'image/svg+xml';
  return $mimes;
}
add_filter('upload_mimes', 'allow_svg_upload');

/**
 * SVGファイルのMIMEタイプとファイル拡張子を確認
 *
 * @param array  $wp_check_filetype_and_ext ファイルタイプチェック結果.
 * @param string $file ファイルパス.
 * @param string $filename ファイル名.
 * @param array  $mimes 許可されたMIMEタイプ.
 * @return array
 */
function fix_svg_mime_type( $wp_check_filetype_and_ext, $file, $filename, $mimes ) {
  if ( ! $wp_check_filetype_and_ext['type'] ) {
    $check_filetype     = wp_check_filetype($filename, $mimes);
    $ext                = $check_filetype['ext'];
    $type               = $check_filetype['type'];
    $proper_filename    = $filename;

    if ( $type && 0 === strpos($type, 'image/') && 'svg' === $ext ) {
      $wp_check_filetype_and_ext['ext']  = $ext;
      $wp_check_filetype_and_ext['type'] = $type;
      $wp_check_filetype_and_ext['proper_filename'] = $proper_filename;
    }
  }

  return $wp_check_filetype_and_ext;
}
add_filter('wp_check_filetype_and_ext', 'fix_svg_mime_type', 10, 4);

/**
 * SVGファイルをサニタイズ（セキュリティ対策）
 *
 * @param array $file アップロードされたファイル情報.
 * @return array
 */
function sanitize_svg_upload( $file ) {
  // SVGファイル以外はスキップ
  if ( 'image/svg+xml' !== $file['type'] ) {
    return $file;
  }

  // ファイルが存在しない場合はスキップ
  if ( ! file_exists($file['tmp_name']) ) {
    return $file;
  }

  // SVGファイルの内容を取得
  $svg_content = file_get_contents($file['tmp_name']);

  // 危険なタグとイベントハンドラを削除
  $dangerous_tags = array(
    'script',
    'iframe',
    'object',
    'embed',
    'applet',
    'meta',
    'link',
    'style',
    'base',
  );

  foreach ( $dangerous_tags as $tag ) {
    $svg_content = preg_replace('/<' . $tag . '\b[^>]*>.*?<\/' . $tag . '>/is', '', $svg_content);
    $svg_content = preg_replace('/<' . $tag . '\b[^>]*\/>/is', '', $svg_content);
  }

  // JavaScriptイベントハンドラを削除
  $svg_content = preg_replace('/\s*on[a-z]+\s*=\s*["\'][^"\']*["\']/i', '', $svg_content);

  // サニタイズされた内容をファイルに書き戻し
  file_put_contents($file['tmp_name'], $svg_content);

  return $file;
}
add_filter('wp_handle_upload_prefilter', 'sanitize_svg_upload');

/**
 * SVGファイルのメディアライブラリでの表示を修正
 *
 * @param array   $response アタッチメントレスポンス.
 * @param WP_Post $attachment アタッチメント投稿オブジェクト.
 * @param array   $meta アタッチメントメタデータ.
 * @return array
 */
function fix_svg_display( $response, $attachment, $meta ) {
  if ( 'image/svg+xml' !== $response['mime'] ) {
    return $response;
  }

  $svg_path = get_attached_file($attachment->ID);

  if ( ! file_exists($svg_path) ) {
    return $response;
  }

  // SVGの実際のサイズを取得
  $svg_content = file_get_contents($svg_path);
  $width       = 104;
  $height      = 104;

  // viewBox属性からサイズを取得
  if ( preg_match('/viewBox=["\']([^"\']+)["\']/i', $svg_content, $matches) ) {
    $viewbox = preg_split('/[\s,]+/', trim($matches[1]));
    if ( count($viewbox) === 4 ) {
      $width  = intval($viewbox[2]);
      $height = intval($viewbox[3]);
    }
  }

  // width/height属性からサイズを取得（viewBoxがない場合）
  if ( 104 === $width && 104 === $height ) {
    if ( preg_match('/width=["\']([0-9.]+)["\']/', $svg_content, $w_matches) ) {
      $width = intval($w_matches[1]);
    }
    if ( preg_match('/height=["\']([0-9.]+)["\']/', $svg_content, $h_matches) ) {
      $height = intval($h_matches[1]);
    }
  }

  // プレビュー用のサイズ設定
  $response['sizes'] = array(
    'full' => array(
      'url'         => $response['url'],
      'width'       => $width,
      'height'      => $height,
      'orientation' => ( $width > $height ) ? 'landscape' : 'portrait',
    ),
  );

  // メディアライブラリのグリッド表示用
  $response['icon'] = $response['url'];

  // 画像として扱う
  $response['type']    = 'image';
  $response['subtype'] = 'svg+xml';

  return $response;
}
add_filter('wp_prepare_attachment_for_js', 'fix_svg_display', 10, 3);

/**
 * SVGファイルのサムネイル生成をスキップ
 * （SVGは拡大縮小可能なベクター画像なので、サムネイル不要）
 *
 * @param array $metadata メタデータ配列.
 * @param int   $attachment_id アタッチメントID.
 * @return array
 */
function skip_svg_thumbnail_generation( $metadata, $attachment_id ) {
  $mime = get_post_mime_type($attachment_id);

  if ( 'image/svg+xml' === $mime ) {
    $attachment = get_post($attachment_id);
    $svg_path   = get_attached_file($attachment_id);

    if ( file_exists($svg_path) ) {
      $svg_content = file_get_contents($svg_path);
      $width       = 0;
      $height      = 0;

      // viewBox属性からサイズを取得
      if ( preg_match('/viewBox=["\']([^"\']+)["\']/i', $svg_content, $matches) ) {
        $viewbox = preg_split('/[\s,]+/', trim($matches[1]));
        if ( count($viewbox) === 4 ) {
          $width  = intval($viewbox[2]);
          $height = intval($viewbox[3]);
        }
      }

      // width/height属性からサイズを取得
      if ( 0 === $width && 0 === $height ) {
        if ( preg_match('/width=["\']([0-9.]+)["\']/', $svg_content, $w_matches) ) {
          $width = intval($w_matches[1]);
        }
        if ( preg_match('/height=["\']([0-9.]+)["\']/', $svg_content, $h_matches) ) {
          $height = intval($h_matches[1]);
        }
      }

      // デフォルト値
      if ( 0 === $width || 0 === $height ) {
        $width  = 800;
        $height = 600;
      }

      $metadata = array(
        'width'  => $width,
        'height' => $height,
        'file'   => basename($svg_path),
      );
    }
  }

  return $metadata;
}
add_filter('wp_generate_attachment_metadata', 'skip_svg_thumbnail_generation', 10, 2);

/**
 * 画像プリロード（プロジェクトに応じてカスタマイズ）
 *
 * LCP最適化のため、クリティカルな画像を事前読み込みする。
 * プロジェクトごとに対象画像を指定してください。
 *
 * 例: トップページのファーストビュー画像
 * if ( is_front_page() ) {
 *   echo '<link rel="preload" as="image" href="..." fetchpriority="high">';
 * }
 */
function preload_critical_images() {
  // プロジェクトに応じて実装してください
}
add_action('wp_head', 'preload_critical_images', 1);