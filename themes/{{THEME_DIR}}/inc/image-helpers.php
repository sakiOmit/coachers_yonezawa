<?php
/**
 * 画像ヘルパー関数
 * WebP専用・Retina対応・レスポンシブ画像出力
 *
 * 出力形式:
 *   - SVG: <img> のみ
 *   - SP分岐あり: <picture> + <source>(1x,2x,3x) + <img>(1x,2x)
 *   - SP分岐なし: <img>(1x,2x)
 *
 * @package {{PACKAGE_NAME}}
 */

if ( ! defined('ABSPATH') ) {
	exit;
}

/**
 * 画像メタデータを取得
 * 静的変数でキャッシュするため、リクエスト内では1度のみファイル読み込み
 * opcache により実質コストゼロ
 *
 * @return array 画像メタデータ配列
 */
function get_images_meta() {
	static $meta = null;

	if ( $meta === null ) {
		$file = get_template_directory() . '/inc/data/images-meta.php';

		if ( file_exists($file) ) {
			$meta = require $file;
		} else {
			$meta = [];

			if ( defined('WP_DEBUG') && WP_DEBUG ) {
				error_log('Warning: images-meta.php not found. Run "npm run image-opt" to create it.');
			}
		}
	}

	return $meta;
}

/**
 * 画像パスからメタデータを取得
 *
 * @param string $src 画像パス（絶対URLまたは相対パス）
 * @return array|null ['width' => int, 'height' => int] or null
 */
function get_image_size_from_meta( $src ) {
	$meta = get_images_meta();

	$theme_url     = get_template_directory_uri();
	$relative_path = str_replace($theme_url . '/assets/images/', '', $src);

	// 拡張子とクエリパラメータを除去
	$key = preg_replace('/\.(jpe?g|png|webp|svg)(\?.*)?$/i', '', $relative_path);

	return $meta[ $key ] ?? null;
}

/**
 * レスポンシブ画像を出力（WebP専用）
 *
 * @param array $args {
 *   画像出力オプション
 *
 *   @type string $acf_field     ACFグループフィールド名（優先）
 *                               ['pc' => image_array, 'sp' => image_array]形式を想定
 *   @type string $src           画像パス（フォールバック）
 *                               例: get_template_directory_uri() . '/assets/images/hero.webp'
 *   @type bool   $sp            SP画像を使用するか (デフォルト: true)
 *   @type int    $width         width属性（自動取得、指定で上書き）
 *   @type int    $height        height属性（自動取得、指定で上書き）
 *   @type string $alt           alt属性
 *   @type string $class         class属性（img要素に適用）
 *   @type string $wrapper_class class属性（picture要素に適用）
 *   @type string $loading       loading属性 (デフォルト: 'lazy')
 *   @type int    $breakpoint    SP/PC切り替えブレークポイント (デフォルト: 767)
 *   その他のdata-*属性なども自由に追加可能
 * }
 *
 * @example
 * // 静的画像
 * render_responsive_image([
 *   'src'   => get_template_directory_uri() . '/assets/images/hero.webp',
 *   'alt'   => 'ヒーロー画像',
 *   'class' => 'p-hero__image',
 * ]);
 *
 * @example
 * // ACF画像（PC/SP別画像）
 * render_responsive_image([
 *   'acf_field' => 'hero_image',
 *   'alt'       => 'ヒーロー画像',
 * ]);
 *
 * @example
 * // SP分岐なし
 * render_responsive_image([
 *   'src' => get_template_directory_uri() . '/assets/images/logo.webp',
 *   'sp'  => false,
 *   'alt' => 'ロゴ',
 * ]);
 */
