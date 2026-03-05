/**
 * verify-grouping.js
 *
 * Chrome DevTools MCP evaluate_script 用テンプレート。
 * apply-grouping.js 適用後のクローンアートボードを走査し、
 * ラッパーFRAME の作成・子要素移動・bbox 整合性を検証する。
 *
 * Usage:
 *   1. Read this file
 *   2. Replace __VERIFICATION_PLAN__ with the verification data array
 *      e.g. [
 *        {
 *          "wrapper_id": "23:55",
 *          "expected_name": "section-hero",
 *          "expected_child_ids": ["23:56", "23:57", "23:58"]
 *        },
 *        ...
 *      ]
 *      - wrapper_id: apply-grouping.js 出力の wrappers[].id
 *      - expected_name: グルーピング計画の suggested_name
 *      - expected_child_ids: グルーピング計画の node_ids（クローン側IDに変換済み）
 *   3. Pass the resulting string to mcp__chrome-devtools__evaluate_script
 *      の function パラメータとして渡す
 *
 * Output (object — MCP が自動シリアライズ):
 *   {
 *     success: true,
 *     total: N,              // 検証対象ラッパー数
 *     verified: N,           // 全検証パスしたラッパー数
 *     issues: [],            // [{wrapperId, type, detail}]
 *     missing: [],           // 存在しないラッパーID
 *     matchRate: 0.0-1.0     // verified / total
 *   }
 *
 * 検証項目:
 *   1. ラッパーFRAMEの存在・名前一致
 *   2. 期待される子要素がラッパー内に存在
 *   3. ラッパーbbox ≈ 子要素union bbox（±2px許容）
 *
 * Constraints:
 *   - Read-only (no mutations)
 *   - Errors are per-wrapper skip (batch continues)
 */
() => {
  const verificationPlan = __VERIFICATION_PLAN__;
  const BBOX_TOLERANCE = 2; // px

  let verified = 0;
  const issues = [];
  const missing = [];

  for (const entry of verificationPlan) {
    const wrapperId = entry.wrapper_id;
    const expectedName = entry.expected_name;
    const expectedChildIds = entry.expected_child_ids || [];

    try {
      // 1. Check wrapper existence
      const wrapper = figma.getNodeById(wrapperId);
      if (!wrapper) {
        missing.push(wrapperId);
        continue;
      }

      let hasIssue = false;

      // 2. Check wrapper name
      if (wrapper.name !== expectedName) {
        issues.push({
          wrapperId,
          type: "name_mismatch",
          detail: `expected "${expectedName}", got "${wrapper.name}"`,
        });
        hasIssue = true;
      }

      // 3. Check children are inside wrapper
      const wrapperChildIds = new Set();
      if ("children" in wrapper) {
        for (const child of wrapper.children) {
          wrapperChildIds.add(child.id);
        }
      }

      const missingChildren = [];
      for (const childId of expectedChildIds) {
        if (!wrapperChildIds.has(childId)) {
          missingChildren.push(childId);
        }
      }

      if (missingChildren.length > 0) {
        issues.push({
          wrapperId,
          type: "missing_children",
          detail: `${missingChildren.length}/${expectedChildIds.length} children not found in wrapper`,
          missingChildren,
        });
        hasIssue = true;
      }

      // 4. Check bounding box alignment
      // Wrapper bbox should approximate the union of children bboxes
      if ("children" in wrapper && wrapper.children.length > 0) {
        let childMinX = Infinity,
          childMinY = Infinity,
          childMaxX = -Infinity,
          childMaxY = -Infinity;

        for (const child of wrapper.children) {
          if (!child.absoluteTransform) continue;
          const cx = child.absoluteTransform[0][2];
          const cy = child.absoluteTransform[1][2];
          childMinX = Math.min(childMinX, cx);
          childMinY = Math.min(childMinY, cy);
          childMaxX = Math.max(childMaxX, cx + child.width);
          childMaxY = Math.max(childMaxY, cy + child.height);
        }

        if (childMinX !== Infinity && wrapper.absoluteTransform) {
          const wrapperX = wrapper.absoluteTransform[0][2];
          const wrapperY = wrapper.absoluteTransform[1][2];
          const wrapperRight = wrapperX + wrapper.width;
          const wrapperBottom = wrapperY + wrapper.height;

          const diffs = {
            left: Math.abs(wrapperX - childMinX),
            top: Math.abs(wrapperY - childMinY),
            right: Math.abs(wrapperRight - childMaxX),
            bottom: Math.abs(wrapperBottom - childMaxY),
          };

          const maxDiff = Math.max(diffs.left, diffs.top, diffs.right, diffs.bottom);

          if (maxDiff > BBOX_TOLERANCE) {
            issues.push({
              wrapperId,
              type: "bbox_mismatch",
              detail: `max diff ${Math.round(maxDiff)}px (tolerance: ${BBOX_TOLERANCE}px)`,
              diffs,
            });
            hasIssue = true;
          }
        }
      }

      if (!hasIssue) {
        verified++;
      }
    } catch (e) {
      issues.push({
        wrapperId,
        type: "error",
        detail: e.message,
      });
    }
  }

  const total = verificationPlan.length;
  const matchRate = total > 0 ? Math.round((verified / total) * 1000) / 1000 : 0;

  return {
    success: true,
    total,
    verified,
    issues,
    missing,
    matchRate,
  };
}
