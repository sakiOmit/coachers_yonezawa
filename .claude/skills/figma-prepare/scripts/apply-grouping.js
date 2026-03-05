/**
 * apply-grouping.js
 *
 * Chrome DevTools MCP evaluate_script 用テンプレート。
 * グルーピング計画（JSON）を受け取り、バッチ実行で GROUP ノードを作成し
 * 子要素をグループ化する。
 *
 * Usage:
 *   1. Read this file
 *   2. Replace __GROUPING_PLAN__ with the actual JSON array
 *      e.g. [
 *        {
 *          "node_ids": ["2:55", "2:56", "2:57"],
 *          "suggested_name": "section-hero",
 *          "parent_id": "1:4"
 *        },
 *        ...
 *      ]
 *   3. Replace __BATCH_INFO__ with batch metadata
 *      e.g. "1/3" (batch 1 of 3)
 *   4. Pass the resulting string to mcp__chrome-devtools__evaluate_script
 *      の function パラメータとして渡す
 *
 * Output (object — MCP が自動シリアライズ):
 *   {
 *     success: true,
 *     applied: N,
 *     skipped: N,
 *     errors: [{ index, error }],
 *     wrappers: [{ id, name, childCount }],
 *     total: N,
 *     batch: "1/3"
 *   }
 *
 * Algorithm per candidate:
 *   1. Validate all node_ids exist and share the same parent
 *   2. Use figma.group() to create a GROUP node (no size constraints)
 *   3. Set group name from suggested_name
 *
 * Why GROUP instead of FRAME:
 *   - GROUP has no own dimensions — it auto-fits to children bounding box
 *   - No risk of fixed height clipping content
 *   - Both GROUP and FRAME map to div/section in code, so no practical difference
 *   - Simpler: no need for manual bbox calculation, position adjustment, or resize
 *
 * Constraints:
 *   - Max 50 candidates per batch (timeout prevention)
 *   - Errors are per-candidate skip (batch continues)
 *   - Requires Figma Plugin API (figma.getNodeById, figma.group, etc.)
 */
() => {
  const groupingPlan = __GROUPING_PLAN__;
  const batchInfo = "__BATCH_INFO__";

  let applied = 0;
  let skipped = 0;
  const errors = [];
  const wrappers = [];

  for (let idx = 0; idx < groupingPlan.length; idx++) {
    const candidate = groupingPlan[idx];
    try {
      const nodeIds = candidate.node_ids || [];
      const name = candidate.suggested_name || "group";

      if (nodeIds.length < 2) {
        errors.push({ index: idx, error: "need at least 2 node_ids" });
        skipped++;
        continue;
      }

      // 1. Resolve all child nodes
      const childNodes = [];
      let allFound = true;
      for (const nid of nodeIds) {
        const node = figma.getNodeById(nid);
        if (!node) {
          errors.push({ index: idx, error: `node ${nid} not found` });
          allFound = false;
          break;
        }
        childNodes.push(node);
      }
      if (!allFound) {
        skipped++;
        continue;
      }

      // 2. Verify all children share the same parent
      const parent = childNodes[0].parent;
      if (!parent) {
        errors.push({ index: idx, error: "first child has no parent" });
        skipped++;
        continue;
      }
      const sameParent = childNodes.every((n) => n.parent && n.parent.id === parent.id);
      if (!sameParent) {
        errors.push({ index: idx, error: "children have different parents" });
        skipped++;
        continue;
      }

      // 3. Create GROUP using figma.group()
      // figma.group() automatically:
      //   - Creates a GROUP node wrapping the given nodes
      //   - Preserves children positions (no coordinate conversion needed)
      //   - Auto-sizes to bounding box of children (no fixed dimensions)
      //   - Maintains z-order of children within the parent
      const group = figma.group(childNodes, parent);
      group.name = name;

      wrappers.push({
        id: group.id,
        name: group.name,
        childCount: group.children.length,
      });
      applied++;
    } catch (e) {
      errors.push({ index: idx, error: e.message });
      skipped++;
    }
  }

  return {
    success: applied > 0 || errors.length === 0,
    applied,
    skipped,
    errors,
    wrappers,
    total: groupingPlan.length,
    batch: batchInfo,
  };
}
