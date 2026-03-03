/**
 * GSAP Configuration
 *
 * Centralized GSAP setup with plugin registration and animation constants
 */

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

// Register plugins
gsap.registerPlugin(ScrollTrigger);

// Global exposure for compatibility
window.gsap = gsap;
window.ScrollTrigger = ScrollTrigger;

/**
 * Animation configuration constants
 *
 * プロジェクト全体で統一されたアニメーション設定
 */
export const ANIMATION_CONFIG = {
  durations: {
    fast: 0.3, // ホバーなど即座に反応
    medium: 0.6, // 標準的なアニメーション
    slow: 1.0, // ゆっくりした演出
    display: 5, // 表示時間（スライダー等）
  },
  easing: {
    // 入り
    easeIn: "power2.in",
    powerIn: "power4.in",
    // 出
    easeOut: "power2.out",
    powerOut: "power4.out",
    // 入り出
    easeInOut: "power2.inOut",
    powerInOut: "power4.inOut",
    // その他
    bounce: "bounce.out",
    elastic: "elastic.out(1, 0.3)",
  },
  // ScrollTriggerのデフォルト設定
  scrollTrigger: {
    start: "top 80%",
    end: "bottom 20%",
    toggleActions: "play none none none",
  },
};

/**
 * フェードインアニメーションの基本設定
 *
 * @param {Element} element - アニメーション対象要素
 * @param {Object} options - カスタムオプション
 * @returns {gsap.core.Tween} GSAPアニメーション
 */
export function createFadeIn(element, options = {}) {
  const defaults = {
    y: 30,
    opacity: 0,
    duration: ANIMATION_CONFIG.durations.medium,
    ease: ANIMATION_CONFIG.easing.easeOut,
  };

  return gsap.from(element, { ...defaults, ...options });
}

/**
 * スクロールトリガー付きフェードイン
 *
 * @param {Element|string} element - 対象要素またはセレクタ
 * @param {Object} options - カスタムオプション
 * @returns {gsap.core.Tween} GSAPアニメーション
 */
export function createScrollFadeIn(element, options = {}) {
  const { triggerOptions = {}, ...animationOptions } = options;

  return gsap.from(element, {
    y: 30,
    opacity: 0,
    duration: ANIMATION_CONFIG.durations.medium,
    ease: ANIMATION_CONFIG.easing.easeOut,
    scrollTrigger: {
      trigger: element,
      ...ANIMATION_CONFIG.scrollTrigger,
      ...triggerOptions,
    },
    ...animationOptions,
  });
}

export { gsap, ScrollTrigger };
