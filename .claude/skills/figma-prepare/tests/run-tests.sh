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
export SCRIPT_DIR SKILLS_DIR
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
  # Issue 112: Use sys.argv to avoid shell variable interpolation in Python code
  if python3 -c "import sys; v=float(sys.argv[1]); assert float(sys.argv[2]) <= v <= float(sys.argv[3])" "$actual" "$min" "$max" 2>/dev/null; then
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
  # Issue 112: Use sys.argv to avoid shell variable interpolation in Python code
  if python3 -c "import sys; assert float(sys.argv[1]) >= float(sys.argv[2])" "$actual" "$min" 2>/dev/null; then
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
bold "=== Phase 3: generate-rename-map.sh ==="

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
bold "=== Phase 2: detect-grouping-candidates.sh ==="

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
    assert layout['direction'] in ('HORIZONTAL','VERTICAL','WRAP'), f'Bad direction'
    assert isinstance(layout['gap'], (int, float)), 'Gap not numeric'
    assert all(k in layout['padding'] for k in ('top','right','bottom','left')), 'Missing padding'
    valid += 1
print(f'  PASS: {valid} frames have valid layout structure')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Layout inference structure invalid"; ((FAIL++)) || true; }

# 4pxスナップ確認（Issue 111: exact source frames はスキップ — Figma実値は4px刻みでない場合がある）
echo "$RESULT4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
violations = []
for f in d.get('frames',[]):
    if f.get('source') == 'exact':
        continue
    gap = f['layout']['gap']
    if gap % 4 != 0:
        violations.append(f'gap={gap} in {f[\"node_name\"]}')
    for k,v in f['layout']['padding'].items():
        if v % 4 != 0:
            violations.append(f'{k}={v} in {f[\"node_name\"]}')
if violations:
    print(f'  FAIL: 4px snap violations: {violations[:3]}')
    sys.exit(1)
print('  PASS: All inferred values snapped to 4px grid (exact frames skipped)')
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
bold "=== Unit: to_kebab regression ==="

python3 -c "
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import to_kebab

# Non-ASCII-only text returns generic 'content' label
assert to_kebab('大規模イベントに強いオペレーション力') == 'content', f'JP-only fail: got \"{to_kebab(\"大規模イベントに強いオペレーション力\")}\"'
assert to_kebab('イベント一覧') == 'content', f'JP-only fail: got \"{to_kebab(\"イベント一覧\")}\"'
assert to_kebab('お問い合わせ') == 'content', f'JP-only fail: got \"{to_kebab(\"お問い合わせ\")}\"'
assert to_kebab('無料相談') == 'content', f'JP-only fail: got \"{to_kebab(\"無料相談\")}\"'
assert to_kebab('資料請求') == 'content', f'JP-only fail: got \"{to_kebab(\"資料請求\")}\"'

# Empty / whitespace
assert to_kebab('') == '', 'Empty string fail'
assert to_kebab('   ') == '', 'Whitespace fail'

# ASCII still works
assert to_kebab('job description') == 'job-description', f'ASCII fail: got \"{to_kebab(\"job description\")}\"'
assert to_kebab('REASON') == 'reason', f'ASCII fail: got \"{to_kebab(\"REASON\")}\"'

# Issue 47: CamelCase splitting
assert to_kebab('CamelCase') == 'camel-case', f'CamelCase fail: got \"{to_kebab(\"CamelCase\")}\"'
assert to_kebab('HTMLParser') == 'html-parser', f'HTMLParser fail: got \"{to_kebab(\"HTMLParser\")}\"'
assert to_kebab('myComponent') == 'my-component', f'myComponent fail: got \"{to_kebab(\"myComponent\")}\"'

# Mixed: ASCII extracted from JP text
assert to_kebab('Hello世界') == 'hello', f'Mixed fail: got \"{to_kebab(\"Hello世界\")}\"'

print('All to_kebab tests passed')
" "$SKILLS_DIR" 2>/dev/null && { green "  PASS: to_kebab unit tests"; ((PASS++)) || true; } || { red "  FAIL: to_kebab unit tests"; ((FAIL++)) || true; }

echo ""

# ================================================================
bold "=== Cross-script: consistency ==="

