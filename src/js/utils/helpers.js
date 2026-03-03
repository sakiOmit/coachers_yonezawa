/**
 * 共通ヘルパー関数
 *
 * プロジェクト全体で使用する汎用的なユーティリティ関数
 */

/**
 * スマホ判定
 *
 * @param {number} breakpoint - ブレークポイント（デフォルト: 767px）
 * @returns {boolean} スマホサイズの場合true
 *
 * @example
 * if (isSP()) {
 * }
 */
export const isSP = (breakpoint = 767) => {
  return window.matchMedia(`(max-width: ${breakpoint}px)`).matches;
};

/**
 * PC判定
 *
 * @param {number} breakpoint - ブレークポイント（デフォルト: 768px）
 * @returns {boolean} PC表示の場合true
 */
export const isPC = (breakpoint = 768) => {
  return window.matchMedia(`(min-width: ${breakpoint}px)`).matches;
};

/**
 * ヘッダー高さキャッシュ
 * @private
 */
let headerHeightCache = null;

/**
 * ヘッダー高さ取得（キャッシュ付き、reflow最小化）
 *
 * 1. CSS変数から取得を試みる（reflow不要）
 * 2. CSS変数がない場合はoffsetHeightで計測（1回のみ、キャッシュする）
 * 3. リサイズ時はキャッシュをクリア
 *
 * @param {string} selector - ヘッダーのセレクタ
 * @param {boolean} forceRecalculate - 強制的に再計算（デフォルト: false）
 * @returns {number} ヘッダーの高さ（px）
 *
 * @example
 * const height = getHeaderHeight();
 */
export const getHeaderHeight = (selector = ".l-header", forceRecalculate = false) => {
  // キャッシュがあり、強制再計算でない場合はキャッシュを返す
  if (headerHeightCache !== null && !forceRecalculate) {
    return headerHeightCache;
  }

  const header = document.querySelector(selector);
  if (!header) {
    headerHeightCache = 0;
    return 0;
  }

  // 1. CSS変数から取得を試みる（最も効率的、reflow不要）
  const cssVarHeight = getComputedStyle(document.documentElement)
    .getPropertyValue("--header-height")
    .trim();

  if (cssVarHeight) {
    const height = parseInt(cssVarHeight, 10);
    if (!isNaN(height)) {
      headerHeightCache = height;
      return height;
    }
  }

  // 2. CSS変数がない場合、offsetHeightで計測（reflow発生）
  const height = header.offsetHeight;
  headerHeightCache = height;
  return height;
};

/**
 * ヘッダー高さキャッシュをクリア
 * リサイズ時やレイアウト変更時に呼び出す
 *
 * @example
 * window.addEventListener('resize', clearHeaderHeightCache);
 */
export const clearHeaderHeightCache = () => {
  headerHeightCache = null;
};

// リサイズ時に自動的にキャッシュをクリア（デバウンス付き + bfcache対応）
if (typeof window !== "undefined") {
  let resizeTimeout;

  const handleResize = () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      clearHeaderHeightCache();
    }, 150);
  };

  const cleanup = () => {
    clearTimeout(resizeTimeout);
    window.removeEventListener("resize", handleResize);
  };

  // 初期化
  window.addEventListener("resize", handleResize, { passive: true });

  // bfcache対応: ページ非表示時にクリーンアップ
  window.addEventListener("pagehide", cleanup);

  // bfcache対応: ページ復帰時に再初期化
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      window.addEventListener("resize", handleResize, { passive: true });
    }
  });
}

/**
 * スクロール位置を設定
 *
 * ヘッダー高さを考慮したスクロール位置を設定
 *
 * @param {string} headerSelector - ヘッダーのセレクタ
 */
export const setScrollPadding = (headerSelector = ".l-header") => {
  const headerHeight = getHeaderHeight(headerSelector);
  document.documentElement.style.scrollPaddingTop = `${headerHeight}px`;
};

/**
 * 要素の表示/非表示を切り替え
 *
 * @param {HTMLElement} element - 対象要素
 * @param {boolean} show - trueで表示、falseで非表示
 * @param {string} className - トグルするクラス名（デフォルト: 'is-show'）
 */
export const toggleVisibility = (element, show, className = "is-show") => {
  if (!element) return;

  if (show) {
    element.classList.add(className);
  } else {
    element.classList.remove(className);
  }
};

/**
 * 要素の有効/無効を切り替え
 *
 * @param {HTMLElement} element - 対象要素
 * @param {boolean} active - trueで有効、falseで無効
 * @param {string} className - トグルするクラス名（デフォルト: 'is-active'）
 */
export const toggleActive = (element, active, className = "is-active") => {
  if (!element) return;

  if (active) {
    element.classList.add(className);
  } else {
    element.classList.remove(className);
  }
};

/**
 * デバウンス関数
 *
 * 連続して呼ばれる関数の実行を制限
 *
 * @param {Function} func - 実行する関数
 * @param {number} wait - 待機時間（ミリ秒）
 * @returns {Function} デバウンスされた関数
 *
 * @example
 * const handleResize = debounce(() => {
 * }, 250);
 *
 * window.addEventListener('resize', handleResize);
 */
export const debounce = (func, wait = 250) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * スロットル関数
 *
 * 一定時間内に一度だけ関数を実行
 *
 * @param {Function} func - 実行する関数
 * @param {number} limit - 制限時間（ミリ秒）
 * @returns {Function} スロットルされた関数
 *
 * @example
 * const handleScroll = throttle(() => {
 * }, 100);
 *
 * window.addEventListener('scroll', handleScroll);
 */
export const throttle = (func, limit = 100) => {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
};

/**
 * 要素が存在するかチェック
 *
 * @param {string} selector - セレクタ
 * @returns {boolean} 要素が存在する場合true
 */
export const exists = (selector) => {
  return document.querySelector(selector) !== null;
};

/**
 * タッチデバイス判定
 *
 * @returns {boolean} タッチデバイスの場合true
 */
export const isTouchDevice = () => {
  return "ontouchstart" in window || navigator.maxTouchPoints > 0;
};

/**
 * ブレークポイント変更を監視
 *
 * メディアクエリの変更を監視し、ブレークポイントを跨いだ時にコールバックを実行
 *
 * @param {string} breakpoint - メディアクエリ（例: "(min-width: 768px)"）
 * @param {Function} callback - ブレークポイント変更時に実行する関数（MediaQueryListEventを受け取る）
 * @returns {Function} クリーンアップ関数（イベントリスナーを削除）
 *
 * @example
 * // PC/SP切り替え時に処理を実行
 * const cleanup = watchBreakpoint("(min-width: 768px)", (e) => {
 *   if (e.matches) {
 *     // PC size
 *     initPCFeatures();
 *   } else {
 *     // SP size
 *     destroyPCFeatures();
 *   }
 * });
 *
 * // コンポーネント破棄時にクリーンアップ
 * cleanup();
 */
export const watchBreakpoint = (breakpoint, callback) => {
  const mediaQuery = window.matchMedia(breakpoint);

  const handleChange = (e) => {
    callback(e);
  };

  mediaQuery.addEventListener("change", handleChange);

  // クリーンアップ関数を返す
  return () => {
    mediaQuery.removeEventListener("change", handleChange);
  };
};
