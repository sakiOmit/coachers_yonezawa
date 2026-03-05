/**
 * apply-renames.js
 *
 * Chrome DevTools MCP evaluate_script 用テンプレート。
 * リネームマップ（JSON）を受け取り、バッチ実行でレイヤー名を変更する。
 *
 * Usage:
 *   1. Read this file
 *   2. Replace __RENAME_MAP__ with the actual JSON object
 *      e.g. {"2:55": "hero-background", "2:56": "hero-title", ...}
 *   3. Replace __BATCH_INFO__ with batch metadata
 *      e.g. "1/3" (batch 1 of 3)
 *   4. Pass the resulting string to mcp__chrome-devtools__evaluate_script
 *      の function パラメータとして渡す
 *
 * Output (object — MCP が自動シリアライズ):
 *   {
 *     success: true,
 *     renamed: N,
 *     skipped: N,
 *     errors: [{ nodeId, error }],
 *     total: N,
 *     batch: "1/3"
 *   }
 *
 * Constraints:
 *   - Max 50 nodes per batch (timeout prevention)
 *   - Errors are per-node skip (batch continues)
 */
() => {
  const renameMap = __RENAME_MAP__;
  const batchInfo = "__BATCH_INFO__";

  let renamed = 0;
  let skipped = 0;
  const errors = [];

  for (const [nodeId, newName] of Object.entries(renameMap)) {
    try {
      const node = figma.getNodeById(nodeId);
      if (!node) {
        errors.push({ nodeId, error: "not found" });
        skipped++;
        continue;
      }

      // Skip if name is already correct
      if (node.name === newName) {
        skipped++;
        continue;
      }

      node.name = newName;
      renamed++;
    } catch (e) {
      errors.push({ nodeId, error: e.message });
      skipped++;
    }
  }

  return {
    success: renamed > 0 || errors.length === 0,
    renamed,
    skipped,
    errors,
    total: Object.keys(renameMap).length,
    batch: batchInfo,
  };
}
