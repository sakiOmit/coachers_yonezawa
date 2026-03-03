/**
 * Header Scroll Component
 * c-page-headerを越えたときにヘッダーの背景色と文字色を変更
 */

/**
 * ヘッダースクロールの初期化
 */
export function initHeaderScroll() {
  const header = document.querySelector(".l-header");
  // js-hero クラスで統一（トップページの p-top__hero と下層ページの c-page-header 両方に付与）
  const hero = document.querySelector(".js-hero");

  // 必要な要素が存在しない場合は何もしない
  if (!header || !hero) {
    return;
  }

  /**
   * スクロール位置をチェックしてヘッダーの状態を更新
   */
  function checkScroll() {
    const heroBottom = hero.offsetTop + hero.offsetHeight;
    const scrollPosition = window.pageYOffset || document.documentElement.scrollTop;

    if (scrollPosition > heroBottom) {
      header.classList.add("is-scrolled");
    } else {
      header.classList.remove("is-scrolled");
    }
  }

  // スクロールイベントリスナー（名前付き関数で定義）
  let ticking = false;
  const handleScroll = () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        checkScroll();
        ticking = false;
      });
      ticking = true;
    }
  };

  const handleResize = () => {
    checkScroll();
  };

  /**
   * クリーンアップ関数
   */
  function cleanup() {
    window.removeEventListener("scroll", handleScroll);
    window.removeEventListener("resize", handleResize);
  }

  // 初期化
  checkScroll();
  window.addEventListener("scroll", handleScroll);
  window.addEventListener("resize", handleResize);

  // bfcache対応: ページ非表示時にクリーンアップ
  window.addEventListener("pagehide", cleanup);

  // bfcache対応: ページ復帰時に再初期化
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      checkScroll();
      window.addEventListener("scroll", handleScroll);
      window.addEventListener("resize", handleResize);
    }
  });
}
