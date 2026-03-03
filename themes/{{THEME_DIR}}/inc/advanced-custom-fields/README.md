# ACF フィールド管理

このプロジェクトでは、Advanced Custom Fields (ACF) を **PHP管理** で統一します。

## 基本方針

### PHP管理（標準）

- **場所**: `themes/{{THEME_DIR}}/inc/advanced-custom-fields/groups/`
- **メリット**:
  - Gitで完全にバージョン管理
  - コードレビューが容易
  - 複数環境での同期が確実
  - プログラム的な制御が可能
  - 管理画面での誤操作を防止

### JSON管理（移行期のみ）

- **場所**: `themes/{{THEME_DIR}}/acf-json/`
- **用途**: SCFからの移行時の一時的な保存先
- **最終的には**: PHP管理に移行する

## ディレクトリ構成

```
advanced-custom-fields/
├── README.md           # このファイル
├── loader.php          # フィールドグループ自動読み込み
└── groups/
    ├── config.php      # 読み込み順序の定義
    ├── options/        # オプションページ用（会社情報など）
    ├── post-types/     # カスタム投稿タイプ用
    ├── pages/          # 固定ページ用
    └── common/         # 共通フィールド部品
```

## 新しいフィールドグループの追加方法

### 1. 適切なディレクトリにファイルを作成

```bash
# オプションページ用
touch groups/options/site-settings.php

# 投稿タイプ用
touch groups/post-types/news.php

# 固定ページ用
touch groups/pages/top-page.php
```

### 2. フィールドグループを定義

```php
<?php
/**
 * ACF フィールドグループ: トップページ設定
 */

if (!defined('ABSPATH')) {
    exit;
}

return [
    'key'    => 'group_top_page_settings',
    'title'  => 'トップページ設定',
    'fields' => [
        [
            'key'   => 'field_top_hero_title',
            'label' => 'ヒーローセクション タイトル',
            'name'  => 'top_hero_title',
            'type'  => 'text',
        ],
        [
            'key'   => 'field_top_hero_image',
            'label' => 'ヒーローセクション 画像',
            'name'  => 'top_hero_image',
            'type'  => 'image',
            'return_format' => 'id',
        ],
    ],
    'location' => [
        [
            [
                'param'    => 'page_template',
                'operator' => '==',
                'value'    => 'pages/page-top.php',
            ]
        ]
    ],
];
```

### 3. config.php に追加

```php
return [
    'options/company-settings.php',
    'pages/top-page.php',  // ← 追加
];
```

### 4. 保存して確認

ファイルを保存すると、自動的にACFに登録されます。

## 命名規則

### キーの命名

すべての `key` は**グローバルでユニーク**である必要があります:

```
group_{カテゴリ}_{名前}           # グループキー
field_{カテゴリ}_{フィールド名}   # フィールドキー
```

**例**:
- `group_top_page_settings` → `field_top_hero_title`
- `group_news_post` → `field_news_date`, `field_news_category`
- `group_company_info` → `field_company_name`, `field_company_address`

### ファイル名

- kebab-case を使用
- 内容が分かりやすい名前に
- 例: `top-page-settings.php`, `company-info.php`

## よく使うフィールドタイプ

```php
// テキスト
[
    'type' => 'text',
]

// テキストエリア
[
    'type' => 'textarea',
    'rows' => 4,
]

// WYSIWYGエディタ
[
    'type' => 'wysiwyg',
    'media_upload' => 1,
]

// 画像
[
    'type' => 'image',
    'return_format' => 'id',  // IDで返す（推奨）
]

// 真偽値
[
    'type' => 'true_false',
    'ui' => 1,
]

// セレクト
[
    'type' => 'select',
    'choices' => [
        'option1' => 'オプション1',
        'option2' => 'オプション2',
    ],
]

// リピーター（Pro版のみ）
[
    'type' => 'repeater',
    'sub_fields' => [
        // サブフィールド定義
    ],
]
```

## location の設定例

```php
// 固定ページテンプレート
'location' => [
    [
        [
            'param'    => 'page_template',
            'operator' => '==',
            'value'    => 'pages/page-top.php',
        ]
    ]
],

// 投稿タイプ
'location' => [
    [
        [
            'param'    => 'post_type',
            'operator' => '==',
            'value'    => 'news',
        ]
    ]
],

// オプションページ
'location' => [
    [
        [
            'param'    => 'options_page',
            'operator' => '==',
            'value'    => 'site-settings',
        ]
    ]
],
```

## 共通フィールドの再利用

複数のフィールドグループで同じフィールドを使う場合、`common/` に切り出して再利用できます。

### 共通フィールドの作成

```php
// groups/common/link-field.php
<?php

if (!defined('ABSPATH')) {
    exit;
}

return [
    'key'         => 'field_common_link_url',
    'label'       => 'リンクURL',
    'name'        => 'link_url',
    'type'        => 'url',
    'placeholder' => 'https://example.com',
];
```

### 共通フィールドの使用

```php
// groups/pages/example.php
return [
    'key'    => 'group_example',
    'title'  => 'サンプル',
    'fields' => [
        include __DIR__ . '/../common/link-field.php',

        [
            'key'   => 'field_example_text',
            'label' => 'テキスト',
            'name'  => 'example_text',
            'type'  => 'text',
        ],
    ],
];
```

## トラブルシューティング

### フィールドが表示されない

1. ACFプラグインが有効化されているか確認
2. `config.php` にファイルが登録されているか確認
3. PHP構文エラーがないか確認: `php -l groups/your-file.php`
4. キーの重複がないか確認

### キーの重複エラー

- すべての `key` はグローバルでユニークである必要があります
- プレフィックスを付けて重複を避けましょう

### フィールドが保存されない

- `location` の設定が正しいか確認
- 条件が正しくマッチしているか確認

## JSON管理からの移行方法

1. WordPress管理画面で既存のフィールドグループを確認
2. JSONファイル (`acf-json/*.json`) を参照
3. PHPファイルに変換して `groups/` に配置
4. `config.php` に追加
5. 動作確認後、JSONファイルを削除

## 参考リンク

- [ACF公式ドキュメント](https://www.advancedcustomfields.com/resources/)
- [PHPでの登録](https://www.advancedcustomfields.com/resources/register-fields-via-php/)
- [フィールドタイプ一覧](https://www.advancedcustomfields.com/resources/#field-types)
