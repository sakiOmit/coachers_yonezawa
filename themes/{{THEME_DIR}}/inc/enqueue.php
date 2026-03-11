<?php

/**
 * アセットの読み込み
 *
 * CSS/JSのエンキュー処理
 */

if ( ! defined('ABSPATH') ) {
    exit;
}

/**
 * ページ設定の一元管理
 * ページグループとその機能を定義
 *
 * プロジェクトに応じてここを編集してください
 *
 * @return array ページ設定配列
 */
function {{THEME_PREFIX}}_get_page_config() {
    return array(
        'features' => array(
            // JSを持つページ（ページ別JSが必要な場合に追加）
            'has_js' => array(),
            // GSAPを使用するページ
            'uses_gsap' => array(),
            // Splideを使用するページ
            'uses_splide' => array(),
        ),
    );
}

/**
 * 現在のページスラッグを取得
 *
 * @param bool $is_dev 開発環境かどうか（404ページのスラッグが異なるため）
 * @return string ページスラッグ
 */
function {{THEME_PREFIX}}_get_current_page_slug( $is_dev = false ) {
    $page_slug = '';

    if ( is_front_page() ) {
        $page_slug = 'top';
    } elseif ( is_404() ) {
        $page_slug = $is_dev ? 'notfound' : '404';
    } elseif ( is_single() ) {
        $page_slug = 'single';
    } elseif ( is_page() ) {
        global $post;
        $page_slug = $post ? $post->post_name : '';

        // お問い合わせ完了ページの統一（complete → thanks）
        if ( $page_slug === 'complete' ) {
            $page_slug = 'thanks';
        }
    } else {
        // アーカイブページやカスタムテンプレートの場合、URLパスから判定
        $current_url = trim(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH), '/');
        $path_parts = explode('/', $current_url);
        if ( ! empty($path_parts[0]) ) {
            $page_slug = $path_parts[0];
        }
    }

    return $page_slug;
}

/**
 * SCSSファイルパスを取得（開発環境用）
 *
 * @param string $page_slug ページスラッグ
 * @return string SCSSファイルパス
 */
function {{THEME_PREFIX}}_get_scss_file_path( $page_slug ) {
    // 404/notfound の正規化
    if ( $page_slug === 'notfound' ) {
        $page_slug = '404';
    }

    // cases/archive, column/single 等はファイル名がディレクトリ部分に含まれる
    if ( str_contains( $page_slug, '/' ) ) {
        return 'src/css/pages/' . $page_slug . '.scss';
    }

    return 'src/css/pages/' . $page_slug . '/style.scss';
}

/**
 * JSファイルパスを取得（開発環境用）
 *
 * @param string $page_slug ページスラッグ
 * @return string JSファイルパス
 */
function {{THEME_PREFIX}}_get_js_file_path( $page_slug ) {
    return 'src/js/pages/' . $page_slug . '/index.js';
}

/**
 * ビルド済みCSSファイルパスを取得（本番環境用）
 *
 * @param string $page_slug ページスラッグ
 * @return string CSSファイルパス
 */
function {{THEME_PREFIX}}_get_built_css_file_path( $page_slug ) {
    if ( $page_slug === 'notfound' ) {
        $page_slug = '404';
    }

    // cases/archive → css/cases/archive.css
    if ( str_contains( $page_slug, '/' ) ) {
        return 'css/' . $page_slug . '.css';
    }

    return 'css/' . $page_slug . '/style.css';
}

/**
 * ビルド済みJSファイルパスを取得（本番環境用）
 *
 * @param string $page_slug ページスラッグ
 * @return string JSファイルパス
 */
function {{THEME_PREFIX}}_get_built_js_file_path( $page_slug ) {
    return 'js/' . $page_slug . '/index.js';
}

/**
 * Viteでビルドされたアセットを読み込む
 */
