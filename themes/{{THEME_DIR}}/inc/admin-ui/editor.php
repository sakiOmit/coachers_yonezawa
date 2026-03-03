<?php

if ( ! defined('ABSPATH') ) {
    exit;
}

/**
 * ACFメタボックスを上に表示
 *
 * ACFフィールドグループを 'high' にすることで上に表示します。
 */
add_filter('acf/input/meta_box_priority', function ( $priority, $field_group ) {
    // すべてのACFフィールドグループを高優先度に設定
    return 'high';
}, 10, 2);
