# ベーススタイル継承ルール

## 基本原則

**「ベーススタイルで定義されているものは継承する。書くのは差分のみ。」**

## 既に定義済みのベーススタイル

### body要素

```scss
body {
  min-width: 320px;
  margin: auto;
  color: var(--color-black);
  background-color: var(--color-gray);
  @include font-ja;
  font-size: rv(16);        // デフォルトフォントサイズ
  line-height: 1.6;         // デフォルト行間
  letter-spacing: 0.08em;   // デフォルト文字間

  @include sp {
    font-size: svw(14);
  }
}
```

### aタグ

```scss
a {
  display: block;
  color: inherit;
  text-decoration: none;
  transition: all 0.3s;
}
```

### img, video

```scss
img, video {
  display: block;
  max-width: 100%;
  height: auto;
}
```

### button

```scss
button {
  transition: all 0.3s;
}
```

## ❌ 重複してはいけない例

```scss
// ❌ BAD: bodyで既に定義済み
.p-About__text {
  font-size: rv(16);      // 不要
  line-height: 1.6;       // 不要
  letter-spacing: 0.08em; // 不要
  @include font-ja;       // 不要
}

// ❌ BAD: aタグで既に定義済み
.c-Button a {
  display: block;         // 不要
  text-decoration: none;  // 不要
  transition: all 0.3s;   // 不要
}

// ❌ BAD: imgで既に定義済み
.p-Gallery__image img {
  display: block;         // 不要
  max-width: 100%;        // 不要
}
```

## ✅ 正しい書き方

```scss
// ✅ GOOD: bodyと異なる値のみ指定
.p-About__heading {
  font-size: rv(32);      // bodyと異なる → 必要

  @include sp {
    font-size: svw(24);
  }
}

// ✅ GOOD: 差分のみ
.p-About__lead {
  font-size: rv(18);      // bodyより大きい → 必要
  line-height: 1.8;       // bodyと異なる → 必要
  // letter-spacing は 0.08em のままなので書かない
}
```

## CSS変数の活用

カラーやフォントは**必ずCSS変数**を使用:

```scss
// ❌ BAD: 直書き
.element {
  color: #333;
  background-color: #1f4c7d;
}

// ✅ GOOD: CSS変数使用
.element {
  color: var(--color-black);
  background-color: var(--color-blue-1);
}
```

### 利用可能なCSS変数

```scss
// カラー
var(--color-blue-1)   // #1f4c7d
var(--color-blue-2)   // #82b9c7
var(--color-blue-3)   // #95bcc7
var(--color-blue-4)   // #d8e7e9
var(--color-black)    // #333
var(--color-gray)     // #fafafa
var(--color-white)    // #fff

// フォントmixin
@include font-ja($fw)      // Noto Sans JP
@include font-gentium($fw) // Gentium Book Plus
@include font-roboto($fw)  // Roboto
```

## コーディング前チェックリスト

- [ ] `font-size: rv(16)` → **不要**（body継承）
- [ ] `line-height: 1.6` → **不要**（body継承）
- [ ] `letter-spacing: 0.08em` → **不要**（body継承）
- [ ] `@include font-ja` → **不要**（body継承）
- [ ] `a { display: block }` → **不要**（aタグ継承）
- [ ] `transition` → **不要**（a, button継承）
- [ ] カラーコード直書き → **NG**（`var(--color-*)`使用）
- [ ] フォント直書き → **NG**（`@include font-*`使用）
