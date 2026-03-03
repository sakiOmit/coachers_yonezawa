# BEM命名規則

## プレフィックス（FLOCSS）

| プレフィックス | 用途 | 例 |
|--------------|------|-----|
| `.l-*` | レイアウト | `.l-header`, `.l-footer` |
| `.c-*` | 汎用コンポーネント | `.c-breadcrumbs`, `.c-button` |
| `.p-*` | ページ固有 | `.p-thanks`, `.p-gallery` |
| `.u-*` | ユーティリティ | `.u-flex`, `.u-hover` |

## BEM構文

```scss
.p-page {                    // Block
  &__element { }             // Element
  &__element--modifier { }   // Modifier
  &__element-child { }       // サブElement（ハイフンで繋ぐ）
}
```

## 🚫 絶対禁止: トップレベルでのBEM Element定義

**BEM Elementは必ず `&__` でネストする。トップレベルでの定義は禁止。**

```scss
// ❌ 禁止: トップレベルでElement定義
.p-page__title { }
.p-page__description { }
.c-button__icon { }
.l-header__nav { }
.u-text__large { }

// ✅ 正しい: &__ でネスト
.p-page {
  &__title { }
  &__description { }
}

.c-button {
  &__icon { }
}

.l-header {
  &__nav { }
}
```

**理由:**
- コードの可読性・保守性向上
- Block-Element の関係が明確
- ファイル内での構造が一目瞭然
- 検索・リファクタリングが容易

## 必須: ケバブケース（kebab-case）

```scss
// ✅ OK
.p-page__main-visual { }
.p-page__hero-section { }
.c-button--primary-large { }

// ❌ NG: キャメルケース
.p-page__mainVisual { }      // 禁止
.p-page__heroSection { }     // 禁止

// ❌ NG: パスカルケース
.p-page__MainVisual { }      // 禁止
```

## 🚫 絶対禁止: `&-` ネスト記法

```scss
// ❌ 禁止
.p-page {
  &__section {
    &-container { }  // NG
    &-content { }    // NG
  }
}

// ✅ 正しい書き方
.p-page {
  &__section { }
  &__section-container { }  // 独立して定義
  &__section-content { }    // 独立して定義
}
```

**ルール:**
- Element内で `&-` を使用することは絶対禁止
- サブElementはハイフン1つ（`-`）で繋ぐ
- Modifierはハイフン2つ（`--`）
- すべてのElementはBlockの直下に独立して定義

## 構造要素の命名パターン

### コンテンツエリア

```scss
.p-page {
  &__main { }         // ページ全体のメインエリア
  &__content { }      // セクション内コンテンツ
  &__container { }    // レイアウト幅制御
}
```

### リスト・グリッド

```scss
.p-page {
  &__list { }         // リストコンテナ
  &__item { }         // リストアイテム
  &__item-title { }   // アイテム内要素
}
```

### テキスト要素

```scss
.p-page {
  &__heading { }      // メイン見出し
  &__title { }        // タイトル
  &__description { }  // 説明文
  &__text { }         // 汎用テキスト
}
```

### Modifier

```scss
.p-page {
  &__element--active { }  // アクティブ状態
  &__element--small { }   // サイズ: 小
  &__element--01 { }      // 番号識別
}
```
