#!/bin/bash
set -euo pipefail

# calculate-complexity.sh
# Purpose: Calculate complexity score from Figma metadata JSON
# Input: Path to metadata JSON file (get_metadata output)
# Output: JSON with complexity scores per section
# Exit: 0=success, 1=invalid input

METADATA_FILE="${1:-}"

if [[ -z "$METADATA_FILE" || ! -f "$METADATA_FILE" ]]; then
  echo "Error: Metadata file required" >&2
  echo "Usage: $0 <metadata.json>" >&2
  exit 1
fi

# Check for python3 or node
if command -v python3 &>/dev/null; then
  python3 - "$METADATA_FILE" <<'PYEOF'
import json
import sys

def count_children(node):
    """Count direct children."""
    children = node.get("children", [])
    return len(children)

def measure_depth(node, current=0):
    """Measure maximum nesting depth."""
    children = node.get("children", [])
    if not children:
        return current
    return max(measure_depth(c, current + 1) for c in children)

def count_text_elements(node):
    """Count TEXT type elements recursively."""
    count = 1 if node.get("type") == "TEXT" else 0
    for child in node.get("children", []):
        count += count_text_elements(child)
    return count

def calculate_score(node):
    """Calculate complexity score (0-100)."""
    children = count_children(node)
    depth = measure_depth(node)
    text_count = count_text_elements(node)
    height = node.get("absoluteBoundingBox", {}).get("height", 0)

    score = (
        min(children * 2, 40)
        + min(depth * 5, 30)
        + min(text_count, 20)
        + min(height / 1000, 10)
    )
    return round(score, 1)

def determine_strategy(score, height):
    """Determine split strategy based on score and height."""
    if height >= 10000:
        return "SPLIT_REQUIRED"
    if height >= 8000 or score >= 70:
        return "SPLIT"
    if height < 5000 and score < 50:
        return "NORMAL"
    return "NORMAL"

try:
    with open(sys.argv[1], "r") as f:
        data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError) as e:
    print(f"Error: Invalid JSON - {e}", file=sys.stderr)
    sys.exit(1)

# Extract top-level frames (sections)
children = data.get("children", [])
if not children:
    # Try document > children > page > children
    document = data.get("document", data)
    children = document.get("children", [])

results = {"sections": [], "summary": {}}

for child in children:
    visible = child.get("visible", True)
    if not visible:
        continue

    name = child.get("name", "Unknown")
    node_id = child.get("id", "")
    height = child.get("absoluteBoundingBox", {}).get("height", 0)
    score = calculate_score(child)
    strategy = determine_strategy(score, height)

    results["sections"].append({
        "name": name,
        "nodeId": node_id,
        "height": round(height),
        "complexity": score,
        "strategy": strategy,
        "children_count": count_children(child),
        "depth": measure_depth(child),
        "text_count": count_text_elements(child),
    })

# Summary
scores = [s["complexity"] for s in results["sections"]]
strategies = [s["strategy"] for s in results["sections"]]
results["summary"] = {
    "total_sections": len(results["sections"]),
    "avg_complexity": round(sum(scores) / len(scores), 1) if scores else 0,
    "max_complexity": max(scores) if scores else 0,
    "NORMAL": strategies.count("NORMAL"),
    "SPLIT": strategies.count("SPLIT"),
    "SPLIT_REQUIRED": strategies.count("SPLIT_REQUIRED"),
}

print(json.dumps(results, indent=2, ensure_ascii=False))
PYEOF
else
  echo "Error: python3 required but not found" >&2
  exit 1
fi
