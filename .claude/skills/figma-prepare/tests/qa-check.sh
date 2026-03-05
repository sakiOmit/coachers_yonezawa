#!/usr/bin/env bash
# /figma-prepare 自動QAチェッカー
#
# 機械的に検出可能なコード品質問題をスキャンする。
# フィードバックループの一環として run-tests.sh と併用。
#
# Usage:
#   bash qa-check.sh           # チェックのみ（exit code: 0=clean, 1=issues found）
#   bash qa-check.sh --json    # JSON出力
#
# チェックカテゴリ:
#   1. unused-import   : Python未使用import検出
#   2. stale-phase-ref : Phase番号の不整合検出
#   3. yaml-key-mismatch: YAML出力キーと実データキーの不一致
#   4. doc-staleness   : ドキュメントの陳腐化検出
#   5. dead-code       : 到達不能コード・未使用変数
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$SKILLS_DIR/scripts"
REFS_DIR="$SKILLS_DIR/references"
LIB_DIR="$SKILLS_DIR/lib"

JSON_MODE=false
[[ "${1:-}" == "--json" ]] && JSON_MODE=true

ISSUES=()
WARNINGS=()

issue() { ISSUES+=("$1"); }
warn()  { WARNINGS+=("$1"); }

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$1"; }
bold()  { printf "\033[1m%s\033[0m\n" "$1"; }

