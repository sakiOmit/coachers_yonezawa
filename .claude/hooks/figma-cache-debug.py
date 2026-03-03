#!/usr/bin/env python3
"""
Figma MCP フック デバッグスクリプト
PostToolUseフックで渡されるデータをログファイルに出力

重要: PostToolUseフックはstdin経由でJSONを受け取る（環境変数ではない）
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ログディレクトリ
LOG_DIR = Path(__file__).parent.parent / "cache" / "figma"
LOG_FILE = LOG_DIR / "debug.log"

def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()

    log_entry = {
        "timestamp": timestamp,
        "env_CLAUDE_PROJECT_DIR": os.environ.get("CLAUDE_PROJECT_DIR", "NOT SET"),
    }

    # stdin から JSON を読み込む
    try:
        stdin_content = sys.stdin.read()
        log_entry["stdin_raw_length"] = len(stdin_content)

        if stdin_content:
            hook_input = json.loads(stdin_content)
            log_entry["hook_input_parsed"] = True
            log_entry["hook_event_name"] = hook_input.get("hook_event_name", "N/A")
            log_entry["tool_name"] = hook_input.get("tool_name", "N/A")
            log_entry["tool_use_id"] = hook_input.get("tool_use_id", "N/A")

            # tool_input の内容
            tool_input = hook_input.get("tool_input", {})
            log_entry["tool_input"] = tool_input

            # tool_response の存在とサイズ
            tool_response = hook_input.get("tool_response")
            if tool_response is not None:
                if isinstance(tool_response, dict):
                    response_str = json.dumps(tool_response, ensure_ascii=False)
                else:
                    response_str = str(tool_response)
                log_entry["tool_response_exists"] = True
                log_entry["tool_response_length"] = len(response_str)
                log_entry["tool_response_type"] = type(tool_response).__name__
                # レスポンスの最初の500文字（デバッグ用）
                log_entry["tool_response_preview"] = response_str[:500] if len(response_str) > 500 else response_str
            else:
                log_entry["tool_response_exists"] = False

            # 全キーを記録
            log_entry["hook_input_keys"] = list(hook_input.keys())
        else:
            log_entry["stdin_content"] = "EMPTY"
            log_entry["hook_input_parsed"] = False

    except json.JSONDecodeError as e:
        log_entry["json_error"] = str(e)
        log_entry["stdin_raw_preview"] = stdin_content[:500] if stdin_content else "EMPTY"
    except Exception as e:
        log_entry["error"] = str(e)

    # ログファイルに追記
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2))
        f.write("\n")

    print(f"[figma-cache-debug] Logged to {LOG_FILE}")

if __name__ == "__main__":
    main()
