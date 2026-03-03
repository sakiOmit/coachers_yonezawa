/**
 * メインJavaScriptエントリーポイント
 * 全ページ共通の初期化処理
 */

// コンポーネント
import { initHamburgerMenu } from "./components/hamburger-menu.js";
import { initHeaderScroll } from "./components/header-scroll.js";

/**
 * ヘッダー高さを CSS カスタムプロパティにセット（リフロー対策版）
 * ResizeObserver でヘッダーのサイズ変更を監視し、パフォーマンスを最適化
 */
function initHeaderHeightObserver() {
  const header = document.querySelector(".l-header");
  if (!header) return;

  // ResizeObserver でヘッダーのサイズ変更を監視
  const resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const height =
        entry.borderBoxSize?.[0]?.blockSize || entry.contentRect.height;

      document.documentElement.style.setProperty(
        "--header-height",
        `${height}px`,
      );
    }
  });

  resizeObserver.observe(header);
}

/**
 * DOM読み込み完了後の初期化
 */
document.addEventListener("DOMContentLoaded", () => {
  initHeaderHeightObserver();

  // 共通UI初期化
  initHeaderScroll();
  initHamburgerMenu();
  initSmoothScroll();
});

/**
 * スムーススクロール
 */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", (e) => {
      const href = anchor.getAttribute("href");
      if (href === "#") return;

      const target = document.querySelector(href);
      if (!target) return;

      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth" });
    });
  });
}
