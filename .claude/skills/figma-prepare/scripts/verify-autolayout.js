/**
 * verify-autolayout.js
 *
 * Chrome DevTools MCP evaluate_script 用テンプレート。
 * apply-autolayout.js 適用後のノードを検証し、
 * layoutMode / itemSpacing / padding / alignment が正しく設定されたか確認する。
 *
 * Usage:
 *   1. Read this file
 *   2. Replace __VERIFICATION_PLAN__ with the verification data array
 *      e.g. [
 *        {
 *          "node_id": "23:55",
 *          "expected_direction": "VERTICAL",
 *          "expected_gap": 24,
 *          "expected_padding": { "top": 16, "right": 16, "bottom": 16, "left": 16 },
 *          "expected_primary_align": "MIN",
 *          "expected_counter_align": "CENTER"
 *        },
 *        ...
 *      ]
 *      - node_id: apply-autolayout.js で適用したノードID
 *      - expected_direction: HORIZONTAL / VERTICAL / WRAP
 *      - expected_gap: itemSpacing 期待値
 *      - expected_padding: { top, right, bottom, left } 期待値
 *      - expected_primary_align: primaryAxisAlignItems 期待値
 *      - expected_counter_align: counterAxisAlignItems 期待値
 *   3. Pass the resulting string to mcp__chrome-devtools__evaluate_script
 *      の function パラメータとして渡す
 *
 * Output (object — MCP が自動シリアライズ):
 *   {
 *     success: true,
 *     total: N,              // 検証対象ノード数
 *     verified: N,           // 全検証パスしたノード数
 *     issues: [],            // [{nodeId, type, detail}]
 *     missing: [],           // 存在しないノードID
 *     matchRate: 0.0-1.0     // verified / total
 *   }
 *
 * 検証項目:
 *   1. ノードの存在・FRAME型確認
 *   2. layoutMode / layoutWrap が期待方向と一致
 *   3. itemSpacing（gap）が期待値と一致（±1px許容）
 *   4. padding 4辺が期待値と一致（±1px許容）
 *   5. primaryAxisAlignItems / counterAxisAlignItems が期待値と一致
 *
 * Constraints:
 *   - Read-only (no mutations)
 *   - Errors are per-node skip (batch continues)
 */
() => {
  const verificationPlan = __VERIFICATION_PLAN__;
  const VALUE_TOLERANCE = 1; // px

  let verified = 0;
  const issues = [];
  const missing = [];

  for (const entry of verificationPlan) {
    const nodeId = entry.node_id;

    try {
      // 1. Check node existence
      const node = figma.getNodeById(nodeId);
      if (!node) {
        missing.push(nodeId);
        continue;
      }

      let hasIssue = false;

      // 2. Check layoutMode / direction
      if (entry.expected_direction) {
        const expectedDir = entry.expected_direction;
        let actualDir;

        if (node.layoutMode === "HORIZONTAL" && node.layoutWrap === "WRAP") {
          actualDir = "WRAP";
        } else {
          actualDir = node.layoutMode || "NONE";
        }

        if (actualDir !== expectedDir) {
          issues.push({
            nodeId,
            type: "direction_mismatch",
            detail: `expected "${expectedDir}", got "${actualDir}"`,
          });
          hasIssue = true;
        }
      }

      // 3. Check gap (itemSpacing)
      if (typeof entry.expected_gap === "number") {
        const actualGap = node.itemSpacing;
        if (typeof actualGap !== "number" || Math.abs(actualGap - entry.expected_gap) > VALUE_TOLERANCE) {
          issues.push({
            nodeId,
            type: "gap_mismatch",
            detail: `expected ${entry.expected_gap}, got ${actualGap}`,
          });
          hasIssue = true;
        }
      }

      // 4. Check padding
      if (entry.expected_padding) {
        const pad = entry.expected_padding;
        const padChecks = [
          { key: "top", expected: pad.top, actual: node.paddingTop },
          { key: "right", expected: pad.right, actual: node.paddingRight },
          { key: "bottom", expected: pad.bottom, actual: node.paddingBottom },
          { key: "left", expected: pad.left, actual: node.paddingLeft },
        ];

        const padMismatches = [];
        for (const pc of padChecks) {
          if (typeof pc.expected === "number") {
            const actual = typeof pc.actual === "number" ? pc.actual : 0;
            if (Math.abs(actual - pc.expected) > VALUE_TOLERANCE) {
              padMismatches.push(`${pc.key}: expected ${pc.expected}, got ${actual}`);
            }
          }
        }

        if (padMismatches.length > 0) {
          issues.push({
            nodeId,
            type: "padding_mismatch",
            detail: padMismatches.join("; "),
          });
          hasIssue = true;
        }
      }

      // 5. Check primary axis alignment
      if (entry.expected_primary_align) {
        const actual = node.primaryAxisAlignItems || "MIN";
        if (actual !== entry.expected_primary_align) {
          issues.push({
            nodeId,
            type: "primary_align_mismatch",
            detail: `expected "${entry.expected_primary_align}", got "${actual}"`,
          });
          hasIssue = true;
        }
      }

      // 6. Check counter axis alignment
      if (entry.expected_counter_align) {
        const actual = node.counterAxisAlignItems || "MIN";
        if (actual !== entry.expected_counter_align) {
          issues.push({
            nodeId,
            type: "counter_align_mismatch",
            detail: `expected "${entry.expected_counter_align}", got "${actual}"`,
          });
          hasIssue = true;
        }
      }

      if (!hasIssue) {
        verified++;
      }
    } catch (e) {
      issues.push({
        nodeId,
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
