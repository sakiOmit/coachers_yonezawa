#!/usr/bin/env bash
# /figma-prepare テストランナー
#
# Usage:
#   bash .claude/skills/figma-prepare/tests/run-tests.sh                    # フィクスチャ使用
#   bash .claude/skills/figma-prepare/tests/run-tests.sh <metadata.json>    # 実データ使用
#
# 実データの場合、フィクスチャ固有テスト（特定nodeId等）はスキップされる。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")"
FIXTURE="${1:-$SCRIPT_DIR/fixture-metadata.json}"
IS_FIXTURE=false
[[ "$FIXTURE" == "$SCRIPT_DIR/fixture-metadata.json" ]] && IS_FIXTURE=true

if [[ ! -f "$FIXTURE" ]]; then
  echo "ERROR: File not found: $FIXTURE" >&2
  exit 1
fi

PASS=0
FAIL=0
SKIP=0
ERRORS=""

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$1"; }
bold()  { printf "\033[1m%s\033[0m\n" "$1"; }

assert_json_field() {
  local json="$1" field="$2" expected="$3" label="$4"
  local actual
  actual=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "__ERROR__")
  if [[ "$actual" == "$expected" ]]; then
    green "  PASS: $label (got: $actual)"
    ((PASS++)) || true
  else
    red "  FAIL: $label (expected: $expected, got: $actual)"
    ((FAIL++)) || true
    ERRORS+="  - $label: expected=$expected, got=$actual\n"
  fi
}

assert_json_range() {
  local json="$1" field="$2" min="$3" max="$4" label="$5"
  local actual
  actual=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "__ERROR__")
  if python3 -c "v=$actual; assert $min <= v <= $max" 2>/dev/null; then
    green "  PASS: $label (got: $actual, range: $min-$max)"
    ((PASS++)) || true
  else
    red "  FAIL: $label (got: $actual, expected range: $min-$max)"
    ((FAIL++)) || true
    ERRORS+="  - $label: got=$actual, expected range=$min-$max\n"
  fi
}

assert_json_gte() {
  local json="$1" field="$2" min="$3" label="$4"
  local actual
  actual=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "__ERROR__")
  if python3 -c "assert float('$actual') >= $min" 2>/dev/null; then
    green "  PASS: $label (got: $actual >= $min)"
    ((PASS++)) || true
  else
    red "  FAIL: $label (got: $actual, expected >= $min)"
    ((FAIL++)) || true
    ERRORS+="  - $label: got=$actual, expected >= $min\n"
  fi
}

skip_test() {
  yellow "  SKIP: $1"
  ((SKIP++)) || true
}

bold "Input: $FIXTURE"
[[ "$IS_FIXTURE" == true ]] && echo "(mode: fixture)" || echo "(mode: real data)"
echo ""

# ================================================================
bold "=== Phase 1: analyze-structure.sh ==="

RESULT1=$(bash "$SKILLS_DIR/scripts/analyze-structure.sh" "$FIXTURE" 2>&1) || {
  red "  FATAL: analyze-structure.sh crashed"
  echo "$RESULT1"
  exit 1
}

# エラーチェック
if echo "$RESULT1" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null; then
  green "  PASS: No error in output"
  ((PASS++)) || true
else
  red "  FAIL: Script returned error"
  echo "$RESULT1"
  ((FAIL++)) || true
fi

# スコアが0-100の範囲
assert_json_range "$RESULT1" "['score']" 0 100 "Score in 0-100 range"

# グレードが有効な文字
GRADE=$(echo "$RESULT1" | python3 -c "import json,sys; print(json.load(sys.stdin)['grade'])" 2>/dev/null || echo "?")
if [[ "$GRADE" =~ ^[A-F]$ ]]; then
  green "  PASS: Grade is valid letter ($GRADE)"
  ((PASS++)) || true
else
  red "  FAIL: Grade invalid ($GRADE)"
  ((FAIL++)) || true
