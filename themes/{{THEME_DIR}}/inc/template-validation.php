<?php
/**
 * テンプレートパーツ引数バリデーション
 *
 * 開発環境でtemplate-partsの必須引数をチェックし、
 * 不足時に警告を表示します。
 *
 * @package {{PACKAGE_NAME}}
 */

if ( ! defined('ABSPATH') ) {
    exit;
}

/**
 * template-parts引数をバリデート
 *
 * @param array  $args          get_template_part()に渡された引数
 * @param array  $required      必須引数の配列（キー名）
 * @param string $template_name テンプレート名（エラーメッセージ用）
 * @return bool バリデーション成功時 true、失敗時 false
 *
 * @example
 * // template-parts/common/page-header.php の先頭で使用
 * if (!validate_template_args($args, ['en_heading', 'breadcrumbs'], 'page-header')) {
 *     return;
 * }
 */
function validate_template_args( $args, $required, $template_name ) {
    // 本番環境ではバリデーションをスキップ（パフォーマンス優先）
  if ( ! defined('WP_DEBUG') || ! WP_DEBUG ) {
      return true;
  }

    $missing = [];

  foreach ( $required as $key ) {
    if ( ! isset($args[ $key ]) || $args[ $key ] === '' || $args[ $key ] === null ) {
        $missing[] = $key;
    }
  }

  if ( ! empty($missing) ) {
      $message = sprintf(
          'Template "%s" missing required arguments: %s',
          $template_name,
          implode(', ', $missing)
      );

      // エラーログに出力
      error_log('[Template Validation] ' . $message);

      // 画面にも警告表示（WP_DEBUG_DISPLAYが有効な場合）
    if ( defined('WP_DEBUG_DISPLAY') && WP_DEBUG_DISPLAY ) {
      echo '<!-- [Template Warning] ' . esc_html($message) . ' -->';
    }

      return false;
  }

    return true;
}

/**
 * 引数のデフォルト値をマージ
 *
 * @param array $args     渡された引数
 * @param array $defaults デフォルト値
 * @return array マージされた引数
 *
 * @example
 * $args = merge_template_defaults($args, [
 *     'class' => '',
 *     'loading' => 'lazy',
 *     'alt' => '',
 * ]);
 */
function merge_template_defaults( $args, $defaults ) {
    return wp_parse_args($args, $defaults);
}

/**
 * 引数から特定のキーを抽出
 *
 * @param array $args 元の引数
 * @param array $keys 抽出するキー
 * @return array 抽出された引数
 */
function extract_template_args( $args, $keys ) {
    return array_intersect_key($args, array_flip($keys));
}

/**
 * HTML属性文字列を生成
 *
 * @param array $attrs 属性の連想配列
 * @return string HTML属性文字列
 *
 * @example
 * echo build_html_attrs(['class' => 'my-class', 'data-id' => '123']);
 * // 出力: class="my-class" data-id="123"
 */
function build_html_attrs( $attrs ) {
    $html = '';
  foreach ( $attrs as $key => $value ) {
    if ( $value !== null && $value !== false && $value !== '' ) {
        $html .= sprintf(' %s="%s"', esc_attr($key), esc_attr($value));
    }
  }
    return trim($html);
}
