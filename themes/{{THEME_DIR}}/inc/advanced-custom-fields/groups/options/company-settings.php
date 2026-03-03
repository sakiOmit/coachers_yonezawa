<?php

/**
 * ACF オプションページ: 会社情報設定
 */

if ( ! defined('ABSPATH') ) {
    exit;
}

return array(
    'key' => 'group_company_settings',
    'title' => '会社情報設定',
    'fields' => array(
        // ========================================
        // 基本情報
        // ========================================
        array(
            'key' => 'field_footer_section',
            'label' => '基本情報',
            'name' => '',
            'type' => 'tab',
            'placement' => 'left',
            'instructions' => '本社の連絡先・住所情報',
        ),
        array(
            'key' => 'field_company_tel',
            'label' => '電話番号',
            'name' => 'company_tel',
            'type' => 'text',
            'instructions' => 'フッターに表示する電話番号を入力してください',
            'placeholder' => '000-000-0000',
            'default_value' => '000-000-0000',
        ),
        array(
            'key' => 'field_company_fax',
            'label' => 'FAX番号',
            'name' => 'company_fax',
            'type' => 'text',
            'instructions' => 'FAX番号を入力してください',
            'placeholder' => '000-000-0000',
            'default_value' => '000-000-0000',
        ),
        array(
            'key' => 'field_company_postal_code',
            'label' => '郵便番号',
            'name' => 'company_postal_code',
            'type' => 'text',
            'instructions' => '郵便番号を入力してください（ハイフンなし可）',
            'placeholder' => '000-0000',
            'default_value' => '000-0000',
        ),
        array(
            'key' => 'field_company_address',
            'label' => '所在地（フッター）',
            'name' => 'company_address',
            'type' => 'text',
            'instructions' => 'フッターに表示する所在地を入力してください',
            'placeholder' => '〒000-0000 住所を設定してください',
            'default_value' => '〒000-0000 住所を設定してください',
        ),
        array(
            'key' => 'field_company_email',
            'label' => 'メールアドレス',
            'name' => 'company_email',
            'type' => 'email',
            'instructions' => '問い合わせ先メールアドレス',
            'placeholder' => 'info@example.com',
            'default_value' => 'info@example.com',
        ),
    ),
    'location' => array(
        array(
            array(
                'param' => 'options_page',
                'operator' => '==',
                'value' => 'company-settings',
            ),
        ),
    ),
    'menu_order' => 0,
    'position' => 'normal',
    'style' => 'default',
    'label_placement' => 'top',
    'instruction_placement' => 'label',
    'active' => true,
);
