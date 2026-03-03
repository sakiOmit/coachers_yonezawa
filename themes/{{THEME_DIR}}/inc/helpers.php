<?php
/**
 * Helper Functions
 *
 * ACFヘルパー関数（フォールバック付き）
 * サイト共通情報取得関数
 *
 * @package Theme_Template
 */

if ( ! defined('ABSPATH') ) {
    exit;
}

/**
 * ACFフィールド取得（フォールバック付き）
 *
 * ACFフィールドが空の場合にデフォルト値を返します。
 * ハードコーディングからACF化への移行時に、既存の値をフォールバックとして活用できます。
 *
 * @param string $field_name ACFフィールド名
 * @param mixed $default デフォルト値
 * @param int|null $post_id 投稿ID（nullの場合は現在の投稿）
 * @return mixed ACFフィールドの値、または空の場合はデフォルト値
 *
 * @example
 * ```php
 * $title = get_acf_or_default('hero_title', 'ようこそ');
 * $description = get_acf_or_default('hero_description', 'デフォルトの説明文', get_the_ID());
 * ```
 */
function get_acf_or_default( $field_name, $default = '', $post_id = null ) {
    // ACFが有効でない場合は即座にデフォルト値を返す
  if ( ! function_exists('get_field') ) {
      return $default;
  }

    $value = get_field($field_name, $post_id);

    // 値が存在し、空でない場合は取得した値を返す
    return ! empty($value) ? $value : $default;
}

/**
 * ACF画像フィールド取得（フォールバック付き）
 *
 * ACF画像フィールドを取得し、空の場合はデフォルト画像URLを返します。
 * 戻り値は常に配列形式（url, alt）で統一されます。
 *
 * @param string $field_name ACFフィールド名
 * @param string $default_url デフォルト画像URL（空の場合はプレースホルダー画像）
 * @param string $size 画像サイズ（'thumbnail', 'medium', 'large', 'full'）
 * @param int|null $post_id 投稿ID（nullの場合は現在の投稿）
 * @return array ['url' => string, 'alt' => string, 'width' => int, 'height' => int]
 *
 * @example
 * ```php
 * $hero_image = get_acf_image_or_default(
 *     'hero_image',
 *     get_template_directory_uri() . '/assets/images/common/hero.webp'
 * );
 * echo '<img src="' . esc_url($hero_image['url']) . '" alt="' . esc_attr($hero_image['alt']) . '">';
 * ```
 */
function get_acf_image_or_default( $field_name, $default_url = '', $size = 'full', $post_id = null ) {
    // ACFが有効でない場合はデフォルト画像を返す
  if ( ! function_exists('get_field') ) {
      return [
          'url' => $default_url,
          'alt' => '',
          'width' => 0,
          'height' => 0,
      ];
  }

    $image = get_field($field_name, $post_id);

    // 画像が存在する場合
  if ( $image ) {
      // 配列形式の場合（Return Format: Array）
    if ( is_array($image) ) {
        return [
            'url' => $image['url'] ?? '',
            'alt' => $image['alt'] ?? '',
            'width' => $image['width'] ?? 0,
            'height' => $image['height'] ?? 0,
        ];
    }

      // URL文字列の場合（Return Format: URL）
    if ( is_string($image) ) {
        return [
            'url' => $image,
            'alt' => '',
            'width' => 0,
            'height' => 0,
        ];
    }

      // 画像IDの場合（Return Format: ID）
    if ( is_numeric($image) ) {
        $image_data = wp_get_attachment_image_src($image, $size);
        $image_alt  = get_post_meta($image, '_wp_attachment_image_alt', true);

        return [
            'url' => $image_data[0] ?? '',
            'alt' => $image_alt ?? '',
            'width' => $image_data[1] ?? 0,
            'height' => $image_data[2] ?? 0,
        ];
    }
  }

    // デフォルト画像を返す
    return [
        'url' => $default_url,
        'alt' => '',
        'width' => 0,
        'height' => 0,
    ];
}

/**
 * ACFリンクフィールド取得（フォールバック付き）
 *
 * ACFリンクフィールドを取得し、空の場合はデフォルト値を返します。
 *
 * @param string $field_name ACFフィールド名
 * @param array $default デフォルトリンク ['url' => '', 'title' => '', 'target' => '']
 * @param int|null $post_id 投稿ID
 * @return array ['url' => string, 'title' => string, 'target' => string]
 *
 * @example
 * ```php
 * $button = get_acf_link_or_default('cta_button', [
 *     'url' => '/contact',
 *     'title' => 'お問い合わせ',
 *     'target' => '',
 * ]);
 * echo '<a href="' . esc_url($button['url']) . '" target="' . esc_attr($button['target']) . '">';
 * echo esc_html($button['title']) . '</a>';
 * ```
 */
