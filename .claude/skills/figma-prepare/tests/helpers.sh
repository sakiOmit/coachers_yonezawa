#!/usr/bin/env bash
# Shared test helpers for run-tests.sh

PASS=0
FAIL=0
SKIP=0
ERRORS=""

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$1"; }
bold()  { printf "\033[1m%s\033[0m\n" "$1"; }

# SAFETY: $field MUST be a hardcoded literal (e.g., "['score']"). Never use external input.
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

# SAFETY: $field MUST be a hardcoded literal (e.g., "['score']"). Never use external input.
assert_json_range() {
  local json="$1" field="$2" min="$3" max="$4" label="$5"
  local actual
  actual=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "__ERROR__")
  if python3 -c "import sys; v=float(sys.argv[1]); assert float(sys.argv[2]) <= v <= float(sys.argv[3])" "$actual" "$min" "$max" 2>/dev/null; then
    green "  PASS: $label (got: $actual, range: $min-$max)"
    ((PASS++)) || true
  else
    red "  FAIL: $label (got: $actual, expected range: $min-$max)"
    ((FAIL++)) || true
    ERRORS+="  - $label: got=$actual, expected range=$min-$max\n"
  fi
}

# SAFETY: $field MUST be a hardcoded literal (e.g., "['score']"). Never use external input.
assert_json_gte() {
  local json="$1" field="$2" min="$3" label="$4"
  local actual
  actual=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "__ERROR__")
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

print_summary() {
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
}
