# ライブラリ統合ガイドライン

このドキュメントは、サードパーティライブラリ（SimpleBar, Splide, GSAP など）の統合方法とベストプラクティスをまとめたものです。

## 一般原則

### ライブラリ初期化の基本ルール

1. **単一初期化**: `data-*` 属性による自動初期化とJavaScript初期化を併用しない
2. **iOS対応**: モバイル対応ライブラリは必ずiOS Safari実機で動作確認
3. **レスポンシブ対応**: `matchMedia` でブレイクポイント判定し、デバイスごとに初期化/破棄
4. **エラーハンドリング**: ライブラリ初期化失敗時のフォールバック処理を実装

---

## SimpleBar（横スクロール実装）

横スクロールUIを実装する際のカスタムスクロールバーライブラリ。

### よくある問題と解決策

#### 問題1: iOS Safariで動作しない

##### ❌ BAD: 二重初期化 + iOS用CSS不足

```html
<!-- HTML: data-simplebar属性を使用 -->
<div class="chart-wrapper" data-simplebar data-simplebar-auto-hide="false">
  ...
</div>
```

```javascript
// JS: さらにnew SimpleBar()で初期化（二重初期化）
const chartWrapper = document.querySelector('.chart-wrapper');
new SimpleBar(chartWrapper, {
  autoHide: false,
});
```

```scss
// SCSS: iOS特有のCSSが不足
.chart-wrapper {
  // -webkit-overflow-scrolling, touch-action が無い
}
```

**問題点:**
- `data-simplebar` 属性とJavaScript初期化の二重初期化
- iOS用プロパティ（`-webkit-overflow-scrolling: touch`, `touch-action`）が不足
- タッチイベントが正しく処理されない

##### ✅ GOOD: JavaScript初期化のみ + iOS対応CSS

```html
<!-- HTML: data-simplebar属性は使用しない -->
<div class="chart-wrapper">
  ...
</div>
```

```javascript
// JS: JavaScript初期化のみ（モバイル時のみ）
import SimpleBar from 'simplebar';
import 'simplebar/dist/simplebar.css';

const isMobile = window.matchMedia('(max-width: 767px)').matches;
const chartWrapper = document.querySelector('.chart-wrapper');

if (isMobile && chartWrapper) {
  try {
    const simpleBarInstance = new SimpleBar(chartWrapper, {
      autoHide: false,
      forceVisible: 'x',        // 横スクロールバーを強制表示
      scrollbarMinSize: 50,      // 最小スクロールバーサイズ
      clickOnTrack: false,       // iOS誤動作防止
    });
  } catch (error) {
    console.error('SimpleBar initialization failed:', error);
    // Fallback: ネイティブスクロール
    chartWrapper.style.overflowX = 'auto';
  }
}
```

```scss
// SCSS: iOS対応CSS
.chart-wrapper {
  @include sp {
    // iOS慣性スクロール有効化
    -webkit-overflow-scrolling: touch;
    // 横スクロールのみ許可（縦スクロール無効化）
    touch-action: pan-x;
  }

  // SimpleBarのスクロールバーカスタマイズ
  .simplebar-track.simplebar-horizontal {
    height: svw(6) !important;
    background: #f9f9f9 !important;
  }

  .simplebar-scrollbar::before {
    background: var(--color-primary) !important;
    opacity: 1 !important;
  }

  // 縦スクロールバーを非表示
  .simplebar-track.simplebar-vertical {
    display: none;
  }
}
```

**参考実装:**
- `src/js/pages/company/growth-timeline.js`
- `src/scss/object/projects/company/_p-growth-story.scss`
- `themes/jll_wp/pages/page-company.php` (`.p-growth-timeline__chart-wrapper`)

---

#### 問題2: レスポンシブ対応が不完全

##### ❌ BAD: デバイス回転時に破棄されない

```javascript
// 初期化のみでリサイズ対応なし
const simpleBarInstance = new SimpleBar(element);
```

**問題点:**
- デバイス回転（縦→横、横→縦）時にSimpleBarが適切に初期化/破棄されない
- PC表示時もSimpleBarが残り、不要なスクロールバーが表示される

##### ✅ GOOD: resize イベントでレスポンシブ対応

```javascript
let simpleBarInstance = null;
const RESIZE_DEBOUNCE_MS = 250;

const initSimpleBar = () => {
  const isMobile = window.matchMedia('(max-width: 767px)').matches;
  const element = document.querySelector('.scroll-wrapper');

  if (!element) return;

  // モバイル時: 初期化
  if (isMobile && !simpleBarInstance) {
    simpleBarInstance = new SimpleBar(element, { /* options */ });
  }
  // PC時: 破棄
  else if (!isMobile && simpleBarInstance) {
    simpleBarInstance.unMount();
    simpleBarInstance = null;
  }
};

// 初期化
domReady(initSimpleBar);

// リサイズ時に再初期化（デバウンス処理）
let resizeTimeout;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(initSimpleBar, RESIZE_DEBOUNCE_MS);
});
```

---

## Splide（カルーセル・スライダー）

カルーセル実装に使用するスライダーライブラリ。

### 基本的な使い方

