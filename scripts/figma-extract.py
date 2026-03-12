#!/usr/bin/env python3
"""
Figma REST API キャッシュからデザイントークンを抽出するヘルパー

REST API で取得した _rest.json キャッシュを読み込み、
実装に必要な情報（テキスト、色、フォント、スペーシング）を構造化して出力する。

Usage:
    # ページ全体のテキスト一覧
    python3 scripts/figma-extract.py texts 1:2883

    # 特定セクションのスタイル情報
    python3 scripts/figma-extract.py styles 1:3008

    # ページ構造ツリー（セクション一覧）
    python3 scripts/figma-extract.py tree 1:2883

    # 特定ノードの詳細
    python3 scripts/figma-extract.py node 1:2883 --find 1:3016

    # デザイントークン抽出（色・フォント・スペーシング）
    python3 scripts/figma-extract.py tokens 1:2883
"""

import os
import sys
import json
import argparse
from pathlib import Path
from collections import Counter

CACHE_DIR = Path(__file__).resolve().parent.parent / ".claude" / "cache" / "figma"
RENAME_MAP_FILE = CACHE_DIR / "rename-map.yaml"

# Rename map: nodeId -> semantic name (loaded once)
_rename_map = {}


def load_rename_map():
    """rename-map.yaml を読み込み、nodeId -> new name のマップを構築"""
    global _rename_map
    if not RENAME_MAP_FILE.exists():
        return

    with open(RENAME_MAP_FILE, encoding="utf-8") as f:
        content = f.read()

    # 簡易YAMLパース（PyYAML不要）
    current_id = None
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        # "30:281": のようなキー行 — 末尾の ": を除去してから引用符を除去
        if stripped.startswith('"') and stripped.endswith('":'):
            current_id = stripped[1:-2]  # "30:281": → 30:281
        elif current_id and stripped.startswith("new:"):
            new_name = stripped.split(":", 1)[1].strip().strip('"')
            _rename_map[current_id] = new_name
            current_id = None


def get_display_name(node):
    """ノードの表示名を取得（rename-map があれば適用）"""
    node_id = node.get("id", "")
    original = node.get("name", "")
    renamed = _rename_map.get(node_id)
    if renamed and renamed != original:
        return f"{renamed} (←{original})"
    return original


def detect_file_key():
    """キャッシュディレクトリから file key を自動検出"""
    rest_files = sorted(CACHE_DIR.glob("*_rest.json"), reverse=True)
    if rest_files:
        # ファイル名: {fileKey}_{nodeId}_{timestamp}_rest.json
        parts = rest_files[0].name.split("_")
        if len(parts) >= 4:
            return parts[0]

    # prefetch-info.yaml から取得
    prefetch = CACHE_DIR / "prefetch-info.yaml"
    if prefetch.exists():
        with open(prefetch) as f:
            for line in f:
                if line.strip().startswith("fileKey:"):
                    return line.split(":", 1)[1].strip().strip('"')

    return None


def find_cache(node_id, file_key=None):
    """REST版キャッシュファイルを検索（最新を優先）"""
    safe_id = node_id.replace(":", "-")

    if file_key:
        pattern = f"{file_key}_{safe_id}_*_rest.json"
        files = sorted(CACHE_DIR.glob(pattern), reverse=True)
        if files:
            return files[0]

    # file_key 不明の場合: ワイルドカードで検索
    pattern_any = f"*_{safe_id}_*_rest.json"
    files = sorted(CACHE_DIR.glob(pattern_any), reverse=True)
    if files:
        return files[0]

    # fallback: MCP版
    pattern_mcp = f"*_{safe_id}_*.json"
    files_mcp = sorted(
        [f for f in CACHE_DIR.glob(pattern_mcp) if "_rest.json" not in f.name],
        reverse=True,
    )
    if files_mcp:
        return files_mcp[0]
    return None