fi

# 合計ノード数 > 0
assert_json_gte "$RESULT1" "['metrics']['total_nodes']" 1 "Total nodes >= 1"

# unnamed_nodes は 0 以上（実データでは 0 の可能性もある）
assert_json_gte "$RESULT1" "['metrics']['unnamed_nodes']" 0 "Unnamed nodes >= 0"

# score_breakdown が5フィールド
echo "$RESULT1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
sb = d.get('score_breakdown', {})
assert len(sb) == 5, f'Expected 5 breakdown fields, got {len(sb)}'
print('  PASS: score_breakdown has 5 fields')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: score_breakdown structure"; ((FAIL++)) || true; }

# recommendation が空でない
echo "$RESULT1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('recommendation','')
assert len(r) > 0, 'Empty recommendation'
print(f'  PASS: recommendation = \"{r}\"')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Empty recommendation"; ((FAIL++)) || true; }

echo ""
echo "  [Detail] $(echo "$RESULT1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
m=d['metrics']
print(f\"nodes={m['total_nodes']}, unnamed={m['unnamed_nodes']}({m['unnamed_rate_pct']}%), flat={m['flat_sections']}, deep={m['deep_nesting_count']}, no_al={m['no_autolayout_frames']}/{m['total_frames']}\")
" 2>/dev/null)"
echo ""

# ================================================================
bold "=== Phase 2: generate-rename-map.sh ==="

RESULT2=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$FIXTURE" 2>&1) || {
  red "  FATAL: generate-rename-map.sh crashed"
  echo "$RESULT2"
  exit 1
}

# エラーチェック
echo "$RESULT2" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null \
  && { green "  PASS: No error in output"; ((PASS++)) || true; } \
  || { red "  FAIL: Script returned error"; echo "$RESULT2"; ((FAIL++)) || true; }

# total >= 0
assert_json_gte "$RESULT2" "['total']" 0 "Rename total >= 0"

# status = dry-run
assert_json_field "$RESULT2" "['status']" "dry-run" "Status is dry-run"

# renames の件数
RENAME_COUNT=$(echo "$RESULT2" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('renames',{})))" 2>/dev/null || echo 0)
green "  INFO: $RENAME_COUNT rename candidates"

# フィクスチャ固有: properly-named ノードが除外されていること
if [[ "$IS_FIXTURE" == true ]]; then
  echo "$RESULT2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
renames = d.get('renames',{})
assert '3:1' not in renames, 'properly-named-footer should not be renamed'
print('  PASS: Properly named nodes excluded from renames')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Properly named node incorrectly targeted"; ((FAIL++)) || true; }
else
  skip_test "Fixture-specific: properly-named exclusion"
fi

# YAML出力テスト
YAML_OUT="/tmp/figma-prepare-test-rename-$$.yaml"
bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$FIXTURE" --output "$YAML_OUT" >/dev/null 2>&1
if [[ -f "$YAML_OUT" ]] && grep -q "renames:" "$YAML_OUT"; then
  green "  PASS: YAML output file generated"
  ((PASS++)) || true
else
  red "  FAIL: YAML output not generated"
  ((FAIL++)) || true
fi
rm -f "$YAML_OUT"

# サンプル表示（最大5件）
echo ""
echo "$RESULT2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
renames = d.get('renames',{})
items = list(renames.items())[:5]
if items:
    print('  [Sample renames]')
    for nid, info in items:
        print(f'    {info[\"old_name\"]:30s} → {info[\"new_name\"]}')
    if len(renames) > 5:
        print(f'    ... and {len(renames)-5} more')
" 2>/dev/null
echo ""

# ================================================================
bold "=== Phase 3: detect-grouping-candidates.sh ==="

RESULT3=$(bash "$SKILLS_DIR/scripts/detect-grouping-candidates.sh" "$FIXTURE" 2>&1) || {
  red "  FATAL: detect-grouping-candidates.sh crashed"
  echo "$RESULT3"
  exit 1
}

