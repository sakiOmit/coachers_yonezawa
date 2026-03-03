<?php
/**
 * ACF 共通フィールド: リンクボタン
 *
 * 複数のフィールドグループで再利用できる共通フィールド
 *
 * @package {{PACKAGE_NAME}}
 */

if ( ! defined('ABSPATH') ) {
    exit;
}

return [
    'key'          => 'field_common_link_button',
    'label'        => 'リンクボタン',
    'name'         => 'link_button',
    'type'         => 'group',
    'instructions' => 'ボタンリンクの設定',
    'sub_fields'   => [
        [
            'key'          => 'field_common_link_button_text',
            'label'        => 'ボタンテキスト',
            'name'         => 'text',
            'type'         => 'text',
            'placeholder'  => '詳しく見る',
            'default_value' => '詳しく見る',
        ],
        [
            'key'         => 'field_common_link_button_url',
            'label'       => 'リンク先URL',
            'name'        => 'url',
            'type'        => 'url',
            'placeholder' => 'https://example.com',
        ],
        [
            'key'     => 'field_common_link_button_target',
            'label'   => 'リンクの開き方',
            'name'    => 'target',
            'type'    => 'select',
            'choices' => [
                '_self'  => '同じタブで開く',
                '_blank' => '新しいタブで開く',
            ],
            'default_value' => '_self',
        ],
    ],
];