# ================================================================
# 1. unused-import: Python未使用import検出
# ================================================================
check_unused_imports() {
  bold "=== Check: unused-import ==="

  # Issue 65: Removed dead first loop (subshell issue made issue() calls invisible)
  local found=0
  for script in "$SCRIPTS_DIR"/*.sh; do
    local basename
    basename=$(basename "$script")
    local result
    result=$(python3 -c "
import re, sys

with open(sys.argv[1], 'r') as f:
    content = f.read()

lines = content.split('\n')
imports = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith('import '):
        mods = stripped.replace('import ', '').split(',')
        for m in mods:
            m = m.strip().split(' as ')[0].strip()
            if m:
                imports.append(m)

stdlib_modules = {'json', 're', 'sys', 'os', 'math', 'statistics', 'unicodedata', 'tempfile', 'subprocess'}
unused = []
for mod in imports:
    if mod not in stdlib_modules:
        continue
    pattern = mod + r'\.'
    code_without_imports = re.sub(r'^(import |from ).*$', '', content, flags=re.MULTILINE)
    if not re.search(pattern, code_without_imports):
        if mod == 'sys' and 'sys.' in code_without_imports:
            continue
        if mod == 'os' and 'os.' in code_without_imports:
            continue
        unused.append(mod)

if unused:
    print(','.join(unused))
" "$script" 2>/dev/null || echo "")

    if [[ -n "$result" ]]; then
      issue "unused-import: $basename has unused import(s): $result"
      found=1
    fi
  done

  if [[ $found -eq 0 ]]; then
    green "  PASS: No unused imports"
  fi
}

# ================================================================
# 2. stale-phase-ref: Phase番号の不整合
# ================================================================
check_stale_phase_refs() {
  bold "=== Check: stale-phase-ref ==="

  local found=0

  # Phase 3 + Stage B/sectioning は Phase 2 であるべき
  while IFS= read -r line; do
    if [[ -n "$line" ]]; then
      # RESOLVED-ISSUES.md と KNOWN-ISSUES.md の既存Issue説明は除外
      if [[ "$line" != *"RESOLVED-ISSUES"* ]] && [[ "$line" != *"KNOWN-ISSUES"* ]]; then
        issue "stale-phase-ref: $line"
        found=1
      fi
    fi
  done < <(grep -rn "Phase 3.*Stage B\|Phase 3.*sectioning\|Phase 3.*セクション分割" \
    "$SCRIPTS_DIR" "$REFS_DIR" "$SKILLS_DIR/SKILL.md" 2>/dev/null || true)

  # Phase 2 + rename は Phase 3 であるべき
  while IFS= read -r line; do
    if [[ -n "$line" ]]; then
      if [[ "$line" != *"RESOLVED-ISSUES"* ]] && [[ "$line" != *"KNOWN-ISSUES"* ]]; then
        issue "stale-phase-ref: $line"
        found=1
      fi
    fi
  done < <(grep -rn "Phase 2.*rename\|Phase 2.*リネーム" \
    "$SCRIPTS_DIR" "$REFS_DIR" 2>/dev/null | grep -v "Phase 2.*Phase 3\|Phase 2=グルーピング\|Phase 2 のグルーピング\|Phase 2 + 3\|Phase 2（グループ化）" || true)

  if [[ $found -eq 0 ]]; then
    green "  PASS: No stale Phase references"
  fi
}

# ================================================================
# 3. yaml-key-mismatch: YAML出力キーの検証
# ================================================================
check_yaml_key_mismatch() {
  bold "=== Check: yaml-key-mismatch ==="

  local found=0

  # detect-grouping-candidates.sh: YAML出力でpatternキーを使っていないか
  if grep -q "'pattern' in c" "$SCRIPTS_DIR/detect-grouping-candidates.sh" 2>/dev/null; then
    issue "yaml-key-mismatch: detect-grouping-candidates.sh uses 'pattern' key but data uses 'structure_hash'"
    found=1
  fi

  # 各スクリプトのYAML出力がyaml_str()を使っているか
  for script in "$SCRIPTS_DIR"/{detect-grouping-candidates,generate-rename-map,infer-autolayout}.sh; do
    if [[ -f "$script" ]]; then
      local basename
      basename=$(basename "$script")
      if grep -q "f.write.*f'" "$script" && ! grep -q "yaml_str" "$script"; then
        issue "yaml-key-mismatch: $basename has YAML output without yaml_str() escaping"
        found=1
      fi
    fi
  done

  if [[ $found -eq 0 ]]; then
    green "  PASS: YAML output keys consistent"
  fi
}

# ================================================================
# 4. doc-staleness: ドキュメントの陳腐化
# ================================================================
check_doc_staleness() {
  bold "=== Check: doc-staleness ==="

  local found=0

  # phase-details.md の信頼度テーブルに 'exact' が含まれるか
  if ! grep -q "exact" "$REFS_DIR/phase-details.md" 2>/dev/null; then
    issue "doc-staleness: phase-details.md missing 'exact' confidence level"
    found=1
  fi

  # phase-details.md に未実装の 'low' 信頼度が残っていないか
  if grep -q "low.*Gap.*ばらつき\|Gap.*ばらつき.*low" "$REFS_DIR/phase-details.md" 2>/dev/null; then
    issue "doc-staleness: phase-details.md references unimplemented 'low' confidence"
    found=1
  fi

  # sectioning-prompt-template.md が Phase 2 を参照しているか
  if grep -q "Phase 3 Stage B" "$REFS_DIR/sectioning-prompt-template.md" 2>/dev/null; then
    issue "doc-staleness: sectioning-prompt-template.md references Phase 3 instead of Phase 2"
    found=1
  fi

  # autolayout_penalty が 0 であることを確認
  if grep -q "autolayout_penalty.*[1-9]" "$REFS_DIR/phase-details.md" 2>/dev/null; then
    issue "doc-staleness: phase-details.md has non-zero autolayout_penalty"
    found=1
  fi

  if [[ $found -eq 0 ]]; then
    green "  PASS: Documentation up-to-date"
  fi
}

# ================================================================
# 5. dead-code: 到達不能コード・未使用変数
# ================================================================
check_dead_code() {
  bold "=== Check: dead-code ==="

  local found=0

  # figma_utils.py の公開関数が少なくとも1つのスクリプトで使われているか
  while IFS= read -r func; do
    if [[ -n "$func" ]]; then
      if ! grep -rq "$func" "$SCRIPTS_DIR"/*.sh 2>/dev/null; then
        warn "dead-code: figma_utils.py exports '$func' but no script imports it"
        found=1
      fi
    fi
  done < <(grep -oP "^def (\w+)" "$LIB_DIR/figma_utils.py" 2>/dev/null | sed 's/^def //' || true)

  # UNNAMED_RE が使われているか
  if ! grep -rq "UNNAMED_RE" "$SCRIPTS_DIR"/*.sh 2>/dev/null; then
    warn "dead-code: UNNAMED_RE exported from figma_utils.py but unused in scripts"
    found=1
  fi

  if [[ $found -eq 0 ]]; then
    green "  PASS: No dead code detected"
  fi
}

# ================================================================
# Main
# ================================================================
echo ""
bold "╔══════════════════════════════════════════════╗"
bold "║       figma-prepare QA Checker               ║"
bold "╚══════════════════════════════════════════════╝"
echo ""

check_unused_imports
echo ""
check_stale_phase_refs
echo ""
check_yaml_key_mismatch
echo ""
check_doc_staleness
echo ""
check_dead_code
echo ""

# ================================================================
# Results
# ================================================================
bold "========================================"
if [[ ${#ISSUES[@]} -eq 0 ]] && [[ ${#WARNINGS[@]} -eq 0 ]]; then
  green "  QA: ALL CLEAN — 0 issues, 0 warnings"
  bold "========================================"

  if $JSON_MODE; then
    echo '{"status":"clean","issues":[],"warnings":[]}'
  fi
  exit 0
else
  if [[ ${#ISSUES[@]} -gt 0 ]]; then
    red "  QA: ${#ISSUES[@]} issue(s) found"
    for i in "${ISSUES[@]}"; do
      red "    - $i"
    done
  fi
  if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    yellow "  QA: ${#WARNINGS[@]} warning(s) found"
    for w in "${WARNINGS[@]}"; do
      yellow "    - $w"
    done
  fi
  bold "========================================"

  if $JSON_MODE; then
    # Issue 64: Use temp files to avoid shell injection in Python string literals
    tmp_issues=$(mktemp)
    tmp_warnings=$(mktemp)
    printf '%s\n' "${ISSUES[@]}" > "$tmp_issues"
    printf '%s\n' "${WARNINGS[@]}" > "$tmp_warnings"
    python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    issues = [l.strip() for l in f if l.strip()]
with open(sys.argv[2]) as f:
    warnings = [l.strip() for l in f if l.strip()]
print(json.dumps({'status': 'issues_found', 'issues': issues, 'warnings': warnings}, indent=2))
" "$tmp_issues" "$tmp_warnings"
    rm -f "$tmp_issues" "$tmp_warnings"
  fi

  # issues があれば exit 1, warnings のみなら exit 0
  [[ ${#ISSUES[@]} -gt 0 ]] && exit 1
  exit 0
fi