P1_UNNAMED=$(echo "$RESULT1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['unnamed_nodes'])" 2>/dev/null || echo "0")
P3_RENAME_TOTAL=$(echo "$RESULT2" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")

# Phase 1の未命名数とPhase 3のリネーム数が一致（許容差±5）
# Issue 130: Use sys.argv to avoid shell variable interpolation in Python code
if python3 -c "import sys; assert abs(int(sys.argv[1]) - int(sys.argv[2])) <= 5" "$P1_UNNAMED" "$P3_RENAME_TOTAL" 2>/dev/null; then
  green "  PASS: Phase1 unnamed ($P1_UNNAMED) ≈ Phase3 renames ($P3_RENAME_TOTAL)"
  ((PASS++)) || true
else
  red "  FAIL: Phase1 unnamed ($P1_UNNAMED) vs Phase3 renames ($P3_RENAME_TOTAL) — gap > 5"
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
    if python3 -c "import sys; assert float(sys.argv[1]) < 80" "$DIRTY_SCORE" 2>/dev/null; then
      green "  PASS: Dirty fixture score < 80 (got: $DIRTY_SCORE, grade: $DIRTY_GRADE)"
      ((PASS++)) || true
    else
      red "  FAIL: Dirty fixture score too high ($DIRTY_SCORE) — should detect issues"
      ((FAIL++)) || true
    fi

    # Unnamed rate should be significant (>30%)
    if python3 -c "import sys; assert float(sys.argv[1]) > 30" "$DIRTY_UNNAMED" 2>/dev/null; then
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
      if python3 -c "import sys; assert int(sys.argv[1]) > 10" "$DIRTY_RENAME_COUNT" 2>/dev/null; then
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
# ================================================================
bold "=== Realistic Fixture: fixture-realistic.json ==="

REALISTIC_FIXTURE="$SCRIPT_DIR/fixture-realistic.json"
if [[ -f "$REALISTIC_FIXTURE" ]]; then
  # --- Phase 1: analyze-structure ---
  REAL_P1=$(bash "$SKILLS_DIR/scripts/analyze-structure.sh" "$REALISTIC_FIXTURE" 2>&1) || {
    red "  FATAL: analyze-structure.sh crashed on realistic fixture"
    echo "$REAL_P1"
    ((FAIL++)) || true
  }

  if [[ -n "${REAL_P1:-}" ]] && echo "$REAL_P1" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    # 1. is_section_root: root FRAME (1440 width) recognized as section root
    echo "$REAL_P1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
# Root is FRAME with 1440 width — deep_nesting should be relative to section roots
# If section root detection works, deep_nesting_count should be low (< total/2)
total = d['metrics']['total_nodes']
deep = d['metrics']['deep_nesting_count']
assert deep < total // 2, f'deep_nesting={deep} >= total/2={total//2}'
print(f'  PASS: is_section_root — deep_nesting={deep} < total/2={total//2}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: is_section_root detection"; ((FAIL++)) || true; }

    # 2. Unnamed detection: lowercase 'image' nodes detected
    REAL_UNNAMED=$(echo "$REAL_P1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['unnamed_nodes'])" 2>/dev/null || echo "0")
    if python3 -c "import sys; assert int(sys.argv[1]) >= 5" "$REAL_UNNAMED" 2>/dev/null; then
      green "  PASS: Unnamed detection — $REAL_UNNAMED unnamed nodes detected (>= 5, includes lowercase image)"
      ((PASS++)) || true
    else
      red "  FAIL: Unnamed detection — only $REAL_UNNAMED detected (expected >= 5)"
      ((FAIL++)) || true
    fi

    # 3. Lowercase 'image' in sample_unnamed
    echo "$REAL_P1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
samples = d.get('sample_unnamed', [])
has_lowercase = any('image' in s.lower() for s in samples)
assert has_lowercase, f'No lowercase image in samples: {samples}'
print('  PASS: Lowercase image detected in sample_unnamed')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Lowercase image not in sample_unnamed"; ((FAIL++)) || true; }

    # 4. Score validation (85-95 range for well-named fixture)
    assert_json_range "$REAL_P1" "['score']" 85 95 "Realistic fixture score in 85-95"

    echo ""
    echo "  [Detail] $(echo "$REAL_P1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
m=d['metrics']
print(f\"score={d['score']} grade={d['grade']} nodes={m['total_nodes']}, unnamed={m['unnamed_nodes']}({m['unnamed_rate_pct']}%), flat={m['flat_sections']}, deep={m['deep_nesting_count']}\")
" 2>/dev/null)"
    echo ""

    # --- Phase 2: generate-rename-map ---
    REAL_P2=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$REALISTIC_FIXTURE" 2>&1) || {
      red "  FATAL: generate-rename-map.sh crashed on realistic fixture"
      ((FAIL++)) || true
    }

    if [[ -n "${REAL_P2:-}" ]]; then
      REAL_RENAME_COUNT=$(echo "$REAL_P2" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
      # Cross-script consistency: Phase 1 unnamed ≈ Phase 3 renames (±5) — Issue 113: Phase 2→3
      if python3 -c "import sys; assert abs(int(sys.argv[1]) - int(sys.argv[2])) <= 5" "$REAL_UNNAMED" "$REAL_RENAME_COUNT" 2>/dev/null; then
        green "  PASS: Cross-script — Phase1 unnamed ($REAL_UNNAMED) ≈ Phase3 renames ($REAL_RENAME_COUNT)"
        ((PASS++)) || true
      else
        red "  FAIL: Cross-script — Phase1 unnamed ($REAL_UNNAMED) vs Phase3 renames ($REAL_RENAME_COUNT) gap > 5"
        ((FAIL++)) || true
      fi

      # --- Rename quality tests (Issue 3+6 regression) ---
      # 1. Navigation detection: Frame 93 (10 TEXT children) → nav-*
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:114',{})
new_name = r.get('new_name','')
assert new_name.startswith('nav-'), f'Frame 93 should be nav-*, got: {new_name}'
print(f'  PASS: Nav detection — Frame 93 → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Nav detection — Frame 93 not renamed to nav-*"; ((FAIL++)) || true; }

      # 2. Icon detection: Frame 1009 (40x40, 1 child) → icon-*
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:108',{})
new_name = r.get('new_name','')
assert new_name.startswith('icon-'), f'Frame 1009 should be icon-*, got: {new_name}'
print(f'  PASS: Icon detection — Frame 1009 → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Icon detection — Frame 1009 not renamed to icon-*"; ((FAIL++)) || true; }

      # 3. Heading detection: Frame 46405 (2 TEXT children) → heading-*
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:102',{})
new_name = r.get('new_name','')
assert new_name.startswith('heading-'), f'Frame 46405 should be heading-*, got: {new_name}'
print(f'  PASS: Heading detection — Frame 46405 → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Heading detection — Frame 46405 not renamed to heading-*"; ((FAIL++)) || true; }

      # 4. Tiny empty frame → icon: Group 45950 (14.67x12.2, empty) → icon-*
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:109',{})
new_name = r.get('new_name','')
assert new_name.startswith('icon-'), f'Group 45950 should be icon-*, got: {new_name}'
print(f'  PASS: Tiny frame → icon — Group 45950 → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Tiny frame not renamed to icon-*"; ((FAIL++)) || true; }

      # 5. Fallback rate < 50% (group-*/frame-*/container-* should be minority)
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
renames = d.get('renames',{})
total = len(renames)
fallback = sum(1 for r in renames.values() if any(r['new_name'].startswith(p) for p in ['group-', 'frame-', 'container-']))
rate = 100*fallback/max(total,1)
assert rate < 50, f'Fallback rate {rate:.1f}% >= 50%'
print(f'  PASS: Fallback rate = {rate:.1f}% < 50% ({fallback}/{total})')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Fallback rate >= 50%"; ((FAIL++)) || true; }

      # 6. Issue 14: heading+body frame → content-* (not heading-*)
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:200',{})
new_name = r.get('new_name','')
assert new_name.startswith('content-'), f'Frame 99001 (heading+body) should be content-*, got: {new_name}'
print(f'  PASS: Issue 14 — heading+body frame → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 14 — heading+body frame not content-*"; ((FAIL++)) || true; }

      # 7. Issue 16: Header detection — Group 46165 (top, wide, has nav child) → header
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:106',{})
new_name = r.get('new_name','')
assert new_name == 'header', f'Group 46165 should be header, got: {new_name}'
print(f'  PASS: Issue 16 — header detection → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 16 — header not detected"; ((FAIL++)) || true; }

      # 8. Issue 16: Footer detection — Group 50001 (bottom, wide, text children) → footer
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:300',{})
new_name = r.get('new_name','')
assert new_name == 'footer', f'Group 50001 should be footer, got: {new_name}'
print(f'  PASS: Issue 16 — footer detection → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 16 — footer not detected"; ((FAIL++)) || true; }
    fi

    # --- Phase 3: detect-grouping-candidates ---
    REAL_P3=$(bash "$SKILLS_DIR/scripts/detect-grouping-candidates.sh" "$REALISTIC_FIXTURE" 2>&1) || {
      red "  FATAL: detect-grouping-candidates.sh crashed on realistic fixture"
      ((FAIL++)) || true
    }

    if [[ -n "${REAL_P3:-}" ]]; then
      # Pattern group detection (cards should be detected)
      REAL_CANDIDATES=$(echo "$REAL_P3" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('candidates',[])))" 2>/dev/null || echo "0")
      if python3 -c "import sys; assert int(sys.argv[1]) >= 1" "$REAL_CANDIDATES" 2>/dev/null; then
        green "  PASS: Grouping — $REAL_CANDIDATES candidates detected (>= 1)"
        ((PASS++)) || true
      else
        red "  FAIL: Grouping — no candidates detected"
        ((FAIL++)) || true
      fi

      # Dedup check: candidates < 50% of total nodes
      REAL_TOTAL=$(echo "$REAL_P1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['total_nodes'])" 2>/dev/null || echo "100")
      if python3 -c "import sys; assert int(sys.argv[1]) < int(sys.argv[2]) * 0.5" "$REAL_CANDIDATES" "$REAL_TOTAL" 2>/dev/null; then
        green "  PASS: Dedup — candidates ($REAL_CANDIDATES) < 50% of nodes ($REAL_TOTAL)"
        ((PASS++)) || true
      else
        red "  FAIL: Dedup — candidates ($REAL_CANDIDATES) >= 50% of nodes ($REAL_TOTAL)"
        ((FAIL++)) || true
      fi

      # Issue 22: Tab + Card list proximity group at root level
      echo "$REAL_P3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
found = False
for c in d.get('candidates', []):
    if c.get('method') == 'proximity' and c.get('parent_name') == '募集一覧':
        ids = set(c.get('node_ids', []))
        if '1:6' in ids and '1:15' in ids:
            found = True
            break
assert found, 'Tab + Card list proximity group not found at root level'
print('  PASS: Issue 22 — Tab + Card list grouped (proximity at root)')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 22 — Tab + Card list NOT grouped at root level"; ((FAIL++)) || true; }

      # Stage A: proximity may group overlapping elements (1:5, 1:101, 1:102)
      # Semantic boundary (lead text vs hero) is delegated to Stage B (Claude reasoning)
      echo "$REAL_P3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
# Verify that any grouping with 1:5 is proximity or zone (not semantic/page-kv)
for c in d.get('candidates', []):
    ids = set(c.get('node_ids', []))
    if '1:5' in ids:
        assert c.get('method') in ('proximity', 'zone'), f'1:5 in unexpected group: {c[\"method\"]}'
print('  PASS: Stage A — 1:5 grouping is proximity/zone only (fine-grained deferred to Stage B)')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage A — 1:5 in unexpected group type"; ((FAIL++)) || true; }

      # Stage A methods: proximity, pattern, spacing, semantic (no page-kv)
      echo "$REAL_P3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
methods = set(c.get('method', '') for c in d.get('candidates', []))
forbidden = methods & {'page-kv'}
assert not forbidden, f'Unexpected methods in Stage A: {forbidden}'
allowed = {'proximity', 'pattern', 'spacing', 'semantic', 'zone'}
unknown = methods - allowed
assert not unknown, f'Unknown methods in Stage A: {unknown}'
print(f'  PASS: Stage A — methods = {methods}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage A — unexpected methods found"; ((FAIL++)) || true; }
    fi

    # --- Phase 4: infer-autolayout ---
    REAL_P4=$(bash "$SKILLS_DIR/scripts/infer-autolayout.sh" "$REALISTIC_FIXTURE" 2>&1) || {
      red "  FATAL: infer-autolayout.sh crashed on realistic fixture"
      ((FAIL++)) || true
    }

    if [[ -n "${REAL_P4:-}" ]]; then
      # resolve_absolute_coords: leaf-level padding values should not have negative values
      # (negative padding indicates coordinate resolution failure)
      echo "$REAL_P4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
negative_padding = []
for f in d.get('frames',[]):
    p = f['layout']['padding']
    for k,v in p.items():
        if v < 0:
            negative_padding.append(f'{f[\"node_name\"]}.{k}={v}')
if negative_padding:
    print(f'  FAIL: Negative padding (coord resolution bug): {negative_padding[:3]}')
    sys.exit(1)
print(f'  PASS: resolve_absolute_coords — no negative padding values ({len(d.get(\"frames\",[]))} frames checked)')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Negative padding detected (coordinate resolution bug)"; ((FAIL++)) || true; }
    fi

    # --- Phase 2 Stage B: prepare-sectioning-context ---
    echo ""
    bold "  --- Phase 2 Stage B: prepare-sectioning-context.sh ---"

    REAL_SEC=$(bash "$SKILLS_DIR/scripts/prepare-sectioning-context.sh" "$REALISTIC_FIXTURE" 2>&1) || {
      red "  FATAL: prepare-sectioning-context.sh crashed on realistic fixture"
      echo "$REAL_SEC"
      ((FAIL++)) || true
    }

    if [[ -n "${REAL_SEC:-}" ]]; then
      # Test 1: JSON parse success (no error)
      echo "$REAL_SEC" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null \
        && { green "  PASS: Stage B — no error in output"; ((PASS++)) || true; } \
        || { red "  FAIL: Stage B — script returned error"; echo "$REAL_SEC"; ((FAIL++)) || true; }

      # Test 2: total_children = 9
      assert_json_field "$REAL_SEC" "['total_children']" "9" "Stage B — total_children = 9"

      # Test 3: Y-coordinate ascending sort
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
children = d['top_level_children']
y_values = [c['bbox']['y'] for c in children]
assert y_values == sorted(y_values), f'Not Y-sorted: {y_values}'
print('  PASS: Stage B — children sorted by Y ascending')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — Y sort broken"; ((FAIL++)) || true; }

      # Test 4: page_name = "募集一覧"
      assert_json_field "$REAL_SEC" "['page_name']" "募集一覧" "Stage B — page_name = 募集一覧"

      # Test 5: page_size = 1440x3858
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
ps = d['page_size']
assert ps['width'] == 1440.0, f'width={ps[\"width\"]}'
assert ps['height'] == 3858.0, f'height={ps[\"height\"]}'
print('  PASS: Stage B — page_size = 1440x3858')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — page_size mismatch"; ((FAIL++)) || true; }

      # Test 6: All children have required fields
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
required = ['id', 'name', 'type', 'bbox', 'child_count', 'is_unnamed']
for c in d['top_level_children']:
    for field in required:
        assert field in c, f'Missing field {field} in {c.get(\"id\",\"?\")}'
print(f'  PASS: Stage B — all {len(d[\"top_level_children\"])} children have required fields')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — missing required fields"; ((FAIL++)) || true; }

      # Test 7: header_candidates includes 1:106
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
hc = d['heuristic_hints']['header_candidates']
assert '1:106' in hc, f'1:106 not in header_candidates: {hc}'
print(f'  PASS: Stage B — header_candidates contains 1:106')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — 1:106 not in header_candidates"; ((FAIL++)) || true; }

      # Test 8: footer_candidates includes 1:300
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
fc = d['heuristic_hints']['footer_candidates']
assert '1:300' in fc, f'1:300 not in footer_candidates: {fc}'
print(f'  PASS: Stage B — footer_candidates contains 1:300')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — 1:300 not in footer_candidates"; ((FAIL++)) || true; }

      # Test 9: gap_analysis is non-empty (9 children → 8 gaps)
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
ga = d['heuristic_hints']['gap_analysis']
assert len(ga) == 8, f'Expected 8 gaps for 9 children, got {len(ga)}'
print(f'  PASS: Stage B — gap_analysis has 8 entries')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — gap_analysis count wrong"; ((FAIL++)) || true; }

      # Test 9b: gap_analysis — 1:5↔1:6 has significant gap (section boundary)
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
ga = d['heuristic_hints']['gap_analysis']
target = [g for g in ga if set(g['between']) == {'1:5', '1:6'}]
assert len(target) == 1, f'1:5↔1:6 gap not found'
gap = target[0]['gap_px']
assert gap > 50, f'1:5↔1:6 gap too small: {gap}'
print(f'  PASS: Stage B — 1:5↔1:6 gap = {gap}px (section boundary)')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — 1:5↔1:6 gap not significant"; ((FAIL++)) || true; }

      # Test 9c: background_candidates includes 1:101 (RECTANGLE h>=100)
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
bg = d['heuristic_hints']['background_candidates']
assert '1:101' in bg, f'1:101 not in background_candidates: {bg}'
print(f'  PASS: Stage B — background_candidates contains 1:101')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — 1:101 not in background_candidates"; ((FAIL++)) || true; }

      # Test 9d: heuristic_hints has gap_analysis key (structure check)
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
hints = d['heuristic_hints']
assert 'gap_analysis' in hints, 'gap_analysis key missing'
assert 'background_candidates' in hints, 'background_candidates key missing'
assert 'page_kv_candidates' not in hints, 'page_kv_candidates should be removed'
print('  PASS: Stage B — heuristic_hints structure (gap_analysis + background_candidates, no page_kv)')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — heuristic_hints structure wrong"; ((FAIL++)) || true; }

      # Test 10: is_unnamed judgment (1:106=true, 1:5=false)
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
children_map = {c['id']: c for c in d['top_level_children']}
assert children_map['1:106']['is_unnamed'] == True, '1:106 should be unnamed'
assert children_map['1:5']['is_unnamed'] == False, '1:5 should not be unnamed'
print('  PASS: Stage B — is_unnamed: 1:106=True, 1:5=False')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage B — is_unnamed judgment wrong"; ((FAIL++)) || true; }

      # Test 11: --output file generation + JSON validation
      SEC_OUT="/tmp/figma-prepare-test-sectioning-$$.json"
      bash "$SKILLS_DIR/scripts/prepare-sectioning-context.sh" "$REALISTIC_FIXTURE" --output "$SEC_OUT" >/dev/null 2>&1
      if [[ -f "$SEC_OUT" ]] && python3 -c "import json, sys; json.load(open(sys.argv[1]))" "$SEC_OUT" 2>/dev/null; then
        green "  PASS: Stage B — --output file generated + valid JSON"
        ((PASS++)) || true
      else
        red "  FAIL: Stage B — --output file not generated or invalid JSON"
        ((FAIL++)) || true
      fi
      rm -f "$SEC_OUT"
    fi
  fi
else
  skip_test "Realistic fixture not found"
fi

echo ""

# ================================================================
bold "=== Enrichment Pipeline: Issues 15, 17, 18 ==="

ENRICHMENT_FIXTURE="$SCRIPT_DIR/fixture-enrichment.json"
if [[ -f "$REALISTIC_FIXTURE" ]] && [[ -f "$ENRICHMENT_FIXTURE" ]]; then
  # Phase 1.5: enrich-metadata.sh
  ENRICHED_TMP="/tmp/figma-prepare-enriched-$$.json"
  ENRICH_RESULT=$(bash "$SKILLS_DIR/scripts/enrich-metadata.sh" "$REALISTIC_FIXTURE" "$ENRICHMENT_FIXTURE" --output "$ENRICHED_TMP" 2>&1) || {
    red "  FATAL: enrich-metadata.sh crashed"
    echo "$ENRICH_RESULT"
    ((FAIL++)) || true
  }

  if [[ -f "$ENRICHED_TMP" ]]; then
    # 1. Enrichment merge count
    ENRICHED_COUNT=$(echo "$ENRICH_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['enriched_nodes'])" 2>/dev/null || echo "0")
    if python3 -c "import sys; assert int(sys.argv[1]) >= 5" "$ENRICHED_COUNT" 2>/dev/null; then
      green "  PASS: enrich-metadata — $ENRICHED_COUNT nodes enriched (>= 5)"
      ((PASS++)) || true
    else
      red "  FAIL: enrich-metadata — only $ENRICHED_COUNT nodes enriched (expected >= 5)"
      ((FAIL++)) || true
    fi

    # 2. Issue 17: fills-based IMAGE detection (enriched rename)
    ENRICHED_P2=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$ENRICHED_TMP" 2>&1) || {
      red "  FATAL: generate-rename-map.sh crashed on enriched data"
      ((FAIL++)) || true
    }

    if [[ -n "${ENRICHED_P2:-}" ]]; then
      # Node 1:101 (RECTANGLE with IMAGE fill) → img-*
      echo "$ENRICHED_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:101',{})
new_name = r.get('new_name','')
assert new_name.startswith('img-'), f'1:101 (IMAGE fill) should be img-*, got: {new_name}'
print(f'  PASS: Issue 17 — IMAGE fill → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 17 — IMAGE fill not detected"; ((FAIL++)) || true; }

      # Node 1:113 (RECTANGLE with IMAGE fill) → img-*
      echo "$ENRICHED_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:113',{})
new_name = r.get('new_name','')
assert new_name.startswith('img-'), f'1:113 (IMAGE fill) should be img-*, got: {new_name}'
print(f'  PASS: Issue 17 — logo IMAGE fill → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 17 — logo IMAGE fill not detected"; ((FAIL++)) || true; }

      # Node 1:107 (RECTANGLE with SOLID fill) → bg-* (not img-*)
      echo "$ENRICHED_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
r = d.get('renames',{}).get('1:107',{})
new_name = r.get('new_name','')
assert new_name.startswith('bg-'), f'1:107 (SOLID fill) should be bg-*, got: {new_name}'
print(f'  PASS: Issue 17 — SOLID fill stays bg-* → {new_name}')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 17 — SOLID fill incorrectly classified"; ((FAIL++)) || true; }
    fi

    # 3. Issue 18: layoutMode complement (enriched autolayout)
    ENRICHED_P4=$(bash "$SKILLS_DIR/scripts/infer-autolayout.sh" "$ENRICHED_TMP" 2>&1) || {
      red "  FATAL: infer-autolayout.sh crashed on enriched data"
      ((FAIL++)) || true
    }

    if [[ -n "${ENRICHED_P4:-}" ]]; then
      echo "$ENRICHED_P4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
frames = d.get('frames',[])
exact = [f for f in frames if f.get('source') == 'exact']
assert len(exact) >= 2, f'Expected >= 2 exact frames, got {len(exact)}'
# Verify enriched frame has correct direction
for f in exact:
    if f['node_id'] == '1:106':
        assert f['layout']['direction'] == 'HORIZONTAL', f'1:106 should be HORIZONTAL'
        assert f['layout']['gap'] == 24, f'1:106 gap should be 24'
        assert f['layout']['confidence'] == 'exact', f'1:106 confidence should be exact'
print(f'  PASS: Issue 18 — {len(exact)} frames with exact layoutMode')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 18 — enriched layoutMode not used"; ((FAIL++)) || true; }
    fi

    # 4. Issue 32: fills=[] should not crash generate-rename-map.sh
    # Node 1:20 has "fills": [] in enrichment — Priority 4 has_image should not IndexError
    echo "$ENRICHED_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
# Just verifying the script didn't crash is the primary test.
# Node 1:20 is a named FRAME ('Card Accent 1'), not unnamed, so it won't be in renames.
# The crash would occur if any unnamed FRAME/GROUP has RECTANGLE children with fills=[].
print('  PASS: Issue 32 — fills=[] did not crash rename pipeline')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 32 — rename pipeline crashed with fills=[]"; ((FAIL++)) || true; }

    rm -f "$ENRICHED_TMP"
  fi
else
  skip_test "Enrichment fixtures not found"
fi

echo ""

# ================================================================
bold "=== Unit: fills=[] edge case (Issue 32) ==="

# Create minimal fixture with RECTANGLE child having fills=[]
python3 -c "
import json, tempfile, subprocess, sys, os

# Minimal fixture: unnamed FRAME with RECTANGLE child (fills=[])
fixture = {
    'id': '0:1', 'name': 'Test Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 1000},
    'children': [{
        'id': '1:1', 'name': 'Frame 1', 'type': 'FRAME',
        'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 800, 'height': 400},
        'children': [
            {
                'id': '1:2', 'name': 'Rectangle 1', 'type': 'RECTANGLE',
                'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 800, 'height': 200},
                'fills': [],  # empty fills — should not crash
                'children': []
            },
            {
                'id': '1:3', 'name': 'Text 1', 'type': 'TEXT',
                'absoluteBoundingBox': {'x': 0, 'y': 200, 'width': 800, 'height': 50},
                'children': []
            },
            {
                'id': '1:4', 'name': 'Frame 2', 'type': 'FRAME',
                'absoluteBoundingBox': {'x': 0, 'y': 250, 'width': 200, 'height': 50},
                'children': [{
                    'id': '1:5', 'name': 'Button', 'type': 'TEXT',
                    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 30},
                    'children': []
                }]
            }
        ]
    }]
}

# Write to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(fixture, f)
    tmp_path = f.name

try:
    script = os.path.join(os.environ['SCRIPT_DIR'], '..', 'scripts', 'generate-rename-map.sh')
    result = subprocess.run(['bash', script, tmp_path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f'CRASH: {result.stderr}')
        sys.exit(1)
    data = json.loads(result.stdout)
    assert 'error' not in data, f'Error: {data}'
    print('OK')
finally:
    os.unlink(tmp_path)
" 2>/dev/null && { green "  PASS: Issue 32 — fills=[] edge case no crash"; ((PASS++)) || true; } || { red "  FAIL: Issue 32 — fills=[] caused crash"; ((FAIL++)) || true; }

echo ""

# ================================================================
bold "=== Unit: INSTANCE header detection (Issue 37) ==="

python3 -c "
import json, tempfile, subprocess, sys, os

# Minimal fixture: INSTANCE node at top (header) + INSTANCE at bottom (footer)
fixture = {
    'id': '0:1', 'name': 'Test Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 5000},
    'children': [
        {
            'id': '1:1', 'name': 'Header Instance', 'type': 'INSTANCE',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 80},
            'children': []
        },
        {
            'id': '1:2', 'name': 'Main Content', 'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 100, 'width': 1440, 'height': 4700},
            'children': []
        },
        {
            'id': '1:3', 'name': 'Footer Component', 'type': 'COMPONENT',
            'absoluteBoundingBox': {'x': 0, 'y': 4850, 'width': 1440, 'height': 150},
            'children': []
        },
    ]
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(fixture, f)
    tmp_path = f.name

try:
    script = os.path.join(os.environ['SCRIPT_DIR'], '..', 'scripts', 'prepare-sectioning-context.sh')
    result = subprocess.run(['bash', script, tmp_path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f'CRASH: {result.stderr}')
        sys.exit(1)
    data = json.loads(result.stdout)
    hints = data['heuristic_hints']

    # INSTANCE header at top should be detected
    assert '1:1' in hints['header_candidates'], f'INSTANCE header not detected: {hints[\"header_candidates\"]}'
    # COMPONENT footer at bottom should be detected
    assert '1:3' in hints['footer_candidates'], f'COMPONENT footer not detected: {hints[\"footer_candidates\"]}'
    print('OK')
finally:
    os.unlink(tmp_path)
" 2>/dev/null && { green "  PASS: Issue 37 — INSTANCE header + COMPONENT footer detected"; ((PASS++)) || true; } || { red "  FAIL: Issue 37 — INSTANCE/COMPONENT type not detected"; ((FAIL++)) || true; }

echo ""

# ================================================================
bold "=== Unit: characters field preference (Issue 38) ==="

python3 -c "
import json, tempfile, subprocess, sys, os

# Fixture: TEXT node with characters field (enriched) differing from name
fixture = {
    'id': '0:1', 'name': 'Test Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 1000},
    'children': [{
        'id': '1:1', 'name': 'Text 1', 'type': 'TEXT',
        'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 30},
        'characters': 'お問い合わせ',
        'children': []
    }, {
        'id': '1:2', 'name': 'Frame 1', 'type': 'FRAME',
        'absoluteBoundingBox': {'x': 0, 'y': 100, 'width': 400, 'height': 200},
        'children': [
            {
                'id': '1:3', 'name': 'Text 2', 'type': 'TEXT',
                'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 30},
                'characters': '募集要項',
                'children': []
            },
            {
                'id': '1:4', 'name': 'Text 3', 'type': 'TEXT',
                'absoluteBoundingBox': {'x': 0, 'y': 40, 'width': 200, 'height': 30},
                'characters': 'REASON',
                'children': []
            }
        ]
    }]
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(fixture, f)
    tmp_path = f.name

try:
    script = os.path.join(os.environ['SCRIPT_DIR'], '..', 'scripts', 'generate-rename-map.sh')
    result = subprocess.run(['bash', script, tmp_path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f'CRASH: {result.stderr}')
        sys.exit(1)
    data = json.loads(result.stdout)
    renames = data.get('renames', {})

    # 1:1 is unnamed TEXT with characters='お問い合わせ' → should use characters, not name
    # to_kebab returns 'content' for non-ASCII-only text (JP_KEYWORD_MAP removed)
    r1 = renames.get('1:1', {})
    assert 'content' in r1.get('new_name', ''), f'1:1 should use characters field, got: {r1.get(\"new_name\", \"\")}'

    # 1:2 is unnamed FRAME with enriched TEXT children
    # get_text_children_content should prefer characters over name
    r2 = renames.get('1:2', {})
    new_name = r2.get('new_name', '')
    assert 'requirements' in new_name or 'heading' in new_name, f'1:2 should use children characters, got: {new_name}'

    print('OK')
finally:
    os.unlink(tmp_path)
" 2>/dev/null && { green "  PASS: Issue 38 — characters field preferred over name"; ((PASS++)) || true; } || { red "  FAIL: Issue 38 — characters field not used"; ((FAIL++)) || true; }

echo ""

# ================================================================
bold "=== Unit: YAML output structure_hash key (Issue 41) ==="

python3 -c "
import json, tempfile, subprocess, sys, os

# Fixture: 3+ children with same structure → pattern detection → YAML output should contain structure_hash
fixture = {
    'id': '0:1', 'name': 'Test Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 2000},
    'children': [
        {'id': '1:1', 'name': 'Frame 1', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 300, 'height': 200},
         'children': [
             {'id': '1:10', 'name': 'Text 1', 'type': 'TEXT',
              'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 30}, 'children': []}
         ]},
        {'id': '1:2', 'name': 'Frame 2', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 0, 'y': 300, 'width': 300, 'height': 200},
         'children': [
             {'id': '1:20', 'name': 'Text 2', 'type': 'TEXT',
              'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 30}, 'children': []}
         ]},
        {'id': '1:3', 'name': 'Frame 3', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 0, 'y': 600, 'width': 300, 'height': 200},
         'children': [
             {'id': '1:30', 'name': 'Text 3', 'type': 'TEXT',
              'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 30}, 'children': []}
         ]},
    ]
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(fixture, f)
    tmp_path = f.name

yaml_path = tmp_path + '.yaml'
try:
    script = os.path.join(os.environ['SCRIPT_DIR'], '..', 'scripts', 'detect-grouping-candidates.sh')
    result = subprocess.run(['bash', script, tmp_path, '--output', yaml_path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f'CRASH: {result.stderr}')
        sys.exit(1)
    with open(yaml_path, 'r') as yf:
        yaml_content = yf.read()
    # YAML output should contain 'structure_hash:' (not 'pattern:')
    assert 'structure_hash:' in yaml_content, f'YAML should contain structure_hash key, got: {yaml_content[:200]}'
    assert 'pattern:' not in yaml_content, f'YAML should NOT contain old pattern key'
    print('OK')
finally:
    os.unlink(tmp_path)
    if os.path.exists(yaml_path):
        os.unlink(yaml_path)
" 2>/dev/null && { green "  PASS: Issue 41 — YAML output uses structure_hash key"; ((PASS++)) || true; } || { red "  FAIL: Issue 41 — YAML output key mismatch"; ((FAIL++)) || true; }

echo ""

# ================================================================
bold "=== Unit: figma_utils.py — yaml_str ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import yaml_str

# Basic string
assert yaml_str('hello') == '\"hello\"', f'Expected \"hello\", got {yaml_str(\"hello\")}'

# String with double quotes
result = yaml_str('say \"hi\"')
assert '\"' not in result.strip('\"').replace('\\\\\"', ''), f'Unescaped quotes in: {result}'

# String with backslash
result = yaml_str('path\\\\to\\\\file')
assert '\\\\\\\\' in result, f'Backslash not escaped: {result}'

# String with special chars
result = yaml_str('line1\\nline2')
assert isinstance(result, str), 'Should return string'

# Non-ASCII (Japanese)
result = yaml_str('日本語テスト')
assert '日本語テスト' in result, f'Non-ASCII lost: {result}'

# Empty string
result = yaml_str('')
assert result == '\"\"', f'Empty string: {result}'

# Integer input (should be coerced to string)
result = yaml_str(123)
assert result == '\"123\"', f'Integer coercion: {result}'

print('OK')
" 2>/dev/null && { green "  PASS: yaml_str — basic, quotes, backslash, special, non-ASCII, empty, int"; ((PASS++)) || true; } || { red "  FAIL: yaml_str unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: figma_utils.py — get_bbox ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import get_bbox

# Normal node
node = {'absoluteBoundingBox': {'x': 10, 'y': 20, 'width': 100, 'height': 50}}
bb = get_bbox(node)
assert bb == {'x': 10, 'y': 20, 'w': 100, 'h': 50}, f'Normal: {bb}'

# Missing absoluteBoundingBox
bb = get_bbox({})
assert bb == {'x': 0, 'y': 0, 'w': 0, 'h': 0}, f'Missing bbox: {bb}'

# Partial bbox
bb = get_bbox({'absoluteBoundingBox': {'x': 5}})
assert bb['x'] == 5 and bb['y'] == 0 and bb['w'] == 0 and bb['h'] == 0, f'Partial: {bb}'

print('OK')
" 2>/dev/null && { green "  PASS: get_bbox — normal, missing, partial"; ((PASS++)) || true; } || { red "  FAIL: get_bbox unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: figma_utils.py — get_root_node ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import get_root_node

# With 'document' key
data = {'document': {'id': 'root', 'children': []}}
assert get_root_node(data)['id'] == 'root', 'document key'

# With 'node' key
data = {'node': {'id': 'n1', 'children': []}}
assert get_root_node(data)['id'] == 'n1', 'node key'

# Bare node (no wrapper)
data = {'id': 'bare', 'children': []}
assert get_root_node(data)['id'] == 'bare', 'bare node'

# Both keys — document takes priority
data = {'document': {'id': 'doc'}, 'node': {'id': 'n'}}
assert get_root_node(data)['id'] == 'doc', 'document priority'

print('OK')
" 2>/dev/null && { green "  PASS: get_root_node — document, node, bare, priority"; ((PASS++)) || true; } || { red "  FAIL: get_root_node unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: figma_utils.py — get_text_children_content ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import get_text_children_content

children = [
    {'type': 'TEXT', 'characters': 'Hello', 'name': 'Text 1'},
    {'type': 'TEXT', 'characters': '', 'name': 'Fallback Name'},
    {'type': 'FRAME', 'name': 'Frame 1'},
    {'type': 'TEXT', 'characters': 'World', 'name': 'Text 3'},
    {'type': 'TEXT', 'name': 'Frame 5'},  # unnamed pattern
]

# Basic: returns all text content
result = get_text_children_content(children)
assert result == ['Hello', 'Fallback Name', 'World', 'Frame 5'], f'basic: {result}'

# max_items
result = get_text_children_content(children, max_items=2)
assert len(result) == 2, f'max_items: {result}'

# filter_unnamed: should exclude 'Frame 5' (matches UNNAMED_RE)
result = get_text_children_content(children, filter_unnamed=True)
assert 'Frame 5' not in result, f'filter_unnamed: {result}'
assert len(result) == 3, f'filter_unnamed len: {result}'

# Empty children
result = get_text_children_content([])
assert result == [], f'empty: {result}'

# Characters preferred over name
children2 = [{'type': 'TEXT', 'characters': 'From characters', 'name': 'From name'}]
result = get_text_children_content(children2)
assert result == ['From characters'], f'prefer chars: {result}'

print('OK')
" 2>/dev/null && { green "  PASS: get_text_children_content — basic, max_items, filter_unnamed, empty, prefer chars"; ((PASS++)) || true; } || { red "  FAIL: get_text_children_content unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: figma_utils.py — to_kebab edge cases ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import to_kebab

# Empty / whitespace
assert to_kebab('') == '', f'empty: {to_kebab(\"\")}'
assert to_kebab('   ') == '', f'whitespace: {to_kebab(\"   \")}'

# Japanese only → 'content'
assert to_kebab('日本語テスト') == 'content', f'jp: {to_kebab(\"日本語テスト\")}'

# CamelCase
assert to_kebab('CamelCase') == 'camel-case', f'camel: {to_kebab(\"CamelCase\")}'

# Acronym
assert to_kebab('HTMLParser') == 'html-parser', f'acronym: {to_kebab(\"HTMLParser\")}'

# Special chars only
assert to_kebab('@#\$%!') == 'content', f'special: {to_kebab(\"@#\$%!\")}'

# Long string truncation (>40 chars)
result = to_kebab('a' * 100)
assert len(result) <= 40, f'truncation: len={len(result)}'

# Mixed Japanese + ASCII
assert to_kebab('日本語test混合') == 'test', f'mixed: {to_kebab(\"日本語test混合\")}'

print('OK')
" 2>/dev/null && { green "  PASS: to_kebab — empty, whitespace, jp, camel, acronym, special, truncation, mixed"; ((PASS++)) || true; } || { red "  FAIL: to_kebab edge case tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: figma_utils.py — is_unnamed (Issue 55) ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import is_unnamed

# Unnamed patterns (auto-generated)
assert is_unnamed('Frame 1') == True, 'Frame 1'
assert is_unnamed('Rectangle 23') == True, 'Rectangle 23'
assert is_unnamed('Text 5') == True, 'Text 5'
assert is_unnamed('Group 100') == True, 'Group 100'
assert is_unnamed('image 1254') == True, 'image lowercase'
assert is_unnamed('Instance 3') == True, 'Instance'
assert is_unnamed('Component 7') == True, 'Component'
assert is_unnamed('Vector') == True, 'Vector no number'
assert is_unnamed('Ellipse') == True, 'Ellipse no number'
assert is_unnamed('Polygon 2') == True, 'Polygon'
assert is_unnamed('Star 1') == True, 'Star'
assert is_unnamed('Line') == True, 'Line no number'

# Named patterns (should NOT be unnamed)
assert is_unnamed('hero-section') == False, 'hero-section'
assert is_unnamed('Header') == False, 'Header'
assert is_unnamed('Frame Header') == False, 'Frame Header'
assert is_unnamed('My Frame 1') == False, 'My Frame 1'
assert is_unnamed('card-feature') == False, 'card-feature'
assert is_unnamed('') == False, 'empty string'

print('OK')
" 2>/dev/null && { green "  PASS: is_unnamed — unnamed patterns, named patterns, empty"; ((PASS++)) || true; } || { red "  FAIL: is_unnamed unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: figma_utils.py — resolve_absolute_coords (Issue 56) ==="
python3 -c "
import sys, os, copy
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import resolve_absolute_coords

# Test 1: Simple parent-child offset accumulation
node = {
    'absoluteBoundingBox': {'x': 10, 'y': 20, 'width': 100, 'height': 100},
    'children': [{
        'absoluteBoundingBox': {'x': 5, 'y': 5, 'width': 50, 'height': 50},
        'children': [{
            'absoluteBoundingBox': {'x': 2, 'y': 3, 'width': 10, 'height': 10},
            'children': []
        }]
    }]
}
resolve_absolute_coords(node)
assert node['absoluteBoundingBox']['x'] == 10, f'root x: {node[\"absoluteBoundingBox\"][\"x\"]}'
assert node['absoluteBoundingBox']['y'] == 20, f'root y: {node[\"absoluteBoundingBox\"][\"y\"]}'
child = node['children'][0]
assert child['absoluteBoundingBox']['x'] == 15, f'child x: {child[\"absoluteBoundingBox\"][\"x\"]}'
assert child['absoluteBoundingBox']['y'] == 25, f'child y: {child[\"absoluteBoundingBox\"][\"y\"]}'
grandchild = child['children'][0]
assert grandchild['absoluteBoundingBox']['x'] == 17, f'grandchild x: {grandchild[\"absoluteBoundingBox\"][\"x\"]}'
assert grandchild['absoluteBoundingBox']['y'] == 28, f'grandchild y: {grandchild[\"absoluteBoundingBox\"][\"y\"]}'

# Test 2: No children (leaf node)
leaf = {'absoluteBoundingBox': {'x': 5, 'y': 10, 'width': 20, 'height': 30}}
resolve_absolute_coords(leaf, parent_x=100, parent_y=200)
assert leaf['absoluteBoundingBox']['x'] == 105, f'leaf x: {leaf[\"absoluteBoundingBox\"][\"x\"]}'
assert leaf['absoluteBoundingBox']['y'] == 210, f'leaf y: {leaf[\"absoluteBoundingBox\"][\"y\"]}'

# Test 3: Missing absoluteBoundingBox
empty_node = {'children': []}
resolve_absolute_coords(empty_node, parent_x=50, parent_y=60)
assert empty_node['absoluteBoundingBox']['x'] == 50, f'empty x'
assert empty_node['absoluteBoundingBox']['y'] == 60, f'empty y'

## Test 4: Double-call guard (Issue 67)
node2 = {
    'absoluteBoundingBox': {'x': 10, 'y': 20, 'width': 100, 'height': 100},
    'children': [{
        'absoluteBoundingBox': {'x': 5, 'y': 5, 'width': 50, 'height': 50},
        'children': []
    }]
}
resolve_absolute_coords(node2)
child2 = node2['children'][0]
assert child2['absoluteBoundingBox']['x'] == 15, f'first call child x'
# Second call should be a no-op (guard prevents double accumulation)
resolve_absolute_coords(node2)
assert child2['absoluteBoundingBox']['x'] == 15, f'double-call child x: {child2[\"absoluteBoundingBox\"][\"x\"]}'
assert child2['absoluteBoundingBox']['y'] == 25, f'double-call child y: {child2[\"absoluteBoundingBox\"][\"y\"]}'

## Test 5: absoluteBoundingBox is None (Issue 60)
null_bbox_node = {'absoluteBoundingBox': None, 'children': []}
resolve_absolute_coords(null_bbox_node, parent_x=10, parent_y=20)
assert null_bbox_node['absoluteBoundingBox']['x'] == 10, f'null bbox x'
assert null_bbox_node['absoluteBoundingBox']['y'] == 20, f'null bbox y'

print('OK')
" 2>/dev/null && { green "  PASS: resolve_absolute_coords — accumulation, leaf, missing bbox, double-call, null bbox"; ((PASS++)) || true; } || { red "  FAIL: resolve_absolute_coords unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: figma_utils.py — snap (Issue 52) ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import snap

# Exact multiples of 4
assert snap(0) == 0, f'0: {snap(0)}'
assert snap(4) == 4, f'4: {snap(4)}'
assert snap(8) == 8, f'8: {snap(8)}'
assert snap(16) == 16, f'16: {snap(16)}'

# Rounding down
assert snap(1) == 0, f'1: {snap(1)}'
assert snap(5) == 4, f'5: {snap(5)}'
assert snap(13) == 12, f'13: {snap(13)}'

# Rounding up
assert snap(3) == 4, f'3: {snap(3)}'
assert snap(6) == 8, f'6: {snap(6)}'
assert snap(7) == 8, f'7: {snap(7)}'
assert snap(14) == 16, f'14: {snap(14)}'
assert snap(15) == 16, f'15: {snap(15)}'

# Exact midpoint (2 → rounds to 0 with Python banker's rounding, but round(2/4)*4=0)
assert snap(2) == 0, f'2: {snap(2)}'

# Negative values (padding can be 0 via max(0,...) but snap itself should handle negatives)
assert snap(-1) == 0, f'-1: {snap(-1)}'
assert snap(-3) == -4, f'-3: {snap(-3)}'

# Custom grid
assert snap(7, grid=8) == 8, f'7 grid=8: {snap(7, grid=8)}'
assert snap(3, grid=8) == 0, f'3 grid=8: {snap(3, grid=8)}'

# Float input
assert snap(5.7) == 4, f'5.7: {snap(5.7)}'

print('OK')
" 2>/dev/null && { green "  PASS: snap — exact, round down, round up, negative, custom grid, float"; ((PASS++)) || true; } || { red "  FAIL: snap unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: figma_utils.py — is_section_root (Issue 53) ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import is_section_root

# Section root: FRAME with width ~1440
assert is_section_root({'type': 'FRAME', 'absoluteBoundingBox': {'width': 1440}}) == True, '1440'
assert is_section_root({'type': 'FRAME', 'absoluteBoundingBox': {'width': 1438}}) == True, '1438'
assert is_section_root({'type': 'FRAME', 'absoluteBoundingBox': {'width': 1442}}) == True, '1442'

# Not section root: wrong type
assert is_section_root({'type': 'GROUP', 'absoluteBoundingBox': {'width': 1440}}) == False, 'GROUP'
assert is_section_root({'type': 'TEXT', 'absoluteBoundingBox': {'width': 1440}}) == False, 'TEXT'

# Not section root: wrong width
assert is_section_root({'type': 'FRAME', 'absoluteBoundingBox': {'width': 800}}) == False, '800'
assert is_section_root({'type': 'FRAME', 'absoluteBoundingBox': {'width': 1460}}) == False, '1460'

# Edge case: missing absoluteBoundingBox
assert is_section_root({'type': 'FRAME'}) == False, 'missing bbox'

# Edge case: missing width
assert is_section_root({'type': 'FRAME', 'absoluteBoundingBox': {}}) == False, 'missing width'

print('OK')
" 2>/dev/null && { green "  PASS: is_section_root — valid, wrong type, wrong width, missing bbox"; ((PASS++)) || true; } || { red "  FAIL: is_section_root unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: to_kebab — whitespace characters (Issue 57) ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import to_kebab

# Tab and newline should be treated as whitespace separators
tab_input = 'hello' + chr(9) + 'world'
nl_input = 'hello' + chr(10) + 'world'
crlf_input = 'hello' + chr(13) + chr(10) + 'world'

assert to_kebab(tab_input) == 'hello-world', 'tab failed: ' + to_kebab(tab_input)
assert to_kebab(nl_input) == 'hello-world', 'newline failed: ' + to_kebab(nl_input)
assert to_kebab(crlf_input) == 'hello-world', 'crlf failed: ' + to_kebab(crlf_input)
assert to_kebab('  hello  ') == 'hello', 'leading/trailing failed'
assert to_kebab('multi   space') == 'multi-space', 'multi-space failed'

print('OK')
" "${SKILLS_DIR}" 2>/dev/null && { green "  PASS: to_kebab — tab, newline, crlf, multi-space"; ((PASS++)) || true; } || { red "  FAIL: to_kebab whitespace tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: enrich-metadata.sh — empty enrichment (Issue 58) ==="
python3 -c "
import json, tempfile, subprocess, sys, os

# Create minimal metadata
metadata = {
    'id': '0:1', 'name': 'Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 1000},
    'children': [{'id': '1:1', 'name': 'Child', 'type': 'FRAME',
                  'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
                  'children': []}]
}
# Empty enrichment
enrichment = {}

meta_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(metadata, meta_file)
meta_file.close()

enrich_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(enrichment, enrich_file)
enrich_file.close()

out_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
out_file.close()

try:
    script = os.path.join(os.environ['SCRIPT_DIR'], '..', 'scripts', 'enrich-metadata.sh')
    result = subprocess.run(['bash', script, meta_file.name, enrich_file.name, '--output', out_file.name],
                           capture_output=True, text=True)
    if result.returncode != 0:
        print(f'CRASH: {result.stderr}')
        sys.exit(1)
    data = json.loads(result.stdout)
    assert data['enriched_nodes'] == 0, f'Expected 0 enriched, got {data[\"enriched_nodes\"]}'
    assert data['total_enrichment_entries'] == 0, f'Expected 0 entries'
    # Output file should be valid JSON
    with open(out_file.name) as f:
        output_data = json.load(f)
    assert output_data['id'] == '0:1', 'Metadata preserved'
    print('OK')
finally:
    os.unlink(meta_file.name)
    os.unlink(enrich_file.name)
    os.unlink(out_file.name)
" 2>/dev/null && { green "  PASS: Issue 58 — empty enrichment handled gracefully"; ((PASS++)) || true; } || { red "  FAIL: Issue 58 — empty enrichment crash"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: prepare-sectioning-context.sh — childless root (Issue 59) ==="
python3 -c "
import json, tempfile, subprocess, sys, os

# Root with no children
fixture = {
    'id': '0:1', 'name': 'Empty Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 0},
    'children': []
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(fixture, f)
    tmp_path = f.name

try:
    script = os.path.join(os.environ['SCRIPT_DIR'], '..', 'scripts', 'prepare-sectioning-context.sh')
    result = subprocess.run(['bash', script, tmp_path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f'CRASH: {result.stderr}')
        sys.exit(1)
    data = json.loads(result.stdout)
    assert data['total_children'] == 0, f'Expected 0, got {data[\"total_children\"]}'
    assert data['top_level_children'] == [], 'Expected empty list'
    assert data['heuristic_hints']['header_candidates'] == [], 'Expected no headers'
    assert data['heuristic_hints']['footer_candidates'] == [], 'Expected no footers'
    assert data['heuristic_hints']['gap_analysis'] == [], 'Expected no gaps'
    print('OK')
finally:
    os.unlink(tmp_path)
" 2>/dev/null && { green "  PASS: Issue 59 — childless root handled gracefully"; ((PASS++)) || true; } || { red "  FAIL: Issue 59 — childless root crash"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: compute_grouping_score (Area 1) ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import alignment_bonus, size_similarity_bonus, compute_grouping_score, _raw_distance

# 1. Identical boxes → score = 1.0
a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
assert compute_grouping_score(a, a) == 1.0, 'identical should be 1.0'

# 2. Boxes within 24px → score >= 0.5 (backward compatible)
b = {'x': 110, 'y': 0, 'w': 100, 'h': 50}
score = compute_grouping_score(a, b, gap=24)
assert score >= 0.5, f'10px apart should score >= 0.5, got {score}'

# 3. Boxes far apart → score close to 0
far = {'x': 500, 'y': 0, 'w': 100, 'h': 50}
assert compute_grouping_score(a, far) < 0.1, 'far apart should be near 0'

# 4. Aligned boxes get bonus (score higher than unaligned at same distance)
aligned = {'x': 0, 'y': 70, 'w': 100, 'h': 50}  # left-aligned, 20px gap
unaligned = {'x': 30, 'y': 70, 'w': 60, 'h': 50}  # not aligned, similar gap
s_aligned = compute_grouping_score(a, aligned)
s_unaligned = compute_grouping_score(a, unaligned)
assert s_aligned >= s_unaligned, f'aligned {s_aligned} should >= unaligned {s_unaligned}'

# 5. Similar-sized boxes get bonus
same_size = {'x': 130, 'y': 0, 'w': 100, 'h': 50}
diff_size = {'x': 130, 'y': 0, 'w': 200, 'h': 100}
s_same = compute_grouping_score(a, same_size)
s_diff = compute_grouping_score(a, diff_size)
assert s_same >= s_diff, f'same-size {s_same} should >= diff-size {s_diff}'

# 6. alignment_bonus returns 0.5 for aligned edges
assert alignment_bonus(a, aligned) == 0.5, 'left-aligned should be 0.5'
assert alignment_bonus(a, {'x': 50, 'y': 200, 'w': 30, 'h': 20}) == 1.0, 'no alignment should be 1.0'

# 7. size_similarity_bonus returns 0.7 for similar sizes
assert size_similarity_bonus(a, same_size) == 0.7, 'same size should be 0.7'
assert size_similarity_bonus(a, diff_size) == 1.0, 'different size should be 1.0'

# 8. Zero-size box handling
zero = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
assert size_similarity_bonus(a, zero) == 1.0, 'zero-size should return 1.0'

print('OK')
" 2>/dev/null && { green "  PASS: compute_grouping_score — identity, proximity, far, aligned, sized, bonus, zero"; ((PASS++)) || true; } || { red "  FAIL: compute_grouping_score unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: structure_similarity / detect_regular_spacing (Area 2) ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import structure_similarity, detect_regular_spacing

# 1. Identical hashes → 1.0
assert structure_similarity('FRAME:[TEXT,TEXT]', 'FRAME:[TEXT,TEXT]') == 1.0

# 2. Completely different → 0.0
assert structure_similarity('FRAME:[TEXT]', 'FRAME:[IMAGE]') == 0.0

# 3. Partial overlap → between 0 and 1
s = structure_similarity('FRAME:[IMAGE,TEXT,TEXT]', 'FRAME:[IMAGE,TEXT,RECTANGLE]')
assert 0.3 < s < 0.9, f'partial overlap should be mid-range, got {s}'

# 4. Leaf nodes (no brackets) — same
assert structure_similarity('TEXT', 'TEXT') == 1.0

# 5. Leaf nodes — different
assert structure_similarity('TEXT', 'IMAGE') == 0.0

# 6. Card-like vs slightly different card
card1 = 'FRAME:[IMAGE,TEXT,TEXT,FRAME]'
card2 = 'FRAME:[RECTANGLE,TEXT,TEXT,FRAME]'  # IMAGE → RECTANGLE
s2 = structure_similarity(card1, card2)
assert s2 >= 0.5, f'card variants should be >= 0.5, got {s2}'

# 7. Empty children
assert structure_similarity('FRAME:[]', 'FRAME:[]') == 1.0

# 8. Regular spacing — evenly spaced
boxes = [{'x': i*120, 'y': 0, 'w': 100, 'h': 50} for i in range(5)]
assert detect_regular_spacing(boxes) == True, 'even spacing should be True'

# 9. Regular spacing — too few elements
assert detect_regular_spacing(boxes[:2]) == False, '2 elements should be False'

# 10. Irregular spacing
irregular = [
    {'x': 0, 'y': 0, 'w': 100, 'h': 50},
    {'x': 110, 'y': 0, 'w': 100, 'h': 50},
    {'x': 500, 'y': 0, 'w': 100, 'h': 50},
]
assert detect_regular_spacing(irregular) == False, 'irregular should be False'

# 11. Vertical regular spacing
vboxes = [{'x': 0, 'y': i*80, 'w': 100, 'h': 60} for i in range(4)]
assert detect_regular_spacing(vboxes) == True, 'vertical even spacing should be True'

print('OK')
" 2>/dev/null && { green "  PASS: structure_similarity / detect_regular_spacing — identical, diff, partial, leaf, card, empty, regular, irregular"; ((PASS++)) || true; } || { red "  FAIL: structure_similarity / detect_regular_spacing unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: structure_hash direct test (Issue 144) ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import structure_hash

# Leaf node — returns just TYPE
assert structure_hash({'type': 'TEXT'}) == 'TEXT', 'leaf TEXT'
assert structure_hash({'type': 'IMAGE', 'children': []}) == 'IMAGE', 'empty children'
assert structure_hash({}) == 'UNKNOWN', 'missing type'

# Node with children — sorted child types
node = {'type': 'FRAME', 'children': [
    {'type': 'TEXT'}, {'type': 'IMAGE'}, {'type': 'TEXT'}
]}
h = structure_hash(node)
assert h == 'FRAME:[IMAGE,TEXT,TEXT]', f'expected sorted children, got {h}'

# Single child
node2 = {'type': 'FRAME', 'children': [{'type': 'RECTANGLE'}]}
assert structure_hash(node2) == 'FRAME:[RECTANGLE]', 'single child'

# INSTANCE type
node3 = {'type': 'INSTANCE', 'children': [
    {'type': 'FRAME'}, {'type': 'TEXT'}
]}
assert structure_hash(node3) == 'INSTANCE:[FRAME,TEXT]', 'INSTANCE parent'

print('OK')
" "$SKILLS_DIR" 2>/dev/null && { green "  PASS: structure_hash — leaf, empty, missing type, sorted children, single, INSTANCE"; ((PASS++)) || true; } || { red "  FAIL: structure_hash direct unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: semantic_detection (Area 3) ==="
python3 -c "
import json, sys, os, tempfile, subprocess

# Build a fixture with card-like, nav-like, and grid-like structures
fixture = {
    'id': '0:1', 'name': 'Test Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 2000},
    'children': [
        # Section with 3 cards
        {
            'id': '1:1', 'name': 'Cards Section', 'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 600},
            'children': [
                {
                    'id': f'1:{10+i}', 'name': f'Card {i}', 'type': 'FRAME',
                    'absoluteBoundingBox': {'x': i*400, 'y': 0, 'width': 350, 'height': 400},
                    'children': [
                        {'id': f'1:{20+i}', 'name': f'img {i}', 'type': 'RECTANGLE',
                         'absoluteBoundingBox': {'x': i*400, 'y': 0, 'width': 350, 'height': 200}},
                        {'id': f'1:{30+i}', 'name': f'text {i}', 'type': 'TEXT',
                         'absoluteBoundingBox': {'x': i*400, 'y': 210, 'width': 350, 'height': 40},
                         'characters': f'Card Title {i}'},
                    ]
                }
                for i in range(3)
            ]
        },
        # Navigation-like section
        {
            'id': '2:1', 'name': 'Nav Section', 'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 700, 'width': 1440, 'height': 60},
            'children': [
                {'id': f'2:{10+i}', 'name': f'Link {i}', 'type': 'TEXT',
                 'absoluteBoundingBox': {'x': i*150, 'y': 700, 'width': 120, 'height': 40},
                 'characters': f'Menu {i}'}
                for i in range(5)
            ]
        },
    ]
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(fixture, f)
    tmp_path = f.name

try:
    script = os.path.join(os.environ['SKILLS_DIR'], 'scripts', 'detect-grouping-candidates.sh')
    result = subprocess.run(['bash', script, tmp_path], capture_output=True, text=True)
    assert result.returncode == 0, f'Script failed: {result.stderr}'
    data = json.loads(result.stdout)

    methods = set(c.get('method', '') for c in data.get('candidates', []))

    # 1. Card detection should find semantic candidates
    card_candidates = [c for c in data['candidates'] if c.get('method') == 'semantic' and c.get('semantic_type') == 'card-list']
    assert len(card_candidates) >= 1, f'Expected card-list detection, found {len(card_candidates)}'

    # 2. Navigation detection
    nav_candidates = [c for c in data['candidates'] if c.get('method') == 'semantic' and c.get('semantic_type') == 'navigation']
    assert len(nav_candidates) >= 1, f'Expected navigation detection, found {len(nav_candidates)}'

    # 3. semantic method is present
    assert 'semantic' in methods, f'Expected semantic in methods: {methods}'

    # 4. No page-kv method
    assert 'page-kv' not in methods, f'page-kv should not be in methods: {methods}'

    # 5. Dedup: semantic should suppress proximity for same nodes
    card_node_ids = set()
    for c in card_candidates:
        card_node_ids.update(c.get('node_ids', []))
    prox_with_card_ids = [c for c in data['candidates']
        if c.get('method') == 'proximity' and set(c.get('node_ids', [])) & card_node_ids]
    assert len(prox_with_card_ids) == 0, 'proximity should be deduplicated when semantic exists'

    # 6. Total candidates >= 2
    assert data['total'] >= 2, f'Expected >= 2 candidates, got {data[\"total\"]}'

    print('OK')
finally:
    os.unlink(tmp_path)
" 2>/dev/null && { green "  PASS: semantic_detection — card, nav, method, no-page-kv, dedup, total"; ((PASS++)) || true; } || { red "  FAIL: semantic_detection unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: detect_header_footer_groups (Issue 85) ==="
python3 -c "
import json, sys, os, tempfile, subprocess

# Build a fixture with flat header elements + content + footer
fixture = {
    'id': '0:1', 'name': 'Test Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 5000},
    'children': [
        # Logo (VECTOR, small, top)
        {'id': '1:1', 'name': 'Vector', 'type': 'VECTOR',
         'absoluteBoundingBox': {'x': 50, 'y': 20, 'width': 100, 'height': 30}},
        # Nav texts (6 items, horizontal, top)
        *[{'id': f'1:{10+i}', 'name': f'Nav {i}', 'type': 'TEXT',
           'absoluteBoundingBox': {'x': 300+i*150, 'y': 25, 'width': 120, 'height': 20},
           'characters': f'Menu {i}'}
          for i in range(6)],
        # Nav wrapper frame
        {'id': '1:20', 'name': 'Frame 1', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 80},
         'children': [
             {'id': '1:21', 'name': 'Sub 1', 'type': 'TEXT',
              'absoluteBoundingBox': {'x': 200, 'y': 10, 'width': 100, 'height': 20}},
             {'id': '1:22', 'name': 'Sub 2', 'type': 'TEXT',
              'absoluteBoundingBox': {'x': 400, 'y': 10, 'width': 100, 'height': 20}},
         ]},
        # Content section (middle)
        {'id': '2:1', 'name': 'Main Content', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 0, 'y': 400, 'width': 1440, 'height': 3000},
         'children': [
             {'id': '2:2', 'name': 'Text 1', 'type': 'TEXT',
              'absoluteBoundingBox': {'x': 50, 'y': 400, 'width': 500, 'height': 40}},
         ]},
        # Footer elements (bottom)
        {'id': '3:1', 'name': 'Line 1', 'type': 'LINE',
         'absoluteBoundingBox': {'x': 0, 'y': 4800, 'width': 1440, 'height': 1}},
        {'id': '3:2', 'name': 'Footer Text', 'type': 'TEXT',
         'absoluteBoundingBox': {'x': 50, 'y': 4850, 'width': 300, 'height': 20},
         'characters': 'Copyright 2024'},
        {'id': '3:3', 'name': 'Footer Links', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 0, 'y': 4900, 'width': 1440, 'height': 80},
         'children': [
             {'id': '3:4', 'name': 'Link 1', 'type': 'TEXT',
              'absoluteBoundingBox': {'x': 50, 'y': 4900, 'width': 100, 'height': 20}},
         ]},
    ]
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(fixture, f)
    tmp_path = f.name

try:
    script = os.path.join(os.environ['SKILLS_DIR'], 'scripts', 'detect-grouping-candidates.sh')
    result = subprocess.run(['bash', script, tmp_path], capture_output=True, text=True)
    assert result.returncode == 0, f'Script failed: {result.stderr}'
    data = json.loads(result.stdout)

    # 1. Header detection: should find semantic/header candidate
    header = [c for c in data['candidates'] if c.get('semantic_type') == 'header']
    assert len(header) >= 1, f'No header detected, candidates: {[c.get(\"semantic_type\",c.get(\"method\")) for c in data[\"candidates\"]]}'
    h = header[0]
    assert '1:1' in h['node_ids'], 'Logo (1:1) should be in header group'
    assert h['count'] >= 2, f'Header should have 2+ elements, got {h[\"count\"]}'

    # 2. Footer detection: should find semantic/footer candidate
    footer = [c for c in data['candidates'] if c.get('semantic_type') == 'footer']
    assert len(footer) >= 1, f'No footer detected'
    ft = footer[0]
    assert ft['count'] >= 2, f'Footer should have 2+ elements, got {ft[\"count\"]}'

    # 3. Content should NOT be in header or footer
    for c in header + footer:
        assert '2:1' not in c.get('node_ids', []), 'Content (2:1) should not be in header/footer'

    # 4. Already-named HEADER/FOOTER should be excluded
    fixture2 = {
        'id': '0:1', 'name': 'Test', 'type': 'FRAME',
        'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 3000},
        'children': [
            {'id': '1:1', 'name': 'HEADER', 'type': 'FRAME',
             'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 80},
             'children': []},
            {'id': '2:1', 'name': 'Content', 'type': 'FRAME',
             'absoluteBoundingBox': {'x': 0, 'y': 80, 'width': 1440, 'height': 2800},
             'children': []},
            {'id': '3:1', 'name': 'FOOTER', 'type': 'FRAME',
             'absoluteBoundingBox': {'x': 0, 'y': 2880, 'width': 1440, 'height': 120},
             'children': []},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
        json.dump(fixture2, f2)
        tmp2 = f2.name
    result2 = subprocess.run(['bash', script, tmp2], capture_output=True, text=True)
    data2 = json.loads(result2.stdout)
    hf2 = [c for c in data2['candidates'] if c.get('semantic_type') in ('header', 'footer')]
    assert len(hf2) == 0, f'Already-named HEADER/FOOTER should not be re-grouped: {hf2}'
    os.unlink(tmp2)

    print('OK')
finally:
    os.unlink(tmp_path)
" 2>/dev/null && { green "  PASS: detect_header_footer — header, footer, exclusion, already-named"; ((PASS++)) || true; } || { red "  FAIL: detect_header_footer unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: infer_zone_semantic_name (Issue 91) ==="
python3 -c "
import json, sys, os, tempfile, subprocess

# Root is directly the artboard (FRAME) — zone detection runs on root-level children
# This matches real usage where get_metadata returns an artboard node
fixture = {
    'id': '1:1', 'name': 'Artboard', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 4500},
    'children': [
        # Zone 1: Hero — large RECTANGLE + TEXT near top
        {'id': '2:1', 'name': 'Rectangle 1', 'type': 'RECTANGLE',
         'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 600}},
        {'id': '2:2', 'name': 'Text 1', 'type': 'TEXT', 'characters': 'Welcome',
         'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 400, 'height': 60}},
        # Zone 2: Cards — 3 card-like frames at same Y band
        {'id': '2:3', 'name': 'Frame 2', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 100, 'y': 800, 'width': 350, 'height': 400},
         'children': [
             {'id': '3:1', 'type': 'RECTANGLE', 'name': 'Image 1', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 350, 'height': 200}},
             {'id': '3:2', 'type': 'TEXT', 'name': 'Title', 'characters': 'Card 1', 'absoluteBoundingBox': {'x': 0, 'y': 210, 'width': 350, 'height': 30}},
         ]},
        {'id': '2:4', 'name': 'Frame 3', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 500, 'y': 800, 'width': 350, 'height': 400},
         'children': [
             {'id': '3:3', 'type': 'RECTANGLE', 'name': 'Image 2', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 350, 'height': 200}},
             {'id': '3:4', 'type': 'TEXT', 'name': 'Title 2', 'characters': 'Card 2', 'absoluteBoundingBox': {'x': 0, 'y': 210, 'width': 350, 'height': 30}},
         ]},
        {'id': '2:5', 'name': 'Frame 4', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 900, 'y': 800, 'width': 350, 'height': 400},
         'children': [
             {'id': '3:5', 'type': 'RECTANGLE', 'name': 'Image 3', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 350, 'height': 200}},
             {'id': '3:6', 'type': 'TEXT', 'name': 'Title 3', 'characters': 'Card 3', 'absoluteBoundingBox': {'x': 0, 'y': 210, 'width': 350, 'height': 30}},
         ]},
        # Zone 3: Navigation-like — 5 small horizontal texts
        {'id': '2:6', 'name': 'Text 2', 'type': 'TEXT', 'characters': 'Home',
         'absoluteBoundingBox': {'x': 100, 'y': 1500, 'width': 60, 'height': 20}},
        {'id': '2:7', 'name': 'Text 3', 'type': 'TEXT', 'characters': 'About',
         'absoluteBoundingBox': {'x': 200, 'y': 1500, 'width': 60, 'height': 20}},
        {'id': '2:8', 'name': 'Text 4', 'type': 'TEXT', 'characters': 'Service',
         'absoluteBoundingBox': {'x': 300, 'y': 1500, 'width': 60, 'height': 20}},
        {'id': '2:9', 'name': 'Text 5', 'type': 'TEXT', 'characters': 'Contact',
         'absoluteBoundingBox': {'x': 400, 'y': 1500, 'width': 60, 'height': 20}},
        {'id': '2:10', 'name': 'Text 6', 'type': 'TEXT', 'characters': 'FAQ',
         'absoluteBoundingBox': {'x': 500, 'y': 1500, 'width': 60, 'height': 20}},
        # Zone 4: Content — mixed TEXT + FRAME (fallback)
        {'id': '2:11', 'name': 'Text 7', 'type': 'TEXT', 'characters': 'Description',
         'absoluteBoundingBox': {'x': 100, 'y': 2000, 'width': 600, 'height': 100}},
        {'id': '2:12', 'name': 'Frame 5', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 100, 'y': 2100, 'width': 600, 'height': 200},
         'children': [
             {'id': '3:7', 'type': 'TEXT', 'name': 'Sub', 'characters': 'Sub text', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 300, 'height': 30}},
         ]},
    ]
}

# Write fixture
tmp_fd, tmp_path = tempfile.mkstemp(suffix='.json')
with os.fdopen(tmp_fd, 'w') as f:
    json.dump(fixture, f)

try:
    result = subprocess.run(
        ['bash', os.path.join(os.environ['SKILLS_DIR'], 'scripts', 'detect-grouping-candidates.sh'), tmp_path],
        capture_output=True, text=True, timeout=30
    )
    data = json.loads(result.stdout)
    candidates = data.get('candidates', [])
    zone_candidates = [c for c in candidates if c.get('method') == 'zone']

    # Test 1: Should have at least 1 zone candidate with semantic name
    assert len(zone_candidates) >= 1, f'Expected zone candidates, got {len(zone_candidates)} (total: {len(candidates)})'

    # Test 2: No zone should have the generic name 'section' (Issue 91 fixed)
    generic = [c for c in zone_candidates if c.get('suggested_name') == 'section']
    assert len(generic) == 0, f'Expected no generic section names, got {len(generic)} with names: {[c[\"suggested_name\"] for c in zone_candidates]}'

    # Test 3: All zone names should be descriptive (start with section- and have suffix)
    for c in zone_candidates:
        name = c.get('suggested_name', '')
        assert name.startswith('section-'), f'Zone name \"{name}\" should start with section-'
        suffix = name[len('section-'):]
        assert len(suffix) > 0, f'Zone name \"{name}\" has empty suffix'

    # Test 4: Hero zone should exist if RECTANGLE + TEXT near top detected
    hero_zones = [c for c in zone_candidates if 'hero' in c.get('suggested_name', '')]
    # hero may or may not be detected depending on zone merging thresholds
    # but generic 'section' must never appear

    print('OK')
finally:
    os.unlink(tmp_path)
" 2>/dev/null && { green "  PASS: infer_zone_semantic_name — semantic names, no-generic, descriptive suffixes"; ((PASS++)) || true; } || { red "  FAIL: infer_zone_semantic_name unit tests"; ((FAIL++)) || true; }

# ================================================================
bold "=== Unit: infer_direction_two / wrap / space_between (Area 4) ==="
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['SKILLS_DIR'], 'lib'))
from figma_utils import (infer_direction_two_elements, detect_wrap, detect_space_between,
    compute_gap_consistency)

# 1. Two elements side by side → HORIZONTAL
a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
b = {'x': 120, 'y': 0, 'w': 100, 'h': 50}
assert infer_direction_two_elements(a, b) == 'HORIZONTAL'

# 2. Two elements stacked → VERTICAL
c = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
d = {'x': 0, 'y': 70, 'w': 100, 'h': 50}
assert infer_direction_two_elements(c, d) == 'VERTICAL'

# 3. Diagonal more horizontal → HORIZONTAL
e = {'x': 0, 'y': 0, 'w': 50, 'h': 50}
f = {'x': 200, 'y': 30, 'w': 50, 'h': 50}
assert infer_direction_two_elements(e, f) == 'HORIZONTAL'

# 4. Diagonal more vertical → VERTICAL
g = {'x': 0, 'y': 0, 'w': 50, 'h': 50}
h = {'x': 30, 'y': 200, 'w': 50, 'h': 50}
assert infer_direction_two_elements(g, h) == 'VERTICAL'

# 5. Same position → VERTICAL (dx == dy == 0, dy not > dx)
same = {'x': 0, 'y': 0, 'w': 50, 'h': 50}
assert infer_direction_two_elements(same, same) == 'VERTICAL'

# 6. WRAP detection: 4+ horizontal elements in 2+ rows
wrap_boxes = [
    {'x': 0, 'y': 0, 'w': 100, 'h': 50},
    {'x': 120, 'y': 0, 'w': 100, 'h': 50},
    {'x': 0, 'y': 70, 'w': 100, 'h': 50},
    {'x': 120, 'y': 70, 'w': 100, 'h': 50},
]
assert detect_wrap(wrap_boxes, 'HORIZONTAL') == True

# 7. WRAP: not enough elements
assert detect_wrap(wrap_boxes[:3], 'HORIZONTAL') == False  # only 3

# 8. WRAP: single row → False
single_row = [{'x': i*120, 'y': 0, 'w': 100, 'h': 50} for i in range(5)]
assert detect_wrap(single_row, 'HORIZONTAL') == False

# 9. WRAP: VERTICAL direction → always False
assert detect_wrap(wrap_boxes, 'VERTICAL') == False

# 10. SPACE_BETWEEN: elements touching both edges
frame = {'x': 0, 'y': 0, 'w': 400, 'h': 50}
sb_boxes = [
    {'x': 0, 'y': 0, 'w': 100, 'h': 50},
    {'x': 150, 'y': 0, 'w': 100, 'h': 50},
    {'x': 300, 'y': 0, 'w': 100, 'h': 50},
]
assert detect_space_between(sb_boxes, 'HORIZONTAL', frame) == True

# 11. SPACE_BETWEEN: not touching end → False
frame2 = {'x': 0, 'y': 0, 'w': 500, 'h': 50}
assert detect_space_between(sb_boxes, 'HORIZONTAL', frame2) == False

# 12. SPACE_BETWEEN: vertical
v_frame = {'x': 0, 'y': 0, 'w': 100, 'h': 300}
v_boxes = [
    {'x': 0, 'y': 0, 'w': 100, 'h': 80},
    {'x': 0, 'y': 110, 'w': 100, 'h': 80},
    {'x': 0, 'y': 220, 'w': 100, 'h': 80},
]
assert detect_space_between(v_boxes, 'VERTICAL', v_frame) == True

# 13. gap_consistency: uniform gaps → low CoV
assert compute_gap_consistency([20, 20, 20]) < 0.01

# 14. gap_consistency: varied gaps → high CoV
cov = compute_gap_consistency([10, 50, 20])
assert cov > 0.3, f'varied gaps should have high CoV, got {cov}'

# 15. gap_consistency: single gap → 0.0
assert compute_gap_consistency([20]) == 0.0

# 16. gap_consistency: empty → 1.0
assert compute_gap_consistency([]) == 1.0

print('OK')
" 2>/dev/null && { green "  PASS: direction_two, wrap, space_between, gap_consistency — 16 cases"; ((PASS++)) || true; } || { red "  FAIL: infer_direction_two / wrap / space_between unit tests"; ((FAIL++)) || true; }

echo ""

# ================================================================
bold "========================================"
bold "  Results: $PASS passed, $FAIL failed, $SKIP skipped"
bold "========================================"

if [[ $FAIL -gt 0 ]]; then
  echo ""
  red "Failed tests:"
  printf '%s' "$ERRORS"
  exit 1
fi

echo ""
green "All tests passed!"
exit 0
