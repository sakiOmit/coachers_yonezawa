#!/usr/bin/env python3
"""
PostToolUse Hook: Skill呼び出しをリアルタイムで記録

Skill ツール使用時に .claude/logs/skill-usage.jsonl へ追記する。
analyze-usage.py がこのログを優先的に読み、JONLフルスキャンを回避する。
"""
import json
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "skill-usage.jsonl"

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

tool_name = input_data.get("tool_name", "")

if tool_name != "Skill":
    sys.exit(0)

tool_input = input_data.get("tool_input", {})
skill_name = tool_input.get("skill", "")

if not skill_name:
    sys.exit(0)

# "prefix:name" 形式の場合、末尾を使用
if ":" in skill_name:
    skill_name = skill_name.split(":")[-1]

# ログディレクトリ作成
LOG_DIR.mkdir(parents=True, exist_ok=True)

# JSONL形式で追記
entry = {
    "timestamp": datetime.now().isoformat(),
    "skill": skill_name,
    "args": tool_input.get("args", ""),
    "session_id": input_data.get("session_id", ""),
}

with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

sys.exit(0)
