# レスポンシブ設計

## 使用する関数

| 関数 | 用途 | 基準 |
|------|------|------|
| `rv($value)` | PC幅でフルード変化 | 768px〜1440px |
| `svw($value)` | SP用vw変換 | 375px基準 |
| `pvw($value)` | PC用vw変換 | 1440px基準 |

## 基本方針

1. **デフォルト（メディアクエリなし）= PC用**
2. **`@include sp` でSP用にオーバーライド**
3. **`rv()` を活用してPC幅内でフルード対応**

## ❌ 絶対にやってはいけないこと

```scss
// ❌ BAD: @include pc と @include sp を併用
.element {
  @include pc {
    padding: rv(40);
  }
  @include sp {
    padding: svw(20);
  }
  // → デフォルトが不明確、768px前後で空白発生
}
```

## ✅ 推奨パターン

```scss
// ✅ GOOD: デフォルトをPC、spでオーバーライド
.element {
  padding: rv(40);        // PC用（デフォルト）

  @include sp {
    padding: svw(20);     // SPのみオーバーライド
  }
}
```

## 実装例

### 余白

```scss
.p-page__content {
  padding-block: rv(84);

  @include sp {
    padding-block: svw(60) svw(84);
  }
}
```

### フォントサイズ

```scss
.p-page__heading {
  font-size: rv(32);

  @include sp {
    font-size: svw(20);
  }
}
```

### gap/margin

```scss
.p-page__section {
  gap: rv(24);

  @include sp {
    gap: svw(24);
  }
}
```

## コンテナ幅

### @include container mixin

```scss
@mixin container($containerWidth) {
  width: $containerWidth;
  margin-inline: auto;
  @media (max-width: $containerWidth) {
    width: 100%;
    padding-inline: rv(16);
  }
  @include sp {
    width: 100%;
    padding-inline: svw(16);
  }
}
```

### よく使われる幅

| 幅 | 用途 |
|----|------|
| `1232px` | 標準ページ |
| `1230px` | トップページセクション |
| `1360px` | ヘッダー |
| `900px` | 狭めコンテンツ |
| `680px` | フォームページ |

### 命名規則

コンテナ幅を設定する要素は必ず `__container` または `-container` で終わる:

```scss
// ✅ GOOD
.p-gallery__container {
  @include container(1232px);
}

// ❌ BAD
.p-gallery__wrapper {
  @include container(1232px);  // NG: container以外の名前
}
```

## コンテナ命名規則（厳守）

**鉄則: クラス名に `container` を含む場合、`@include container()` のみ記述可能**

### ❌ 悪い例

```scss
// ❌ BAD: container命名に他のプロパティを記述
.l-header__container {
  @include container(1200px);
  display: flex;           // NG: container含む命名に禁止
  gap: 40px;               // NG
  padding: 20px;           // NG
}

// ❌ BAD: container含む命名なのに@include containerがない
.p-top__mv-container {
  display: flex;           // NG: container含む命名なら@include container必須
  align-items: center;
}

// ❌ BAD: container含む命名なのに@include containerがない
.p-page__content-container {
  display: grid;           // NG: containerという文字列が入っている
  gap: 40px;
}
```

**問題点:**
- 命名とスタイルの責務が一致していない
- コンテナの役割が不明確
- 保守性が低下

### ✅ 良い例

```scss
// ✅ GOOD: container命名には@include containerのみ
.l-header__container {
  @include container(1200px);  // containerのみ
}

.l-header__inner {
  display: flex;               // レイアウトは別要素で
  gap: 40px;
  align-items: center;
}

// ✅ GOOD: レイアウト用なら-wrapper等の命名を使用
.p-top__mv-wrapper {
  display: flex;               // wrapperなのでレイアウトOK
  align-items: center;
  justify-content: center;
}
```

### 実践例

```scss
// ページ構造
.p-page__container {
  @include container(1232px);
}

.p-page__content {
  display: flex;
  gap: rv(60);

  @include sp {
    flex-direction: column;
    gap: svw(40);
  }
}

.p-page__main {
  flex: 1;
}

.p-page__sidebar {
  width: rv(300);
}
```

**メリット:**
- 責務が明確（Single Responsibility Principle）
- 同じコンテナで異なるレイアウトが可能
- 保守性・再利用性が向上