function render_responsive_image( $args = [] ) {
	$defaults = [
		'acf_field' => '',
		'src'       => '',
		'sp'        => true,
		'alt'       => '',
		'width'     => null,
		'height'    => null,
		'loading'   => 'lazy',
		'breakpoint' => 767,
	];

	$args = wp_parse_args($args, $defaults);

	// --- 1. 画像ソース決定 ---

	$pc_src = '';
	$sp_src = null;
	$alt    = $args['alt'];
	$width  = $args['width'];
	$height = $args['height'];

	if ( ! empty($args['acf_field']) && function_exists('get_field') ) {
		$acf_group = get_field($args['acf_field']) ?: null;
		if ( $acf_group && is_array($acf_group) ) {
			$pc_image = $acf_group['pc'] ?? null;
			$sp_image = $acf_group['sp'] ?? null;

			if ( $pc_image && ! empty($pc_image['url']) ) {
				$pc_src = $pc_image['url'];
				$width  = $width ?? ( $pc_image['width'] ?? null );
				$height = $height ?? ( $pc_image['height'] ?? null );
				$alt    = ! empty($alt) ? $alt : ( $pc_image['alt'] ?? '' );

				if ( $args['sp'] && $sp_image && ! empty($sp_image['url']) ) {
					$sp_src = $sp_image['url'];
				}
			}
		}
	}

	// ACFが無い or 取得できなかった場合 → src フォールバック
	if ( empty($pc_src) ) {
		if ( empty($args['src']) ) {
			return;
		}
		$pc_src = $args['src'];
	}

	// --- 2. パス生成 ---

	$path_info = pathinfo($pc_src);
	$base_path = $path_info['dirname'] . '/' . $path_info['filename'];
	$ext       = strtolower($path_info['extension'] ?? '');
	$is_svg    = ( $ext === 'svg' );

	// PC WebP パス
	$pc_webp    = $is_svg ? null : $base_path . '.webp';
	$pc_webp_2x = $is_svg ? null : $base_path . '@2x.webp';

	// SP WebP パス（3x含む）
	$has_sp = false;
	$sp_webp    = null;
	$sp_webp_2x = null;
	$sp_webp_3x = null;

	if ( $args['sp'] && ! $is_svg ) {
		if ( $sp_src ) {
			// ACFからSP画像取得済み
			$sp_info    = pathinfo($sp_src);
			$sp_base    = $sp_info['dirname'] . '/' . $sp_info['filename'];
			$sp_webp    = $sp_base . '.webp';
			$sp_webp_2x = $sp_base . '@2x.webp';
			$sp_webp_3x = $sp_base . '@3x.webp';
			$has_sp     = true;
		} else {
			// _sp サフィックス規約
			$sp_webp    = $base_path . '_sp.webp';
			$sp_webp_2x = $base_path . '_sp@2x.webp';
			$sp_webp_3x = $base_path . '_sp@3x.webp';
			$has_sp     = true;
		}
	}

	// --- 3. width/height 自動取得（images-meta.php、opcache済み） ---

	if ( $width === null || $height === null ) {
		$meta_src = $is_svg ? $pc_src : $pc_webp;
		if ( $meta_src ) {
			$meta = get_image_size_from_meta($meta_src);
			if ( $meta ) {
				$width  = $width ?? $meta['width'];
				$height = $height ?? $meta['height'];
			}
		}
	}

	// --- 4. カスタム属性 ---

	$excluded_keys = [ 'acf_field', 'src', 'sp', 'breakpoint', 'width', 'height', 'alt', 'loading', 'class', 'wrapper_class' ];
	$custom_attrs  = array_diff_key($args, array_flip($excluded_keys));

	$attrs_html = '';
	foreach ( $custom_attrs as $key => $value ) {
		if ( $value !== '' && $value !== null ) {
			$attrs_html .= sprintf(' %s="%s"', esc_attr($key), esc_attr($value));
		}
	}

	$wrapper_class = $args['wrapper_class'] ?? '';

	// --- 5. HTML出力 ---

	if ( $is_svg ) {
		// SVG: <img> のみ
		?>
	<img
		src="<?php echo esc_url($pc_src); ?>"
		<?php if ( $width ) : ?>width="<?php echo esc_attr($width); ?>"<?php endif; ?>
		<?php if ( $height ) : ?>height="<?php echo esc_attr($height); ?>"<?php endif; ?>
		alt="<?php echo esc_attr($alt); ?>"
		loading="<?php echo esc_attr($args['loading']); ?>"
		<?php if ( isset($args['class']) ) : ?>class="<?php echo esc_attr($args['class']); ?>"<?php endif; ?>
		<?php echo $attrs_html; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
	/>
		<?php
	} elseif ( $has_sp ) {
		// SP分岐あり: <picture> + <source>(1x,2x,3x) + <img>(1x,2x)
		?>
	<picture<?php if ( $wrapper_class ) : ?> class="<?php echo esc_attr($wrapper_class); ?>"<?php endif; ?><?php echo $attrs_html; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>
		<source
			media="(max-width: <?php echo esc_attr($args['breakpoint']); ?>px)"
			srcset="<?php echo esc_url($sp_webp); ?> 1x, <?php echo esc_url($sp_webp_2x); ?> 2x, <?php echo esc_url($sp_webp_3x); ?> 3x"
		/>
		<img
			src="<?php echo esc_url($pc_webp); ?>"
			srcset="<?php echo esc_url($pc_webp); ?> 1x, <?php echo esc_url($pc_webp_2x); ?> 2x"
			<?php if ( $width ) : ?>width="<?php echo esc_attr($width); ?>"<?php endif; ?>
			<?php if ( $height ) : ?>height="<?php echo esc_attr($height); ?>"<?php endif; ?>
			alt="<?php echo esc_attr($alt); ?>"
			loading="<?php echo esc_attr($args['loading']); ?>"
			<?php if ( isset($args['class']) ) : ?>class="<?php echo esc_attr($args['class']); ?>"<?php endif; ?>
		/>
	</picture>
		<?php
	} else {
		// SP分岐なし: <img>(1x,2x) のみ
		?>
	<img
		src="<?php echo esc_url($pc_webp); ?>"
		srcset="<?php echo esc_url($pc_webp); ?> 1x, <?php echo esc_url($pc_webp_2x); ?> 2x"
		<?php if ( $width ) : ?>width="<?php echo esc_attr($width); ?>"<?php endif; ?>
		<?php if ( $height ) : ?>height="<?php echo esc_attr($height); ?>"<?php endif; ?>
		alt="<?php echo esc_attr($alt); ?>"
		loading="<?php echo esc_attr($args['loading']); ?>"
		<?php if ( isset($args['class']) ) : ?>class="<?php echo esc_attr($args['class']); ?>"<?php endif; ?>
		<?php echo $attrs_html; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
	/>
		<?php
	}
}

