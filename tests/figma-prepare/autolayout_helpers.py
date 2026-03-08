"""Shared helper functions for autolayout test modules."""


def _bb(x, y, w, h):
    """Shorthand to create a bounding box dict."""
    return {'x': x, 'y': y, 'w': w, 'h': h}


def _node(name='Frame', ntype='FRAME', x=0, y=0, w=100, h=100, children=None, visible=True, **extra):
    """Create a minimal Figma node dict for testing."""
    node = {
        'name': name,
        'type': ntype,
        'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
        'children': children or [],
    }
    if not visible:
        node['visible'] = False
    node.update(extra)
    return node
