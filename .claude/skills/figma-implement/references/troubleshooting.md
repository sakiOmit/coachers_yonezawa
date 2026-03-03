# Troubleshooting: figma-implement

よくあるエラーと解決方法。

---

## Error: "Cache not found"

**Cause**: `/figma-prefetch` was not run before implementation.

**Solution**:
1. Run `/figma-prefetch {url}` first
2. Verify cache:
   ```bash
   bash .claude/skills/figma-implement/scripts/validate-cache.sh \
     .claude/cache/figma/{page-name}
   ```
3. Then run `/figma-implement`

---

## Error: "raw_jsx validation failed"

**Cause**: Cached raw_jsx is abstracted or incomplete.

**Solution**:
1. Check the specific node:
   ```bash
   cat .claude/cache/figma/{page}/nodes/{nodeId}.json | jq '.raw_jsx | length'
   ```
2. If length < 500 or contains "// Section", re-fetch:
   ```bash
   /figma-recursive-splitter {url} --force
   ```
3. Or use `get_design_context` directly for that section

---

## Error: "Token limit exceeded"

**Cause**: Page is too large for single retrieval.

**Solution**:
1. Use `/figma-recursive-splitter` for split retrieval
2. Or use `--section` option to implement one section at a time:
   ```bash
   /figma-implement --page {page} --section hero
   ```

---

## Error: "Build failed" (Step 8)

**Cause**: SCSS/Astro syntax error or missing import.

**Solution**:
1. Run build manually to see detailed error:
   ```bash
   npm run astro:build
   ```
2. Check SCSS imports in `src/css/pages/{page}/style.scss`
3. Verify Astro page imports and Props interface
4. Fix errors and re-run Step 8

---

## Error: "Playwright connection failed"

**Cause**: Browser not installed or Docker network issue.

**Solution**:
1. Check Playwright installation:
   ```bash
   npx playwright install chromium
   ```
2. Verify Docker is running if using containerized browser
3. Check MCP Playwright server is connected

---

## Error: "Container width incorrect"

**Cause**: Wrong calculation method or missing artboard info.

**Solution**:
1. Use `/figma-container-width-calculator` for accurate calculation
2. Verify artboard margin-based formula:
   ```
   containerWidth = artboardWidth - (firstContentFrame.x * 2)
   ```
3. Check metadata.json for artboard dimensions

---

## Error: "Design tokens extraction failed"

**Cause**: Figma Variables not defined or API error.

**Solution**:
1. Check if Figma file has Variables defined
2. If Variables are empty, manually extract from design-context:
   - Colors: Look for `fill` and `stroke` properties
   - Fonts: Look for `fontFamily`, `fontSize`, `fontWeight`
   - Spacing: Look for `gap`, `padding`, `margin` values
3. Add extracted values to `foundation/_variables.scss`
