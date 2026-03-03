/**
 * Animation Utilities
 *
 * Reusable animation functions and helpers
 */

import { gsap, ANIMATION_CONFIG } from "../lib/gsap-config.js";

/**
 * Check if user prefers reduced motion
 *
 * @returns {boolean} True if reduced motion is preferred
 */
export function shouldReduceMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Check if GSAP and required plugins are loaded
 *
 * @param {string[]} plugins - Array of plugin names to check
 * @returns {boolean} True if all plugins are loaded
 */
export function checkGSAP(plugins = []) {
  if (typeof gsap === "undefined") {
    return false;
  }

  for (const plugin of plugins) {
    if (typeof window[plugin] === "undefined") {
      return false;
    }
  }

  return true;
}

/**
 * Slide up reveal animation using clip-path
 *
 * @param {Element|string} element - Target element or selector
 * @param {Object} options - Animation options
 * @returns {gsap.core.Timeline} GSAP timeline
 */
export function slideUpReveal(element, options = {}) {
  const {
    duration = ANIMATION_CONFIG.durations.slow,
    ease = ANIMATION_CONFIG.easing.powerOut,
    onComplete,
    delay = 0,
  } = options;

  return gsap.fromTo(
    element,
    { clipPath: "inset(100% 0 0 0)" },
    {
      clipPath: "inset(0% 0 0 0)",
      duration,
      ease,
      delay,
      onComplete,
    },
  );
}

/**
 * Create a mask transition controller for image cycling
 *
 * @param {string} selector - Selector for the mask group container
 * @param {Object} options - Configuration options
 * @returns {Object} Controller object with init/destroy methods
 */
export function createMaskTransitionController(selector, options = {}) {
  const {
    displayDuration = 5000,
    animDuration = 1.2,
    ease = ANIMATION_CONFIG.easing.powerOut,
  } = options;

  const maskImages = document.querySelectorAll(selector);
  if (!maskImages.length) return null;

  // Group images by mask-group and mask-order
  const groups = {};
  maskImages.forEach((image) => {
    const group = image.dataset.maskGroup;
    const order = parseInt(image.dataset.maskOrder, 10);

    if (!groups[group]) {
      groups[group] = {};
    }
    if (!groups[group][order]) {
      groups[group][order] = [];
    }
    groups[group][order].push(image);
  });

  // Sort orders within each group
  const sortedGroups = {};
  Object.keys(groups).forEach((groupKey) => {
    const orders = Object.keys(groups[groupKey])
      .map((o) => parseInt(o, 10))
      .sort((a, b) => a - b);
    sortedGroups[groupKey] = orders.map((order) => groups[groupKey][order]);
  });

  const groupIntervals = {};
  const groupControllers = {};

  const initializeGroups = () => {
    Object.keys(sortedGroups).forEach((groupKey) => {
      const orderGroups = sortedGroups[groupKey];
      if (orderGroups.length <= 1) return;

      // Clear all properties first
      orderGroups.forEach((orderGroup) => {
        orderGroup.forEach((image) => {
          gsap.set(image, { clearProps: "clipPath,zIndex" });
        });
      });

      // Set initial state for each order group
      orderGroups.forEach((orderGroup, orderIndex) => {
        orderGroup.forEach((image) => {
          const img = image.querySelector("img");
          if (img) {
            gsap.set(img, { opacity: 1 });
          }

          if (orderIndex === 0) {
            gsap.set(image, { clipPath: "inset(0% 0 0 0)", zIndex: 1 });
          } else {
            gsap.set(image, { clipPath: "inset(100% 0 0 0)", zIndex: 0 });
          }
        });
      });

      // Create controller for this group
      const controller = {
        currentOrderIndex: 0,
        orderGroups: orderGroups,
        change: function () {
          const currentOrderGroup = this.orderGroups[this.currentOrderIndex];
          const nextOrderIndex =
            (this.currentOrderIndex + 1) % this.orderGroups.length;
          const nextOrderGroup = this.orderGroups[nextOrderIndex];

          currentOrderGroup.forEach((image) => {
            gsap.set(image, { zIndex: 1 });
          });
          nextOrderGroup.forEach((image) => {
            gsap.set(image, { zIndex: 2 });
          });

          nextOrderGroup.forEach((image, index) => {
            gsap.fromTo(
              image,
              { clipPath: "inset(100% 0 0 0)" },
              {
                clipPath: "inset(0% 0 0 0)",
                duration: animDuration,
                ease: ease,
                onComplete:
                  index === nextOrderGroup.length - 1
                    ? () => {
                      currentOrderGroup.forEach((img) => {
                        gsap.set(img, { zIndex: 0 });
                      });
                    }
                    : undefined,
              },
            );
          });

          this.currentOrderIndex = nextOrderIndex;
        },
      };

      groupControllers[groupKey] = controller;
    });
  };

  /**
   * Initialize and start the mask transition
   */
  function init() {
    if (!checkGSAP()) return;

    initializeGroups();

    const groupKeys = Object.keys(groupControllers);

    // Immediately show first transition for all groups
    groupKeys.forEach((groupKey) => {
      const controller = groupControllers[groupKey];
      const orderGroups = controller.orderGroups;

      if (orderGroups.length <= 1) return;

      const currentOrderGroup = orderGroups[0];
      const nextOrderGroup = orderGroups[1];

      currentOrderGroup.forEach((image) => {
        gsap.set(image, { zIndex: 1 });
      });
      nextOrderGroup.forEach((image) => {
        gsap.set(image, { zIndex: 2 });
      });

      nextOrderGroup.forEach((image, index) => {
        gsap.fromTo(
          image,
          { clipPath: "inset(100% 0 0 0)" },
          {
            clipPath: "inset(0% 0 0 0)",
            duration: animDuration,
            ease: ease,
            onComplete:
              index === nextOrderGroup.length - 1
                ? () => {
                  currentOrderGroup.forEach((img) => {
                    gsap.set(img, { zIndex: 0 });
                  });
                }
                : undefined,
          },
        );
      });

      controller.currentOrderIndex = 1;
    });

    // Start intervals for all groups
    groupKeys.forEach((groupKey) => {
      const controller = groupControllers[groupKey];
      const intervalId = setInterval(
        () => controller.change(),
        displayDuration,
      );
      groupIntervals[groupKey] = intervalId;
    });
  }

  /**
   * Destroy the mask transition
   */
  function destroy() {
    Object.keys(groupIntervals).forEach((groupKey) => {
      clearInterval(groupIntervals[groupKey]);
    });

    maskImages.forEach((image) => {
      gsap.set(image, { clipPath: "inset(0% 0 0 0)", zIndex: "" });
    });
  }

  return {
    init,
    destroy,
  };
}

/**
 * Split text into spans for character-by-character animation
 *
 * @param {Element|string} element - Target element or selector
 * @returns {Element[]} Array of span elements
 */
export function splitTextToSpans(element) {
  const target =
    typeof element === "string" ? document.querySelector(element) : element;
  if (!target) return [];

  const text = target.textContent;
  const spans = text.split("").map((char) => {
    const span = document.createElement("span");
    span.textContent = char === " " ? "\u00A0" : char; // Non-breaking space
    span.style.display = "inline-block";
    return span;
  });

  target.textContent = "";
  spans.forEach((span) => target.appendChild(span));

  return spans;
}
