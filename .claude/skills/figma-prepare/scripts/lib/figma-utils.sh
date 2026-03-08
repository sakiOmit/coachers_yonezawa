#!/usr/bin/env bash
# Shared utilities for figma-prepare shell scripts.
#
# Usage (from any .sh script in scripts/):
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/lib/figma-utils.sh"
#
# Provides:
#   SKILLS_DIR  - absolute path to .claude/skills/figma-prepare/
#   LIB_DIR     - absolute path to .claude/skills/figma-prepare/lib/
#   FIGMA_PYTHON_PATH_SETUP - Python snippet to insert LIB_DIR into sys.path
#   validate_input_file <path> <usage-msg>  - exit 1 if file missing
#   run_figma_python <python-code> [args...] - run Python with figma_utils on path

# Guard: SCRIPT_DIR must be set by the caller before sourcing this file.
if [[ -z "${SCRIPT_DIR:-}" ]]; then
  echo "ERROR: SCRIPT_DIR must be set before sourcing figma-utils.sh" >&2
  exit 1
fi

# Derived paths
SKILLS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIB_DIR="${SKILLS_DIR}/lib"

# Python one-liner to insert LIB_DIR into sys.path (for embedding in -c strings)
FIGMA_PYTHON_PATH_SETUP="import sys, os; sys.path.insert(0, '${LIB_DIR}')"

# ---------------------------------------------------------------------------
# validate_input_file <file-path> <usage-message>
#   Prints JSON error to stderr and exits 1 if the file does not exist.
# ---------------------------------------------------------------------------
validate_input_file() {
  local file_path="$1"
  local usage_msg="${2:-Usage: <script> <file>}"
  if [[ ! -f "$file_path" ]]; then
    echo "{\"error\": \"${usage_msg}\"}" >&2
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# run_figma_python <python-code> [args...]
#   Executes python3 -c with LIB_DIR already on sys.path.
#   The Python code can import figma_utils.* directly.
#   Additional arguments are passed as sys.argv[1..].
# ---------------------------------------------------------------------------
run_figma_python() {
  local code="$1"
  shift
  python3 -c "
import sys, os
sys.path.insert(0, '${LIB_DIR}')
${code}
" "$@"
}
