#!/usr/bin/env python3
"""
UserPromptSubmit Hook: レビュー/QA完了後に分析を提案
"""
import json
import sys
import re
import os
from datetime import datetime, timedelta

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

prompt = input_data.get("prompt", "")

# レビュー/QA完了を示すキーワードパターン
review_patterns = [
    r"レビュー完了",
    r"QA完了",
    r"review complete",
    r"qa complete",
    r"/qa\s+full.*完了",
    r"/review.*完了",
]

# 分析提案キーワードチェック
should_suggest = False
for pattern in review_patterns:
    if re.search(pattern, prompt, re.IGNORECASE):
        should_suggest = True
        break

if not should_suggest:
    sys.exit(0)

# 最後の分析からの経過時間をチェック
metrics_file = os.path.join(
    os.environ.get("CLAUDE_PROJECT_DIR", "."),
    ".claude/metrics/latest-analysis.json"
)

suggest_analysis = True

if os.path.exists(metrics_file):
    try:
        with open(metrics_file, 'r') as f:
            data = json.load(f)
            last_analysis = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
            # 24時間以内に分析済みならスキップ
            if datetime.now() - last_analysis < timedelta(hours=24):
                suggest_analysis = False
    except (json.JSONDecodeError, ValueError):
        pass

if suggest_analysis:
    context = """
---
[自動提案] レビューが完了しました。傾向分析を実行しますか？

`/analyze-project` - レビュー履歴から傾向を分析し、改善提案を生成

定期的な分析により、繰り返し発生する問題パターンを特定できます。
---
"""
    print(context)

sys.exit(0)
