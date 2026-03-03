# SCSS/CSS Rules

## Overview

このルールファイルは、FLOCSS + BEM設計に基づくSCSS規約を定義します。
保守性・拡張性を重視し、チーム開発での一貫性を保証します。

## FLOCSS構成

```
src/scss/
├── foundation/           # 変数・mixin・リセット
│   ├── _variables.scss
│   ├── _mixins.scss
│   └── _reset.scss
├── layout/               # l- prefix
│   ├── _l-header.scss
│   └── _l-footer.scss
└── object/
    ├── component/        # c- prefix（再利用可能）
    ├── project/          # p- prefix（ページ固有）
    └── utility/          # u- prefix（単機能）
```

## SCSSファイル命名規則

SCSSファイル名は必ず **kebab-case** で記述:

```
✅ 正しい
_c-section-heading.scss
_p-job-card.scss
_l-main-header.scss

❌ 禁止
_c-sectionHeading.scss   # camelCase
_c-section_heading.scss  # snake_case
_c-SectionHeading.scss   # PascalCase
```

## BEM命名規則（必須）

### kebab-case必須

```scss
// ✅ 正しい
.p-job-card {}
.p-job-card__title {}
.p-job-card__title--large {}

// ❌ 禁止
.p-jobCard {}           // camelCase禁止
.p-job_card {}          // snake_case禁止
.p-JobCard {}           // PascalCase禁止
```

### &__ネスト必須

```scss
// ✅ 正しい
.p-job-card {
  &__title {
    font-size: rv(18);
  }

  &__description {
    margin-top: rv(16);
  }

  &--featured {
    border: 1px solid $color-primary;
  }
}

// ❌ 禁止 - &-ネスト
.p-job-card {
  &-title {}     // BEM要素は &__ を使用
}
```

### Modifier記法

```scss
// ✅ 正しい
.p-button {
  &--primary {}
  &--secondary {}
  &--large {}
}

// ❌ 禁止 - 独立したModifier
.p-button-primary {}    // ブロックと分離している
```

## レスポンシブ設計

### PC First + SP Override

```scss
.p-section {
  padding: rv(80) 0;      // PC値（デフォルト）

  @include sp {
    padding: svw(40) 0;   // SP値（上書き）
  }
}
```

### サイズ関数

| 関数 | 用途 | 基準幅 |
|------|------|-------|
| `rv()` | PC固定値 | - |
| `pvw()` | PC vw | 1440px |
| `svw()` | SP vw | 375px |

```scss
.p-title {
  font-size: rv(32);      // PC: 32px固定

  @include sp {
    font-size: svw(24);   // SP: 24/375 * 100vw
  }
}
```

## コンテナルール（厳守）

### クラス名に`container`を含む場合

**構文:** `@include container($max-width?)` - 引数省略でデフォルト値使用（推奨）

```scss
// ✅ 正しい - デフォルト値使用（推奨）
.p-section__container {
  @include container();
}

// ✅ 正しい - カスタム幅指定
.p-narrow__container {
  @include container(800px);
}

// ❌ 禁止 - 他のプロパティ追加
.p-section__container {
  @include container();
  display: flex;          // 禁止
  padding: rv(20);        // 禁止
  margin-bottom: rv(40);  // 禁止
}
```

### レイアウトが必要な場合

```scss
// ✅ 正しい - __inner を使用
.p-section__container {
  @include container();
}

.p-section__inner {
  display: flex;
  gap: rv(24);
}
```

## ホバースタイル（必須）

### @include hover 使用必須

```scss
// ✅ 正しい - タッチデバイス対応
.p-button {
  @include hover {
    opacity: 0.8;
  }
}

// ❌ 禁止 - 直接:hover
.p-button {
  &:hover {
    opacity: 0.8;
  }
}
```

## mixin インポート（必須）

### @use 宣言必須

hover mixin を使用する場合、ファイル先頭で必ずインポート:

```scss
// ✅ 正しい - @use でインポート
@use '../foundation/mixins/hover' as *;

.p-element {
  @include hover {
    opacity: 0.8;
  }
}

// ❌ 禁止 - インポートなしで使用
.p-element {
  @include hover {  // エラー: Undefined mixin
    opacity: 0.8;
  }
}
```

