#!/usr/bin/env bash
# /figma-prepare integration test runner
#
# Usage:
#   bash .claude/skills/figma-prepare/tests/run-tests.sh                    # fixture mode
#   bash .claude/skills/figma-prepare/tests/run-tests.sh <metadata.json>    # real data mode
#
# Python unit tests are in test_figma_utils.py (run via pytest separately).
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

# shellcheck source=helpers.sh
source "$SCRIPT_DIR/helpers.sh"

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

# Error check
if echo "$RESULT1" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null; then
  green "  PASS: No error in output"
  ((PASS++)) || true
else
  red "  FAIL: Script returned error"
  echo "$RESULT1"
  ((FAIL++)) || true
fi

assert_json_range "$RESULT1" "['score']" 0 100 "Score in 0-100 range"

GRADE=$(echo "$RESULT1" | python3 -c "import json,sys; print(json.load(sys.stdin)['grade'])" 2>/dev/null || echo "?")
if [[ "$GRADE" =~ ^[A-F]$ ]]; then
  green "  PASS: Grade is valid letter ($GRADE)"
  ((PASS++)) || true
else
  red "  FAIL: Grade invalid ($GRADE)"
  ((FAIL++)) || true
fi

assert_json_gte "$RESULT1" "['metrics']['total_nodes']" 1 "Total nodes >= 1"
assert_json_gte "$RESULT1" "['metrics']['unnamed_nodes']" 0 "Unnamed nodes >= 0"

echo "$RESULT1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
sb = d.get('score_breakdown', {})
assert len(sb) == 5, f'Expected 5 breakdown fields, got {len(sb)}'
r = d.get('recommendation','')
assert len(r) > 0, 'Empty recommendation'
" && { green "  PASS: score_breakdown (5 fields) + recommendation"; ((PASS++)) || true; } \
  || { red "  FAIL: score_breakdown or recommendation"; ((FAIL++)) || true; }

echo ""
echo "  [Detail] $(echo "$RESULT1" | python3 -c "
import json,sys
d=json.load(sys.stdin); m=d['metrics']
print(f\"nodes={m['total_nodes']}, unnamed={m['unnamed_nodes']}({m['unnamed_rate_pct']}%), flat={m['flat_sections']}, deep={m['deep_nesting_count']}, no_al={m['no_autolayout_frames']}/{m['total_frames']}\")
" 2>/dev/null)"
echo ""

# ================================================================
bold "=== Phase 3: generate-rename-map.sh ==="

RESULT2=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$FIXTURE" 2>&1) || {
  red "  FATAL: generate-rename-map.sh crashed"; echo "$RESULT2"; exit 1
}

echo "$RESULT2" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null \
  && { green "  PASS: No error in output"; ((PASS++)) || true; } \
  || { red "  FAIL: Script returned error"; echo "$RESULT2"; ((FAIL++)) || true; }

assert_json_gte "$RESULT2" "['total']" 0 "Rename total >= 0"
assert_json_field "$RESULT2" "['status']" "dry-run" "Status is dry-run"

RENAME_COUNT=$(echo "$RESULT2" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('renames',{})))" 2>/dev/null || echo 0)
green "  INFO: $RENAME_COUNT rename candidates"

if [[ "$IS_FIXTURE" == true ]]; then
  echo "$RESULT2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert '3:1' not in d.get('renames',{}), 'properly-named-footer should not be renamed'
" && { green "  PASS: Properly named nodes excluded"; ((PASS++)) || true; } \
   || { red "  FAIL: Properly named node incorrectly targeted"; ((FAIL++)) || true; }
else
  skip_test "Fixture-specific: properly-named exclusion"
fi

# YAML output
YAML_OUT="/tmp/figma-prepare-test-rename-$$.yaml"
bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$FIXTURE" --output "$YAML_OUT" >/dev/null 2>&1
if [[ -f "$YAML_OUT" ]] && grep -q "renames:" "$YAML_OUT"; then
  green "  PASS: YAML output file generated"; ((PASS++)) || true
