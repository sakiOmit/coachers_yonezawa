<?php
/**
 * カスタム投稿タイプの登録
 *
 * プロジェクトに応じてカスタマイズしてください。
 * 以下はサンプルとしてニュース投稿タイプを定義しています。
 *
 * @package {{PACKAGE_NAME}}
 */

if ( ! defined('ABSPATH') ) {
    exit;
}

/**
 * カスタム投稿タイプの登録
 */
function {{THEME_PREFIX}}_register_custom_post_types() {
    // ============================================
    // サンプル: ニュース投稿タイプ
    // 必要に応じて編集・削除してください
    // ============================================
    register_post_type('news', [
        'labels' => [
            'name'               => 'ニュース',
            'singular_name'      => 'ニュース',
            'menu_name'          => 'ニュース',
            'add_new'            => '新規追加',
            'add_new_item'       => '新しいニュースを追加',
            'edit_item'          => 'ニュースを編集',
            'new_item'           => '新しいニュース',
            'view_item'          => 'ニュースを表示',
            'search_items'       => 'ニュースを検索',
            'not_found'          => 'ニュースが見つかりませんでした',
            'not_found_in_trash' => 'ゴミ箱にニュースはありません',
            'all_items'          => 'すべてのニュース',
        ],
        'public'             => true,
        'has_archive'        => true,
        'show_in_rest'       => true,
        'menu_icon'          => 'dashicons-megaphone',
        'menu_position'      => 5,
        'supports'           => [ 'title', 'editor', 'thumbnail', 'excerpt' ],
        'rewrite'            => [
            'slug'       => 'news',
            'with_front' => false,
        ],
        'capability_type'    => 'post',
    ]);
}
add_action('init', '{{THEME_PREFIX}}_register_custom_post_types', 10);

/**
 * タクソノミーの登録
 */
function {{THEME_PREFIX}}_register_taxonomies() {
    // ============================================
    // サンプル: ニュースカテゴリー
    // 必要に応じて編集・削除してください
    // ============================================
    register_taxonomy('news_category', 'news', [
        'labels' => [
            'name'              => 'ニュースカテゴリー',
            'singular_name'     => 'ニュースカテゴリー',
            'search_items'      => 'カテゴリーを検索',
            'all_items'         => 'すべてのカテゴリー',
            'edit_item'         => 'カテゴリーを編集',
            'update_item'       => 'カテゴリーを更新',
            'add_new_item'      => '新しいカテゴリーを追加',
            'new_item_name'     => '新しいカテゴリー名',
            'menu_name'         => 'カテゴリー',
        ],
        'hierarchical'      => true,
        'show_ui'           => true,
        'show_in_rest'      => true,
        'show_admin_column' => true,
        'query_var'         => true,
        'rewrite'           => [
            'slug'       => 'news/category',
            'with_front' => false,
        ],
    ]);
}
add_action('init', '{{THEME_PREFIX}}_register_taxonomies', 5);
