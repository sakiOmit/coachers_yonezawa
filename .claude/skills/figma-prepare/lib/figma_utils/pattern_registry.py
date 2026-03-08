"""Cross-section pattern registry for figma-prepare.

Builds a registry of recurring structural patterns across all sections,
enabling consistent grouping and naming. When the same card structure
appears in section-features and section-testimonials, this registry
ensures both are recognized as the same pattern.

Round 2, Proposal D.
"""

from collections import defaultdict

from .geometry import filter_visible_children
from .scoring import structure_hash


def build_pattern_registry(root, min_occurrences=2):
    """Build a registry of recurring structural patterns across all sections.

    Walks the tree, computes structure_hash for each non-leaf FRAME/GROUP/INSTANCE/COMPONENT,
    and tracks frequency across sections.

    Args:
        root: Root node of the Figma metadata tree.
        min_occurrences: Minimum occurrences to include in registry.

    Returns:
        Dict of structure_hash -> {
            'count': int,
            'sections': list of parent section names,
            'example_ids': list of first 5 node IDs,
            'node_type': most common node type,
        }
    """
    hash_data = defaultdict(lambda: {
        'count': 0, 'sections': set(), 'example_ids': [], 'types': defaultdict(int)
    })

    # Handle list input (root_children) by wrapping in a synthetic root node
    if isinstance(root, list):
        children = [c for c in root if c.get('visible') != False]
        synthetic_root = {'type': 'FRAME', 'name': 'root', 'children': children}
        _walk_for_patterns(synthetic_root, hash_data, section_name='root')
    else:
        _walk_for_patterns(root, hash_data, section_name='root')

    # Filter by min_occurrences and format
    registry = {}
    for h, data in hash_data.items():
        if data['count'] >= min_occurrences:
            dominant_type = max(data['types'], key=data['types'].get) if data['types'] else ''
            registry[h] = {
                'count': data['count'],
                'sections': sorted(data['sections']),
                'example_ids': data['example_ids'][:5],
                'node_type': dominant_type,
            }

    return registry


def _walk_for_patterns(node, hash_data, section_name='root'):
    """Recursively walk tree and collect structure hashes.

    Args:
        node: Current node.
        hash_data: Accumulator dict.
        section_name: Current section context name.
    """
    children = filter_visible_children(node)
    node_type = node.get('type', '')
    node_name = node.get('name', '')

    # Update section context for top-level named frames
    current_section = section_name
    if node_type in ('FRAME', 'SECTION') and node_name and not node_name.startswith(('Frame ', 'Group ')):
        current_section = node_name

    # Hash non-leaf container nodes
    if node_type in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT') and children:
        h = structure_hash(node)
        hash_data[h]['count'] += 1
        hash_data[h]['sections'].add(current_section)
        if len(hash_data[h]['example_ids']) < 5:
            node_id = node.get('id', '')
            if node_id:
                hash_data[h]['example_ids'].append(node_id)
        hash_data[h]['types'][node_type] += 1

    for child in children:
        _walk_for_patterns(child, hash_data, current_section)


def lookup_pattern(structure_hash_val, registry):
    """Look up a structure hash in the registry.

    Args:
        structure_hash_val: Hash to look up.
        registry: Registry from build_pattern_registry().

    Returns:
        Registry entry dict or None.
    """
    return registry.get(structure_hash_val)


def format_registry_summary(registry, max_entries=10):
    """Format registry as human-readable text for prompt injection.

    Args:
        registry: Pattern registry dict.
        max_entries: Maximum entries to include.

    Returns:
        str: Formatted text block.
    """
    if not registry:
        return ''

    lines = ['## Cross-Section Pattern Registry']
    lines.append('The following structural patterns appear multiple times across sections:')
    lines.append('')

    # Sort by count (most frequent first)
    sorted_patterns = sorted(registry.items(), key=lambda x: x[1]['count'], reverse=True)

    for i, (h, data) in enumerate(sorted_patterns[:max_entries], 1):
        sections_str = ', '.join(data['sections'][:3])
        if len(data['sections']) > 3:
            sections_str += f' (+{len(data["sections"]) - 3} more)'
        lines.append(
            f'{i}. **{data["node_type"]}** pattern (hash: `{h[:40]}...`): '
            f'{data["count"]}x across [{sections_str}]'
        )

    lines.append('')
    lines.append('When grouping, treat elements matching these patterns consistently across sections.')
    lines.append('')
    return '\n'.join(lines)
