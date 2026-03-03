# Coding Style Rules

## Overview

このルールファイルは、プロジェクト全体に適用される一般的なコーディングスタイルを定義します。
言語横断的な規約と、チーム開発での一貫性を保証します。

## 一般原則

### シンプルさを優先

- 必要最小限のコードで実装
- 将来の仮定に基づく過剰設計を避ける
- 理解しやすいコードを書く

### DRY（Don't Repeat Yourself）

重複コードは共通化:

```php
// ❌ 重複
function get_job_title() { return get_field('title'); }
function get_news_title() { return get_field('title'); }

// ✅ 共通化
function get_post_title_field() { return get_field('title'); }
```

### 早期リターン

```php
// ✅ 正しい - 早期リターン
function process_data($data) {
    if (empty($data)) {
        return null;
    }

    // メイン処理
    return $result;
}

// ❌ 避ける - 深いネスト
function process_data($data) {
    if (!empty($data)) {
        // 深いネスト
        if (condition) {
            // さらに深い
        }
    }
}
```

## 命名規則

### 言語別規則

| 言語 | 変数/関数 | クラス | 定数 |
|------|----------|--------|------|
| PHP | snake_case | PascalCase | UPPER_SNAKE |
| JavaScript | camelCase | PascalCase | UPPER_SNAKE |
| SCSS | kebab-case | - | $kebab-case |

### 意味のある命名

```php
// ✅ 正しい - 意図が明確
$active_jobs = get_active_job_listings();
$is_published = $post->post_status === 'publish';

// ❌ 避ける - 曖昧
$data = get_data();
$flag = check_status();
```

## コメント

### 必要な場合のみ

```php
// ✅ WHYを説明
// ACF v5.9以降でrepeaterの空配列がfalseを返すため
if (!empty($items)) {

// ❌ WHATの説明（コードで明らか）
// タイトルを取得する
$title = get_the_title();
```

### PHPDoc（公開API/複雑な関数）

```php
/**
 * レスポンシブ画像を出力
 *
 * @param array|int $image ACF画像フィールドまたはattachment ID
 * @param string $class CSSクラス名
 * @param array $sizes ['pc' => int, 'sp' => int]
 * @return void
 */
function render_responsive_image($image, $class, $sizes = []) {
```

## ファイル構成

### 1ファイル1責務

```
// ✅ 正しい - 責務分離
inc/
├── helpers/
│   ├── image-helpers.php      # 画像関連
│   ├── string-helpers.php     # 文字列関連
│   └── date-helpers.php       # 日付関連

// ❌ 避ける - 巨大ファイル
inc/
└── helpers.php                # すべてのヘルパー
```

### Import順序

```javascript
// 1. 外部ライブラリ
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

// 2. 内部モジュール
import { initNavigation } from './modules/navigation';
import { initSlider } from './modules/slider';

// 3. スタイル
import '../scss/main.scss';
```

## エラーハンドリング

### 適切なエラー処理

```php
// ✅ 正しい - 明示的なエラー処理
function get_job_data($job_id) {
    if (!$job_id) {
        return null;
    }

    $job = get_post($job_id);
    if (!$job || $job->post_type !== 'job') {
        return null;
    }

    return $job;
}
```

### JavaScript

```javascript
// ✅ 正しい - try/catch
async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch failed:', error);
        return null;
    }
}
```

## パフォーマンス意識

### データベースクエリ

```php
// ✅ 正しい - 必要なフィールドのみ
$query = new WP_Query([
    'post_type' => 'job',
    'posts_per_page' => 10,
    'fields' => 'ids'  // IDのみ取得
]);

// ❌ 避ける - 不要なデータ取得
$all_posts = get_posts(['numberposts' => -1]);
```

### JavaScript

```javascript
// ✅ 正しい - イベント委譲
document.querySelector('.p-list').addEventListener('click', (e) => {
    if (e.target.matches('.p-list__item')) {
        handleItemClick(e.target);
    }
});

// ❌ 避ける - 個別リスナー
document.querySelectorAll('.p-list__item').forEach(item => {
    item.addEventListener('click', handleItemClick);
});
```

## Git運用

### コミットメッセージ

```
feat: 求人検索機能を追加
fix: ヘッダーのレスポンシブ崩れを修正
refactor: 画像ヘルパー関数を整理
docs: READMEにセットアップ手順を追加
style: SCSSのインデント修正
```

### ブランチ命名

```
feature/job-search
fix/header-responsive
refactor/image-helpers
```

## 禁止事項

| 禁止項目 | 理由 |
|---------|------|
| ハードコードされたURL/パス | 環境依存 |
| マジックナンバー | 意図不明 |
| 巨大な関数（100行超） | 保守性低下 |
| 深いネスト（4階層超） | 可読性低下 |
| 未使用コード | デッドコード |

## プレースホルダー形式

### 統一形式（必須）

プレースホルダーは `{{PLACEHOLDER}}` 形式に統一せよ。

```
✅ 正しい
{{THEME_NAME}}
{{PACKAGE_NAME}}
{{PROJECT_NAME}}

❌ 禁止
{THEME_NAME}      # 単一波括弧
%THEME_NAME%      # パーセント記号
$THEME_NAME       # 変数形式
```

| 項目 | 形式 |
|------|------|
| テーマ名 | `{{THEME_NAME}}` |
| パッケージ名 | `{{PACKAGE_NAME}}` |
| プロジェクト名 | `{{PROJECT_NAME}}` |

**理由**: 形式統一により init-project.js での一括置換が確実に動作する。

## ドキュメント整合性

### ステップ数・参照パスの一致

ドキュメント内で言及するステップ数やファイルパスは、**実装と完全に一致**させること。

| 項目 | ルール |
|------|--------|
| ステップ数 | 「7ステップ」と書いたら実際に7つのステップが存在すること |
| ファイルパス | 参照するパスが実際に存在すること |
| ディレクトリ名 | 単数/複数形を実装と一致させる（component vs components） |

### 確認タイミング
- ドキュメント作成・更新時
- 実装変更後のドキュメント見直し

## Single Source of Truth

### docs/ と .claude/ の二重管理禁止

| 項目 | 正（Single Source） | 参照側 |
|------|---------------------|--------|
| エージェント定義 | .claude/agents/README.md | docs/claude-guide/agents.md |
| スキル定義 | .claude/skills/*/SKILL.md | docs/claude-guide/skills.md |
| ルール定義 | .claude/rules/*.md | docs/coding-guidelines/*.md |

**原則:**
- 正のソースを更新したら、参照側も更新せよ
- 矛盾が発生したら、正のソースを優先

## ドキュメント同期ルール

### agents/skills 変更時の docs 更新必須

| 変更対象 | 更新必須ファイル |
|----------|-----------------|
| .claude/agents/ | docs/claude-guide/agents.md |
| .claude/skills/ | docs/claude-guide/skills.md |

**チェックリスト:**
- [ ] 正のソースを更新した
- [ ] 対応する docs を更新した
- [ ] CLAUDE.md のクイックリファレンスを確認した

## チェックリスト

- [ ] 命名規則に従っている
- [ ] 早期リターンを使用
- [ ] 適切なエラーハンドリング
- [ ] コメントはWHYを説明
- [ ] 1ファイル1責務
- [ ] マジックナンバーなし
- [ ] 未使用コードなし
