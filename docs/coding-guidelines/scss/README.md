# SCSS設計規約

## ドキュメント一覧

| ファイル | 内容 | 参照タイミング |
|---------|------|---------------|
| [naming.md](./naming.md) | BEM命名規則・FLOCSS | クラス名を決める時 |
| [responsive.md](./responsive.md) | レスポンシブ設計・コンテナ | rv/svw使用時 |
| [base-styles.md](./base-styles.md) | ベーススタイル継承 | 新コンポーネント作成時 |

## クイックリファレンス

### 命名規則

```scss
.p-page__element-child--modifier { }
//  │      │       │        └─ Modifier (--区切り)
//  │      │       └─ サブElement (-区切り)
//  │      └─ Element (__区切り)
//  └─ Block (p-プレフィックス)
```

### レスポンシブ

```scss
.element {
  padding: rv(40);      // PC（デフォルト）

  @include sp {
    padding: svw(20);   // SP（オーバーライド）
  }
}
```

### 禁止事項

- `&-` ネスト記法
- `@include pc` と `@include sp` の併用
- ベーススタイル重複（`font-size: rv(16)` 等）
- カラーコード直書き（`var(--color-*)` 使用）

## ディレクトリ構成

```
src/scss/
├── foundation/          # 変数・関数・mixin
├── layout/              # l-* (header, footer)
└── object/
    ├── components/      # c-* (汎用)
    ├── projects/        # p-* (ページ固有)
    └── utility/         # u-* (ユーティリティ)
```
