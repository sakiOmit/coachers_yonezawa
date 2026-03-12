#!/usr/bin/env python3
"""
UserPromptSubmit Hook: 実装完了キーワード検出でレビュー提案
"""
import json
import sys
import re

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

prompt = input_data.get("prompt", "")

# 実装完了を示すキーワードパターン
completion_patterns = [
    r"実装完了",
    r"実装しました",
    r"完成しました",
    r"できました",
    r"終わりました",
    r"修正しました",
    r"対応しました",
    r"作成しました",
    r"implementation complete",
    r"done",
    r"finished",
]

# パターンマッチ
for pattern in completion_patterns:
    if re.search(pattern, prompt, re.IGNORECASE):
        # コンテキストを追加（ブロックではなくコンテキスト追加）
        context = """
---
[自動提案] 実装が完了したようです。以下のレビューコマンドを検討してください：
- `/review all` - SCSS/PHP/JS の統合レビュー
- `/qa check` - 機械的なQAチェック
- `/qa full` - 完全QA（納品前推奨）

レビューを実行する場合は上記コマンドを入力してください。
---
"""
        print(context)
        sys.exit(0)

sys.exit(0)