# エラーチェック
echo "$RESULT3" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null \
  && { green "  PASS: No error in output"; ((PASS++)) || true; } \
  || { red "  FAIL: Script returned error"; echo "$RESULT3"; ((FAIL++)) || true; }

# total >= 0
assert_json_gte "$RESULT3" "['total']" 0 "Grouping total >= 0"

# status = dry-run
assert_json_field "$RESULT3" "['status']" "dry-run" "Status is dry-run"

# メソッド別集計
echo "$RESULT3" | python3 -c "
import json,sys
from collections import Counter
d=json.load(sys.stdin)
candidates = d.get('candidates',[])
methods = Counter(c.get('method','') for c in candidates)
print(f'  INFO: {len(candidates)} candidates: {dict(methods)}')
" 2>/dev/null
echo ""

# ================================================================
bold "=== Phase 4: infer-autolayout.sh ==="

RESULT4=$(bash "$SKILLS_DIR/scripts/infer-autolayout.sh" "$FIXTURE" 2>&1) || {
  red "  FATAL: infer-autolayout.sh crashed"
  echo "$RESULT4"
  exit 1
}

# エラーチェック
echo "$RESULT4" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null \
  && { green "  PASS: No error in output"; ((PASS++)) || true; } \
  || { red "  FAIL: Script returned error"; echo "$RESULT4"; ((FAIL++)) || true; }

# total >= 0
assert_json_gte "$RESULT4" "['total']" 0 "AutoLayout total >= 0"

# status = dry-run
assert_json_field "$RESULT4" "['status']" "dry-run" "Status is dry-run"

# 推論結果のバリデーション
echo "$RESULT4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
frames = d.get('frames',[])
valid = 0
for f in frames:
    layout = f.get('layout',{})
    assert layout['direction'] in ('HORIZONTAL','VERTICAL'), f'Bad direction'
    assert isinstance(layout['gap'], (int, float)), 'Gap not numeric'
    assert all(k in layout['padding'] for k in ('top','right','bottom','left')), 'Missing padding'
    valid += 1
print(f'  PASS: {valid} frames have valid layout structure')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Layout inference structure invalid"; ((FAIL++)) || true; }

# 4pxスナップ確認
echo "$RESULT4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
violations = []
for f in d.get('frames',[]):
    gap = f['layout']['gap']
    if gap % 4 != 0:
        violations.append(f'gap={gap} in {f[\"node_name\"]}')
    for k,v in f['layout']['padding'].items():
        if v % 4 != 0:
            violations.append(f'{k}={v} in {f[\"node_name\"]}')
if violations:
    print(f'  FAIL: 4px snap violations: {violations[:3]}')
    sys.exit(1)
print('  PASS: All values snapped to 4px grid')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Grid snap check failed"; ((FAIL++)) || true; }

# サンプル表示
echo ""
echo "$RESULT4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
frames = d.get('frames',[])[:5]
if frames:
    print('  [Sample AutoLayout inferences]')
    for f in frames:
        l = f['layout']
        p = l['padding']
        print(f'    {f[\"node_name\"]:30s} → {l[\"direction\"]} gap={l[\"gap\"]} pad=[{p[\"top\"]},{p[\"right\"]},{p[\"bottom\"]},{p[\"left\"]}] ({l[\"confidence\"]})')
" 2>/dev/null
echo ""

# ================================================================
bold "=== Cross-script: consistency ==="

