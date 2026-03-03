# プロジェクトテンプレート化ガイド

このドキュメントでは、現在のプロジェクトをgitテンプレートリポジトリ化し、新規プロジェクトで再利用する方法を説明します。

## 📋 目次

1. [テンプレート化の準備](#テンプレート化の準備)
2. [新規プロジェクトでの使用方法](#新規プロジェクトでの使用方法)
3. [プレースホルダー一覧](#プレースホルダー一覧)
4. [トラブルシューティング](#トラブルシューティング)

## テンプレート化の準備

### 1. プレースホルダーの配置

プロジェクト固有の情報を以下のプレースホルダーに置き換えます：

```
wordpress-template        - プロジェクト名（例: hypex_acusnet）
wordpress-template-wp          - テーマ名（例: Acushnet Japan Inc. Recruit）
wordpress-template-wp           - テーマディレクトリ名（例: acshnet-japan-inc-recruit-wp）
wordpress_template_wp        - テーマプレフィックス（PHP関数名用）（例: acshnet_japan_inc_recruit_wp）
株式会社サンプル        - 会社名（日本語）（例: アクシュネットジャパン株式会社）
Sample Company Inc.     - 会社名（英語）（例: Acushnet Japan Inc.）
wordpress-template-wp         - テキストドメイン（例: acshnet-japan-inc-recruit-wp）
Wordpress_Template_Wp_Theme        - パッケージ名（例: Acushnet_Japan_Inc_Recruit_Theme）
株式会社サンプルのWebサイト         - プロジェクト説明
```

### 2. 置き換え対象のファイル例

#### PHP ファイル
```php
// themes/wordpress-template-wp/functions.php
/**
 * wordpress-template-wp Theme
 * @package Wordpress_Template_Wp_Theme
 */

// テキストドメイン
__( 'Text', 'wordpress-template-wp' );

// 関数プレフィックス
function wordpress_template_wp_setup() {
  // テーマセットアップ
}
add_action('after_setup_theme', 'wordpress_template_wp_setup');
```

#### SCSS ファイル
```scss
// src/scss/foundation/_utilities.scss
/**
 * @package Wordpress_Template_Wp_Theme
 */
```

#### ドキュメント
```markdown
# 株式会社サンプルのWebサイト

株式会社サンプルのWebサイト
```

#### 設定ファイル
```yaml
# config/wordpress-pages.yaml
pages:
  - title: "株式会社サンプルについて"
    description: "株式会社サンプルの会社情報"
```

### 3. テーマディレクトリ名

テンプレートリポジトリでは、テーマディレクトリを以下のように命名：

```
themes/wordpress-template-wp/
```

初期化スクリプトが自動的にリネームします。

### 4. GitHubテンプレートリポジトリ化

```bash
# GitHubリポジトリをテンプレート化
# Settings > Template repository にチェック
```

## 新規プロジェクトでの使用方法

### 1. テンプレートからリポジトリを作成

GitHubでテンプレートリポジトリから新規リポジトリを作成：

```bash
# Use this template ボタンをクリック
# または
gh repo create my-new-project --template owner/template-repo
```

### 2. クローン

```bash
git clone https://github.com/your-org/my-new-project.git
cd my-new-project
```

### 3. 初期化スクリプトを実行

```bash
npm install
npm run init
```

### 4. 対話形式で入力

```
===========================================
🚀 プロジェクト初期化セットアップ
===========================================

プロジェクト名（英数字とハイフン、アンダースコア）[my-new-project]: my-client-site
テーマディレクトリ名（英数字とハイフン）[my-client-site-wp]: my-client-site-wp
テーマ名（表示用）[my-client-site-wp]: My Client Site
会社名（日本語）[株式会社サンプル]: 株式会社サンプルクライアント
会社名（英語）[Sample Company Inc.]: Sample Client Inc.
テキストドメイン（WordPress翻訳用）[my-client-site-wp]: my-client-site-wp
パッケージ名（PHPパッケージ名）[My_Client_Site_Wp_Theme]: My_Client_Site_Theme
プロジェクト説明: 株式会社サンプルクライアントのコーポレートサイト
```

### 5. 確認して完了

```
===========================================
📋 入力内容の確認
===========================================
PROJECT_NAME: my-client-site
THEME_DIR: my-client-site-wp
THEME_NAME: My Client Site
COMPANY_NAME: 株式会社サンプルクライアント
COMPANY_NAME_EN: Sample Client Inc.
TEXT_DOMAIN: my-client-site-wp
PACKAGE_NAME: My_Client_Site_Theme
DESCRIPTION: 株式会社サンプルクライアントのコーポレートサイト
===========================================

🔄 ファイルを置き換え中...

✓ CLAUDE.md
✓ src/scss/foundation/_utilities.scss
✓ themes/my-client-site-wp/functions.php
✓ config/wordpress-pages.yaml
...

📁 テーマディレクトリをリネーム: wordpress-template-wp → my-client-site-wp

===========================================
✅ プロジェクト初期化完了！
===========================================
処理ファイル数: 245
変更ファイル数: 87
===========================================

📝 次のステップ:
  1. npm install
  2. npm run docker:init
  3. npm run dev
```

### 6. 開発開始

```bash
npm run docker:init
npm run dev
```

## プレースホルダー一覧

### 必須プレースホルダー

| プレースホルダー       | 説明                     | 例                                   |
| ---------------------- | ------------------------ | ------------------------------------ |
| `wordpress-template`     | プロジェクト名           | `hypex_acusnet`                      |
| `wordpress-template-wp`        | テーマディレクトリ名     | `acshnet-japan-inc-recruit-wp`       |
| `wordpress-template-wp`       | テーマ名（表示用）       | `Acushnet Japan Inc. Recruit`        |
| `wordpress_template_wp`     | テーマプレフィックス（PHP関数名用） | `acshnet_japan_inc_recruit_wp` |
| `株式会社サンプル`     | 会社名（日本語）         | `アクシュネットジャパン株式会社`     |
| `Sample Company Inc.`  | 会社名（英語）           | `Acushnet Japan Inc.`                |
| `wordpress-template-wp`      | WordPressテキストドメイン | `acshnet-japan-inc-recruit-wp`       |
| `Wordpress_Template_Wp_Theme`     | PHPパッケージ名          | `Acushnet_Japan_Inc_Recruit_Theme`   |
| `株式会社サンプルのWebサイト`      | プロジェクト説明         | `アクシュネットジャパンの採用サイト` |

### 配置場所の例

#### PHPファイル
- `themes/wordpress-template-wp/functions.php`
- `themes/wordpress-template-wp/style.css`
- `themes/wordpress-template-wp/inc/**/*.php`

#### ドキュメント
- `CLAUDE.md`
- `README.md`
- `docs/**/*.md`

#### 設定ファイル
- `config/wordpress-pages.yaml`
- `.mcp.json`
- `package.json`

#### SCSS
- `src/scss/foundation/_utilities.scss`

## トラブルシューティング

### ❌ スクリプト実行時にエラー

```bash
# Node.jsのバージョン確認（v18以上推奨）
node -v

# 依存関係の再インストール
rm -rf node_modules package-lock.json
npm install
```

### ❌ プレースホルダーが置き換わらない

**原因**: 該当ファイルに`{{PLACEHOLDER}}`が存在しない

**対処**:
1. テンプレートリポジトリに戻ってプレースホルダーを配置
2. 手動で該当ファイルを修正

### ❌ テーマディレクトリがリネームされない

**原因**: `themes/wordpress-template-wp/` が存在しない

**対処**:
```bash
# 手動でリネーム
mv themes/old-theme-name themes/new-theme-name
```

### ❌ 二重に実行してしまった

**警告**: 初期化スクリプトは1回のみ実行してください

**対処**:
```bash
# gitでリセット
git reset --hard HEAD

# または最初からやり直し
git clone ... (再クローン)
```

## ベストプラクティス

### ✅ テンプレート作成時

1. **プレースホルダーを漏れなく配置**
   - 全てのプロジェクト固有情報を置き換える
   - grep で確認: `grep -r "固有の文字列" .`

2. **テストする**
   - 別ディレクトリでテンプレートから新規作成
   - 初期化スクリプトを実行
   - 正常に動作するか確認

3. **ドキュメント更新**
   - README.md にテンプレート使用方法を記載
   - CLAUDE.md にプロジェクト固有ガイドを記載

### ✅ 新規プロジェクト作成時

1. **初期化は最初の1回のみ**
   - `npm run init` は最初に1回だけ実行
   - 実行後は通常の開発フロー

2. **入力内容の確認**
   - 対話形式で入力した内容を必ず確認
   - 間違えた場合はgit resetでやり直し

3. **コミット前に確認**
   - プレースホルダーが残っていないか確認
   - `grep -r "{{" .` で検索

## 参考資料

- [GitHubテンプレートリポジトリ作成](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
- [WordPress テーマ開発](https://developer.wordpress.org/themes/)
