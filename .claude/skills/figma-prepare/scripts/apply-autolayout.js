/**
 * apply-autolayout.js
 *
 * Chrome DevTools MCP evaluate_script 用テンプレート。
 * Auto Layout 計画（JSON）を受け取り、バッチ実行で
 * layoutMode / itemSpacing / padding / counterAxisAlignItems を設定する。
 *
 * Usage:
 *   1. Read this file
 *   2. Replace __AUTOLAYOUT_PLAN__ with the actual JSON array
 *      e.g. [
 *        {
 *          "node_id": "2:55",
 *          "direction": "VERTICAL",
 *          "gap": 24,
 *          "padding": { "top": 16, "right": 16, "bottom": 16, "left": 16 },
 *          "primary_axis_align": "MIN",
 *          "counter_axis_align": "CENTER",
 *          "confidence": "high"
 *        },
 *        ...
 *      ]
 *   3. Replace __BATCH_INFO__ with batch metadata
 *      e.g. "1/3" (batch 1 of 3)
 *   4. Replace __MIN_CONFIDENCE__ with minimum confidence to apply
 *      e.g. "medium" (apply high + medium, skip low)
 *   5. Pass the resulting string to mcp__chrome-devtools__evaluate_script
 *      の function パラメータとして渡す
 *
 * Output (object — MCP が自動シリアライズ):
 *   {
 *     success: true,
 *     applied: N,
 *     skipped: N,
 *     errors: [{ nodeId, error }],
 *     total: N,
 *     batch: "1/3"
 *   }
 *
 * Constraints:
 *   - Max 50 nodes per batch (timeout prevention)
 *   - Errors are per-node skip (batch continues)
 *   - Only applies to FRAME nodes (INSTANCE/COMPONENT are read-only in Plugin API)
 *   - Confidence filtering: skip entries below min_confidence
 */
() => {
  const autolayoutPlan = __AUTOLAYOUT_PLAN__;
  const batchInfo = "__BATCH_INFO__";
  const minConfidence = "__MIN_CONFIDENCE__";

  // Confidence ranking: exact > high > medium > low
  const confidenceRank = { exact: 4, high: 3, medium: 2, low: 1 };
  const minRank = confidenceRank[minConfidence] || 2; // default: medium

  let applied = 0;
  let skipped = 0;
  const errors = [];

  for (const entry of autolayoutPlan) {
    try {
      const nodeId = entry.node_id;
      const confidence = entry.confidence || "medium";

      // Skip low-confidence entries if below threshold
      if ((confidenceRank[confidence] || 0) < minRank) {
        skipped++;
        continue;
      }

      const node = figma.getNodeById(nodeId);
      if (!node) {
        errors.push({ nodeId, error: "not found" });
        skipped++;
        continue;
      }

      // Auto Layout can only be set on FRAME nodes
      // INSTANCE/COMPONENT are typically read-only for layout changes
      if (node.type !== "FRAME") {
        errors.push({ nodeId, error: `type ${node.type} — only FRAME supported for layout changes` });
        skipped++;
        continue;
      }

      // Direction: HORIZONTAL, VERTICAL, or WRAP
      const direction = entry.direction;
      if (direction === "WRAP") {
        node.layoutMode = "HORIZONTAL";
        node.layoutWrap = "WRAP";
      } else if (direction === "HORIZONTAL" || direction === "VERTICAL") {
        node.layoutMode = direction;
        node.layoutWrap = "NO_WRAP";
      } else {
        errors.push({ nodeId, error: `unknown direction: ${direction}` });
        skipped++;
        continue;
      }

      // Gap (itemSpacing)
      if (typeof entry.gap === "number") {
        node.itemSpacing = Math.max(0, entry.gap);
      }

      // Padding
      const pad = entry.padding || {};
      if (typeof pad.top === "number") node.paddingTop = Math.max(0, pad.top);
      if (typeof pad.right === "number") node.paddingRight = Math.max(0, pad.right);
      if (typeof pad.bottom === "number") node.paddingBottom = Math.max(0, pad.bottom);
      if (typeof pad.left === "number") node.paddingLeft = Math.max(0, pad.left);

      // Primary axis alignment
      const primaryAlign = entry.primary_axis_align;
      if (primaryAlign === "SPACE_BETWEEN") {
        node.primaryAxisAlignItems = "SPACE_BETWEEN";
      } else if (primaryAlign === "CENTER") {
        node.primaryAxisAlignItems = "CENTER";
      } else if (primaryAlign === "MAX") {
        node.primaryAxisAlignItems = "MAX";
      } else {
        node.primaryAxisAlignItems = "MIN";
      }

      // Counter axis alignment
      // Issue 104: infer_layout now outputs 'MAX' directly (Figma API terminology)
      // 'END' kept for backward compatibility with any existing plans
      const counterAlign = entry.counter_axis_align;
      if (counterAlign === "CENTER") {
        node.counterAxisAlignItems = "CENTER";
      } else if (counterAlign === "MAX" || counterAlign === "END") {
        node.counterAxisAlignItems = "MAX";
      } else {
        node.counterAxisAlignItems = "MIN";
      }

      // Sizing mode: keep HUG or FIXED based on current state
      // Don't change sizing — preserve original intent

      applied++;
    } catch (e) {
      errors.push({ nodeId: entry.node_id, error: e.message });
      skipped++;
    }
  }

  return {
    success: true,
    applied,
    skipped,
    errors,
    total: autolayoutPlan.length,
    batch: batchInfo,
  };
}
