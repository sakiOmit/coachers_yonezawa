# FAQ・アンチパターン集

このドキュメントは、よくある規約違反パターンと質問をまとめたものです。

## よくある規約違反パターン（絶対に避けること）

### 違反1: containerクラスを使わない手動幅制御

#### ❌ BAD: 規約違反

```scss
.p-page {
  &__list {
    max-width: rv(1026);
    margin: auto;  // 手動でセンタリング
  }

  &__tabs {
    padding-left: rv(104);  // paddingで幅制御
  }
}
```

**問題点:**
- `@include container` mixin未使用
- レスポンシブ対応が不完全（SPでの左右paddingが自動で付かない）
- メンテナンス性が低い（幅を変更する際に複数箇所を修正）

#### ✅ GOOD: 規約準拠

```scss
.p-page {
  &__container {
    @include container(1232px);  // containerクラス + mixin使用
  }
}
```

**参照:** `02-scss-design.md` の「コンテナ幅の設定」

---

### 違反2: @include pc と @include sp の併用

#### ❌ BAD: 併用すると768px前後で空白が発生

```scss
.element {
  @include pc {
    padding: rv(40);
  }
  @include sp {
    padding: svw(20);
  }
  // → デフォルトが不明確、ブレークポイントでスタイル適用漏れ
}
```

**問題点:**
- デフォルト（メディアクエリなし）のスタイルが存在しない
- 768px前後で両方のメディアクエリが適用されない空白地帯が発生
- どちらが優先されるか不明確

#### ✅ GOOD: デフォルトPC、spでオーバーライド

```scss
.element {
  padding: rv(40);  // デフォルト = PC（768px以上）

  @include sp {
    padding: svw(20);  // SPのみオーバーライド（767px以下）
  }
}
```

**参照:** `02-scss-design.md` の「レスポンシブ設計」

---

### 違反3: エントリーポイントに直接スタイルを書く

#### ❌ BAD: エントリーポイントに直接スタイルを書く

```scss
// src/css/pages/[page]/style.scss

@use "scss/foundation/function" as *;

.p-page {
  background: #fafafa;  // NG: 直接スタイルを書いている
  padding: rv(40);
}
```

**問題点:**
- アーキテクチャ違反（エントリーポイントはモジュールの読み込みのみ）
- スタイルの所在が不明確（`src/scss/object/projects/` にあるべき）
- ファイル構成が混乱する

#### ✅ GOOD: @use のみ

```scss
// src/css/pages/[page]/style.scss

@use "scss/foundation/function" as *;
@use "scss/foundation/mixins/block" as *;
@use "scss/foundation/mixins/responsive" as *;

@use "scss/object/components/c-Breadcrumbs";
@use "scss/object/projects/p-PageHeader";
@use "scss/object/projects/[page]/p-Page";  // 実装はこちら
```

```scss
// src/scss/object/projects/[page]/_p-Page.scss

@use "../../foundation/function" as *;
// ...

.p-page {
  background: var(--color-gray);
  padding: rv(40);

  // ...
}
```

**参照:** `02-scss-design.md` の「エントリーポイントの書き方」

---

### 違反4: Template Name コメントの欠落

#### ❌ BAD: Template Name がない

```php
<?php
/**
 * 通常投稿アーカイブページ
 */

get_header();
?>
```

**問題点:**
- WordPress管理画面でテンプレート選択時に識別できない
- 規約違反
- 他の開発者がファイルの用途を理解しにくい

#### ✅ GOOD: Template Name を記載

```php
<?php
/**
 * Template Name: ニュース一覧
 * 通常投稿アーカイブページ
 */

get_header();
?>
```

**参照:** `03-template-parts.md` の「ページテンプレートの基本構造」

---

### 違反5: 画像を直接imgタグで出力

#### ❌ BAD: 直接imgタグを使用

```php
<img src="<?php echo get_template_directory_uri(); ?>/assets/images/hero.png" alt="ヒーロー画像">
```

**問題点:**
- WebP対応がない
- Retina対応がない
- レスポンシブ対応がない
- メタデータ自動取得がない

#### ✅ GOOD: render_responsive_image() を使用

```php
<?php
render_responsive_image([
  'src' => get_template_directory_uri() . '/assets/images/hero.png',
  'alt' => 'ヒーロー画像',
  'class' => 'p-page__hero-image',
  'loading' => 'eager'
]);
?>
```

**参照:** `03-image-handling.md` の「画像出力規約」

---

### 違反6: &-ネスト記法の使用

#### ❌ BAD: &-ネスト記法（絶対禁止）

```scss
.p-page {
  &__section {
    &-container { }  // ❌ 絶対NG
    &-content { }    // ❌ 絶対NG
  }
}
```

**問題点:**
- 可読性の低下
- HTML/PHPとの対応が困難
- BEM原則違反

#### ✅ GOOD: すべて独立したElementとして定義

```scss
.p-page {
  &__section { }
  &__section-container { }
  &__section-content { }
}
```

**参照:** `02-scss-design.md` の「命名規則」

---

## 参考実装ファイル

**模範となるファイル:**