## 画像サイズ指定ルール

画像要素にwidth/height両方を指定せず、baseスタイルを活かす。

```scss
// ✅ 正しい - baseスタイル活用
.p-section__image {
  // max-width: 100%; height: auto; は base で定義済み
  // サイズ制御が必要な場合のみ max-width を指定
  max-width: rv(400);
}

// ❌ 禁止 - 両方指定
.p-section__image {
  width: 100%;
  height: auto;  // base と重複
}
```

## 禁止事項

### ベーススタイル重複

```scss
// ❌ 禁止 - ベースで定義済みのスタイル
.p-section__title {
  font-family: $font-family-base;  // 重複
  line-height: 1.5;                // 重複
  color: $color-text;              // 重複
}
```

### マジックナンバー

```scss
// ❌ 禁止
.p-card {
  margin-top: 47px;       // 意味不明な値
}

// ✅ 正しい - 変数使用
.p-card {
  margin-top: rv(48);     // 8の倍数
}
```

### 深いネスト（3階層まで）

```scss
// ❌ 禁止 - 4階層以上
.p-card {
  &__content {
    &__inner {
      &__text {           // 4階層目
        // ...
      }
    }
  }
}

// ✅ 正しい - フラットに
.p-card {
  &__content {}
  &__content-inner {}
  &__content-text {}
}
```

## コード品質

### 未使用クラス

定義のみで使用されていないクラスは削除。

### プロパティ順序（推奨）

```scss
.p-element {
  // 1. Positioning
  position: relative;
  top: 0;

  // 2. Box Model
  display: flex;
  width: 100%;
  padding: rv(16);
  margin: 0;

  // 3. Typography
  font-size: rv(16);
  line-height: 1.5;

  // 4. Visual
  background: $color-bg;
  border: 1px solid $color-border;

  // 5. Animation
  transition: opacity 0.3s;
}
```

## Figma Variables連携

### Figma → SCSS変数 命名規則マッピング

| Figma変数名 | SCSS変数名（CSS Custom Properties） |
|-------------|-------------------------------------|
| `color/primary` | `--color-primary` |
| `color/text/secondary` | `--color-text-secondary` |
| `spacing/section` | `--spacing-section` |
| `font/heading/h1` | `--font-heading-h1` |
| `fontSize/body` | `--font-size-body` |
| `lineHeight/tight` | `--line-height-tight` |
| `letterSpacing/wide` | `--letter-spacing-wide` |

### 変換ルール

1. **スラッシュ `/` → ハイフン `-`**
   ```
   color/primary → color-primary
   font/heading/h1 → font-heading-h1
   ```

2. **camelCase → kebab-case**
   ```
   fontSize → font-size
   lineHeight → line-height
   letterSpacing → letter-spacing
   ```

3. **CSS Custom Properties形式（`--` プレフィックス）**
   ```
   color-primary → --color-primary
   ```

4. **数値接尾辞の保持**
   ```
   spacing/8 → --spacing-8
   spacing/16 → --spacing-16
   ```

### 自動生成セクションの識別

```scss
// ===== Figma Design Tokens (Auto-generated) =====
// Source: {fileKey} / {nodeId}
// Generated: {timestamp}
// ================================================

:root {
  --color-primary: #d71218;
  // ... 自動生成された変数
}

// ===== End Figma Design Tokens =====
```

**注意:**
- 自動生成セクション内の手動編集は非推奨（再生成時に上書きされる）
- カスタム変数は自動生成セクションの外に定義

### 関連コマンド

- `/figma-variables-to-scss` - デザイントークン自動抽出
- `/figma-implement` Step 4 - 実装ワークフロー内での使用

## チェックリスト

- [ ] kebab-case命名
- [ ] &__ネスト使用
- [ ] container要素は@include container()のみ
- [ ] @include hover使用
- [ ] ベーススタイル重複なし
- [ ] マジックナンバーなし
- [ ] 3階層以内のネスト
- [ ] Figma Variables変換は命名規則に従っている