def load_node_data(node_id, file_key=None):
    """キャッシュからノードデータを読み込み"""
    cache_file = find_cache(node_id, file_key)
    if not cache_file:
        print(f"ERROR: Cache not found for {node_id}", file=sys.stderr)
        print(f"Run: python3 scripts/figma-fetch-all.py --pages {node_id}", file=sys.stderr)
        sys.exit(1)

    with open(cache_file, encoding="utf-8") as f:
        data = json.load(f)

    # REST API format: { "nodes": { "1:2883": { "document": {...} } } }
    nodes = data.get("nodes", {})
    for nid, ndata in nodes.items():
        return ndata.get("document", {}), cache_file.name

    return {}, cache_file.name


def find_node_by_id(root, target_id):
    """ノードツリーから特定IDのノードを再帰検索"""
    if root.get("id") == target_id:
        return root
    for child in root.get("children", []):
        found = find_node_by_id(child, target_id)
        if found:
            return found
    return None


# --- Commands ---

def cmd_texts(root, _args):
    """全テキストノードを一覧出力"""
    def walk(node, depth=0):
        if node.get("type") == "TEXT":
            chars = node.get("characters", "").replace("\n", "\\n")
            style = node.get("style", {})
            font = style.get("fontFamily", "?")
            size = style.get("fontSize", "?")
            weight = style.get("fontWeight", "?")
            name = get_display_name(node)
            print(f"{'  ' * depth}[{node['id']}] \"{name}\" {font} {size}px w{weight} | {chars[:120]}")
        for child in node.get("children", []):
            walk(child, depth + 1)

    walk(root)


