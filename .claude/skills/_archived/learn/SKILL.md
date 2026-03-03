---
name: learn
description: "/learn - 知見の手動記録"
disable-model-invocation: true
allowed-tools:
  - mcp__serena__read_memory
  - mcp__serena__write_memory
  - mcp__serena__edit_memory
  - Read
  - Glob
context: fork
agent: general-purpose
---

# /learn - 知見の手動記録

致命的なバグの解消法や重要な知見を、閾値を待たずに即座に記録します。

## 使用方法

```bash
# 基本形式
/learn "[記録したい内容]"

# カテゴリ指定（省略可）
/learn [カテゴリ] "[記録したい内容]"
```

## カテゴリ一覧

| カテゴリ | 記録先メモリ | 説明 |
|---------|-------------|------|
| `wordpress` / `wp` / `php` | troubleshooting-wordpress.md | WordPress/PHP関連 |
| `js` / `javascript` | troubleshooting-js.md | JavaScript関連 |
| `build` / `vite` / `docker` | troubleshooting-build.md | ビルド/環境関連 |
| `scss` / `css` | common-issues-patterns.md | SCSS関連パターン |
| `pattern` / `rule` | common-issues-patterns.md | 一般的なパターン |
| `base` | base-styles-reference.md | ベーススタイル |
| (省略時) | 内容から自動判定 | - |

## 使用例

### WordPress関連

```bash
/learn wordpress "ACFのrepeaterフィールドは必ず空配列チェックしてからforeachする"

/learn wp "パーマリンク設定変更後は必ず「変更を保存」を2回クリック"

/learn php "render_responsive_image()の第2引数altは必須、空文字禁止"
```

### JavaScript関連

```bash
/learn js "ScrollTriggerはページ遷移前に必ずScrollTrigger.getAll().forEach(t => t.kill())する"

/learn javascript "Swiperのdestroyはloop:trueの場合slideが複製されるので注意"

/learn js "GSAPアニメーションはcleanup関数でkill()しないとメモリリーク"
```

### ビルド/環境関連

```bash
/learn build "vite.config.jsにエントリー追加後はnpm run dev再起動必須"

/learn docker "wordpress_dataのパーミッション問題はdocker compose exec経由で解決"

/learn vite "HMRが効かない場合はwp-config.phpのVITE_DEV_MODE確認"
```

### SCSS関連

```bash
/learn scss "containerクラスには@include container()以外のプロパティ禁止"

/learn css "&-ネストは禁止、必ず&__を使う"
```

### 自動カテゴリ判定

```bash
# カテゴリ省略時は内容から自動判定
/learn "get_field()は必ずif文で存在チェック"
# → WordPress関連と判定 → troubleshooting-wordpress.md に記録
```

## 実行フロー（自動）

```
1. カテゴリ判定（指定 or 自動）
2. 該当メモリを読み込み
3. 重複チェック（既に同じ内容があれば更新）
4. 新規追加 or 発生回数更新
5. 完了報告
```

## 記録フォーマット

### トラブルシューティング系

```markdown
### 🔴 [タイトル]（手動登録）
- **重要度**: Critical（手動登録のため）
- **内容**: [記録内容]
- **登録日**: [日付]
- **登録理由**: 手動（致命的/重要）
```

### パターン系

```markdown
### [パターン名]（手動登録）
- **検出回数**: ∞（手動登録のため閾値済み扱い）
- **内容**: [記録内容]
- **登録日**: [日付]
- **自動検出可能**: [判定結果]
- **Lintルール**: [提案があれば]
```

## 手動登録の特別扱い

- **閾値スキップ**: 手動登録は即座に「重要」として記録
- **優先表示**: レビュー時に優先的に参照される
- **Lint提案**: 自動検出可能な場合は即座にルール追加を提案

## 自然言語での依頼も可能

コマンドを使わなくても、以下のように依頼できます:

```
「このバグの解消法を記録して: [内容]」
「これ覚えておいて: [内容]」
「次回のために記録: [内容]」
```

エージェントが適切なメモリに記録します。

## 関連コマンド

| コマンド | 説明 |
|----------|------|
| `/reflect` | 蓄積された知見を分析 |
| `/suggest-rules` | Lintルール提案 |
