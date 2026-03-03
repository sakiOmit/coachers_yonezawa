# YAML + PHP インポート機能テンプレート

このディレクトリには、WordPress カスタム投稿タイプ用のインポート機能を自動生成するためのテンプレートが含まれています。

## テンプレートファイル

### 1. `importer-template.php`
PHPインポート機能のテンプレート。以下のプレースホルダーを含みます:

- `{{POST_TYPE}}` - カスタム投稿タイプのスラッグ (例: `office_location`)
- `{{POST_TYPE_SLUG}}` - URLフレンドリーなスラッグ (例: `office`)
- `株式会社サンプルのWebサイト` - 説明文 (例: `オフィス・工場情報`)
- `{{MENU_TITLE}}` - 管理画面メニュー名 (例: `オフィス・工場インポート`)
- `{{YAML_FILENAME}}` - YAMLファイル名 (例: `office-locations-data.yaml`)
- `{{ROOT_KEY}}` - YAMLのルートキー (例: `locations`)
- `{{FUNCTION_PREFIX}}` - 関数プレフィックス (例: `office`)

**条件付きセクション:**
- `{{TAXONOMY_SETUP}}` - タクソノミーがある場合のみ含める
- `{{IMAGE_FIELDS}}` - 画像フィールドがある場合のみ含める
- `{{FIELDS_*}}` - 動的に生成されるフィールド処理

### 2. `data-template.yaml`
YAMLデータファイルのテンプレート。サンプルデータを含みます。

### 3. `field-definitions.json`
フィールド定義のサンプル。エージェントがフィールド構造を理解するための参考資料。

## 使用方法

`/create-importer` コマンドを実行すると、wordpress-professional-engineer エージェントがこれらのテンプレートを参照して新しいインポート機能を生成します。

## 参考実装

以下の既存実装がテンプレートのベースになっています:

- `themes/{{THEME_NAME}}/inc/office-import.php`
- `themes/{{THEME_NAME}}/inc/statistics-import.php`
- `themes/{{THEME_NAME}}/config/office-locations-data.yaml`
- `themes/{{THEME_NAME}}/config/company-statistics-data.yaml`
