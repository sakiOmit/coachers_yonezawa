# SCSS設計規約

**Single Source of Truth:** `.claude/rules/scss.md`

詳細は `scss/` サブディレクトリを参照してください。

## 詳細ドキュメント

- **[scss/naming.md](./scss/naming.md)** - BEM命名規則・FLOCSS
- **[scss/responsive.md](./scss/responsive.md)** - レスポンシブ設計・コンテナ
- **[scss/base-styles.md](./scss/base-styles.md)** - ベーススタイル継承

## クイックリファレンス

### 命名規則

```scss
// Block__Element-Child--Modifier
.p-page__section-title--active { }

// 必須: ケバブケース
.p-page__main-visual { }  // ✅
.p-page__mainVisual { }   // ❌ 禁止
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

### コンテナ

**構文:** `@include container($max-width?)` - 引数省略でデフォルト値使用（推奨）

```scss
// 推奨: デフォルト値使用
.p-page__container {
  @include container();
}

// カスタム幅が必要な場合
.p-narrow__container {
  @include container(800px);
}
```

### ホバー効果

```scss
// ✅ 正しい実装（タッチデバイス対応）
.element {
  @include hover {
    opacity: 0.8;
    color: var(--color-primary);
  }
}

// ❌ 禁止（:hover直接記述）
.element {
  &:hover {
    opacity: 0.8;
  }
}
```

**理由:**
- `@include hover` は `@media (any-hover: hover)` でラップされ、タッチデバイスで誤動作しない
- マウス環境でのみホバー効果が適用される
- ハイブリッドデバイス（タッチ+マウス）にも柔軟に対応

## 禁止事項

| 禁止 | 理由 |
|------|------|
| `.p-page__element { }` トップレベル | `&__` ネスト必須 |
| `&-` ネスト | セレクタが不明確になる |
| `&:hover { }` 直接記述 | `@include hover` 必須（タッチデバイス対応） |
| `@include pc` + `@include sp` 併用 | 768px前後で空白発生 |
| `font-size: rv(16)` | body継承あり |
| `line-height: 1.6` | body継承あり |
| カラーコード直書き | `var(--color-*)` 使用 |

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

## エントリーポイント

```scss
// src/css/pages/[page]/style.scss
@use "scss/foundation/function" as *;
@use "scss/foundation/mixins/block" as *;
@use "scss/foundation/mixins/responsive" as *;

@use "scss/object/components/c-Breadcrumbs";
@use "scss/object/projects/p-PageHeader";
@use "scss/object/projects/[page]/p-[Component]";
```

**重要:** エントリーポイントには直接スタイルを書かない