P1_UNNAMED=$(echo "$RESULT1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['unnamed_nodes'])" 2>/dev/null || echo "0")
P2_TOTAL=$(echo "$RESULT2" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")

# Phase 1の未命名数とPhase 2のリネーム数が一致（許容差±5）
if python3 -c "assert abs($P1_UNNAMED - $P2_TOTAL) <= 5" 2>/dev/null; then
  green "  PASS: Phase1 unnamed ($P1_UNNAMED) ≈ Phase2 renames ($P2_TOTAL)"
  ((PASS++)) || true
else
  red "  FAIL: Phase1 unnamed ($P1_UNNAMED) vs Phase2 renames ($P2_TOTAL) — gap > 5"
  ((FAIL++)) || true
fi

echo ""

# ================================================================
# ================================================================
bold "=== Dirty Fixture: fixture-dirty.json ==="

DIRTY_FIXTURE="$SCRIPT_DIR/fixture-dirty.json"
if [[ -f "$DIRTY_FIXTURE" ]]; then
  DIRTY_RESULT=$(bash "$SKILLS_DIR/scripts/analyze-structure.sh" "$DIRTY_FIXTURE" 2>&1) || {
    red "  FATAL: analyze-structure.sh crashed on dirty fixture"
    echo "$DIRTY_RESULT"
    ((FAIL++)) || true
  }

  if [[ -n "${DIRTY_RESULT:-}" ]] && echo "$DIRTY_RESULT" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    # Dirty fixture should have low score (D or F)
    DIRTY_SCORE=$(echo "$DIRTY_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['score'])" 2>/dev/null || echo "999")
    DIRTY_GRADE=$(echo "$DIRTY_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['grade'])" 2>/dev/null || echo "?")
    DIRTY_UNNAMED=$(echo "$DIRTY_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['unnamed_rate_pct'])" 2>/dev/null || echo "0")

    # Score should be below 80 (not grade A)
    if python3 -c "assert float('$DIRTY_SCORE') < 80" 2>/dev/null; then
      green "  PASS: Dirty fixture score < 80 (got: $DIRTY_SCORE, grade: $DIRTY_GRADE)"
      ((PASS++)) || true
    else
      red "  FAIL: Dirty fixture score too high ($DIRTY_SCORE) — should detect issues"
      ((FAIL++)) || true
    fi

    # Unnamed rate should be significant (>30%)
    if python3 -c "assert float('$DIRTY_UNNAMED') > 30" 2>/dev/null; then
      green "  PASS: Dirty fixture unnamed rate > 30% (got: ${DIRTY_UNNAMED}%)"
      ((PASS++)) || true
    else
      red "  FAIL: Dirty fixture unnamed rate too low (${DIRTY_UNNAMED}%) — expected >30%"
      ((FAIL++)) || true
    fi

    echo ""
    echo "  [Detail] $(echo "$DIRTY_RESULT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
m=d['metrics']
print(f\"score={d['score']} grade={d['grade']} nodes={m['total_nodes']}, unnamed={m['unnamed_nodes']}({m['unnamed_rate_pct']}%), flat={m['flat_sections']}, deep={m['deep_nesting_count']}\")
" 2>/dev/null)"

    # Phase 2 should find many renames
    DIRTY_RENAME=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$DIRTY_FIXTURE" 2>&1) || true
    if [[ -n "${DIRTY_RENAME:-}" ]]; then
      DIRTY_RENAME_COUNT=$(echo "$DIRTY_RENAME" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
      if python3 -c "assert int('$DIRTY_RENAME_COUNT') > 10" 2>/dev/null; then
        green "  PASS: Dirty fixture rename candidates > 10 (got: $DIRTY_RENAME_COUNT)"
        ((PASS++)) || true
      else
        red "  FAIL: Dirty fixture rename candidates too few ($DIRTY_RENAME_COUNT)"
        ((FAIL++)) || true
      fi
    fi
  fi
else
  skip_test "Dirty fixture not found"
fi

echo ""

# ================================================================
bold "========================================"
bold "  Results: $PASS passed, $FAIL failed, $SKIP skipped"
bold "========================================"

if [[ $FAIL -gt 0 ]]; then
  echo ""
  red "Failed tests:"
  printf "$ERRORS"
  exit 1
fi

echo ""
green "All tests passed!"
exit 0