```javascript
import Splide from '@splidejs/splide';
import '@splidejs/splide/css';

const splide = new Splide('.splide', {
  type: 'loop',         // ループスライド
  perPage: 3,           // PC: 3枚表示
  perMove: 1,
  gap: '1rem',
  breakpoints: {
    767: {              // SP: 1枚表示
      perPage: 1,
      gap: '0.5rem',
    },
  },
});

splide.mount();
```

### 注意点

- **破棄処理**: `splide.destroy()` を適切に呼ぶ（特にSPA的な動的ページ遷移時）
- **アクセシビリティ**: `aria-label` を適切に設定
- **画像遅延読み込み**: `data-splide-lazy` 属性を活用

### よくある問題と解決策

#### 問題: `autoWidth: true` + `loading="lazy"` でスライダーが不安定

##### 症状

- スライダーの幅計算がズレる（たまに動かない）
- ページ初回アクセス時やキャッシュクリア後に発生しやすい
- 低速回線で再現率が高い

##### 原因

`autoWidth: true` は画像の実際の幅を取得してスライダーを計算する。
`DOMContentLoaded` 時点で `loading="lazy"` の画像は未読み込みのため、正確な寸法が取得できない。

##### ❌ BAD: 初期化後に放置

```javascript
document.addEventListener("DOMContentLoaded", () => {
  new Splide(".splide", {
    autoWidth: true,  // 画像幅に依存
  }).mount();
  // 画像が後から読み込まれても再計算されない
});
```

##### ✅ GOOD: 画像読み込み後に `refresh()` で再計算

```javascript
/**
 * コンテナ内のすべての画像の読み込み完了を待機
 */
function waitForImages(container) {
  const images = container.querySelectorAll("img");
  const promises = Array.from(images).map((img) => {
    if (img.complete) return Promise.resolve();
    return new Promise((resolve) => {
      img.addEventListener("load", resolve, { once: true });
      img.addEventListener("error", resolve, { once: true });
    });
  });
  return Promise.all(promises);
}

document.addEventListener("DOMContentLoaded", () => {
  const element = document.querySelector(".splide");
  if (!element) return;

  // 1. Splide を即座に初期化
  const splide = new Splide(element, {
    autoWidth: true,
  }).mount();

  // 2. 画像読み込み完了後に寸法を再計算
  waitForImages(element).then(() => {
    splide.refresh();
  });
});
```

##### 使い分け

| スライダーの位置 | 推奨アプローチ |
|-----------------|---------------|
| ファーストビュー内 | `loading="eager"` + 通常初期化 |
| ファーストビュー外 | `loading="lazy"` + `refresh()` |

**参考実装:**
- `src/js/pages/recruit-message/image-loop.js`
- `src/js/pages/recruit-message/strategy-slider.js`

---

## GSAP（アニメーション）

高度なアニメーション実装に使用。

### 基本原則

- **ScrollTrigger使用時**: `markers: true` で動作確認後、本番では削除
- **パフォーマンス**: `will-change` プロパティを適切に使用
- **クリーンアップ**: コンポーネント破棄時に `ScrollTrigger.getAll().forEach(t => t.kill())` で破棄

```javascript
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

gsap.to('.element', {
  scrollTrigger: {
    trigger: '.element',
    start: 'top center',
    end: 'bottom center',
    toggleActions: 'play none none reverse',
    // markers: true, // 開発時のみ
  },
  opacity: 1,
  y: 0,
  duration: 1,
});
```

**詳細:** アニメーション実装時は `interactive-ux-engineer` エージェントに依頼すること。

---

## トラブルシューティング

### iOS Safariでライブラリが動作しない場合

1. **ブラウザキャッシュをクリア**: Safari設定 > Safari > 詳細 > Webサイトデータ > すべてのWebサイトデータを削除
2. **コンソールエラー確認**: Mac + iOS実機をUSB接続してリモートデバッグ（Safari > 開発 > [デバイス名]）
3. **iOS特有CSS確認**:
   - `-webkit-overflow-scrolling: touch` が設定されているか
   - `touch-action` プロパティが適切か
   - `position: fixed` による問題（iOS Safari特有のバグ）がないか

### ライブラリが読み込まれない場合

1. **package.json確認**: `dependencies` または `devDependencies` に記載されているか
2. **ビルド確認**: `npm run build` でエラーが出ていないか
3. **enqueue.php確認**: WordPress側で正しくエンキューされているか（`themes/jll_wp/inc/enqueue.php`）

### パフォーマンス問題

- **バンドルサイズ**: `vite.config.js` で適切にチャンク分割されているか確認
- **遅延読み込み**: 初期表示に不要なライブラリは動的インポート（`import()`）
- **不要な初期化**: 条件分岐で必要な場合のみ初期化

---

## 新規ライブラリ追加時のチェックリスト

- [ ] `package.json` に追加（`npm install <library>`）
- [ ] 初期化コードを適切な場所に配置（`src/js/pages/` または `src/js/utils/`）
- [ ] CSS/SCSSをインポート
- [ ] iOS Safari実機で動作確認
- [ ] レスポンシブ対応確認（PC/SP/タブレット）
- [ ] ビルドサイズ確認（`npm run build`）
- [ ] `vite.config.js` でチャンク分割設定（必要に応じて）
- [ ] このドキュメントに使用方法・注意点を追記

---

**関連ドキュメント:**
- `04-build-configuration.md` - Viteビルド設定
- `06-faq.md` - よくある問題と解決策
