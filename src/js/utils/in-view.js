/**
 * Intersection Observer Utility
 *
 * パフォーマンスに優れたビューポート検出ユーティリティ
 * 要素がビューポートに入った・出た時の処理を簡単に実装できます
 */

/**
 * InView検出のデフォルト設定
 */
const DEFAULT_OPTIONS = {
  threshold: 0.1,
  rootMargin: "0px",
  once: false,
  className: "is-in-view",
  onEnter: null,
  onLeave: null,
  onProgress: null,
};

/**
 * Intersection Observerのインスタンスキャッシュ
 * 同じ設定のObserverを再利用してパフォーマンスを最適化
 * @private
 */
const observerCache = new Map();

/**
 * Intersection Observerの設定からキーを生成
 * @private
 * @param {Object} options - Observer設定
 * @returns {string} キャッシュキー
 */
function getObserverKey(options) {
  const { threshold, rootMargin } = options;
  return `${threshold}-${rootMargin}`;
}

/**
 * 要素がビューポートに入った・出た時の処理を設定
 *
 * @param {string|Element|NodeList|Element[]} target - 対象要素（セレクタ、Element、NodeList、配列）
 * @param {Object} options - 設定オプション
 * @param {number|number[]} [options.threshold=0.1] - 可視率の閾値（0.0～1.0）
 * @param {string} [options.rootMargin="0px"] - ルート要素のマージン（CSS記法）
 * @param {boolean} [options.once=false] - 一度だけ実行するか
 * @param {string} [options.className="is-in-view"] - 自動付与するクラス名
 * @param {Function} [options.onEnter] - 要素が入った時のコールバック (element, entry) => void
 * @param {Function} [options.onLeave] - 要素が出た時のコールバック (element, entry) => void
 * @param {Function} [options.onProgress] - 可視率変化時のコールバック (element, entry) => void
 * @returns {Object} コントロールオブジェクト { observer, elements, destroy }
 *
 * @example
 * // 基本的な使い方（クラス自動付与）
 * inView('.fade-in-element');
 *
 * @example
 * // カスタムクラス名と一度だけ実行
 * inView('.scroll-animation', {
 *   className: 'is-visible',
 *   once: true
 * });
 *
 * @example
 * // コールバック関数でカスタムアニメーション
 * inView('.custom-animation', {
 *   threshold: 0.5,
 *   onEnter: (element) => {
 *     element.style.transform = 'translateY(0)';
 *     element.style.opacity = '1';
 *   },
 *   onLeave: (element) => {
 *     element.style.transform = 'translateY(20px)';
 *     element.style.opacity = '0';
 *   }
 * });
 *
 * @example
 * // 可視率に応じた処理
 * inView('.progress-bar', {
 *   threshold: [0, 0.25, 0.5, 0.75, 1],
 *   onProgress: (element, entry) => {
 *     const ratio = Math.round(entry.intersectionRatio * 100);
 *     element.style.setProperty('--progress', `${ratio}%`);
 *   }
 * });
 *
 * @example
 * // 複数要素を配列で指定
 * const elements = document.querySelectorAll('.item');
 * const controller = inView(elements, { once: true });
 *
 * // 後でクリーンアップ
 * controller.destroy();
 */
export function inView(target, options = {}) {
  const config = { ...DEFAULT_OPTIONS, ...options };

  // 要素を取得
  let elements;
  if (typeof target === "string") {
    elements = document.querySelectorAll(target);
  } else if (target instanceof Element) {
    elements = [target];
  } else if (target instanceof NodeList || Array.isArray(target)) {
    elements = Array.from(target);
  } else {
    return { observer: null, elements: [], destroy: () => {} };
  }

  if (elements.length === 0) {
    return { observer: null, elements: [], destroy: () => {} };
  }

  // Observerの設定
  const observerOptions = {
    threshold: config.threshold,
    rootMargin: config.rootMargin,
  };

  const observerKey = getObserverKey(observerOptions);

  // 既存のObserverを再利用、なければ新規作成
  let observer = observerCache.get(observerKey);

  if (!observer) {
    observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const element = entry.target;

        // 要素が入った時
        if (entry.isIntersecting) {
          if (config.className) {
            element.classList.add(config.className);
          }

          if (config.onEnter) {
            config.onEnter(element, entry);
          }

          // 一度だけ実行の場合は監視を解除
          if (config.once) {
            observer.unobserve(element);
          }
        }
        // 要素が出た時
        else {
          if (config.className && !config.once) {
            element.classList.remove(config.className);
          }

          if (config.onLeave) {
            config.onLeave(element, entry);
          }
        }

        // 可視率変化時のコールバック
        if (config.onProgress) {
          config.onProgress(element, entry);
        }
      });
    }, observerOptions);

    observerCache.set(observerKey, observer);
  }

  // 要素を監視開始
  elements.forEach((element) => {
    observer.observe(element);
  });

  // コントロールオブジェクトを返す
  return {
    observer,
    elements,
    /**
     * 監視を停止し、リソースをクリーンアップ
     */
    destroy() {
      elements.forEach((element) => {
        observer.unobserve(element);
        if (config.className) {
          element.classList.remove(config.className);
        }
      });
    },
  };
}

/**
 * すべてのObserverインスタンスを破棄
 * ページ遷移時やSPA環境でのクリーンアップに使用
 *
 * @example
 * // ページ離脱時にクリーンアップ
 * window.addEventListener('beforeunload', () => {
 *   destroyAllObservers();
 * });
 */
export function destroyAllObservers() {
  observerCache.forEach((observer) => {
    observer.disconnect();
  });
  observerCache.clear();
}

/**
 * data属性ベースの自動初期化
 * data-in-view属性を持つ要素を自動的に監視
 *
 * @param {Object} options - デフォルト設定をオーバーライド
 * @returns {Object[]} 生成されたコントローラーの配列
 *
 * @example
 * // HTML
 * // <div data-in-view data-threshold="0.5" data-once="true" data-class="is-visible">
 * //   Content
 * // </div>
 *
 * // JavaScript
 * initAutoInView();
 */
export function initAutoInView(options = {}) {
  const elements = document.querySelectorAll("[data-in-view]");
  const controllers = [];

  elements.forEach((element) => {
    const threshold = parseFloat(element.dataset.threshold) || options.threshold;
    const rootMargin = element.dataset.rootMargin || options.rootMargin;
    const once = element.dataset.once === "true" || options.once;
    const className = element.dataset.class || options.className;

    const controller = inView(element, {
      threshold,
      rootMargin,
      once,
      className,
      ...options,
    });

    controllers.push(controller);
  });

  return controllers;
}