else
  red "  FAIL: YAML output not generated"; ((FAIL++)) || true
fi
rm -f "$YAML_OUT"

# Issue 174: Semantic group/container naming test
bold "  --- Issue 174: Semantic group/container naming ---"
SEMANTIC_FIXTURE="/tmp/figma-prepare-test-semantic-$$.json"
python3 -c "
import json
fixture = {
    'id': '0:1', 'name': 'Test Page', 'type': 'FRAME',
    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 3000},
    'children': [
        {'id': '1:1', 'name': 'Frame 1', 'type': 'FRAME',
         'absoluteBoundingBox': {'x': 100, 'y': 100, 'width': 600, 'height': 800},
         'children': [
             {'id': '1:10', 'name': 'Frame 10', 'type': 'FRAME',
              'absoluteBoundingBox': {'x': 100, 'y': 100, 'width': 500, 'height': 180},
              'children': [
                  {'id': '1:11', 'name': 'Text 1', 'type': 'TEXT',
                   'absoluteBoundingBox': {'x': 110, 'y': 110, 'width': 200, 'height': 30},
                   'characters': 'サービスについて', 'children': []},
              ]},
             {'id': '1:20', 'name': 'Frame 11', 'type': 'FRAME',
              'absoluteBoundingBox': {'x': 100, 'y': 300, 'width': 500, 'height': 180},
              'children': [
                  {'id': '1:21', 'name': 'Text 2', 'type': 'TEXT',
                   'absoluteBoundingBox': {'x': 110, 'y': 310, 'width': 200, 'height': 30},
                   'characters': '詳しくはこちら', 'children': []},
              ]},
             {'id': '1:30', 'name': 'Frame 12', 'type': 'FRAME',
              'absoluteBoundingBox': {'x': 100, 'y': 500, 'width': 500, 'height': 180},
              'children': [
                  {'id': '1:31', 'name': 'Text 3', 'type': 'TEXT',
                   'absoluteBoundingBox': {'x': 110, 'y': 510, 'width': 200, 'height': 30},
                   'characters': 'お問い合わせ', 'children': []},
              ]},
             {'id': '1:40', 'name': 'Frame 13', 'type': 'FRAME',
              'absoluteBoundingBox': {'x': 100, 'y': 700, 'width': 500, 'height': 180},
              'children': [
                  {'id': '1:41', 'name': 'Text 4', 'type': 'TEXT',
                   'absoluteBoundingBox': {'x': 110, 'y': 710, 'width': 200, 'height': 30},
                   'characters': '料金プラン', 'children': []},
              ]},
         ]},
    ],
}
with open('$SEMANTIC_FIXTURE', 'w') as f:
    json.dump(fixture, f)
"

SEMANTIC_RESULT=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$SEMANTIC_FIXTURE" 2>&1) || {
  red "  FATAL: generate-rename-map.sh crashed on semantic fixture"
  ((FAIL++)) || true
}

if [[ -n "${SEMANTIC_RESULT:-}" ]]; then
  echo "$SEMANTIC_RESULT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
renames = d.get('renames',{})
r = renames.get('1:1', {})
name = r.get('new_name', '')
assert name.startswith('group-'), f'Expected group-*, got: {name}'
assert 'service' in name, f'Expected service slug, got: {name}'
assert not name.split('-')[-1].isdigit(), f'Expected semantic slug, not numeric: {name}'
print(f'Semantic name: {name}')
" && { green "  PASS: Issue 174 — group uses semantic slug from child text"; ((PASS++)) || true; } \
   || { red "  FAIL: Issue 174 — semantic group naming"; ((FAIL++)) || true; }
fi
rm -f "$SEMANTIC_FIXTURE"

echo ""

# ================================================================
bold "=== Phase 2: detect-grouping-candidates.sh ==="

RESULT3=$(bash "$SKILLS_DIR/scripts/detect-grouping-candidates.sh" "$FIXTURE" 2>&1) || {
  red "  FATAL: detect-grouping-candidates.sh crashed"; echo "$RESULT3"; exit 1
}

