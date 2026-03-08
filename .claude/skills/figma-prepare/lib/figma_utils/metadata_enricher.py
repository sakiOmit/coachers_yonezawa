"""Enrich Figma metadata with resolved coordinates and design context data.

Extracted from enrich-metadata.sh (Issue refactor).
Merges enrichment data (fills, layoutMode, characters, etc.) into metadata tree.
"""

import json
import sys

from .metadata import get_root_node

# Properties to merge from enrichment into metadata nodes
ENRICHMENT_KEYS = [
    'fills', 'strokes', 'effects',
    'layoutMode', 'layoutWrap',  # Issue 137: layoutWrap for WRAP detection
    'itemSpacing',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'primaryAxisAlignItems', 'counterAxisAlignItems',
    'characters', 'style',
]


def enrich_node(node, enrichment_map, stats):
    """Recursively walk metadata tree and merge enrichment data.

    Args:
        node: Metadata tree node dict
        enrichment_map: Dict mapping nodeId -> enrichment properties
        stats: Mutable dict with 'enriched_nodes' and 'merged_keys' counters
    """
    node_id = node.get('id', '')

    if node_id in enrichment_map:
        enrich_data = enrichment_map[node_id]
        merged_keys = []
        for key in ENRICHMENT_KEYS:
            if key in enrich_data and enrich_data[key] is not None:
                node[key] = enrich_data[key]
                merged_keys.append(key)
        if merged_keys:
            stats['enriched_nodes'] += 1
            stats['merged_keys'] += len(merged_keys)

    for child in [c for c in node.get('children', []) if c.get('visible') != False]:
        enrich_node(child, enrichment_map, stats)


def enrich_metadata(metadata, enrichment):
    """Enrich metadata tree with enrichment map data.

    Args:
        metadata: Figma get_metadata output (JSON tree, modified in place)
        enrichment: Flat map { nodeId: { fills, layoutMode, characters, ... } }

    Returns:
        Dict with stats: { enriched_nodes, merged_keys, total_enrichment_entries }
    """
    root = get_root_node(metadata)

    stats = {'enriched_nodes': 0, 'merged_keys': 0}
    enrich_node(root, enrichment, stats)

    return {
        'enriched_nodes': stats['enriched_nodes'],
        'merged_keys': stats['merged_keys'],
        'total_enrichment_entries': len(enrichment),
    }


def enrich_metadata_from_files(metadata_path, enrichment_path, output_path=''):
    """Load files, enrich metadata, and output result.

    Args:
        metadata_path: Path to metadata JSON file
        enrichment_path: Path to enrichment JSON file
        output_path: If set, write enriched metadata to this file and return stats JSON.
                     If empty, return enriched metadata JSON.

    Returns:
        JSON string (stats if output_path given, full metadata otherwise)
    """
    sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    with open(enrichment_path, 'r') as f:
        enrichment = json.load(f)

    stats = enrich_metadata(metadata, enrichment)

    if output_path:
        # Write enriched metadata to file
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        result = {
            **stats,
            'output': output_path,
            'status': 'success',
        }
        return json.dumps(result, indent=2)
    else:
        # Return enriched metadata as JSON
        return json.dumps(metadata, indent=2, ensure_ascii=False)