| 用途 | ファイル |
|------|---------|
| シンプルページ | `src/scss/object/projects/thanks/_p-Thanks.scss` |
| グリッドレイアウト | `src/scss/object/projects/gallery/_p-Gallery.scss` |
| 共通コンポーネント | `src/scss/object/projects/_p-PageHeader.scss` |
| エントリーポイント | `src/css/pages/thanks/style.scss` |
| WordPressテンプレート | `themes/{{THEME_NAME}}/pages/page-thanks.php` |

## よくある質問（FAQ）

### Q1: Element区切りにハイフンを使うと、Modifierと区別できないのでは？

**A**: ハイフンの数で区別します。

- **Element区切り**: ハイフン1つ（`__item-title`, `__section-content`）
- **Modifier**: ハイフン2つ（`__item--active`, `__section--large`）

この規則を守れば、混同することはありません。

---

### Q2: なぜアンダースコア区切りではなくハイフン区切りなのか？

**A**: 既存実装の大多数がハイフン区切りを使用しているためです。

- gallery, news, art など主要ページがハイフン区切り
- 統一コストが最小になる
- BEMの標準的な記法とも合致

---

### Q3: 既存のアンダースコア区切りコードはどうすべきか？

**A**: 新規実装では必ずハイフン区切りを使用してください。既存コードは以下の方針で対応：

- **新規ページ**: 必ずハイフン区切り
- **既存ページの大規模修正時**: ハイフン区切りに統一
- **既存ページの小規模修正**: そのままでも可（ただし新規追加部分はハイフン区切り）

---

### Q4: `__section-container` と `__container` はどう使い分ける？

**A**: コンテキストに応じて使い分けます。

- `__container`: ページ全体の汎用コンテナ
- `__section-container`: 特定セクション専用のコンテナ

ただし、どちらも `@include container($width)` を使用することが必須です。

---

### Q5: なぜ `&-header` のようなネスト記法を禁止するのか？

**A**: 複数の理由から、`&-` によるネスト記法は絶対禁止としています。

**禁止する理由:**

1. **可読性の低下**: ネストが深くなると、実際のクラス名が分かりにくくなる
   ```scss
   // ❌ これでは .p-page__content-header なのか判別しにくい
   .p-page {
     &__content {
       &-header { }
     }
   }

   // ✅ 一目で .p-page__content-header と分かる
   .p-page {
     &__content-header { }
   }
   ```

2. **HTML/PHPとの対応が困難**: テンプレートファイルでクラス名を検索する際、ネストされていると見つけられない

3. **BEM原則違反**: BEMでは、すべてのElementはBlock直下に定義するのが原則
   - Element間に親子関係があっても、クラス名では階層化しない
   - `__section-header-title` のように、ハイフンで繋げて一つのElementとする

4. **一貫性の確保**: プロジェクト全体で同じパターンを強制することで、誰が書いても同じ構造になる

**正しい書き方:**
```scss
.p-page {
  // すべてのElementをBlock直下に並べる
  &__content { }
  &__content-header { }
  &__content-header-title { }
  &__content-main { }
  &__content-footer { }
}
```

---

### Q6: どのタイミングでtemplate-partに切り出すべきか？

**A**: 以下のいずれかに該当する場合：

1. **2箇所以上で使用される** → 即座に切り出し
2. **70行以上の大型セクション** → 可読性向上のため切り出し
3. **セクション内の繰り返し要素** → DRY原則に従い切り出し

**迷ったら切り出さない**を基本とし、明確な再利用性がある場合のみ切り出す。

**参照:** `03-template-parts.md` の「切り出し基準」

---

### Q7: template-partsの`common/`と`[page]/`の使い分けは？

**A**: 使用箇所で判断：

- **`common/`**: 2箇所以上で使用される汎用コンポーネント
- **`[page]/`**: 特定ページ内でのみ使用されるコンポーネント

例: `page-header`は14箇所で使用 → `common/`
例: `top-heading`はhome内4箇所のみ → `home/`

---

### Q8: vite.config.jsの更新を忘れたらどうなる？

**A**: 致命的な問題が発生します：

- ❌ 開発環境では動作するが、本番環境でCSSが読み込まれない
- ❌ `npm run build` でCSSファイルが生成されない
- ❌ WordPress側でスタイルが適用されない

**対策**: 新規ページ作成時は必ず `05-checklist.md` を参照して確認

---

### Q9: loading属性はどう使い分ける？

**A**: 以下の表に従ってください：

| 用途 | loading値 | 理由 |
|------|-----------|------|
| **ファーストビュー画像** | `eager` | LCPスコア向上、すぐに表示 |
| **スクロール後の画像** | `lazy` | 初期ロード高速化、帯域節約 |
| **ギャラリー画像** | `lazy` | 必要時に読み込み |
| **ロゴ** | `eager` | すぐに表示が必要 |

**参照:** `03-image-handling.md` の「loading属性の使い分け」

---

### Q10: ベーススタイルで定義済みのスタイルを書いてしまった場合は？

**A**: 重複スタイルは即座に削除してください。

**削除すべき例:**
- `font-size: rv(16)` → 不要（body継承）
- `line-height: 1.6` → 不要（body継承）
- `letter-spacing: 0.08em` → 不要（body継承）
- `@include font-ja` → 不要（body継承）
- `a { display: block }` → 不要（aタグ継承）
- `transition: all 0.3s` → 不要（a, button継承）

**原則**: ベーススタイルで定義されているものは継承する。書くのは差分のみ。

**参照:** `02-scss-design.md` の「ベーススタイルの継承ルール」