def cmd_styles(root, _args):
    """ノード内の全スタイル情報を構造化出力"""
    def walk(node, depth=0):
        ntype = node.get("type", "")
        name = get_display_name(node)

        info_parts = []

        # fills
        fills = node.get("fills", [])
        for fill in fills:
            if fill.get("type") == "SOLID" and fill.get("visible", True):
                c = fill.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                a = c.get("a", 1)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                if a < 1:
                    info_parts.append(f"fill:{hex_color} a={a:.2f}")
                else:
                    info_parts.append(f"fill:{hex_color}")

        # strokes
        strokes = node.get("strokes", [])
        for stroke in strokes:
            if stroke.get("type") == "SOLID" and stroke.get("visible", True):
                c = stroke.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                sw = node.get("strokeWeight", 1)
                info_parts.append(f"stroke:#{r:02x}{g:02x}{b:02x} {sw}px")

        # text style
        if ntype == "TEXT":
            style = node.get("style", {})
            font = style.get("fontFamily", "")
            size = style.get("fontSize", "")
            weight = style.get("fontWeight", "")
            lh = style.get("lineHeightPx", "")
            ls = style.get("letterSpacing", "")
            info_parts.append(f"font:{font} {size}px w{weight}")
            if lh:
                info_parts.append(f"lh:{lh}px")
            if ls:
                info_parts.append(f"ls:{ls}px")

        # layout
        bbox = node.get("absoluteBoundingBox", {})
        w = bbox.get("width", "")
        h = bbox.get("height", "")

        # padding (from layout)
        paddings = []
        for key in ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft"]:
            val = node.get(key)
            if val is not None:
                paddings.append(f"{key.replace('padding', 'p').lower()[0:2]}:{val}")

        gap = node.get("itemSpacing")
        layout_mode = node.get("layoutMode", "")

        if layout_mode:
            info_parts.append(f"layout:{layout_mode}")
        if gap is not None:
            info_parts.append(f"gap:{gap}")
        if paddings:
            info_parts.append(" ".join(paddings))

        # Overflow detection: child bbox exceeds parent bbox (threshold: 20px)
        # Ignores minor overflow from strokes/anti-aliasing
        children = node.get("children", [])
        if bbox and children:
            parent_x = bbox.get("x", 0)
            parent_y = bbox.get("y", 0)
            parent_w = bbox.get("width", 0)
            parent_h = bbox.get("height", 0)
            overflow_threshold = 20
            for child in children:
                child_bb = child.get("absoluteBoundingBox")
                if not child_bb:
                    continue
                cx = child_bb.get("x", 0)
                cy = child_bb.get("y", 0)
                cw = child_bb.get("width", 0)
                ch = child_bb.get("height", 0)
                overflow_dirs = []
                if parent_x - cx > overflow_threshold:
                    overflow_dirs.append(f"left:{parent_x - cx:.0f}px")
                if parent_y - cy > overflow_threshold:
                    overflow_dirs.append(f"top:{parent_y - cy:.0f}px")
                if (cx + cw) - (parent_x + parent_w) > overflow_threshold:
                    overflow_dirs.append(f"right:{(cx + cw) - (parent_x + parent_w):.0f}px")
                if (cy + ch) - (parent_y + parent_h) > overflow_threshold:
                    overflow_dirs.append(f"bottom:{(cy + ch) - (parent_y + parent_h):.0f}px")
                if overflow_dirs:
                    child_name = get_display_name(child)
                    info_parts.append(f"⚠OVERFLOW child=\"{child_name}\" {' '.join(overflow_dirs)}")

        # Visual padding: detect discrepancy from primaryAxisAlignItems/counterAxisAlignItems
        if layout_mode and bbox and children:
            children_with_bb = [c for c in children if c.get("absoluteBoundingBox")]
            if children_with_bb:
                parent_x = bbox.get("x", 0)
                parent_y = bbox.get("y", 0)
                parent_w = bbox.get("width", 0)
                parent_h = bbox.get("height", 0)
                first_bb = children_with_bb[0]["absoluteBoundingBox"]
                last_bb = children_with_bb[-1]["absoluteBoundingBox"]

                warnings = []
                threshold = 2  # px差分の警告閾値

                if layout_mode == "VERTICAL":
                    vp_top = first_bb["y"] - parent_y
                    vp_bottom = (parent_y + parent_h) - (last_bb["y"] + last_bb["height"])
                    fp_top = node.get("paddingTop", 0) or 0
                    fp_bottom = node.get("paddingBottom", 0) or 0
                    # Only warn when frame padding is explicitly set (>0)
                    if fp_top > 0 and abs(vp_top - fp_top) > threshold:
                        warnings.append(f"visual-pt:{vp_top:.0f}(frame:{fp_top:.0f})")
                    if fp_bottom > 0 and abs(vp_bottom - fp_bottom) > threshold:
                        warnings.append(f"visual-pb:{vp_bottom:.0f}(frame:{fp_bottom:.0f})")
                elif layout_mode == "HORIZONTAL":
                    vp_left = first_bb["x"] - parent_x
                    vp_right = (parent_x + parent_w) - (last_bb["x"] + last_bb["width"])
                    fp_left = node.get("paddingLeft", 0) or 0
                    fp_right = node.get("paddingRight", 0) or 0
                    if fp_left > 0 and abs(vp_left - fp_left) > threshold:
                        warnings.append(f"visual-pl:{vp_left:.0f}(frame:{fp_left:.0f})")
                    if fp_right > 0 and abs(vp_right - fp_right) > threshold:
                        warnings.append(f"visual-pr:{vp_right:.0f}(frame:{fp_right:.0f})")

                if warnings:
                    align_info = node.get("primaryAxisAlignItems", "")
                    info_parts.append(f"⚠VISUAL {' '.join(warnings)} align:{align_info}")

        info = "  ".join(info_parts) if info_parts else ""

        if info or ntype in ("TEXT", "FRAME", "COMPONENT", "INSTANCE"):
            size_str = f"{w:.0f}x{h:.0f}" if isinstance(w, (int, float)) else ""
            print(f"{'  ' * depth}[{node.get('id')}] {ntype} \"{name}\" {size_str}  {info}")

        for child in node.get("children", []):
            walk(child, depth + 1)

    walk(root)


def cmd_tree(root, _args):
    """ページ構造ツリーを出力（セクション単位）"""
    def walk(node, depth=0):
        ntype = node.get("type", "")
        name = get_display_name(node)
        children_count = len(node.get("children", []))
        bbox = node.get("absoluteBoundingBox", {})
        y = bbox.get("y", "")
        h = bbox.get("height", "")

        marker = ""
        if ntype == "TEXT":
            chars = node.get("characters", "").replace("\n", " ")[:60]
            marker = f'  → "{chars}"'

        y_str = f"y={y:.0f}" if isinstance(y, (int, float)) else ""
        h_str = f"h={h:.0f}" if isinstance(h, (int, float)) else ""

        print(f"{'  ' * depth}[{node.get('id')}] {ntype} \"{name}\" {y_str} {h_str} ({children_count} children){marker}")

        # Only go 3 levels deep for tree view
        if depth < 3:
            for child in node.get("children", []):
                walk(child, depth + 1)

    walk(root)


