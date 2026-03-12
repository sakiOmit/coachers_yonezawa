#!/usr/bin/env python3
"""
Figma MCP キャッシュ事前読み込みフック
PreToolUse で mcp__figma__get_design_context の呼び出し前にキャッシュをチェック

既存のキャッシュがTTL内であれば、APIを呼ばずにキャッシュを返す。
figma-cache.py（PostToolUse）と連携して動作する。
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# キャッシュディレクトリ（figma-cache.py と同じ）
CACHE_DIR = Path(__file__).parent.parent / "cache" / "figma"
CACHE_TTL_HOURS = 24


def find_cache(file_key: str, node_id: str) -> dict | None:
    """
    指定されたfileKey/nodeIdに一致するTTL内のキャッシュを検索

    Args:
        file_key: FigmaファイルのキーID
        node_id: FigmaノードID（例: "1:2" または "1-2"）

    Returns:
        キャッシュデータ（dict）またはNone
    """
    if not CACHE_DIR.exists():
        return None

    # nodeIdを正規化（":"を"-"に変換）
    normalized_node_id = node_id.replace(":", "-")
    cutoff = datetime.now() - timedelta(hours=CACHE_TTL_HOURS)

    # ファイル名パターン: {fileKey}_{nodeId}_{timestamp}.json
    matching_caches = []

    for cache_file in CACHE_DIR.glob("*.json"):
        if cache_file.name == "debug.log":
            continue

        # ファイル名をパース
        parts = cache_file.stem.split("_")
        if len(parts) < 3:
            continue

        cached_file_key = parts[0]
        cached_node_id = parts[1]

        # fileKeyとnodeIdが一致するか確認
        if cached_file_key != file_key or cached_node_id != normalized_node_id:
            continue

        # TTLチェック
        try:
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if mtime < cutoff:
                continue
            matching_caches.append((cache_file, mtime))
        except Exception:
            continue

    if not matching_caches:
        return None

    # 最新のキャッシュを選択
    matching_caches.sort(key=lambda x: x[1], reverse=True)
    latest_cache_file = matching_caches[0][0]

    try:
        with open(latest_cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        print(f"[figma-cache-preload] Cache hit: {latest_cache_file.name}")
        return cache_data
    except Exception as e:
        print(f"[figma-cache-preload] Error reading cache: {e}", file=sys.stderr)
        return None


def main():
    """
    PreToolUseフックのメイン処理
    stdin経由でJSONデータを受け取り、キャッシュがあれば返す
    """
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"[figma-cache-preload] Error: Invalid JSON from stdin: {e}", file=sys.stderr)
        return
    except Exception as e:
        print(f"[figma-cache-preload] Error reading stdin: {e}", file=sys.stderr)
        return

    # ツール名を確認
    tool_name = hook_input.get("tool_name", "")

    # mcp__figma__get_design_context のみ対象
    if tool_name != "mcp__figma__get_design_context":
        return

    tool_input = hook_input.get("tool_input", {})
    file_key = tool_input.get("fileKey", "")
    node_id = tool_input.get("nodeId", "")

    if not file_key or not node_id:
        print("[figma-cache-preload] Missing fileKey or nodeId")
        return

    # キャッシュを検索
    cache_data = find_cache(file_key, node_id)

    if cache_data:
        # キャッシュヒット - キャッシュ情報を出力
        cached_at = cache_data.get("cached_at", "unknown")
        output = cache_data.get("output", [])

        # outputのサイズを計算
        if isinstance(output, list):
            output_size = sum(len(json.dumps(item, ensure_ascii=False)) for item in output)
        else:
            output_size = len(str(output))

        print(f"[figma-cache-preload] Using cached response from {cached_at}")
        print(f"[figma-cache-preload] Cache size: {output_size} chars")

        # フックからのレスポンスとしてキャッシュ情報を出力
        # 注意: Claude Codeのフック仕様により、stdoutへの出力は
        # ユーザーへの通知として表示される
        # 実際のキャッシュ利用は手動でReadツールを使う必要がある
        # （PreToolUseフックでのtool_response上書きは現在サポートされていない）
        result = {
            "cache_hit": True,
            "cached_at": cached_at,
            "cache_size_chars": output_size,
            "recommendation": f"キャッシュが利用可能です。Read ツールで .claude/cache/figma/ 内の該当ファイルを読み込んでください。"
        }
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"[figma-cache-preload] No valid cache found for {file_key}/{node_id}")


if __name__ == "__main__":
    main()
