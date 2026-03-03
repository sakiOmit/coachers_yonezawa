# トップページ自動セットアップ

## 🚀 クイックスタート（推奨）

1つのコマンドでトップページを自動セットアップできます。

```bash
./scripts/setup-top-page.sh
```

### 何が実行されるか

このスクリプトは以下を自動的に実行します:

1. ✅ 固定ページ「トップページ」を作成
2. ✅ ページテンプレート「pages/page-top.php」を適用
3. ✅ ACFフィールド値を設定（メインビジュアルのタイトル・サブタイトル）
4. ✅ フロントページ（トップページ）に設定
5. ✅ パーマリンク設定をフラッシュ

### 実行結果

```
=========================================
トップページ自動セットアップ開始
=========================================

[1/4] 固定ページを作成中...
✓ 固定ページを作成しました (ID: 5)

[2/4] ACFフィールド値を設定中...
✓ メインビジュアル タイトルを設定
✓ メインビジュアル サブタイトルを設定

[3/4] フロントページに設定中...
✓ トップページをフロントページに設定

[4/4] パーマリンク設定をフラッシュ中...
✓ パーマリンク設定を更新

=========================================
✓ セットアップ完了!
=========================================

以下のURLで確認できます:
→ http://localhost:8000/

WordPress管理画面:
→ http://localhost:8000/wp-admin/
```

## 📦 ACFフィールドの自動インポート

ACFフィールドグループは、WordPress管理画面に初回アクセス時に**自動的にインポート**されます。

### 仕組み

- `themes/{{THEME_NAME}}/inc/acf-auto-import.php` が初回アクセス時に実行
- `themes/{{THEME_NAME}}/acf-json/` 内のJSONファイルを自動インポート
- インポート済みフラグを保存（重複インポート防止）

### 手動でインポートをリセット

```
http://localhost:8000/wp-admin/?reset_acf_import=1
```

管理画面でこのURLにアクセスすると、インポートフラグがリセットされ、次回アクセス時に再インポートされます。

## 🛠 トラブルシューティング

### スクリプト実行時にエラーが出る

```bash
# Dockerコンテナが起動しているか確認
docker compose ps

# WordPressコンテナが起動していない場合
docker compose up -d

# 再実行
./scripts/setup-top-page.sh
```

### 既にページが存在する場合

スクリプトは既存ページを検索して使用します。削除したい場合:

```bash
# 既存のトップページを削除
docker compose exec wordpress wp post delete $(docker compose exec wordpress wp post list --post_type=page --name=home --field=ID --allow-root) --force --allow-root

# 再実行
./scripts/setup-top-page.sh
```

### ACFフィールドが表示されない

1. ACFプラグインがインストールされているか確認
2. WordPress管理画面に一度アクセス（自動インポートが実行される）
3. **カスタムフィールド > フィールドグループ** で「トップページ設定」が存在するか確認

### スタイルが反映されない

```bash
# ビルドを実行
npm run build

# または開発モードで起動
npm run dev
```

## 📝 手動セットアップ（参考）

自動セットアップを使わない場合は、以下のドキュメントを参照してください:

- [手動セットアップ手順](./wordpress-top-page-setup.md)

## 🔄 セットアップのやり直し

```bash
# 1. トップページを削除
docker compose exec wordpress wp post delete $(docker compose exec wordpress wp post list --post_type=page --name=home --field=ID --allow-root) --force --allow-root

# 2. ACFインポートフラグをリセット
docker compose exec wordpress wp option delete {{THEME_PREFIX}}_acf_imported --allow-root

# 3. セットアップスクリプトを再実行
./scripts/setup-top-page.sh
```

## 次のステップ

セットアップ完了後:

1. ✅ http://localhost:8000/ でトップページを確認
2. 📝 WordPress管理画面でACFフィールドを編集
3. 🎨 必要に応じてコンテンツを追加
