/**
 * Hamburger Menu with GSAP Animations
 *
 * GSAPを使用した滑らかなハンバーガーメニューの開閉アニメーション
 */

import { gsap } from "gsap";
import { ANIMATION_CONFIG } from "../lib/gsap-config.js";
import { disableScroll, enableScroll } from "../utils/scroll-control.js";

/**
 * ハンバーガーメニューの初期化
 */
export function initHamburgerMenu() {
  const hamburgerButton = document.querySelector(".c-hamburger");
  const hamburgerMenu = document.querySelector(".l-hamburger-menu");
  const overlay = hamburgerMenu?.querySelector(".l-hamburger-menu__overlay");
  const content = hamburgerMenu?.querySelector(".l-hamburger-menu__content");
  const menuItems = hamburgerMenu?.querySelectorAll(".l-hamburger-menu__item");
  const header = document.querySelector(".l-header");

  if (!hamburgerButton || !hamburgerMenu) {
    return;
  }

  // ユーザーのモーション設定をチェック
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  // アニメーション設定
  const config = {
    duration: prefersReducedMotion
      ? 0
      : ANIMATION_CONFIG.durations.medium * 0.8,
    ease: ANIMATION_CONFIG.easing.powerOut,
  };

  // 初期状態の設定
  gsap.set(hamburgerMenu, {
    visibility: "hidden",
  });

  gsap.set(overlay, {
    opacity: 0,
    x: "100%",
  });

  gsap.set(content, {
    x: "100%",
  });

  gsap.set(menuItems, {
    opacity: 0,
    x: 30,
  });

  // アニメーションタイムライン
  let openTimeline = null;
  let closeTimeline = null;

  /**
   * メニューを開く
   */
  const openMenu = () => {
    // 既存のアニメーションをキャンセル
    if (closeTimeline) {
      closeTimeline.kill();
    }

    // クラスとaria属性を即座に更新
    hamburgerButton.classList.add("is-active");
    hamburgerMenu.classList.add("is-active");
    header?.classList.add("is-menu-open");
    hamburgerButton.setAttribute("aria-expanded", "true");
    hamburgerButton.setAttribute("aria-label", "メニューを閉じる");
    hamburgerMenu.setAttribute("aria-hidden", "false");

    // スクロール無効化
    disableScroll();

    // GSAPアニメーション
    openTimeline = gsap.timeline({
      onStart: () => {
        gsap.set(hamburgerMenu, { visibility: "visible" });
      },
    });

    if (prefersReducedMotion) {
      // アクセシビリティ対応: アニメーションなし
      gsap.set(overlay, { opacity: 1, x: "0%" });
      gsap.set(content, { x: "0%" });
      gsap.set(menuItems, { opacity: 1, x: 0 });
    } else {
      // オーバーレイを右から左へスライド
      openTimeline.to(
        overlay,
        {
          opacity: 1,
          x: "0%",
          duration: config.duration,
          ease: config.ease,
        },
        0
      );

      // コンテンツスライドイン
      openTimeline.to(
        content,
        {
          x: "0%",
          duration: config.duration * 1.2,
          ease: config.ease,
        },
        0.15
      );

      // メニューアイテムを順次表示（stagger効果）
      openTimeline.to(
        menuItems,
        {
          opacity: 1,
          x: 0,
          duration: config.duration * 0.8,
          stagger: 0.08,
          ease: config.ease,
        },
        0.3
      );
    }
  };

  /**
   * メニューを閉じる
   */
  const closeMenu = () => {
    // 既存のアニメーションをキャンセル
    if (openTimeline) {
      openTimeline.kill();
    }

    // クラスとaria属性を更新
    hamburgerButton.classList.remove("is-active");
    hamburgerMenu.classList.remove("is-active");
    header?.classList.remove("is-menu-open");
    hamburgerButton.setAttribute("aria-expanded", "false");
    hamburgerButton.setAttribute("aria-label", "メニューを開く");
    hamburgerMenu.setAttribute("aria-hidden", "true");

    // スクロール有効化
    enableScroll();

    // GSAPアニメーション
    closeTimeline = gsap.timeline({
      onComplete: () => {
        gsap.set(hamburgerMenu, { visibility: "hidden" });
      },
    });

    if (prefersReducedMotion) {
      // アクセシビリティ対応: アニメーションなし
      gsap.set(overlay, { opacity: 0, x: "100%" });
      gsap.set(content, { x: "100%" });
      gsap.set(menuItems, { opacity: 0, x: 30 });
      gsap.set(hamburgerMenu, { visibility: "hidden" });
    } else {
      // メニューアイテムをフェードアウト
      closeTimeline.to(
        menuItems,
        {
          opacity: 0,
          x: 30,
          duration: config.duration * 0.6,
          stagger: 0.04,
          ease: ANIMATION_CONFIG.easing.powerIn,
        },
        0
      );

      // コンテンツスライドアウト
      closeTimeline.to(
        content,
        {
          x: "100%",
          duration: config.duration * 1.1,
          ease: ANIMATION_CONFIG.easing.powerIn,
        },
        0.1
      );

      // オーバーレイを左から右へスライドアウト
      closeTimeline.to(
        overlay,
        {
          opacity: 0,
          x: "100%",
          duration: config.duration,
          ease: ANIMATION_CONFIG.easing.powerIn,
        },
        0.2
      );
    }
  };

  // イベントリスナー登録

  // ハンバーガーボタンクリック（トグル）
  hamburgerButton.addEventListener("click", () => {
    const isOpen = hamburgerMenu.classList.contains("is-active");

    if (isOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  // オーバーレイクリックで閉じる
  if (overlay) {
    overlay.addEventListener("click", closeMenu);
  }

  // Escapeキーハンドラー（名前付き関数で定義）
  const handleEscape = (e) => {
    if (e.key === "Escape" && hamburgerMenu.classList.contains("is-active")) {
      closeMenu();
    }
  };

  // ESCキーで閉じる
  document.addEventListener("keydown", handleEscape);

  // メニュー内のリンククリックで閉じる
  const menuLinks = hamburgerMenu.querySelectorAll("a");
  menuLinks.forEach((link) => {
    link.addEventListener("click", () => {
      // 少し遅延を入れてクリック感を出す
      setTimeout(closeMenu, 100);
    });
  });

  const resetMenuImmediate = () => {
    if (openTimeline) openTimeline.kill();
    if (closeTimeline) closeTimeline.kill();

    hamburgerButton.classList.remove("is-active");
    hamburgerMenu.classList.remove("is-active");
    header?.classList.remove("is-menu-open");
    hamburgerButton.setAttribute("aria-expanded", "false");
    hamburgerButton.setAttribute("aria-label", "メニューを開く");
    hamburgerMenu.setAttribute("aria-hidden", "true");

    gsap.set(hamburgerMenu, { visibility: "hidden" });
    gsap.set(overlay, { opacity: 0, x: "100%" });
    gsap.set(content, { x: "100%" });
    gsap.set(menuItems, { opacity: 0, x: 30 });

    enableScroll();
  };

  window.addEventListener("pagehide", () => {
    resetMenuImmediate();
    document.removeEventListener("keydown", handleEscape);
  });

  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      resetMenuImmediate();
      document.addEventListener("keydown", handleEscape);
    }
  });
}
