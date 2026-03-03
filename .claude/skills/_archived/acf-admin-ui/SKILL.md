---
name: acf-admin-ui
description: "ACF管理画面UI最適化コマンド"
disable-model-invocation: true
allowed-tools:
  - Task
  - Read
  - Write
  - Edit
  - Glob
  - Bash
context: fork
agent: general-purpose
---

# ACF管理画面UI最適化コマンド

WordPress管理画面をACF（Advanced Custom Fields無料版）で最適化し、クライアント体験を向上させます。

## 使用方法

```bash
/acf-admin-ui
```

## 実行内容

1. **要件ヒアリング**
   - どのような管理画面改善を希望するか確認
   - 対象コンテンツタイプ（カスタム投稿タイプなど）

2. **wordpress-acf-specialistエージェント起動**
   - ACFフィールドグループ設計
   - 管理画面UI最適化実装
   - カスタムブロック作成（必要に応じて）

3. **実装完了後の確認**
   - PHPシンタックスチェック
   - WordPress管理画面での動作確認

## 利用可能な機能

### ACFフィールド管理
- カスタム投稿タイプ用フィールド
- オプションページ用フィールド
- タクソノミー用フィールド
- 固定ページ用フィールド

### 管理画面UI最適化
- **ダッシュボード:** クイックアクセス、統計ウィジェット
- **メニュー:** 並び替え、アイコン変更、通知バッジ
- **一覧カラム:** サムネイル、カスタムフィールド表示、並び替え
- **エディタ:** ツールバー最適化、カスタムスタイル
- **メディアライブラリ:** 寸法・サイズ表示
- **バリデーション:** カスタムルール、エラーメッセージ日本語化

### カスタムブロック
- Gutenbergブロック作成
- ACF連携ブロック
- 再利用可能コンポーネント

## プロジェクト構造

### ACF特化モジュール

```
themes/{{THEME_NAME}}/inc/advanced-custom-fields/
├── groups/                       # フィールドグループ定義
├── admin-ui/                     # ACF特化UI
│   ├── field-styling.php         # フィールドスタイリング
│   ├── meta-box-layout.php       # メタボックス配置
│   ├── conditional-logic.php     # 条件分岐UI
│   └── validation.php            # バリデーション
└── blocks/                       # カスタムブロック
```

### 汎用管理画面UIモジュール

```
themes/{{THEME_NAME}}/inc/admin-ui/
├── dashboard.php                 # ダッシュボード
├── menu.php                      # メニュー整理
├── columns.php                   # 一覧カラム
├── editor.php                    # エディタUI
├── media.php                     # メディアライブラリ
├── notifications.php             # 通知表示
└── user-experience.php           # UX全般
```

## 使用例

### 例1: 新規カスタム投稿タイプのフィールド追加

```
/acf-admin-ui
```

→ エージェントが対話形式で以下を実施:
1. 投稿タイプ名を確認（例: `product`）
2. 必要なフィールドをヒアリング
3. ACFフィールドグループPHPファイル生成
4. 一覧カラムに表示項目追加
5. バリデーションルール追加（必要に応じて）

### 例2: ダッシュボードカスタマイズ

既に実装済み：
- クイックアクセスウィジェット
- サイト統計ウィジェット
- 使い方ガイドウィジェット

カスタマイズしたい場合は `themes/{{THEME_NAME}}/inc/admin-ui/dashboard.php` を編集。

### 例3: ACFフィールド定義の自動生成

acf-field-generatorスキルを使用:

```
/skill acf-field-generator
```

→ 対話形式でフィールドグループを生成

## トラブルシューティング

### スタイルが反映されない

1. ブラウザキャッシュをクリア
2. WordPress管理画面を再読み込み

### フィールドが表示されない

1. ACFプラグインが有効か確認
2. PHPシンタックスエラーチェック: `php -l themes/{{THEME_NAME}}/inc/advanced-custom-fields/groups/post-types/[file].php`
3. `functions.php` でローダーが読み込まれているか確認

### カスタムカラムが表示されない

1. `columns.php` の投稿タイプ名を確認
2. ACFフィールド名が正しいか確認
3. `get_field()` の戻り値をデバッグ

## 関連リソース

- **エージェント:** `.claude/agents/wordpress-professional-engineer.md`
- **スキル:** `.claude/skills/acf-field-generator/`
- **ACF公式ドキュメント:** https://www.advancedcustomfields.com/resources/

## 注意事項

- ACF無料版を前提（`repeater`, `flexible_content`, `clone`フィールドは使用不可）
- すべてのフィールドはコードベースで管理（管理画面からの作成は非推奨）
- キーは必ずグローバルでユニーク
