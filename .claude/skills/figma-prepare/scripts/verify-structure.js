/**
 * verify-structure.js
 *
 * Chrome DevTools MCP evaluate_script 用テンプレート。
 * クローンアートボードのツリーを DFS で走査し、
 * リネームマップの期待名と実際の名前を比較して構造 diff を生成する。
 *
 * Usage:
 *   1. Read this file
 *   2. Replace __CLONE_NODE_ID__ with the clone artboard ID (e.g. "23:128")
 *   3. Replace __EXPECTED_NAMES__ with the expected name map
 *      e.g. {"23:130": "hero-background", "23:131": "hero-title", ...}
 *      Keys are clone-side node IDs, values are expected names after rename.
 *   4. Pass the resulting string to mcp__chrome-devtools__evaluate_script
 *      の function パラメータとして渡す
 *
 * Output (object — MCP が自動シリアライズ):
 *   {
 *     success: true,
 *     total: N,          // 検証対象ノード数
 *     matched: N,        // 名前一致
 *     mismatched: [],    // [{nodeId, expected, actual}]
 *     missing: [],       // クローン内に見つからないID
 *     matchRate: 0.0-1.0
 *   }
 *
 * Constraints:
 *   - Read-only (no mutations)
 *   - Errors are per-node skip (batch continues)
 */
() => {
  const cloneNodeId = "__CLONE_NODE_ID__";
  const expectedNames = __EXPECTED_NAMES__;

  // 1. Get clone root
  const cloneRoot = figma.getNodeById(cloneNodeId);
  if (!cloneRoot) {
    return { success: false, error: `Clone node "${cloneNodeId}" not found` };
  }

  // 2. Build a set of all node IDs in the clone tree via DFS
  const cloneNodeIds = new Set();
  function collectIds(node) {
    cloneNodeIds.add(node.id);
    if ("children" in node) {
      for (const child of node.children) {
        collectIds(child);
      }
    }
  }
  collectIds(cloneRoot);

  // 3. Compare expected names against actual names
  let matched = 0;
  const mismatched = [];
  const missing = [];
  const entries = Object.entries(expectedNames);

  for (const [nodeId, expectedName] of entries) {
    try {
      if (!cloneNodeIds.has(nodeId)) {
        missing.push(nodeId);
        continue;
      }

      const node = figma.getNodeById(nodeId);
      if (!node) {
        missing.push(nodeId);
        continue;
      }

      if (node.name === expectedName) {
        matched++;
      } else {
        mismatched.push({
          nodeId,
          expected: expectedName,
          actual: node.name,
        });
      }
    } catch (e) {
      mismatched.push({
        nodeId,
        expected: expectedName,
        actual: `[error: ${e.message}]`,
      });
    }
  }

  const total = entries.length;
  const matchRate = total > 0 ? Math.round((matched / total) * 1000) / 1000 : 0;

  return {
    success: true,
    total,
    matched,
    mismatched,
    missing,
    matchRate,
  };
}
