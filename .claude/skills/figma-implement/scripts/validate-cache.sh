#!/bin/bash
# =============================================================================
# validate-cache.sh
#
# figma-implement 実行前のキャッシュ検証
# Step 0 (Cache Validation) で使用
#
# Usage: validate-cache.sh <cache_dir>
# =============================================================================

set -e

CACHE_DIR=$1

if [ -z "$CACHE_DIR" ]; then
  echo "Usage: validate-cache.sh <cache_dir>"
  exit 1
fi

if [ ! -d "$CACHE_DIR" ]; then
  echo "❌ FAIL: Cache directory not found: $CACHE_DIR"
  echo ""
  echo "Solution: Run /figma-prefetch first"
  exit 1
fi

ERRORS=0
WARNINGS=0

# Check 1: prefetch-info.yaml exists
if [ ! -f "$CACHE_DIR/prefetch-info.yaml" ]; then
  echo "❌ FAIL: prefetch-info.yaml not found"
  echo "   Run /figma-prefetch to create cache"
  ERRORS=$((ERRORS + 1))
else
  echo "✅ prefetch-info.yaml exists"

  # Check TTL (24 hours)
  if command -v yq &> /dev/null; then
    TIMESTAMP=$(yq -r '.timestamp // empty' "$CACHE_DIR/prefetch-info.yaml" 2>/dev/null)
    if [ -n "$TIMESTAMP" ]; then
      CACHE_TIME=$(date -d "$TIMESTAMP" +%s 2>/dev/null || echo "0")
      NOW=$(date +%s)
      AGE=$(( (NOW - CACHE_TIME) / 3600 ))
      if [ "$AGE" -gt 24 ]; then
        echo "⚠️ WARN: Cache is $AGE hours old (> 24h TTL)"
        WARNINGS=$((WARNINGS + 1))
      else
        echo "✅ Cache age: ${AGE}h (within 24h TTL)"
      fi
    fi
  fi
fi

# Check 2: PC cache
PC_DIR="$CACHE_DIR/pc"
if [ -d "$PC_DIR" ]; then
  # Check for design-context or nodes
  if [ -f "$PC_DIR/design-context.json" ]; then
    echo "✅ PC: design-context.json exists"
  elif [ -d "$PC_DIR/nodes" ]; then
    NODE_COUNT=$(find "$PC_DIR/nodes" -name "*.json" | wc -l)
    echo "✅ PC: nodes/ exists ($NODE_COUNT files)"
  else
    echo "❌ FAIL: PC cache has no design-context.json or nodes/"
    ERRORS=$((ERRORS + 1))
  fi
else
  # Single-level structure (backward compatibility)
  if [ -f "$CACHE_DIR/design-context.json" ]; then
    echo "✅ design-context.json exists (legacy structure)"
  elif [ -d "$CACHE_DIR/nodes" ]; then
    NODE_COUNT=$(find "$CACHE_DIR/nodes" -name "*.json" | wc -l)
    echo "✅ nodes/ exists ($NODE_COUNT files, legacy structure)"
  else
    echo "❌ FAIL: No design-context.json or nodes/ found"
    ERRORS=$((ERRORS + 1))
  fi
fi

# Check 3: SP cache (optional)
SP_DIR="$CACHE_DIR/sp"
if [ -d "$SP_DIR" ]; then
  if [ -f "$SP_DIR/design-context.json" ] || [ -d "$SP_DIR/nodes" ]; then
    echo "✅ SP cache exists"
  else
    echo "⚠️ WARN: SP directory exists but is incomplete"
    WARNINGS=$((WARNINGS + 1))
  fi
else
  echo "ℹ️ INFO: No SP cache (PC-only implementation)"
fi

# Check 4: Verify at least one node has raw_jsx
if [ -d "$CACHE_DIR/nodes" ] || [ -d "$CACHE_DIR/pc/nodes" ]; then
  NODES_DIR="$CACHE_DIR/nodes"
  [ -d "$CACHE_DIR/pc/nodes" ] && NODES_DIR="$CACHE_DIR/pc/nodes"

  VALID_JSX=0
  for node_file in "$NODES_DIR"/*.json; do
    if [ -f "$node_file" ]; then
      HAS_JSX=$(jq 'has("raw_jsx") and (.raw_jsx | length > 500)' "$node_file" 2>/dev/null || echo "false")
      if [ "$HAS_JSX" = "true" ]; then
        VALID_JSX=$((VALID_JSX + 1))
      fi
    fi
  done

  if [ "$VALID_JSX" -gt 0 ]; then
    echo "✅ $VALID_JSX nodes have valid raw_jsx"
  else
    echo "⚠️ WARN: No nodes with valid raw_jsx found"
    WARNINGS=$((WARNINGS + 1))
  fi
fi

# Summary
echo ""
if [ $ERRORS -gt 0 ]; then
  echo "❌ FAIL: $ERRORS error(s), $WARNINGS warning(s)"
  echo ""
  echo "Next steps:"
  echo "  1. Run /figma-prefetch to create/update cache"
  echo "  2. Or run /figma-recursive-splitter if page is large"
  exit 1
elif [ $WARNINGS -gt 0 ]; then
  echo "⚠️ PASS with warnings: $WARNINGS warning(s)"
  echo "   Consider refreshing cache with /figma-prefetch --force"
  exit 0
else
  echo "✅ PASS: Cache is valid and ready for implementation"
  exit 0
fi
