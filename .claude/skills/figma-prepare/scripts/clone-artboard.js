/**
 * clone-artboard.js
 *
 * Chrome DevTools MCP evaluate_script 用テンプレート。
 * アートボード（トップレベル FRAME）を深い複製し、右隣に配置する。
 * 複製後に元→複製の ID マッピングテーブルを生成する。
 *
 * Usage:
 *   1. Read this file
 *   2. Replace __SOURCE_NODE_ID__ with the target artboard ID (e.g. "1:4")
 *   3. Pass the resulting string to mcp__chrome-devtools__evaluate_script
 *      の function パラメータとして渡す
 *
 * Output (object — MCP が自動シリアライズ):
 *   {
 *     success: true,
 *     clone: { id, name, x, y, width, height },
 *     mapping: { "originalId": "cloneId", ... },
 *     total: N,
 *     nameMatchRate: 0.0-1.0
 *   }
 *
 * Constraints:
 *   - node.clone() creates a deep copy with new IDs
 *   - Children order is preserved → index-based mapping is accurate
 *   - Mapping is validated by name match rate (≥95% = OK)
 */
() => {
  const sourceNodeId = "__SOURCE_NODE_ID__";
  const GAP = 100; // px gap between original and clone

  // 1. Get source artboard
  const source = figma.getNodeById(sourceNodeId);
  if (!source) {
    return { success: false, error: `Source node "${sourceNodeId}" not found` };
  }

  if (source.type !== "FRAME") {
    return { success: false, error: `Source node is "${source.type}", expected "FRAME"` };
  }

  // 2. Deep clone
  const clone = source.clone();
  clone.name = `${source.name} [prepared]`;
  clone.x = source.x + source.width + GAP;
  clone.y = source.y;

  // 3. Append to current page
  figma.currentPage.appendChild(clone);

  // 4. Build ID mapping via parallel DFS traversal
  const mapping = {};
  let total = 0;
  let nameMatches = 0;

  function buildMapping(origNode, cloneNode) {
    mapping[origNode.id] = cloneNode.id;
    total++;
    if (origNode.name === cloneNode.name || cloneNode.name === `${origNode.name} [prepared]`) {
      nameMatches++;
    }

    // Recurse into children if both have children
    if ("children" in origNode && "children" in cloneNode) {
      const origChildren = origNode.children;
      const cloneChildren = cloneNode.children;
      const len = Math.min(origChildren.length, cloneChildren.length);
      for (let i = 0; i < len; i++) {
        buildMapping(origChildren[i], cloneChildren[i]);
      }
    }
  }

  buildMapping(source, clone);

  const nameMatchRate = total > 0 ? nameMatches / total : 0;

  // 5. Return result (MCP auto-serializes)
  const result = {
    success: true,
    clone: {
      id: clone.id,
      name: clone.name,
      x: clone.x,
      y: clone.y,
      width: clone.width,
      height: clone.height,
    },
    mapping,
    total,
    nameMatchRate: Math.round(nameMatchRate * 1000) / 1000,
  };

  if (nameMatchRate < 0.95) {
    result.warning = `Name match rate ${(nameMatchRate * 100).toFixed(1)}% is below 95% threshold. Mapping may be inaccurate.`;
  }

  return result;
}