/**
 * サイトロゴを出力
 * ホームへのリンク付きロゴ画像を出力（WebP・Retina対応）
 *
 * @param array $args {
 *   ロゴ出力オプション
 *
 *   @type string $src     ロゴ画像パス（デフォルト: '/assets/images/common/logo.webp'）
 *   @type string $alt     alt属性（デフォルト: サイト名）
 *   @type int    $width   width属性（デフォルト: 200）
 *   @type int    $height  height属性（デフォルト: 50）
 *   @type string $class   img要素のclass属性（デフォルト: 'l-header__logo-image'）
 *   @type string $link_class aタグのclass属性（デフォルト: 'l-header__logo-link'）
 *   @type string $aria_label aタグのaria-label（デフォルト: 'ホーム'）
 *   @type string $loading loading属性（デフォルト: 'eager'）
 * }
 */
function render_logo( $args = [] ) {
	$defaults = [
		'src'        => get_template_directory_uri() . '/assets/images/common/logo.webp',
		'alt'        => get_bloginfo('name'),
		'width'      => 200,
		'height'     => 50,
		'class'      => 'l-header__logo-image',
		'link_class' => 'l-header__logo-link',
		'aria_label' => 'ホーム',
		'loading'    => 'eager',
	];

	$args     = wp_parse_args($args, $defaults);
	$home_url = esc_url(home_url('/'));

	$link_class = $args['link_class'];
	$aria_label = $args['aria_label'];

	$image_args = [
		'src'     => $args['src'],
		'alt'     => $args['alt'],
		'width'   => $args['width'],
		'height'  => $args['height'],
		'class'   => $args['class'],
		'loading' => $args['loading'],
		'sp'      => false,
	];
	?>
	<a href="<?php echo $home_url; ?>" class="<?php echo esc_attr($link_class); ?>" aria-label="<?php echo esc_attr($aria_label); ?>">
		<?php render_responsive_image($image_args); ?>
	</a>
	<?php
}