def cmd_node(root, args):
    """特定ノードIDの詳細を出力"""
    target = args.find
    if not target:
        print("ERROR: --find <nodeId> required", file=sys.stderr)
        sys.exit(1)

    node = find_node_by_id(root, target)
    if not node:
        print(f"Node {target} not found", file=sys.stderr)
        sys.exit(1)

    # Pretty print node without children (too large)
    output = {k: v for k, v in node.items() if k != "children"}
    output["children_count"] = len(node.get("children", []))
    output["children_ids"] = [c.get("id") for c in node.get("children", [])]
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_tokens(root, _args):
    """デザイントークンを集計（色、フォント、スペーシング）"""
    colors = Counter()
    fonts = Counter()
    font_sizes = Counter()
    spacings = Counter()

    def walk(node):
        # Colors from fills
        for fill in node.get("fills", []):
            if fill.get("type") == "SOLID" and fill.get("visible", True):
                c = fill.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                colors[f"#{r:02x}{g:02x}{b:02x}"] += 1

        # Colors from strokes
        for stroke in node.get("strokes", []):
            if stroke.get("type") == "SOLID" and stroke.get("visible", True):
                c = stroke.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                colors[f"#{r:02x}{g:02x}{b:02x} (stroke)"] += 1

        # Text styles
        if node.get("type") == "TEXT":
            style = node.get("style", {})
            font = style.get("fontFamily", "")
            size = style.get("fontSize", 0)
            weight = style.get("fontWeight", 400)
            if font:
                fonts[f"{font} w{weight}"] += 1
            if size:
                font_sizes[f"{size}px"] += 1

        # Spacing from layout
        gap = node.get("itemSpacing")
        if gap is not None and gap > 0:
            spacings[f"gap:{gap}px"] += 1

        for key in ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft"]:
            val = node.get(key)
            if val is not None and val > 0:
                spacings[f"{key}:{val}px"] += 1

        for child in node.get("children", []):
            walk(child)

    walk(root)

    print("=== Colors ===")
    for color, count in colors.most_common():
        print(f"  {color:30s}  ×{count}")

    print("\n=== Fonts ===")
    for font, count in fonts.most_common():
        print(f"  {font:40s}  ×{count}")

    print("\n=== Font Sizes ===")
    for size, count in sorted(font_sizes.items(), key=lambda x: float(x[0].replace("px", ""))):
        print(f"  {size:10s}  ×{count}")

    print("\n=== Spacings (top 20) ===")
    for sp, count in spacings.most_common(20):
        print(f"  {sp:25s}  ×{count}")


COMMANDS = {
    "texts": cmd_texts,
    "styles": cmd_styles,
    "tree": cmd_tree,
    "node": cmd_node,
    "tokens": cmd_tokens,
}


def main():
    parser = argparse.ArgumentParser(description="Extract design data from Figma REST API cache")
    parser.add_argument("command", choices=COMMANDS.keys(), help="Extraction command")
    parser.add_argument("node_id", help="Page nodeId (e.g. 1:2883)")
    parser.add_argument("--find", help="Target nodeId for 'node' command")
    parser.add_argument("--file-key", help="Figma file key (auto-detected from cache)")
    args = parser.parse_args()

    # Load rename map for semantic names
    load_rename_map()
    rename_count = len(_rename_map)

    file_key = args.file_key or detect_file_key()
    root, cache_name = load_node_data(args.node_id, file_key)
    if not root:
        print("ERROR: Empty node data", file=sys.stderr)
        sys.exit(1)

    print(f"# Source: {cache_name}")
    print(f"# Node: {args.node_id}")
    if rename_count:
        print(f"# Rename map: {rename_count} entries loaded")
    print()

    COMMANDS[args.command](root, args)


if __name__ == "__main__":
    main()
