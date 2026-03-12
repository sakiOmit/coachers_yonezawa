/**
 * Scroll Control Utilities
 *
 * スクロールの有効化/無効化、スムーススクロール用ユーティリティ
 */

/**
 * スクロールを無効化
 * body要素にクラスを追加してスクロールを防止
 */
export function disableScroll() {
  document.body.classList.add("is-scroll-locked");
}

/**
 * スクロールを有効化
 * body要素からクラスを削除してスクロールを許可
 */
export function enableScroll() {
  document.body.classList.remove("is-scroll-locked");
}

/**
 * スクロール状態をトグル
 *
 * @param {boolean} enable - trueで有効化、falseで無効化
 */
export function toggleScroll(enable) {
  if (enable) {
    enableScroll();
  } else {
    disableScroll();
  }
}

/**
 * ページトップにスクロール
 *
 * @param {Object} options - スクロールオプション
 * @param {boolean} options.immediate - trueで即座に移動（アニメーションなし）
 */
export function scrollToTop(options = {}) {
  const { immediate = false } = options;

  if (immediate) {
    window.scrollTo({ top: 0, behavior: "instant" });
  } else {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

/**
 * 指定要素にスクロール
 *
 * @param {Element|string} target - 対象要素またはCSSセレクタ
 * @param {Object} options - スクロールオプション
 * @param {number} options.offset - オフセット（ヘッダー高さ分など）
 */
export function scrollToElement(target, options = {}) {
  const { offset = 0 } = options;
  const element =
    typeof target === "string" ? document.querySelector(target) : target;

  if (element) {
    const elementPosition =
      element.getBoundingClientRect().top + window.pageYOffset;
    const offsetPosition = elementPosition + offset;

    window.scrollTo({
      top: offsetPosition,
      behavior: "smooth",
    });
  }
}

/**
 * スクロールロック用CSS
 *
 * 以下のCSSをグローバルに追加する必要があります:
 *
 * body.is-scroll-locked {
 *   overflow: hidden;
 *   position: fixed;
 *   width: 100%;
 *   height: 100%;
 * }
 */
