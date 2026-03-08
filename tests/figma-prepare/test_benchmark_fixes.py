"""Tests for benchmark accuracy improvements.

Improvement A: EN+JP detection with title-case labels and large sibling lists.
Improvement B: Zone detection minimum member count filter.
"""
import pytest

from figma_utils.detect_en_jp import _is_en_label, detect_en_jp_label_pairs
from figma_utils.grouping_zones import detect_vertical_zone_groups
from figma_utils.constants import ZONE_MIN_MEMBERS


# ============================================================
# Helper
# ============================================================

def _make_text(text, x=0, y=0, w=100, h=30, node_id=""):
    return {
        "type": "TEXT",
        "name": "Text 1",
        "id": node_id,
        "characters": text,
        "absoluteBoundingBox": {"x": x, "y": y, "width": w, "height": h},
    }


def _make_frame(name="Frame 1", x=0, y=0, w=200, h=100, node_id=""):
    return {
        "type": "FRAME",
        "name": name,
        "id": node_id,
        "absoluteBoundingBox": {"x": x, "y": y, "width": w, "height": h},
        "children": [],
    }


# ============================================================
# Improvement A: EN+JP title-case detection
# ============================================================

class TestEnJpTitleCase:
    """EN+JP pairs with title-case English labels (benchmark fix)."""

    def test_title_case_single_word(self):
        """'Environment' (title-case) + JP text -> pair detected."""
        children = [
            _make_text("Environment", x=157, y=2388, w=246, h=48),
            _make_text("環境への取り組み", x=160, y=2450, w=218, h=36),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_text'] == "Environment"
        assert pairs[0]['jp_text'] == "環境への取り組み"

    def test_title_case_multi_word(self):
        """'Human resources' (sentence-case) + JP text -> pair detected."""
        children = [
            _make_text("Human resources", x=157, y=3000, w=246, h=48),
            _make_text("人材への取り組み", x=160, y=3060, w=218, h=36),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_text'] == "Human resources"

    def test_title_case_two_words_capitalized(self):
        """'Business Organization' (title-case both words) -> pair detected."""
        children = [
            _make_text("Business Organization", x=157, y=3500, w=300, h=48),
            _make_text("事業組織への取り組み", x=160, y=3560, w=250, h=36),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_text'] == "Business Organization"

    def test_all_lowercase_still_rejected(self):
        """'environment' (all lowercase) -> not detected as EN label."""
        children = [
            _make_text("environment", x=157, y=2388, w=246, h=48),
            _make_text("環境への取り組み", x=160, y=2450, w=218, h=36),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_is_en_label_title_case(self):
        """_is_en_label accepts title-case strings."""
        assert _is_en_label("Environment") is True
        assert _is_en_label("Social") is True
        assert _is_en_label("Human resources") is True
        assert _is_en_label("Business organization") is True

    def test_is_en_label_still_rejects_lowercase(self):
        """_is_en_label still rejects all-lowercase strings."""
        assert _is_en_label("environment") is False
        assert _is_en_label("social") is False
        assert _is_en_label("human resources") is False

    def test_is_en_label_uppercase_still_works(self):
        """_is_en_label still accepts all-uppercase strings."""
        assert _is_en_label("ENVIRONMENT") is True
        assert _is_en_label("HUMAN RESOURCES") is True


class TestEnJpLargeSiblingList:
    """EN+JP pairs detected among many siblings (100+ children)."""

    def test_pairs_among_100_plus_siblings(self):
        """EN+JP pairs detected when mixed with 100+ non-text FRAME siblings."""
        children = []
        # Add 100 FRAME siblings
        for i in range(100):
            children.append(_make_frame(
                name=f"Frame {i}", x=0, y=i * 50, w=200, h=40, node_id=f"f:{i}"
            ))
        # Add EN+JP pair at the end
        children.append(_make_text("Environment", x=157, y=5100, w=246, h=48, node_id="en:1"))
        children.append(_make_text("環境への取り組み", x=160, y=5160, w=218, h=36, node_id="jp:1"))
        # Add another pair far from the first
        children.append(_make_text("Social", x=500, y=5100, w=150, h=48, node_id="en:2"))
        children.append(_make_text("社会への取り組み", x=500, y=5160, w=218, h=36, node_id="jp:2"))

        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 2
        en_texts = {p['en_text'] for p in pairs}
        assert "Environment" in en_texts
        assert "Social" in en_texts

    def test_non_consecutive_pairs(self):
        """EN+JP pairs detected when separated by non-TEXT nodes."""
        children = [
            _make_text("Environment", x=157, y=2388, w=246, h=48, node_id="en:1"),
            _make_frame(name="Separator 1", x=0, y=2400, w=1440, h=20, node_id="sep:1"),
            _make_frame(name="Separator 2", x=0, y=2420, w=1440, h=20, node_id="sep:2"),
            _make_text("環境への取り組み", x=160, y=2450, w=218, h=36, node_id="jp:1"),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_text'] == "Environment"
        assert pairs[0]['jp_text'] == "環境への取り組み"

    def test_vertical_en_above_jp(self):
        """EN label above JP label (vertical layout) -> detected."""
        children = [
            _make_text("Social", x=160, y=2800, w=120, h=48, node_id="en:1"),
            _make_text("社会への取り組み", x=160, y=2860, w=218, h=36, node_id="jp:1"),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        # Distance = 2860 - (2800+48) = 12px, well within 200px
        assert pairs[0]['en_text'] == "Social"


# ============================================================
# Improvement B: Zone minimum member count
# ============================================================

class TestZoneMinMembers:
    """Vertical zone groups filtered by minimum member count."""

    def _make_zone_node(self, y, h=200, node_id="", name="Frame 1"):
        """Create a FRAME node at the given Y position."""
        return {
            "type": "FRAME",
            "name": name,
            "id": node_id,
            "absoluteBoundingBox": {"x": 0, "y": y, "width": 1440, "height": h},
            "children": [],
        }

    def test_zone_min_members_constant(self):
        """ZONE_MIN_MEMBERS constant is 3."""
        assert ZONE_MIN_MEMBERS == 3

    def test_zone_with_3_nodes_kept(self):
        """Zone with 3 overlapping nodes -> kept in results."""
        page_bb = {"x": 0, "y": 0, "w": 1440, "h": 5000}
        # 3 nodes that overlap vertically (same Y range)
        children = [
            self._make_zone_node(y=100, h=200, node_id="1:1", name="Frame 1"),
            self._make_zone_node(y=150, h=200, node_id="1:2", name="Frame 2"),
            self._make_zone_node(y=200, h=200, node_id="1:3", name="Frame 3"),
            # Need a 4th child total for detect_vertical_zone_groups to run
            # (it has a len < 4 early return)
            # Add isolated nodes far below
            self._make_zone_node(y=2000, h=100, node_id="2:1", name="Frame 4"),
            self._make_zone_node(y=3000, h=100, node_id="3:1", name="Frame 5"),
        ]
        result = detect_vertical_zone_groups(children, page_bb)
        # The first 3 nodes should form a zone group
        zone_ids = [set(z['node_ids']) for z in result]
        assert any({"1:1", "1:2", "1:3"}.issubset(ids) for ids in zone_ids), \
            f"Expected zone with 3 nodes, got: {zone_ids}"

    def test_zone_with_2_nodes_filtered(self):
        """Zone with only 2 overlapping nodes -> filtered out."""
        page_bb = {"x": 0, "y": 0, "w": 1440, "h": 5000}
        # Create 5 isolated nodes (no zone will have 3+ members)
        children = [
            self._make_zone_node(y=0, h=100, node_id="1:1", name="Frame 1"),
            self._make_zone_node(y=500, h=100, node_id="1:2", name="Frame 2"),
            self._make_zone_node(y=1000, h=100, node_id="1:3", name="Frame 3"),
            self._make_zone_node(y=1500, h=100, node_id="1:4", name="Frame 4"),
            self._make_zone_node(y=2000, h=100, node_id="1:5", name="Frame 5"),
        ]
        result = detect_vertical_zone_groups(children, page_bb)
        # All zones should have 1 node each (all isolated), so all filtered out
        assert len(result) == 0

    def test_zone_with_1_node_filtered(self):
        """Zones with single isolated nodes -> all filtered out."""
        page_bb = {"x": 0, "y": 0, "w": 1440, "h": 8000}
        # 4 completely isolated nodes (large gaps)
        children = [
            self._make_zone_node(y=0, h=50, node_id="1:1", name="Frame 1"),
            self._make_zone_node(y=2000, h=50, node_id="1:2", name="Frame 2"),
            self._make_zone_node(y=4000, h=50, node_id="1:3", name="Frame 3"),
            self._make_zone_node(y=6000, h=50, node_id="1:4", name="Frame 4"),
        ]
        result = detect_vertical_zone_groups(children, page_bb)
        assert len(result) == 0

    def test_mixed_zones_only_large_kept(self):
        """Mix of 3-node zone and 2-node zone -> only 3-node zone kept."""
        page_bb = {"x": 0, "y": 0, "w": 1440, "h": 5000}
        children = [
            # Zone A: 3 overlapping nodes (should be kept)
            self._make_zone_node(y=100, h=200, node_id="a:1", name="Frame 1"),
            self._make_zone_node(y=150, h=200, node_id="a:2", name="Frame 2"),
            self._make_zone_node(y=200, h=200, node_id="a:3", name="Frame 3"),
            # Zone B: 2 overlapping nodes far below (should be filtered)
            self._make_zone_node(y=2000, h=200, node_id="b:1", name="Frame 4"),
            self._make_zone_node(y=2050, h=200, node_id="b:2", name="Frame 5"),
        ]
        result = detect_vertical_zone_groups(children, page_bb)
        # Only zone A should survive
        assert len(result) == 1
        assert set(result[0]['node_ids']) == {"a:1", "a:2", "a:3"}
