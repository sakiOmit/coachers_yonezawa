/**
 * Responsive Utilities
 *
 * Media query-based animation controllers and responsive helpers
 */

/**
 * Responsive Animation Controller
 *
 * Manages media query-based initialization and destruction of animations
 *
 * @example
 * const controller = new ResponsiveAnimation(
 *   '(min-width: 768px)',
 *   () => { // PC init },
 *   () => { // PC destroy }
 * );
 * controller.start();
 */
export class ResponsiveAnimation {
  /**
   * @param {string} mediaQuery - Media query string
   * @param {Function} initFn - Function to call when media query matches
   * @param {Function} destroyFn - Function to call when media query no longer matches
   */
  constructor(mediaQuery, initFn, destroyFn) {
    this.mediaQuery = window.matchMedia(mediaQuery);
    this.initFn = initFn;
    this.destroyFn = destroyFn;
    this.isInitialized = false;

    this.handleChange = this.handleChange.bind(this);
  }

  /**
   * Handle media query changes
   *
   * @param {MediaQueryListEvent} e - Media query event
   */
  handleChange(e) {
    if (e.matches && !this.isInitialized) {
      this.initFn();
      this.isInitialized = true;
    } else if (!e.matches && this.isInitialized) {
      this.destroyFn();
      this.isInitialized = false;
    }
  }

  /**
   * Start listening to media query changes
   */
  start() {
    // Check initial state
    if (this.mediaQuery.matches) {
      this.initFn();
      this.isInitialized = true;
    }

    // Listen for changes
    this.mediaQuery.addEventListener("change", this.handleChange);
  }

  /**
   * Stop listening and cleanup
   */
  stop() {
    this.mediaQuery.removeEventListener("change", this.handleChange);

    if (this.isInitialized) {
      this.destroyFn();
      this.isInitialized = false;
    }
  }

  /**
   * Get current media query state
   *
   * @returns {boolean} True if media query matches
   */
  matches() {
    return this.mediaQuery.matches;
  }
}

/**
 * Create a responsive controller that switches between PC and mobile animations
 *
 * @param {Object} config - Configuration object
 * @param {string} config.breakpoint - Breakpoint in pixels (default: 767)
 * @param {Function} config.pcInit - PC initialization function
 * @param {Function} config.pcDestroy - PC destruction function
 * @param {Function} config.mobileInit - Mobile initialization function
 * @param {Function} config.mobileDestroy - Mobile destruction function
 * @returns {Object} Controller object with start/stop methods
 */
export function createResponsiveController(config = {}) {
  const {
    breakpoint = 767,
    pcInit = () => {},
    pcDestroy = () => {},
    mobileInit = () => {},
    mobileDestroy = () => {},
  } = config;

  const pcController = new ResponsiveAnimation(
    `(min-width: ${breakpoint + 1}px)`,
    pcInit,
    () => {
      pcDestroy();
      mobileInit();
    },
  );

  const mobileController = new ResponsiveAnimation(
    `(max-width: ${breakpoint}px)`,
    mobileInit,
    () => {
      mobileDestroy();
      pcInit();
    },
  );

  return {
    start() {
      // Only start one controller based on initial state
      if (window.matchMedia(`(min-width: ${breakpoint + 1}px)`).matches) {
        pcController.start();
      } else {
        mobileController.start();
      }
    },
    stop() {
      pcController.stop();
      mobileController.stop();
    },
    pcController,
    mobileController,
  };
}
