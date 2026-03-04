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
bold "=== Unit: to_kebab regression (Issue 12-13) ==="

python3 -c "
import re

JP_KEYWORD_MAP = {
    '募集詳細を見る': 'view-detail',
    '募集要項': 'requirements',
    'すべて': 'all', 'お知らせ': 'news', '一覧': 'list',
    '詳しく': 'more', '詳細': 'detail', '見る': 'view',
    '採用': 'recruit', '新卒': 'new-grad', '中途': 'mid-career',
    '募集': 'jobs', '事業': 'business', '仕事': 'work',
    'について': 'about', '環境': 'environment', '社員': 'staff',
    'インタビュー': 'interview', 'お問い合わせ': 'contact',
    '送信': 'submit', '申し込': 'apply', '戻る': 'back',
    'トップ': 'top', 'ホーム': 'home', '検索': 'search',
    'カテゴリー': 'category', 'イベント': 'event',
    '要項': 'requirements',
}

def to_kebab(text):
    text = text.strip()
    if not text:
        return ''
    for jp, en in sorted(JP_KEYWORD_MAP.items(), key=lambda x: -len(x[0])):
        if jp in text:
            ratio = len(jp) / len(text)
            if ratio >= 0.5:
                return en
    text = re.sub(r'[^\x00-\x7f]', ' ', text)
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:40] if text else ''

# Issue 12: ratio check prevents false match on long text
assert to_kebab('大規模イベントに強いオペレーション力') == '', f'Issue 12 fail: got \"{to_kebab(\"大規模イベントに強いオペレーション力\")}\"'
assert to_kebab('イベント一覧') == 'event', f'Issue 12 fail: got \"{to_kebab(\"イベント一覧\")}\"'
assert to_kebab('イベント') == 'event', f'Issue 12 exact match fail'
assert to_kebab('お問い合わせ') == 'contact', f'Issue 12 exact match fail'

# Issue 13: non-ASCII stripped to empty
assert to_kebab('無料相談') == '', f'Issue 13 fail: got \"{to_kebab(\"無料相談\")}\"'
assert to_kebab('資料請求') == '', f'Issue 13 fail: got \"{to_kebab(\"資料請求\")}\"'
assert to_kebab('募集要項') == 'requirements', f'Issue 13 registered keyword fail'

# ASCII still works
assert to_kebab('job description') == 'job-description', f'ASCII fail: got \"{to_kebab(\"job description\")}\"'
assert to_kebab('REASON') == 'reason', f'ASCII fail: got \"{to_kebab(\"REASON\")}\"'

print('All to_kebab tests passed')
" 2>/dev/null && { green "  PASS: to_kebab unit tests (Issue 12-13)"; ((PASS++)) || true; } || { red "  FAIL: to_kebab unit tests"; ((FAIL++)) || true; }

echo ""

# ================================================================
bold "=== Cross-script: consistency ==="

P1_UNNAMED=$(echo "$RESULT1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['unnamed_nodes'])" 2>/dev/null || echo "0")
P3_RENAME_TOTAL=$(echo "$RESULT2" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")

# Phase 1の未命名数とPhase 3のリネーム数が一致（許容差±5）
if python3 -c "assert abs($P1_UNNAMED - $P3_RENAME_TOTAL) <= 5" 2>/dev/null; then
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
    if python3 -c "assert int('$REAL_UNNAMED') >= 5" 2>/dev/null; then
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
      # Cross-script consistency: Phase 1 unnamed ≈ Phase 2 renames (±5)
      if python3 -c "assert abs($REAL_UNNAMED - $REAL_RENAME_COUNT) <= 5" 2>/dev/null; then
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
      if python3 -c "assert int('$REAL_CANDIDATES') >= 1" 2>/dev/null; then
        green "  PASS: Grouping — $REAL_CANDIDATES candidates detected (>= 1)"
        ((PASS++)) || true
      else
        red "  FAIL: Grouping — no candidates detected"
        ((FAIL++)) || true
      fi

      # Dedup check: candidates < 50% of total nodes
      REAL_TOTAL=$(echo "$REAL_P1" | python3 -c "import json,sys; print(json.load(sys.stdin)['metrics']['total_nodes'])" 2>/dev/null || echo "100")
      if python3 -c "assert int('$REAL_CANDIDATES') < int('$REAL_TOTAL') * 0.5" 2>/dev/null; then
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
# Verify that any grouping with 1:5 is only proximity (not semantic/page-kv)
for c in d.get('candidates', []):
    ids = set(c.get('node_ids', []))
    if '1:5' in ids:
        assert c.get('method') == 'proximity', f'1:5 in non-proximity group: {c[\"method\"]}'
print('  PASS: Stage A — 1:5 grouping is proximity only (semantic deferred to Stage B)')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Stage A — 1:5 in unexpected group type"; ((FAIL++)) || true; }

      # Stage A methods: only proximity and pattern (no page-kv or semantic)
      echo "$REAL_P3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
methods = set(c.get('method', '') for c in d.get('candidates', []))
forbidden = methods & {'page-kv', 'semantic'}
assert not forbidden, f'Unexpected methods in Stage A: {forbidden}'
print(f'  PASS: Stage A — methods = {methods} (proximity/pattern only)')
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

    # --- Phase 3 Stage B: prepare-sectioning-context ---
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
      if [[ -f "$SEC_OUT" ]] && python3 -c "import json; json.load(open('$SEC_OUT'))" 2>/dev/null; then
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
    if python3 -c "assert int('$ENRICHED_COUNT') >= 5" 2>/dev/null; then
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
exact = [f for f in frames if f.get('source') == 'enriched']
assert len(exact) >= 2, f'Expected >= 2 exact (enriched) frames, got {len(exact)}'
# Verify enriched frame has correct direction
for f in exact:
    if f['node_id'] == '1:106':
        assert f['layout']['direction'] == 'HORIZONTAL', f'1:106 should be HORIZONTAL'
        assert f['layout']['gap'] == 24, f'1:106 gap should be 24'
        assert f['layout']['confidence'] == 'exact', f'1:106 confidence should be exact'
print(f'  PASS: Issue 18 — {len(exact)} frames with exact layoutMode')
" 2>/dev/null && { ((PASS++)) || true; } || { red "  FAIL: Issue 18 — enriched layoutMode not used"; ((FAIL++)) || true; }
    fi

    rm -f "$ENRICHED_TMP"
  fi
else
  skip_test "Enrichment fixtures not found"
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
