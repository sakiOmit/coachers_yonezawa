# Figma画像書き出しガイドライン

## 基本ルール

**すべての画像は2倍サイズで書き出す**

### 理由

画像最適化スクリプトは**ダウンスケールアプローチ**を採用しています：

- ✅ **Sharpのダウンスケール** = 高品質（Lanczos3アルゴリズム）
- ❌ **アップスケール** = 粗くなる（補間の限界）
- 💡 元画像を大きめに用意 → 必要サイズはダウンスケールで生成

### 書き出し手順

1. Figmaでコンポーネント/画像を選択
2. Export設定で **2x** を選択
3. PNG/JPEGで書き出し
4. `src/images/` に配置
5. `npm run optimize:images` 実行

### 生成される画像

```
元画像: 1000px（Figmaから2x書き出し）
↓
1x: 500px（ダウンスケール生成）← 高品質（Lanczos3）
2x: 1000px（元画像そのまま）← 最高品質（リサイズなし）
```

**実装詳細:**
- 1x画像: 元画像を0.5倍にダウンスケール（Lanczos3アルゴリズム）
- 2x画像: 元画像をそのまま使用（リサイズなし、劣化なし）
- 3x画像（SPのみ）: 元画像を1.5倍にリサイズ

### PC/SP画像の扱い

#### PC画像
```
ファイル名: hero.png（2xで書き出し）
例: Figmaで500px幅 → 1000pxで書き出し

生成結果:
- hero.webp: 500px（ダウンスケール）
- hero@2x.webp: 1000px（元画像そのまま）
```

#### SP画像
```
ファイル名: hero_sp.png（2xで書き出し、1.15倍補正適用）
例: Figmaで375px幅 → 750pxで書き出し

生成結果:
- hero_sp.webp: 431px（(750 / 2) * 1.15）
- hero_sp@2x.webp: 863px（750 * 1.15）
- hero_sp@3x.webp: 1294px（(750 * 1.5) * 1.15）

※ SP画像は375px基準の粗さ対策として1.15倍補正を自動適用
```

### 注意事項

#### ❌ やってはいけないこと
- 1xで書き出してスクリプトで拡大 → 粗くなる
- デザインサイズそのままで書き出し → アップスケールが必要になる
- 書き出し後に手動でリサイズ → スクリプトに任せる

#### ✅ 正しい手順
- 常に2xで書き出す
- スクリプトにダウンスケールを任せる（高品質）
- ファイル名規則を守る（PC: `name.png`, SP: `name_sp.png`）

### ファイル命名規則

```
PC画像: hero.png, logo.png, feature-01.png
SP画像: hero_sp.png, logo_sp.png, feature-01_sp.png

※ SP画像は必ず _sp 接尾辞を付ける
※ kebab-case（ハイフン区切り）を推奨
```

### WordPress実装例

最適化後の画像は `render_responsive_image()` で使用：

```php
<?php
render_responsive_image([
  'src' => get_template_directory_uri() . '/assets/images/hero.webp',
  'alt' => 'ヒーロー画像',
  'class' => 'p-hero__image',
  'loading' => 'eager', // Above the fold
]);
?>
```

自動的に以下のsrcsetが生成されます：

```html
<img
  src="/assets/images/hero.webp"
  srcset="/assets/images/hero.webp 1x,
          /assets/images/hero@2x.webp 2x"
  alt="ヒーロー画像"
  class="p-hero__image"
  width="500"
  height="300"
  loading="eager"
/>
```

### トラブルシューティング

#### Q: 画像が粗く見える
A: 以下を確認してください：
- Figmaから2xで書き出しているか
- `npm run optimize:images` を実行したか
- ブラウザのデバイスピクセル比に対応しているか（srcsetが正しく生成されているか）

#### Q: ファイルサイズが大きい
A: WebP形式で自動圧縮されます（品質85%）。さらに圧縮が必要な場合：
- `scripts/optimize/images.ts` の `CONFIG.quality.webp` を調整（デフォルト85）
- 元画像のサイズを見直す（不要に大きくない？）

#### Q: SP画像の1.15倍補正とは？

A: モバイルデバイスのサイズ差による画質劣化を防ぐための補正です。

**背景:**
- Figmaのモバイルデザインは通常 **375pxまたは390px** で作成される
- 実際のデバイスは **414px、430px** など大きいサイズもある
- 375pxデザイン → 430pxデバイス表示 = **約1.15倍に拡大** → 粗く見える

**解決策:**
- 全デザインを430px基準で作るのは工数的に現実的ではない
- スクリプトで自動的に **1.15倍（430 ÷ 375 = 1.147）** に拡大
- ダウンスケールアプローチなので高品質を維持

**運用:**
- Figmaでは通常サイズ（375px等）で2x書き出し
- スクリプトが自動的に430pxデバイス対応サイズを生成
- デザイナーは特別な作業不要

## まとめ

1. **Figmaから2x書き出し**（最重要）
2. `src/images/` に配置
3. `npm run optimize:images` 実行
4. 生成されたWebP画像をWordPressで使用
5. ファイル名規則を守る（PC/SP区別）

この手順により、高品質でパフォーマンスに優れた画像を自動生成できます。
