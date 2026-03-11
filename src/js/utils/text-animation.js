/**
 * Text Animation Utility
 * テキストを文字単位で分割し、アニメーション用にspanでラップする
 */

/**
 * テキストを文字ごとにspanでラップする
 * @param {HTMLElement} element - 対象要素
 * @param {Object} options - オプション
 * @param {boolean} options.preserveSpaces - スペースを保持するか（デフォルト: true）
 * @returns {HTMLElement[]} - ラップされた文字のspan要素配列
 */
export function splitTextToChars(element, options = {}) {
  const { preserveSpaces = true } = options;

  if (!element) {
    return [];
  }

  // オリジナルのテキストをaria-labelに保存（アクセシビリティ）
  const originalText = element.textContent;
  element.setAttribute("aria-label", originalText);

  // 子ノードを取得
  const childNodes = Array.from(element.childNodes);

  // 結果を格納する配列
  const result = [];
  let charIndex = 0;

  // 各ノードを処理
  childNodes.forEach(node => {
    if (node.nodeType === Node.TEXT_NODE) {
      // テキストノードの場合、文字ごとに分割
      const text = node.textContent;
      const chars = Array.from(text);

      chars.forEach(char => {
        if (char === " " && !preserveSpaces) {
          result.push(" ");
        } else if (char === " ") {
          result.push(`<span class="char" style="display: inline-block; opacity: 0;" data-char-index="${charIndex}">&nbsp;</span>`);
          charIndex++;
        } else {
          result.push(`<span class="char" style="display: inline-block; opacity: 0;" data-char-index="${charIndex}">${char}</span>`);
          charIndex++;
        }
      });
    } else if (node.nodeName === "BR") {
      // <br>タグの場合、そのまま保持
      result.push("<br>");
    }
  });

  // 元の要素のHTMLを置き換え
  element.innerHTML = result.join("");

  // ラップされたspan要素を返す
  return Array.from(element.querySelectorAll(".char"));
}

/**
 * 文字を順番にフェードインさせる
 * @param {HTMLElement[]} chars - 文字のspan要素配列
 * @param {Object} options - アニメーションオプション
 * @param {number} options.stagger - 各文字の遅延時間（ミリ秒）
 * @param {number} options.duration - アニメーション時間（ミリ秒）
 */
export function animateChars(chars, options = {}) {
  const { stagger = 50, duration = 500 } = options;

  // prefers-reduced-motion対応
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (prefersReducedMotion) {
    // モーション軽減設定時は即座に表示
    chars.forEach(char => {
      char.style.opacity = "1";
      char.style.transition = "none";
    });
    return;
  }

  // 各文字を順番にフェードイン
  chars.forEach((char, index) => {
    setTimeout(() => {
      char.style.transition = `opacity ${duration}ms ease-out`;
      char.style.opacity = "1";
    }, index * stagger);
  });
}
