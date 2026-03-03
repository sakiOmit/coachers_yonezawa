#!/bin/bash
# detect-shared-components.sh - Detect shared components across multiple Figma page metadata files
# Usage: bash detect-shared-components.sh <metadata1.json> <metadata2.json> [metadata3.json ...]
# Input: 2+ metadata JSON files (get_metadata output), each representing a page
# Output: JSON with detected shared components (name, position, structure, instance matching)
# Exit: 0=success, 1=invalid input

set -uo pipefail

if [[ $# -lt 2 ]]; then
  echo "Error: At least 2 metadata files required" >&2
  echo "Usage: $0 <metadata1.json> <metadata2.json> [...]" >&2
  exit 1
fi

# Validate all files exist
for f in "$@"; do
  if [[ ! -f "$f" ]]; then
    echo "Error: File not found: $f" >&2
    exit 1
  fi
done

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 required but not found" >&2
  exit 1
fi

python3 - "$@" <<'PYEOF'
import json
import sys
from collections import defaultdict


def extract_sections(data):
    """Extract top-level visible frames (sections) from metadata."""
    children = data.get("children", [])
    if not children:
        document = data.get("document", data)
        children = document.get("children", [])
    sections = []
    for child in children:
        if not child.get("visible", True):
            continue
        sections.append(child)
    return sections


def get_node_type(node):
    """Get node type string."""
    return node.get("type", "UNKNOWN")


def count_children_recursive(node):
    """Count all descendants."""
    children = node.get("children", [])
    total = len(children)
    for c in children:
        total += count_children_recursive(c)
    return total


def get_child_types(node):
    """Get sorted list of direct children types for structure comparison."""
    children = node.get("children", [])
    return sorted(get_node_type(c) for c in children)


def get_bounding_box(node):
    """Get absoluteBoundingBox safely."""
    return node.get("absoluteBoundingBox", {})


# --- Detection Methods ---

def detect_by_name(pages_sections):
    """3-1. Name matching: find sections with identical names across pages."""
    name_map = defaultdict(list)
    for page_name, sections in pages_sections.items():
        for section in sections:
            sname = section.get("name", "").strip()
            if sname:
                name_map[sname].append({
                    "page": page_name,
                    "nodeId": section.get("id", ""),
                    "type": get_node_type(section),
                })
    results = []
    for name, occurrences in name_map.items():
        pages = list(set(o["page"] for o in occurrences))
        if len(pages) >= 2:
            results.append({
                "name": name,
                "detection_method": "name",
                "pages": sorted(pages),
                "occurrence_count": len(occurrences),
                "occurrences": occurrences,
            })
    return results


def detect_by_position(pages_sections):
    """3-2. Position matching: find sections at same relative position across pages."""
    POSITION_TOLERANCE = 20  # px

    def classify_position(section, all_sections):
        """Classify section as top/bottom/middle based on relative y."""
        bbox = get_bounding_box(section)
        y = bbox.get("y", 0)
        height = bbox.get("height", 0)

        all_ys = [get_bounding_box(s).get("y", 0) for s in all_sections]
        if not all_ys:
            return "unknown", y
        min_y = min(all_ys)
        max_bottom = max(
            get_bounding_box(s).get("y", 0) + get_bounding_box(s).get("height", 0)
            for s in all_sections
        )

        if abs(y - min_y) <= POSITION_TOLERANCE:
            return "top", y
        if abs((y + height) - max_bottom) <= POSITION_TOLERANCE:
            return "bottom", y
        return "middle", y

    position_map = defaultdict(list)
    for page_name, sections in pages_sections.items():
        for section in sections:
            pos_class, y_val = classify_position(section, sections)
            position_map[pos_class].append({
                "page": page_name,
                "name": section.get("name", ""),
                "nodeId": section.get("id", ""),
                "y": y_val,
                "height": get_bounding_box(section).get("height", 0),
            })

    results = []
    for pos_class, occurrences in position_map.items():
        if pos_class == "middle":
            continue
        pages = list(set(o["page"] for o in occurrences))
        if len(pages) >= 2:
            # Group by similar height (within tolerance)
            representative = occurrences[0]
            similar = [
                o for o in occurrences
                if abs(o["height"] - representative["height"]) <= POSITION_TOLERANCE * 5
            ]
            sim_pages = list(set(o["page"] for o in similar))
            if len(sim_pages) >= 2:
                names = list(set(o["name"] for o in similar))
                results.append({
                    "name": names[0] if len(names) == 1 else f"{pos_class} element ({', '.join(names[:3])})",
                    "detection_method": "position",
                    "position": pos_class,
                    "pages": sorted(sim_pages),
                    "occurrence_count": len(similar),
                    "occurrences": similar,
                })
    return results


def detect_by_structure(pages_sections):
    """3-3. Structure matching: find sections with similar child structures."""
    structure_map = defaultdict(list)
    for page_name, sections in pages_sections.items():
        for section in sections:
            child_types = tuple(get_child_types(section))
            child_count = len(section.get("children", []))
            if child_count == 0:
                continue
            key = (child_types, child_count)
            structure_map[key].append({
                "page": page_name,
                "name": section.get("name", ""),
                "nodeId": section.get("id", ""),
                "child_count": child_count,
                "child_types": list(child_types),
            })

    results = []
    for key, occurrences in structure_map.items():
        pages = list(set(o["page"] for o in occurrences))
        if len(pages) >= 2:
            names = list(set(o["name"] for o in occurrences))
            # Skip if already detected by name (same name across pages)
            if len(names) == 1:
                continue
            results.append({
                "name": f"Similar structure ({', '.join(names[:3])})",
                "detection_method": "structure",
                "pages": sorted(pages),
                "occurrence_count": len(occurrences),
                "child_types": list(key[0]),
                "child_count": key[1],
                "occurrences": occurrences,
            })
    return results


def detect_by_instance(pages_sections):
    """3-4. Instance detection: find Figma component instances shared across pages."""
    instance_map = defaultdict(list)

    def find_instances(node, page_name):
        if get_node_type(node) == "INSTANCE":
            comp_id = node.get("componentId", "")
            if comp_id:
                instance_map[comp_id].append({
                    "page": page_name,
                    "name": node.get("name", ""),
                    "nodeId": node.get("id", ""),
                    "componentId": comp_id,
                })
        for child in node.get("children", []):
            find_instances(child, page_name)

    for page_name, sections in pages_sections.items():
        for section in sections:
            find_instances(section, page_name)

    results = []
    for comp_id, occurrences in instance_map.items():
        pages = list(set(o["page"] for o in occurrences))
        if len(pages) >= 2:
            names = list(set(o["name"] for o in occurrences))
            results.append({
                "name": names[0] if names else comp_id,
                "detection_method": "instance",
                "componentId": comp_id,
                "pages": sorted(pages),
                "occurrence_count": len(occurrences),
                "occurrences": occurrences,
            })
    return results


def suggest_type(name):
    """Suggest component type from name."""
    name_lower = name.lower()
    type_keywords = {
        "header": "header",
        "footer": "footer",
        "nav": "navigation",
        "button": "button",
        "btn": "button",
        "card": "card",
        "hero": "hero",
        "cta": "cta",
        "form": "form",
        "modal": "modal",
        "menu": "navigation",
        "sidebar": "sidebar",
        "breadcrumb": "breadcrumb",
        "tab": "tab",
        "accordion": "accordion",
        "slider": "slider",
        "carousel": "slider",
    }
    for keyword, comp_type in type_keywords.items():
        if keyword in name_lower:
            return comp_type
    return "unknown"


def deduplicate(all_results):
    """Remove duplicate detections, preferring more specific methods."""
    priority = {"instance": 4, "name": 3, "structure": 2, "position": 1}
    seen = {}

    for result in sorted(all_results, key=lambda r: priority.get(r["detection_method"], 0), reverse=True):
        pages_key = tuple(sorted(result["pages"]))
        name_key = result["name"].lower().strip()

        dedup_key = (name_key, pages_key)
        if dedup_key not in seen:
            seen[dedup_key] = result

    return list(seen.values())


# --- Main ---

files = sys.argv[1:]
pages_sections = {}

for filepath in files:
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Warning: Skipping {filepath} - {e}", file=sys.stderr)
        continue

    # Derive page name from filename or metadata
    page_name = data.get("name", filepath.rsplit("/", 1)[-1].replace(".json", ""))
    sections = extract_sections(data)
    pages_sections[page_name] = sections

if len(pages_sections) < 2:
    print("Error: Need at least 2 valid page metadata files", file=sys.stderr)
    sys.exit(1)

# Run all 4 detection methods
name_results = detect_by_name(pages_sections)
position_results = detect_by_position(pages_sections)
structure_results = detect_by_structure(pages_sections)
instance_results = detect_by_instance(pages_sections)

all_results = name_results + position_results + structure_results + instance_results
deduplicated = deduplicate(all_results)

# Add suggested_type
for r in deduplicated:
    r["suggested_type"] = suggest_type(r["name"])
    # Remove verbose occurrences for cleaner output
    r.pop("occurrences", None)

# Summary
output = {
    "shared_components": deduplicated,
    "summary": {
        "total_detected": len(deduplicated),
        "by_method": {
            "name": len(name_results),
            "position": len(position_results),
            "structure": len(structure_results),
            "instance": len(instance_results),
        },
        "pages_analyzed": len(pages_sections),
        "page_names": sorted(pages_sections.keys()),
    },
}

print(json.dumps(output, indent=2, ensure_ascii=False))
PYEOF
