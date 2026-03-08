"""Convert Figma MCP XML metadata to JSON format for figma_utils.

The figma_utils.metadata module already handles XML natively via
``load_metadata()`` and ``parse_figma_xml()``.  This script is a thin
convenience wrapper that:

1. Reads a raw Figma MCP XML file (as returned by ``get_metadata``).
2. Parses it using the project's built-in XML parser.
3. Writes a JSON fixture file in the standard ``{'document': ...}`` format
   expected by ``run_structure_analysis``, ``detect_grouping_candidates``,
   ``generate_rename_map``, and ``run_autolayout_inference``.

Usage:
    python convert_xml_to_json.py input.xml output.json
    python convert_xml_to_json.py --batch dir_with_xmls/ output_dir/
"""

import json
import os
import sys

# Add the figma_utils lib to the path
LIB_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..',
    '.claude', 'skills', 'figma-prepare', 'lib',
)
sys.path.insert(0, os.path.abspath(LIB_DIR))

from figma_utils.metadata import parse_figma_xml  # noqa: E402


def convert_xml_string(xml_string):
    """Convert raw XML metadata string to JSON-compatible dict.

    Returns:
        dict: ``{'document': <root_node_dict>}``
    """
    root = parse_figma_xml(xml_string)
    return {'document': root}


def convert_file(xml_path, json_path):
    """Convert a single XML file to JSON fixture.

    Returns:
        dict: The converted data (also written to *json_path*).
    """
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_str = f.read()

    data = convert_xml_string(xml_str)

    os.makedirs(os.path.dirname(json_path) or '.', exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return data


def batch_convert(xml_dir, json_dir):
    """Convert all *.xml files in *xml_dir* to JSON in *json_dir*."""
    os.makedirs(json_dir, exist_ok=True)
    converted = []
    for fname in sorted(os.listdir(xml_dir)):
        if not fname.endswith('.xml'):
            continue
        xml_path = os.path.join(xml_dir, fname)
        json_name = fname.replace('.xml', '.json')
        json_path = os.path.join(json_dir, json_name)
        convert_file(xml_path, json_path)
        converted.append((xml_path, json_path))
        print(f"  {fname} -> {json_name}")
    return converted


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} input.xml output.json")
        print(f"       {sys.argv[0]} --batch xml_dir/ json_dir/")
        sys.exit(1)

    if sys.argv[1] == '--batch':
        xml_dir = sys.argv[2]
        json_dir = sys.argv[3] if len(sys.argv) > 3 else xml_dir
        results = batch_convert(xml_dir, json_dir)
        print(f"Converted {len(results)} file(s)")
    else:
        xml_path = sys.argv[1]
        json_path = sys.argv[2]
        convert_file(xml_path, json_path)
        print(f"Converted {xml_path} -> {json_path}")


if __name__ == '__main__':
    main()
