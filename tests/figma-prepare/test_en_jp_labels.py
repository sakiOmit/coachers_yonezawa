"""Tests for EN+JP label pair detection and JP keyword map."""
import json
import os
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    detect_en_jp_label_pairs,
    JP_KEYWORD_MAP,
    _jp_keyword_lookup,
)


# ============================================================
# detect_en_jp_label_pairs (Issue 185)
# ============================================================
class TestDetectEnJpLabelPairs:
    def _make_text(self, text, x=0, y=0, w=100, h=30):
        return {
            "type": "TEXT",
            "name": "Text 1",
            "characters": text,
            "absoluteBoundingBox": {"x": x, "y": y, "width": w, "height": h},
        }

    def test_basic_pair(self):
        """COMPANY + 会社情報 at similar Y -> pair detected."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_idx'] == 0
        assert pairs[0]['jp_idx'] == 1
        assert pairs[0]['en_text'] == "COMPANY"
        assert pairs[0]['jp_text'] == "会社情報"

    def test_multi_word_en_label(self):
        """OUR BUSINESS + 事業紹介 -> pair detected (multi-word EN label)."""
        children = [
            self._make_text("OUR BUSINESS", x=100, y=100, w=200, h=30),
            self._make_text("事業紹介", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_text'] == "OUR BUSINESS"

    def test_too_many_words_not_label(self):
        """EN text with > 3 words -> not detected as label."""
        children = [
            self._make_text("THIS IS NOT A LABEL", x=100, y=100, w=400, h=30),
            self._make_text("日本語テスト", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_lowercase_not_label(self):
        """Lowercase EN text -> not detected as label."""
        children = [
            self._make_text("company info", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_too_far_apart(self):
        """EN+JP pair more than 200px apart -> not detected."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=400, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_multiple_pairs(self):
        """Multiple EN+JP pairs -> all detected."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
            self._make_text("RECRUIT", x=500, y=100, w=200, h=30),
            self._make_text("採用情報", x=500, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 2

    def test_non_text_nodes_ignored(self):
        """Non-TEXT nodes among children -> ignored."""
        children = [
            {"type": "FRAME", "name": "Frame 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 100}},
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_idx'] == 1
        assert pairs[0]['jp_idx'] == 2

    def test_single_child_no_pair(self):
        """Single child -> no pair possible."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_empty_children(self):
        """Empty children list -> no pairs."""
        assert detect_en_jp_label_pairs([]) == []

    def test_horizontal_proximity(self):
        """EN+JP pair side by side (horizontal proximity) -> detected."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=100, h=30),
            self._make_text("会社情報", x=220, y=100, w=100, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1

    def test_overlapping_nodes(self):
        """EN+JP pair overlapping -> detected (distance=0)."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=110, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1

    def test_title_case_is_label(self):
        """Title case (first letter upper) -> detected as EN label (benchmark fix)."""
        children = [
            self._make_text("Company", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_text'] == "Company"
        assert pairs[0]['jp_text'] == "会社情報"


# ============================================================
# JP_KEYWORD_MAP additions (Issue 185)
# ============================================================
class TestJpKeywordMapAdditions185:
    def test_company_info(self):
        assert _jp_keyword_lookup("会社情報") == "company-info"

    def test_business_intro(self):
        assert _jp_keyword_lookup("事業紹介") == "business"

    def test_recruit_blog(self):
        assert _jp_keyword_lookup("採用ブログ") == "recruit-blog"


# ============================================================
# generate-rename-map.sh integration: EN+JP pairs (Issue 185)
# ============================================================
class TestGenerateRenameMapEnJpPairs:
    def test_en_jp_pair_renamed(self):
        """COMPANY + 会社情報 TEXT siblings -> en-label-company + heading-company-info."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "section-root",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                "children": [
                    {
                        "id": "1:1", "type": "TEXT", "name": "Text 1",
                        "characters": "COMPANY",
                        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 200, "height": 30},
                    },
                    {
                        "id": "1:2", "type": "TEXT", "name": "Text 2",
                        "characters": "会社情報",
                        "absoluteBoundingBox": {"x": 100, "y": 140, "width": 200, "height": 30},
                    },
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            assert "1:1" in renames
            assert renames["1:1"]["new_name"] == "en-label-company"
            assert "1:2" in renames
            assert renames["1:2"]["new_name"] == "heading-company-info"
        finally:
            os.unlink(path)

    def test_en_jp_pair_recruit(self):
        """RECRUIT + 採用情報 -> en-label-recruit + heading-recruit."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "section-root",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                "children": [
                    {
                        "id": "1:1", "type": "TEXT", "name": "Text 1",
                        "characters": "RECRUIT",
                        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 200, "height": 30},
                    },
                    {
                        "id": "1:2", "type": "TEXT", "name": "Text 2",
                        "characters": "採用情報",
                        "absoluteBoundingBox": {"x": 100, "y": 140, "width": 200, "height": 30},
                    },
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            assert "1:1" in renames
            assert renames["1:1"]["new_name"] == "en-label-recruit"
            assert "1:2" in renames
            assert renames["1:2"]["new_name"] == "heading-recruit"
        finally:
            os.unlink(path)

    def test_already_named_not_overridden(self):
        """Already-named nodes (non-matching UNNAMED_RE) -> not overridden."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "section-root",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                "children": [
                    {
                        "id": "1:1", "type": "TEXT", "name": "custom-en-label",
                        "characters": "COMPANY",
                        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 200, "height": 30},
                    },
                    {
                        "id": "1:2", "type": "TEXT", "name": "Text 2",
                        "characters": "会社情報",
                        "absoluteBoundingBox": {"x": 100, "y": 140, "width": 200, "height": 30},
                    },
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            # 1:1 has custom name -> should NOT be overridden
            assert "1:1" not in renames
            # 1:2 is unnamed -> should still get heading rename
            assert "1:2" in renames
            assert renames["1:2"]["new_name"] == "heading-company-info"
        finally:
            os.unlink(path)
