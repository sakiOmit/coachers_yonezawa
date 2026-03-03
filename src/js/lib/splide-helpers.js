/**
 * Splide Helpers
 *
 * Factory functions for creating Splide instances
 */

import Splide from "@splidejs/splide";
import "@splidejs/splide/css";

/**
 * 無限ループスライダーを作成
 *
 * @param {string} selector - Splide要素のCSSセレクタ
 * @param {Object} options - Splide設定オプション
 * @returns {Splide} Splideインスタンス
 *
 * @example
 * const slider = createInfiniteLoopSplide('.js-logo-slider', {
 *   perPage: 5,
 *   gap: 20,
 * });
 */
export function createInfiniteLoopSplide(selector, options = {}) {
  const defaultOptions = {
    type: "loop",
    drag: "free",
    focus: "center",
    arrows: false,
    pagination: false,
    autoScroll: {
      speed: 1,
    },
    ...options,
  };

  const splide = new Splide(selector, defaultOptions);

  // AutoScrollエクステンションが利用可能な場合はマウント
  if (window.splide?.Extensions?.AutoScroll) {
    splide.mount(window.splide.Extensions);
  } else {
    splide.mount();
  }

  // デバッグ用にグローバル公開
  window.Splide = Splide;

  return splide;
}

/**
 * 遅延初期化スライダーを作成（IntersectionObserver使用）
 *
 * ビューポートに入った時点で初期化することで初期ロードを軽減
 *
 * @param {string} selector - Splide要素のCSSセレクタ
 * @param {Object} options - Splide設定オプション
 * @param {Object} observerOptions - IntersectionObserverオプション
 * @returns {IntersectionObserver|null} Observerインスタンス
 *
 * @example
 * createLazySplide('.js-gallery-slider', {
 *   perPage: 3,
 *   gap: 16,
 * }, {
 *   rootMargin: '100px',
 * });
 */
export function createLazySplide(selector, options = {}, observerOptions = {}) {
  const element = document.querySelector(selector);
  if (!element) return null;

  let initialized = false;

  const defaultObserverOptions = {
    rootMargin: "200px",
    ...observerOptions,
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting && !initialized) {
        const splide = new Splide(selector, options);
        splide.mount();
        initialized = true;
        observer.unobserve(entry.target);
      }
    });
  }, defaultObserverOptions);

  observer.observe(element);

  return observer;
}

/**
 * 標準スライダーを作成
 *
 * @param {string} selector - Splide要素のCSSセレクタ
 * @param {Object} options - Splide設定オプション
 * @returns {Splide} Splideインスタンス
 *
 * @example
 * const slider = createSplide('.js-hero-slider', {
 *   type: 'fade',
 *   rewind: true,
 *   autoplay: true,
 * });
 */
export function createSplide(selector, options = {}) {
  const splide = new Splide(selector, options);
  splide.mount();
  return splide;
}

/**
 * レスポンシブ設定付きスライダーを作成
 *
 * @param {string} selector - Splide要素のCSSセレクタ
 * @param {Object} pcOptions - PC用設定
 * @param {Object} spOptions - SP用設定
 * @param {number} breakpoint - ブレークポイント（デフォルト: 768）
 * @returns {Splide} Splideインスタンス
 *
 * @example
 * const slider = createResponsiveSplide('.js-card-slider',
 *   { perPage: 3, gap: 24 },
 *   { perPage: 1, gap: 16 }
 * );
 */
export function createResponsiveSplide(
  selector,
  pcOptions = {},
  spOptions = {},
  breakpoint = 768
) {
  const options = {
    ...pcOptions,
    breakpoints: {
      [breakpoint]: spOptions,
    },
  };

  return createSplide(selector, options);
}
