/**
 * InView Utility - 使用例
 *
 * このファイルは実装例を示すためのものです。
 * 実際のプロジェクトでは、各ページのJSファイルから import して使用してください。
 */

import { inView, initAutoInView, destroyAllObservers } from "./in-view.js";

/**
 * 例1: 基本的なフェードインアニメーション
 * クラスの自動付与のみ
 */
function example1() {
  // CSSで .is-in-view スタイルを定義しておく
  inView(".fade-in-element");
}

/**
 * 例2: カスタムクラス名と一度だけ実行
 */
function example2() {
  inView(".scroll-animation", {
    className: "is-visible",
    once: true, // 一度だけ実行
    threshold: 0.3, // 30%表示で発火
  });
}

/**
 * 例3: コールバック関数でカスタムアニメーション
 */
function example3() {
  inView(".custom-animation", {
    threshold: 0.5,
    onEnter: (element) => {
      element.style.transform = "translateY(0)";
      element.style.opacity = "1";
      console.log("Element entered:", element);
    },
    onLeave: (element) => {
      element.style.transform = "translateY(20px)";
      element.style.opacity = "0";
      console.log("Element left:", element);
    },
  });
}

/**
 * 例4: 段階的なthresholdで可視率に応じた処理
 */
function example4() {
  inView(".progress-bar", {
    threshold: [0, 0.25, 0.5, 0.75, 1],
    onProgress: (element, entry) => {
      const ratio = Math.round(entry.intersectionRatio * 100);
      element.style.setProperty("--progress", `${ratio}%`);
      element.setAttribute("aria-valuenow", ratio);
    },
  });
}

/**
 * 例5: GSAPと組み合わせたアニメーション
 */
function example5() {
  import("../lib/gsap-config.js").then(({ gsap }) => {
    inView(".gsap-animation", {
      threshold: 0.3,
      once: true,
      onEnter: (element) => {
        gsap.from(element, {
          y: 50,
          opacity: 0,
          duration: 0.8,
          ease: "power2.out",
        });
      },
    });
  });
}

/**
 * 例6: 複数要素に対して個別のディレイを設定
 */
function example6() {
  const items = document.querySelectorAll(".stagger-item");

  items.forEach((item, index) => {
    inView(item, {
      threshold: 0.2,
      once: true,
      onEnter: (element) => {
        setTimeout(() => {
          element.classList.add("is-visible");
        }, index * 100); // 100msずつディレイ
      },
    });
  });
}

/**
 * 例7: スクロール進捗バー
 */
function example7() {
  const progressBar = document.querySelector(".scroll-progress");

  if (progressBar) {
    inView("body", {
      threshold: Array.from({ length: 101 }, (_, i) => i / 100), // 0～1まで1%刻み
      onProgress: (element, entry) => {
        const scrolled = entry.intersectionRatio * 100;
        progressBar.style.width = `${scrolled}%`;
      },
    });
  }
}

/**
 * 例8: rootMarginを使った早めのトリガー
 */
function example8() {
  inView(".early-trigger", {
    rootMargin: "100px 0px", // 100px前から検出
    once: true,
    onEnter: (element) => {
      element.classList.add("is-loaded");
    },
  });
}

/**
 * 例9: data属性による自動初期化
 */
function example9() {
  // HTML:
  // <div data-in-view data-threshold="0.5" data-once="true" data-class="is-visible">
  //   Content
  // </div>

  const controllers = initAutoInView({
    // デフォルト設定（data属性で上書き可能）
    threshold: 0.1,
    className: "is-in-view",
    once: false,
  });

  console.log(`${controllers.length} elements initialized`);
}

/**
 * 例10: 手動でのクリーンアップ
 */
function example10() {
  const controller = inView(".temporary-element", {
    onEnter: (element) => {
      element.classList.add("is-visible");
    },
  });

  // 後でクリーンアップが必要な場合
  setTimeout(() => {
    controller.destroy();
    console.log("Observer destroyed");
  }, 10000);
}

/**
 * 例11: ページ遷移時の完全クリーンアップ（SPA向け）
 */
function example11() {
  // ページ離脱前に全Observerを破棄
  window.addEventListener("beforeunload", () => {
    destroyAllObservers();
  });

  // Astro View Transitionsなどでのページ遷移時
  document.addEventListener("astro:before-preparation", () => {
    destroyAllObservers();
  });
}

/**
 * 例12: アニメーションライブラリと組み合わせ（anime.js想定）
 */
function example12() {
  inView(".anime-target", {
    threshold: 0.3,
    once: true,
    onEnter: async (element) => {
      // 動的インポート
      const anime = (await import("animejs")).default;

      anime({
        targets: element,
        translateY: [50, 0],
        opacity: [0, 1],
        duration: 800,
        easing: "easeOutQuad",
      });
    },
  });
}

/**
 * 推奨される実装パターン
 */
function recommendedPattern() {
  // 1. prefers-reduced-motionの確認
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  if (prefersReducedMotion) {
    // アニメーションなしで即座に表示
    document.querySelectorAll(".fade-in-element").forEach((el) => {
      el.classList.add("is-visible");
    });
    return;
  }

  // 2. 通常のアニメーション
  inView(".fade-in-element", {
    threshold: 0.2,
    once: true,
    className: "is-visible",
  });
}

// 初期化（実際のプロジェクトでは不要）
// example1();
// example2();
// recommendedPattern();