echo "$RESULT3" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null \
  && { green "  PASS: No error in output"; ((PASS++)) || true; } \
  || { red "  FAIL: Script returned error"; echo "$RESULT3"; ((FAIL++)) || true; }

assert_json_gte "$RESULT3" "['total']" 0 "Grouping total >= 0"
assert_json_field "$RESULT3" "['status']" "dry-run" "Status is dry-run"

echo "$RESULT3" | python3 -c "
from collections import Counter
import json,sys
d=json.load(sys.stdin)
candidates = d.get('candidates',[])
methods = Counter(c.get('method','') for c in candidates)
print(f'  INFO: {len(candidates)} candidates: {dict(methods)}')
" 2>/dev/null
echo ""

# ================================================================
bold "=== Phase 4: infer-autolayout.sh ==="

RESULT4=$(bash "$SKILLS_DIR/scripts/infer-autolayout.sh" "$FIXTURE" 2>&1) || {
  red "  FATAL: infer-autolayout.sh crashed"; echo "$RESULT4"; exit 1
}

echo "$RESULT4" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'error' not in d" 2>/dev/null \
  && { green "  PASS: No error in output"; ((PASS++)) || true; } \
  || { red "  FAIL: Script returned error"; echo "$RESULT4"; ((FAIL++)) || true; }

assert_json_gte "$RESULT4" "['total']" 0 "AutoLayout total >= 0"
assert_json_field "$RESULT4" "['status']" "dry-run" "Status is dry-run"

# Layout structure + 4px snap
echo "$RESULT4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for f in d.get('frames',[]):
    l = f.get('layout',{})
    assert l['direction'] in ('HORIZONTAL','VERTICAL','WRAP'), f'Bad direction'
    assert isinstance(l['gap'], (int, float)), 'Gap not numeric'
    assert all(k in l['padding'] for k in ('top','right','bottom','left')), 'Missing padding'
    if f.get('source') != 'exact':
        assert l['gap'] % 4 == 0, f'gap={l[\"gap\"]} not snapped'
        for k,v in l['padding'].items():
            assert v % 4 == 0, f'{k}={v} not snapped'
" && { green "  PASS: Layout structure valid + 4px snap"; ((PASS++)) || true; } \
  || { red "  FAIL: Layout structure or snap"; ((FAIL++)) || true; }

echo ""

# ================================================================
bold "=== Cross-script: consistency ==="

