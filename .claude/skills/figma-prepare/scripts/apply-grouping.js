/**
 * apply-grouping.js
 *
 * Chrome DevTools MCP evaluate_script 用テンプレート。
 * グルーピング計画（JSON）を受け取り、バッチ実行でラッパー Frame を作成し
 * 子要素を移動する。
 *
 * Usage:
 *   1. Read this file
 *   2. Replace __GROUPING_PLAN__ with the actual JSON array
 *      e.g. [
 *        {
 *          "node_ids": ["2:55", "2:56", "2:57"],
 *          "suggested_name": "section-hero",
 *          "suggested_wrapper": "section",
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
 *     batch: "1/3"
 *   }
 *
 * Algorithm per candidate:
 *   1. Validate all node_ids exist
 *   2. Compute bounding box union of all children
 *   3. Create wrapper FRAME at bounding box position
 *   4. Insert wrapper into parent at correct z-order (before first child)
 *   5. Move children into wrapper (preserving order)
 *   6. Set wrapper name from suggested_name
 *
 * Constraints:
 *   - Max 50 candidates per batch (timeout prevention)
 *   - Errors are per-candidate skip (batch continues)
 *   - Requires Figma Plugin API (figma.getNodeById, node.appendChild, etc.)
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
      const parentId = candidate.parent_id || "";

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

      // 3. Compute bounding box union
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const node of childNodes) {
        const x = node.absoluteTransform[0][2];
        const y = node.absoluteTransform[1][2];
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x + node.width);
        maxY = Math.max(maxY, y + node.height);
      }

      // 4. Find insertion index (z-order: before first child in parent.children)
      const parentChildren = parent.children;
      let insertIndex = parentChildren.length;
      for (let i = 0; i < parentChildren.length; i++) {
        if (childNodes.some((cn) => cn.id === parentChildren[i].id)) {
          insertIndex = i;
          break;
        }
      }

      // 5. Create wrapper FRAME
      const wrapper = figma.createFrame();
      wrapper.name = name;
      wrapper.resize(maxX - minX, maxY - minY);

      // Position wrapper at the bounding box origin
      // Use parent-relative coordinates
      const parentX = parent.absoluteTransform ? parent.absoluteTransform[0][2] : 0;
      const parentY = parent.absoluteTransform ? parent.absoluteTransform[1][2] : 0;
      wrapper.x = minX - parentX;
      wrapper.y = minY - parentY;

      // Remove default fill (white background)
      wrapper.fills = [];

      // Clip content disabled (don't clip overflowing children)
      wrapper.clipsContent = false;

      // 6. Insert wrapper into parent at correct z-order
      parent.insertChild(insertIndex, wrapper);

      // 7. Move children into wrapper (preserve original order)
      // childNodes are already in document order from parent.children
      const childOrder = childNodes.map((n) => ({ node: n, origX: n.x, origY: n.y }));

      for (const { node, origX, origY } of childOrder) {
        // Convert position to wrapper-relative
        const nodeAbsX = node.absoluteTransform[0][2];
        const nodeAbsY = node.absoluteTransform[1][2];
        const wrapperAbsX = wrapper.absoluteTransform[0][2];
        const wrapperAbsY = wrapper.absoluteTransform[1][2];

        wrapper.appendChild(node);

        // Adjust position relative to wrapper
        node.x = nodeAbsX - wrapperAbsX;
        node.y = nodeAbsY - wrapperAbsY;
      }

      wrappers.push({
        id: wrapper.id,
        name: wrapper.name,
        childCount: wrapper.children.length,
      });
      applied++;
    } catch (e) {
      errors.push({ index: idx, error: e.message });
      skipped++;
    }
  }

  return {
    success: true,
    applied,
    skipped,
    errors,
    wrappers,
    batch: batchInfo,
  };
}
