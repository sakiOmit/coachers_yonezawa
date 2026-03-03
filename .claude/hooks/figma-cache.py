#!/usr/bin/env python3
"""
Figma MCP レスポンスキャッシュフック
PostToolUse で mcp__figma__get_design_context の結果を保存

重要: PostToolUseフックはstdin経由でJSONを受け取る（環境変数ではない）
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# キャッシュディレクトリ
CACHE_DIR = Path(__file__).parent.parent / "cache" / "figma"
CACHE_TTL_HOURS = 24

def clean_old_cache():
    """24時間以上経過したキャッシュを削除"""
    if not CACHE_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(hours=CACHE_TTL_HOURS)
    for cache_file in CACHE_DIR.glob("*.json"):
        # debug.logは除外
        if cache_file.name == "debug.log":
            continue
        try:
            if datetime.fromtimestamp(cache_file.stat().st_mtime) < cutoff:
                cache_file.unlink()
                print(f"[figma-cache] Deleted old cache: {cache_file.name}")
        except Exception:
            pass

def save_cache(tool_input: dict, tool_response):
    """キャッシュを保存"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    file_key = tool_input.get("fileKey", "unknown")
    node_id = tool_input.get("nodeId", "unknown").replace(":", "-")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ファイル名: {fileKey}_{nodeId}_{timestamp}.json
    cache_filename = f"{file_key}_{node_id}_{timestamp}.json"
    cache_path = CACHE_DIR / cache_filename

    # tool_responseを文字列化（dictまたはstringの場合に対応）
    if isinstance(tool_response, dict):
        response_str = json.dumps(tool_response, ensure_ascii=False)
    else:
        response_str = str(tool_response)

    cache_data = {
        "cached_at": datetime.now().isoformat(),
        "input": tool_input,
        "output": tool_response
    }

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

    print(f"[figma-cache] Saved: {cache_filename} ({len(response_str)} chars)")

def main():
    """
    PostToolUseフックのメイン処理
    stdin経由でJSONデータを受け取る
    """
    try:
        # stdin から JSON を読み込む
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"[figma-cache] Error: Invalid JSON from stdin: {e}", file=sys.stderr)
        return
    except Exception as e:
        print(f"[figma-cache] Error reading stdin: {e}", file=sys.stderr)
        return

    # ツール名を確認
    tool_name = hook_input.get("tool_name", "")

    # mcp__figma__get_design_context のみ対象
    if tool_name != "mcp__figma__get_design_context":
        return

    tool_input = hook_input.get("tool_input", {})
    tool_response = hook_input.get("tool_response", {})

    # 古いキャッシュを削除
    clean_old_cache()

    # 新しいキャッシュを保存
    if tool_response:
        save_cache(tool_input, tool_response)
    else:
        print("[figma-cache] Warning: tool_response is empty")

if __name__ == "__main__":
    main()