function {{THEME_PREFIX}}_enqueue_assets() {
    $theme_version = wp_get_theme()->get('Version');
    $assets_dir    = get_template_directory_uri() . '/assets';

    // 開発環境の判定
    $vite_port       = getenv('VITE_PORT') ?: '3000';
    $vite_dev_server = 'http://localhost:' . $vite_port;
    $is_vite_dev     = defined('VITE_DEV_MODE') && VITE_DEV_MODE === true;

    if ( $is_vite_dev ) {
        // 開発環境: Vite開発サーバーから読み込み（HMR有効）
        wp_enqueue_script(
            'vite-client',
            $vite_dev_server . '/@vite/client',
            array(),
            null,
            false
        );

        // 共通SCSS（HMR有効）
        wp_enqueue_style(
            '{{TEXT_DOMAIN}}-common-dev',
            $vite_dev_server . '/src/css/common.scss',
            array(),
            null
        );

        // 共通JS（HMR有効）
        wp_enqueue_script(
            '{{TEXT_DOMAIN}}-common',
            $vite_dev_server . '/src/js/main.js',
            array(),
            null,
            true
        );

        // ページ別SCSS/JSの読み込み（開発環境）
        {{THEME_PREFIX}}_enqueue_page_assets_dev($vite_dev_server);
    } else {
        // 本番環境: ビルド済みアセットを読み込み

        // 共通CSS
        wp_enqueue_style(
            '{{TEXT_DOMAIN}}-common',
            $assets_dir . '/css/style/style.css',
            array(),
            $theme_version,
            'all'
        );

        // ベンダーJS
        $page_slug   = {{THEME_PREFIX}}_get_current_page_slug(false);
        $page_config = {{THEME_PREFIX}}_get_page_config();
        $gsap_pages  = $page_config['features']['uses_gsap'];

        // GSAPベンダー（条件付き読み込み）
        if ( in_array($page_slug, $gsap_pages) && file_exists(get_template_directory() . '/assets/js/vendor-gsap.js') ) {
            wp_enqueue_script(
                '{{TEXT_DOMAIN}}-vendor-gsap',
                $assets_dir . '/js/vendor-gsap.js',
                array(),
                $theme_version,
                true
            );
        }

        // Splideベンダー（条件付き読み込み）
        $splide_pages = $page_config['features']['uses_splide'];
        if ( in_array($page_slug, $splide_pages) && file_exists(get_template_directory() . '/assets/js/vendor-splide.js') ) {
            wp_enqueue_script(
                '{{TEXT_DOMAIN}}-vendor-splide',
                $assets_dir . '/js/vendor-splide.js',
                array(),
                $theme_version,
                true
            );
        }

        // その他のベンダー
        if ( file_exists(get_template_directory() . '/assets/js/vendor.js') ) {
            wp_enqueue_script(
                '{{TEXT_DOMAIN}}-vendor',
                $assets_dir . '/js/vendor.js',
                array(),
                $theme_version,
                true
            );
        }

        // 共通JS
        $common_dependencies = array();
        if ( in_array($page_slug, $gsap_pages) ) {
            $common_dependencies[] = '{{TEXT_DOMAIN}}-vendor-gsap';
        }

        wp_enqueue_script(
            '{{TEXT_DOMAIN}}-common',
            $assets_dir . '/js/main.js',
            $common_dependencies,
            $theme_version,
            true
        );

        // ページ別CSS/JSの読み込み
        {{THEME_PREFIX}}_enqueue_page_assets($assets_dir, $theme_version);
    }

    // WordPress標準のjQueryを使用しない
    wp_deregister_script('jquery');
}
add_action('wp_enqueue_scripts', '{{THEME_PREFIX}}_enqueue_assets');

/**
 * ページ別のCSS/JSを読み込む（開発環境）
 */
