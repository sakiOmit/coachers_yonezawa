#!/usr/bin/env python3
"""
PostToolUse Hook: ファイル編集後の通知と自動チェック提案
"""
import json
import sys
import os

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})

if tool_name not in ["Edit", "Write"]:
    sys.exit(0)

file_path = tool_input.get("file_path", "")
if not file_path:
    sys.exit(0)

# ファイル種別に応じたコンテキスト追加
context_parts = []

# SCSSファイル
if file_path.endswith(".scss"):
    context_parts.append(f"✓ SCSS修正: {os.path.basename(file_path)}")

# PHPファイル
elif file_path.endswith(".php"):
    context_parts.append(f"✓ PHP修正: {os.path.basename(file_path)}")

# JSファイル
elif file_path.endswith((".js", ".ts")):
    context_parts.append(f"✓ JS修正: {os.path.basename(file_path)}")

if context_parts:
    print("\n".join(context_parts))

sys.exit(0)
