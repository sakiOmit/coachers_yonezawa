---
name: create-importer
description: "YAML + PHP インポート機能生成"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Write
  - Glob
  - Bash
context: fork
agent: general-purpose
---

# YAML + PHP インポート機能生成

このコマンドは、WordPress カスタム投稿タイプ用の YAML データ + PHP インポート機能を自動生成します。

## 実行フロー

### Step 1: 要件ヒアリング

ユーザーに以下を確認してください:

1. **カスタム投稿タイプ名** (例: `office_location`, `company_statistic`)
2. **投稿タイプの説明** (例: "オフィス・工場情報", "企業統計データ")
3. **ACF フィールド構成** (例: `postal_code`, `address`, `map_url`, `sort_order` など)
4. **タクソノミー** (あれば。例: `office_category`)
5. **画像フィールド** (あれば。例: `image_group[pc]`, `image_group[sp]`)
6. **サンプルデータ件数** (YAML に含めるサンプル数。デフォルト: 3件)

### Step 2: テンプレートファイルの確認

以下のテンプレートファイルを参照してください:

```bash
# PHPインポート機能のベース実装（そのまま使用可能）
themes/{{THEME_NAME}}/inc/office-import.php

# YAMLデータのサンプル
themes/{{THEME_NAME}}/config/office-locations-data.yaml

# テンプレートファイル
.claude/templates/importer/README.md
.claude/templates/importer/data-template.yaml
.claude/templates/importer/field-definitions.json
```

**重要**: `office-import.php` をテンプレートとして使用し、必要な箇所のみ置き換えてください。

### Step 3: wordpress-professional-engineer を起動

**重要: メインエージェントは実装を行わず、必ず wordpress-professional-engineer を起動すること**

以下の情報を渡してエージェントを起動:

```
Task tool で wordpress-professional-engineer を起動し、以下のタスクを依頼:

---
カスタム投稿タイプ「{投稿タイプ名}」用のYAML + PHPインポート機能を作成してください。

## 要件

**投稿タイプ**: {post_type_slug}
**説明**: {description}

**ACFフィールド**:
- field_name_1: 説明
- field_name_2: 説明
...

**タクソノミー**: {taxonomy_slug} (あれば)

**画像フィールド**: {image_fields} (あれば)

## 成果物

1. **YAMLデータファイル**
   - パス: `themes/{{THEME_NAME}}/config/{slug}-data.yaml`
   - サンプルデータ {sample_count} 件を含める

2. **PHPインポート機能**
   - パス: `themes/{{THEME_NAME}}/inc/{slug}-import.php`
   - 既存の `office-import.php` と同じ設計パターンを踏襲
   - 管理画面メニュー: 「ツール > {メニュー名}」

3. **functions.php への追加**
   - `require_once` でインポート機能を読み込み
---
```

### Step 4: 動作確認

エージェントの実装完了後、以下を確認:

1. **ファイル生成確認**
   ```bash
   ls -la themes/{{THEME_NAME}}/config/{slug}-data.yaml
   ls -la themes/{{THEME_NAME}}/inc/{slug}-import.php
   ```

2. **パーミッション確認**
   ```bash
   # 644 になっているか確認
   stat -c "%a %n" themes/{{THEME_NAME}}/config/{slug}-data.yaml
   stat -c "%a %n" themes/{{THEME_NAME}}/inc/{slug}-import.php
   ```

3. **WordPress 管理画面で確認**
   - 「ツール」メニューに新しいインポート項目が表示されるか
   - プレビュー機能が正常に動作するか
   - インポート実行が成功するか

### Step 5: ドキュメント更新

CLAUDE.md に新しいインポート機能の使用方法を追記（必要に応じて）。

## トラブルシューティング

### パーミッションエラーが出る場合

```bash
chmod 644 themes/{{THEME_NAME}}/config/{slug}-data.yaml
chmod 644 themes/{{THEME_NAME}}/inc/{slug}-import.php
```

### 管理画面にメニューが表示されない

`functions.php` で正しく `require_once` されているか確認:

```bash
grep -n "require_once.*{slug}-import" themes/{{THEME_NAME}}/functions.php
```

### YAML パースエラーが出る場合

- インデント（スペース2個）が正しいか確認
- クォートが必要な値（URL等）にクォートがあるか確認

## 使用例

```bash
# コマンド実行
/create-importer

# ユーザーが情報を入力
# → wordpress-professional-engineer が起動
# → YAML + PHP ファイルが生成される
# → WordPress 管理画面で「ツール > {メニュー名}」からインポート実行
```