function {{THEME_PREFIX}}_enqueue_page_assets_dev( $vite_dev_server ) {
    $page_slug     = {{THEME_PREFIX}}_get_current_page_slug(true);
    $page_config   = {{THEME_PREFIX}}_get_page_config();
    $pages_with_js = $page_config['features']['has_js'];

    if ( $page_slug ) {
        // ページ別SCSS（HMR有効）
        $scss_file = {{THEME_PREFIX}}_get_scss_file_path($page_slug);
        wp_enqueue_style(
            '{{TEXT_DOMAIN}}-page-' . $page_slug . '-dev',
            $vite_dev_server . '/' . $scss_file,
            array( '{{TEXT_DOMAIN}}-common-dev' ),
            null
        );

        // ページ別JS（HMR有効）
        if ( in_array($page_slug, $pages_with_js) ) {
            $js_file = {{THEME_PREFIX}}_get_js_file_path($page_slug);
            wp_enqueue_script(
                '{{TEXT_DOMAIN}}-page-' . $page_slug . '-dev',
                $vite_dev_server . '/' . $js_file,
                array( '{{TEXT_DOMAIN}}-common' ),
                null,
                true
            );
        }
    }
}

/**
 * ページ別のCSS/JSを読み込む（本番環境）
 */
function {{THEME_PREFIX}}_enqueue_page_assets( $assets_dir, $theme_version ) {
    $page_slug     = {{THEME_PREFIX}}_get_current_page_slug(false);
    $page_config   = {{THEME_PREFIX}}_get_page_config();
    $pages_with_js = $page_config['features']['has_js'];

    if ( $page_slug ) {
        // ページ別CSS
        $css_file = {{THEME_PREFIX}}_get_built_css_file_path($page_slug);
        $css_path = get_template_directory() . '/assets/' . $css_file;
        if ( file_exists($css_path) ) {
            wp_enqueue_style(
                '{{TEXT_DOMAIN}}-page-' . $page_slug,
                $assets_dir . '/' . $css_file,
                array( '{{TEXT_DOMAIN}}-common' ),
                $theme_version
            );
        }

        // ページ別JS
        if ( in_array($page_slug, $pages_with_js) ) {
            $js_file = {{THEME_PREFIX}}_get_built_js_file_path($page_slug);
            $js_path = get_template_directory() . '/assets/' . $js_file;
            if ( file_exists($js_path) ) {
                $dependencies = array( '{{TEXT_DOMAIN}}-common' );
                $gsap_pages   = $page_config['features']['uses_gsap'];
                $splide_pages = $page_config['features']['uses_splide'];

                if ( in_array($page_slug, $gsap_pages) ) {
                    $dependencies[] = '{{TEXT_DOMAIN}}-vendor-gsap';
                }

                if ( in_array($page_slug, $splide_pages) ) {
                    $dependencies[] = '{{TEXT_DOMAIN}}-vendor-splide';
                }

                wp_enqueue_script(
                    '{{TEXT_DOMAIN}}-page-' . $page_slug,
                    $assets_dir . '/' . $js_file,
                    $dependencies,
                    $theme_version,
                    true
                );
            }
        }
    }
}

/**
 * scriptタグにtype="module"を追加
 */
function {{THEME_PREFIX}}_add_type_module( $tag, $handle ) {
    $module_handles = array(
        'vite-client',
        '{{TEXT_DOMAIN}}-main',
        '{{TEXT_DOMAIN}}-common',
        '{{TEXT_DOMAIN}}-vendor',
        '{{TEXT_DOMAIN}}-vendor-gsap',
        '{{TEXT_DOMAIN}}-vendor-splide'
    );

    $is_module = in_array($handle, $module_handles) ||
        strpos($handle, '{{TEXT_DOMAIN}}-page-') === 0;

    if ( ! $is_module ) {
        return $tag;
    }

    $tag = preg_replace('/\stype=["\']text\/javascript["\']/i', '', $tag);
    $tag = str_replace('<script ', '<script type="module" ', $tag);

    return $tag;
}
add_filter('script_loader_tag', '{{THEME_PREFIX}}_add_type_module', 10, 3);

/**
 * WordPress標準のブロックライブラリCSSを無効化
 */
function {{THEME_PREFIX}}_remove_block_library_css() {
    if ( ! is_singular('post') && ! is_archive() ) {
        wp_dequeue_style('wp-block-library');
        wp_dequeue_style('wp-block-library-theme');
        wp_dequeue_style('global-styles');
        wp_dequeue_style('classic-theme-styles');
    }
}
add_action('wp_enqueue_scripts', '{{THEME_PREFIX}}_remove_block_library_css', 100);