P1_UNNAMED=$(echo "$RESULT1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['unnamed_nodes'])" 2>/dev/null || echo "0")
P3_RENAME_TOTAL=$(echo "$RESULT2" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")

if python3 -c "import sys; assert abs(int(sys.argv[1]) - int(sys.argv[2])) <= 5" "$P1_UNNAMED" "$P3_RENAME_TOTAL" 2>/dev/null; then
  green "  PASS: Phase1 unnamed ($P1_UNNAMED) ≈ Phase3 renames ($P3_RENAME_TOTAL)"
  ((PASS++)) || true
else
  red "  FAIL: Phase1 unnamed ($P1_UNNAMED) vs Phase3 renames ($P3_RENAME_TOTAL) — gap > 5"
  ((FAIL++)) || true
fi

echo ""

# ================================================================
# Dirty Fixture
# ================================================================
bold "=== Dirty Fixture: fixture-dirty.json ==="

DIRTY_FIXTURE="$SCRIPT_DIR/fixture-dirty.json"
if [[ -f "$DIRTY_FIXTURE" ]]; then
  DIRTY_RESULT=$(bash "$SKILLS_DIR/scripts/analyze-structure.sh" "$DIRTY_FIXTURE" 2>&1) || {
    red "  FATAL: analyze-structure.sh crashed on dirty fixture"
    ((FAIL++)) || true
  }

  if [[ -n "${DIRTY_RESULT:-}" ]] && echo "$DIRTY_RESULT" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    DIRTY_SCORE=$(echo "$DIRTY_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['score'])" 2>/dev/null || echo "999")

    if python3 -c "import sys; assert float(sys.argv[1]) < 80" "$DIRTY_SCORE" 2>/dev/null; then
      green "  PASS: Dirty fixture score < 80 (got: $DIRTY_SCORE)"
      ((PASS++)) || true
    else
      red "  FAIL: Dirty fixture score too high ($DIRTY_SCORE)"
      ((FAIL++)) || true
    fi

    DIRTY_UNNAMED=$(echo "$DIRTY_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['unnamed_rate_pct'])" 2>/dev/null || echo "0")
    if python3 -c "import sys; assert float(sys.argv[1]) > 30" "$DIRTY_UNNAMED" 2>/dev/null; then
      green "  PASS: Dirty fixture unnamed rate > 30% (got: ${DIRTY_UNNAMED}%)"
      ((PASS++)) || true
    else
      red "  FAIL: Dirty fixture unnamed rate too low (${DIRTY_UNNAMED}%)"
      ((FAIL++)) || true
    fi

    # Renames should be > 10
    DIRTY_RENAME=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$DIRTY_FIXTURE" 2>&1) || true
    if [[ -n "${DIRTY_RENAME:-}" ]]; then
      DIRTY_RENAME_COUNT=$(echo "$DIRTY_RENAME" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
      if python3 -c "import sys; assert int(sys.argv[1]) > 10" "$DIRTY_RENAME_COUNT" 2>/dev/null; then
        green "  PASS: Dirty rename candidates > 10 (got: $DIRTY_RENAME_COUNT)"
        ((PASS++)) || true
      else
        red "  FAIL: Dirty rename candidates too few ($DIRTY_RENAME_COUNT)"
        ((FAIL++)) || true
      fi
    fi
  fi
else
  skip_test "Dirty fixture not found"
fi

echo ""

# ================================================================
# Realistic Fixture
# ================================================================
bold "=== Realistic Fixture: fixture-realistic.json ==="

REALISTIC_FIXTURE="$SCRIPT_DIR/fixture-realistic.json"
if [[ -f "$REALISTIC_FIXTURE" ]]; then
  # --- Phase 1 ---
  REAL_P1=$(bash "$SKILLS_DIR/scripts/analyze-structure.sh" "$REALISTIC_FIXTURE" 2>&1) || {
    red "  FATAL: analyze-structure.sh crashed on realistic fixture"
    ((FAIL++)) || true
  }

  if [[ -n "${REAL_P1:-}" ]] && echo "$REAL_P1" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    # is_section_root detection
    echo "$REAL_P1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
total = d['metrics']['total_nodes']
deep = d['metrics']['deep_nesting_count']
assert deep < total // 2, f'deep_nesting={deep} >= total/2={total//2}'
" && { green "  PASS: is_section_root — deep_nesting < total/2"; ((PASS++)) || true; } \
     || { red "  FAIL: is_section_root detection"; ((FAIL++)) || true; }

    # Unnamed >= 5
    REAL_UNNAMED=$(echo "$REAL_P1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['unnamed_nodes'])" 2>/dev/null || echo "0")
    if python3 -c "import sys; assert int(sys.argv[1]) >= 5" "$REAL_UNNAMED" 2>/dev/null; then
      green "  PASS: Unnamed detection — $REAL_UNNAMED (>= 5)"
      ((PASS++)) || true
    else
      red "  FAIL: Unnamed detection — only $REAL_UNNAMED (expected >= 5)"
      ((FAIL++)) || true
    fi

    # Lowercase 'image' in sample_unnamed
    echo "$REAL_P1" | python3 -c "
import json,sys
d=json.load(sys.stdin)
samples = d.get('sample_unnamed', [])
assert any('image' in s.lower() for s in samples), f'No image: {samples}'
" && { green "  PASS: Lowercase image in sample_unnamed"; ((PASS++)) || true; } \
     || { red "  FAIL: Lowercase image not in sample_unnamed"; ((FAIL++)) || true; }

    assert_json_range "$REAL_P1" "['score']" 85 95 "Realistic score in 85-95"

    # --- Phase 3: rename ---
    REAL_P2=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$REALISTIC_FIXTURE" 2>&1) || {
      red "  FATAL: generate-rename-map.sh crashed"; ((FAIL++)) || true
    }

    if [[ -n "${REAL_P2:-}" ]]; then
      REAL_RENAME_COUNT=$(echo "$REAL_P2" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")

      # Cross-script consistency
      if python3 -c "import sys; assert abs(int(sys.argv[1]) - int(sys.argv[2])) <= 5" "$REAL_UNNAMED" "$REAL_RENAME_COUNT" 2>/dev/null; then
        green "  PASS: Cross-script — unnamed ($REAL_UNNAMED) ≈ renames ($REAL_RENAME_COUNT)"
        ((PASS++)) || true
      else
        red "  FAIL: Cross-script — unnamed ($REAL_UNNAMED) vs renames ($REAL_RENAME_COUNT) gap > 5"
        ((FAIL++)) || true
      fi

      # Rename quality: specific node checks
      echo "$REAL_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
renames = d.get('renames',{})
checks = [
    ('1:114', 'nav-',     'Nav detection'),
    ('1:108', 'icon-',    'Icon detection'),
    ('1:102', 'heading-', 'Heading detection'),
    ('1:109', 'icon-',    'Tiny frame icon'),
    ('1:200', 'body-',    'Issue 14: heading+body (Issue 170: TEXT-only → body-*)'),
    ('1:106', 'header',   'Issue 16: header'),
    ('1:300', 'footer',   'Issue 16: footer'),
]
ok = 0
for nid, prefix, label in checks:
    r = renames.get(nid, {})
    name = r.get('new_name', '')
    if prefix.endswith('-'):
        assert name.startswith(prefix), f'{label}: {nid} expected {prefix}*, got: {name}'
    else:
        assert name == prefix, f'{label}: {nid} expected {prefix}, got: {name}'
    ok += 1
# Fallback rate < 50%
total = len(renames)
fallback = sum(1 for r in renames.values() if any(r['new_name'].startswith(p) for p in ['group-', 'frame-', 'container-']))
rate = 100*fallback/max(total,1)
assert rate < 50, f'Fallback rate {rate:.1f}% >= 50%'
print(f'{ok} rename checks passed, fallback={rate:.1f}%')
" && { green "  PASS: Rename quality — all node checks + fallback < 50%"; ((PASS++)) || true; } \
     || { red "  FAIL: Rename quality check"; ((FAIL++)) || true; }
    fi

    # --- Phase 2: grouping ---
    REAL_P3=$(bash "$SKILLS_DIR/scripts/detect-grouping-candidates.sh" "$REALISTIC_FIXTURE" 2>&1) || {
      red "  FATAL: detect-grouping-candidates.sh crashed"; ((FAIL++)) || true
    }

    if [[ -n "${REAL_P3:-}" ]]; then
      echo "$REAL_P3" | python3 -c "
import json,sys
d=json.load(sys.stdin)
candidates = d.get('candidates',[])
total_nodes = int(sys.argv[1])

# At least 1 candidate
assert len(candidates) >= 1, 'No candidates'

# Dedup: < 50% of nodes
assert len(candidates) < total_nodes * 0.5, f'{len(candidates)} >= {total_nodes}*0.5'

# Issue 22: Tab + Card list grouped (proximity or heading-content)
found_22 = any(
    c.get('method') in ('proximity', 'heading-content')
    and {'1:6', '1:15'} <= set(c.get('node_ids', []))
    for c in candidates
)
assert found_22, 'Issue 22: Tab + Card list not grouped'

# Methods: only proximity, pattern, spacing, semantic, zone
methods = set(c.get('method', '') for c in candidates)
assert not (methods & {'page-kv'}), f'Unexpected methods: {methods}'

print(f'{len(candidates)} candidates, methods={methods}')
" "$(echo "$REAL_P1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['total_nodes'])" 2>/dev/null)" \
     && { green "  PASS: Grouping quality — candidates, dedup, Issue 22, methods"; ((PASS++)) || true; } \
     || { red "  FAIL: Grouping quality"; ((FAIL++)) || true; }
    fi

    # --- Phase 4: autolayout ---
    REAL_P4=$(bash "$SKILLS_DIR/scripts/infer-autolayout.sh" "$REALISTIC_FIXTURE" 2>&1) || {
      red "  FATAL: infer-autolayout.sh crashed"; ((FAIL++)) || true
    }

    if [[ -n "${REAL_P4:-}" ]]; then
      echo "$REAL_P4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for f in d.get('frames',[]):
    p = f['layout']['padding']
    for k,v in p.items():
        assert v >= 0, f'{f[\"node_name\"]}.{k}={v} negative'
" && { green "  PASS: No negative padding (resolve_absolute_coords OK)"; ((PASS++)) || true; } \
     || { red "  FAIL: Negative padding detected"; ((FAIL++)) || true; }
    fi

    # --- Stage B: prepare-sectioning-context ---
    bold "  --- Stage B: prepare-sectioning-context.sh ---"

    REAL_SEC=$(bash "$SKILLS_DIR/scripts/prepare-sectioning-context.sh" "$REALISTIC_FIXTURE" 2>&1) || {
      red "  FATAL: prepare-sectioning-context.sh crashed"; ((FAIL++)) || true
    }

    if [[ -n "${REAL_SEC:-}" ]]; then
      echo "$REAL_SEC" | python3 -c "
import json,sys
d=json.load(sys.stdin)

# No error
assert 'error' not in d

# total_children = 9, page_name, page_size
assert d['total_children'] == 9, f'total_children={d[\"total_children\"]}'
assert d['page_name'] == '募集一覧'
assert d['page_size']['width'] == 1440.0
assert d['page_size']['height'] == 3858.0

# Y-sorted
children = d['top_level_children']
y_values = [c['bbox']['y'] for c in children]
assert y_values == sorted(y_values), f'Not Y-sorted: {y_values}'

# Required fields
for c in children:
    for field in ['id', 'name', 'type', 'bbox', 'child_count', 'is_unnamed']:
        assert field in c, f'Missing {field} in {c.get(\"id\",\"?\")}'

# Heuristic hints
hints = d['heuristic_hints']
assert '1:106' in hints['header_candidates']
assert '1:300' in hints['footer_candidates']
assert len(hints['gap_analysis']) == 8
assert '1:101' in hints['background_candidates']
assert 'page_kv_candidates' not in hints

# is_unnamed
children_map = {c['id']: c for c in children}
assert children_map['1:106']['is_unnamed'] == True
assert children_map['1:5']['is_unnamed'] == False

# 1:5-1:6 gap > 50px
target = [g for g in hints['gap_analysis'] if set(g['between']) == {'1:5', '1:6'}]
assert len(target) == 1 and target[0]['gap_px'] > 50

print('All Stage B checks passed')
" && { green "  PASS: Stage B — all checks (14 assertions)"; ((PASS++)) || true; } \
     || { red "  FAIL: Stage B checks"; ((FAIL++)) || true; }

      # --output test
      SEC_OUT="/tmp/figma-prepare-test-sectioning-$$.json"
      bash "$SKILLS_DIR/scripts/prepare-sectioning-context.sh" "$REALISTIC_FIXTURE" --output "$SEC_OUT" >/dev/null 2>&1
      if [[ -f "$SEC_OUT" ]] && python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$SEC_OUT" 2>/dev/null; then
        green "  PASS: Stage B — --output valid JSON"
        ((PASS++)) || true
      else
        red "  FAIL: Stage B — --output invalid"
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
# Enrichment Pipeline
# ================================================================
bold "=== Enrichment Pipeline: Issues 15, 17, 18 ==="

ENRICHMENT_FIXTURE="$SCRIPT_DIR/fixture-enrichment.json"
if [[ -f "$REALISTIC_FIXTURE" ]] && [[ -f "$ENRICHMENT_FIXTURE" ]]; then
  ENRICHED_TMP="/tmp/figma-prepare-enriched-$$.json"
  ENRICH_RESULT=$(bash "$SKILLS_DIR/scripts/enrich-metadata.sh" "$REALISTIC_FIXTURE" "$ENRICHMENT_FIXTURE" --output "$ENRICHED_TMP" 2>&1) || {
    red "  FATAL: enrich-metadata.sh crashed"
    ((FAIL++)) || true
  }

  if [[ -f "$ENRICHED_TMP" ]]; then
    # Enrichment count >= 5
    ENRICHED_COUNT=$(echo "$ENRICH_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['enriched_nodes'])" 2>/dev/null || echo "0")
    if python3 -c "import sys; assert int(sys.argv[1]) >= 5" "$ENRICHED_COUNT" 2>/dev/null; then
      green "  PASS: enrich-metadata — $ENRICHED_COUNT nodes (>= 5)"
      ((PASS++)) || true
    else
      red "  FAIL: only $ENRICHED_COUNT enriched (expected >= 5)"
      ((FAIL++)) || true
    fi

    # Issue 17: fills-based IMAGE/bg detection
    ENRICHED_P2=$(bash "$SKILLS_DIR/scripts/generate-rename-map.sh" "$ENRICHED_TMP" 2>&1) || {
      red "  FATAL: generate-rename-map.sh crashed on enriched data"; ((FAIL++)) || true
    }

    if [[ -n "${ENRICHED_P2:-}" ]]; then
      echo "$ENRICHED_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
renames = d.get('renames',{})
checks = [
    ('1:101', 'img-',  'IMAGE fill → img-*'),
    ('1:113', 'img-',  'logo IMAGE fill → img-*'),
    ('1:107', 'bg-',   'SOLID fill → bg-*'),
]
for nid, prefix, label in checks:
    r = renames.get(nid, {})
    name = r.get('new_name', '')
    assert name.startswith(prefix), f'{label}: {nid} got {name}'
print('fills-based detection OK')
" && { green "  PASS: Issue 17 — IMAGE/SOLID fill detection"; ((PASS++)) || true; } \
     || { red "  FAIL: Issue 17 — fill detection"; ((FAIL++)) || true; }

      # Issue 32: fills=[] no crash — verify node 1:20 (fills: [] in enrichment) processed without error
      echo "$ENRICHED_P2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
# Enriched data includes node 1:20 with fills=[]; verify no error entries for it
assert 'error' not in d, 'Top-level error in rename output'
renames = d.get('renames',{})
r = renames.get('1:20', {})
assert r.get('error') is None, f'Error for node 1:20: {r}'
" && { green "  PASS: Issue 32 — fills=[] node 1:20 processed without error"; ((PASS++)) || true; } \
       || { red "  FAIL: Issue 32 — fills=[] caused error for node 1:20"; ((FAIL++)) || true; }
    fi

    # Issue 18: layoutMode complement
    ENRICHED_P4=$(bash "$SKILLS_DIR/scripts/infer-autolayout.sh" "$ENRICHED_TMP" 2>&1) || {
      red "  FATAL: infer-autolayout.sh crashed"; ((FAIL++)) || true
    }

    if [[ -n "${ENRICHED_P4:-}" ]]; then
      echo "$ENRICHED_P4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
exact = [f for f in d.get('frames',[]) if f.get('source') == 'exact']
assert len(exact) >= 2, f'Expected >= 2 exact frames, got {len(exact)}'
for f in exact:
    if f['node_id'] == '1:106':
        assert f['layout']['direction'] == 'HORIZONTAL'
        assert f['layout']['gap'] == 24
        assert f['layout']['confidence'] == 'exact'
" && { green "  PASS: Issue 18 — enriched layoutMode used"; ((PASS++)) || true; } \
     || { red "  FAIL: Issue 18"; ((FAIL++)) || true; }
    fi

    rm -f "$ENRICHED_TMP"
  fi
else
  skip_test "Enrichment fixtures not found"
fi

echo ""

# ================================================================
print_summary