function get_acf_link_or_default( $field_name, $default = [], $post_id = null ) {
    // ACFが有効でない場合はデフォルト値を返す
  if ( ! function_exists('get_field') ) {
      return array_merge([
          'url' => '',
          'title' => '',
          'target' => '',
      ], $default);
  }

    $link = get_field($field_name, $post_id);

    // リンクフィールドが存在する場合
  if ( $link && is_array($link) ) {
      return [
          'url' => $link['url'] ?? '',
          'title' => $link['title'] ?? '',
          'target' => $link['target'] ?? '',
      ];
  }

    // デフォルト値を返す
    return array_merge([
        'url' => '',
        'title' => '',
        'target' => '',
    ], $default);
}

/**
 * ACF選択肢フィールド取得（フォールバック付き）
 *
 * Select, Radio Button, Checkbox などの選択肢フィールドを取得します。
 *
 * @param string $field_name ACFフィールド名
 * @param mixed $default デフォルト値
 * @param int|null $post_id 投稿ID
 * @return mixed 選択された値、または空の場合はデフォルト値
 *
 * @example
 * ```php
 * $color = get_acf_choice_or_default('theme_color', 'blue');
 * ```
 */
function get_acf_choice_or_default( $field_name, $default = '', $post_id = null ) {
    // get_acf_or_default と同じ処理
    return get_acf_or_default($field_name, $default, $post_id);
}

/**
 * ACF真偽値フィールド取得（フォールバック付き）
 *
 * True/False フィールドを取得します。
 *
 * @param string $field_name ACFフィールド名
 * @param bool $default デフォルト値（true/false）
 * @param int|null $post_id 投稿ID
 * @return bool 真偽値
 *
 * @example
 * ```php
 * $is_featured = get_acf_bool_or_default('is_featured', false);
 * if ($is_featured) {
 *     echo '<span class="badge">注目</span>';
 * }
 * ```
 */
function get_acf_bool_or_default( $field_name, $default = false, $post_id = null ) {
    // ACFが有効でない場合はデフォルト値を返す
  if ( ! function_exists('get_field') ) {
      return $default;
  }

    $value = get_field($field_name, $post_id);

    // 値が明示的に設定されている場合
  if ( $value !== null ) {
      return (bool) $value;
  }

    return $default;
}

/**
 * テンプレートディレクトリのパスを取得（末尾スラッシュなし）
 *
 * get_template_directory_uri() のショートハンド
 *
 * @return string テンプレートディレクトリのURL
 *
 * @example
 * ```php
 * $logo = template_uri() . '/assets/images/common/logo.webp';
 * ```
 */
function template_uri() {
    return get_template_directory_uri();
}

/**
 * 画像URLを生成
 *
 * テーマ内の画像パスから完全なURLを生成します。
 *
 * @param string $path テーマディレクトリからの相対パス
 * @return string 完全な画像URL
 *
 * @example
 * ```php
 * $hero_bg = get_theme_image_url('assets/images/common/hero.webp');
 * // → http://example.com/wp-content/themes/{{THEME_DIR}}/assets/images/common/hero.webp
 * ```
 */
function get_theme_image_url( $path ) {
    return get_template_directory_uri() . '/' . ltrim($path, '/');
}

/**
 * サイト共通情報を取得
 *
 * ACFオプションページからサイトの基本情報を取得します。
 * ACFにデータがない場合はデフォルト値を返します。
 *
 * @param string $key 情報のキー
 * @return string サイト情報（エスケープ済み）
 *
 * @example
 * ```php
 * $tel = get_site_info('tel');
 * $address = get_site_info('address');
 * ```
 */
function get_site_info( $key ) {
    // デフォルト値（プロジェクトに応じてカスタマイズ）
    $defaults = array(
        'tel'         => '000-0000-0000',
        'fax'         => '000-0000-0000',
        'postal_code' => '000-0000',
        'address'     => '〒000-0000 住所を設定してください',
        'email'       => 'info@example.com',
    );

    $default = isset($defaults[ $key ]) ? $defaults[ $key ] : '';

    if ( ! function_exists('get_field') ) {
        return $default;
    }

    $field_name = 'site_' . $key;
    $info       = get_field($field_name, 'option');

    // 値が空の場合はデフォルト値を使用
    if ( empty($info) ) {
        $info = $default;
    }

    // データタイプに応じて適切なエスケープ関数を使用
    if ( $key === 'tel' || $key === 'fax' || $key === 'postal_code' ) {
        return esc_attr($info);
    }
    if ( $key === 'email' ) {
        return sanitize_email($info);
    }

    return esc_html($info);
}
