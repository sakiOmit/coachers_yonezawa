#!/usr/bin/env bash
# Phase 2 Stage C: Generate Nested Grouping Context
#
# For each leaf section in sectioning-plan.yaml, generates an enriched children
# table and a fully-populated prompt for Claude (Haiku) nested grouping inference.
#
# This script does NOT call Claude. It produces context JSON that the SKILL.md
# workflow level uses to invoke Claude, mirroring the Stage B design pattern.
#
# Issue 194 Phase 3: Stage C parallel execution alongside Stage A.
# Issue 225: --groups and --depth support for recursive nested grouping.
#
# Usage:
#   bash generate-nested-grouping-context.sh <metadata.json> <sectioning-plan.yaml> \
#     [--output nested-context.json]
#
#   bash generate-nested-grouping-context.sh <metadata.json> --groups <nested-grouping-result.json> \
#     [--depth <n>] [--output nested-context.json]
#
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo '{"error": "Usage: generate-nested-grouping-context.sh <metadata.json> <sectioning-plan.yaml> [--output nested-context.json] OR <metadata.json> --groups <groups.json> [--depth n] [--output out.json]"}' >&2
  exit 1
fi

METADATA_FILE="$1"
PLAN_FILE=""
GROUPS_FILE=""
OUTPUT_FILE=""
DEPTH="0"

if [[ ! -f "$METADATA_FILE" ]]; then
  echo "{\"error\": \"Metadata file not found: $METADATA_FILE\"}" >&2
  exit 1
fi

# Parse arguments: detect --groups mode vs plan mode
shift 1
if [[ $# -gt 0 && "$1" == "--groups" ]]; then
  # --groups mode
  GROUPS_FILE="${2:-}"
  if [[ -z "$GROUPS_FILE" ]]; then
    echo '{"error": "--groups requires a file path argument"}' >&2
    exit 1
  fi
  if [[ ! -f "$GROUPS_FILE" ]]; then
    echo "{\"error\": \"Groups file not found: $GROUPS_FILE\"}" >&2
    exit 1
  fi
  shift 2
else
  # Plan mode (original behavior)
  PLAN_FILE="$1"
  if [[ ! -f "$PLAN_FILE" ]]; then
    echo "{\"error\": \"Sectioning plan file not found: $PLAN_FILE\"}" >&2
    exit 1
  fi
  shift 1
fi

# Parse optional flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    --depth)
      DEPTH="${2:-0}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATE_FILE="$SKILLS_DIR/references/nested-grouping-prompt-template.md"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "{\"error\": \"Prompt template not found: $TEMPLATE_FILE\"}" >&2
  exit 1
fi

# Build Python arguments
PYTHON_ARGS=("--metadata" "$METADATA_FILE" "--template" "$TEMPLATE_FILE" "--depth" "$DEPTH")

if [[ -n "$PLAN_FILE" ]]; then
  PYTHON_ARGS+=("--plan" "$PLAN_FILE")
fi

if [[ -n "$GROUPS_FILE" ]]; then
  PYTHON_ARGS+=("--groups" "$GROUPS_FILE")
fi

if [[ -n "$OUTPUT_FILE" ]]; then
  PYTHON_ARGS+=("--output" "$OUTPUT_FILE")
fi

exec python3 -c "
import sys, os, argparse
sys.path.insert(0, os.path.join('${SKILLS_DIR}', 'lib'))
from figma_utils.nested_context import generate_nested_context

parser = argparse.ArgumentParser()
parser.add_argument('--metadata', required=True)
parser.add_argument('--template', required=True)
parser.add_argument('--plan', default='')
parser.add_argument('--groups', default='')
parser.add_argument('--output', default='')
parser.add_argument('--depth', type=int, default=0)
args = parser.parse_args()

generate_nested_context(
    metadata_file=args.metadata,
    template_file=args.template,
    plan_file=args.plan,
    groups_file=args.groups,
    output_file=args.output,
    depth=args.depth,
)
" "${PYTHON_ARGS[@]}"
